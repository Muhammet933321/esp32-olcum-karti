package tr.olcumkarti.mobil.kasa

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import tr.olcumkarti.mobil.kasa.Sinama.K1
import tr.olcumkarti.mobil.kasa.Sinama.K2
import tr.olcumkarti.mobil.kasa.Sinama.anahtar
import tr.olcumkarti.mobil.kasa.Sinama.tur

class KasaKayitTest {
    private val sarici = BellekSarici()

    @Test
    fun gidisDonus() {
        val p = KasaKayit.paketle(K1, 7, "Telefon şğü", anahtar(), sarici)
        val k = KasaKayit.coz(K1, p, sarici)
        assertEquals(K1, k.kimlik)
        assertEquals(7, k.n)
        assertEquals("Telefon şğü", k.ad)
        assertArrayEquals(anahtar(), k.anahtar)
        // Uc degerler: n = 1 ve 255, bos ad, tam 24 baytlik ad.
        assertEquals(255, KasaKayit.coz(K1, KasaKayit.paketle(K1, 255, "", anahtar(), sarici), sarici).n)
        assertEquals(1, KasaKayit.coz(K1, KasaKayit.paketle(K1, 1, "a".repeat(24), anahtar(), sarici), sarici).n)
    }

    @Test
    fun baslikSurumluVeHerSarimdaIvFarkli() {
        val a = KasaKayit.paketle(K1, 1, "x", anahtar(), sarici)
        val b = KasaKayit.paketle(K1, 1, "x", anahtar(), sarici)
        assertEquals("OKKS", String(a, 0, 4, Charsets.US_ASCII))
        assertEquals(1, a[4].toInt())
        assertEquals(5 + 12 + (2 + 1 + 32) + 16, a.size)
        assertFalse(a.contentEquals(b))
    }

    @Test
    fun yanlisKimlikleAcilmaz() {
        val p = KasaKayit.paketle(K1, 1, "x", anahtar(), sarici)
        assertEquals("bozuk", tur { KasaKayit.coz(K2, p, sarici) })
    }

    @Test
    fun herTekBitBozulmasiBozuk() {
        val p = KasaKayit.paketle(K1, 3, "ad", anahtar(), sarici)
        for (i in p.indices) {
            for (bit in 0..7) {
                val q = p.copyOf()
                q[i] = (q[i].toInt() xor (1 shl bit)).toByte()
                assertEquals("bayt $i bit $bit", "bozuk", tur { KasaKayit.coz(K1, q, sarici) })
            }
        }
    }

    @Test
    fun kirpikVeUzatilmisDosyaBozuk() {
        val p = KasaKayit.paketle(K1, 3, "ad", anahtar(), sarici)
        for (boy in 0 until p.size) assertEquals("boy $boy", "bozuk", tur { KasaKayit.coz(K1, p.copyOf(boy), sarici) })
        assertEquals("bozuk", tur { KasaKayit.coz(K1, p + byteArrayOf(0), sarici) })
        assertEquals("bozuk", tur { KasaKayit.coz(K1, ByteArray(4096), sarici) })
    }

    @Test
    fun baskaSarmaAnahtariylaYaDaAnahtarKaybindaBozuk() {
        val p = KasaKayit.paketle(K1, 3, "ad", anahtar(), sarici)
        assertEquals("bozuk", tur { KasaKayit.coz(K1, p, BellekSarici(ByteArray(32) { 1 })) })
        sarici.yokEt()
        assertEquals("bozuk", tur { KasaKayit.coz(K1, p, sarici) })
    }

