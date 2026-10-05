package tr.olcumkarti.mobil.bildirim

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.PowerManager
import android.provider.Settings
import com.getcapacitor.JSArray
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import com.getcapacitor.annotation.Permission
import com.getcapacitor.annotation.PermissionCallback
import tr.olcumkarti.mobil.kasa.KasaDeposu
import tr.olcumkarti.mobil.kasa.KasaKayit
import tr.olcumkarti.mobil.kasa.KeystoreSarici
import java.io.File
import java.util.Base64
import java.util.concurrent.Executors

/**
 * Bildirimlerin WebView koprusu (tasarim A31, A37, A38, A42). Ince kabuk.
 *  - `zarfYaz`: WebView'in imzali `/bildirim/bilgi` ile aldigi zarf OLDUGU GIBI saklanir. Yazmadan once K ile
 *    acilip denetlenir (acilmiyorsa yazilmaz); cozulmus icerik atilir — kopruye de diske de GITMEZ.
 *  - `durum`: izin, pil muafiyeti, zarf var mi, servis ne yapiyor, ayar. Araci bilgisi DONMEZ.
 *  - izinler aciklamasi WebView'de gosterildikten SONRA istenir (A37): bu sinif kendiliginden istemez.
 * Hata TUR adiyla doner; istisna mesaji kopruye gitmez. Gunluk yok (A45).
 */
@CapacitorPlugin(name = "Bildirim", permissions = [Permission(strings = [Manifest.permission.POST_NOTIFICATIONS], alias = "bildirim")])
class BildirimPlugin : Plugin() {
    private val sira = Executors.newSingleThreadExecutor { r -> Thread(r, "bildirim-eklenti") }
    private val kasaDizini: File by lazy { File(context.filesDir, IzlemeServisi.KASA_DIZINI) }
    private val depo: BildirimDeposu by lazy { BildirimDeposu(kasaDizini) }

    /** Uygulama acilirken: zarfi olan kart varsa 15 dakikalik yoklama kurulu olsun (A30). */
    override fun load() {
        try { sira.execute { try { if (depo.kimlikler().isNotEmpty()) YoklamaIsi.kur(context) } catch (_: Exception) {} } } catch (_: Exception) {}
    }

    private fun kos(call: PluginCall, islem: () -> JSObject) {
        try {
            sira.execute {
                try {
                    call.resolve(islem())
                } catch (e: ZarfHatasi) {
                    call.reject(e.tur, e.tur)
                } catch (e: Throwable) {
                    call.reject("ic-hata", "ic-hata")
                }
            }
        } catch (e: Exception) {
            call.reject("ic-hata", "ic-hata")
        }
    }

    private fun kimlik(call: PluginCall): String {
        val k = call.getString("kimlik")
        if (!KasaKayit.kimlikGecerli(k)) throw ZarfHatasi("bicim")
        return k!!
    }

    private fun ayar(): BildirimAyar = BildirimAyar.oku(IzlemeServisi.ayarDosyasi(context))

    private fun izinVar(): Boolean = BildirimGosterici(context, "tr").izinVar()

    private fun pilMuaf(): Boolean =
        (context.getSystemService(Context.POWER_SERVICE) as PowerManager).isIgnoringBatteryOptimizations(context.packageName)

    @PluginMethod
    fun zarfYaz(call: PluginCall) = kos(call) {
        val kimlik = kimlik(call)
        val zarf = try { Base64.getDecoder().decode(call.getString("zarf") ?: throw ZarfHatasi("bicim")) } catch (e: IllegalArgumentException) { throw ZarfHatasi("bicim") }
        val kasa = KasaDeposu(kasaDizini, KeystoreSarici(context.packageManager.hasSystemFeature(PackageManager.FEATURE_STRONGBOX_KEYSTORE)))
        val kayit = try { kasa.anahtarOku(kimlik) } catch (e: Exception) { throw ZarfHatasi("anahtar-yok") }
        try {
            val bilgi = Zarf.bilgiCoz(kayit.anahtar, kimlik, kayit.n, zarf)          // acilmiyorsa ZarfHatasi (etiket / icerik)
            bilgi.anahtar.fill(0)
            try { AraciAdresi.coz(bilgi.uri) } catch (e: AraciHatasi) { throw ZarfHatasi("adres") }
        } finally {
            kayit.anahtar.fill(0)
        }
        depo.zarfYaz(kimlik, zarf)
        YoklamaIsi.kur(context)
        BildirimGosterici(context, ayar().dil).ayarYenileKaldir()
        JSObject().put("yazildi", true)
    }

    /** WebView'in dogruladigi kartin yerel adresi (A36: servis bu adresi imzasiz yoklar). */
    @PluginMethod
    fun adresYaz(call: PluginCall) = kos(call) {
        depo.adresYaz(kimlik(call), call.getString("adres"))
        JSObject().put("yazildi", true)
    }

    @PluginMethod
    fun zarfSil(call: PluginCall) = kos(call) {
        depo.zarfSil(kimlik(call))
        if (depo.kimlikler().isEmpty()) YoklamaIsi.iptal(context)
        JSObject().put("silindi", true)
    }

