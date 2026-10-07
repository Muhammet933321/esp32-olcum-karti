package tr.olcumkarti.mobil.paylas

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File

/** 5F: paylasilacak dosyanin gecici deposu — ad denetimi, sira, boy, temizlik (saf JVM). */
class PaylasDeposuTest {
    @get:Rule val gecici = TemporaryFolder()

    private fun turu(islem: () -> Any?): String? = try { islem(); null } catch (e: PaylasHatasi) { e.tur }
    private fun kok(): File = File(gecici.root, "onbellek/paylas")

    @Test
    fun baslatYazBitir_parcalarSirayla_dosyaAyniBaytlar() {
        val d = PaylasDeposu(kok())
        d.baslat("kayit-101-aku-sarj.csv")
        d.yaz("kayit-101-aku-sarj.csv", byteArrayOf(1, 2, 3))
        d.yaz("kayit-101-aku-sarj.csv", byteArrayOf(4, 5))
        val f = d.bitir("kayit-101-aku-sarj.csv", 5)
        assertEquals(File(kok(), "kayit-101-aku-sarj.csv"), f)
        assertArrayEquals(byteArrayOf(1, 2, 3, 4, 5), f.readBytes())
    }

    @Test
    fun adDosyaSisteminegider_gecersizAdHerIslemdeReddedilir_dizinDisinaYazilmaz() {
        val d = PaylasDeposu(kok())
        val kotu = listOf(null, "", "../kasa/x.csv", "..\\x.csv", "a/b.csv", "kayit.exe", "kayit.csv.sh", "kayit..csv", ".gizli.csv", "kayit 1.csv",
            "kayıt.csv", "a".repeat(90) + ".csv", "kayit.CSV", "kayit", "rapor.htm", "rapor.PDF", "rapor.html.exe", "rapor.js")
        for (ad in kotu) {
            assertEquals(ad, "bicim", turu { d.baslat(ad) })
            assertEquals(ad, "bicim", turu { d.yaz(ad, byteArrayOf(1)) })
            assertEquals(ad, "bicim", turu { d.bitir(ad, 1) })
        }
        assertFalse(kok().exists())
        assertFalse(File(gecici.root, "onbellek/kasa").exists())
        for (ad in listOf("kayit-5.kyt", "kayit-5-rapor.txt", "kayit-101-aku-sarj-en.csv", "a.csv", "kayit-5-rapor.html", "kayit-5-rapor.pdf")) { d.baslat(ad); d.yaz(ad, byteArrayOf(1)); d.bitir(ad, 1) }
    }

    @Test
    fun baslat_oncekiPaylasiminDosyasiniSiler_tekDosyaKalir() {
        val d = PaylasDeposu(kok())
        d.baslat("kayit-1.csv"); d.yaz("kayit-1.csv", ByteArray(10)); d.bitir("kayit-1.csv", 10)
        File(kok(), "yabanci.bin").writeBytes(ByteArray(3))
        d.baslat("kayit-2.kyt")
        assertEquals(listOf("kayit-2.kyt"), kok().list()!!.toList())
        assertEquals(0L, File(kok(), "kayit-2.kyt").length())
        d.temizle()
        assertEquals(0, kok().list()!!.size)
        PaylasDeposu(File(gecici.root, "hic-yok")).temizle()                 // dizin yokken temizlik hata degil
    }

    @Test
    fun sira_baslatilmadanYaDaBaskaAdlaYazilamaz_bitirildiktenSonraYazilamaz() {
        val d = PaylasDeposu(kok())
        assertEquals("sira", turu { d.yaz("kayit-1.csv", byteArrayOf(1)) })
        assertEquals("sira", turu { d.bitir("kayit-1.csv", 1) })
        d.baslat("kayit-1.csv")
        assertEquals("sira", turu { d.yaz("kayit-2.csv", byteArrayOf(1)) })
        d.yaz("kayit-1.csv", byteArrayOf(1))
        d.bitir("kayit-1.csv", 1)
        assertEquals("sira", turu { d.yaz("kayit-1.csv", byteArrayOf(2)) })
        assertEquals("sira", turu { d.bitir("kayit-1.csv", 1) })
        assertArrayEquals(byteArrayOf(1), File(kok(), "kayit-1.csv").readBytes())
    }

    @Test
    fun boy_beklenenleTutmazsaDosyaSilinir_bosDosyaPaylasilmaz() {
        val d = PaylasDeposu(kok())
        d.baslat("kayit-1.csv"); d.yaz("kayit-1.csv", ByteArray(10))
        assertEquals("boy", turu { d.bitir("kayit-1.csv", 11) })
        assertEquals(0, kok().list()!!.size)
        d.baslat("kayit-1.csv")
        assertEquals("boy", turu { d.bitir("kayit-1.csv", 0) })
        d.baslat("kayit-1.csv"); d.yaz("kayit-1.csv", ByteArray(4))
        assertEquals("boy", turu { d.bitir("kayit-1.csv", -4) })
    }

    @Test
    fun sinirlar_parcaVeToplamBoy() {
        val d = PaylasDeposu(kok())
        d.baslat("kayit-1.csv")
        assertEquals("bicim", turu { d.yaz("kayit-1.csv", ByteArray(PaylasDeposu.PARCA_AZAMI + 1)) })
        d.yaz("kayit-1.csv", ByteArray(PaylasDeposu.PARCA_AZAMI))
        assertEquals(1 shl 20, PaylasDeposu.PARCA_AZAMI)
        assertEquals(64L * 1024 * 1024, PaylasDeposu.AZAMI)
        // Toplam sinir: 64 parca sigar, 65.'de dosya silinir.
        val parca = ByteArray(PaylasDeposu.PARCA_AZAMI)
        for (i in 2..64) d.yaz("kayit-1.csv", parca)
        assertEquals("cok-buyuk", turu { d.yaz("kayit-1.csv", ByteArray(1)) })
        assertEquals(0, kok().list()!!.size)
        assertEquals("sira", turu { d.yaz("kayit-1.csv", ByteArray(1)) })
        assertTrue(PaylasDeposu.MIMELER == setOf("text/csv", "text/plain", "application/octet-stream", "text/html", "application/pdf"))
    }
}
