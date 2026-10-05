package tr.olcumkarti.mobil.bildirim

import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.net.ConnectivityManager
import android.net.Network
import android.os.Build
import android.os.IBinder
import android.os.SystemClock
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import tr.olcumkarti.mobil.kasa.KasaDeposu
import tr.olcumkarti.mobil.kasa.KasaKayit
import tr.olcumkarti.mobil.kasa.KeystoreSarici
import java.io.File

/**
 * ANLIK IZLEME servisi (tasarim A28–A34): yalniz kayit surerken calisir; kalici bildirim "Olcum karti
 * izleniyor". Kayit bitince bitis bildirimi atilir ve servis KENDINI durdurur.
 * Ince kabuk — karar ve protokol saf katmanlarda (IzlemeDongusu, Izleyici, BildirimKarar):
 *  - zarf `files/kasa/<kimlik>.zarf`'tan, K kasadan OKUNUR (servis imzalamaz, sayaca DOKUNMAZ — sart S1;
 *    ayri surec de degil). Cozulmus araci bilgisi yalniz oturum boyunca bellekte (A31).
 *  - araciya TLS: sertifika + ad dogrulamasi zorunlu (TlsBaglanti, S2)
 *  - telefonun agi geri gelince bekleme kesilir, hemen yeniden baglanilir (A34)
 * Gunluk YOK (A45): araci adresi, konu, anahtar hicbir yere yazilmaz.
 */
class IzlemeServisi : Service() {
    private val kilit = Any()
    private val uyku = Object()
    @Volatile private var dongu: IzlemeDongusu? = null
    @Volatile private var izleyici: Izleyici? = null
    @Volatile private var karar: BildirimKarar? = null
    /** Karar katmani kurulmadan gelen yerel haber (servis yeni basladi): kurulunca uygulanir. */
    @Volatile private var bekleyenYerel: Pair<Long, Long>? = null
    private var is_: Thread? = null
    private var agGeriBildirimi: ConnectivityManager.NetworkCallback? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val kimlik = intent?.getStringExtra(EK_KIMLIK)
        if (intent?.action == EYLEM_YEREL) {
            // Uygulama ondeyken yerel akistan duyulan kayit durumu (A35: ayni olay iki kez bildirilmez).
            val kod = intent.getLongExtra(EK_DURUM, -1); val oturum = intent.getLongExtra(EK_OTURUM, -1)
            if (kimlik == calisanKimlik && kod >= 0 && oturum >= 0) {
                synchronized(kilit) {
                    val k = karar
                    if (k != null) k.yerelG(kod, oturum) else bekleyenYerel = Pair(kod, oturum)
                }
            }
            if (is_ == null) stopSelf()                       // servis yalniz bu haber icin ayaga kalkmis: kapan
            return START_NOT_STICKY
        }
        if (intent?.action != EYLEM_BASLAT || !KasaKayit.kimlikGecerli(kimlik)) { kapat(); return START_NOT_STICKY }
        if (is_ != null) return START_NOT_STICKY              // zaten izliyor

