package tr.olcumkarti.mobil.ag

import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.OutputStream
import java.net.HttpURLConnection
import java.net.InetAddress
import java.net.Proxy
import java.net.ServerSocket
import java.net.Socket
import java.net.URL
import java.util.concurrent.CopyOnWriteArrayList
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import kotlin.concurrent.thread

/** Kartin /akis ucu gibi davranan soket sunucusu: istek basliklarini okur, yaniti `isle` yazar. */
private class AkisSunucusu(private val isle: (yol: String, basliklar: Map<String, String>, cikis: OutputStream, soket: Socket) -> Unit) {
    private val soket = ServerSocket(0, 50, InetAddress.getByName("127.0.0.1"))
    val port: Int get() = soket.localPort
    val istekSayisi = AtomicInteger(0)

    init {
        thread(isDaemon = true) {
            while (!soket.isClosed) {
                val s = try { soket.accept() } catch (e: Exception) { break }
                thread(isDaemon = true) { try { s.use { tek(it) } } catch (_: Exception) {} }
            }
        }
    }

    private fun satir(s: Socket): String {
        val b = StringBuilder()
        while (true) {
            val c = s.getInputStream().read()
            if (c < 0 || c == '\n'.code) break
            if (c != '\r'.code) b.append(c.toChar())
        }
        return b.toString()
    }

    private fun tek(s: Socket) {
        val ilk = satir(s).split(" ")
        if (ilk.size < 2) return
        val bas = HashMap<String, String>()
        while (true) {
            val l = satir(s)
            if (l.isEmpty()) break
            val k = l.indexOf(':')
            if (k > 0) bas[l.substring(0, k).lowercase()] = l.substring(k + 1).trim()
        }
        istekSayisi.incrementAndGet()
        isle(ilk[1], bas, s.getOutputStream(), s)
    }

    fun kapat() = soket.close()
}

private const val AKIS_BASI = "HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nCache-Control: no-cache\r\nConnection: keep-alive\r\n\r\n"
private const val KART_ACILIS = "retry: 3000\n\nevent: kimlik\ndata: {\"jeton\":\"sinamajetonu\",\"surucu\":true}\n\n"

private fun OutputStream.yaz(metin: String) {
    write(metin.toByteArray(Charsets.UTF_8))
    flush()
}

private class Kayitci : Akis.Dinleyici {
    val olaylar = CopyOnWriteArrayList<String>()
    val bitis = CountDownLatch(1)
    val ilkSatir = CountDownLatch(1)

    override fun satirlar(satirlar: List<String>) {
        for (s in satirlar) olaylar.add("satir:$s")
        ilkSatir.countDown()
    }

    override fun durum(hal: String, tur: String?, kod: Int) {
        olaylar.add("durum:$hal" + (if (tur != null) ":$tur" else "") + (if (kod > 0) ":$kod" else ""))
        if (hal != "acik") bitis.countDown()
    }

    fun bitisler(): List<String> = olaylar.filter { it.startsWith("durum:") && it != "durum:acik" }
}

class AkisTest {
    private var sunucu: AkisSunucusu? = null
    private val ac: (String) -> HttpURLConnection = { URL(it).openConnection(Proxy.NO_PROXY) as HttpURLConnection }

    private fun sun(isle: (String, Map<String, String>, OutputStream, Socket) -> Unit): String {
        val s = AkisSunucusu(isle)
        sunucu = s
        return "http://127.0.0.1:${s.port}/akis?_c=1&_s=7&_i=ab"
    }

    @After
    fun bitir() { sunucu?.kapat() }

