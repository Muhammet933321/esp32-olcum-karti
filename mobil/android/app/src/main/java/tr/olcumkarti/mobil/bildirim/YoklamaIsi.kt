package tr.olcumkarti.mobil.bildirim

import android.content.Context
import android.content.pm.PackageManager
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequest
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import tr.olcumkarti.mobil.kasa.KasaDeposu
import tr.olcumkarti.mobil.kasa.KeystoreSarici
import java.io.File
import java.util.concurrent.TimeUnit

/**
 * 15 DAKIKALIK YOKLAMA (tasarim A29 c, A30): araciya baglanir, kalici durum mesajini okur, kapanir (en cok
 * ~20 s). Anlik izleme KAPALIYKEN bildirimlerin tek yolu; aciksa kaydin PC'den baslatildigini fark edip
 * servisi baslatir — Android arka plandan servis baslatmayi engellerse "Kayit suruyor — izlemek icin dokun".
 * Ince kabuk: karar `Yoklama.degerlendir`de (JVM'de sinanir), protokol `Izleyici`de (tek seferlik kip).
 * Servisin izledigi kart atlanir (obur kartlar yoklanir). Zarfi olan kart kalmadiysa kendini iptal eder.
 * Gunluk yok (A45); hata disari cikmaz (is her zaman "basarili": sonraki 15 dakikada yeniden denenir).
 */
class YoklamaIsi(ctx: Context, parametreler: WorkerParameters) : Worker(ctx, parametreler) {
    override fun doWork(): Result {
        try {
            val uyg = applicationContext
            val kasaDizini = File(uyg.filesDir, IzlemeServisi.KASA_DIZINI)
            val depo = BildirimDeposu(kasaDizini)
            val kimlikler = depo.kimlikler()
            if (kimlikler.isEmpty()) { iptal(uyg); return Result.success() }
            val ayar = BildirimAyar.oku(IzlemeServisi.ayarDosyasi(uyg))
            val gosterici = BildirimGosterici(uyg, ayar.dil)
            gosterici.kanallariKur()
            val kasa = KasaDeposu(kasaDizini, KeystoreSarici(uyg.packageManager.hasSystemFeature(PackageManager.FEATURE_STRONGBOX_KEYSTORE)))
            for (kimlik in kimlikler) {
                if (isStopped) break
                if (IzlemeServisi.calisanKimlik == kimlik) continue          // bu karti servis izliyor; OBUR kartlar yoklanir
                val zarf = depo.zarfOku(kimlik) ?: continue
                val kayit = try { kasa.anahtarOku(kimlik) } catch (e: Exception) { null }
                if (kayit == null) { gosterici.ayarYenile(); continue }
                var okunan: Map<String, Any?>? = null
                val bitis = try {
                    // Bu oturumun karar nesnesi SESSIZ: bildirim karari asagida, onceki yoklamayla karsilastirilarak verilir.
                    Izleyici({ TlsBaglanti.ac(it) }, BildirimKarar({}, { 0.0 }), Any())
                        .calis(kayit.anahtar, kimlik, kayit.n, zarf, tekSefer = true, durumGoruldu = { okunan = it })
                } finally {
                    kayit.anahtar.fill(0)
                }
                if (bitis.sinif == "ayar") { gosterici.ayarYenile(); continue }
                val s = Yoklama.degerlendir(depo.durumOku(kimlik), okunan, { ayar.acik(it) }) { gosterici.goster(it) }
                depo.durumYaz(kimlik, s.durum)
                if (s.kayitSuruyor && ayar.anlik) {
                    try { IzlemeServisi.baslat(uyg, kimlik) } catch (e: Exception) { gosterici.izlemeDokun() }      // A29 c
                }
            }
        } catch (_: Exception) {
        }
        return Result.success()
    }

    companion object {
        const val AD = "yoklama"
        const val ARALIK_DK = 15L

        /** Zarf yazildiginda ve uygulama acilirken: is yoksa kurar, varsa DOKUNMAZ (sayaci sifirlanmaz). */
        fun kur(ctx: Context) {
            try {
                val istek = PeriodicWorkRequest.Builder(YoklamaIsi::class.java, ARALIK_DK, TimeUnit.MINUTES)
                    .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                    .build()
                WorkManager.getInstance(ctx.applicationContext).enqueueUniquePeriodicWork(AD, ExistingPeriodicWorkPolicy.KEEP, istek)
            } catch (_: Exception) {
            }
        }

        fun iptal(ctx: Context) {
            try { WorkManager.getInstance(ctx.applicationContext).cancelUniqueWork(AD) } catch (_: Exception) {}
        }
    }
}
