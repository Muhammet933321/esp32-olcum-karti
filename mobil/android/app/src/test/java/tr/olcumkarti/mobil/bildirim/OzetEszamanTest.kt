package tr.olcumkarti.mobil.bildirim

import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.CyclicBarrier
import java.util.concurrent.atomic.AtomicInteger
import kotlin.concurrent.thread
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import tr.olcumkarti.mobil.kasa.AtomikYazim

/** Curutucu 5E K-8: servis ile yoklama ayni ozet dosyasini ayni anda yazarsa. */
class OzetEszamanTest {
    @get:Rule val gecici = TemporaryFolder()
    private val kimlik = "0123456789abcdef"

    private fun durum(o: Long) = mapOf<String, Any?>("c" to 1L, "a" to 3L, "t" to 1790000000L, "k" to 2L, "o" to o, "y" to 1L)

    @Test
    fun ayniHedefeEszamanliAtomikYazim_hataYok_hedefHepTamBirIcerik() {
        val hedef = File(gecici.newFolder("k"), "x.durum")
        val icerikler = (0 until 8).map { i -> ByteArray(2000 + 4000 * i) { ('a' + i).code.toByte() } }
        val hata = AtomicInteger(0)
        val bozuk = AtomicInteger(0)
        val kapi = CyclicBarrier(icerikler.size)
        val isler = icerikler.map { veri ->
            thread {
                kapi.await()
                repeat(60) {
                    try { AtomikYazim.yaz(hedef, veri) } catch (e: Exception) { hata.incrementAndGet() }
                    val okunan = try { hedef.readBytes() } catch (e: Exception) { null }
                    if (okunan != null && icerikler.none { it.contentEquals(okunan) }) bozuk.incrementAndGet()
                }
            }
        }
        isler.forEach { it.join() }
        assertEquals("yazim hatasi", 0, hata.get())
        assertEquals("yarim / karisik icerik", 0, bozuk.get())
        assertTrue(icerikler.any { it.contentEquals(hedef.readBytes()) })
    }

    @Test
    fun ozetGuncelle_okuDegistirYazTekParca_arayaGirenYazimEzilmez() {
        val kok = gecici.newFolder("kasa"); val d = BildirimDeposu(kok)
        d.durumYaz(kimlik, YoklamaDurumu(durum(0), false))
        // Iki is parcacigi ayni ozeti artirir: degistirme sirasinda oteki araya giremezse toplam TAM cikar.
        val iceride = AtomicInteger(0)
        val cakisma = AtomicInteger(0)
        val kapi = CyclicBarrier(4)
        val isler = (0 until 4).map {
            thread {
                kapi.await()
                repeat(25) {
                    BildirimDeposu(kok).durumGuncelle(kimlik) { onceki ->
                        if (iceride.incrementAndGet() != 1) cakisma.incrementAndGet()
                        Thread.sleep(1)
                        iceride.decrementAndGet()
                        YoklamaDurumu(durum((onceki!!.cevrimici!!["o"] as Long) + 1), false)
                    }
                }
            }
        }
        isler.forEach { it.join() }
        assertEquals(0, cakisma.get())
        assertEquals(100L, d.durumOku(kimlik)!!.cevrimici!!["o"])
    }

    @Test
    fun ozetGuncelle_nullDonerseOzetDegismez_ilkOkumadaNullVerir_kimlikDenetlenir() {
        val kok = gecici.newFolder("kasa"); val d = BildirimDeposu(kok)
        var gorulen: YoklamaDurumu? = YoklamaDurumu(null, true)
        d.durumGuncelle(kimlik) { gorulen = it; YoklamaDurumu(durum(81), true) }
        assertNull(gorulen)
        d.durumGuncelle(kimlik) { null }
        assertEquals(81L, d.durumOku(kimlik)!!.cevrimici!!["o"]); assertTrue(d.durumOku(kimlik)!!.kopuk)
        assertEquals("bicim", try { d.durumGuncelle("../x") { YoklamaDurumu(null, false) }; null } catch (e: ZarfHatasi) { e.tur })
    }

    @Test
    fun servisVeYoklama_ozetiYalnizTekParcaGunceller_kaynakta() {
        // Oku ve yaz arasina baska yazar girebilen eski kalip (durumYaz(durumOku...)) uretim kodunda KALMAMIS olmali.
        val kok = generateSequence(File("").absoluteFile) { it.parentFile }.first { File(it, "app/src/main/java").isDirectory }
        val dizin = File(kok, "app/src/main/java/tr/olcumkarti/mobil/bildirim")
        for (ad in listOf("IzlemeServisi.kt", "YoklamaIsi.kt")) {
            val metin = File(dizin, ad).readText()
            assertTrue(ad, "durumGuncelle(kimlik)" in metin)
            assertTrue(ad, "durumYaz(" !in metin && "durumOku(" !in metin)
        }
        assertEquals(2, File(dizin, "IzlemeServisi.kt").readText().split("durumGuncelle(kimlik)").size - 1)
    }
}
