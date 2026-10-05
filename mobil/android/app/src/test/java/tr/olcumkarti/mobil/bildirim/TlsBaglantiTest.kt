package tr.olcumkarti.mobil.bildirim

import org.junit.AfterClass
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.BeforeClass
import org.junit.Test
import java.io.File
import java.net.ServerSocket
import java.nio.file.Files
import java.security.KeyStore
import javax.net.ssl.KeyManagerFactory
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLServerSocket
import javax.net.ssl.SSLSocketFactory
import javax.net.ssl.TrustManagerFactory

/**
 * 5E-2 / kullanici sarti S2: araciya TLS'te SERTIFIKA ve ANA BILGISAYAR ADI dogrulamasi ZORUNLU.
 * Gercek TLS el sikismasi, 127.0.0.1'deki yerel sunucuyla; sertifikalar test basinda JDK'nin `keytool`'uyla
 * gecici dizinde uretilir (depoya girmez, test bitince silinir). Aga cikilmaz.
 */
class TlsBaglantiTest {
    companion object {
        private lateinit var dizin: File
        private const val GECIT = "sinama-gecidi"
        private lateinit var dogruAd: File      // SAN: localhost
        private lateinit var yanlisAd: File     // SAN: baska.ornek.invalid

        private fun uret(dosya: File, san: String) {
            val keytool = File(System.getProperty("java.home"), "bin/keytool" + if (System.getProperty("os.name").startsWith("Windows")) ".exe" else "")
            val p = ProcessBuilder(
                keytool.path, "-genkeypair", "-alias", "a", "-keyalg", "RSA", "-keysize", "2048", "-validity", "2",
                "-dname", "CN=sinama", "-ext", "san=dns:$san", "-storetype", "PKCS12",
                "-keystore", dosya.path, "-storepass", GECIT, "-keypass", GECIT,
            ).redirectErrorStream(true).start()
            p.inputStream.readBytes()
            check(p.waitFor() == 0) { "keytool calismadi" }
        }

        @BeforeClass @JvmStatic
        fun kur() {
            dizin = Files.createTempDirectory("tls-sinama").toFile()
            dogruAd = File(dizin, "dogru.p12").also { uret(it, "localhost") }
            yanlisAd = File(dizin, "yanlis.p12").also { uret(it, "baska.ornek.invalid") }
        }

        @AfterClass @JvmStatic
        fun temizle() { dizin.deleteRecursively() }

        private fun depo(f: File): KeyStore = KeyStore.getInstance("PKCS12").apply { f.inputStream().use { load(it, GECIT.toCharArray()) } }

        /** Sunucu: verilen sertifikayla dinler; baglananla el sikisir, "merhaba" yazar, bir bayt okur. */
        private fun sunucu(sertifika: File): SSLServerSocket {
            val km = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm()).apply { init(depo(sertifika), GECIT.toCharArray()) }
            val ctx = SSLContext.getInstance("TLS").apply { init(km.keyManagers, null, null) }
            val s = ctx.serverSocketFactory.createServerSocket(0, 5, java.net.InetAddress.getByName("127.0.0.1")) as SSLServerSocket
            Thread {
                try {
                    while (true) {
                        val c = s.accept()
                        Thread {
                            try { c.getOutputStream().write("merhaba".toByteArray()); c.getOutputStream().flush(); c.getInputStream().read() } catch (_: Exception) {} finally { try { c.close() } catch (_: Exception) {} }
                        }.apply { isDaemon = true }.start()
                    }
                } catch (_: Exception) {}
            }.apply { isDaemon = true }.start()
            return s
        }

