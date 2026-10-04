package tr.olcumkarti.mobil.kasa

import org.junit.After
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import tr.olcumkarti.mobil.kasa.Sinama.K1
import tr.olcumkarti.mobil.kasa.Sinama.K2
import tr.olcumkarti.mobil.kasa.Sinama.anahtar
import tr.olcumkarti.mobil.kasa.Sinama.tur
import java.io.File
import java.util.Base64

class KasaDeposuTest {
    private val ust = Sinama.geciciDizin()
    private val kok = File(ust, "files/kasa")
    private val sarici = BellekSarici()
    private val depo = KasaDeposu(kok, sarici) { sarici.yokEt() }
    private val komut = KasaKomut(depo)
    private val b64 = Base64.getEncoder()
    private val KOTU_KIMLIKLER = listOf(null, "", "../x", "0123456789ABCDEF", "0123456789abcde", "0123456789abcdef0",
        "../../aaaaaaaaaa", "..\\..\\aaaaaaaaaa", "/aaaaaaaaaaaaaaa", "aaaaaaaaaaaaaa/.", "0123456789abcde\u0000")

    @After
    fun temizle() {
        ust.deleteRecursively()
    }

    private fun agac(): List<String> = ust.walkTopDown().filter { it.isFile }.map { it.relativeTo(ust).invariantSeparatorsPath }.sorted().toList()

    @Test
    fun yazOkuKaliciVeUstuneYazilir() {
        depo.anahtarYaz(K1, 2, "Telefon", anahtar())
        val k = KasaDeposu(kok, sarici).anahtarOku(K1)    // yeni nesne: diskten
        assertEquals(2, k.n)
        assertEquals("Telefon", k.ad)
        assertArrayEquals(anahtar(), k.anahtar)
        depo.anahtarYaz(K1, 3, "Yeni", anahtar(0x40))
        assertArrayEquals(anahtar(0x40), depo.anahtarOku(K1).anahtar)
        assertEquals(3, depo.anahtarOku(K1).n)
        assertEquals(listOf("files/kasa/$K1.anahtar"), agac())
    }

    @Test
    fun kayitYokkenYok() {
        assertEquals("yok", tur { depo.anahtarOku(K1) })
        depo.anahtarYaz(K2, 1, "x", anahtar())
        assertEquals("yok", tur { depo.anahtarOku(K1) })
    }

    @Test
    fun kotuKimlikHerIslemdeBicim_dizinDisinaCikilamaz() {
        for (k in KOTU_KIMLIKLER) {
            assertEquals("yaz $k", "bicim", tur { depo.anahtarYaz(k, 1, "x", anahtar()) })
            assertEquals("oku $k", "bicim", tur { depo.anahtarOku(k) })
            assertEquals("sil $k", "bicim", tur { depo.sil(k) })
            assertEquals("sayacOku $k", "bicim", tur { depo.sayacOku(k) })
            assertEquals("sayacYaz $k", "bicim", tur { depo.sayacYaz(k, 5) })
            assertEquals("komut sayacYaz $k", "bicim", tur { komut.sayacYaz(k, "5") })
        }
        assertEquals(emptyList<String>(), agac())
        // Dizin disindaki dosya sil ile de silinemez.
        val disari = File(ust, "files/aaaaaaaaaa.anahtar").apply { parentFile!!.mkdirs(); writeText("x") }
        kok.mkdirs()
        assertEquals("bicim", tur { depo.sil("../aaaaaaaaaa") })
        assertTrue(disari.exists())
    }

    @Test
    fun anahtarUzunluguVeAlanDenetimi() {
        assertEquals("bicim", tur { depo.anahtarYaz(K1, 1, "x", ByteArray(31)) })
        assertEquals("bicim", tur { depo.anahtarYaz(K1, 1, "x", ByteArray(33)) })
        assertEquals("bicim", tur { depo.anahtarYaz(K1, 0, "x", anahtar()) })
        assertEquals("bicim", tur { depo.anahtarYaz(K1, 256, "x", anahtar()) })
        assertEquals("bicim", tur { depo.anahtarYaz(K1, 1, "a".repeat(25), anahtar()) })
        assertEquals(emptyList<String>(), agac())
    }

    @Test
    fun baskaKimliginDosyasiKopyalanirsaAcilmaz() {
        depo.anahtarYaz(K1, 1, "x", anahtar())
        File(kok, "$K1.anahtar").copyTo(File(kok, "$K2.anahtar"))
        assertEquals("bozuk", tur { depo.anahtarOku(K2) })
        assertEquals("tamam", tur { depo.anahtarOku(K1) })
    }

