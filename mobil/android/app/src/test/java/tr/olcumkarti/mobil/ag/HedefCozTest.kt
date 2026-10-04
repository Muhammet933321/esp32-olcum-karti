package tr.olcumkarti.mobil.ag

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class HedefCozTest {
    private val at = "@"
    private val cozmez: (String) -> List<String> = { throw IllegalStateException("ad cozulmemeliydi") }

    private fun tur(url: String, yerelDongu: Boolean = false, adCoz: (String) -> List<String> = cozmez): String = try {
        HedefCoz.coz(url, yerelDongu, adCoz).url
    } catch (e: AgHatasi) {
        "!${e.tur}"
    }

    @Test
    fun ozelIpAynenVeUrlIpIleYenidenKurulur() {
        assertEquals("http://192.168.1.7:80/eslestir/bilgi", tur("http://192.168.1.7/eslestir/bilgi"))
        assertEquals("http://10.0.0.5:8080/akis?_c=1&_s=2&_i=ab", tur("http://10.0.0.5:8080/akis?_c=1&_s=2&_i=ab"))
        assertEquals("http://192.168.4.1:80", tur("http://192.168.4.1"))
    }

    @Test
    fun herkeseAcikVeBozukHedefReddedilir() {
        assertEquals("!ozel-degil", tur("http://8.8.8.8/x"))
        assertEquals("!ozel-degil", tur("http://127.0.0.1:18080/x"))
        assertEquals("!ad-izinsiz", tur("http://evil.example/x"))
        assertEquals("!bicim", tur("https://192.168.1.7/x"))
        assertEquals("!bicim", tur("http://a${at}192.168.1.7/x"))
        assertEquals("!bicim", tur("http://192.168.1.7:80${at}8.8.8.8/x"))
        assertEquals("!bicim", tur("http://192.168.1.7/x#${at}8.8.8.8"))
        assertEquals("!bicim", tur("http://192.168.1.7/a b"))
        assertEquals("!bicim", tur("http://192.168.1.7/a\r\nHost: x"))
        assertEquals("!bicim", tur("http://0xC0A80101/x"))
        assertEquals("!bicim", tur("http:///x"))
        assertEquals("!bicim", tur("192.168.1.7/x"))
    }

    @Test
    fun yerelDonguYalnizSecenekle() {
        val c = HedefCoz.coz("http://127.0.0.1:18080/x", true, cozmez)
        assertTrue(c.yerelDongu)
        assertEquals("http://127.0.0.1:18080/x", c.url)
        assertFalse(HedefCoz.coz("http://192.168.1.7/x", true, cozmez).yerelDongu)
    }

    @Test
    fun adCozulurVeCozulenAdresDeKuraldanGecer() {
        assertEquals("http://192.168.1.7:80/x", tur("http://olcum.local/x") { listOf("192.168.1.7") })
        // Herkese acik adres donduren ad sunucusu: ret. Karisik yanitta ILK OZEL adres.
        assertEquals("!ozel-degil", tur("http://olcum.local/x") { listOf("8.8.8.8") })
        assertEquals("!ozel-degil", tur("http://olcum.local/x") { emptyList() })
        assertEquals("http://10.1.2.3:80/x", tur("http://OLCUM.LOCAL/x") { listOf("8.8.8.8", "10.1.2.3", "192.168.1.7") })
        assertEquals("!ozel-degil", tur("http://olcum.local/x") { listOf("192.168.1.7.evil", "0300.0250.1.1") })
        assertEquals("!ad-cozulmedi", tur("http://olcum.local/x") { throw java.net.UnknownHostException("x") })
        assertEquals("!wifi-yok", tur("http://olcum.local/x") { throw AgHatasi("wifi-yok") })
    }

    @Test
    fun ipHedefteAdCozucuHicCagrilmaz() {
        var cagri = 0
        HedefCoz.coz("http://192.168.1.7/x", false) { cagri++; listOf("8.8.8.8") }
        assertEquals(0, cagri)
    }
}
