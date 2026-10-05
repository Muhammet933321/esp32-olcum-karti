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
        // Cevrimici durum mesajinda kayit durumu / oturum OKUNAMIYORSA mesaj okunamamis sayilir (curutucu 5E
        // B10): ozet ezilmez, sonraki yoklama degisikligi yine yakalar.
        if (BildirimKarar.pyEsit(simdi["c"], 1) && (simdi["k"] !is Long || simdi["o"] !is Long)) return Sonuc(onceki, false)
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
        val cevrimici = BildirimKarar.pyEsit(simdi["c"], 1)
        if (cevrimici && eski != null) yenidenBasladi(k, eski, simdi)      // yeni durumdan ONCE: "son haber" eski saat kalsin
        k.mqttMesaj("durum", simdi)
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

    /**
     * Servis kayit durumunu YEREL akistan duydugunda (uygulama onde) ozeti ilerletir (curutucu 5E B4): servis
     * "kayit bitti"yi yerel yoldan bildirip kapandiysa, kartin MQTT durumu hic gelmemis olsa da yoklama ayni
     * bitisi 15 dakika sonra YENIDEN bildirmez.
     */
    fun ozetYerel(onceki: YoklamaDurumu?, kod: Long, oturum: Long): YoklamaDurumu =
        YoklamaDurumu((onceki?.cevrimici ?: mapOf("c" to 1L)) + mapOf("k" to kod, "o" to oturum), onceki?.kopuk ?: false)

    /**
     * Kart iki yoklama ARASINDA yeniden basladiysa (acilis numarasi `a` degisti) ve o sirada kayit suruyorduysa
     * (curutucu 5E K-13): kartin o acilista yayinladigi — kalici OLMAYAN — olay mesajinin karsiligi karar
     * katmanina verilir; metin, sinif (`yeniden_basladi`) ve etiket anlik izlemeyle AYNI olur.
     *   ayni oturum suruyor                     -> "yeniden basladi, kayit suruyor"
     *   pil / skop oturumu artik surmuyor        -> "yeniden basladi, ... kesildi" (bu turler acilista SURMEZ)
     *   olcum oturumu artik surmuyor             -> siradan "kayit bitti" (olcum acilista surer; sonradan bitmistir)
     */
    private fun yenidenBasladi(k: BildirimKarar, eski: Map<String, Any?>, simdi: Map<String, Any?>) {
        val ea = eski["a"] as? Long ?: return
        val ya = simdi["a"] as? Long ?: return
        val eo = eski["o"] as? Long ?: return
        if (ea == ya || eski["k"] !in BildirimKarar.KAYITTA) return
        val suruyor = simdi["k"] in BildirimKarar.KAYITTA && simdi["o"] == eo
        if (suruyor) k.mqttMesaj("olay", mapOf("n" to 1L, "a" to ya, "o" to "basladi", "devam" to 1L, "oturum" to eo))
        else if (eski["y"] in KESILEN_TURLER) k.mqttMesaj("olay", mapOf("n" to 1L, "a" to ya, "o" to "kayit_bitti", "sebep" to 5L, "oturum" to eo))
    }

    private fun yerel(k: BildirimKarar, d: Map<String, Any?>) {
        val kod = d["k"] as? Long ?: return
        val oturum = d["o"] as? Long ?: return
        k.yerelG(kod, oturum)
    }

    /** Yeniden oynatilan durum ile yeni durum arasina konan sanal sure (yerel erisim penceresinden buyuk). */
    private const val ARALIK_S = 1000.0

    /** Yeniden baslamada SURMEYEN oturum turleri: pil (2), skop (3) — kart bunlari "sebep 5" ile kapatir. */
    private val KESILEN_TURLER = setOf<Any?>(2L, 3L)
}
