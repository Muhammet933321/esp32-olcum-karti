package tr.olcumkarti.mobil.depo

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File
import java.util.Calendar

class KartDepoTest {
    @get:Rule val gecici = TemporaryFolder()
    private val K = "0123456789abcdef"

    private fun depo(saat: Calendar? = null): KartDepo =
        if (saat == null) KartDepo(File(gecici.root, "kart")) else KartDepo(File(gecici.root, "kart"), { saat })

    private fun tur(islem: () -> Unit): String? = try { islem(); null } catch (e: DepoHatasi) { e.tur }

    @Test
    fun bosDepo_boySifir_okumaBos_durumYok() {
        val d = depo()
        assertEquals(0L, d.veriBoyu(K))
        assertEquals(0, d.veriOku(K, 0, 100).size)
        assertNull(d.durumOku(K))
        assertNull(d.kalOku(K))
        assertNull(d.veriDosyasi(K))
        assertFalse("okuma dizin yaratmaz", File(gecici.root, "kart/$K").exists())
    }

    @Test
    fun ekle_sonaEkler_boyDoner_parcaliOkumaAyniBaytlar() {
        val d = depo()
        assertEquals(3L, d.veriEkle(K, byteArrayOf(1, 2, 3)))
        assertEquals(5L, d.veriEkle(K, byteArrayOf(4, 5)))
        assertEquals(5L, d.veriEkle(K, ByteArray(0)))
        assertEquals(5L, d.veriBoyu(K))
        assertArrayEquals(byteArrayOf(1, 2, 3, 4, 5), d.veriOku(K, 0, 100))
        assertArrayEquals(byteArrayOf(2, 3), d.veriOku(K, 1, 2))
        assertArrayEquals(byteArrayOf(5), d.veriOku(K, 4, 100))
        assertEquals(0, d.veriOku(K, 5, 100).size)
        assertEquals(0, d.veriOku(K, 99, 100).size)
        // Diskteki dosya PC ile ayni ad ve AYNI baytlar (ek baslik / cerceve yok).
        assertArrayEquals(byteArrayOf(1, 2, 3, 4, 5), File(gecici.root, "kart/$K/kayitlar.kyt").readBytes())
        assertEquals("kayitlar.kyt", d.veriDosyasi(K)!!.name)
    }

    @Test
    fun kirp_kisaltir_uzatirsaSifirDoldurur() {
        val d = depo()
        d.veriEkle(K, byteArrayOf(1, 2, 3, 4, 5))
        d.veriKirp(K, 2)
        assertArrayEquals(byteArrayOf(1, 2), d.veriOku(K, 0, 100))
        d.veriKirp(K, 4)
        assertArrayEquals(byteArrayOf(1, 2, 0, 0), d.veriOku(K, 0, 100))
        d.veriKirp(K, 0)
        assertEquals(0L, d.veriBoyu(K))
        // Kirpmadan sonra ekleme yeni sonun ARDINA gider.
        d.veriEkle(K, byteArrayOf(9))
        assertArrayEquals(byteArrayOf(9), d.veriOku(K, 0, 100))
    }

    @Test
    fun durumVeKalibrasyon_atomik_geciciKalintiOkumayiEtkilemez() {
        val d = depo()
        d.durumYaz(K, "{\"son_sira\":1}".toByteArray())
        d.durumYaz(K, "{\"son_sira\":2}".toByteArray())
        assertEquals("{\"son_sira\":2}", String(d.durumOku(K)!!))
        val dizin = File(gecici.root, "kart/$K")
        assertFalse(File(dizin, "durum.json.gecici").exists())
        // Yarida kesilmis yazim: gecici dosyada cop var, asil dosya ESKI icerigin tamami.
        File(dizin, "durum.json.gecici").writeBytes("{\"son_si".toByteArray())
        assertEquals("{\"son_sira\":2}", String(d.durumOku(K)!!))
        d.durumYaz(K, "{\"son_sira\":3}".toByteArray())
        assertEquals("{\"son_sira\":3}", String(d.durumOku(K)!!))
        // Yazim GECICI dosyadan gecer: gecici yol yazilamazsa (dizin) hedefe HIC dokunulmaz, hata doner.
        File(dizin, "durum.json.gecici").delete()
        File(dizin, "durum.json.gecici").mkdir()
        assertEquals("yazilamadi", tur { d.durumYaz(K, "{\"son_sira\":4}".toByteArray()) })
        assertEquals("{\"son_sira\":3}", String(d.durumOku(K)!!))
        File(dizin, "durum.json.gecici").delete()
        d.kalYaz(K, byteArrayOf(7, 8))
        assertArrayEquals(byteArrayOf(7, 8), d.kalOku(K))
        assertEquals("{\"son_sira\":3}", String(d.durumOku(K)!!))       // dosyalar birbirini ezmez
    }

