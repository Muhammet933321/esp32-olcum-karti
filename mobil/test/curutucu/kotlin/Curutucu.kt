// CURUTUCU kaniti (5A-7). Gradle YOK: gercek Hedef.kt + HttpIstek.kt, kotlin derleyicisiyle dogrudan
// derlenir ve JVM'de (JDK 17) kosar. Yalniz 127.0.0.1. Kosma yordami: test/curutucu/OKU.txt
//
// `hazirlaSaf`, KartAgPlugin.hazirla'nin Android'e bagli OLMAYAN kisminin BIREBIR kopyasidir
// (URL ayristirma, sema/kullanici denetimi, Hedef.ayir, URL'nin yeniden kurulmasi). Ad cozumu ve
// Wi-Fi baglama burada yok (cihaz ister).
package tr.olcumkarti.mobil.ag

import java.io.File
import java.net.HttpURLConnection
import java.net.InetAddress
import java.net.Proxy
import java.net.ServerSocket
import java.net.Socket
import java.net.URL
import kotlin.concurrent.thread

fun hazirlaSaf(url: String, hataAyiklama: Boolean): String {
    val u = try { URL(url) } catch (e: Exception) { throw AgHatasi("bicim") }
    if (u.protocol != "http" || u.userInfo != null) throw AgHatasi("bicim")
    val port = if (u.port < 0) Hedef.VARSAYILAN_PORT else u.port
    val h = try {
        Hedef.ayir("${u.host}:$port", hataAyiklama)
    } catch (e: Hedef.Hata) {
        throw AgHatasi(e.tur)
    }
    if (h.ad == "127.0.0.1") return url
    val dosya = u.file ?: ""
    return "http://${h.ad}:${h.port}$dosya"
}

private fun hexCoz(h: String): String {
    val sb = StringBuilder()
    var i = 0
    while (i + 4 <= h.length) { sb.append(h.substring(i, i + 4).toInt(16).toChar()); i += 4 }
    return sb.toString()
}
private fun hexKodla(s: String) = s.map { "%04x".format(it.code) }.joinToString("")

/** Fark taramasi: girdi dosyasi satir basina "tur<TAB>hex(UTF-16)"; cikti ayni sirada sonuc. */
private fun fark(girdi: String, cikti: String) {
    val out = StringBuilder()
    for (l in File(girdi).readLines()) {
        if (l.isEmpty()) continue
        val p = l.split("\t")
        val tur = p[0]
        val s = hexCoz(if (p.size > 1) p[1] else "")
        val r = when (tur) {
            "ayir" -> try { val h = Hedef.ayir(s, false); "${h.ad}:${h.port}" } catch (e: Hedef.Hata) { "!${e.tur}" }
            "ozel" -> if (Hedef.ozelAdres(s)) "1" else "0"
            "url" -> try { "OK " + hexKodla(hazirlaSaf(s, false)) } catch (e: AgHatasi) { "!${e.tur}" } catch (e: Throwable) { "COKTU:" + e.javaClass.simpleName }
            else -> "?"
        }
        out.append(r).append('\n')
    }
    File(cikti).writeText(out.toString())
}

private class Sunucu(val isle: (Socket, String) -> Unit) {
    val soket = ServerSocket(0, 50, InetAddress.getByName("127.0.0.1"))
    val port get() = soket.localPort
    val istekler: MutableList<String> = java.util.Collections.synchronizedList(ArrayList<String>())
    init {
        thread(isDaemon = true) {
            while (!soket.isClosed) {
                val s = try { soket.accept() } catch (e: Exception) { break }
                thread(isDaemon = true) {
                    try {
                        s.use {
                            // istek basliklarini bos satira kadar oku
                            val sb = StringBuilder()
                            val g = it.getInputStream()
                            while (!sb.endsWith("\r\n\r\n")) { val c = g.read(); if (c < 0) break; sb.append(c.toChar()) }
                            istekler.add(sb.toString())
                            isle(it, sb.toString())
                        }
                    } catch (_: Exception) {}
                }
            }
        }
    }
}

private fun olc(ad: String, blok: () -> HttpYanit): Pair<String, Long> {
    val t0 = System.nanoTime()
    val r = try { "kod=" + blok().kod } catch (e: AgHatasi) { "AgHatasi(" + e.tur + ")" } catch (e: Throwable) { "BASKA:" + e.javaClass.simpleName }
    val ms = (System.nanoTime() - t0) / 1_000_000
    println("  $ad -> $r, $ms ms")
    return Pair(r, ms)
}

private fun govdeBoyu(ist: String) = Regex("(?i)content-length: (\\d+)").find(ist)?.groupValues?.get(1)?.toInt() ?: 0

