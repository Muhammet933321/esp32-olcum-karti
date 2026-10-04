package tr.olcumkarti.mobil.ag

import java.io.IOException
import java.net.HttpURLConnection
import java.net.SocketTimeoutException
import java.net.UnknownServiceException
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Kartin canli akisi (SSE, `/akis`): baglan-oku dongusu. Saf JVM: Android sinifi yok, birim testinde
 * yerel soket sunucusuna karsi kosar. `baglantiAc` adresi dogrular ve baglantiyi KURAR (Android'de:
 * hedef kurali + Wi-Fi agina bagli + vekilsiz); `AgHatasi` atarsa turu aynen bildirilir.
 *
 * Dinleyiciye gidenler:
 *  - `durum("acik")`: ilk `dolu` OLMAYAN olayda, en cok bir kez (dolu kart "acik" gorunmez)
 *  - `satirlar(...)`: yalniz varsayilan olayin verisi. `kimlik` olayi (oturum jetonu tasir), `id:`,
 *    `retry:`, yorum TASINMAZ (A7)
 *  - TEK bitis: `durum("kapandi")` (baglanti bitti / kapat()), `durum("dolu")`, ya da
 *    `durum("hata", tur, kod)` — tur: bicim | baglanti | zaman-asimi | cleartext | http (+kod) | AgHatasi turu
 * Adres (imza tasir) ve istisna metni dinleyiciye GITMEZ (A45).
 */
class Akis(
    private val baglantiAc: (String) -> HttpURLConnection,
    private val dinleyici: Dinleyici,
    private val okumaZamanAsimiMs: Int = OKUMA_ZAMAN_ASIMI_MS,
    private val baglantiZamanAsimiMs: Int = BAGLANTI_ZAMAN_ASIMI_MS,
) {
    interface Dinleyici {
        fun satirlar(satirlar: List<String>)
        fun durum(hal: String, tur: String?, kod: Int)
    }

    @Volatile private var kapatildi = false
    @Volatile private var baglanti: HttpURLConnection? = null
    private val bitti = AtomicBoolean(false)

    private fun bitir(hal: String, tur: String? = null, kod: Int = 0) {
        if (bitti.compareAndSet(false, true)) dinleyici.durum(hal, tur, kod)
    }

    /** Baglantiyi HEMEN keser (okuma bloklu olsa da) ve bitisi bildirir. Her is parcacigindan cagrilabilir. */
    fun kapat() {
        kapatildi = true
        try { baglanti?.disconnect() } catch (_: Exception) {}
        bitir("kapandi")
    }

    /** Bloklar: akis bitene, kopana ya da kapat() cagrilana kadar. Kendi is parcaciginda cagrilir. */
    fun calis(url: String) {
        if (kapatildi) { bitir("kapandi"); return }
        if (!ADRES.matches(url)) { bitir("hata", "bicim"); return }
        var b: HttpURLConnection? = null
        try {
            b = baglantiAc(url)
            baglanti = b
            if (kapatildi) { bitir("kapandi"); return }
            b.requestMethod = "GET"
            b.connectTimeout = baglantiZamanAsimiMs
            b.readTimeout = okumaZamanAsimiMs
            b.instanceFollowRedirects = false
            b.useCaches = false
            b.setRequestProperty("User-Agent", HttpIstek.KULLANICI_ARACI)
            b.setRequestProperty("Accept", "text/event-stream")
            b.setRequestProperty("Accept-Encoding", "identity")
            b.setRequestProperty("X-Olcum", "1")
            val kod = b.responseCode
            if (kod != 200) { bitir("hata", "http", kod); return }
            oku(b)
        } catch (e: AgHatasi) {
            bitir("hata", e.tur)
        } catch (e: SocketTimeoutException) {
            bitir("hata", "zaman-asimi")
        } catch (e: UnknownServiceException) {
            bitir("hata", "cleartext")
        } catch (e: IOException) {
            bitir("hata", "baglanti")
        } catch (e: RuntimeException) {
            bitir("hata", "baglanti")
        } finally {
            try { b?.disconnect() } catch (_: Exception) {}
        }
    }

    private fun oku(b: HttpURLConnection) {
        val ayirici = SseAyirici()
        val tampon = ByteArray(4096)
        var acik = false
        b.inputStream.use { giris ->
            while (true) {
                val n = giris.read(tampon)
                if (n < 0 || kapatildi) break
                val satirlar = ArrayList<String>()
                for (o in ayirici.besle(tampon, 0, n)) {
                    if (o.ad == "dolu") { bitir("dolu"); return }
                    if (!acik) {
                        acik = true
                        if (!bitti.get()) dinleyici.durum("acik", null, 0)
                    }
                    if (o.ad.isEmpty() || o.ad == "message") satirlar.add(o.veri)
                }
                if (satirlar.isNotEmpty() && !bitti.get()) dinleyici.satirlar(satirlar)
            }
        }
        bitir("kapandi")
    }

    companion object {
        const val OKUMA_ZAMAN_ASIMI_MS = 40000        // kart 15 s'de bir `: kalp` yollar
        const val BAGLANTI_ZAMAN_ASIMI_MS = 10000
        private val ADRES = Regex("^http://[^/?#\\s]+/akis(\\?[\\x21-\\x7e]*)?$")
    }
}
