package tr.olcumkarti.mobil.depo

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class DepoYoluTest {
    private val K = "0123456789abcdef"

    @Test
    fun gecerliAdres_kimlikDoner() {
        assertEquals(K, DepoYolu.kimlik("https://localhost/_depo/$K/kayitlar.kyt"))
        assertTrue(DepoYolu.depoAdresi("https://localhost/_depo/$K/kayitlar.kyt"))
    }

    @Test
    fun baskaHerBicimReddedilir() {
        val kotu = listOf(
            null, "", "https://localhost/_depo/", "https://localhost/_depo/$K", "https://localhost/_depo/$K/",
            "https://localhost/_depo/$K/durum.json", "https://localhost/_depo/$K/kalibrasyon.json",
            "https://localhost/_depo/$K/kayitlar.kyt?x=1", "https://localhost/_depo/$K/kayitlar.kyt#a",
            "https://localhost/_depo/$K/kayitlar.kyt/", "https://localhost/_depo/$K/kayitlar.kyt/..",
            "https://localhost/_depo/$K/../$K/kayitlar.kyt", "https://localhost/_depo/../kasa/$K.bin",
            "https://localhost/_depo/%2e%2e/kasa/$K/kayitlar.kyt", "https://localhost/_depo/$K/kayitlar%2ekyt",
            "https://localhost/_depo/0123456789ABCDEF/kayitlar.kyt", "https://localhost/_depo/0123456789abcde/kayitlar.kyt",
            "https://localhost/_depo/0123456789abcdef0/kayitlar.kyt", "https://localhost/_depo//kayitlar.kyt",
            "http://localhost/_depo/$K/kayitlar.kyt", "https://localhost:8080/_depo/$K/kayitlar.kyt",
            "https://localhost.evil.com/_depo/$K/kayitlar.kyt", "https://localhost/x/_depo/$K/kayitlar.kyt",
            "https://localhost/_depo/$K/kayitlar.kyt\n", " https://localhost/_depo/$K/kayitlar.kyt",
            "https://localhost/_depo/$K/KAYITLAR.KYT", "https://localhost/_depo/$K/kayitlarXkyt",
        )
        for (u in kotu) assertNull("$u", DepoYolu.kimlik(u))
    }

    @Test
    fun depoOnEkiTasiyanBozukAdresDosyaSunucusunaBirakilmaz() {
        assertTrue(DepoYolu.depoAdresi("https://localhost/_depo/../kasa/x"))
        assertTrue(DepoYolu.depoAdresi("https://localhost/_depo/"))
        assertFalse(DepoYolu.depoAdresi("https://localhost/index.html"))
        assertFalse(DepoYolu.depoAdresi("https://localhost/_depox"))
        assertFalse(DepoYolu.depoAdresi(null))
    }
}
