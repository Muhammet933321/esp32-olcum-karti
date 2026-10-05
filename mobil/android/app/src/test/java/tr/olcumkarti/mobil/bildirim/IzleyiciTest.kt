package tr.olcumkarti.mobil.bildirim

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import javax.crypto.Cipher
import javax.crypto.spec.IvParameterSpec
import javax.crypto.spec.SecretKeySpec

/**
 * 5E-4a: zarf -> araci -> karar zinciri, SAHTE araciyla ve SANAL saatle. Kartin yolladigi her sey testte
 * gercek bicimiyle uretilir: `/bildirim/bilgi` zarfi K ile, MQTT yukleri bildirim anahtariyla muhurlenir
 * (AAD = konu adi). Calisma dizini android/app.
 */
class IzleyiciTest {
    private val K = ByteArray(32) { (it * 7 + 1).toByte() }
    private val ANAHTAR = ByteArray(32) { (200 - it).toByte() }
    private val KIMLIK = "0123456789abcdef"
    private val N = 3
    private val ONEK = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
    private val KULLANICI = "sinama-kullanici"
    private val GIRIS = "sinama-giris-sozu"
    private val ADRES = "mqtts://araci.sinama.example:8883"
    private var nonceSayaci = 0

    private fun hx(b: ByteArray): String = b.joinToString("") { "%02x".format(it) }

    private fun muhurle(anahtar: ByteArray, aad: ByteArray, duz: ByteArray): ByteArray {
        val nonce = ByteArray(12).also { it[0] = (++nonceSayaci).toByte(); it[1] = (nonceSayaci shr 8).toByte() }
        val c = Cipher.getInstance("ChaCha20-Poly1305")
        c.init(Cipher.ENCRYPT_MODE, SecretKeySpec(anahtar, "ChaCha20"), IvParameterSpec(nonce))
        c.updateAAD(aad)
        return Zarf.SIHIR + nonce + c.doFinal(duz)
    }

    private fun json(v: Any?): String = when (v) {
        null -> "null"
        is String -> "\"" + v.replace("\\", "\\\\").replace("\"", "\\\"") + "\""
        is Map<*, *> -> v.entries.joinToString(",", "{", "}") { json(it.key as String) + ":" + json(it.value) }
        is List<*> -> v.joinToString(",", "[", "]") { json(it) }
        else -> v.toString()
    }

    private fun bilgiZarfi(
        uri: String = ADRES, k: ByteArray = K, kimlik: String = KIMLIK, n: Int = N, kullanici: String = KULLANICI, giris: String = GIRIS,
    ): ByteArray = muhurle(k, Zarf.bilgiAad(kimlik, n),
        json(mapOf("u" to uri, "k" to kullanici, "p" to giris, "o" to ONEK, "a" to hx(ANAHTAR))).toByteArray(Charsets.UTF_8))

    private fun yayin(son: String, icerik: Map<String, Any?>, anahtar: ByteArray = ANAHTAR, muhurKonusu: String? = null, onek: String = ONEK, kalici: Boolean = false): ByteArray {
        val konu = "ok/$onek/$son"
        val yuk = muhurle(anahtar, (muhurKonusu ?: konu).toByteArray(Charsets.UTF_8), json(icerik).toByteArray(Charsets.UTF_8))
        return MqttPaket.paket((3 shl 4) or (if (kalici) 1 else 0), MqttPaket.dize(konu) + yuk)
    }

    private val CONNACK = byteArrayOf(0x20, 0x02, 0x00, 0x00)
    private val SUBACK = byteArrayOf(0x90.toByte(), 0x03, 0x00, 0x01, 0x01)
    private val PINGRESP = byteArrayOf(0xd0.toByte(), 0x00)

    /** Abone olununca `yayinlar`i sirayla yollayan araci. */
    private fun araci(yayinlar: List<ByteArray> = emptyList(), connack: ByteArray = CONNACK): SahteAraci = SahteAraci { a, ilk, _ ->
        when (ilk shr 4) {
            MqttPaket.CONNECT -> connack
            MqttPaket.SUBSCRIBE -> { a.kuyruk.addLast(SUBACK); for (y in yayinlar) a.kuyruk.addLast(y); null }
            MqttPaket.PINGREQ -> PINGRESP
            else -> null
        }
    }

