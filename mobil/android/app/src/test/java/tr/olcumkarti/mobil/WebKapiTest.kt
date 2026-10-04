package tr.olcumkarti.mobil

import org.junit.Assert.assertEquals
import org.junit.Test

class WebKapiTest {
    private val at = "@"

    @Test
    fun yalnizPaketKokeniVeYerelSemalar() {
        val izinli = listOf(
            "https://localhost", "https://localhost/", "https://localhost/assets/index.js",
            "https://localhost/?x=1", "https://localhost/#/durum", "HTTPS://LOCALHOST/a",
            "data:image/png;base64,AAAA", "blob:https://localhost/1-2-3", "about:blank",
        )
        for (u in izinli) assertEquals(u, true, WebKapi.izinli(u))
    }

    @Test
    fun baskaHerAdresEngellenir() {
        val yasak = listOf(
            null, "", "http://example.com/", "https://example.com/", "http://localhost/",
            "http://192.168.1.5/eslestir/bilgi", "http://10.0.0.1/", "http://olcum.local/",
            "https://localhost.evil.com/", "https://localhost:8080/", "https://localhost${at}evil.com/",
            "https://localhostevil.com", "https://localhost\\evil.com/", "https://localhost/\nHost: x",
            "ftp://localhost/", "file:///data/data/x", "content://x", "javascript:alert(1)",
            "intent://x#Intent;end", "ws://example.com/", "wss://localhost.evil.com/", "//example.com/",
            "capacitor://localhost/",
        )
        for (u in yasak) assertEquals("$u", false, WebKapi.izinli(u))
    }
}
