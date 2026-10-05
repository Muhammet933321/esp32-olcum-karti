package tr.olcumkarti.mobil.bildirim

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File

/** 5E-4b: bildirimin diskteki dosyalari, ayari, kanal eslemesi ve yeniden baglanma dongusu (saf JVM). */
class BildirimKabukTest {
    @get:Rule val gecici = TemporaryFolder()

    private val KIMLIK = "0123456789abcdef"
    private fun zarf(boy: Int = 120, dolgu: Int = 7): ByteArray = Zarf.SIHIR + ByteArray(boy - 4) { (it + dolgu).toByte() }
    private fun turu(islem: () -> Any?): String? = try { islem(); null } catch (e: ZarfHatasi) { e.tur }

    // ── zarf dosyasi (A31) ──────────────────────────────────────────────────────────────────────

    @Test
    fun zarf_yazOkuSil_oldugunGibi_ustuneYazilir() {
        val d = BildirimDeposu(gecici.newFolder("kasa"))
        assertNull(d.zarfOku(KIMLIK)); assertFalse(d.zarfVar(KIMLIK))
        d.zarfYaz(KIMLIK, zarf())
        assertArrayEquals(zarf(), d.zarfOku(KIMLIK)); assertTrue(d.zarfVar(KIMLIK))
        d.zarfYaz(KIMLIK, zarf(200, 9))
        assertArrayEquals(zarf(200, 9), d.zarfOku(KIMLIK))
        assertEquals(listOf(KIMLIK), d.kimlikler())
        d.zarfSil(KIMLIK)
        assertNull(d.zarfOku(KIMLIK)); assertEquals(emptyList<String>(), d.kimlikler())
        d.zarfSil(KIMLIK)                                                    // yokken silmek hata degil
    }

    @Test
    fun zarf_bicimiTutmayanYazilmaz_eskiDosyaKalir() {
        val kok = gecici.newFolder("kasa")
        val d = BildirimDeposu(kok)
        d.zarfYaz(KIMLIK, zarf())
        assertEquals("bicim", turu { d.zarfYaz(KIMLIK, ByteArray(120) { 1 }) })                       // sihir yok
        assertEquals("bicim", turu { d.zarfYaz(KIMLIK, zarf(Zarf.EN_AZ - 1)) })                        // kisa
        assertEquals("bicim", turu { d.zarfYaz(KIMLIK, zarf(BildirimDeposu.ZARF_AZAMI + 1)) })         // buyuk
        assertArrayEquals(zarf(), d.zarfOku(KIMLIK))
        d.zarfYaz(KIMLIK, zarf(Zarf.EN_AZ)); d.zarfYaz(KIMLIK, zarf(BildirimDeposu.ZARF_AZAMI))         // sinirlar kabul
        assertEquals(2048, BildirimDeposu.ZARF_AZAMI)
        assertEquals(listOf("$KIMLIK.zarf"), kok.list()!!.toList())                                    // gecici dosya kalmadi
    }

    @Test
    fun kimlikDosyaAdinaGider_gecersizKimlikHerIslemdeReddedilir() {
        val kok = gecici.newFolder("kasa")
        val d = BildirimDeposu(kok)
        for (k in listOf(null, "", "../../../etc/pwd", "0123456789ABCDEF", "0123456789abcde", "0123456789abcdef0", "0123456789abcde/")) {
            assertEquals("bicim", turu { d.zarfYaz(k, zarf()) })
            assertEquals("bicim", turu { d.zarfOku(k) })
            assertEquals("bicim", turu { d.zarfSil(k) })
            assertEquals("bicim", turu { d.olayOku(k) })
            assertEquals("bicim", turu { d.olayYaz(k, 1, 1) })
        }
        assertEquals(0, kok.list()!!.size)
    }

    @Test
    fun zarf_diskteBozulmusDosya_yokSayilir() {
        val kok = gecici.newFolder("kasa")
        val d = BildirimDeposu(kok)
        File(kok, "$KIMLIK.zarf").writeBytes(ByteArray(5))
        assertNull(d.zarfOku(KIMLIK))
        File(kok, "$KIMLIK.zarf").writeBytes(ByteArray(BildirimDeposu.ZARF_AZAMI + 1))
        assertNull(d.zarfOku(KIMLIK)); assertFalse(d.zarfVar(KIMLIK))
        File(kok, "baska.zarf").writeBytes(zarf())                           // kimlik bicimli olmayan ad listeye girmez
        assertEquals(emptyList<String>(), d.kimlikler().filter { it == "baska" })
    }

