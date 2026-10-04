package tr.olcumkarti.mobil.ag

import java.net.URL

/**
 * KartAg'in kapisi: istenen URL -> baglanilacak URL (her zaman DOGRULANMIS IP ile yeniden kurulur).
 * Saf Kotlin (Android sinifi yok): JVM'de sinanir. `java.net.URL`'in hosgorusu hedefe TASINMAZ:
 * ad/port Hedef.ayir'in kati kuralindan gecer, baglanti adresi onun dondurdugunden kurulur.
 */
object HedefCoz {
    class Cozum(val url: String, val ip: String, val port: Int, val yerelDongu: Boolean)

    /**
     * @param yerelDongu yalniz hata ayiklama derlemesinde true (adb reverse ile sahte kart)
     * @param adCoz `olcum.local` icin IPv4 adres METINLERI (Wi-Fi agi uzerinden); atarsa ad-cozulmedi
     */
    fun coz(url: String, yerelDongu: Boolean, adCoz: (String) -> List<String>): Cozum {
        val u = try { URL(url) } catch (e: Exception) { throw AgHatasi("bicim") }
        if (u.protocol != "http" || u.userInfo != null || u.ref != null) throw AgHatasi("bicim")
        val port = if (u.port < 0) Hedef.VARSAYILAN_PORT else u.port
        val h = try {
            Hedef.ayir("${u.host}:$port", yerelDongu)
        } catch (e: Hedef.Hata) {
            throw AgHatasi(e.tur)
        }
        val dosya = u.file ?: ""
        if (dosya.any { it.code < 0x21 || it.code > 0x7e }) throw AgHatasi("bicim")
        if (h.ad == "127.0.0.1") return Cozum("http://127.0.0.1:${h.port}$dosya", h.ad, h.port, true)
        var ip = h.ad
        if (h.ad == Hedef.KART_ADI) {
            val adresler = try { adCoz(h.ad) } catch (e: AgHatasi) { throw e } catch (e: Exception) { throw AgHatasi("ad-cozulmedi") }
            // Cozulen adres de AYNI kuraldan gecer: herkese acik IP donduren ad sunucusu ise yaramaz.
            ip = adresler.firstOrNull { Hedef.ozelAdres(it) } ?: throw AgHatasi("ozel-degil")
        }
        return Cozum("http://$ip:${h.port}$dosya", ip, h.port, false)
    }
}
