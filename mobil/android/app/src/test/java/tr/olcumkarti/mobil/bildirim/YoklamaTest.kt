package tr.olcumkarti.mobil.bildirim

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

/** 5E-4c: 15 dakikalik yoklama — iki kalici durum arasindaki farktan bildirim (A29 c, A30, A33). */
class YoklamaTest {
    @get:Rule val gecici = TemporaryFolder()

    private fun durum(k: Long, o: Long, a: Long = 3, c: Long = 1): Map<String, Any?> =
        mapOf("c" to c, "a" to a, "t" to 1790000000L, "k" to k, "o" to o, "y" to 1L, "d" to 5L, "e" to 0L, "f" to "A3-test")
    private val KOPTU = mapOf<String, Any?>("c" to 0L)
    private val BOS = 1L; private val KAYIT = 2L; private val DOLU = 3L; private val BEKLIYOR = 4L

    private class Kosu(val sonuc: Yoklama.Sonuc, val cikan: List<Bildirim>) {
        val anahtarlar get() = cikan.map { it.anahtar }
    }

    private fun kos(onceki: YoklamaDurumu?, simdi: Map<String, Any?>?, kapali: Set<String> = emptySet()): Kosu {
        val cikan = ArrayList<Bildirim>()
        return Kosu(Yoklama.degerlendir(onceki, simdi, { it !in kapali }, { cikan.add(it) }), cikan)
    }

    /** Art arda yoklamalar: her birinin ozeti bir sonrakine girer. */
    private fun zincir(vararg durumlar: Map<String, Any?>?): List<List<String>> {
        var ozet: YoklamaDurumu? = null
        return durumlar.map { d -> val k = kos(ozet, d); ozet = k.sonuc.durum; k.anahtarlar }
    }

    @Test
    fun ilkYoklama_bildirimYok_ozetSaklanir_kayitSuruyorBilgisiDoner() {
        val k = kos(null, durum(KAYIT, 81))
        assertEquals(emptyList<String>(), k.anahtarlar)
        assertTrue(k.sonuc.kayitSuruyor)
        assertEquals(81L, k.sonuc.durum!!.cevrimici!!["o"]); assertFalse(k.sonuc.durum!!.kopuk)
        assertFalse(kos(null, durum(BOS, 80)).sonuc.kayitSuruyor)
        assertTrue(kos(null, durum(BEKLIYOR, 80)).sonuc.kayitSuruyor)              // bekliyor da kayit sayilir
    }

    @Test
    fun kayitSuruyordu_artikSurmuyor_kayitBittiBirKez() {
        assertEquals(listOf(emptyList(), emptyList(), listOf("bld.kayit_bitti_yerel"), emptyList(), emptyList()),
            zincir(durum(KAYIT, 81), durum(KAYIT, 81), durum(BOS, 81), durum(BOS, 81), durum(BOS, 81)))
        val k = kos(YoklamaDurumu(durum(KAYIT, 81), false), durum(BOS, 81))
        assertEquals(mapOf<String, Any?>("oturum" to 81L), k.cikan[0].degerler)
        assertEquals("bitti", k.cikan[0].sinif); assertFalse(k.cikan[0].sessiz)
        assertFalse(k.sonuc.kayitSuruyor)
    }

    @Test
    fun oturumDegistiyse_eskisiBitmistir_yenisiSuruyor() {
        val k = kos(YoklamaDurumu(durum(KAYIT, 81), false), durum(KAYIT, 82))
        assertEquals(listOf("bld.kayit_bitti_yerel"), k.anahtarlar)
        assertEquals(81L, k.cikan[0].degerler["oturum"])
        assertTrue(k.sonuc.kayitSuruyor)
    }

    @Test
    fun bellekDolduysa_doluBildirimi_uyariSinifinda() {
        val k = kos(YoklamaDurumu(durum(KAYIT, 81), false), durum(DOLU, 81))
        assertEquals(listOf("bld.dolu_oturum"), k.anahtarlar)
        assertEquals("dolu", k.cikan[0].sinif)
        assertEquals("uyari", Kanal.sinifin(k.cikan[0].sinif))
    }