    private class Duzen(val izleyici: Izleyici, val karar: BildirimKarar, val cikan: List<Bildirim>, val adresler: List<AraciAdresi>)

    private fun kur(a: SahteAraci?, baglan: ((AraciAdresi) -> MqttBaglanti)? = null, pencere: Double = 900.0, yakin: Double = 120.0): Duzen {
        val cikan = ArrayList<Bildirim>()
        val adresler = ArrayList<AraciAdresi>()
        val karar = BildirimKarar({ cikan.add(it) }, { (a?.ms ?: 0L) / 1000.0 }, pencereS = pencere, yakinS = yakin)
        val i = Izleyici({ adres -> adresler.add(adres); baglan?.invoke(adres) ?: a!! }, karar, Any(), { a?.ms ?: 0L }, { "okm-sinama" })
        return Duzen(i, karar, cikan, adresler)
    }

    private val DURUM_KAYITTA = mapOf("c" to 1L, "a" to 3L, "t" to 1790000000L, "k" to 2L, "o" to 81L, "y" to 2L, "d" to 5L, "e" to 0L, "f" to "A3-test")

    // ── zincirin tamami ─────────────────────────────────────────────────────────────────────────

    @Test
    @Suppress("UNCHECKED_CAST")
    fun zincir_kararVektorundekiSenaryo_araciUzerindenAyniBildirimler() {
        val v = DuzJson.nesne(File("../../test/vektor/bildirim_karar.json").readText(Charsets.UTF_8))["senaryolar"] as List<Map<String, Any?>>
        val s = v.first { it["ad"] == "kayit_bitti_sebepler" }
        val ops = s["ops"] as List<List<Any?>>
        assertTrue(ops.all { it[0] == "mqtt" })
        val a = araci(ops.map { yayin(it[1] as String, it[2] as Map<String, Any?>) })
        val d = kur(a)
        a.zamanAsiminda = { d.izleyici.durdur() }
        var baglandi = 0
        val b = d.izleyici.calis(K, KIMLIK, N, bilgiZarfi(), baglandi = { baglandi++ })
        assertEquals("durduruldu", b.tur); assertEquals("tamam", b.sinif); assertTrue(b.baglandi)
        assertEquals(1, baglandi)
        assertEquals(ops.size, d.izleyici.cozulen); assertEquals(0, d.izleyici.atilan)
        val beklenen = ((s["beklenen"] as Map<*, *>)["bildirimler"] as List<List<Any?>>).map { listOf(it[0], it[1]) }
        assertEquals(beklenen, d.cikan.map { listOf(it.etiket, it.anahtar) })
        assertEquals(5, d.cikan.size)
    }

    @Test
    fun baglanti_zarftakiAdreseVeKimlikle_aboneligiOnekle_yalnizAbone() {
        val a = araci()
        val d = kur(a)
        a.zamanAsiminda = { d.izleyici.durdur() }
        d.izleyici.calis(K, KIMLIK, N, bilgiZarfi())
        assertEquals(1, d.adresler.size)
        assertEquals("araci.sinama.example", d.adresler[0].ad); assertEquals(8883, d.adresler[0].port)
        assertArrayEquals(MqttPaket.connect("okm-sinama", KULLANICI, GIRIS, MqttIstemci.KEEPALIVE_S).drop(2).toByteArray(), a.gelen[0].second)
        assertArrayEquals(MqttPaket.subscribe(1, "ok/$ONEK/#", 1).drop(2).toByteArray(), a.gelen[1].second)
        assertEquals(listOf(MqttPaket.CONNECT, MqttPaket.SUBSCRIBE, MqttPaket.DISCONNECT), a.turler())
        assertTrue(a.kapandi)
    }

