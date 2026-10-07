package tr.olcumkarti.mobil.ag

import java.net.Inet4Address
import java.net.NetworkInterface

/**
 * Telefon hotspot SAHIBIYKEN kartin oldugu yerel alt ag (2026-10-07, kullanici: "kart Honor'un
 * hotspotuna bagli ama uygulamada gorunmuyor"). O durumda telefonda istemci Wi-Fi AGI YOKTUR
 * (yalniz mobil veri); eklenti eskiden her istegi Wi-Fi agina baglamak istedigi icin "wifi-yok" ile
 * hic istek atmiyordu. Kart ise telefonun paylasim arayuzunun (Honor: wlan2 10.62.11.41/24)
 * alt aginda ve dogrudan bagli — cekirdek oraya Wi-Fi'ye baglamadan yonlendirir.
 *
 * Kural: YALNIZ paylasim arayuzu adlari (wlan / ap / swlan / softap + rakam); mobil veri
 * (rmnet, ccmni ...), VPN (tun), p2p sayilmaz. Onek 16..30 (daha genis = yanlis bildirim, daha dar
 * = konak yok). Telefonun kendi adresi hedef olamaz. Ozel adres kurali (Hedef.kt) ayrica gecerli.
 */
object YerelAg {
    data class Arayuz(val ad: String, val ip: String, val onek: Int)

    private val AD = Regex("^(wlan|ap|swlan|softap)\\d+$")

    fun paylasimAdiMi(ad: String): Boolean = AD.matches(ad)

    /** "a.b.c.d" -> 32 bit sayi; bicim disi -> null */
    fun sayi(ip: String): Long? {
        val p = ip.split(".")
        if (p.size != 4) return null
        var n = 0L
        for (x in p) {
            val v = x.toIntOrNull() ?: return null
            if (v !in 0..255 || x.length > 3) return null
            n = (n shl 8) or v.toLong()
        }
        return n
    }

    fun icinde(hedef: String, a: Arayuz): Boolean {
        if (a.onek !in 16..30) return false
        val h = sayi(hedef) ?: return false
        val s = sayi(a.ip) ?: return false
        if (h == s) return false
        val maske = (0xFFFFFFFFL shl (32 - a.onek)) and 0xFFFFFFFFL
        return (h and maske) == (s and maske)
    }

    fun paylasimda(hedef: String, liste: List<Arayuz> = arayuzler()): Boolean = liste.any { icinde(hedef, it) }

    /** Ayakta, IPv4'lu paylasim arayuzleri (hata = bos liste). */
    fun arayuzler(): List<Arayuz> = try {
        NetworkInterface.getNetworkInterfaces()?.toList().orEmpty()
            .filter { it.isUp && !it.isLoopback && paylasimAdiMi(it.name) }
            .flatMap { ni ->
                ni.interfaceAddresses.filter { it.address is Inet4Address }
                    .mapNotNull { ia -> ia.address.hostAddress?.let { Arayuz(ni.name, it, ia.networkPrefixLength.toInt()) } }
            }
    } catch (e: Exception) {
        emptyList()
    }
}
