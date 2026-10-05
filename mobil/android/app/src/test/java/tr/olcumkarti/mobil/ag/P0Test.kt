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
    fun butunAdreslereAyniAnda_asilAdres204VerinceHemenDoner_asiliAdresBekletmez() {
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
        val s = p.durdur(listOf("kart", "asili", "olu"))          // ILK adres asil
        val ms = (System.nanoTime() - t0) / 1_000_000
        assertTrue(s.tamam)
        assertEquals("kart", s.adres)
        assertEquals(listOf("kart"), s.basarili)
        assertTrue("asili adres bekletti: $ms ms", ms < 500)
        assertTrue(baslayan.containsAll(listOf("asili", "olu", "kart")))
    }

    @Test
    fun yalniz204Basaridir_baska2xxBasariDegilVeYenidenDenenmez() {
        for (kod in listOf(200, 201, 202, 203, 205, 206, 299)) {
            val sayac = AtomicInteger(0)
            val p = P0({ sayac.incrementAndGet(); kod }, { })
            assertEquals("kod $kod", 0, p.adresiDene("a"))
            assertEquals("kod $kod", 1, sayac.get())
            val s = P0({ kod }, { }).durdur(listOf("x"))
            assertFalse("kod $kod", s.tamam)
            assertTrue("kod $kod", s.basarili.isEmpty())
        }
        assertEquals(204, P0.BASARI_KODU)
        assertTrue(P0({ 204 }, { }).durdur(listOf("x")).tamam)
    }

    @Test
    fun baskaAdresinBasarisiAsilKartinYenidenDenemesiniKesmez() {
        // Asil kart ilk denemede mesgul (503); "baska" adres hemen 204 der. Kart 204 verene dek denenir
        // ve sonuc KARTIN adresidir.
        val kartDeneme = AtomicInteger(0)
        val p = P0({ adres ->
            if (adres == "kart") {
                Thread.sleep(30)
                if (kartDeneme.incrementAndGet() == 1) 503 else 204
            } else 204
        }, { Thread.sleep(it / 10) })
        val s = p.durdur(listOf("kart", "baska"))
        assertTrue(s.tamam)
        assertEquals("kart", s.adres)
        assertEquals(2, kartDeneme.get())
        assertEquals(setOf("kart", "baska"), s.basarili.toSet())
    }

    @Test
    fun asilBasarisizsaHepsiBitinceDoner_basariliListesiAsiliIcermez() {
        val p = P0({ adres ->
            when (adres) {
                "asil" -> throw AgHatasi("baglanti")
                "gec" -> { Thread.sleep(200); 204 }
                else -> 204
            }
        }, { })
        val s = p.durdur(listOf("asil", "baska", "gec"))
        assertTrue(s.tamam)
        assertEquals("baska", s.adres)                            // asil DEGIL: cagiran "baska-yanit" der
        assertEquals(setOf("baska", "gec"), s.basarili.toSet())    // gec biten de beklendi
        assertFalse(s.basarili.contains("asil"))
    }

    @Test
    fun kaliciHataYenidenDenenmez_geciciHataDenenir() {
        for (tur in P0.KALICI_HATALAR) {
            val sayac = AtomicInteger(0)
            val bekleme = ArrayList<Long>()
            val p = P0({ sayac.incrementAndGet(); throw AgHatasi(tur) }, { bekleme.add(it) })
            assertEquals(tur, 0, p.adresiDene("a"))
            assertEquals(tur, 1, sayac.get())
            assertTrue(tur, bekleme.isEmpty())
        }
        assertEquals(setOf("wifi-yok", "ozel-degil", "bicim", "ad-izinsiz", "cleartext"), P0.KALICI_HATALAR)
        for (tur in listOf("baglanti", "zaman-asimi", "ad-cozulmedi")) {
            val sayac = AtomicInteger(0)
            val p = P0({ sayac.incrementAndGet(); throw AgHatasi(tur) }, { })
            assertEquals(tur, 0, p.adresiDene("a"))
            assertEquals(tur, P0.AZAMI_DENEME, sayac.get())
        }
        // Wi-Fi kapaliyken dokunus: sonuc beklemeden gelir.
        val t0 = System.nanoTime()
        assertFalse(P0({ throw AgHatasi("wifi-yok") }).durdur(listOf("a", "b")).tamam)
        assertTrue((System.nanoTime() - t0) / 1_000_000 < 300)
    }

    @Test
    fun surenTuraBaglanir_yeniIsParcacigiAcmaz_turBitinceYeniTurBaslar() {
        val canli = AtomicInteger(0)
        val azami = AtomicInteger(0)
        val gonderme = AtomicInteger(0)
        val p0 = P0({ _ ->
            gonderme.incrementAndGet()
            val n = canli.incrementAndGet()
            azami.accumulateAndGet(n) { a, b -> maxOf(a, b) }
            try { Thread.sleep(300) } finally { canli.decrementAndGet() }
            204
        }, { })
        val tur = P0Tur(p0)
        val sonuclar = Collections.synchronizedList(ArrayList<P0.Sonuc>())
        val bitti = java.util.concurrent.CountDownLatch(20)
        for (i in 0 until 20) {                                   // 20 hizli dokunus x 3 adres
            tur.durdur(listOf("a", "b", "c")) { s -> sonuclar.add(s); bitti.countDown() }
            Thread.sleep(5)
        }
        assertTrue(bitti.await(3, java.util.concurrent.TimeUnit.SECONDS))
        assertEquals(20, sonuclar.size)                           // hicbir dokunus yanitsiz kalmaz
        assertTrue(sonuclar.all { it.tamam })
        assertTrue("es zamanli baglanti: ${azami.get()}", azami.get() <= 3)
        assertEquals(3, gonderme.get())
        // Tur bitti: yeni dokunus YENI tur baslatir (eski sonuc yeniden kullanilmaz).
        val ikinci = java.util.concurrent.CountDownLatch(1)
        tur.durdur(listOf("a", "b", "c")) { ikinci.countDown() }
        assertTrue(ikinci.await(3, java.util.concurrent.TimeUnit.SECONDS))
        Thread.sleep(400)
        assertEquals(6, gonderme.get())
    }

    @Test
    fun farkliAdresListesiSurenTuruBeklemez() {
        val p0 = P0({ adres -> if (adres == "yavas") { Thread.sleep(600); 204 } else 204 }, { })
        val tur = P0Tur(p0)
        val yavas = java.util.concurrent.CountDownLatch(1)
        val hizli = java.util.concurrent.CountDownLatch(1)
        tur.durdur(listOf("x", "yavas")) { yavas.countDown() }    // asil "x" hemen 204: tur biter
        tur.durdur(listOf("yavas")) { yavas.countDown() }
        val t0 = System.nanoTime()
        tur.durdur(listOf("hizli")) { hizli.countDown() }
        assertTrue(hizli.await(300, java.util.concurrent.TimeUnit.MILLISECONDS))
        assertTrue((System.nanoTime() - t0) / 1_000_000 < 300)
    }

    // olcum.local cozulemiyor / cozumu ASILI (Android'de .local cogu zaman calismaz): oteki adresler
    // BEKLEMEZ — ne gonderme ne sonuc.
    @Test
    fun adCozulemezseOtekiAdreslerBeklemez_asilVarken() {
        val gonderildi = java.util.concurrent.ConcurrentHashMap<String, Long>()
        val t0 = System.nanoTime()
        val p = P0({ adres ->
            gonderildi.putIfAbsent(adres, (System.nanoTime() - t0) / 1_000_000)
            if (adres == "olcum.local") { Thread.sleep(2000); throw AgHatasi("ad-cozulmedi") }
            Thread.sleep(40); 204
        }, { Thread.sleep(it) })
        val s = p.durdur(listOf("kart", "olcum.local", "ap"))
        val ms = (System.nanoTime() - t0) / 1_000_000
        assertTrue(s.tamam)
        assertEquals("kart", s.adres)
        assertTrue("sonuc ad cozumunu bekledi: $ms ms", ms < 500)
        for (a in listOf("kart", "olcum.local", "ap")) assertTrue("$a gec gonderildi: ${gonderildi[a]} ms", (gonderildi[a] ?: 9999) < 200)
    }

    @Test
    fun adCozulemezseOtekiAdreslerBeklemez_asilYokken() {
        // Kart henuz bulunmadi (bagli adres yok): liste adla BASLAR. Ad "asil" SAYILMAZ; ilk 204 sonuctur.
        val gonderildi = java.util.concurrent.ConcurrentHashMap<String, Long>()
        val t0 = System.nanoTime()
        val p = P0({ adres ->
            gonderildi.putIfAbsent(adres, (System.nanoTime() - t0) / 1_000_000)
            if (adres == "olcum.local") { Thread.sleep(2000); throw AgHatasi("ad-cozulmedi") }
            Thread.sleep(40); 204
        }, { Thread.sleep(it) })
        val s = p.durdur(listOf("olcum.local", "ap"), asilVar = false)
        val ms = (System.nanoTime() - t0) / 1_000_000
        assertTrue(s.tamam)
        assertEquals("ap", s.adres)
        assertTrue("sonuc ad cozumunu bekledi: $ms ms", ms < 500)
        assertTrue((gonderildi["ap"] ?: 9999) < 200)
        // asilVar = true (ilk adres asil) olsaydi sonuc ad cozumunu BEKLERDI: fark olculur.
        val t1 = System.nanoTime()
        val bekleyen = P0({ adres -> if (adres == "olcum.local") { Thread.sleep(600); throw AgHatasi("ozel-degil") } else 204 }, { })
            .durdur(listOf("olcum.local", "ap"))
        assertTrue(bekleyen.tamam)
        assertTrue((System.nanoTime() - t1) / 1_000_000 >= 550)
    }

    @Test
    fun asilYokkenTurAyriSayilir() {
        val p0 = P0({ adres -> if (adres == "yavas") { Thread.sleep(500); 503 } else 204 }, { })
        val tur = P0Tur(p0)
        val bitti = java.util.concurrent.CountDownLatch(1)
        val t0 = System.nanoTime()
        tur.durdur(listOf("yavas", "ap"), false) { s -> if (s.tamam && s.adres == "ap") bitti.countDown() }
        assertTrue(bitti.await(300, java.util.concurrent.TimeUnit.MILLISECONDS))
        assertTrue((System.nanoTime() - t0) / 1_000_000 < 300)
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
        assertEquals(4, P0.AZAMI_ADRES)
    }
}