    @Test
    fun bosKullaniciVeGiris_connecteKonmaz() {
        val a = araci()
        val d = kur(a)
        a.zamanAsiminda = { d.izleyici.durdur() }
        d.izleyici.calis(K, KIMLIK, N, bilgiZarfi(kullanici = "", giris = ""))
        assertArrayEquals(MqttPaket.connect("okm-sinama", null, null, MqttIstemci.KEEPALIVE_S).drop(2).toByteArray(), a.gelen[0].second)
    }

    @Test
    fun mqttBagli_oturumBoyuncaDogru_bitinceYanlis() {
        val a = araci()
        val d = kur(a)
        var surerken: Boolean? = null
        a.zamanAsiminda = { surerken = d.karar.mqttBagli; d.izleyici.durdur() }
        assertFalse(d.karar.mqttBagli)
        d.izleyici.calis(K, KIMLIK, N, bilgiZarfi())
        assertEquals(true, surerken)
        assertFalse(d.karar.mqttBagli)
    }

    // ── ayar hatalari: araciya HIC gidilmez ─────────────────────────────────────────────────────

    @Test
    fun zarfAcilmazsa_zarf_baglantiDenenmez() {
        for (bozuk in listOf(bilgiZarfi(k = ByteArray(32) { 9 }), bilgiZarfi(kimlik = "fedcba9876543210"), bilgiZarfi(n = N + 1), ByteArray(10), ByteArray(0))) {
            val d = kur(araci())
            val b = d.izleyici.calis(K, KIMLIK, N, bozuk)
            assertEquals("zarf", b.tur); assertEquals("ayar", b.sinif); assertFalse(b.baglandi)
            assertEquals(0, d.adresler.size)
        }
    }

    @Test
    fun adresGecersizse_adres_baglantiDenenmez() {
        val at = 64.toChar()
        for (uri in listOf("mqtt://araci.sinama.example:1883", "wss://araci.sinama.example", "mqtts://203.0.113.9:8883", "mqtts://kisi${at}araci.sinama.example", "mqtts://tekad")) {
            val d = kur(araci())
            val b = d.izleyici.calis(K, KIMLIK, N, bilgiZarfi(uri = uri))
            assertEquals(uri.take(6), "adres", b.tur); assertEquals("ayar", b.sinif)
            assertEquals(0, d.adresler.size)
        }
    }

    @Test
    fun baglantiHatalari_tlsGuven_agInternet() {
        val tls = kur(null, baglan = { throw AraciHatasi("tls") }).izleyici.calis(K, KIMLIK, N, bilgiZarfi())
        assertEquals("tls", tls.tur); assertEquals("guven", tls.sinif); assertFalse(tls.baglandi)
        val ag = kur(null, baglan = { throw AraciHatasi("ag") }).izleyici.calis(K, KIMLIK, N, bilgiZarfi())
        assertEquals("ag", ag.tur); assertEquals("internet", ag.sinif)
    }

    @Test
    fun connackReddi_4ve5AyarYenile_digerleriAraci() {
        for (kod in listOf(4, 5)) {
            val b = kur(araci(connack = byteArrayOf(0x20, 0x02, 0x00, kod.toByte()))).izleyici.calis(K, KIMLIK, N, bilgiZarfi())
            assertEquals("kimlik-ret", b.tur); assertEquals(kod, b.kod); assertEquals("ayar", b.sinif); assertFalse(b.baglandi)
        }
        val b = kur(araci(connack = byteArrayOf(0x20, 0x02, 0x00, 0x03))).izleyici.calis(K, KIMLIK, N, bilgiZarfi())
        assertEquals("ret", b.tur); assertEquals(3, b.kod); assertEquals("araci", b.sinif)
    }

    @Test
    fun aginKopmasi_internet_kartAlarmiDegil() {
        val a = araci(listOf(yayin("durum", DURUM_KAYITTA, kalici = true)))
        val d = kur(a)
        a.zamanAsiminda = { it.akisBitti = true }
        val b = d.izleyici.calis(K, KIMLIK, N, bilgiZarfi())
        assertEquals("koptu", b.tur); assertEquals("internet", b.sinif); assertTrue(b.baglandi)
        assertEquals(emptyList<String>(), d.cikan.map { it.anahtar })       // kayit suruyordu ama "karttan haber yok" YOK (A34)
        assertFalse(d.karar.mqttBagli)
    }