    @Test
    fun arsiv_zamanDamgaliAd_cakismadaNumara_icerikAyni() {
        val saat = Calendar.getInstance().apply { set(2026, Calendar.OCTOBER, 5, 7, 8, 9) }
        val d = depo(saat)
        assertEquals("kalibrasyon-20261005-070809.json", d.kalArsivle(K, byteArrayOf(1)))
        assertEquals("kalibrasyon-20261005-070809-1.json", d.kalArsivle(K, byteArrayOf(2)))
        assertEquals("kalibrasyon-20261005-070809-2.json", d.kalArsivle(K, byteArrayOf(3)))
        val dizin = File(gecici.root, "kart/$K")
        assertArrayEquals(byteArrayOf(1), File(dizin, "kalibrasyon-20261005-070809.json").readBytes())
        assertArrayEquals(byteArrayOf(2), File(dizin, "kalibrasyon-20261005-070809-1.json").readBytes())
        assertNull("arsiv asil dosya degildir", d.kalOku(K))
        assertEquals(3, d.boyutlar(K)["arsiv"])
    }

    @Test
    fun kimlikYalniz16OnaltilikHane_yolKacisiYok() {
        val d = depo()
        val kotu = listOf(null, "", "abc", "0123456789ABCDEF", "0123456789abcdeg", "0123456789abcdef0",
            "../../../../etc/x", "..", "0123456789abcde/", "0123456789abcdef/..", " 0123456789abcdef")
        for (k in kotu) {
            assertEquals("$k", "bicim", tur { d.veriBoyu(k) })
            assertEquals("$k", "bicim", tur { d.veriEkle(k, byteArrayOf(1)) })
            assertEquals("$k", "bicim", tur { d.veriOku(k, 0, 10) })
            assertEquals("$k", "bicim", tur { d.veriKirp(k, 0) })
            assertEquals("$k", "bicim", tur { d.durumYaz(k, byteArrayOf(1)) })
            assertEquals("$k", "bicim", tur { d.durumOku(k) })
            assertEquals("$k", "bicim", tur { d.kalYaz(k, byteArrayOf(1)) })
            assertEquals("$k", "bicim", tur { d.kalArsivle(k, byteArrayOf(1)) })
            assertEquals("$k", "bicim", tur { d.sifirla(k) })
            assertEquals("$k", "bicim", tur { d.veriDosyasi(k) })
        }
        // Hicbiri kokun DISINA ya da kokun icine dosya yazmadi.
        assertTrue((File(gecici.root, "kart").listFiles() ?: emptyArray()).isEmpty())
        assertTrue(gecici.root.list()!!.all { it == "kart" })
    }

