package tr.olcumkarti.mobil.bildirim

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Curutucu 5E K-7: kart temelli kapandiysa anlik izleme sonsuza dek yasamaz. */
class VazgecmeTest {
    private val SAAT = 60 * 60 * 1000L

    @Test
    fun kartKesintisizAltiSaatCevrimdisiysa_dolar_oncesindeDolmaz() {
        assertEquals(6 * SAAT, Vazgecme.SURE_MS)
        val v = Vazgecme()
        assertFalse(v.doldu(false, 1000))                       // sure ILK cevrimdisi gorulmede baslar
        assertFalse(v.doldu(false, 1000 + 6 * SAAT - 1))
        assertTrue(v.doldu(false, 1000 + 6 * SAAT))
        assertTrue(v.doldu(false, 1000 + 9 * SAAT))
    }

    @Test
    fun kartCevrimiciGorulurse_sureSifirlanir() {
        val v = Vazgecme()
        assertFalse(v.doldu(false, 0))
        assertFalse(v.doldu(true, 5 * SAAT))                    // kart dondu
        assertFalse(v.doldu(false, 5 * SAAT + 1))               // yeniden koptu: sure BASTAN
        assertFalse(v.doldu(false, 11 * SAAT))
        assertTrue(v.doldu(false, 11 * SAAT + 1))
        assertFalse(v.doldu(true, 20 * SAAT))                   // dolduktan sonra da cevrimici = dolmamis
    }

    @Test
    fun durumBilinmiyorken_dolmaz_amaSureDeSifirlanmaz_cevrimiciKartHicDolmaz() {
        val v = Vazgecme()
        assertFalse(v.doldu(null, 0))
        assertFalse(v.doldu(null, 100 * SAAT))                  // hic "cevrimdisi" denmedi: sure baslamadi
        assertFalse(v.doldu(false, 100 * SAAT))
        assertFalse(v.doldu(null, 107 * SAAT))                  // bilinmiyorken karar yok
        assertTrue(v.doldu(false, 107 * SAAT))                  // ...ama aradaki sure sayildi
        val hep = Vazgecme()
        for (t in 0..40) assertFalse(hep.doldu(true, t * SAAT))
        assertTrue(Vazgecme(10).doldu(false, 0).not() && Vazgecme(0).doldu(false, 0))
    }

    @Test
    fun servis_surdurKararinaVazgecmeyiKatar() {
        val kok = generateSequence(File("").absoluteFile) { it.parentFile }.first { File(it, "app/src/main/java").isDirectory }
        val metin = File(kok, "app/src/main/java/tr/olcumkarti/mobil/bildirim/IzlemeServisi.kt").readText()
        assertTrue("surdur = { synchronized(kilit) { k.kayitSuruyor() != false && !vazgecme.doldu(k.kartCevrimici, SystemClock.elapsedRealtime()) } }," in metin)
        assertTrue("            val vazgecme = Vazgecme()\n" in metin.replace("\r\n", "\n"))
    }
}