    // ── mesaj suzgeci (A32) ─────────────────────────────────────────────────────────────────────

    @Test
    fun etiketiTutmayanMesajAtilirVeSayilir_cozulenVarkenOturumSurer() {
        val bitti = mapOf("n" to 1L, "a" to 3L, "t" to 1790000100L, "o" to "kayit_bitti", "sebep" to 1L, "oturum" to 81L, "nokta" to 12L)
        val a = araci(listOf(
            yayin("durum", DURUM_KAYITTA),
            yayin("olay", bitti, anahtar = ByteArray(32) { 5 }),                       // yanlis anahtar
            yayin("olay", bitti, muhurKonusu = "ok/$ONEK/durum"),                       // baska konu icin muhurlenmis
            yayin("olay", bitti, anahtar = ByteArray(32) { 6 }),
            yayin("olay", bitti, anahtar = ByteArray(32) { 7 }),
            yayin("olay", bitti),
        ))
        val d = kur(a)
        a.zamanAsiminda = { d.izleyici.durdur() }
        val b = d.izleyici.calis(K, KIMLIK, N, bilgiZarfi())
        assertEquals("durduruldu", b.tur)
        assertEquals(4, d.izleyici.atilan); assertEquals(2, d.izleyici.cozulen)
        assertEquals(listOf("bld.kayit_bitti"), d.cikan.map { it.anahtar })
    }

    @Test
    fun hicMesajCozulemedenUcMesajAtilirsa_anahtar_ayarYenile() {
        val y = { yayin("durum", DURUM_KAYITTA, anahtar = ByteArray(32) { 5 }) }
        val iki = araci(listOf(y(), y()))
        val d2 = kur(iki)
        iki.zamanAsiminda = { d2.izleyici.durdur() }
        assertEquals("durduruldu", d2.izleyici.calis(K, KIMLIK, N, bilgiZarfi()).tur)     // sinirin altinda surer
        assertEquals(2, d2.izleyici.atilan)

        val d = kur(araci(listOf(y(), y(), y(), y())))
        val b = d.izleyici.calis(K, KIMLIK, N, bilgiZarfi())
        assertEquals("anahtar", b.tur); assertEquals("ayar", b.sinif); assertTrue(b.baglandi)
        assertEquals(3, Izleyici.ATILAN_SINIR)
        assertEquals(0, d.izleyici.cozulen)
        assertEquals(emptyList<Bildirim>(), d.cikan)
    }

    @Test
    fun onekDisiKonu_yokSayilir_sayilmaz() {
        val baska = "0".repeat(32)
        val a = araci(listOf(yayin("durum", DURUM_KAYITTA, onek = baska), yayin("durum", DURUM_KAYITTA, onek = baska), yayin("durum", DURUM_KAYITTA, onek = baska)))
        val d = kur(a)
        a.zamanAsiminda = { d.izleyici.durdur() }
        assertEquals("durduruldu", d.izleyici.calis(K, KIMLIK, N, bilgiZarfi()).tur)
        assertEquals(0, d.izleyici.atilan); assertEquals(0, d.izleyici.cozulen)
        assertNull(d.karar.kartCevrimici)
    }

    // ── tek seferlik okuma (A30) ────────────────────────────────────────────────────────────────

