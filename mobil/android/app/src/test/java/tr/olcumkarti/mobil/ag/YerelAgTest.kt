package tr.olcumkarti.mobil.ag

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Telefon hotspot SAHIBIYKEN (istemci Wi-Fi agi yok) kart telefonun kendi paylasim arayuzunun alt
 * aginda (2026-10-07, Honor: wlan2 10.62.11.41/24, kart 10.62.11.98). Eklenti o alt aga Wi-Fi'ye
 * baglamadan gider — YALNIZ dogrudan bagli paylasim arayuzu; mobil veri arayuzu asla.
 */
class YerelAgTest {
    private val hotspot = YerelAg.Arayuz("wlan2", "10.62.11.41", 24)

    @Test fun paylasimArayuzAdlari() {
        for (a in listOf("wlan0", "wlan2", "ap0", "swlan0", "softap0")) assertTrue(a, YerelAg.paylasimAdiMi(a))
        for (a in listOf("rmnet_data4", "ccmni0", "lo", "p2p0", "tun0", "wlan", "xwlan0")) assertFalse(a, YerelAg.paylasimAdiMi(a))
    }

    @Test fun ayniAltAgdaKartIcinde() {
        assertTrue(YerelAg.icinde("10.62.11.98", hotspot))
        assertTrue(YerelAg.icinde("10.62.11.1", hotspot))
    }

    @Test fun baskaAltAgTelefonunKendisiVeBicimDisiIcindeDegil() {
        assertFalse("baska alt ag", YerelAg.icinde("10.62.12.98", hotspot))
        assertFalse("ev agi", YerelAg.icinde("192.168.1.6", hotspot))
        assertFalse("telefonun kendi adresi", YerelAg.icinde("10.62.11.41", hotspot))
        assertFalse("ad", YerelAg.icinde("olcum.local", hotspot))
        assertFalse("bozuk", YerelAg.icinde("10.62.11.300", hotspot))
    }

    @Test fun cokGenisYaDaCokDarOnekReddedilir() {
        // /15'ten genis (yanlis bildirilen arayuz) ya da /31-/32 (konak yok) alt agi paylasim sayilmaz
        assertFalse(YerelAg.icinde("10.62.11.98", YerelAg.Arayuz("wlan2", "10.62.11.41", 8)))
        assertFalse(YerelAg.icinde("10.62.11.40", YerelAg.Arayuz("wlan2", "10.62.11.41", 31)))
        assertTrue(YerelAg.icinde("10.62.11.98", YerelAg.Arayuz("wlan2", "10.62.11.41", 16)))
    }

    @Test fun listeIcindeArama() {
        val liste = listOf(YerelAg.Arayuz("wlan0", "192.168.1.20", 24), hotspot)
        assertTrue(YerelAg.paylasimda("10.62.11.98", liste))
        assertTrue(YerelAg.paylasimda("192.168.1.6", liste))
        assertFalse(YerelAg.paylasimda("172.16.0.5", liste))
        assertFalse(YerelAg.paylasimda("10.62.11.98", emptyList()))
    }

    @Test fun ipSayi() {
        assertEquals(0x0A3E0B62L, YerelAg.sayi("10.62.11.98"))
        assertEquals(null, YerelAg.sayi("10.62.11"))
        assertEquals(null, YerelAg.sayi("a.b.c.d"))
    }
}