    @Test
    fun sonOlay_yazOku_bozukDosyaNull() {
        val kok = gecici.newFolder("kasa")
        val d = BildirimDeposu(kok)
        assertNull(d.olayOku(KIMLIK))
        d.olayYaz(KIMLIK, 3, 41)
        assertEquals(Pair(3L, 41L), d.olayOku(KIMLIK))
        d.olayYaz(KIMLIK, 4_000_000_000L, 1)                                 // acilis degeri 32 bit isaretsiz olabilir
        assertEquals(Pair(4_000_000_000L, 1L), d.olayOku(KIMLIK))
        File(kok, "$KIMLIK.olay").writeBytes(ByteArray(15))
        assertNull(d.olayOku(KIMLIK))
        File(kok, "$KIMLIK.olay").writeBytes(ByteArray(24) { 1 })                // uzun dosya da (ilk 16 bayt gecerli gorunse bile)
        assertNull(d.olayOku(KIMLIK))
        File(kok, "$KIMLIK.olay").writeBytes(ByteArray(16) { 0xff.toByte() })   // eksi sayi
        assertNull(d.olayOku(KIMLIK))
    }

    @Test
    fun eslesmeKaldirilinca_kasaSilmesiZarfiVeOlayiDaSiler() {
        val kok = gecici.newFolder("kasa")
        val d = BildirimDeposu(kok)
        d.zarfYaz(KIMLIK, zarf()); d.olayYaz(KIMLIK, 1, 2)
        d.zarfYaz("fedcba9876543210", zarf())
        val sarici = object : tr.olcumkarti.mobil.kasa.Sarici {
            override fun sar(duz: ByteArray, aad: ByteArray): ByteArray = duz
            override fun ac(sarili: ByteArray, aad: ByteArray): ByteArray = sarili
        }
        tr.olcumkarti.mobil.kasa.KasaDeposu(kok, sarici).sil(KIMLIK)
        assertNull(d.zarfOku(KIMLIK)); assertNull(d.olayOku(KIMLIK))
        assertEquals(listOf("fedcba9876543210"), d.kimlikler())             // baska kartinki durur
    }

    // ── ayar ────────────────────────────────────────────────────────────────────────────────────

    @Test
    fun ayar_varsayilan_anlikKapali_butunSiniflarAcik() {
        val a = BildirimAyar()
        assertFalse(a.anlik); assertEquals("tr", a.dil)
        assertEquals(listOf("kopuk", "bitti", "dolu", "esik", "yeniden_basladi", "kacirilan", "deneme"), BildirimAyar.SINIFLAR)
        assertTrue(BildirimAyar.SINIFLAR.all { a.acik(it) })
        assertEquals("{\"anlik\":false,\"kapali\":[],\"dil\":\"tr\"}", a.json())
    }

    @Test
    fun ayar_yazOku_gidisDonus_bozukVeGecersizAlanlarAyiklanir() {
        val dosya = File(gecici.newFolder("bildirim"), "ayar.json")
        assertFalse(BildirimAyar.oku(dosya).anlik)                           // dosya yok: varsayilan
        BildirimAyar.yaz(dosya, BildirimAyar(true, setOf("bitti", "deneme"), "en"))
        val a = BildirimAyar.oku(dosya)
        assertTrue(a.anlik); assertEquals(setOf("bitti", "deneme"), a.kapali); assertEquals("en", a.dil)
        assertFalse(a.acik("bitti")); assertTrue(a.acik("kopuk"))
        assertEquals("{\"anlik\":true,\"kapali\":[\"bitti\",\"deneme\"],\"dil\":\"en\"}", a.json())

        val b = BildirimAyar.coz("{\"anlik\":\"evet\",\"kapali\":[\"bitti\",\"yok-boyle\",5],\"dil\":\"de\"}")
        assertFalse(b.anlik); assertEquals(setOf("bitti"), b.kapali); assertEquals("tr", b.dil)
        for (bozuk in listOf(null, "", "{", "[]", "{\"anlik\":true,}")) {
            val c = BildirimAyar.coz(bozuk)
            assertFalse(c.anlik); assertEquals(emptySet<String>(), c.kapali)
        }
        dosya.writeText("x".repeat(2000))
        assertFalse(BildirimAyar.oku(dosya).anlik)
    }

