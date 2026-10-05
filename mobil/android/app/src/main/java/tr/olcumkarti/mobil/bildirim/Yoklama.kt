package tr.olcumkarti.mobil.bildirim

/**
 * Iki yoklama arasinda saklanan ozet (`files/kasa/<kimlik>.durum`): kartin CEVRIMICI oldugu son kalici durum
 * mesaji (kayit durumu, oturum, acilis — olcum degeri ya da sir YOK) ve "karttan haber yok" bildirilmis mi.
 */
class YoklamaDurumu(val cevrimici: Map<String, Any?>?, val kopuk: Boolean) {
    /** Yalniz karar icin gereken alanlar yazilir (tamsayilar); gerisi diske gitmez. */
    fun json(): String {
        val d = cevrimici
        val alanlar = if (d == null) "null" else ALANLAR.mapNotNull { a -> (d[a] as? Long)?.let { "\"$a\":$it" } }.joinToString(",", "{", "}")
        return "{\"d\":$alanlar,\"kopuk\":$kopuk}"
    }

    companion object {
        val ALANLAR = listOf("c", "a", "t", "k", "o", "y")

        fun coz(metin: String?): YoklamaDurumu? {
            val m = try { DuzJson.nesne(metin ?: return null) } catch (e: JsonHatasi) { return null }
            @Suppress("UNCHECKED_CAST")
            val d = (m["d"] as? Map<String, Any?>)?.filter { it.key in ALANLAR && it.value is Long }
            return YoklamaDurumu(d, m["kopuk"] == true)
        }
    }
}

/**
 * 15 dakikalik YOKLAMA (tasarim A29 c, A30): araciya baglanip kalici durum mesajini okuyan tek seferlik
 * oturumun sonucunu, ONCEKI yoklamayla karsilastirip bildirime cevirir. Olay mesajlari kalici degildir —
 * uygulama kapaliyken biten kayit, durumun DEGISMESINDEN anlasilir:
 *   kayit suruyordu -> artik surmuyor / oturum degisti : "kayit bitti" (bellek dolduysa "bellek doldu")
 *   kayit suruyordu -> araci "kart cevrimdisi" diyor   : "karttan haber yok" (A33)
 *   haber yoktu     -> kart yeniden cevrimici           : ayni bildirim "yeniden baglandi" olur
 * Karar `BildirimKarar`in KENDISIYLE verilir (onceki durum sessizce yeniden oynatilir, sonra yeni durum
 * beslenir): metinler, etiketler ve sinif anahtarlari anlik izlemeyle AYNI — ayni olayi iki yol da gorurse
 * Android ayni etiketli bildirimi gunceller. Saf Kotlin.
 */
object Yoklama {
    class Sonuc(val durum: YoklamaDurumu?, val kayitSuruyor: Boolean)

    /**
     * @param onceki onceki yoklamanin ozeti (ilk yoklamada null: bildirim CIKMAZ, yalniz ozet saklanir)
     * @param simdi  okunan kalici durum mesaji; null = okunamadi (ozet DEGISMEZ, bildirim cikmaz)
     */
    fun degerlendir(onceki: YoklamaDurumu?, simdi: Map<String, Any?>?, acik: (String) -> Boolean, cikis: (Bildirim) -> Unit): Sonuc {
        if (simdi == null) return Sonuc(onceki, false)
        var saat = 0.0
        var sesli = false
        val k = BildirimKarar({ if (sesli) cikis(it) }, { saat }, acik)
        val eski = onceki?.cevrimici
        if (eski != null) {
            k.mqttMesaj("durum", eski)
            yerel(k, eski)
        }
        saat = ARALIK_S                                    // eski yerel haber "kart yerelde gorunuyor" SAYILMASIN (A36)
        if (eski != null && onceki.kopuk) k.mqttMesaj("durum", mapOf("c" to 0L))      // SESSIZ: zaten bildirilmisti
        sesli = true
        k.mqttMesaj("durum", simdi)
        val cevrimici = BildirimKarar.pyEsit(simdi["c"], 1)
        if (cevrimici) yerel(k, simdi)
        val yeni = if (cevrimici) YoklamaDurumu(simdi, false) else YoklamaDurumu(eski, k.baglanti != null)
        return Sonuc(yeni, cevrimici && k.kayitSuruyor() == true)
    }

    /**
     * Anlik izleme (servis) bir durum mesaji gordugunde ozeti gunceller: yoklama, servisin ZATEN bildirdigi
     * degisikligi bir daha bildirmesin. `kopuk`: servis o an "karttan haber yok" gosteriyor mu.
     */
    fun ozet(onceki: YoklamaDurumu?, icerik: Map<String, Any?>, kopuk: Boolean): YoklamaDurumu? = when {
        BildirimKarar.pyEsit(icerik["c"], 1) -> YoklamaDurumu(icerik, false)
        BildirimKarar.pyEsit(icerik["c"], 0) -> YoklamaDurumu(onceki?.cevrimici, kopuk)
        else -> onceki
    }

    private fun yerel(k: BildirimKarar, d: Map<String, Any?>) {
        val kod = d["k"] as? Long ?: return
        val oturum = d["o"] as? Long ?: return
        k.yerelG(kod, oturum)
    }

    /** Yeniden oynatilan durum ile yeni durum arasina konan sanal sure (yerel erisim penceresinden buyuk). */
    private const val ARALIK_S = 1000.0
}
