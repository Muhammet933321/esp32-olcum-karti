package tr.olcumkarti.mobil.ag

import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.SocketTimeoutException
import java.net.URL
import java.net.UnknownServiceException

/** Hata TURU; istisna mesaji (adres, ayrinti) kopruye ve gunluge GITMEZ (A45, S3). */
class AgHatasi(val tur: String) : Exception(tur)

class HttpYanit(val kod: Int, val basliklar: Map<String, String>, val govde: ByteArray)

/**
 * Tek HTTP istegi. Saf JVM: Android sinifi yok, birim testinde yerel sunucuya karsi kosar.
 * `baglantiAc` baglantiyi KURAR (Android'de Wi-Fi agina bagli, vekilsiz); adres kurali cagiranin isi.
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
        val bitis = System.nanoTime() + zamanAsimiMs * 1_000_000L
        var b: HttpURLConnection? = null
        try {
            b = baglantiAc(URL(url))
            b.requestMethod = yontem
            b.connectTimeout = zamanAsimiMs
            b.readTimeout = zamanAsimiMs
            b.instanceFollowRedirects = false
            b.useCaches = false
            for ((ad, deger) in basliklar) {
                if (ad.equals("Host", ignoreCase = true)) continue   // Host = baglanilan adres (A3)
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
            val veri = akis?.use { oku(it, azamiGovde, bitis) } ?: ByteArray(0)
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
            throw AgHatasi("baglanti")
        } catch (e: RuntimeException) {
            throw AgHatasi("baglanti")
        } finally {
            b?.disconnect()
        }
    }

    private fun oku(akis: InputStream, azami: Int, bitis: Long): ByteArray {
        val cikti = ByteArrayOutputStream()
        val tampon = ByteArray(8192)
        while (true) {
            val n = akis.read(tampon)
            if (n < 0) break
            cikti.write(tampon, 0, n)
            if (cikti.size() > azami) throw AgHatasi("govde-buyuk")
            // Damla damla gelen yanit readTimeout'u hic tetiklemez: toplam sure de sinirli.
            if (System.nanoTime() > bitis) throw AgHatasi("zaman-asimi")
        }
        return cikti.toByteArray()
    }

    companion object {
        const val AZAMI_GOVDE = 64 * 1024
        const val AZAMI_GOVDE_SINIR = 1024 * 1024
    }
}