        val ayar = BildirimAyar.oku(ayarDosyasi(this))
        val gosterici = BildirimGosterici(this, ayar.dil)
        gosterici.kanallariKur()
        try {
            val tur = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE else 0
            ServiceCompat.startForeground(this, BildirimGosterici.IZLEME_NO, gosterici.izleme("baglaniyor"), tur)
        } catch (e: Exception) {
            // Android 12+: arka plandan on plan servisi baslatilamadi (A29) — sessizce vazgec.
            stopSelf(); return START_NOT_STICKY
        }
        gosterici.ayarYenileKaldir()
        calisanKimlik = kimlik
        sonDurum = "baglaniyor"
        agiDinle()
        is_ = Thread({ calis(kimlik!!, ayar, gosterici) }, "izleme").also { it.start() }
        return START_NOT_STICKY
    }

    private fun calis(kimlik: String, ayar: BildirimAyar, gosterici: BildirimGosterici) {
        var bitis = "durduruldu"
        try {
            val kasaDizini = File(filesDir, KASA_DIZINI)
            val depo = BildirimDeposu(kasaDizini)
            val kasa = KasaDeposu(kasaDizini, KeystoreSarici(packageManager.hasSystemFeature(PackageManager.FEATURE_STRONGBOX_KEYSTORE)))
            val k = BildirimKarar(
                cikis = { gosterici.goster(it) },
                saatS = { SystemClock.elapsedRealtime() / 1000.0 },
                acik = { ayar.acik(it) },
                onceki = depo.olayOku(kimlik),
                kaliciYaz = { a, n -> depo.olayYaz(kimlik, a, n) },
            )
            synchronized(kilit) {
                karar = k
                bekleyenYerel?.let { k.yerelG(it.first, it.second) }
                bekleyenYerel = null
            }
            val d = IzlemeDongusu(
                oturum = { baglandi ->
                    val zarf = depo.zarfOku(kimlik)
                    val kayit = try { kasa.anahtarOku(kimlik) } catch (e: Exception) { null }
                    if (zarf == null || kayit == null) IzlemeBitis("zarf")
                    else try {
                        val i = Izleyici({ TlsBaglanti.ac(it) }, k, kilit)
                        izleyici = i
                        if (dongu == null) i.durdur()
                        i.calis(kayit.anahtar, kimlik, kayit.n, zarf, baglandi = baglandi,
                            surdur = { synchronized(kilit) { k.kayitSuruyor() != false } })
                    } finally {
                        izleyici = null
                        kayit.anahtar.fill(0)
                    }
                },
                bekle = { ms -> synchronized(uyku) { try { uyku.wait(ms) } catch (_: InterruptedException) {} } },
                durum = { ad -> sonDurum = ad; gosterici.izlemeGuncelle(ad) },
            )
            dongu = d
            bitis = d.calis()
        } catch (e: Exception) {
            bitis = "ic-hata"
        }
        sonDurum = bitis
        if (bitis == "ayar") gosterici.ayarYenile()
        kapat()
    }

    private fun agiDinle() {
        val yonetici = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val g = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) = uyandir()
        }
        try { yonetici.registerDefaultNetworkCallback(g); agGeriBildirimi = g } catch (_: Exception) {}
    }

    private fun uyandir() = synchronized(uyku) { uyku.notifyAll() }

    private fun kapat() {
        dongu?.durdur(); dongu = null
        izleyici?.durdur()
        uyandir()
        try { ServiceCompat.stopForeground(this, ServiceCompat.STOP_FOREGROUND_REMOVE) } catch (_: Exception) {}
        stopSelf()
    }

    override fun onDestroy() {
        dongu?.durdur(); dongu = null
        izleyici?.durdur()
        uyandir()
        agGeriBildirimi?.let { g ->
            try { (getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager).unregisterNetworkCallback(g) } catch (_: Exception) {}
        }
        agGeriBildirimi = null
        karar = null
        calisanKimlik = null
        if (sonDurum !in BITIS_DURUMLARI) sonDurum = "durduruldu"
        super.onDestroy()
    }

    companion object {
        const val EYLEM_BASLAT = "tr.olcumkarti.mobil.IZLE"
        const val EYLEM_DURDUR = "tr.olcumkarti.mobil.IZLEME_DUR"
        const val EYLEM_YEREL = "tr.olcumkarti.mobil.IZLEME_YEREL"
        const val EK_KIMLIK = "kimlik"
        const val EK_DURUM = "durum"
        const val EK_OTURUM = "oturum"
        const val KASA_DIZINI = "kasa"
        private val BITIS_DURUMLARI = setOf("kayit-bitti", "ayar", "durduruldu", "ic-hata")

        /** Izlenen kartin kimligi; null = servis calismiyor. Ayni surecte eklenti okur. */
        @Volatile var calisanKimlik: String? = null
            private set
        /** Son durum adi: baglaniyor | izleniyor | internet | guven | araci | kayit-bitti | ayar | durduruldu | ic-hata. */
        @Volatile var sonDurum: String = "durduruldu"
            private set

        fun ayarDosyasi(ctx: Context): File = File(File(ctx.filesDir, "bildirim"), "ayar.json")

        fun baslat(ctx: Context, kimlik: String) {
            ContextCompat.startForegroundService(ctx, Intent(ctx, IzlemeServisi::class.java).setAction(EYLEM_BASLAT).putExtra(EK_KIMLIK, kimlik))
        }

        fun durdur(ctx: Context) {
            ctx.stopService(Intent(ctx, IzlemeServisi::class.java))
        }

        /** Servis calisiyorsa yerel kayit durumunu iletir; calismiyorsa hicbir sey yapmaz. */
        fun yerel(ctx: Context, kimlik: String, durum: Long, oturum: Long) {
            if (calisanKimlik != kimlik) return
            try {
                ctx.startService(Intent(ctx, IzlemeServisi::class.java).setAction(EYLEM_YEREL)
                    .putExtra(EK_KIMLIK, kimlik).putExtra(EK_DURUM, durum).putExtra(EK_OTURUM, oturum))
            } catch (_: Exception) {}
        }
    }
}