    @Test
    fun bozukKirpikVeAnahtarKaybiBozuk() {
        depo.anahtarYaz(K1, 1, "x", anahtar())
        val d = File(kok, "$K1.anahtar")
        val iyi = d.readBytes()
        d.writeBytes(iyi.copyOf(iyi.size - 1))
        assertEquals("bozuk", tur { depo.anahtarOku(K1) })
        d.writeBytes(iyi.copyOf().also { it[20] = (it[20].toInt() xor 1).toByte() })
        assertEquals("bozuk", tur { depo.anahtarOku(K1) })
        d.writeBytes(ByteArray(0))
        assertEquals("bozuk", tur { depo.anahtarOku(K1) })
        d.writeBytes(ByteArray(100000))
        assertEquals("bozuk", tur { depo.anahtarOku(K1) })
        d.writeBytes(iyi)
        assertEquals("tamam", tur { depo.anahtarOku(K1) })
        // Keystore anahtari kaybolmus (ör. uygulama verisi geri yuklenmis): kayit acilamaz.
        assertEquals("bozuk", tur { KasaDeposu(kok, BellekSarici(ByteArray(32) { 9 })).anahtarOku(K1) })
    }

    @Test
    fun disktekiDosyadaDuzAnahtarYok() {
        val k = anahtar(0x61)     // yazdirilabilir baytlar: 'a'..
        depo.anahtarYaz(K1, 1, "SINAMA-AD", k)
        depo.sayacYaz(K1, 42)
        for (ad in agac()) {
            val icerik = File(ust, ad).readBytes()
            assertFalse(ad, Sinama.icerir(icerik, k))
            assertFalse(ad, Sinama.icerir(icerik, k.copyOfRange(0, 8)))
            assertFalse(ad, Sinama.icerir(icerik, b64.encode(k).copyOfRange(0, 12)))
            assertFalse(ad, Sinama.icerir(icerik, "SINAMA-AD".toByteArray()))
            assertFalse(ad, Sinama.icerir(ad.toByteArray(), b64.encodeToString(k).take(8).toByteArray()))
        }
    }

    @Test
    fun yarimYazimKalintisiKaydiEtkilemez() {
        depo.anahtarYaz(K1, 1, "x", anahtar())
        File(kok, "$K1.anahtar.gecici").writeBytes(ByteArray(10))
        assertArrayEquals(anahtar(), depo.anahtarOku(K1).anahtar)
        assertEquals(1, depo.liste().size)
        depo.anahtarYaz(K1, 1, "x", anahtar(0x30))
        assertEquals(listOf("files/kasa/$K1.anahtar"), agac())
    }

    @Test
    fun listeAnahtarIcermez() {
        assertEquals(emptyList<Any>(), komut.liste()["kayitlar"])
        depo.anahtarYaz(K2, 5, "Tablet", anahtar(0x41))
        depo.anahtarYaz(K1, 2, "Telefon", anahtar(0x61))
        depo.sayacYaz(K1, 9)
        File(kok, "not.txt").writeText("x")
        File(kok, "KOTU.anahtar").writeText("x")
        val l = komut.liste()
        assertEquals(
            mapOf("kayitlar" to listOf(
                mapOf("kimlik" to K1, "n" to 2, "ad" to "Telefon"),
                mapOf("kimlik" to K2, "n" to 5, "ad" to "Tablet"),
            )), l)
        val metin = l.toString()
        assertFalse(metin.contains("anahtar"))
        assertFalse(metin.contains(b64.encodeToString(anahtar(0x61)).take(10)))
    }

    @Test
    fun listeBozukKaydiGizlemez() {
        depo.anahtarYaz(K1, 2, "Telefon", anahtar())
        File(kok, "$K2.anahtar").writeBytes(ByteArray(70))
        assertEquals(
            listOf(mapOf("kimlik" to K1, "n" to 2, "ad" to "Telefon"), mapOf("kimlik" to K2, "bozuk" to true)),
            komut.liste()["kayitlar"])
    }