    @Test
    fun kayitSurerkenKartCevrimdisi_kartanHaberYokBirKez_donunceAyniEtiketle() {
        assertEquals(listOf(emptyList(), listOf("bld.kopuk"), emptyList(), emptyList(), listOf("bld.geri_kayit"), emptyList()),
            zincir(durum(KAYIT, 81), KOPTU, KOPTU, KOPTU, durum(KAYIT, 81), durum(KAYIT, 81)))
        val kopuk = kos(YoklamaDurumu(durum(KAYIT, 81), false), KOPTU)
        assertEquals("kopuk", kopuk.cikan[0].sinif); assertEquals("baglanti", kopuk.cikan[0].etiket)
        assertTrue(kopuk.sonuc.durum!!.kopuk); assertFalse(kopuk.sonuc.kayitSuruyor)
        assertEquals(81L, kopuk.sonuc.durum!!.cevrimici!!["o"])                    // son cevrimici durum korunur
        val geri = kos(kopuk.sonuc.durum, durum(KAYIT, 81))
        assertEquals("baglanti", geri.cikan[0].etiket)                             // AYNI bildirim guncellenir (A33)
        assertFalse(geri.sonuc.durum!!.kopuk)
    }

    @Test
    fun kopukkenKayitBitmisse_donunce_geriVeKayitBitti() {
        assertEquals(listOf(emptyList(), listOf("bld.kopuk"), listOf("bld.geri", "bld.kayit_bitti_yerel")),
            zincir(durum(KAYIT, 81), KOPTU, durum(BOS, 81)))
    }

    @Test
    fun kayitYokkenKartCevrimdisi_sessiz_ozetKopukDegil() {
        assertEquals(listOf(emptyList<String>(), emptyList(), emptyList()), zincir(durum(BOS, 81), KOPTU, durum(BOS, 81)))
        assertFalse(kos(YoklamaDurumu(durum(BOS, 81), false), KOPTU).sonuc.durum!!.kopuk)
        // Hic cevrimici gorulmemisken "cevrimdisi": alarm yok (kayit surdugu bilinmiyor).
        val ilk = kos(null, KOPTU)
        assertEquals(emptyList<String>(), ilk.anahtarlar); assertNull(ilk.sonuc.durum!!.cevrimici)
    }

    @Test
    fun okunamayanYoklama_ozetDegismez_bildirimYok() {
        val onceki = YoklamaDurumu(durum(KAYIT, 81), false)
        val k = kos(onceki, null)
        assertEquals(emptyList<String>(), k.anahtarlar)
        assertTrue(k.sonuc.durum === onceki); assertFalse(k.sonuc.kayitSuruyor)
        assertNull(kos(null, null).sonuc.durum)
        // Okunamayan yoklamadan SONRA gelen degisiklik kaybolmaz.
        assertEquals(listOf(emptyList(), emptyList(), listOf("bld.kayit_bitti_yerel")), zincir(durum(KAYIT, 81), null, durum(BOS, 81)))
    }

    @Test
    fun kapaliSinif_bildirilmez_amaOzetIlerler() {
        val k = kos(YoklamaDurumu(durum(KAYIT, 81), false), durum(BOS, 81), kapali = setOf("bitti"))
        assertEquals(emptyList<String>(), k.anahtarlar)
        assertEquals(BOS, k.sonuc.durum!!.cevrimici!!["k"])
        assertEquals(emptyList<String>(), kos(YoklamaDurumu(durum(KAYIT, 81), false), KOPTU, kapali = setOf("kopuk")).anahtarlar)
    }

    @Test
    fun ozet_jsonGidisDonus_yalnizKararAlanlari_bozukNull() {
        val o = YoklamaDurumu(durum(KAYIT, 81) + mapOf("gizli" to "x", "v" to 12.5), true)
        assertEquals("{\"d\":{\"c\":1,\"a\":3,\"t\":1790000000,\"k\":2,\"o\":81,\"y\":1},\"kopuk\":true}", o.json())
        val geri = YoklamaDurumu.coz(o.json())!!
        assertTrue(geri.kopuk)
        assertEquals(mapOf<String, Any?>("c" to 1L, "a" to 3L, "t" to 1790000000L, "k" to 2L, "o" to 81L, "y" to 1L), geri.cevrimici)
        assertEquals("{\"d\":null,\"kopuk\":false}", YoklamaDurumu(null, false).json())
        assertNull(YoklamaDurumu.coz("{\"d\":null,\"kopuk\":false}")!!.cevrimici)
        for (bozuk in listOf(null, "", "{", "[]")) assertNull(YoklamaDurumu.coz(bozuk))
        // Diskten gelen fazla / yanlis turde alan ayiklanir.
        assertEquals(mapOf<String, Any?>("k" to 2L), YoklamaDurumu.coz("{\"d\":{\"k\":2,\"o\":\"81\",\"x\":5},\"kopuk\":1}")!!.cevrimici)
        assertFalse(YoklamaDurumu.coz("{\"d\":{\"k\":2},\"kopuk\":1}")!!.kopuk)
        // Diskten okunan ozetle de ayni karar.
        assertEquals(listOf("bld.kayit_bitti_yerel"), kos(YoklamaDurumu.coz(YoklamaDurumu(durum(KAYIT, 81), false).json()), durum(BOS, 81)).anahtarlar)
    }

