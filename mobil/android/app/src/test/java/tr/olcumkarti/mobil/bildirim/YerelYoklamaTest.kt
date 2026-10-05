package tr.olcumkarti.mobil.bildirim

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import tr.olcumkarti.mobil.ag.AgHatasi
import tr.olcumkarti.mobil.ag.HttpYanit

/** A36: araci "kart cevrimdisi" derken kart yerelde gorunuyor mu — imzasiz /eslestir/bilgi yoklamasi (saf JVM). */
class YerelYoklamaTest {
    @get:Rule val gecici = TemporaryFolder()

    private val KIMLIK = "0123456789abcdef"
    private val ADRES = "192.168.1.7:80"
    private fun yanit(kod: Int, govde: String) = HttpYanit(kod, emptyMap(), govde.toByteArray(Charsets.UTF_8))
    private fun bilgi(kimlik: String = KIMLIK) = "{\"kimlik\":\"$kimlik\",\"tuz\":\"00\",\"tur\":20000,\"acilis\":\"ab\"}"

    private class Kayit(val url: String, val sure: Int, val azami: Int)

    private fun kur(yanit: () -> HttpYanit): Pair<YerelYoklama, ArrayList<Kayit>> {
        val istekler = ArrayList<Kayit>()
        return Pair(YerelYoklama { url, sure, azami -> istekler.add(Kayit(url, sure, azami)); yanit() }, istekler)
    }

    @Test
    fun kartGorunuyor_imzasizBilgiIstegi_kimlikTamEsitse() {
        val (y, istekler) = kur { yanit(200, bilgi()) }
        assertTrue(y.kartGorunuyor(KIMLIK, ADRES))
        assertEquals(1, istekler.size)
        assertEquals("http://192.168.1.7:80/eslestir/bilgi", istekler[0].url)
        assertEquals(2_000, istekler[0].sure); assertEquals(1024, istekler[0].azami)
        assertEquals("/eslestir/bilgi", YerelYoklama.YOL)
        assertEquals(10_000L, YerelYoklama.ARALIK_MS)
    }

    @Test
    fun baskaKart_hataKodu_bozukYanit_agHatasi_gorunmuyor() {
        assertFalse(kur { yanit(200, bilgi("fedcba9876543210")) }.first.kartGorunuyor(KIMLIK, ADRES))     // o adreste BASKA kart
        assertFalse(kur { yanit(200, bilgi(KIMLIK.uppercase())) }.first.kartGorunuyor(KIMLIK, ADRES))
        assertFalse(kur { yanit(404, bilgi()) }.first.kartGorunuyor(KIMLIK, ADRES))
        assertFalse(kur { yanit(500, bilgi()) }.first.kartGorunuyor(KIMLIK, ADRES))
        for (govde in listOf("", "{", "[]", "{\"kimlik\":5}", "{\"baska\":\"$KIMLIK\"}", "<html>$KIMLIK</html>")) {
            assertFalse(govde, kur { yanit(200, govde) }.first.kartGorunuyor(KIMLIK, ADRES))
        }
        assertFalse(kur { yanit(200, bilgi() + " ".repeat(1024)) }.first.kartGorunuyor(KIMLIK, ADRES))     // buyuk yanit
        assertFalse(kur { throw AgHatasi("zaman-asimi") }.first.kartGorunuyor(KIMLIK, ADRES))
        assertFalse(kur { throw IllegalStateException("wifi yok") }.first.kartGorunuyor(KIMLIK, ADRES))
    }

    @Test
    fun adres_yalnizOzelIPv4_adVeHerkeseAcikAdreseISTEK_GITMEZ() {
        val (y, istekler) = kur { yanit(200, bilgi()) }
        for (adres in listOf(null, "", "olcum.local", "olcum.local:80", "8.8.8.8", "203.0.113.9:80", "ornek.example", "192.168.1.7/yol", "192.168.1.7:0",
            "192.168.1.7:99999", "http://192.168.1.7:80/x?y", "192.168.1.7:80:80", "127.0.0.1", "0.0.0.0", "192.168.001.7", "1".repeat(30))) {
            assertFalse(adres, y.kartGorunuyor(KIMLIK, adres))
            assertNull(adres, YerelYoklama.url(adres).takeIf { adres != null && adres.startsWith("http://") })
        }
        assertEquals(0, istekler.size)
        assertEquals("http://10.0.0.5:80/eslestir/bilgi", YerelYoklama.url("10.0.0.5"))
        assertEquals("http://172.16.9.1:8080/eslestir/bilgi", YerelYoklama.url("172.16.9.1:8080"))
        assertEquals("http://169.254.1.1:80/eslestir/bilgi", YerelYoklama.url("169.254.1.1"))
        assertEquals("http://192.168.4.1:80/eslestir/bilgi", YerelYoklama.url("192.168.4.1:80"))
        assertNull(YerelYoklama.url("http://192.168.1.7:80/x"))
    }

