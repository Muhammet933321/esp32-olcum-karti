package tr.olcumkarti.mobil.ag

import java.util.Collections
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

/**
 * ACIL DURDURMA `p0` (tasarim A8–A11, Ö7). Kart `p0`'i HER ZAMAN kabul eder (imzasiz, basari 204).
 * Bu yol hicbir seyi BEKLEMEZ: imza, sayac yazimi, esitleme, kimlik dogrulamasi, baska isteklerin
 * kuyrugu. Verilen adreslerin HEPSINE ayni anda gonderilir.
 *  - Basari YALNIZ 204'tur (kartin `p0` yaniti). Baska 2xx basari DEGILDIR ve yeniden denenmez: o
 *    adresteki sey kart degil (yonlendirici, baska bir cihaz).
 *  - Bir adresin basarisi oteki adreslerin denemesini KESMEZ (kart degil de baska bir cihaz once
 *    yanit verdiyse gercek kartin yeniden denemesi surer).
 *  - Listedeki ILK adres "asil"dir (bu baglantida kimligi dogrulanmis kart): o 204 verince HEMEN
 *    donulur. Asil basarisizsa butun denemeler bitince / toplam sure dolunca donulur.
 * Yeniden deneme (P0-S, DEVIR 5.12.84): 503 ya da GECICI ag hatasinda 150 / 300 / 450 ms arayla, adres
 * basina en fazla 4 deneme. KALICI hata (Wi-Fi yok, adres kurala uymuyor …) yeniden DENENMEZ.
 * Saf Kotlin: gonderme ve bekleme enjekte, JVM'de sinanir.
 */
class P0(
    private val gonder: (adres: String) -> Int,           // HTTP kodu; ag hatasinda AgHatasi atar
    private val bekle: (ms: Long) -> Unit = { Thread.sleep(it) },
    private val calistir: (Runnable) -> Unit = { Thread(it, "p0").apply { isDaemon = true }.start() },
) {
    /** `tamam` = en az bir adres 204 verdi; `adres` = asil adres basariliysa o, degilse ilk basarili. */
    class Sonuc(val tamam: Boolean, val adres: String?, val deneme: Int, val basarili: List<String> = emptyList())

    /** Tek adres: 204 gelene dek dener. Donus: kacinci denemede basardi (0 = basaramadi). */
    fun adresiDene(adres: String): Int {
        for (deneme in 1..AZAMI_DENEME) {
            val kod = try {
                gonder(adres)
            } catch (e: AgHatasi) {
                if (e.tur in KALICI_HATALAR) return 0     // yeniden denemek ayni sonucu verir: hemen vazgec
                -1
            } catch (e: RuntimeException) {
                -1
            }
            if (kod == BASARI_KODU) return deneme
            // 503 (kart mesgul) ve gecici ag hatasi yeniden denenir; baska kod (200, 400, 403, 404)
            // denenmez: o adresteki sey kart degil ya da istegi anlamiyor.
            if (kod != 503 && kod != -1) return 0
            if (deneme < AZAMI_DENEME) bekle(ARALAR_MS[deneme - 1])
        }
        return 0
    }

    /** Butun adreslere AYNI ANDA. Asil (ilk) adres 204 verince hemen; yoksa hepsi bitince / sure dolunca. */
    fun durdur(adresler: List<String>, toplamSureMs: Long = TOPLAM_SURE_MS): Sonuc {
        val tekil = adresler.distinct().take(AZAMI_ADRES)
        if (tekil.isEmpty()) return Sonuc(false, null, 0)
        val asil = tekil[0]
        val basarili = Collections.synchronizedList(ArrayList<String>())
        val ilkDeneme = AtomicInteger(0)
        val kalan = AtomicInteger(tekil.size)
        val bitti = CountDownLatch(1)
        for (adres in tekil) {
            calistir(Runnable {
                try {
                    val d = adresiDene(adres)
                    if (d > 0) {
                        basarili.add(adres)
                        ilkDeneme.compareAndSet(0, d)
                        if (adres == asil) bitti.countDown()
                    }
                } finally {
                    if (kalan.decrementAndGet() == 0) bitti.countDown()
                }
            })
        }
        bitti.await(toplamSureMs, TimeUnit.MILLISECONDS)
        val liste = synchronized(basarili) { ArrayList(basarili) }
        if (liste.isEmpty()) return Sonuc(false, null, AZAMI_DENEME)
        return Sonuc(true, if (liste.contains(asil)) asil else liste[0], ilkDeneme.get(), liste)
    }

    companion object {
        const val BASARI_KODU = 204
        const val AZAMI_DENEME = 4
        val ARALAR_MS = longArrayOf(150, 300, 450)
        const val BAGLANTI_SURESI_MS = 800
        const val AZAMI_ADRES = 4
        /** En kotu hal: 4 deneme × 800 ms + 900 ms bekleme; ustune pay. */
        const val TOPLAM_SURE_MS = 4 * 800L + 900L + 300L
        /** Yeniden denemenin sonucu degistirmeyecegi hata turleri (AgHatasi.tur). */
        val KALICI_HATALAR = setOf("wifi-yok", "ozel-degil", "bicim", "ad-izinsiz", "cleartext")
    }
}

/**
 * Art arda dokunuslari TEK tura baglar: suren bir tur varken AYNI adres listesiyle gelen cagri yeni
 * is parcaciklari ACMAZ, o turun sonucunu alir (20 hizli dokunus 20 × 4 baglanti acmaz). Cagri hicbir
 * zaman bekletilmez / reddedilmez: tur bittiyse (ya da liste farkliysa) HEMEN yeni tur baslar.
 */
class P0Tur(
    private val p0: P0,
    private val calistir: (Runnable) -> Unit = { Thread(it, "p0-ana").apply { isDaemon = true }.start() },
) {
    private val kilit = Any()
    private var surenAdresler: List<String>? = null
    private var bekleyenler: ArrayList<(P0.Sonuc) -> Unit>? = null

    fun durdur(adresler: List<String>, bitince: (P0.Sonuc) -> Unit) {
        val benim = arrayListOf(bitince)
        var izlenen = false
        synchronized(kilit) {
            val b = bekleyenler
            if (b != null && surenAdresler == adresler) {
                b.add(bitince)                            // suren tura baglan
                return
            }
            if (b == null) {
                surenAdresler = adresler
                bekleyenler = benim
                izlenen = true
            }
            // Suren tur BASKA adreslere gidiyorsa: bu cagri kendi (izlenmeyen) turunu kosar.
        }
        calistir(Runnable {
            val s = try { p0.durdur(adresler) } catch (e: RuntimeException) { P0.Sonuc(false, null, 0) }
            val hedefler = synchronized(kilit) {
                if (izlenen) {
                    bekleyenler = null
                    surenAdresler = null
                }
                ArrayList(benim)
            }
            for (f in hedefler) f(s)
        })
    }
}