    @Test
    fun kartGibiAkis_satirlarSirayla_kimlikOlayiTasinmaz_baglantiBitinceKapandi() {
        val gorulen = HashMap<String, String>()
        var gorulenYol = ""
        val url = sun { yol, bas, cikis, _ ->
            gorulenYol = yol
            gorulen.putAll(bas)
            cikis.yaz(AKIS_BASI + KART_ACILIS)
            cikis.yaz("id: 1\ndata: D 12.0000 0.500000 6.00000 1.0000 0.0002778 1000 97 0 0\n\n")
            cikis.yaz(": kalp\n\n")
            cikis.yaz("id: 2\ndata: G 1 0 0 5 5 1 0 0 0 0 0 9 0 0 0\n\nid: 3\ndata: K 1 2 3\n\n")
        }
        val k = Kayitci()
        Akis(ac, k).calis(url)
        assertEquals(
            listOf(
                "durum:acik",
                "satir:D 12.0000 0.500000 6.00000 1.0000 0.0002778 1000 97 0 0",
                "satir:G 1 0 0 5 5 1 0 0 0 0 0 9 0 0 0",
                "satir:K 1 2 3",
                "durum:kapandi",
            ),
            k.olaylar.toList(),
        )
        assertFalse(k.olaylar.any { it.contains("jeton") })
        assertEquals("/akis?_c=1&_s=7&_i=ab", gorulenYol)
        assertEquals("1", gorulen["x-olcum"])
        assertEquals("text/event-stream", gorulen["accept"])
        assertEquals(HttpIstek.KULLANICI_ARACI, gorulen["user-agent"])
    }

    @Test
    fun doluKart_yalnizDoluBildirilir_acikDenmez() {
        val url = sun { _, _, cikis, _ -> cikis.yaz(AKIS_BASI + "event: dolu\ndata: 4\n\n") }
        val k = Kayitci()
        Akis(ac, k).calis(url)
        assertEquals(listOf("durum:dolu"), k.olaylar.toList())
    }

    @Test
    fun http200DisiKod_hataHttpVeKod() {
        val url = sun { _, _, cikis, _ -> cikis.yaz("HTTP/1.1 401 X\r\nConnection: close\r\nContent-Length: 0\r\n\r\n") }
        val k = Kayitci()
        Akis(ac, k).calis(url)
        assertEquals(listOf("durum:hata:http:401"), k.olaylar.toList())
    }

    @Test
    fun yonlendirmeIzlenmez() {
        val url = sun { _, _, cikis, _ -> cikis.yaz("HTTP/1.1 302 X\r\nLocation: http://127.0.0.1:1/akis\r\nConnection: close\r\nContent-Length: 0\r\n\r\n") }
        val k = Kayitci()
        Akis(ac, k).calis(url)
        assertEquals(listOf("durum:hata:http:302"), k.olaylar.toList())
        assertEquals(1, sunucu!!.istekSayisi.get())
    }

    @Test
    fun susanSunucu_okumaZamanAsimi() {
        assertEquals(40000, Akis.OKUMA_ZAMAN_ASIMI_MS)
        val url = sun { _, _, cikis, _ ->
            cikis.yaz(AKIS_BASI + KART_ACILIS)
            Thread.sleep(5000)
        }
        val k = Kayitci()
        val t0 = System.nanoTime()
        Akis(ac, k, okumaZamanAsimiMs = 300).calis(url)
        val ms = (System.nanoTime() - t0) / 1_000_000
        assertEquals(listOf("durum:acik", "durum:hata:zaman-asimi"), k.olaylar.toList())
        assertTrue("sure $ms ms", ms in 250..2500)
    }

    @Test
    fun kalpAtanSunucuZamanAsiminaDusmez() {
        val url = sun { _, _, cikis, _ ->
            cikis.yaz(AKIS_BASI + KART_ACILIS)
            for (i in 0 until 8) { Thread.sleep(150); cikis.yaz(": kalp\n\n") }        // 1.2 s, okuma suresi 400 ms
            cikis.yaz("data: D 1\n\n")
        }
        val k = Kayitci()
        Akis(ac, k, okumaZamanAsimiMs = 400).calis(url)
        assertEquals(listOf("durum:acik", "satir:D 1", "durum:kapandi"), k.olaylar.toList())
    }

