package tr.olcumkarti.mobil.bildirim

import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.net.InetSocketAddress
import javax.net.ssl.HttpsURLConnection
import javax.net.ssl.SSLException
import javax.net.ssl.SSLSession
import javax.net.ssl.SSLSocket
import javax.net.ssl.SSLSocketFactory

/** Baglanti hatasi: `tur` sabit ad (adres-gecersiz, tls, ag). Adres / sertifika ayrintisi TASIMAZ (S3). */
class AraciHatasi(val tur: String) : Exception(tur)

/** Cozulmus araci adresi. toString adresi YAZMAZ. */
class AraciAdresi(val ad: String, val port: Int) {
    override fun toString(): String = "AraciAdresi(***)"

    companion object {
        private val AD = Regex("^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)(\\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$")
        private val BICIM = Regex("^mqtts://([^/:?#\\s]+)(?::([0-9]{1,5}))?/?$")

        /**
         * Yalniz `mqtts://ad[:port]` (TLS). Sifresiz `mqtt://`, `ws(s)://`, kullanici bilgisi, yol, sorgu,
         * IP adresi (sertifika adi dogrulanamaz), tek etiketli ad: AraciHatasi("adres-gecersiz").
         */
        fun coz(uri: String?): AraciAdresi {
            val m = if (uri == null) null else BICIM.matchEntire(uri.trim().lowercase())
            val ad = m?.groupValues?.get(1) ?: throw AraciHatasi("adres-gecersiz")
            if (!AD.matches(ad) || ad.all { it.isDigit() || it == '.' }) throw AraciHatasi("adres-gecersiz")
            val port = m.groupValues[2].let { if (it.isEmpty()) 8883 else it.toInt() }
            if (port < 1 || port > 65535) throw AraciHatasi("adres-gecersiz")
            return AraciAdresi(ad, port)
        }
    }
}

/**
 * Araciya TLS baglantisi (kullanici sarti S2): SERTIFIKA zinciri sistem guven deposuyla ve ANA BILGISAYAR
 * ADI sertifikayla dogrulanir — ikisi de ZORUNLU, kapatan secenek YOK.
 *  - ad dogrulamasi iki katman: el sikismada `endpointIdentificationAlgorithm = "HTTPS"`, ardindan
 *    platformun ad dogrulayicisi oturuma bir kez daha bakar (biri atlanirsa oteki tutar)
 *  - guven deposu varsayilan `SSLSocketFactory` (sistem CA'lari). `fabrika` yalniz TEST icindir (yerel
 *    araci icin gecici CA); uretimde verilmez. `adDogrula` da yalniz test icin degistirilir (JDK'nin
 *    varsayilan dogrulayicisi her adi reddeder; Android'inki sertifikaya bakar).
 */
class TlsBaglanti private constructor(private val soket: SSLSocket) : MqttBaglanti {
    override val giris: InputStream = soket.inputStream
    override val cikis: OutputStream = soket.outputStream
    override fun okumaSuresi(ms: Int) { soket.soTimeout = ms }
    override fun kapat() { try { soket.close() } catch (_: IOException) {} }

    companion object {
        const val BAGLANTI_MS = 10_000

        /** Ikinci katman: platformun ad dogrulayicisi (Android'de sertifikadaki adlara bakar). */
        val PLATFORM_AD_DOGRULAYICI: (String, SSLSession) -> Boolean =
            { ad, oturum -> HttpsURLConnection.getDefaultHostnameVerifier().verify(ad, oturum) }

        fun ac(
            adres: AraciAdresi,
            fabrika: SSLSocketFactory = SSLSocketFactory.getDefault() as SSLSocketFactory,
            adDogrula: (String, SSLSession) -> Boolean = PLATFORM_AD_DOGRULAYICI,
        ): TlsBaglanti {
            var soket: SSLSocket? = null
            try {
                val duz = java.net.Socket()
                duz.connect(InetSocketAddress(adres.ad, adres.port), BAGLANTI_MS)
                soket = fabrika.createSocket(duz, adres.ad, adres.port, true) as SSLSocket
                val p = soket.sslParameters
                p.endpointIdentificationAlgorithm = "HTTPS"
                soket.sslParameters = p
                soket.soTimeout = BAGLANTI_MS
                soket.startHandshake()
                if (!adDogrula(adres.ad, soket.session)) throw SSLException("ad")
                return TlsBaglanti(soket)
            } catch (e: SSLException) {
                try { soket?.close() } catch (_: IOException) {}
                throw AraciHatasi("tls")
            } catch (e: IOException) {
                try { soket?.close() } catch (_: IOException) {}
                throw AraciHatasi("ag")
            }
        }
    }
}