    @Test
    fun icYapisiTutarsizDuzMetinBozuk() {
        // Etiketi GECERLI ama ic uzunlugu tutarsiz duz metinler (surum karisikligi / hatali yazar).
        val aad = byteArrayOf(0x4f, 0x4b, 0x4b, 0x53, 1) + K1.toByteArray()
        fun dosya(duz: ByteArray) = byteArrayOf(0x4f, 0x4b, 0x4b, 0x53, 1) + sarici.sar(duz, aad)
        val iyi = byteArrayOf(1, 0) + anahtar()
        assertEquals("tamam", tur { KasaKayit.coz(K1, dosya(iyi), sarici) })
        assertEquals("bozuk", tur { KasaKayit.coz(K1, dosya(byteArrayOf(0, 0) + anahtar()), sarici) })       // n = 0
        assertEquals("bozuk", tur { KasaKayit.coz(K1, dosya(byteArrayOf(1, 1) + anahtar()), sarici) })       // ad eksik
        assertEquals("bozuk", tur { KasaKayit.coz(K1, dosya(iyi + byteArrayOf(0)), sarici) })                // fazla bayt
        assertEquals("bozuk", tur { KasaKayit.coz(K1, dosya(byteArrayOf(1, 0)), sarici) })                   // anahtar yok
        assertEquals("bozuk", tur { KasaKayit.coz(K1, dosya(byteArrayOf(1, 1, 0xff.toByte()) + anahtar()), sarici) })  // bozuk UTF-8
    }

    @Test
    fun anahtarUzunluguTam32() {
        assertEquals("bicim", tur { KasaKayit.paketle(K1, 1, "x", ByteArray(31) { 5 }, sarici) })
        assertEquals("bicim", tur { KasaKayit.paketle(K1, 1, "x", ByteArray(33) { 5 }, sarici) })
        assertEquals("bicim", tur { KasaKayit.paketle(K1, 1, "x", ByteArray(0), sarici) })
    }

    @Test
    fun nVeAdSinirlari() {
        assertEquals("bicim", tur { KasaKayit.paketle(K1, 0, "x", anahtar(), sarici) })
        assertEquals("bicim", tur { KasaKayit.paketle(K1, 256, "x", anahtar(), sarici) })
        assertEquals("bicim", tur { KasaKayit.paketle(K1, -1, "x", anahtar(), sarici) })
        assertEquals("bicim", tur { KasaKayit.paketle(K1, 1, "a".repeat(25), anahtar(), sarici) })
        assertEquals("bicim", tur { KasaKayit.paketle(K1, 1, "ş".repeat(13), anahtar(), sarici) })   // 26 bayt
        assertEquals("tamam", tur { KasaKayit.paketle(K1, 1, "ş".repeat(12), anahtar(), sarici) })
    }

    @Test
    fun kimlikKurali() {
        assertTrue(KasaKayit.kimlikGecerli(K1))
        for (k in listOf(null, "", "../x", "0123456789ABCDEF", "0123456789abcde", "0123456789abcdef0", "0123456789abcdeg",
            "../../aaaaaaaaaa", "..\\..\\aaaaaaaaaa", "0123456789abcde\n", "0123456789abcde/", "0123456789abcde.", "０１２３４５６７89abcdef")) {
            assertFalse("kimlik: $k", KasaKayit.kimlikGecerli(k))
        }
        assertEquals("bicim", tur { KasaKayit.paketle("../../aaaaaaaaaa", 1, "x", anahtar(), sarici) })
        assertEquals("bicim", tur { KasaKayit.coz("0123456789ABCDEF", ByteArray(80), sarici) })
    }

    @Test
    fun sariliCiktidaDuzAnahtarVeAdYok() {
        val k = anahtar()
        val p = KasaKayit.paketle(K1, 9, "SINAMA-AD-GORUNMEZ", k, sarici)
        assertFalse(Sinama.icerir(p, k))
        for (i in 0..k.size - 8) assertFalse("anahtar parcasi $i", Sinama.icerir(p, k.copyOfRange(i, i + 8)))
        assertFalse(Sinama.icerir(p, "SINAMA-AD".toByteArray()))
    }

    @Test
    fun saricidanGelenIstisnaMesajiSizmaz() {
        val patlak = object : Sarici {
            override fun sar(duz: ByteArray, aad: ByteArray): ByteArray = throw IllegalStateException("GIZLI-AYRINTI")
            override fun ac(sarili: ByteArray, aad: ByteArray): ByteArray = throw IllegalStateException("GIZLI-AYRINTI")
        }
        assertEquals("ic-hata", tur { KasaKayit.paketle(K1, 1, "x", anahtar(), patlak) })
        assertEquals("bozuk", tur { KasaKayit.coz(K1, KasaKayit.paketle(K1, 1, "x", anahtar(), sarici), patlak) })
        assertEquals("Kayit", Kayit(K1, 1, "x", anahtar()).toString())
    }
}
