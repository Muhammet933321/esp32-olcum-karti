package tr.olcumkarti.mobil.bildirim

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 5E-3: bildirim karar katmani. Vektor `mobil/test/vektor/bildirim_karar.json` — kartla ve gercek araciyla
 * sinanmis Python basvurusundan (kopru/pc_bildirim.py Mantik) uretildi: AYNI olay dizisi, AYNI bildirim
 * dizisi (etiket, anahtar, degerler, sessiz) ve AYNI son durum. Calisma dizini android/app.
 */
class BildirimKararTest {
    @Suppress("UNCHECKED_CAST")
    private val vektor: List<Map<String, Any?>> by lazy {
        val f = File("../../test/vektor/bildirim_karar.json")
        assertTrue("vektor dosyasi yok: ${f.path}", f.isFile)
        DuzJson.nesne(f.readText(Charsets.UTF_8))["senaryolar"] as List<Map<String, Any?>>
    }

    /** Python `str(v)` karsiligi (vektordeki dokum bicimi). */
    private fun py(v: Any?): String = when (v) {
        null -> "None"
        is Boolean -> if (v) "True" else "False"
        is Kod -> "KOD(${v.onek}${py(v.kod)})"
        is Sayi -> "SAYI(${py(v.x)},${v.bolen},${v.basamak})"
        is Sure -> "SURE(${py(v.ms)})"
        is SaatEki -> "EK(${v.anahtar},SAAT(${v.unix}))"
        else -> v.toString()
    }

    private class Kosu(val bildirimler: List<List<Any?>>, val karar: BildirimKarar, val yazilan: List<Pair<Long, Long>>)

    @Suppress("UNCHECKED_CAST")
    private fun kos(s: Map<String, Any?>, pencere: Double? = null, yakin: Double? = null): Kosu {
        var saat = 1000.0
        val cikan = ArrayList<List<Any?>>()
        val yazilan = ArrayList<Pair<Long, Long>>()
        val kapali = (s["kapali"] as List<String>?) ?: emptyList()
        val onceki = (s["onceki"] as List<Long>?)?.let { Pair(it[0], it[1]) }
        val k = BildirimKarar(
            cikis = { b -> cikan.add(listOf(b.etiket, b.anahtar, b.degerler.mapValues { py(it.value) }, b.sessiz)) },
            saatS = { saat }, acik = { it !in kapali }, onceki = onceki, kaliciYaz = { a, n -> yazilan.add(Pair(a, n)) },
            pencereS = pencere ?: ((s["pencere"] as Long?) ?: 900L).toDouble(), yakinS = yakin ?: ((s["yakin"] as Long?) ?: 120L).toDouble(),
        )
        for (op in s["ops"] as List<List<Any?>>) {
            when (op[0]) {
                "saat" -> saat += (op[1] as Long).toDouble()
                "mqtt" -> k.mqttMesaj(op[1] as String, op[2] as Map<String, Any?>)
                "bagli" -> k.mqttBagliOldu(op[1] as Boolean)
                "yerel" -> k.yerelG(op[1] as Long, op[2] as Long)
                "yerel_gor" -> k.yerelGoruldu()
                "tik" -> k.tik()
                else -> throw IllegalStateException("bilinmeyen islem")
            }
        }
        return Kosu(cikan, k, yazilan)
    }

    @Test
    fun pythonBasvurusuylaAyniBildirimDizisi_butunSenaryolar() {
        assertTrue(vektor.size >= 25)
        var toplam = 0
        for (s in vektor) {
            val ad = s["ad"] as String
            val beklenen = s["beklenen"] as Map<*, *>
            val k = kos(s)
            assertEquals(ad, beklenen["bildirimler"], k.bildirimler)
            val son = beklenen["son"] as Map<*, *>
            assertEquals("$ad kacirilan", son["kacirilan"], k.karar.kacirilan)
            assertEquals("$ad baglanti", son["baglanti"], k.karar.baglanti)
            assertEquals("$ad kart_cevrimici", son["kart_cevrimici"], k.karar.kartCevrimici)
            assertEquals("$ad kayit_suruyor", son["kayit_suruyor"], k.karar.kayitSuruyor())
            toplam += k.bildirimler.size
        }
        assertTrue("vektor bos olamaz", toplam >= 60)
    }

