package tr.olcumkarti.mobil.ag

import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.SocketTimeoutException
import java.net.URL
import java.net.UnknownServiceException
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledFuture
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

/** Hata TURU; istisna mesaji (adres, ayrinti) kopruye ve gunluge GITMEZ (A45, S3). */
class AgHatasi(val tur: String) : Exception(tur)

class HttpYanit(val kod: Int, val basliklar: Map<String, String>, val govde: ByteArray)

/**
 * Tek HTTP istegi. Saf JVM: Android sinifi yok, birim testinde yerel sunucuya karsi kosar.
 * `baglantiAc` baglantiyi KURAR (Android'de Wi-Fi agina bagli, vekilsiz); adres kurali cagiranin isi.
 *
 * `zamanAsimiMs` istegin TOPLAM suresidir (baglanti + baslik + govde). Soket sureleri okuma basina
 * sifirlandigi icin bayt bayt damlatan bir sunucu onlari hic tetiklemez (curutucu 5A-7, H1/H2): toplam
 * sureyi bir bekci tutar ve dolunca baglantiyi keser.
 */
class HttpIstek(private val baglantiAc: (URL) -> HttpURLConnection) {

    fun yap(
        yontem: String,
        url: String,
        basliklar: Map<String, String>,
        govde: ByteArray?,
        zamanAsimiMs: Int,
        azamiGovde: Int = AZAMI_GOVDE,
    ): HttpYanit {
        if (yontem != "GET" && yontem != "POST") throw AgHatasi("bicim")
        val kesildi = AtomicBoolean(false)
        var b: HttpURLConnection? = null
        var bekci: ScheduledFuture<*>? = null
        try {
            b = baglantiAc(URL(url))
            val baglanti = b
            bekci = BEKCI.schedule({
                kesildi.set(true)
                try { baglanti.disconnect() } catch (_: Exception) {}
            }, zamanAsimiMs.toLong(), TimeUnit.MILLISECONDS)
            b.requestMethod = yontem
            b.connectTimeout = zamanAsimiMs
            b.readTimeout = zamanAsimiMs
            b.instanceFollowRedirects = false
            b.useCaches = false
            b.setRequestProperty("User-Agent", KULLANICI_ARACI)   // model / surum sizmasin
            for ((ad, deger) in basliklar) {
                if (ad.equals("Host", ignoreCase = true) || ad.equals("User-Agent", ignoreCase = true)) continue
                b.setRequestProperty(ad, deger)
            }
            if (yontem == "POST") {
                val g = govde ?: ByteArray(0)
                b.doOutput = true
                b.setFixedLengthStreamingMode(g.size)
                b.outputStream.use { it.write(g) }
            }
            val kod = b.responseCode
            val akis: InputStream? = if (kod >= 400) b.errorStream else b.inputStream
            val veri = akis?.use { oku(it, azamiGovde, kesildi) } ?: ByteArray(0)
            if (kesildi.get()) throw AgHatasi("zaman-asimi")
            val bas = HashMap<String, String>()
            for ((ad, degerler) in b.headerFields) {
                if (ad != null && degerler.isNotEmpty()) bas[ad.lowercase()] = degerler[0]
            }
            return HttpYanit(kod, bas, veri)
        } catch (e: AgHatasi) {
            throw e
        } catch (e: SocketTimeoutException) {
            throw AgHatasi("zaman-asimi")
        } catch (e: UnknownServiceException) {
            throw AgHatasi("cleartext")     // sifresiz HTTP ag guvenligi ayariyla engellendi
        } catch (e: IOException) {
            throw AgHatasi(if (kesildi.get()) "zaman-asimi" else "baglanti")
        } catch (e: RuntimeException) {
            throw AgHatasi(if (kesildi.get()) "zaman-asimi" else "baglanti")
        } finally {
            bekci?.cancel(false)
            b?.disconnect()
        }
    }

    private fun oku(akis: InputStream, azami: Int, kesildi: AtomicBoolean): ByteArray {
        val cikti = ByteArrayOutputStream()
        val tampon = ByteArray(8192)
        while (true) {
            val n = akis.read(tampon)
            if (n < 0) break
            cikti.write(tampon, 0, n)
            if (cikti.size() > azami) throw AgHatasi("govde-buyuk")
            if (kesildi.get()) throw AgHatasi("zaman-asimi")
        }
        return cikti.toByteArray()
    }

    companion object {
        const val AZAMI_GOVDE = 64 * 1024
        const val AZAMI_GOVDE_SINIR = 1024 * 1024
        const val KULLANICI_ARACI = "olcum-mobil"
        private val BEKCI = Executors.newSingleThreadScheduledExecutor { r ->
            Thread(r, "http-bekci").apply { isDaemon = true }
        }
    }
}
