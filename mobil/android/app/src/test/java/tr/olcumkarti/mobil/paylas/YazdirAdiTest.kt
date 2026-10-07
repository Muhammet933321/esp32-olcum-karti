package tr.olcumkarti.mobil.paylas

import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * 5P (K12): panelin rapor "Yazdir"i Android yazdirma penceresine gider. Is adi JS'ten gelir ve yazdirma
 * kuyrugunda / "PDF olarak kaydet"in onerdigi dosya adinda gorunur: yalniz guvenli karakterler, sinirli boy,
 * bos ya da gecersizse sabit ad.
 */
class YazdirAdiTest {
    @Test fun gecerliAdAynenKalir() {
        assertEquals("kayit-5-rapor", YazdirAdi.temizle("kayit-5-rapor"))
        assertEquals("Olcum raporu 2026.10.07", YazdirAdi.temizle("Olcum raporu 2026.10.07"))
    }

    @Test fun guvensizKarakterlerAltCizgiOlur() {
        assertEquals("a_b_c", YazdirAdi.temizle("a/b\\c"))
        assertEquals("kay_t", YazdirAdi.temizle("kayıt"))
        assertEquals("x_y", YazdirAdi.temizle("x\ny"))
    }

    @Test fun bosYaDaGecersizSabitAd() {
        assertEquals(YazdirAdi.VARSAYILAN, YazdirAdi.temizle(null))
        assertEquals(YazdirAdi.VARSAYILAN, YazdirAdi.temizle(""))
        assertEquals(YazdirAdi.VARSAYILAN, YazdirAdi.temizle("   "))
        assertEquals(YazdirAdi.VARSAYILAN, YazdirAdi.temizle("../.."))
    }

    @Test fun boySinirli() {
        assertEquals(YazdirAdi.AZAMI, YazdirAdi.temizle("a".repeat(500)).length)
    }
}
