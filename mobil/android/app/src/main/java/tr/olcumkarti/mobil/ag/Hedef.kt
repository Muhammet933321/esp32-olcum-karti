package tr.olcumkarti.mobil.ag

/**
 * Kart adresi kurali (tasarim A3, A5, S5): uygulama YALNIZ ozel (RFC 1918) ve baglanti-yerel IPv4
 * adreslerine ve `olcum.local` adina gider. JS ikizi: src/cekirdek/hedef.js. Ikisi de
 * test/vektor/hedef.tsv'yi gecer. ASIL KAPI BURASI: aga cikan tek kod KartAg'dir.
 */
object Hedef {
    const val KART_ADI = "olcum.local"
    const val VARSAYILAN_PORT = 80

    class Hata(val tur: String) : Exception(tur)   // "bicim" | "ozel-degil" | "ad-izinsiz"

    data class Sonuc(val ad: String, val port: Int)

    private val PARCA = Regex("^(0|[1-9][0-9]{0,2})$")
    private val PORT = Regex("^[1-9][0-9]{0,4}$")
    private val BOZUK_IP = Regex("^[0-9][0-9a-fA-FxX.]*$")
    private val HTTP = Regex("^[hH][tT][tT][pP]://")
    private const val YASAK = "/?#@\\[]"

    /** Yalniz kati noktali-onluk: dort parca, ASCII rakam, bas sifir yok, 0..255. */
    private fun sekizliler(ip: String): IntArray? {
        val p = ip.split(".")
        if (p.size != 4) return null
        val s = IntArray(4)
        for (i in 0 until 4) {
            if (!PARCA.matches(p[i])) return null
            val n = p[i].toInt()
            if (n > 255) return null
            s[i] = n
        }
        return s
    }

    fun ozelAdres(ip: String): Boolean {
        val s = sekizliler(ip) ?: return false
        val a = s[0]
        val b = s[1]
        return a == 10 || (a == 172 && b in 16..31) || (a == 192 && b == 168) || (a == 169 && b == 254)
    }

    /** yerelDongu: YALNIZ hata ayiklama derlemesinde (adb reverse ile sahte kart). */
    fun ayir(metin: String, yerelDongu: Boolean = false): Sonuc {
        var s = metin.trim(' ')
        if (HTTP.containsMatchIn(s)) {
            s = s.substring(7)
            if (s.endsWith("/")) s = s.substring(0, s.length - 1)
        }
        if (s.isEmpty() || s.any { it.code < 0x21 || it.code > 0x7e || YASAK.indexOf(it) >= 0 }) throw Hata("bicim")
        var ad = s
        var port = VARSAYILAN_PORT
        val k = s.indexOf(':')
        if (k >= 0) {
            ad = s.substring(0, k)
            val p = s.substring(k + 1)
            if (!PORT.matches(p) || p.toInt() > 65535) throw Hata("bicim")
            port = p.toInt()
        }
        if (sekizliler(ad) != null) {
            if (ozelAdres(ad) || (yerelDongu && ad == "127.0.0.1")) return Sonuc(ad, port)
            throw Hata("ozel-degil")
        }
        if (ad.lowercase() == KART_ADI) return Sonuc(KART_ADI, port)
        if (ad.isEmpty() || BOZUK_IP.matches(ad)) throw Hata("bicim")
        throw Hata("ad-izinsiz")
    }
}