    @Test
    fun tekSefer_kaliciDurumOkununcaKapanir_sonrakiMesajIslenmez() {
        val bitti = mapOf("n" to 1L, "a" to 3L, "t" to 1790000100L, "o" to "kayit_bitti", "sebep" to 1L, "oturum" to 81L, "nokta" to 12L)
        val a = araci(listOf(yayin("durum", DURUM_KAYITTA, kalici = true)))
        val d = kur(a)
        val bas = a.ms
        var gorulen: Map<String, Any?>? = null
        val b = d.izleyici.calis(K, KIMLIK, N, bilgiZarfi(), tekSefer = true, durumGoruldu = { gorulen = it })
        assertEquals("durum-okundu", b.tur); assertEquals("tamam", b.sinif); assertTrue(b.baglandi)
        assertEquals(DURUM_KAYITTA, gorulen)                                               // yoklama bunu karsilastirir (A30)
        assertEquals(true, d.karar.kayitSuruyor())
        assertEquals(0L, a.ms - bas)                                                       // beklemeden
        assertEquals(MqttPaket.DISCONNECT, a.turler().last())
        // Olay, durumdan ONCE gelirse islenir; durum gelince kapanir.
        val a2 = araci(listOf(yayin("olay", bitti), yayin("durum", DURUM_KAYITTA)))
        val d2 = kur(a2)
        assertEquals("durum-okundu", d2.izleyici.calis(K, KIMLIK, N, bilgiZarfi(), tekSefer = true).tur)
        assertEquals(listOf("bld.kayit_bitti"), d2.cikan.map { it.anahtar })
        assertEquals(true, d2.karar.kartCevrimici)                                         // durum da islendi (olayda kapanmadi)
    }

    @Test
    fun tekSefer_durumGelmezse_20SaniyedeSureIleKapanir_surekliKipSurer() {
        val a = araci()
        val d = kur(a)
        val bas = a.ms
        val b = d.izleyici.calis(K, KIMLIK, N, bilgiZarfi(), tekSefer = true)
        assertEquals("sure", b.tur); assertEquals("tamam", b.sinif)
        assertTrue("${a.ms - bas}", a.ms - bas in 20_000L..21_000L)
        assertEquals(20_000L, Izleyici.TEK_SEFER_MS)
        // Surekli kip ayni surede KAPANMAZ (ve kalici durum gelse de surer).
        val a2 = araci(listOf(yayin("durum", DURUM_KAYITTA, kalici = true)))
        val d2 = kur(a2)
        val bas2 = a2.ms
        a2.zamanAsiminda = { if (it.ms - bas2 >= 60_000) d2.izleyici.durdur() }
        assertEquals("durduruldu", d2.izleyici.calis(K, KIMLIK, N, bilgiZarfi()).tur)
        assertTrue(a2.ms - bas2 >= 60_000)
    }

    // ── saat isleri ve durdurma ─────────────────────────────────────────────────────────────────

    @Test
    fun tik_oturumBoyuncaKararaUlasir_yerelYolKopuguBildirilir() {
        val a = araci()
        val d = kur(a)
        d.karar.yerelG(2, 53)                                                              // yerelde kayit suruyor goruldu
        val bas = a.ms
        a.zamanAsiminda = { if (it.ms - bas >= 30_000) d.izleyici.durdur() }
        d.izleyici.calis(K, KIMLIK, N, bilgiZarfi())
        assertEquals(listOf("bld.kopuk_yerel"), d.cikan.map { it.anahtar })               // 20 s yerel sessizlik (tik olmadan cikmaz)
    }

    @Test
    fun durdur_baslamadanOnceCagrilirsaBaglanmaz_sirasindaCagrilirsaBiter() {
        val d = kur(araci())
        d.izleyici.durdur()
        val b = d.izleyici.calis(K, KIMLIK, N, bilgiZarfi())
        assertEquals("durduruldu", b.tur); assertFalse(b.baglandi)
        assertEquals(0, d.adresler.size)
    }

    // ── kayit bitince durma (A28) ───────────────────────────────────────────────────────────────

