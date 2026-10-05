package tr.olcumkarti.mobil.bildirim

/** Kod -> metin (ceviri sozlugunden: `onek + kod`, yoksa `onek + "bilinmeyen"`). */
data class Kod(val onek: String, val kod: Any?)
/** Olcekli sayi: x / bolen, `basamak` ondalik; x tamsayi degilse "?". */
data class Sayi(val x: Any?, val bolen: Int, val basamak: Int)
/** Sure (ms) -> s:dd:ss; tamsayi degilse / eksi ise "?". */
data class Sure(val ms: Any?)
/** Ic ice metin (bld.kesildi'nin "son gorulme" eki): anahtar + unix saati. */
data class SaatEki(val anahtar: String, val unix: Long)

/**
 * Gosterilecek bildirim. `etiket` AYNI olan sonraki bildirim oncekini GUNCELLER (Android bildirim kimligi).
 * `anahtar` + `degerler` metni kurar (strings.xml, A43) — metin BURADA kurulmaz. `sessiz`: zaten gosterilmis
 * bir bildirimin daha ayrintili hali (ses / titresim yok).
 */
class Bildirim(val etiket: String, val sinif: String, val anahtar: String, val degerler: Map<String, Any?>, val sessiz: Boolean)

/**
 * MQTT + yerel haberleri bildirime ceviren KARAR katmani (tasarim A33–A36). Kartla ve gercek araciyla
 * sinanmis PC karsiliginin (`kopru/pc_bildirim.py` `Mantik`) BIREBIR tasinmasi: ayni olay dizisinde ayni
 * bildirim dizisi (`mobil/test/vektor/bildirim_karar.json`, Python'dan uretildi; BildirimKararTest).
 * Ag yok, Android sinifi yok, saat enjekte: JVM'de sinanir. Is parcacigi guvenligi cagiranin isi (tek kilit).
 *
 *  - durum (retained) / vasiyet {c:0}: "karttan haber yok" YALNIZ kayit surerken (A33); kart yerelde
 *    gorunuyorsa "ev interneti koptu" (A36); donunce AYNI bildirim (etiket `baglanti`) guncellenir
 *  - olay: (a, n) ile yineleme ayiklanir; bosluklardan KACIRILAN olay sayilir
 *  - yollar arasi yineleme (A35): (aile, a, oturum) + zaman penceresi; daha ayrintili ikinci haber ayni
 *    bildirimi SESSIZCE gunceller, daha az ayrintili olani duser
 * Pencereler kurucudan; varsayilan PC'nin degerleri (900 / 120 s — kullanici karari, 2026-10-05).
 */