    @Test
    fun sinirlar_okumaYazmaKirpma() {
        val d = depo()
        assertEquals("bicim", tur { d.veriOku(K, -1, 10) })
        assertEquals("bicim", tur { d.veriOku(K, 0, 0) })
        assertEquals("bicim", tur { d.veriOku(K, 0, KartDepo.OKUMA_AZAMI + 1) })
        assertEquals("bicim", tur { d.veriEkle(K, ByteArray(KartDepo.YAZMA_AZAMI + 1)) })
        assertEquals("bicim", tur { d.veriKirp(K, -1) })
        assertEquals("bicim", tur { d.veriKirp(K, KartDepo.KIRPMA_AZAMI + 1) })
        assertEquals("bicim", tur { d.durumYaz(K, ByteArray(KartDepo.KUCUK_AZAMI + 1)) })
        assertEquals(0L, d.veriBoyu(K))
        assertEquals(1 shl 20, KartDepo.OKUMA_AZAMI)
        // Tavanda yazim / okuma calisir.
        d.veriEkle(K, ByteArray(KartDepo.YAZMA_AZAMI) { (it % 251).toByte() })
        val b = d.veriOku(K, 0, KartDepo.OKUMA_AZAMI)
        assertEquals(KartDepo.OKUMA_AZAMI, b.size)
        assertEquals((1000 % 251).toByte(), b[1000])
    }

    @Test
    fun sifirla_yalnizOKartinDosyalari_sonraBos() {
        val d = depo()
        val oteki = "fedcba9876543210"
        d.veriEkle(K, byteArrayOf(1, 2))
        d.durumYaz(K, byteArrayOf(3))
        d.kalYaz(K, byteArrayOf(4))
        d.kalArsivle(K, byteArrayOf(5))
        d.veriEkle(oteki, byteArrayOf(9))
        assertEquals(2L, d.boyutlar(K)["veri"])
        assertEquals(5L, d.boyutlar(K)["toplam"])
        d.sifirla(K)
        assertEquals(0L, d.veriBoyu(K))
        assertNull(d.durumOku(K))
        assertNull(d.kalOku(K))
        assertFalse(File(gecici.root, "kart/$K").exists())
        assertArrayEquals(byteArrayOf(9), d.veriOku(oteki, 0, 10))
        d.sifirla(K)                                                    // yokken sifirlamak hata degil
        assertEquals(0L, d.boyutlar(K)["toplam"])
    }

    @Test
    fun sifirla_durumEnSonSilinir_yaridaKalirsaDurumYerinde() {
        val sira = ArrayList<String>()
        var izin = Int.MAX_VALUE
        val d = KartDepo(File(gecici.root, "kart"), { Calendar.getInstance() }) { f ->
            if (izin-- <= 0) false else { sira.add(f.name); f.delete() }
        }
        d.durumYaz(K, byteArrayOf(1)); d.veriEkle(K, byteArrayOf(2)); d.kalYaz(K, byteArrayOf(3)); d.kalArsivle(K, byteArrayOf(4))
        d.sifirla(K)
        assertEquals(5, sira.size)
        assertEquals("durum.json", sira[3])                       // dosyalarin SONUNCUSU
        assertEquals(K, sira[4])                                  // ardindan dizin
        // Yarida kalan silme: iki dosya gitti, ucuncude hata. durum.json YERINDE (esitleyici "depo kisa" der, durur).
        d.durumYaz(K, byteArrayOf(1)); d.veriEkle(K, byteArrayOf(2)); d.kalYaz(K, byteArrayOf(3))
        izin = 2
        assertEquals("yazilamadi", tur { d.sifirla(K) })
        assertArrayEquals(byteArrayOf(1), d.durumOku(K))
        assertEquals(0L, d.veriBoyu(K))
    }

    @Test
    fun yarimKuyruk_dosyadaKalir_depoIcerigeBakmaz() {
        // Ekleme yarida kesildi (elektrik): dosyada yarim kayit. Depo onu AYNEN verir; ileri sarma /
        // kirpma esitleyicinin isidir (esitle.js, A23) — depo sessizce "duzeltmez".
        val d = depo()
        d.veriEkle(K, byteArrayOf(1, 2, 3))
        File(gecici.root, "kart/$K/kayitlar.kyt").appendBytes(byteArrayOf(0xA5.toByte(), 2))
        assertEquals(5L, d.veriBoyu(K))
        assertArrayEquals(byteArrayOf(1, 2, 3, 0xA5.toByte(), 2), d.veriOku(K, 0, 100))
        d.veriKirp(K, 3)
        assertArrayEquals(byteArrayOf(1, 2, 3), d.veriOku(K, 0, 100))
    }
}