private fun http() {
    val istek = HttpIstek { it.openConnection(Proxy.NO_PROXY) as HttpURLConnection }
    var kirmizi = 0
    fun iddia(ad: String, kosul: Boolean) { println((if (kosul) "  YESIL   " else "  KIRMIZI ") + ad); if (!kosul) kirmizi++ }

    println("[H1] Baslik evresinde damla damla yanit: toplam sure siniri isliyor mu? (zamanAsimiMs = 300)")
    val damla = Sunucu { s, _ ->
        val c = s.getOutputStream()
        c.write("HTTP/1.1 200 X\r\nConnection: close\r\n".toByteArray()); c.flush()
        // 4 s boyunca her 100 ms'de bir baslik BAYTI: readTimeout (300) hic dolmaz.
        c.write("X-Dolgu: ".toByteArray()); c.flush()
        repeat(40) { c.write('a'.code); c.flush(); Thread.sleep(100) }
        c.write("\r\nContent-Length: 2\r\n\r\nok".toByteArray()); c.flush()
    }
    val (r1, ms1) = olc("GET /baslik-damla") { istek.yap("GET", "http://127.0.0.1:${damla.port}/x", emptyMap(), null, 300) }
    iddia("H1: 300 ms sinirli istek en gec 3x300 = 900 ms'de doner (olculen $ms1 ms, sonuc $r1)", ms1 < 900)

    println("[H2] Govde evresi: asim ne kadar gec fark ediliyor? (zamanAsimiMs = 500; baslik 450. ms'de, sonra 450 ms'de bir bayt)")
    val gec = Sunucu { s, _ ->
        val c = s.getOutputStream()
        Thread.sleep(450)
        c.write("HTTP/1.1 200 X\r\nConnection: close\r\n\r\n".toByteArray()); c.flush()
        repeat(10) { Thread.sleep(450); c.write(1); c.flush() }
    }
    val (_, ms2) = olc("GET /gec") { istek.yap("GET", "http://127.0.0.1:${gec.port}/x", emptyMap(), null, 500) }
    iddia("H2: 500 ms sinirli istek 1.2x500 = 600 ms icinde doner (olculen $ms2 ms)", ms2 < 600)

    println("[H3] POST + 401 (kart yeniden basladi: 401 + X-Acilis) JVM'de yanit olarak donuyor mu?")
    val k401 = Sunucu { s, ist ->
        repeat(govdeBoyu(ist)) { s.getInputStream().read() }
        s.getOutputStream().write("HTTP/1.1 401 X\r\nConnection: close\r\nX-Acilis: abc\r\nContent-Length: 0\r\n\r\n".toByteArray())
    }
    val (r3, _) = olc("POST /komut (401, WWW-Authenticate YOK)") { istek.yap("POST", "http://127.0.0.1:${k401.port}/komut", mapOf("X-Olcum" to "1"), "G?".toByteArray(), 2000) }
    iddia("H3a: POST'a 401 yaniti kod=401 olarak doner (sonuc $r3)", r3 == "kod=401")
    val k401b = Sunucu { s, ist ->
        repeat(govdeBoyu(ist)) { s.getInputStream().read() }
        s.getOutputStream().write("HTTP/1.1 401 X\r\nConnection: close\r\nWWW-Authenticate: Basic realm=\"x\"\r\nX-Acilis: abc\r\nContent-Length: 0\r\n\r\n".toByteArray())
    }
    val (r3b, _) = olc("POST /komut (401 + WWW-Authenticate: Basic)") { istek.yap("POST", "http://127.0.0.1:${k401b.port}/komut", mapOf("X-Olcum" to "1"), "G?".toByteArray(), 2000) }
    iddia("H3b: POST'a 401 + WWW-Authenticate yaniti kod=401 olarak doner (sonuc $r3b)", r3b == "kod=401")
    val (r3c, _) = olc("GET (401 + WWW-Authenticate: Basic)") { istek.yap("GET", "http://127.0.0.1:${k401b.port}/x", emptyMap(), null, 2000) }
    iddia("H3c: GET'e 401 + WWW-Authenticate kod=401 (sonuc $r3c)", r3c == "kod=401")

    println("[H4] Baslik suzgeci: Host disinda tehlikeli basliklar / satir sonu")
    val yanki = Sunucu { s, ist ->
        repeat(minOf(govdeBoyu(ist), 2)) { s.getInputStream().read() }
        s.getOutputStream().write("HTTP/1.1 200 X\r\nConnection: close\r\nContent-Length: 0\r\n\r\n".toByteArray())
    }
    fun sonIstek() = yanki.istekler.lastOrNull()?.replace("\r\n", " | ") ?: "(istek ULASMADI)"
    olc("GET, baslik degeri icinde CRLF") { istek.yap("GET", "http://127.0.0.1:${yanki.port}/a", mapOf("X-A" to "1\r\nX-Enjekte: evet"), null, 1000) }
    println("    sunucunun gordugu: " + sonIstek())
    iddia("H4a: CRLF'li baslik degeri sunucuya ayri baslik olarak ULASMAZ", !(yanki.istekler.lastOrNull() ?: "").contains("\r\nX-Enjekte:"))
    val once = yanki.istekler.size
    olc("GET, yol icinde CRLF") { istek.yap("GET", "http://127.0.0.1:${yanki.port}/a HTTP/1.1\r\nX-Enjekte: evet\r\nX-B: ", emptyMap(), null, 1000) }
    println("    sunucunun gordugu: " + (if (yanki.istekler.size > once) sonIstek() else "(istek ULASMADI)"))
    iddia("H4b: yoldaki CRLF sunucuya ayri baslik olarak ULASMAZ", yanki.istekler.size == once || !yanki.istekler.last().contains("\r\nX-Enjekte:"))
    val once2 = yanki.istekler.size
    olc("POST govde 2 bayt; cagiran Content-Length: 999 + Transfer-Encoding + Connection + Cookie verdi") {
        istek.yap("POST", "http://127.0.0.1:${yanki.port}/a", mapOf("Content-Length" to "999", "Transfer-Encoding" to "chunked", "Connection" to "upgrade", "Cookie" to "a=b", "Accept-Encoding" to "identity"), "ab".toByteArray(), 1000)
    }
    println("    sunucunun gordugu: " + (if (yanki.istekler.size > once2) sonIstek() else "(istek ULASMADI)"))

    println(if (kirmizi == 0) "\nHTTP: hepsi yesil" else "\nHTTP: $kirmizi KIRMIZI")
}

fun main(a: Array<String>) {
    when (a.getOrNull(0)) {
        "fark" -> fark(a[1], a[2])
        "http" -> http()
        else -> println("kullanim: fark <girdi> <cikti> | http")
    }
}