class BildirimKarar(
    private val cikis: (Bildirim) -> Unit,
    private val saatS: () -> Double,                       // tekduze saat (s)
    private val acik: (sinif: String) -> Boolean = { true },
    onceki: Pair<Long, Long>? = null,                      // onceki calismadan kalan son (a, n)
    private val kaliciYaz: (a: Long, n: Long) -> Unit = { _, _ -> },
    private val pencereS: Double = PENCERE_S,
    private val yakinS: Double = YAKIN_S,
    /**
     * PC koprusu SUREKLI bagli; telefonda servis yalniz kayit surerken calisir (curutucu 5E B3, B11). Bu iki
     * davranis PC'de acik, telefonda KAPALI (varsayilan); vektor testleri PC degerleriyle kosar:
     *  - acilisBoslugu: bu calismada ILK gorulen olayin oncesindeki bosluk "kacirilan" sayilir. Telefonda
     *    sayilmaz: servis yokken yayinlananlar (her acilisin bildirimsiz "basladi"si dahil) kacirilmis degildir.
     *  - yerelKopukluk: yerel akis 20 s susarsa "karttan haber yok". Telefonda servise yalniz kayit durumu
     *    DEGISINCE haber gelir; sessizlik kopukluk demek degildir.
     */
    private val acilisBoslugu: Boolean = false,
    private val yerelKopukluk: Boolean = false,
) {
    private val goruldu = LinkedHashSet<Pair<Long, Long>>()
    private val sonN = HashMap<Long, Long>()
    private var sonA: Long? = null
    private val onceki: Pair<Long, Long>? = onceki
    private var aGuncel: Long? = null
    var kacirilan = 0L
        private set
    var kartCevrimici: Boolean? = null
        private set
    private var durum: Map<String, Any?>? = null
    private var sonDurumSaat: Double? = null
    private var sonGorulme: Long? = null                   // kartin son "c:1" unix zamani
    private val oturumTur = HashMap<Long, Long>()
    private var yerelG: Pair<Long, Long>? = null
    private var yerelGSaat: Double? = null
    private var yerelSon: Double? = null
    var mqttBagli = false
        private set
    var baglanti: String? = null                           // null | kopuk | ev | yerel
        private set
    private var baglantiOturum: Any? = null
    private val kayitlar = ArrayList<Kayit>()
    private var sayac = 0

    private class Kayit(
        val aile: String, val a: Long?, val oturum: Long?, var sira: Int, var sinif: String, var anahtar: String,
        var degisken: Map<String, Any?>, val t: Double, val etiket: String, var gosterildi: Boolean,
    )

    // ── disaridan ───────────────────────────────────────────────────────────────────────────────
    fun mqttBagliOldu(bagli: Boolean) { mqttBagli = bagli }

    /** Cozulmus mesaj: `son` = konunun onekten sonraki kismi ("durum" / "olay"). */
    fun mqttMesaj(son: String, icerik: Map<String, Any?>) {
        if (son == "durum") durumIsle(icerik) else if (son == "olay") olayIsle(icerik)
    }

    /** Kart yerelde GORULDU ama kayit durumu bilinmiyor (servisin imzasiz /eslestir/bilgi yoklamasi, A36). */
    fun yerelGoruldu() { yerelSon = saatS() }

    /** Yerel akistan `G` satiri (uygulama ondeyken canli akis): kayit durumu + oturum. */
    fun yerelG(durumKodu: Long, oturum: Long) {
        yerelSon = saatS()
        val once = yerelG
        yerelG = Pair(durumKodu, oturum)
        yerelGSaat = saatS()
        if (once == null) return
        val (od, oo) = once
        if (od in KAYITTA && (durumKodu !in KAYITTA || oturum != oo)) {
            val dolu = durumKodu == KDR_DOLU
            bildir("oturum_sonu", aGuncel, oo, 1, if (dolu) "dolu" else "bitti",
                if (dolu) "bld.dolu_oturum" else "bld.kayit_bitti_yerel", mapOf("oturum" to oo))
        }
    }

    /** Saniyede bir: yerel erisim degisti mi (kopuk <-> ev), yalniz yerel yolda kopukluk. */
    fun tik() {
        if (kartCevrimici == false) { baglantiDegerlendir(); return }
        val yerelYol = yerelKopukluk && (!mqttBagli || kartCevrimici == null)
        if (!yerelYol) return
        val ys = yerelSon
        val kopuk = ys != null && saatS() - ys > YEREL_KOPUK_S
        if (baglanti == null && kopuk) {
            val (suruyor, oturum) = kayit()
            if (suruyor == true) {
                baglanti = "yerel"; baglantiOturum = oturum
                goster("baglanti", "kopuk", "bld.kopuk_yerel", mapOf("oturum" to oturum))
            }
        } else if (baglanti == "yerel" && !kopuk) {
            val (suruyor, oturum) = kayit()
            geriGeldi(suruyor == true, oturum)
        }
    }

    /** Kayit suruyor mu (servis: surmuyorsa kendini durdurur — A28). null = bilinmiyor. */
    fun kayitSuruyor(): Boolean? = kayit().first

    // ── durum (retained) ────────────────────────────────────────────────────────────────────────
    private fun durumIsle(d: Map<String, Any?>) {
        val c = d["c"]
        if (pyEsit(c, 1)) {
            kartCevrimici = true
            durum = d; sonDurumSaat = saatS()
            tam(d["t"])?.let { if (it > 0) sonGorulme = it }
            tam(d["a"])?.let { aGuncel = it }
            val o = tam(d["o"]); val y = tam(d["y"])
            if (o != null && o > 0 && y != null) oturumTur[o] = y
            if (baglanti != null) geriGeldi(pyIcinde(d["k"], KAYITTA), d["o"])
        } else if (pyEsit(c, 0)) {
            kartCevrimici = false
            baglantiDegerlendir()
        }
    }

    private fun geriGeldi(suruyor: Boolean, oturum: Any?) {
        if (suruyor) goster("baglanti", "kopuk", "bld.geri_kayit", mapOf("oturum" to oturum))
        else goster("baglanti", "kopuk", "bld.geri", emptyMap())
        baglanti = null
    }

    /** Araci karti cevrimdisi diyor: kayit suruyorsa "karttan haber yok"; kart yerelde gorunuyorsa "ev interneti koptu". */
    private fun baglantiDegerlendir() {
        val hedef = if (yerelErisim()) "ev" else "kopuk"
        if (baglanti == hedef || (baglanti == "yerel" && hedef == "kopuk")) { baglanti = hedef; return }
        if (baglanti == null) {
            val (suruyor, oturum) = kayit()
            if (suruyor != true) return
            baglantiOturum = oturum
        }
        baglanti = hedef
        goster("baglanti", "kopuk", if (hedef == "ev") "bld.ev_interneti" else "bld.kopuk", mapOf("oturum" to baglantiOturum))
    }

    // ── olay ────────────────────────────────────────────────────────────────────────────────────
    private fun olayIsle(d: Map<String, Any?>) {
        val n = tam(d["n"]) ?: return
        val a = tam(d["a"]) ?: return
        val o = d["o"] as? String ?: return
        val an = Pair(a, n)
        if (an in goruldu) return                               // QoS 1 yeniden teslim
        val pr = onceki
        if (pr != null && pr.first == a && n <= pr.second && !sonN.containsKey(a)) return      // onceki calismada gorulmus
        goruldu.add(an)
        while (goruldu.size > AN_AZAMI) goruldu.remove(goruldu.first())
        bosluk(a, n)
        aGuncel = a
        kaliciYaz(a, n)
        val oturum = tam(d["oturum"])
        when (o) {
            "basladi" -> if (pyEsit(d["devam"], 1)) {
                bildir("basladi", a, oturum, 2, "yeniden_basladi", "bld.basladi_devam", mapOf("oturum" to oturum))
            }
            "kayit_bitti" -> {
                val s = d["sebep"]
                if (pyEsit(s, 2)) {
                    bildir("oturum_sonu", a, oturum, 2, "dolu", "bld.dolu_oturum", mapOf("oturum" to oturum))
                } else if (pyEsit(s, 5)) {
                    bildir("oturum_sonu", a, oturum, 2, "yeniden_basladi", "bld.kesildi", mapOf("oturum" to oturum, "tur" to null, "saat" to null))
                } else {
                    bildir("oturum_sonu", a, oturum, 2, "bitti", "bld.kayit_bitti",
                        mapOf("oturum" to oturum, "sebep" to Kod("sebep.", s), "nokta" to (if (d.containsKey("nokta")) d["nokta"] else "?")))
                }
            }
            "pil_bitti" -> bildir("oturum_sonu", a, null, 3, "bitti", "bld.pil_bitti", mapOf(
                "durum" to Kod("pil.durum.", d["durum"]), "mah" to Sayi(d["mah_milli"], 1000, 1),
                "wh" to Sayi(d["wh_milli"], 1000, 2), "sure" to Sure(d["sure_ms"])))
            "dolu" -> bildir("oturum_sonu", a, null, 2, "dolu", "bld.dolu", emptyMap())
            "esik" -> bildir("esik", a, null, 2, "esik", "bld.esik", mapOf("deger" to Sayi(d["deger"], 10, 1), "esik" to Sayi(d["esik"], 10, 1)))
            "deneme" -> bildir("deneme", a, null, 2, "deneme", "bld.deneme", emptyMap())
        }
    }

    /** Kalici oturum yok: cevrimdisiyken kacan olaylar (a, n) bosluklarindan sayilir. */
    private fun bosluk(a: Long, n: Long) {
        var eksik = 0L
        val once = sonN[a]
        if (once != null) {
            eksik = maxOf(0L, n - once - 1)
            sonN[a] = maxOf(once, n)
        } else {
            val pr = onceki
            if (!acilisBoslugu) eksik = 0                       // telefon: bu calismanin ilk olayi — oncesi sayilmaz
            else if (sonA != null) eksik = n - 1                // kart yeniden basladi; yeni acilisin ilk olaylari
            else if (pr != null) eksik = if (pr.first == a) maxOf(0L, n - pr.second - 1) else n - 1
            sonN[a] = n
        }
        sonA = a
        if (eksik > 0) {
            kacirilan += eksik
            goster("kacirilan", "kacirilan", "bld.kacirilan", mapOf("adet" to kacirilan))
        }
    }

    // ── bildirim ────────────────────────────────────────────────────────────────────────────────
    private fun bildir(aile: String, a: Long?, oturum: Long?, sira: Int, sinif: String, anahtar: String, degisken: Map<String, Any?>) {
        val simdi = saatS()
        kayitlar.removeAll { simdi - it.t > pencereS }
        val m = eslesen(aile, a, oturum, simdi)
        if (m != null) {
            if (sira <= m.sira) return                          // ayni ya da daha az ayrintili: tek bildirim
            m.sira = sira; m.sinif = sinif; m.anahtar = anahtar; m.degisken = degisken
            if (acik(sinif)) {
                cikis(Bildirim(m.etiket, sinif, anahtar, metinDegerleri(m), m.gosterildi))
                m.gosterildi = true
            }
            return
        }
        val r = Kayit(aile, a, oturum, sira, sinif, anahtar, degisken, simdi, etiket(aile, a, oturum), false)
        kayitlar.add(r)
        if (acik(sinif)) {
            cikis(Bildirim(r.etiket, sinif, anahtar, metinDegerleri(r), false))
            r.gosterildi = true
        }
    }

    private fun eslesen(aile: String, a: Long?, oturum: Long?, simdi: Double): Kayit? {
        if (aile == "deneme") return null
        for (r in kayitlar.asReversed()) {
            if (r.aile != aile) continue
            if (r.a != null && a != null && r.a != a) continue
            if (r.oturum != null && oturum != null) {
                if (r.oturum != oturum) continue
            } else if (simdi - r.t > yakinS) {
                continue
            }
            return r
        }
        return null
    }

    private fun etiket(aile: String, a: Long?, oturum: Long?): String {
        sayac += 1
        if (aile == "oturum_sonu" && oturum != null && oturum >= 0) return "os-" + java.lang.Long.toHexString(oturum and 0xFFFFFFFFL)
        if (aile == "basladi" && a != null && a >= 0) return "bs-" + java.lang.Long.toHexString(a and 0xFFFFFFFFL)
        return aile.take(2) + "-t" + Integer.toHexString(sayac and 0xFFFFFF)
    }

    /** Degiskenler: null -> "?"; bld.kesildi'ye oturum turu ve "son gorulme" eki. */
    private fun metinDegerleri(r: Kayit): Map<String, Any?> {
        val deg = LinkedHashMap<String, Any?>()
        for ((ad, v) in r.degisken) deg[ad] = v ?: "?"
        if (r.anahtar == "bld.kesildi") {
            val tur = r.oturum?.let { oturumTur[it] }
            deg["tur"] = Kod("oturum.tur.", tur ?: 1L)
            val sg = sonGorulme
            deg["saat"] = if (sg != null) SaatEki("bld.kesildi_saat", sg) else ""
        }
        return deg
    }

    private fun goster(etiket: String, sinif: String, anahtar: String, deg: Map<String, Any?>) {
        if (!acik(sinif)) return
        cikis(Bildirim(etiket, sinif, anahtar, deg.mapValues { it.value ?: "?" }, false))
    }

    // ── yardimcilar ─────────────────────────────────────────────────────────────────────────────
    /** Kayit suruyor mu: yerel `G` ile MQTT `durum`'un HANGISI daha yeniyse o. */
    private fun kayit(): Pair<Boolean?, Any?> {
        val g = yerelG; val gt = yerelGSaat
        val d = durum; val dt = sonDurumSaat
        // Python `max(adaylar, key=zaman)`: esitlikte ILK aday (yerel) kazanir.
        if (g != null && gt != null && (d == null || dt == null || gt >= dt)) return Pair(g.first in KAYITTA, g.second)
        if (d != null && dt != null) return Pair(pyIcinde(d["k"], KAYITTA), d["o"])
        return Pair(null, null)
    }

    private fun yerelErisim(): Boolean {
        val ys = yerelSon ?: return false
        return saatS() - ys <= YEREL_ERISIM_S
    }

    companion object {
        /** KDR_KAYIT, KDR_BEKLIYOR (kayit_yonet.h). */
        val KAYITTA = setOf(2L, 4L)
        const val KDR_DOLU = 3L
        const val YEREL_ERISIM_S = 15.0          // son yerel haber bundan yeniyse kart "yerelde gorunuyor"
        const val YEREL_KOPUK_S = 20.0           // yalniz yerel yol: bu kadar haber gelmezse "karttan haber yok"
        /**
         * Yollar arasi yineleme penceresi: PC ile AYNI (900 s; oturumu bilinmeyen haberler 120 s). Tasarimin
         * 30 s'si (A35) kullanici karariyla degisti (2026-10-05): 15 dakikalik yoklama ayni olayi 30 s'den
         * SONRA da getirebilir; cift bildirim olmasin.
         */
        const val PENCERE_S = 900.0
        const val YAKIN_S = 120.0
        const val AN_AZAMI = 1024

        /** Python `_tamsayi`: int (bool DEGIL). JSON'dan Long gelir; 5.0 (Double) tamsayi SAYILMAZ. */
        fun tam(x: Any?): Long? = x as? Long

        /** Python `x == n` (1 == 1.0 == True). */
        fun pyEsit(x: Any?, n: Long): Boolean = when (x) {
            is Long -> x == n
            is Double -> x == n.toDouble()
            is Boolean -> (if (x) 1L else 0L) == n
            else -> false
        }

        fun pyIcinde(x: Any?, kume: Set<Long>): Boolean = kume.any { pyEsit(x, it) }
    }
}
