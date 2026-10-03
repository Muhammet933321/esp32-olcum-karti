package tr.olcumkarti.mobil.ag

import org.junit.After
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Before
import org.junit.Test
import java.io.OutputStream
import java.net.HttpURLConnection
import java.net.InetAddress
import java.net.Proxy
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.atomic.AtomicInteger
import kotlin.concurrent.thread

/** Android birim testi sinif yolunda JDK'nin HTTP sunucusu yok: kucuk bir soket sunucusu. */
private class KucukSunucu(private val isle: (yontem: String, yol: String, basliklar: Map<String, String>, govde: ByteArray, cikis: OutputStream) -> Unit) {
    private val soket = ServerSocket(0, 50, InetAddress.getByName("127.0.0.1"))
    val port: Int get() = soket.localPort

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
        val bas = HashMap<String, String>()
        while (true) {
            val l = satir(s)
            if (l.isEmpty()) break
            val k = l.indexOf(':')
            if (k > 0) bas[l.substring(0, k).lowercase()] = l.substring(k + 1).trim()
        }
        val n = bas["content-length"]?.toInt() ?: 0
        val govde = ByteArray(n)
        var okunan = 0
        while (okunan < n) {
            val r = s.getInputStream().read(govde, okunan, n - okunan)
            if (r < 0) break
            okunan += r
        }
        isle(ilk[0], ilk[1], bas, govde, s.getOutputStream())
    }

    fun kapat() = soket.close()
}

private fun OutputStream.yanit(kod: Int, basliklar: Map<String, String> = emptyMap(), govde: ByteArray = ByteArray(0)) {
    val b = StringBuilder("HTTP/1.1 $kod X\r\nConnection: close\r\nContent-Length: ${govde.size}\r\n")
    for ((a, d) in basliklar) b.append("$a: $d\r\n")
    b.append("\r\n")
    write(b.toString().toByteArray())
    write(govde)
    flush()
}

class HttpIstekTest {
    private lateinit var sunucu: KucukSunucu
    private lateinit var taban: String
    private val hedefeVaran = AtomicInteger(0)
    private val istek = HttpIstek { it.openConnection(Proxy.NO_PROXY) as HttpURLConnection }

    @Before
    fun kur() {
        sunucu = KucukSunucu { yontem, yol, bas, govde, c ->
            when (yol) {
                "/yanki" -> c.yanit(200, mapOf(
                    "X-Yontem" to yontem,
                    "X-Olcum-Geldi" to (bas["x-olcum"] ?: "yok"),
                    "X-Host-Geldi" to (bas["host"] ?: "yok"),
                ), govde)
                "/503" -> c.yanit(503, mapOf("X-Acilis" to "abc"), "mesgul".toByteArray())
                "/sessiz" -> Thread.sleep(3000)
                "/buyuk" -> {
                    c.write("HTTP/1.1 200 X\r\nConnection: close\r\n\r\n".toByteArray())
                    val p = ByteArray(4096)
                    repeat(64) { c.write(p) }
                    c.flush()
                }
                "/damla" -> {
                    c.write("HTTP/1.1 200 X\r\nConnection: close\r\n\r\n".toByteArray())
                    repeat(40) { c.write(1); c.flush(); Thread.sleep(100) }
                }
                "/yonlendir" -> c.yanit(302, mapOf("Location" to "$taban/hedef"))
                "/hedef" -> { hedefeVaran.incrementAndGet(); c.yanit(200) }
                else -> c.yanit(404)
            }
        }
        taban = "http://127.0.0.1:${sunucu.port}"
    }

    @After
    fun kapat() = sunucu.kapat()

    private fun tur(blok: () -> Unit): String = try {
        blok(); "hata-yok"
    } catch (e: AgHatasi) {
        e.tur
    }

    @Test
    fun getVePostGovdeBaslik() {
        val g = istek.yap("GET", "$taban/yanki", mapOf("X-Olcum" to "1"), null, 2000)
        assertEquals(200, g.kod)
        assertEquals("GET", g.basliklar["x-yontem"])
        assertEquals("1", g.basliklar["x-olcum-geldi"])
        assertEquals(0, g.govde.size)
        val veri = byteArrayOf(0, 1, 2, -1, 10, 13)
        val p = istek.yap("POST", "$taban/yanki", mapOf("Content-Type" to "text/plain"), veri, 2000)
        assertEquals("POST", p.basliklar["x-yontem"])
        assertArrayEquals(veri, p.govde)
    }

    @Test
    fun hostBasligiCagirandanAlinmaz() {
        val y = istek.yap("GET", "$taban/yanki", mapOf("Host" to "evil.example"), null, 2000)
        assertEquals("127.0.0.1:${sunucu.port}", y.basliklar["x-host-geldi"])
    }

    @Test
    fun hataKoduIstisnaDegilYanit() {
        val y = istek.yap("GET", "$taban/503", emptyMap(), null, 2000)
        assertEquals(503, y.kod)
        assertEquals("abc", y.basliklar["x-acilis"])
        assertEquals("mesgul", String(y.govde))
    }

    @Test
    fun yanitVermeyenSunucuZamanAsimi() {
        val t0 = System.nanoTime()
        assertEquals("zaman-asimi", tur { istek.yap("GET", "$taban/sessiz", emptyMap(), null, 400) })
        assertTrue((System.nanoTime() - t0) / 1_000_000 < 1500)
    }

    @Test
    fun damlaDamlaYanitToplamSureyleKesilir() {
        val t0 = System.nanoTime()
        assertEquals("zaman-asimi", tur { istek.yap("GET", "$taban/damla", emptyMap(), null, 500) })
        assertTrue((System.nanoTime() - t0) / 1_000_000 < 1500)
    }

    @Test
    fun govdeSiniri() {
        assertEquals("govde-buyuk", tur { istek.yap("GET", "$taban/buyuk", emptyMap(), null, 2000, 64 * 1024) })
        assertEquals(262144, istek.yap("GET", "$taban/buyuk", emptyMap(), null, 2000, 512 * 1024).govde.size)
    }

    @Test
    fun yonlendirmeIzlenmez() {
        val y = istek.yap("GET", "$taban/yonlendir", emptyMap(), null, 2000)
        assertEquals(302, y.kod)
        assertEquals(0, hedefeVaran.get())
    }

    @Test
    fun kapaliPortBaglantiHatasi_veMesajSizmiyor() {
        try {
            istek.yap("GET", "http://127.0.0.1:9/x", emptyMap(), null, 800)
            fail("hata bekleniyordu")
        } catch (e: AgHatasi) {
            assertTrue(e.tur == "baglanti" || e.tur == "zaman-asimi")
            assertEquals(e.tur, e.message)          // mesaj = tur; adres/ayrinti yok
            assertEquals(null, e.cause)
        }
    }

    @Test
    fun yalnizGetVePost() {
        assertEquals("bicim", tur { istek.yap("DELETE", "$taban/yanki", emptyMap(), null, 500) })
    }
}