    @PluginMethod
    fun durum(call: PluginCall) = kos(call) {
        val k = call.getString("kimlik")
        val a = ayar()
        JSObject()
            .put("zarf", KasaKayit.kimlikGecerli(k) && depo.zarfVar(k))
            .put("izin", izinVar())
            .put("izinGerekli", Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU)
            .put("pilMuaf", pilMuaf())
            .put("calisiyor", IzlemeServisi.calisanKimlik != null)
            .put("izleme", IzlemeServisi.sonDurum)
            .put("anlik", a.anlik)
            .put("kapali", JSArray(BildirimAyar.SINIFLAR.filter { !a.acik(it) }))
            .put("dil", a.dil)
            .put("uretici", Uretici.sinifi(Build.MANUFACTURER, Build.BRAND))
    }

    @PluginMethod
    fun ayarYaz(call: PluginCall) = kos(call) {
        val eski = ayar()
        val anlik = call.getBoolean("anlik") ?: eski.anlik
        val dil = call.getString("dil")?.takeIf { it in BildirimAyar.DILLER } ?: eski.dil
        val kapali = call.getArray("kapali")?.toList<Any?>()?.filterIsInstance<String>()?.filter { it in BildirimAyar.SINIFLAR }?.toSet() ?: eski.kapali
        val yeni = BildirimAyar(anlik, kapali, dil)
        BildirimAyar.yaz(IzlemeServisi.ayarDosyasi(context), yeni)
        // Yalniz anlik izleme ACIKTAN KAPALIYA cekilince durdurulur: dil / sinif yazimi "bu kayit icin" baslatilmis
        // izlemeyi kesmez.
        if (eski.anlik && !yeni.anlik && IzlemeServisi.calisanKimlik != null) IzlemeServisi.durdur(context)
        JSObject().put("anlik", yeni.anlik)
    }

    /** Bildirim izni (Android 13+). Aciklama WebView'de gosterildikten SONRA cagrilir. */
    @PluginMethod
    fun izinIste(call: PluginCall) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU || izinVar()) { call.resolve(JSObject().put("izin", izinVar())); return }
        requestPermissionForAlias("bildirim", call, "izinSonucu")
    }

    @PermissionCallback
    private fun izinSonucu(call: PluginCall) {
        call.resolve(JSObject().put("izin", izinVar()))
    }

    /** Pil optimizasyonu muafiyeti: SISTEMIN kendi onay penceresi acilir; karar kullanicinin (A37). */
    @PluginMethod
    fun pilMuafiyetiIste(call: PluginCall) {
        try {
            if (!pilMuaf()) {
                activity.startActivity(Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, Uri.parse("package:" + context.packageName)))
            }
            call.resolve(JSObject().put("pilMuaf", pilMuaf()))
        } catch (e: Exception) {
            call.reject("ic-hata", "ic-hata")
        }
    }

    /**
     * Bu uygulamanin SISTEM ayar sayfasini acar (A37: pil yoneticisi / otomatik baslatma yonergesinin ilk adimi).
     * Hicbir ayari DEGISTIRMEZ; degisikligi kullanici yapar.
     */
    @PluginMethod
    fun uygulamaAyarlariAc(call: PluginCall) {
        try {
            activity.startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:" + context.packageName)))
            call.resolve(JSObject().put("acildi", true))
        } catch (e: Exception) {
            call.reject("ic-hata", "ic-hata")
        }
    }

    /**
     * Anlik izlemeyi baslatir (A29 a, b): ayar acik ve zarf varsa. `buKayit`: ayar KAPALI olsa da yalniz bu kayit
     * icin (kullanici kayit baslatirken soruya "ac" dedi). Neden baslamadigi `neden`de.
     */
    @PluginMethod
    fun izlemeBaslat(call: PluginCall) = kos(call) {
        val kimlik = kimlik(call)
        val neden = when {
            !ayar().anlik && call.getBoolean("buKayit") != true -> "kapali"
            !depo.zarfVar(kimlik) -> "zarf-yok"
            IzlemeServisi.calisanKimlik == kimlik -> "calisiyor"
            else -> null
        }
        if (neden == null) IzlemeServisi.baslat(context, kimlik)
        JSObject().put("basladi", neden == null).put("neden", neden ?: "")
    }

    @PluginMethod
    fun izlemeDurdur(call: PluginCall) = kos(call) {
        IzlemeServisi.durdur(context)
        JSObject().put("durdu", true)
    }

    /** Uygulama ondeyken yerel akistan duyulan kayit durumu (A35). Servis calismiyorsa hicbir sey yapmaz. */
    @PluginMethod
    fun yerel(call: PluginCall) = kos(call) {
        val kimlik = kimlik(call)
        val durum = (call.data.opt("durum") as? Number)?.toLong() ?: throw ZarfHatasi("bicim")
        val oturum = (call.data.opt("oturum") as? Number)?.toLong() ?: throw ZarfHatasi("bicim")
        if (durum < 0 || oturum < 0) throw ZarfHatasi("bicim")
        IzlemeServisi.yerel(context, kimlik, durum, oturum)
        JSObject().put("iletildi", IzlemeServisi.calisanKimlik == kimlik)
    }

    /** Deneme bildirimi: kanal, ses ve izin calisiyor mu — karta ve araciya GITMEDEN (yalniz bu telefonda). */
    @PluginMethod
    fun deneme(call: PluginCall) = kos(call) {
        val g = BildirimGosterici(context, ayar().dil)
        g.kanallariKur()
        g.goster(Bildirim("deneme-yerel", "deneme", "izleme.deneme_yerel", emptyMap(), false))
        JSObject().put("izin", g.izinVar())
    }

    override fun handleOnDestroy() {
        sira.shutdown()
    }
}