        /** YALNIZ verilen sertifikaya guvenen fabrika (test CA'si). */
        private fun guvenen(sertifika: File): SSLSocketFactory {
            val tm = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm()).apply { init(depo(sertifika)) }
            return SSLContext.getInstance("TLS").apply { init(null, tm.trustManagers, null) }.socketFactory
        }
    }

    private fun tur(islem: () -> Any?): String? = try { islem(); null } catch (e: AraciHatasi) { e.tur }
    private val HER_AD: (String, javax.net.ssl.SSLSession) -> Boolean = { _, _ -> true }

    @Test
    fun guvenilmeyenSertifika_sistemGuvenDeposuyla_REDDEDILIR() {
        val s = sunucu(dogruAd)
        try {
            // Varsayilan fabrika (sistem CA'lari): kendinden imzali sertifika, adi DOGRU olsa da kabul edilmez.
            assertEquals("tls", tur { TlsBaglanti.ac(AraciAdresi("localhost", s.localPort), adDogrula = HER_AD) })
        } finally { s.close() }
    }

    @Test
    fun guvenilenSertifika_YANLIS_AD_REDDEDILIR_elSikismaKatmani() {
        val s = sunucu(yanlisAd)
        try {
            // Sertifikaya guveniliyor ama adi "localhost" degil. Ikinci katman BILEREK devre disi (hep true):
            // reddi yapan el sikismadaki ad dogrulamasidir (endpointIdentificationAlgorithm).
            assertEquals("tls", tur { TlsBaglanti.ac(AraciAdresi("localhost", s.localPort), guvenen(yanlisAd), HER_AD) })
        } finally { s.close() }
    }

    @Test
    fun guvenilenSertifika_dogruAd_baglanir_veriAkar() {
        val s = sunucu(dogruAd)
        try {
            val b = TlsBaglanti.ac(AraciAdresi("localhost", s.localPort), guvenen(dogruAd), HER_AD)
            val t = ByteArray(16)
            b.okumaSuresi(3000)
            val n = b.giris.read(t)
            assertEquals("merhaba", String(t, 0, n))
            b.cikis.write(1)
            b.kapat()
            b.kapat()                                            // iki kez kapatmak hata degil
        } finally { s.close() }
    }

    @Test
    fun ikinciKatman_platformDogrulayicisiHayirDerse_REDDEDILIR() {
        val s = sunucu(dogruAd)
        try {
            var soruldu: String? = null
            assertEquals("tls", tur { TlsBaglanti.ac(AraciAdresi("localhost", s.localPort), guvenen(dogruAd)) { ad, _ -> soruldu = ad; false } })
            assertEquals("localhost", soruldu)                   // dogrulayiciya ARACININ adi sorulur
        } finally { s.close() }
    }

    @Test
    fun baglanilamayanPort_ag_hataMetniAdresTasimaz() {
        val bos = ServerSocket(0).use { it.localPort }           // kapali port
        val h = try { TlsBaglanti.ac(AraciAdresi("localhost", bos)); null } catch (e: AraciHatasi) { e }
        assertEquals("ag", h!!.tur)
        assertEquals("ag", h.message)
        assertFalse(h.toString().contains("localhost") || h.toString().contains(bos.toString()))
        assertEquals(null, h.cause)
        assertFalse(AraciAdresi("ornek.invalid", 8883).toString().contains("ornek"))
    }

    @Test
    fun adresYalnizMqtts_baskaHerBicimReddedilir() {
        val a = AraciAdresi.coz("mqtts://x1.eu-central.ornek.invalid:8883")
        assertEquals("x1.eu-central.ornek.invalid", a.ad)
        assertEquals(8883, a.port)
        assertEquals(8883, AraciAdresi.coz("mqtts://araci.ornek.invalid").port)
        assertEquals(443, AraciAdresi.coz(" MQTTS://Araci.Ornek.Invalid:443/ ").port)
        assertEquals("araci.ornek.invalid", AraciAdresi.coz(" MQTTS://Araci.Ornek.Invalid:443/ ").ad)
        val at = 64.toChar()                                  // kullanici bilgisi ayirici (dosyada e-posta bicimi olusmasin)
        val kotu = listOf(
            null, "", "mqtt://araci.ornek.invalid:1883", "tcp://araci.ornek.invalid:1883", "ws://araci.ornek.invalid", "wss://araci.ornek.invalid:8084/mqtt",
            "https://araci.ornek.invalid", "araci.ornek.invalid:8883", "mqtts://", "mqtts://:8883", "mqtts://araci.ornek.invalid:0",
            "mqtts://araci.ornek.invalid:65536", "mqtts://araci.ornek.invalid:88x", "mqtts://araci.ornek.invalid/yol",
            "mqtts://araci.ornek.invalid?x=1", "mqtts://araci.ornek.invalid#a", "mqtts://kullanici:gizli${at}araci.ornek.invalid:8883",
            "mqtts://kullanici${at}araci.ornek.invalid", "mqtts://192.168.1.7:8883", "mqtts://10.0.0.1", "mqtts://localhost:8883",
            "mqtts://tekad", "mqtts://-kotu.ornek.invalid", "mqtts://araci..ornek.invalid", "mqtts://araci.ornek.invalid:8883 x",
            "mqtts://araci.ornek.invalid\n:8883", "mqtts://[::1]:8883", "mqtts://araci_alt.ornek.invalid",
        )
        for (u in kotu) assertEquals("$u", "adres-gecersiz", tur { AraciAdresi.coz(u) })
        assertTrue(TlsBaglanti.BAGLANTI_MS in 5_000..15_000)
    }
}