    @Test
    fun surdurHayirDerse_10SaniyeSonraGerekKalmadi_oAradaGelenMesajIslenir() {
        val bitti = mapOf("n" to 1L, "a" to 3L, "t" to 1790000100L, "o" to "kayit_bitti", "sebep" to 1L, "oturum" to 81L, "nokta" to 12L)
        val a = araci(listOf(yayin("durum", DURUM_KAYITTA, kalici = true)))
        val d = kur(a)
        val bas = a.ms
        var gonderildi = false
        a.zamanAsiminda = { if (!gonderildi && it.ms - bas >= 5_000) { gonderildi = true; it.kuyruk.addLast(yayin("olay", bitti)) } }
        val b = d.izleyici.calis(K, KIMLIK, N, bilgiZarfi(), surdur = { false })
        assertEquals("gerek-kalmadi", b.tur); assertEquals("tamam", b.sinif); assertTrue(b.baglandi)
        assertTrue("${a.ms - bas}", a.ms - bas in 10_000L..11_000L)
        assertEquals(10_000L, Izleyici.GEREKSIZ_MS)
        assertEquals(listOf("bld.kayit_bitti"), d.cikan.map { it.anahtar })               // bekleme surerken gelen ayrinti kaybolmadi
        assertEquals(MqttPaket.DISCONNECT, a.turler().last())
    }

    @Test
    fun surdurYenidenEvetDerse_sayacSifirlanir_varsayilandaHicDurmaz() {
        val a = araci()
        val d = kur(a)
        val bas = a.ms
        // 0–8 s hayir, 8–9 s evet, sonra hep hayir: bitis 9 s + 10 s'den ONCE olamaz.
        val b = d.izleyici.calis(K, KIMLIK, N, bilgiZarfi(), surdur = { (a.ms - bas) in 8_000L..9_000L })
        assertEquals("gerek-kalmadi", b.tur)
        assertTrue("${a.ms - bas}", a.ms - bas in 19_000L..20_500L)

        val a2 = araci()
        val d2 = kur(a2)
        val bas2 = a2.ms
        a2.zamanAsiminda = { if (it.ms - bas2 >= 60_000) d2.izleyici.durdur() }
        assertEquals("durduruldu", d2.izleyici.calis(K, KIMLIK, N, bilgiZarfi()).tur)     // surdur verilmezse sure siniri yok
    }

    // ── yeniden deneme ve sir ───────────────────────────────────────────────────────────────────

    @Test
    fun bekleme_ayarVeTamamDenenmez_internetHizli_guvenVeAraciSeyrek() {
        fun b(tur: String, deneme: Int) = Izleyici.bekleme(IzlemeBitis(tur), deneme)
        for (tur in listOf("zarf", "adres", "kimlik-ret", "anahtar", "durduruldu", "durum-okundu", "sure", "gerek-kalmadi")) assertNull(tur, b(tur, 1))
        for (tur in listOf("ag", "koptu", "sessiz", "zaman-asimi")) {
            assertEquals(tur, listOf(2_000L, 5_000L, 10_000L, 30_000L, 60_000L, 60_000L, 60_000L), (1..7).map { b(tur, it) })
            assertEquals(2_000L, b(tur, 0))
        }
        for (tur in listOf("tls", "ret", "abone-ret", "bicim", "bilinmeyen-tur")) {
            assertEquals(tur, listOf(60_000L, 300_000L, 900_000L, 900_000L), (1..4).map { b(tur, it) })
        }
    }

    @Test
    fun bitisNesnesiVeIstemciKimligi_sirTasimaz() {
        val a = araci(listOf(yayin("durum", DURUM_KAYITTA)))
        val d = kur(a)
        a.zamanAsiminda = { it.okumaHatasi = true }
        val b = d.izleyici.calis(K, KIMLIK, N, bilgiZarfi())
        assertEquals("koptu", b.tur)
        assertEquals(setOf("tur", "kod", "baglandi"), IzlemeBitis::class.java.declaredFields.map { it.name }.toSet())
        for (sir in listOf("araci.sinama", ONEK, KULLANICI, GIRIS, hx(ANAHTAR), KIMLIK, "gizli-ayrinti")) assertFalse(b.toString().contains(sir))
        val k1 = Izleyici.rastgeleKimlik(); val k2 = Izleyici.rastgeleKimlik()
        assertTrue(Regex("^okm-[0-9a-f]{16}$").matches(k1))
        assertNotEquals(k1, k2)
    }
}
