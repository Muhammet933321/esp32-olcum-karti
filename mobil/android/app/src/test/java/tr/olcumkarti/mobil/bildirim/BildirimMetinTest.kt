package tr.olcumkarti.mobil.bildirim

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.util.TimeZone

/**
 * 5E-3: bildirim metinleri. Sablonlar GERCEK kaynak dosyalarindan (res/values/bildirim.xml tr,
 * values-en/bildirim.xml en) okunur; beklenen cumleler PC'nin gercek ciktisi
 * (mobil/test/vektor/bildirim_metin.json). Ayni senaryo -> ayni etiket, baslik, cumle, sessizlik.
 * Calisma dizini android/app.
 */
class BildirimMetinTest {
    /** strings.xml okuyucu (yalniz <string name="..">..</string>); XML varliklari ve Android kacislari cozulur. */
    private fun kaynak(yol: String): Map<String, String> {
        val f = File(yol)
        assertTrue("kaynak dosyasi yok: ${f.path}", f.isFile)
        val m = LinkedHashMap<String, String>()
        for (e in Regex("<string name=\"([a-z0-9_]+)\"[^>]*>(.*?)</string>").findAll(f.readText(Charsets.UTF_8))) {
            var s = e.groupValues[2].replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
            s = Regex("\\\\(.)").replace(s) { it.groupValues[1] }
            m[e.groupValues[1]] = s
        }
        return m
    }

    private val tr by lazy { kaynak("src/main/res/values/bildirim.xml") }
    private val en by lazy { kaynak("src/main/res/values-en/bildirim.xml") }
    private fun sozluk(dil: String): (String) -> String? = { a -> (if (dil == "tr") tr else en)[a.replace('.', '_')] }

    @Suppress("UNCHECKED_CAST")
    private fun json(yol: String): Map<String, Any?> = DuzJson.nesne(File(yol).readText(Charsets.UTF_8))

    @Suppress("UNCHECKED_CAST")
    private fun kos(s: Map<String, Any?>, dil: String, dilim: TimeZone): List<List<Any?>> {
        var saat = 1000.0
        val metin = BildirimMetin(dil, sozluk(dil), dilim)
        val cikan = ArrayList<List<Any?>>()
        val kapali = (s["kapali"] as List<String>?) ?: emptyList()
        val onceki = (s["onceki"] as List<Long>?)?.let { Pair(it[0], it[1]) }
        val k = BildirimKarar(
            cikis = { b -> cikan.add(listOf(b.etiket, metin.baslik(), metin.kur(b), b.sessiz)) }, saatS = { saat },
            acik = { it !in kapali }, onceki = onceki,
            pencereS = ((s["pencere"] as Long?) ?: 900L).toDouble(), yakinS = ((s["yakin"] as Long?) ?: 120L).toDouble(),
            acilisBoslugu = true, yerelKopukluk = true,          // PC davranisi (vektor PC'den uretildi)
        )
        for (op in s["ops"] as List<List<Any?>>) {
            when (op[0]) {
                "saat" -> saat += (op[1] as Long).toDouble()
                "mqtt" -> k.mqttMesaj(op[1] as String, op[2] as Map<String, Any?>)
                "bagli" -> k.mqttBagliOldu(op[1] as Boolean)
                "yerel" -> k.yerelG(op[1] as Long, op[2] as Long)
                "yerel_gor" -> k.yerelGoruldu()
                "tik" -> k.tik()
            }
        }
        return cikan
    }

    @Test
    @Suppress("UNCHECKED_CAST")
    fun pcIleAyniCumleler_butunSenaryolar_trVeEn() {
        val karar = (json("../../test/vektor/bildirim_karar.json")["senaryolar"] as List<Map<String, Any?>>).associateBy { it["ad"] as String }
        val v = json("../../test/vektor/bildirim_metin.json")
        val fark = (v["utc_fark_dk"] as Long).toInt()
        val dilim = TimeZone.getTimeZone("GMT%s%02d:%02d".format(if (fark < 0) "-" else "+", Math.abs(fark) / 60, Math.abs(fark) % 60))
        var toplam = 0
        for (s in v["senaryolar"] as List<Map<String, Any?>>) {
            val ad = s["ad"] as String
            for (dil in listOf("tr", "en")) {
                // PC `None` yazar (Python); telefon bilinmeyen kodu "?" diye yazar — tek bilincli fark.
                val beklenen = (s[dil] as List<List<Any?>>).map { listOf(it[0], it[1], (it[2] as String).replace("(None)", "(?)"), it[3]) }
                assertEquals("$ad / $dil", beklenen, kos(karar[ad]!!, dil, dilim))
                toplam += beklenen.size
            }
        }
        assertTrue(toplam >= 120)
    }

