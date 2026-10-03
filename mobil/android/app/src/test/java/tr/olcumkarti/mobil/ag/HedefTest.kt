package tr.olcumkarti.mobil.ag

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/** JS ile AYNI vektorler: mobil/test/vektor/hedef.tsv (calisma dizini android/app). */
class HedefTest {
    private data class V(val tur: String, val girdi: String, val beklenen: String)

    private fun vektorler(): List<V> {
        val dosya = File("../../test/vektor/hedef.tsv")
        assertTrue("vektor dosyasi yok: ${dosya.path}", dosya.isFile)
        return dosya.readLines(Charsets.UTF_8).filter { it.isNotEmpty() && !it.startsWith("#") }.map {
            val p = it.split("\t")
            val girdi = p[1].replace("{BOSLUK}", " ").replace("{AT}", "@")
                .replace("{SATIR}", "\n").replace("{TERS}", "\\")
            V(p[0], girdi, p[2])
        }
    }

    private fun ayirSonuc(girdi: String, yerelDongu: Boolean): String = try {
        val h = Hedef.ayir(girdi, yerelDongu)
        "${h.ad}:${h.port}"
    } catch (e: Hedef.Hata) {
        "!${e.tur}"
    }

    @Test
    fun vektorDosyasiDolu() {
        val v = vektorler()
        assertTrue(v.count { it.tur == "ozel" } >= 40)
        assertTrue(v.count { it.tur == "ayir" } >= 45)
        assertTrue(v.count { it.tur == "dongu" } >= 5)
    }

    @Test
    fun ozelAdres() {
        for (v in vektorler().filter { it.tur == "ozel" }) {
            assertEquals("ozel: [${v.girdi}]", v.beklenen == "1", Hedef.ozelAdres(v.girdi))
        }
    }

    @Test
    fun ayir() {
        for (v in vektorler().filter { it.tur == "ayir" }) {
            assertEquals("ayir: [${v.girdi}]", v.beklenen, ayirSonuc(v.girdi, false))
        }
    }

    @Test
    fun yerelDonguYalnizSecenekle() {
        for (v in vektorler().filter { it.tur == "dongu" }) {
            assertEquals("dongu: [${v.girdi}]", v.beklenen, ayirSonuc(v.girdi, true))
        }
        assertEquals("!ozel-degil", ayirSonuc("127.0.0.1", false))
    }
}
