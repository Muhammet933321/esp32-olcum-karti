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
    // Curutucu 5D B13: Capacitor'in dosya / icerik on ekleri uygulamanin okuyabildigi HER dosyayi verir.
    @Test
    fun capacitorDosyaOnEkleriKapali_yuzdeKacisiYoldaYok() {
        val yasak = listOf(
            "https://localhost/_capacitor_file_/data/user/0/x/files/kasa/a.bin",
            "https://localhost/_capacitor_file_/data/user/0/x/files/kart/0123456789abcdef/durum.json",
            "https://localhost/_capacitor_content_/media/external/file/1",
            "https://localhost/_CAPACITOR_FILE_/data/x", "https://localhost/_capacitor_http_interceptor_?u=x",
            "https://localhost/%5Fcapacitor_file_/data/x", "https://localhost/%5fcapacitor_file_/data/x",
            "https://localhost/_capacitor%5Ffile_/data/x", "https://localhost/a/..%2f_capacitor_file_/x",
            "https://localhost/assets/%2e%2e/x", "https://localhost/?u=%2F_capacitor_file_%2Fx",
            "https://localhost/x/_capacitor_file_/data",
        )
        for (u in yasak) assertEquals(u, false, WebKapi.izinli(u))
        // Kendi adreslerimiz ve depo adresi ACIK kalir; parcadaki (#) yuzde isareti yola sayilmaz.
        val izinli = listOf(
            "https://localhost/_depo/0123456789abcdef/kayitlar.kyt", "https://localhost/assets/kayit_isci-r8i5Zwg0.js",
            "https://localhost/index.html", "https://localhost/#/kayitlar/61536", "https://localhost/#/x%20y",
            "https://localhost/capacitor.js", "https://localhost/native-bridge.js",
        )
        for (u in izinli) assertEquals(u, true, WebKapi.izinli(u))
    }
}
