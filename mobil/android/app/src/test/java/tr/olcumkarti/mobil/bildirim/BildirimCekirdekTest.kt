package tr.olcumkarti.mobil.bildirim

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 5E-1: bildirim cekirdegi (saf Kotlin). Vektorler:
 *  - zarf: ortak/test/vektor/kripto.json "zarf" (kart, PC ve JS ile AYNI dosya)
 *  - MQTT: mobil/test/vektor/mqtt.json (kopru/mqtt_istemci.py'den uretildi)
 * Calisma dizini android/app.
 */
class BildirimCekirdekTest {
    private fun hex(s: String): ByteArray = ByteArray(s.length / 2) { s.substring(2 * it, 2 * it + 2).toInt(16).toByte() }
    private fun hx(b: ByteArray): String = b.joinToString("") { "%02x".format(it) }

    @Suppress("UNCHECKED_CAST")
    private fun dosya(yol: String): Map<String, Any?> {
        val f = File(yol)
        assertTrue("vektor dosyasi yok: ${f.path}", f.isFile)
        return DuzJson.nesne(f.readText(Charsets.UTF_8))
    }

    @Suppress("UNCHECKED_CAST")
    private fun liste(m: Map<String, Any?>, ad: String): List<Map<String, Any?>> = m[ad] as List<Map<String, Any?>>

    private fun jsonHata(metin: String): Boolean = try { DuzJson.oku(metin); false } catch (e: JsonHatasi) { true }
    private fun zarfTuru(islem: () -> Any?): String? = try { islem(); null } catch (e: ZarfHatasi) { e.tur }
    private fun mqttTuru(islem: () -> Any?): String? = try { islem(); null } catch (e: MqttHatasi) { e.tur }

    // ── DuzJson ─────────────────────────────────────────────────────────────────────────────────
    @Test
    fun json_degerler_sira_kacislar() {
        val m = DuzJson.nesne("""{"b":1,"10":-2,"a":[true,false,null,1.5,1e3,"x\n\"\\\/\u011f"],"n":{},"bos":"","buyuk":9223372036854775807}""")
        assertEquals(listOf("b", "10", "a", "n", "bos", "buyuk"), m.keys.toList())          // sira korunur
        assertEquals(1L, m["b"])
        assertEquals(-2L, m["10"])
        assertEquals(listOf(true, false, null, 1.5, 1000.0, "x\n\"\\/ğ"), m["a"])
        assertEquals(emptyMap<String, Any?>(), m["n"])
        assertEquals(Long.MAX_VALUE, m["buyuk"])
        assertEquals(1.0e19, DuzJson.oku("10000000000000000000") as Double, 0.0)          // Long'a sigmayan tamsayi
        assertEquals("😀", DuzJson.oku("\"\\ud83d\\ude00\""))
        assertNull(DuzJson.oku(" null "))
        assertEquals(2L, DuzJson.nesne("""{"a":1,"a":2}""")["a"])                           // yinelenen anahtar: son
    }

    @Test
    fun json_katidir_gevsekBicimlerReddedilir() {
        val kotu = listOf(
            "", " ", "{", "}", "[1,]", "{\"a\":1,}", "{'a':1}", "{a:1}", "[1 2]", "01", "1.", ".5", "+1", "1e", "-",
            "tru", "nul", "NaN", "Infinity", "\"a", "\"\\x\"", "\"\\u12\"", "\"\\u12g4\"", "\"a\tb\"", "\"a\nb\"",
            "{\"a\":1} x", "[] []", "// yorum\n1", "\uFEFF{}", "{\"a\"}", "{\"a\":}", "[,1]", "{,}", "\"a\"\"b\"",
        )
        for (k in kotu) assertTrue("kabul edildi: $k", jsonHata(k))
        assertTrue(jsonHata("[".repeat(DuzJson.DERINLIK_AZAMI + 2) + "]".repeat(DuzJson.DERINLIK_AZAMI + 2)))
        assertFalse(jsonHata("[".repeat(DuzJson.DERINLIK_AZAMI) + "]".repeat(DuzJson.DERINLIK_AZAMI)))
        // Kok nesne degilse nesne() reddeder.
        for (k in listOf("[]", "1", "\"x\"", "null", "true")) assertTrue(k, try { DuzJson.nesne(k); false } catch (e: JsonHatasi) { true })
    }

    // ── Zarf (ortak vektorler) ──────────────────────────────────────────────────────────────────
    private val zarf: Map<String, Any?> by lazy {
        @Suppress("UNCHECKED_CAST")
        dosya("../../../ortak/test/vektor/kripto.json")["zarf"] as Map<String, Any?>
    }

    @Test
    fun zarf_ortakVektorler_duzMetinBaytBayt() {
        val anahtar = hex(zarf["anahtar"] as String)
        val kur = liste(zarf, "kur")
        assertTrue(kur.size >= 11)
        for (v in kur) {
            val konu = v["konu"] as String
            val duz = Zarf.coz(anahtar, konu.toByteArray(Charsets.UTF_8), hex(v["zarf"] as String))
            assertEquals(v["ad"] as String, v["duz"] as String, String(duz, Charsets.UTF_8))
            assertEquals(v["ad"] as String, DuzJson.nesne(v["duz"] as String), Zarf.ac(anahtar, konu, hex(v["zarf"] as String)))
        }
        val durum = Zarf.ac(anahtar, kur[0]["konu"] as String, hex(kur[0]["zarf"] as String))
        assertEquals(1L, durum["c"])
        assertEquals("A3-1E", durum["f"])
        // Anahtar sirasi korunur (tamsayi benzeri anahtarlar dahil).
        val s = zarf["sirali"] as Map<*, *>
        assertEquals(listOf("b", "10", "2", "a"), Zarf.ac(anahtar, s["konu"] as String, hex(s["zarf"] as String)).keys.toList())
    }

    @Test
    fun zarf_redVektorleri_hepsiReddedilir_turDogru() {
        val red = liste(zarf, "red")
        assertTrue(red.size >= 16)
        val beklenen = mapOf(
            "yanlis_konu" to "etiket", "baska_onek" to "etiket", "yanlis_anahtar" to "etiket", "sifreli_bit" to "etiket",
            "etiket_son_bit" to "etiket", "nonce_bit" to "etiket", "bir_bayt_fazla" to "etiket",
            "sihir_OKB2" to "bicim", "sihirsiz" to "bicim", "kisa_31" to "bicim", "bos" to "bicim",
            "json_degil" to "icerik", "json_liste" to "icerik", "json_metin" to "icerik", "utf8_degil" to "icerik", "bom_json" to "icerik",
        )
        for (v in red) {
            val ad = v["ad"] as String
            val tur = zarfTuru { Zarf.ac(hex(v["anahtar"] as String), v["konu"] as String, hex(v["zarf"] as String)) }
            assertTrue("kabul edildi: $ad", tur != null)
            if (beklenen.containsKey(ad)) assertEquals(ad, beklenen[ad], tur)
        }
        assertEquals("bicim", zarfTuru { Zarf.coz(ByteArray(31), ByteArray(0), ByteArray(40)) })
        assertEquals(32, Zarf.EN_AZ)
    }

    @Test
    fun bilgi_ortakVektorler_cozulur_yaDaReddedilir() {
        val aad = zarf["bilgi_aad"] as Map<*, *>
        assertEquals(aad["aad"], hx(Zarf.bilgiAad(aad["kimlik"] as String, (aad["n"] as Long).toInt())))
        val bilgi = liste(zarf, "bilgi")
        assertTrue(bilgi.size >= 15)
        var tamam = 0
        var red = 0
        for (v in bilgi) {
            val ad = v["ad"] as String
            val sonuc = v["sonuc"] as Map<*, *>
            val coz = { Zarf.bilgiCoz(hex(v["K"] as String), v["kimlik"] as String, (v["n"] as Long).toInt(), hex(v["govde"] as String)) }
            if (sonuc.containsKey("hata")) {
                assertTrue("kabul edildi: $ad", zarfTuru(coz) != null)
                red++
            } else {
                val b = coz()
                assertEquals(ad, sonuc["uri"], b.uri)
                assertEquals(ad, sonuc["kullanici"], b.kullanici)
                assertEquals(ad, sonuc["parola"], b.parola)
                assertEquals(ad, sonuc["onek"], b.onek)
                assertEquals(ad, sonuc["anahtar"], hx(b.anahtar))
                assertFalse("toString sir yaziyor", b.toString().contains(b.parola) || b.toString().contains(b.onek) || b.toString().contains(b.uri))
                tamam++
            }
        }
        assertTrue("hem gecen hem reddedilen vektor olmali ($tamam / $red)", tamam >= 3 && red >= 8)
    }

    @Test
    fun zarfHatasi_sirTasimaz() {
        val v = liste(zarf, "red").first { it["ad"] == "yanlis_anahtar" }
        val h = try { Zarf.ac(hex(v["anahtar"] as String), v["konu"] as String, hex(v["zarf"] as String)); null } catch (e: ZarfHatasi) { e }
        assertEquals("etiket", h!!.message)
        assertFalse(h.toString().contains(v["konu"] as String))
        assertNull(h.cause)                                   // platform istisnasi (ve mesaji) zincire girmez
    }

    // ── MQTT paketleri (Python basvurusuyla ayni baytlar) ───────────────────────────────────────
    private val mqtt: Map<String, Any?> by lazy { dosya("../../test/vektor/mqtt.json") }

    @Test
    fun mqtt_uzunlukVeDize() {
        for (v in liste(mqtt, "uzunluk")) {
            val n = (v["n"] as Long).toInt()
            val b = hex(v["bayt"] as String)
            assertEquals("$n", v["bayt"], hx(MqttPaket.uzunlukKodla(n)))
            assertEquals("$n", Pair(n, b.size), MqttPaket.uzunlukCoz(b, 0, b.size))
        }
        assertEquals("bicim", mqttTuru { MqttPaket.uzunlukKodla(-1) })
        assertEquals("bicim", mqttTuru { MqttPaket.uzunlukKodla(MqttPaket.UZUNLUK_AZAMI + 1) })
        assertNull(MqttPaket.uzunlukCoz(hex("8080"), 0, 2))                                  // henuz tam degil
        assertNull(MqttPaket.uzunlukCoz(ByteArray(0), 0, 0))
        assertEquals("bicim", mqttTuru { MqttPaket.uzunlukCoz(hex("8080808001"), 0, 5) })    // 4 bayttan uzun
        for (v in liste(mqtt, "dize")) assertEquals(v["metin"] as String, v["bayt"], hx(MqttPaket.dize(v["metin"] as String)))
        assertEquals("bicim", mqttTuru { MqttPaket.dize("a".repeat(65536)) })
    }

    @Test
    fun mqtt_connectSubscribeVeSabitPaketler() {
        for (v in liste(mqtt, "connect")) {
            assertEquals(v["kimlik"] as String, v["paket"],
                hx(MqttPaket.connect(v["kimlik"] as String, v["kullanici"] as String?, v["parola"] as String?, (v["keepalive"] as Long).toInt())))
        }
        for (v in liste(mqtt, "subscribe")) {
            assertEquals(v["paket"], hx(MqttPaket.subscribe((v["no"] as Long).toInt(), v["konu"] as String, (v["qos"] as Long).toInt())))
        }
        val s = mqtt["sabit"] as Map<*, *>
        assertEquals(s["puback_1"], hx(MqttPaket.puback(1)))
        assertEquals(s["puback_65535"], hx(MqttPaket.puback(65535)))
        assertEquals(s["pingreq"], hx(MqttPaket.pingreq()))
        assertEquals(s["disconnect"], hx(MqttPaket.disconnect()))
        for (qos in listOf(-1, 2, 3)) assertEquals("bicim", mqttTuru { MqttPaket.subscribe(1, "a", qos) })
        for (no in listOf(0, 65536, -1)) assertEquals("bicim", mqttTuru { MqttPaket.subscribe(no, "a", 1) })
        assertEquals("bicim", mqttTuru { MqttPaket.connect("a", null, null, 65536) })
        assertEquals(0, MqttPaket.connackKodu(hex("0000")))
        assertEquals(5, MqttPaket.connackKodu(hex("0005")))
        assertEquals("bicim", mqttTuru { MqttPaket.connackKodu(hex("00")) })
        assertEquals(Pair(7, 1), MqttPaket.suback(hex("000701")))
        assertEquals(Pair(65535, 0x80), MqttPaket.suback(hex("ffff80")))
        assertEquals("bicim", mqttTuru { MqttPaket.suback(hex("0007")) })
    }

    @Test
    fun mqtt_publishCozVeRed() {
        for (v in liste(mqtt, "publish")) {
            val y = MqttPaket.publishCoz((v["ilk"] as Long).toInt(), hex(v["govde"] as String))
            assertEquals(v["konu"], y.konu)
            assertEquals(v["yuk"], hx(y.yuk))
            assertEquals(v["kalici"], y.kalici)
            assertEquals((v["qos"] as Long).toInt(), y.qos)
            assertEquals((v["no"] as Long?)?.toInt(), y.paketNo)
        }
        for (v in liste(mqtt, "publish_red")) {
            assertEquals(v["ad"] as String, "bicim", mqttTuru { MqttPaket.publishCoz((v["ilk"] as Long).toInt(), hex(v["govde"] as String)) })
        }
    }

    @Test
    fun mqtt_ayristirici_parcaliAkis_buyukPaketReddi() {
        val paketler = liste(mqtt, "publish").map { hex(it["paket"] as String) } + listOf(hex("d000"), hex("20020000"))
        val akis = paketler.reduce { a, b -> a + b }
        // Tek seferde, bayt bayt ve 7'ser baytla beslenince AYNI paket dizisi cikar.
        for (adim in listOf(akis.size, 1, 7)) {
            val a = MqttPaket.Ayristirici()
            val cikan = ArrayList<ByteArray>()
            var i = 0
            while (i < akis.size) {
                val n = minOf(adim, akis.size - i)
                a.besle(akis.copyOfRange(i, i + n))
                i += n
                while (true) { val p = a.sonraki() ?: break; cikan.add(MqttPaket.paket(p.first, p.second)) }
            }
            assertEquals("adim $adim", paketler.size, cikan.size)
            for (k in paketler.indices) assertArrayEquals("adim $adim paket $k", paketler[k], cikan[k])
            assertEquals(0, a.bekleyen())
        }
        val yarim = MqttPaket.Ayristirici()
        yarim.besle(hex("30"))
        assertNull(yarim.sonraki())
        yarim.besle(hex("05000161"))
        assertNull(yarim.sonraki())                           // govde eksik: beklenir
        // Bildirilen uzunluk siniri asiyor: govde gelmeden REDDEDILIR (bellek dolmaz).
        val buyuk = MqttPaket.Ayristirici(1000)
        buyuk.besle(hex("30") + MqttPaket.uzunlukKodla(1001))
        assertEquals("buyuk", mqttTuru { buyuk.sonraki() })
        val tasan = MqttPaket.Ayristirici(1000)
        assertEquals("buyuk", mqttTuru { for (i in 0 until 20) tasan.besle(ByteArray(100) { 0xff.toByte() }) })
        assertEquals(16384, MqttPaket.PAKET_AZAMI)
        val bozuk = MqttPaket.Ayristirici()
        bozuk.besle(hex("30ffffffff01"))
        assertEquals("bicim", mqttTuru { bozuk.sonraki() })
    }
}
