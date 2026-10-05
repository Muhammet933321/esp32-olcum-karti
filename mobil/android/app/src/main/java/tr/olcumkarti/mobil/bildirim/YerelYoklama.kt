package tr.olcumkarti.mobil.bildirim

import tr.olcumkarti.mobil.ag.Hedef
import tr.olcumkarti.mobil.ag.HttpYanit

/**
 * "Ev interneti koptu, kart calisiyor" (tasarim A36): araci karti CEVRIMDISI derken kart yerel agda hala
 * gorunuyor mu? Servis bunu YALNIZ imzasiz `GET /eslestir/bilgi` ile yoklar (A15: servis imzalamaz, sayaca
 * dokunmaz) ve yanittaki kimligi eslestigi kartin kimligiyle karsilastirir.
 *  - yalniz araci "cevrimdisi" dedigi surece yoklanir (kartin olcum dongusu bosuna mesgul edilmez)
 *  - adres WebView'in son baglandigi adrestir (`<kimlik>.adres`); YALNIZ ozel / baglanti-yerel IPv4
 *    (ag/Hedef — sifresiz HTTP'nin sinirinin aynisi); ad cozulmez
 *  - yanit kucuk (<= GOVDE_AZAMI), kati JSON, kimlik TAM esit olmali; baska her sey "gorunmuyor"
 * Saf Kotlin: HTTP istegi enjekte, JVM'de sinanir. Hata disari cikmaz (gorunmuyor sayilir).
 */
class YerelYoklama(private val istek: (url: String, zamanAsimiMs: Int, azamiGovde: Int) -> HttpYanit) {

    fun kartGorunuyor(kimlik: String, adres: String?): Boolean {
        val url = url(adres) ?: return false
        return try {
            val y = istek(url, ZAMAN_ASIMI_MS, GOVDE_AZAMI)
            if (y.kod != 200 || y.govde.size > GOVDE_AZAMI) return false
            DuzJson.nesne(String(y.govde, Charsets.UTF_8))["kimlik"] == kimlik
        } catch (e: Exception) {
            false
        }
    }

    companion object {
        const val YOL = "/eslestir/bilgi"
        const val ARALIK_MS = 10_000L
        const val ZAMAN_ASIMI_MS = 2_000
        const val GOVDE_AZAMI = 1024
        const val ADRES_AZAMI = 21                    // "255.255.255.255:65535"

        /** Yoklama yalniz araci karti ACIKCA cevrimdisi dediginde (bilinmiyorken / cevrimiciyken degil). */
        fun gerekli(kartCevrimici: Boolean?): Boolean = kartCevrimici == false

        /** "ip[:port]" -> yoklanacak URL; ozel IPv4 degilse (ad dahil) null. */
        fun url(adres: String?): String? {
            if (adres == null) return null                // uzun / bicimsiz metni Hedef.ayir reddeder
            val h = try { Hedef.ayir(adres) } catch (e: Hedef.Hata) { return null }
            if (!Hedef.ozelAdres(h.ad)) return null
            return "http://${h.ad}:${h.port}$YOL"
        }
    }
}
