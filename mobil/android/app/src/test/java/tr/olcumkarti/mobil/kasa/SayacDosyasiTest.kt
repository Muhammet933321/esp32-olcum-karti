package tr.olcumkarti.mobil.kasa

import org.junit.After
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import tr.olcumkarti.mobil.kasa.Sinama.tur
import java.io.File

class SayacDosyasiTest {
    private val dizin = Sinama.geciciDizin()
    private val dosya = File(dizin, "0123456789abcdef.sayac")
    private val sayac = SayacDosyasi(dosya)

    @After
    fun temizle() {
        dizin.deleteRecursively()
    }

    @Test
    fun dosyaYokkenSifir() {
        assertEquals(0L, sayac.oku())
        assertFalse(dosya.exists())
    }

    @Test
    fun yazOku_bicimVeGeciciDosyaKalmaz() {
        assertEquals(1759500000000L, sayac.yaz(1759500000000L))
        assertEquals(1759500000000L, sayac.oku())
        assertEquals(1759500000000L, SayacDosyasi(dosya).oku())
        val metin = dosya.readText()
        assertTrue(Regex("^1759500000000\n[0-9a-f]{8}\n$").matches(metin))
        assertArrayEquals(arrayOf(dosya.name), dizin.list())
        assertEquals(Long.MAX_VALUE, sayac.yaz(Long.MAX_VALUE))
        assertEquals(Long.MAX_VALUE, sayac.oku())
    }

    @Test
    fun kucukDegerGeri_dosyaDegismez() {
        sayac.yaz(5000)
        val once = dosya.readBytes()
        assertEquals("geri", tur { sayac.yaz(4999) })
        assertEquals("geri", tur { sayac.yaz(0) })
        assertArrayEquals(once, dosya.readBytes())
        assertEquals(5000L, sayac.oku())
    }

    @Test
    fun esitVeBuyukKabul() {
        sayac.yaz(5000)
        assertEquals(5000L, sayac.yaz(5000))
        assertEquals(5001L, sayac.yaz(5001))
        assertEquals(5001L, sayac.oku())
    }

    @Test
    fun bozukVeYarimDosyaBozuk_sifirDonmez() {
        sayac.yaz(123456)
        val iyi = dosya.readText()
        val bozuklar = listOf(
            "",                                   // bos (yarim yazim)
            "123456",                             // saglama yok
            "123456\n",                           // saglama satiri yok
            iyi.dropLast(1),                      // son satir sonu yok
            iyi.dropLast(3),                      // kirpik saglama
            iyi.replaceFirst("123456", "123457"), // deger degismis, saglama eski
            iyi.replaceFirst("123456", "0123456"),
            "123456\n00000000\n",                 // yanlis saglama
            iyi + "\n",
            iyi + "x",
            " $iyi",
            iyi.replace("\n", "\r\n"),
            "-1\n" + iyi.substringAfter("\n"),
            "abc\nabcdef01\n",
            "99999999999999999999\n00000000\n",   // Long tasmasi
            "x".repeat(4096),
        )
        for (b in bozuklar) {
            dosya.writeText(b)
            assertEquals("icerik: ${b.take(30)}", "bozuk", tur { sayac.oku() })
            // Bozuk dosyanin ustune de yazilmaz: eski deger bilinmeden monotonluk korunamaz.
            assertEquals("bozuk", tur { sayac.yaz(Long.MAX_VALUE) })
            assertEquals(b, dosya.readText())
        }
        dosya.writeBytes(byteArrayOf(0, 1, 2, 0xff.toByte()))
        assertEquals("bozuk", tur { sayac.oku() })
    }

    @Test
    fun metinAyristirma() {
        assertEquals(0L, SayacDosyasi.ayristir("0"))
        assertEquals(Long.MAX_VALUE, SayacDosyasi.ayristir("9223372036854775807"))
        assertEquals(7L, SayacDosyasi.ayristir("007"))
        for (m in listOf(null, "", "-1", "+1", " 1", "1 ", "1\n", "1.0", "1e3", "0x10", "12345678901234567890",
            "9223372036854775808", "9999999999999999999", "١٢٣", "abc")) {
            assertEquals("metin: $m", "bicim", tur { SayacDosyasi.ayristir(m) })
        }
        assertEquals("bicim", tur { sayac.yaz(-1) })
        assertFalse(dosya.exists())
    }

    @Test
    fun geciciDosyaKalintisiOkumayiEtkilemez() {
        sayac.yaz(777)
        // Yazim sirasinda cokme: gecici dosya yarim kaldi, yeniden adlandirma olmadi.
        val gecici = File(dizin, dosya.name + ".gecici")
        gecici.writeText("99")
        assertEquals(777L, sayac.oku())
        assertEquals("geri", tur { sayac.yaz(776) })
        assertEquals(778L, sayac.yaz(778))
        assertEquals(778L, sayac.oku())
        assertFalse(gecici.exists())
    }

    @Test
    fun ilkYazimdanOnceCokmeSifir() {
        File(dizin, dosya.name + ".gecici").writeText("55\n")
        assertEquals(0L, sayac.oku())
    }
}
