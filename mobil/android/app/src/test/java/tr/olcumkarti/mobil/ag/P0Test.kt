package tr.olcumkarti.mobil.ag

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Collections
import java.util.concurrent.atomic.AtomicInteger

class P0Test {
    @Test
    fun ilkDenemedeBasari_beklemeYok() {
        val bekleme = ArrayList<Long>()
        val p = P0({ 204 }, { bekleme.add(it) })
        assertEquals(1, p.adresiDene("a"))
        assertTrue(bekleme.isEmpty())
    }

    @Test
    fun mesgul503VeAgHatasiYenidenDenenir_150_300_450() {
        val bekleme = ArrayList<Long>()
        val yanit = ArrayDeque(listOf(503, -1, 503, 204))
        val p = P0({ val k = yanit.removeFirst(); if (k < 0) throw AgHatasi("baglanti") else k }, { bekleme.add(it) })
        assertEquals(4, p.adresiDene("a"))
        assertEquals(listOf(150L, 300L, 450L), bekleme)
    }

    @Test
    fun enFazlaDortDeneme_sonraVazgecer() {
        val sayac = AtomicInteger(0)
        val bekleme = ArrayList<Long>()
        val p = P0({ sayac.incrementAndGet(); 503 }, { bekleme.add(it) })
        assertEquals(0, p.adresiDene("a"))
        assertEquals(4, sayac.get())
        assertEquals(listOf(150L, 300L, 450L), bekleme)     // son denemeden sonra bekleme yok
    }

    @Test
    fun kartDegilseYenidenDenenmez() {
        for (kod in listOf(400, 403, 404, 500, 302)) {
            val sayac = AtomicInteger(0)
            val p = P0({ sayac.incrementAndGet(); kod }, { })
            assertEquals("kod $kod", 0, p.adresiDene("a"))
            assertEquals("kod $kod", 1, sayac.get())
        }
    }

    @Test
    fun butunAdreslereAyniAnda_ilkBasariDoner_asiliAdresBekletmez() {
        val baslayan = Collections.synchronizedList(ArrayList<String>())
        val p = P0({ adres ->
            baslayan.add(adres)
            when (adres) {
                "asili" -> { Thread.sleep(3000); 204 }
                "olu" -> throw AgHatasi("baglanti")
                else -> { Thread.sleep(40); 204 }
            }
        }, { Thread.sleep(it) })
        val t0 = System.nanoTime()
        val s = p.durdur(listOf("asili", "olu", "kart"))
        val ms = (System.nanoTime() - t0) / 1_000_000
        assertTrue(s.tamam)
        assertEquals("kart", s.adres)
        assertTrue("asili adres bekletti: $ms ms", ms < 500)
        assertTrue(baslayan.containsAll(listOf("asili", "olu", "kart")))
    }

    @Test
    fun hepsiBasarisiz_tamamYanlis_veToplamSureyiAsmaz() {
        val p = P0({ throw AgHatasi("baglanti") }, { })
        val s = p.durdur(listOf("a", "b"))
        assertFalse(s.tamam)
        assertEquals(null, s.adres)
        val asili = P0({ Thread.sleep(5000); 204 }, { })
        val t0 = System.nanoTime()
        assertFalse(asili.durdur(listOf("a"), toplamSureMs = 300).tamam)
        assertTrue((System.nanoTime() - t0) / 1_000_000 < 800)
    }

    @Test
    fun bosVeYinelenenAdres() {
        assertFalse(P0({ 204 }, { }).durdur(emptyList()).tamam)
        val sayac = AtomicInteger(0)
        assertTrue(P0({ sayac.incrementAndGet(); 204 }, { }).durdur(listOf("a", "a", "a")).tamam)
        Thread.sleep(50)
        assertEquals(1, sayac.get())
    }

    @Test
    fun hedefSabitleri() {
        assertEquals(4, P0.AZAMI_DENEME)
        assertEquals(listOf(150L, 300L, 450L), P0.ARALAR_MS.toList())
        assertEquals(800, P0.BAGLANTI_SURESI_MS)
    }
}