    @Test
    fun vektorKapsami_herBildirimAnahtariEnAzBirSenaryoda() {
        val gorulen = vektor.flatMap { s -> ((s["beklenen"] as Map<*, *>)["bildirimler"] as List<List<Any?>>).map { it[1] as String } }.toSet()
        val gereken = setOf(
            "bld.kopuk", "bld.kopuk_yerel", "bld.ev_interneti", "bld.geri", "bld.geri_kayit", "bld.kayit_bitti", "bld.kayit_bitti_yerel",
            "bld.dolu", "bld.dolu_oturum", "bld.kesildi", "bld.pil_bitti", "bld.esik", "bld.basladi_devam", "bld.kacirilan", "bld.deneme",
        )
        assertEquals(emptySet<String>(), gereken - gorulen)
        // Sessiz guncelleme (ayni etiket, daha ayrintili haber) de vektorde var.
        assertTrue(vektor.any { s -> ((s["beklenen"] as Map<*, *>)["bildirimler"] as List<List<Any?>>).any { it[3] == true } })
    }

    @Test
    fun kaliciYazim_herYeniOlaydaSonAN_yinelenenVeBicimsizdeYok() {
        val s = vektor.first { it["ad"] == "olay_yineleme_ve_bosluk" }
        assertEquals(listOf(Pair(3L, 1L), Pair(3L, 2L), Pair(3L, 6L), Pair(3L, 4L), Pair(3L, 9L)), kos(s).yazilan)
        assertEquals(listOf(Pair(3L, 2L)), kos(vektor.first { it["ad"] == "bicimsiz_olaylar_yok_sayilir" }).yazilan)
    }

    @Test
    fun telefonPencereleri_A35_varsayilan30Saniye() {
        assertEquals(30.0, BildirimKarar.PENCERE_S, 0.0)
        assertEquals(30.0, BildirimKarar.YAKIN_S, 0.0)
        // Varsayilan kurucuyla (telefon): yerel "bitti"den 20 s sonra gelen MQTT ayrintisi AYNI bildirimi gunceller,
        // 31 s sonra gelen AYRI bildirim olur.
        fun kur(gecikme: Double): List<Pair<String, Boolean>> {
            var saat = 0.0
            val cikan = ArrayList<Pair<String, Boolean>>()
            val k = BildirimKarar({ cikan.add(Pair(it.anahtar, it.sessiz)) }, { saat })
            k.yerelG(2, 53); k.yerelG(1, 53)
            saat += gecikme
            k.mqttMesaj("olay", mapOf("n" to 1L, "a" to 3L, "o" to "kayit_bitti", "sebep" to 1L, "oturum" to 53L, "nokta" to 9L))
            return cikan
        }
        assertEquals(listOf(Pair("bld.kayit_bitti_yerel", false), Pair("bld.kayit_bitti", true)), kur(20.0))
        assertEquals(listOf(Pair("bld.kayit_bitti_yerel", false), Pair("bld.kayit_bitti", false)), kur(31.0))
    }

    @Test
    fun gorulenOlayBellegiSinirli_enEskiAtilir() {
        var saat = 0.0
        var n = 0
        val k = BildirimKarar({ n++ }, { saat })
        for (i in 1..(BildirimKarar.AN_AZAMI + 10)) k.mqttMesaj("olay", mapOf("n" to i.toLong(), "a" to 3L, "o" to "deneme"))
        assertEquals(BildirimKarar.AN_AZAMI + 10, n)
        k.mqttMesaj("olay", mapOf("n" to (BildirimKarar.AN_AZAMI + 10).toLong(), "a" to 3L, "o" to "deneme"))    // yeni gorulen: yinelenmez
        assertEquals(BildirimKarar.AN_AZAMI + 10, n)
        k.mqttMesaj("olay", mapOf("n" to 1L, "a" to 3L, "o" to "deneme"))                                         // bellekten dusmus: yeniden gosterilir
        assertEquals(BildirimKarar.AN_AZAMI + 11, n)
        assertEquals(1024, BildirimKarar.AN_AZAMI)
    }

    @Test
    fun bildirimNesnesiSirTasimaz_yalnizAnahtarVeDeger() {
        val s = vektor.first { it["ad"] == "kayit_bitti_sebepler" }
        val alanlar = Bildirim::class.java.declaredFields.map { it.name }.toSet()
        assertEquals(setOf("etiket", "sinif", "anahtar", "degerler", "sessiz"), alanlar)
        assertTrue(kos(s).bildirimler.all { (it[1] as String).startsWith("bld.") })
    }
}