    @Test
    fun gerekli_yalnizAraciAcikcaCevrimdisiDediginde() {
        assertTrue(YerelYoklama.gerekli(false))
        assertFalse(YerelYoklama.gerekli(true))
        assertFalse(YerelYoklama.gerekli(null))
    }

    @Test
    fun kararaBaglaninca_kopukYerineEvInterneti_yoklamaKesilinceKopuk() {
        // Servisin yaptigi: araci "cevrimdisi" dedi -> yoklama kart yerelde diyor -> yerelGoruldu -> tik.
        var saat = 0.0
        val cikan = ArrayList<String>()
        val k = BildirimKarar({ cikan.add(it.anahtar) }, { saat })
        val durum = mapOf<String, Any?>("c" to 1L, "a" to 3L, "t" to 1790000000L, "k" to 2L, "o" to 81L, "y" to 1L)
        k.mqttBagliOldu(true)
        k.mqttMesaj("durum", durum)
        val (y, _) = kur { yanit(200, bilgi()) }
        saat = 100.0
        k.mqttMesaj("durum", mapOf("c" to 0L))
        assertEquals(listOf("bld.kopuk"), cikan)
        assertTrue(YerelYoklama.gerekli(k.kartCevrimici))
        saat = 110.0
        if (y.kartGorunuyor(KIMLIK, ADRES)) k.yerelGoruldu()
        k.tik()
        assertEquals(listOf("bld.kopuk", "bld.ev_interneti"), cikan)
        saat = 120.0; k.yerelGoruldu(); k.tik()
        assertEquals(2, cikan.size)                                              // gorunmeye devam: yeni bildirim yok
        saat = 140.0; k.tik()                                                    // 15 s'den uzun suredir gorulmedi
        assertEquals(listOf("bld.kopuk", "bld.ev_interneti", "bld.kopuk"), cikan)
        k.mqttMesaj("durum", durum)
        assertFalse(YerelYoklama.gerekli(k.kartCevrimici))                       // kart dondu: yoklama durur
    }

    @Test
    fun adresDosyasi_yalnizOzelIPv4Yazilir_bozukDosyaNull_eslesmeKalkincaSilinir() {
        val kok = gecici.newFolder("kasa")
        val d = BildirimDeposu(kok)
        assertNull(d.adresOku(KIMLIK))
        d.adresYaz(KIMLIK, ADRES)
        assertEquals(ADRES, d.adresOku(KIMLIK))
        for (kotu in listOf(null, "", "olcum.local", "8.8.8.8:80", "192.168.1.7/x", "x".repeat(40))) {
            assertEquals(kotu, "bicim", try { d.adresYaz(KIMLIK, kotu); null } catch (e: ZarfHatasi) { e.tur })
        }
        assertEquals(ADRES, d.adresOku(KIMLIK))                                  // reddedilen yazim eskisini bozmaz
        assertEquals("bicim", try { d.adresYaz("../x", ADRES); null } catch (e: ZarfHatasi) { e.tur })
        assertEquals("bicim", try { d.adresOku("../x"); null } catch (e: ZarfHatasi) { e.tur })
        java.io.File(kok, "$KIMLIK.adres").writeText("8.8.8.8:80")               // diskte degistirilmis: herkese acik adres okunmaz
        assertNull(d.adresOku(KIMLIK))
        java.io.File(kok, "$KIMLIK.adres").writeText("1".repeat(200))
        assertNull(d.adresOku(KIMLIK))
        d.adresYaz(KIMLIK, "10.0.0.5")
        val sarici = object : tr.olcumkarti.mobil.kasa.Sarici {
            override fun sar(duz: ByteArray, aad: ByteArray): ByteArray = duz
            override fun ac(sarili: ByteArray, aad: ByteArray): ByteArray = sarili
        }
        tr.olcumkarti.mobil.kasa.KasaDeposu(kok, sarici).sil(KIMLIK)
        assertNull(d.adresOku(KIMLIK))
    }
}