    @Test
    fun kaynakDosyalari_trVeEnAyniAnahtarlar_yerTutucularAyni_bosYok() {
        assertEquals(tr.keys, en.keys)
        assertTrue(tr.size >= 35)
        val yer = Regex("\\{[a-z_]+\\}")
        for (a in tr.keys) {
            assertTrue(a, tr[a]!!.isNotBlank() && en[a]!!.isNotBlank())
            assertEquals(a, yer.findAll(tr[a]!!).map { it.value }.toSet(), yer.findAll(en[a]!!).map { it.value }.toSet())
        }
        // Telefona ozel sozler: PC'den soz etmez.
        for (m in listOf(tr, en)) assertFalse(m.values.any { it.contains("PC") })
        assertTrue(tr["bld_kacirilan"]!!.contains("bu telefon"))
        assertTrue(en["bld_kacirilan"]!!.contains("this phone"))
    }

    @Test
    fun sayiSureKodVeEksikSablon() {
        val m = BildirimMetin("tr", sozluk("tr"), TimeZone.getTimeZone("GMT"))
        fun kur(anahtar: String, deg: Map<String, Any?>) = m.kur(Bildirim("e", "s", anahtar, deg, false))
        // Yarim-cift yuvarlama (Python ile ayni): 0.125 -> 0,12 · 0.375 -> 0,38; tamsayi olmayan "?".
        assertEquals("Pil testi bitti — çalışıyor: 0,1 mAh, 0,12 Wh, süre 0:00:59",
            kur("bld.pil_bitti", mapOf("durum" to Kod("pil.durum.", 1L), "mah" to Sayi(125L, 1000, 1), "wh" to Sayi(125L, 1000, 2), "sure" to Sure(59_999L))))
        assertEquals("Pil testi bitti — bilinmeyen durum (9): ? mAh, 0,38 Wh, süre 27:46:40",
            kur("bld.pil_bitti", mapOf("durum" to Kod("pil.durum.", 9L), "mah" to Sayi(2.5, 1000, 1), "wh" to Sayi(375L, 1000, 2), "sure" to Sure(100_000_000L))))
        assertEquals("Pil testi bitti — bilinmeyen durum (?): ? mAh, ? Wh, süre ?",
            kur("bld.pil_bitti", mapOf("durum" to Kod("pil.durum.", null), "mah" to Sayi(null, 1000, 1), "wh" to Sayi("x", 1000, 2), "sure" to Sure(-1L))))
        val ing = BildirimMetin("en", sozluk("en"), TimeZone.getTimeZone("GMT"))
        assertEquals("Unsynced data 61.2% (threshold 60.0%) — sync the recordings",
            ing.kur(Bildirim("e", "s", "bld.esik", mapOf("deger" to Sayi(612L, 10, 1), "esik" to Sayi(600L, 10, 1)), false)))
        // Saat eki verilen dilimde; bos ek metne hicbir sey eklemez.
        assertEquals("Kart yeniden başladı — Pil testi kesildi (oturum 7), son haber 2026-09-21 14:13",
            kur("bld.kesildi", mapOf("oturum" to 7L, "tur" to Kod("oturum.tur.", 2L), "saat" to SaatEki("bld.kesildi_saat", 1790000000L))))
        assertEquals("Kart yeniden başladı — Ölçüm kaydı kesildi (oturum 7)",
            kur("bld.kesildi", mapOf("oturum" to 7L, "tur" to Kod("oturum.tur.", 1L), "saat" to "")))
        // Sozlukte olmayan anahtar: anahtarin kendisi (cokme yok); bilinmeyen yer tutucu oldugu gibi kalir.
        assertEquals("bld.yok_boyle", kur("bld.yok_boyle", mapOf("x" to 1L)))
        assertEquals("Kayıt bitti (oturum {oturum})", kur("bld.kayit_bitti_yerel", emptyMap()))
        // Degeri olmayan alan "?" (Kotlin'in "null" yazisi ekrana cikmaz).
        assertEquals("Kayıt bitti (oturum ?)", kur("bld.kayit_bitti_yerel", mapOf("oturum" to null)))
        assertEquals("Ölçüm kartı", m.baslik())
        assertEquals("Measurement board", ing.baslik())
    }
}