    @Test
    fun servisinOzeti_yoklamaServisinBildirdiginiYinelemez() {
        // Servis kayit surerken durumu gordu, sonra "bos" durumunu gordu (ve bitisi KENDISI bildirdi): ozet ilerledi.
        var ozet = Yoklama.ozet(null, durum(KAYIT, 81), false)
        ozet = Yoklama.ozet(ozet, durum(BOS, 81), false)
        assertEquals(emptyList<String>(), kos(ozet, durum(BOS, 81)).anahtarlar)
        // Servis "karttan haber yok" gosterirken kapandi: yoklama ayni seyi yeniden bildirmez, donusu bildirir.
        var o2 = Yoklama.ozet(null, durum(KAYIT, 81), false)
        o2 = Yoklama.ozet(o2, KOPTU, true)
        assertTrue(o2!!.kopuk); assertEquals(81L, o2.cevrimici!!["o"])
        assertEquals(emptyList<String>(), kos(o2, KOPTU).anahtarlar)
        assertEquals(listOf("bld.geri_kayit"), kos(o2, durum(KAYIT, 81)).anahtarlar)
        // Servis kartin dondugunu gorunce ozetteki "haber yok" bayragi KALKAR (yoksa yoklama donusu bir daha bildirir).
        val donmus = Yoklama.ozet(o2, durum(KAYIT, 81), false)!!
        assertFalse(donmus.kopuk)
        assertEquals(emptyList<String>(), kos(donmus, durum(KAYIT, 81)).anahtarlar)
        // Bicimsiz durum mesaji ozeti degistirmez.
        assertTrue(Yoklama.ozet(o2, mapOf("c" to "x"), false) === o2)
    }

    @Test
    fun ozetDosyasi_yazOku_kimlikDenetimi_eslesmeKalkincaSilinir() {
        val kok = gecici.newFolder("kasa")
        val d = BildirimDeposu(kok)
        val kimlik = "0123456789abcdef"
        assertNull(d.durumOku(kimlik))
        d.durumYaz(kimlik, YoklamaDurumu(durum(KAYIT, 81), true))
        assertEquals(81L, d.durumOku(kimlik)!!.cevrimici!!["o"]); assertTrue(d.durumOku(kimlik)!!.kopuk)
        d.durumYaz(kimlik, null)                                                   // null yazilmaz: eski ozet kalir
        assertEquals(81L, d.durumOku(kimlik)!!.cevrimici!!["o"])
        // Boyu asan dosya, icerigi GECERLI olsa da okunmaz (bosluk doldurulmus gecerli JSON).
        java.io.File(kok, "$kimlik.durum").writeText(YoklamaDurumu(durum(KAYIT, 81), true).json() + " ".repeat(BildirimDeposu.DURUM_AZAMI))
        assertNull(d.durumOku(kimlik))
        d.durumYaz(kimlik, YoklamaDurumu(durum(KAYIT, 81), true))
        assertEquals("bicim", try { d.durumOku("../x"); null } catch (e: ZarfHatasi) { e.tur })
        assertEquals("bicim", try { d.durumYaz("../x", YoklamaDurumu(null, false)); null } catch (e: ZarfHatasi) { e.tur })
        d.durumYaz(kimlik, YoklamaDurumu(durum(BOS, 81), false))
        val sarici = object : tr.olcumkarti.mobil.kasa.Sarici {
            override fun sar(duz: ByteArray, aad: ByteArray): ByteArray = duz
            override fun ac(sarili: ByteArray, aad: ByteArray): ByteArray = sarili
        }
        tr.olcumkarti.mobil.kasa.KasaDeposu(kok, sarici).sil(kimlik)
        assertNull(d.durumOku(kimlik))
    }
}