    @Test
    fun silSonrasiYokVeSayacSifir() {
        depo.anahtarYaz(K1, 1, "x", anahtar())
        depo.anahtarYaz(K2, 1, "y", anahtar())
        depo.sayacYaz(K1, 5000)
        depo.sayacYaz(K2, 6000)
        File(kok, "$K1.sayac.gecici").writeText("x")
        depo.sil(K1)
        assertEquals("yok", tur { depo.anahtarOku(K1) })
        assertEquals(0L, depo.sayacOku(K1))
        assertEquals(listOf("files/kasa/$K2.anahtar", "files/kasa/$K2.sayac"), agac())
        // Baska kayit duruyor: sarma anahtari YOK EDILMEZ.
        assertEquals(0, sarici.yokEtSayisi)
        assertEquals(6000L, depo.sayacOku(K2))
        assertEquals("tamam", tur { depo.anahtarOku(K2) })
        depo.sil(K1)                                   // yinelenen silme zararsiz
        assertEquals(0, sarici.yokEtSayisi)
        depo.sil(K2)
        assertEquals(1, sarici.yokEtSayisi)            // son kayit: sarma anahtari da gider
        assertEquals(emptyList<String>(), agac())
    }

    @Test
    fun bozukSayacSilIleKurtarilir() {
        depo.sayacYaz(K1, 5)
        File(kok, "$K1.sayac").writeText("5")
        assertEquals("bozuk", tur { depo.sayacOku(K1) })
        depo.sil(K1)
        assertEquals(0L, depo.sayacOku(K1))
    }

    @Test
    fun sayaclarKimligeGoreAyri() {
        assertEquals(0L, depo.sayacOku(K1))
        depo.sayacYaz(K1, 100)
        assertEquals(0L, depo.sayacOku(K2))
        assertEquals("geri", tur { depo.sayacYaz(K1, 99) })
        assertEquals(50L, depo.sayacYaz(K2, 50))
    }

    // ---- Komut katmani (eklentinin govdesi) ----

    @Test
    fun komutGidisDonus() {
        val a64 = b64.encodeToString(anahtar())
        assertEquals(emptyMap<String, Any>(), komut.anahtarYaz(K1, 4, "Telefon", a64))
        assertEquals(mapOf("kimlik" to K1, "n" to 4, "ad" to "Telefon", "anahtar" to a64), komut.anahtarOku(K1))
        assertEquals(mapOf("isaret" to "0"), komut.sayacOku(K1))
        assertEquals(mapOf("isaret" to "1759500004096"), komut.sayacYaz(K1, "1759500004096"))
        assertEquals(mapOf("isaret" to "1759500004096"), komut.sayacOku(K1))
        assertEquals("geri", tur { komut.sayacYaz(K1, "1759500004095") })
        assertEquals(emptyMap<String, Any>(), komut.sil(K1))
        assertEquals("yok", tur { komut.anahtarOku(K1) })
        assertEquals(mapOf("isaret" to "0"), komut.sayacOku(K1))
    }

    @Test
    fun komutEksikVeBozukGirdiBicim() {
        val a64 = b64.encodeToString(anahtar())
        assertEquals("bicim", tur { komut.anahtarYaz(K1, null, "x", a64) })
        assertEquals("bicim", tur { komut.anahtarYaz(K1, 1, null, a64) })
        assertEquals("bicim", tur { komut.anahtarYaz(K1, 1, "x", null) })
        assertEquals("bicim", tur { komut.anahtarYaz(null, 1, "x", a64) })
        assertEquals("bicim", tur { komut.anahtarYaz(K1, 1, "x", "base64 degil!") })
        assertEquals("bicim", tur { komut.anahtarYaz(K1, 1, "x", b64.encodeToString(ByteArray(31) { 7 })) })
        assertEquals("bicim", tur { komut.anahtarYaz(K1, 1, "x", b64.encodeToString(ByteArray(33) { 7 })) })
        assertEquals("bicim", tur { komut.anahtarYaz(K1, 1, "x", "") })
        for (i in listOf(null, "", "-1", " 5", "5 ", "12345678901234567890", "9223372036854775808", "1.5")) {
            assertEquals("isaret: $i", "bicim", tur { komut.sayacYaz(K1, i) })
        }
        assertEquals(emptyList<String>(), agac())
    }

    @Test
    fun beklenmeyenIstisnaIcHataOlur_mesajSizmaz() {
        val patlak = KasaKomut(KasaDeposu(kok, sarici) { throw IllegalStateException("GIZLI-AYRINTI") })
        assertEquals("ic-hata", tur { patlak.sil(K1) })
    }
}
