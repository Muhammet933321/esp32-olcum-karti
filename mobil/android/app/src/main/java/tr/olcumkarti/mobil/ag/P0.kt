package tr.olcumkarti.mobil.ag

import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

/**
 * ACIL DURDURMA `p0` (tasarim A8–A11, Ö7). Kart `p0`'i HER ZAMAN kabul eder (imzasiz, basari 204).
 * Bu yol hicbir seyi BEKLEMEZ: imza, sayac yazimi, esitleme, kimlik dogrulamasi, baska isteklerin
 * kuyrugu. Verilen adreslerin HEPSINE ayni anda gonderilir; ilk basari yeter.
 * Yeniden deneme (P0-S, DEVIR 5.12.84): 503 ya da ag hatasinda 150 / 300 / 450 ms arayla, adres basina
 * en fazla 4 deneme. Saf Kotlin: gonderme ve bekleme enjekte, JVM'de sinanir.
 */
class P0(
    private val gonder: (adres: String) -> Int,           // HTTP kodu; ag hatasinda AgHatasi atar
    private val bekle: (ms: Long) -> Unit = { Thread.sleep(it) },
    private val calistir: (Runnable) -> Unit = { Thread(it, "p0").apply { isDaemon = true }.start() },
) {
    class Sonuc(val tamam: Boolean, val adres: String?, val deneme: Int)

    /** Tek adres: basari kodu gelene dek dener. Donus: kacinci denemede basardi (0 = basaramadi). */
    fun adresiDene(adres: String, vazgec: () -> Boolean = { false }): Int {
        for (deneme in 1..AZAMI_DENEME) {
            if (vazgec()) return 0
            val kod = try { gonder(adres) } catch (e: AgHatasi) { -1 } catch (e: RuntimeException) { -1 }
            if (kod in 200..299) return deneme
            // 503 (kart mesgul) ve ag hatasi yeniden denenir; baska kod (400, 403, 404) denenmez:
            // o adresteki sey kart degil ya da istegi anlamiyor.
            if (kod != 503 && kod != -1) return 0
            if (deneme < AZAMI_DENEME) bekle(ARALAR_MS[deneme - 1])
        }
        return 0
    }

    /** Butun adreslere AYNI ANDA; ilk basarida doner. Hepsi basarisizsa tamam = false. */
    fun durdur(adresler: List<String>, toplamSureMs: Long = TOPLAM_SURE_MS): Sonuc {
        val tekil = adresler.distinct().take(AZAMI_ADRES)
        if (tekil.isEmpty()) return Sonuc(false, null, 0)
        val kazanan = AtomicReference<Sonuc?>(null)
        val biten = CountDownLatch(tekil.size)
        val ilk = CountDownLatch(1)
        for (adres in tekil) {
            calistir(Runnable {
                try {
                    val d = adresiDene(adres) { kazanan.get() != null }
                    if (d > 0 && kazanan.compareAndSet(null, Sonuc(true, adres, d))) ilk.countDown()
                } finally {
                    biten.countDown()
                    if (biten.count == 0L) ilk.countDown()
                }
            })
        }
        ilk.await(toplamSureMs, TimeUnit.MILLISECONDS)
        return kazanan.get() ?: Sonuc(false, null, AZAMI_DENEME)
    }

    companion object {
        const val AZAMI_DENEME = 4
        val ARALAR_MS = longArrayOf(150, 300, 450)
        const val BAGLANTI_SURESI_MS = 800
        const val AZAMI_ADRES = 4
        /** En kotu hal: 4 deneme × 800 ms + 900 ms bekleme; ustune pay. */
        const val TOPLAM_SURE_MS = 4 * 800L + 900L + 300L
    }
}