    @Test
    fun kapat_blokluOkumayiHemenKeser_tekBitis_sonrasindaSatirYok() {
        val devam = CountDownLatch(1)
        val url = sun { _, _, cikis, _ ->
            cikis.yaz(AKIS_BASI + KART_ACILIS + "data: D 1\n\n")
            devam.await(5, TimeUnit.SECONDS)
            try { cikis.yaz("data: D 2\n\n") } catch (_: Exception) {}
        }
        val k = Kayitci()
        val akis = Akis(ac, k)
        val is_ = thread(isDaemon = true) { akis.calis(url) }
        assertTrue(k.ilkSatir.await(3, TimeUnit.SECONDS))
        val t0 = System.nanoTime()
        akis.kapat()
        assertEquals("kapat() donunce bitis bildirilmis olmali", listOf("durum:kapandi"), k.bitisler())
        is_.join(1000)
        val ms = (System.nanoTime() - t0) / 1_000_000
        assertFalse("okuma is parcacigi $ms ms sonra hala calisiyor", is_.isAlive)
        devam.countDown()
        Thread.sleep(200)
        assertEquals(listOf("durum:acik", "satir:D 1", "durum:kapandi"), k.olaylar.toList())
        akis.kapat()                                                         // ikinci kapat: yeni olay yok
        assertEquals(1, k.bitisler().size)
    }

    @Test
    fun calismadanOnceKapatilanAkisBaglanmaz() {
        val url = sun { _, _, cikis, _ -> cikis.yaz(AKIS_BASI + KART_ACILIS) }
        val k = Kayitci()
        val akis = Akis(ac, k)
        akis.kapat()
        akis.calis(url)
        assertEquals(listOf("durum:kapandi"), k.olaylar.toList())
        assertEquals(0, sunucu!!.istekSayisi.get())
    }

    @Test
    fun yolAkisDegilse_bicim_sunucuyaGidilmez() {
        val taban = sun { _, _, cikis, _ -> cikis.yaz(AKIS_BASI) }.substringBefore("/akis")
        for (kotu in listOf("$taban/komut", "$taban/akis/x", "$taban/akisx?_c=1", "$taban/", taban, "https://127.0.0.1/akis", "$taban/akis?a b", "")) {
            val k = Kayitci()
            Akis(ac, k).calis(kotu)
            assertEquals(kotu, listOf("durum:hata:bicim"), k.olaylar.toList())
        }
        assertEquals(0, sunucu!!.istekSayisi.get())
    }

    @Test
    fun baglantiKurucununHataTuruAynenBildirilir_baskaIstisnaBaglanti() {
        val k = Kayitci()
        Akis({ throw AgHatasi("wifi-yok") }, k).calis("http://127.0.0.1:9/akis")
        assertEquals(listOf("durum:hata:wifi-yok"), k.olaylar.toList())
        val k2 = Kayitci()
        Akis({ throw IllegalStateException("http://127.0.0.1:9/akis?_i=sinama") }, k2).calis("http://127.0.0.1:9/akis")
        assertEquals(listOf("durum:hata:baglanti"), k2.olaylar.toList())
    }

    @Test
    fun dinleyenYokkenBaglanti_hataBaglanti() {
        val s = ServerSocket(0, 1, InetAddress.getByName("127.0.0.1"))
        val port = s.localPort
        s.close()
        val k = Kayitci()
        Akis(ac, k).calis("http://127.0.0.1:$port/akis")
        assertEquals(listOf("durum:hata:baglanti"), k.olaylar.toList())
    }

    @Test
    fun devSatirAtilir_akisSurer() {
        val url = sun { _, _, cikis, _ ->
            cikis.yaz(AKIS_BASI + KART_ACILIS)
            cikis.yaz("data: " + "x".repeat(200000) + "\n\n")
            cikis.yaz("data: D 1\n\n")
        }
        val k = Kayitci()
        Akis(ac, k).calis(url)
        assertEquals(listOf("durum:acik", "satir:D 1", "durum:kapandi"), k.olaylar.toList())
    }
}