    @Test
    fun kanal_uyariSesliSiniflar_gerisiBilgi() {
        assertEquals(listOf("uyari", "bilgi", "uyari", "uyari", "bilgi", "bilgi", "bilgi"), BildirimAyar.SINIFLAR.map { Kanal.sinifin(it) })
        assertEquals("bilgi", Kanal.sinifin("bilinmeyen"))
        assertEquals(setOf("izleme", "uyari", "bilgi"), setOf(Kanal.IZLEME, Kanal.UYARI, Kanal.BILGI))
    }

    // ── yeniden baglanma dongusu (A28, A31, A34) ────────────────────────────────────────────────

    private class Kosu(val bitis: String, val durumlar: List<String>, val beklemeler: List<Long>, val oturumSayisi: Int)

    private fun dongu(bitisler: List<IzlemeBitis>, baglanan: Set<Int> = emptySet(), beklerken: (Int, IzlemeDongusu) -> Unit = { _, _ -> }): Kosu {
        val durumlar = ArrayList<String>()
        val beklemeler = ArrayList<Long>()
        var i = 0
        lateinit var d: IzlemeDongusu
        d = IzlemeDongusu(
            oturum = { baglandi ->
                val b = bitisler[i]
                if (i in baglanan) baglandi()
                i++
                b
            },
            bekle = { ms -> beklemeler.add(ms); beklerken(beklemeler.size, d) },
            durum = { durumlar.add(it) },
        )
        return Kosu(d.calis(), durumlar, beklemeler, i)
    }

    @Test
    fun dongu_internetYokkenHizlaYenidenDener_baglaninca_izleniyor_kayitBitinceDurur() {
        val k = dongu(listOf(IzlemeBitis("ag"), IzlemeBitis("ag"), IzlemeBitis("zaman-asimi"), IzlemeBitis("gerek-kalmadi", baglandi = true)), baglanan = setOf(3))
        assertEquals("kayit-bitti", k.bitis)
        assertEquals(listOf("baglaniyor", "internet", "baglaniyor", "internet", "baglaniyor", "internet", "baglaniyor", "izleniyor"), k.durumlar)
        assertEquals(listOf(2_000L, 5_000L, 10_000L), k.beklemeler)
    }

    @Test
    fun dongu_baglanipKopanOturumBastanSayar() {
        val k = dongu(
            listOf(IzlemeBitis("ag"), IzlemeBitis("ag"), IzlemeBitis("ag"), IzlemeBitis("koptu", baglandi = true), IzlemeBitis("ag"), IzlemeBitis("durduruldu")),
            baglanan = setOf(3),
        )
        assertEquals("durduruldu", k.bitis)
        assertEquals(listOf(2_000L, 5_000L, 10_000L, 2_000L, 5_000L), k.beklemeler)
    }

    @Test
    fun dongu_ayarHatasindaDenemez_guvenVeAraciSeyrekDener() {
        for (tur in listOf("zarf", "adres", "kimlik-ret", "anahtar")) {
            val k = dongu(listOf(IzlemeBitis(tur), IzlemeBitis("ag")))
            assertEquals(tur, "ayar", k.bitis); assertEquals(1, k.oturumSayisi)
            assertEquals(emptyList<Long>(), k.beklemeler); assertEquals(listOf("baglaniyor"), k.durumlar)
        }
        val g = dongu(listOf(IzlemeBitis("tls"), IzlemeBitis("tls"), IzlemeBitis("ret", 3), IzlemeBitis("sure")))
        assertEquals("durduruldu", g.bitis)
        assertEquals(listOf(60_000L, 300_000L, 900_000L), g.beklemeler)
        assertEquals(listOf("baglaniyor", "guven", "baglaniyor", "guven", "baglaniyor", "araci", "baglaniyor"), g.durumlar)
    }

    @Test
    fun dongu_durdurBeklerkenYaDaOturumdaGelirse_yeniOturumAcilmaz() {
        val beklerken = dongu(listOf(IzlemeBitis("ag"), IzlemeBitis("ag"))) { _, d -> d.durdur() }
        assertEquals("durduruldu", beklerken.bitis); assertEquals(1, beklerken.oturumSayisi)

        lateinit var d: IzlemeDongusu
        var n = 0
        val durumlar = ArrayList<String>()
        d = IzlemeDongusu({ n++; d.durdur(); IzlemeBitis("zarf") }, { throw AssertionError("beklenmez") }, { durumlar.add(it) })
        assertEquals("durduruldu", d.calis())                                // durdurulan oturumun bitisi yorumlanmaz
        assertEquals(1, n)
        d.durdur()
        assertEquals(listOf("baglaniyor"), durumlar)
    }
}
