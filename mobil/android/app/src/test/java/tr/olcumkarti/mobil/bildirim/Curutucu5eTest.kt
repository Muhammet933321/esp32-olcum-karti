package tr.olcumkarti.mobil.bildirim

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test
import java.io.InputStream
import java.io.OutputStream
import java.nio.file.Files
import javax.crypto.Cipher
import javax.crypto.spec.IvParameterSpec
import javax.crypto.spec.SecretKeySpec

/**
 * 5E BAGIMSIZ CURUTUCU — Kotlin kanitlari. Her test "dogru davranisi" bekler: bulgu VARKEN KIRMIZI.
 * Kosmak icin bu dosya GECICI olarak android/app/src/test/java/tr/olcumkarti/mobil/bildirim/ altina
 * kopyalanir (SahteAraci oradadir), kostuktan sonra silinir. Ayrinti: ../BULGULAR.md.
 * Butun degerler sinama degeridir (gercek adres / sir yok).
 */
class Curutucu5eTest {
    private val K = ByteArray(32) { (it * 7 + 1).toByte() }
    private val ANAHTAR = ByteArray(32) { (200 - it).toByte() }
    private val BASKA_ANAHTAR = ByteArray(32) { (it + 9).toByte() }
    private val KIMLIK = "0123456789abcdef"
    private val N = 3
    private val ONEK = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
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
        is String -> "\"" + v + "\""
        is Map<*, *> -> v.entries.joinToString(",", "{", "}") { json(it.key as String) + ":" + json(it.value) }
        else -> v.toString()
    }

    private fun bilgiZarfi(): ByteArray = muhurle(K, Zarf.bilgiAad(KIMLIK, N),
        json(mapOf("u" to ADRES, "k" to "sinama-kullanici", "p" to "sinama-giris", "o" to ONEK, "a" to hx(ANAHTAR))).toByteArray(Charsets.UTF_8))

    private fun yayin(son: String, icerik: Map<String, Any?>, anahtar: ByteArray = ANAHTAR, kalici: Boolean = false): ByteArray {
        val konu = "ok/$ONEK/$son"
        val yuk = muhurle(anahtar, konu.toByteArray(Charsets.UTF_8), json(icerik).toByteArray(Charsets.UTF_8))
        return MqttPaket.paket((3 shl 4) or (if (kalici) 1 else 0), MqttPaket.dize(konu) + yuk)
    }

    private val CONNACK = byteArrayOf(0x20, 0x02, 0x00, 0x00)
    private val SUBACK = byteArrayOf(0x90.toByte(), 0x03, 0x00, 0x01, 0x01)
    private val PINGRESP = byteArrayOf(0xd0.toByte(), 0x00)

    private fun araci(yayinlar: List<ByteArray>): SahteAraci = SahteAraci { a, ilk, _ ->
        when (ilk shr 4) {
            MqttPaket.CONNECT -> CONNACK
            MqttPaket.SUBSCRIBE -> { a.kuyruk.addLast(SUBACK); for (y in yayinlar) a.kuyruk.addLast(y); null }
            MqttPaket.PINGREQ -> PINGRESP
            else -> null
        }
    }

    private fun durum(k: Long, o: Long, a: Long = 3L): Map<String, Any?> =
        mapOf("c" to 1L, "a" to a, "t" to 1790000000L, "k" to k, "o" to o, "y" to 1L)

    // ── B1: 15 dakikalik yoklama eskimis bildirim anahtarini HIC fark etmez ─────────────────────────
    // Tek seferlik oturumda araci yalniz BIR kalici mesaj (durum) yollar; ATILAN_SINIR = 3'e hic ulasilmaz.
    // Sonuc: tur "sure" (sinif "tamam") -> YoklamaIsi ne bildirim ne "ayar yenilenmeli" uretir; sonsuza dek sessiz.
    @Test
    fun b1_yoklama_eskimisAnahtarla_ayarYenilenmeliDemeli() {
        val a = araci(listOf(yayin("durum", durum(2, 81), anahtar = BASKA_ANAHTAR, kalici = true)))
        val i = Izleyici({ a }, BildirimKarar({}, { a.ms / 1000.0 }), Any(), { a.ms }, { "okm-sinama" })
        var okunan: Map<String, Any?>? = null
        val b = i.calis(K, KIMLIK, N, bilgiZarfi(), tekSefer = true, durumGoruldu = { okunan = it })
        assertEquals(1, i.atilan); assertEquals(0, i.cozulen); assertEquals(null, okunan)
        // Kartin anahtari degismis (QR!): kullaniciya "bildirim ayari yenilenmeli" denmeli (A31).
        assertEquals("yoklama eskimis anahtari fark etmeli (tur=${b.tur})", "ayar", b.sinif)
    }

    // ── B2: araciya yazabilen biri uc cozulmeyen mesajla izlemeyi KALICI olarak "ayar"a dusurur ────────
    // Kalici (retained) cop mesajlar her abonelikte gecerli durumdan ONCE gelebilir: cozulen == 0 iken 3 atilan.
    @Test
    fun b2_ucSahteMesaj_gecerliDurumdanOnceGelirse_izlemeAyaraDusmemeli() {
        val cop = (1..3).map { MqttPaket.paket((3 shl 4) or 1, MqttPaket.dize("ok/$ONEK/x$it") + Zarf.SIHIR + ByteArray(40) { 7 }) }
        val a = araci(cop + listOf(yayin("durum", durum(2, 81), kalici = true)))
        val cikan = ArrayList<Bildirim>()
        val karar = BildirimKarar({ cikan.add(it) }, { a.ms / 1000.0 })
        val i = Izleyici({ a }, karar, Any(), { a.ms }, { "okm-sinama" })
        a.zamanAsiminda = { i.durdur() }
        val b = i.calis(K, KIMLIK, N, bilgiZarfi())
        assertNotEquals("uc cop mesaj 'anahtar eskidi' saydirdi; gecerli durum hic islenmedi", "anahtar", b.tur)
        assertEquals(1, i.cozulen)
        assertEquals(true, karar.kayitSuruyor())
    }

    // ── B3: kart yeniden baslayinca ilk izlenen kayitta SAHTE "1 olay kacirildi" ──────────────────────
    // Kart her acilista n=1 "basladi" (devam=0, bildirimi YOK) yayinlar; servis yalniz kayit surerken calisir,
    // o olayi hic goremez. Ilk gordugu olay (n=2) "kacirilan 1" bildirimi uretir — her guc kesmesinden sonra.
    @Test
    fun b3_yeniAcilistaIlkIzlenenKayit_kacirilanBildirimiCikmamali() {
        val cikan = ArrayList<Bildirim>()
        val k = BildirimKarar({ cikan.add(it) }, { 0.0 }, onceki = Pair(3L, 2L))       // onceki izleme: acilis 3, son olay 2
        // acilis 4: n=1 "basladi" (devam 0) servis yokken yayinlandi; servis kayitla basladi, kayit bitti:
        k.mqttMesaj("olay", mapOf("n" to 2L, "a" to 4L, "t" to 1790000100L, "o" to "kayit_bitti", "sebep" to 1L, "oturum" to 9L, "nokta" to 10L))
        assertEquals("kacirilan tek olay bildirimi OLMAYAN acilis 'basladi'si; kullaniciya 'olay kacirildi' denmemeli",
            emptyList<String>(), cikan.filter { it.sinif == "kacirilan" }.map { it.anahtar })
    }

    // ── B4: servisin YEREL yoldan bildirdigi "kayit bitti"yi yoklama 15 dk sonra YENIDEN bildirir ─────
    // IzlemeServisi ozeti yalniz MQTT durum mesajinda gunceller (IzlemeServisi.kt durumGoruldu). Bitis yerel
    // akistan duyulduysa ve kartin MQTT durumu servis kapanmadan (10 s) gelmediyse (ev interneti kesik — A36)
    // ozet "kayit suruyor"da kalir.
    @Test
    fun b4_servisinYerelYoldanBildirdigiBitis_yoklamadaYinelenmemeli() {
        var t = 0.0
        val servis = ArrayList<Bildirim>()
        val k = BildirimKarar({ servis.add(it) }, { t })
        var ozet: YoklamaDurumu? = null
        fun mqttDurum(d: Map<String, Any?>) {                         // Izleyici.mesaj + IzlemeServisi.durumGoruldu
            k.mqttMesaj("durum", d)
            ozet = Yoklama.ozet(ozet, d, k.baglanti != null)
        }
        mqttDurum(durum(2, 81))
        k.yerelG(2, 81)                                               // uygulama onde: yerel akis
        t = 60.0
        k.yerelG(1, 0)                                                // kayit bitti: yerel akistan duyuldu
        ozet = Yoklama.ozetYerel(ozet, 1, 0)                          // DUZELTME (B4): IzlemeServisi yerel haberde de ozeti ilerletir
        assertEquals(listOf("os-51"), servis.map { it.etiket })       // servis bildirdi
        assertEquals(false, k.kayitSuruyor())                         // 10 s sonra "gerek-kalmadi": servis durur
        val yoklama = ArrayList<Bildirim>()
        Yoklama.degerlendir(ozet, durum(1, 0), { true }) { yoklama.add(it) }      // 15 dk sonra
        assertEquals("yoklama servisin bildirdigini yineledi", emptyList<String>(), yoklama.map { it.etiket + ":" + it.anahtar })
    }

    // ── B5: araciya ulasilamiyorken servis kayit bitse de KENDINI DURDURMAZ (A28) ─────────────────────
    // `surdur` yalniz Izleyici.calis icindeki tikte (BAGLIYKEN) sorulur; IzlemeDongusu bagli degilken kayit
    // durumuna hic bakmaz. Telefon kartin AP'sindeyse / interneti yoksa kalici bildirim sonsuza dek kalir.
    @Test
    fun b5_internetYokkenKayitBittiyse_donguBitmeli() {
        val k = BildirimKarar({}, { 0.0 })
        val kilit = Any()
        k.yerelG(2, 81); k.yerelG(1, 0)                               // uygulama onde: kayit bitti (yerel akis)
        assertEquals(false, k.kayitSuruyor())
        class Yeter : RuntimeException()
        var tur = 0
        val d = IzlemeDongusu(
            oturum = { baglandi ->                                    // IzlemeServisi.calis'taki oturumun aynisi
                Izleyici({ throw AraciHatasi("ag") }, k, kilit).calis(K, KIMLIK, N, bilgiZarfi(), baglandi = baglandi,
                    surdur = { synchronized(kilit) { k.kayitSuruyor() != false } })
            },
            bekle = { if (++tur > 50) throw Yeter() },
            durum = {},
        )
        val bitis = try { d.calis() } catch (e: Yeter) { "50 denemeden sonra hala donuyor" }
        assertEquals("kayit-bitti", bitis)
    }

    // ── B6: SUBACK'ten once gelen PUBLISH'ler SINIRSIZ biriktirilir (bellek) ──────────────────────────
    @Test
    fun b6_subacktenOnceYayinSeli_bellektekiBirikimSinirliOlmali() {
        var saat = 0L
        var verilen = 0L
        var asama = 0
        val sel = MqttPaket.paket(3 shl 4, MqttPaket.dize("ok/$ONEK/durum") + ByteArray(4000))      // tek okumaya sigar
        val yol = object : MqttBaglanti {
            override val giris = object : InputStream() {
                override fun read(): Int = throw UnsupportedOperationException()
                override fun read(b: ByteArray): Int {
                    val p = if (asama++ == 0) CONNACK else sel
                    System.arraycopy(p, 0, b, 0, p.size); verilen += p.size; return p.size
                }
            }
            override val cikis = object : OutputStream() { override fun write(b: Int) {} }
            override fun okumaSuresi(ms: Int) {}
            override fun kapat() {}
        }
        val b = MqttIstemci(yol) { saat++ }.calis("okm-sinama", null, null, "ok/$ONEK/#", {}, {})
        // Araci SUBACK yollamadan el sikisma suresi boyunca yayin akitti; istemci hepsini bellekte tuttu.
        assertTrue("SUBACK beklenirken ${verilen / 1024} KiB yayin biriktirildi (bitis ${b.tur})", verilen <= 64L * MqttPaket.PAKET_AZAMI)
    }

    // ── B7: ayristirici, sinirin ALTINDAKI paketlerden olusan gecerli akisi "buyuk" diye reddeder ─────
    @Test
    fun b7_azamiBoydaIkiPaket_4096lukOkumalarla_buyukDenmemeli() {
        val p = MqttPaket.paket(3 shl 4, ByteArray(MqttPaket.PAKET_AZAMI))                 // tam sinirda: KABUL edilmeli
        val akis = p + p
        val ayr = MqttPaket.Ayristirici()
        var paket = 0
        var i = 0
        try {
            while (true) {                                            // MqttIstemci.paketAl ile ayni sira
                while (ayr.sonraki() != null) paket++
                if (i >= akis.size) break
                val n = minOf(4096, akis.size - i)
                ayr.besle(akis.copyOfRange(i, i + n), n)
                i += n
            }
        } catch (e: MqttHatasi) {
            fail("gecerli akis '${e.tur}' diye reddedildi ($i. baytta, $paket paket cozuldu)")
        }
        assertEquals(2, paket)
    }

    // ── B8: adresYaz'in kabul ettigi adresi adresOku okuyamaz (A36 sessizce devre disi) ───────────────
    @Test
    fun b8_yazilanAdres_okunabilmeli() {
        val dizin = Files.createTempDirectory("curutucu5e").toFile()
        try {
            val depo = BildirimDeposu(dizin)
            for (adres in listOf("http://192.168.100.100:8080", " 192.168.100.100:8080 ", "http://192.168.1.107/")) {
                depo.adresYaz(KIMLIK, adres)                          // hata yok: "yazildi"
                assertNotNull("yazilan adres okunamiyor: boy ${adres.length}", depo.adresOku(KIMLIK))
            }
        } finally {
            dizin.deleteRecursively()
        }
    }

    // ── B9: "kati" JSON okuyucu \u kacisinda ASCII olmayan rakamlari kabul eder ──────────────────────
    @Test
    fun b9_json_uKacisindaYalnizAsciiOnaltilik() {
        val arapRakamli = "\"\\u\u0660\u0660\u0664\u0661\""            // \u + Arap-Hint 0 0 4 1
        val sonuc = try { DuzJson.oku(arapRakamli) } catch (e: JsonHatasi) { null }
        assertEquals("RFC 8259: \\u ardindan 4 ASCII onaltilik hane; bu girdi REDDEDILMELI", null, sonuc)
    }

    // ── B10: yoklama, k / o alani eksik bir durum mesajinda "kayit bitti"yi SESSIZCE kaybeder ─────────
    @Test
    fun b10_eksikAlanliDurum_kayitDurumuOzettenSilinmemeli() {
        val cikan = ArrayList<Bildirim>()
        val eksik = mapOf<String, Any?>("c" to 1L, "a" to 3L, "t" to 1790000000L)                  // k ve o yok
        val s1 = Yoklama.degerlendir(YoklamaDurumu(durum(2, 81), false), eksik, { true }) { cikan.add(it) }
        val s2 = Yoklama.degerlendir(s1.durum, durum(1, 0), { true }) { cikan.add(it) }
        assertFalse(s2.kayitSuruyor)
        assertEquals("kayit bitti (oturum 81) hic bildirilmedi", listOf("os-51"), cikan.map { it.etiket })
    }

    // ── B11: canli akis sururken 20 s sonra SAHTE "karttan haber yok" (yerel yol) ─────────────────────
    // PC'de HER kart satiri "yerelde goruldu" saatini tazeler; telefonda servise yalniz G DEGISINCE haber gider.
    // Araci bagli ama kalici durum mesaji henuz yok / gelmediyse (kartCevrimici == null) 20 s sonra tik()
    // "yerel yol sessiz" der.
    @Test
    fun b11_kaliciDurumYokken_yerelGdenYirmiSaniyeSonra_kopukDenmemeli() {
        val a = araci(emptyList())                                    // aracida kalici durum mesaji YOK
        val cikan = ArrayList<Bildirim>()
        val karar = BildirimKarar({ cikan.add(it) }, { a.ms / 1000.0 })
        karar.yerelG(2, 81)                                           // uygulama onde: kayit suruyor (tek haber)
        val i = Izleyici({ a }, karar, Any(), { a.ms }, { "okm-sinama" })
        val bas = a.ms
        a.zamanAsiminda = { if (it.ms - bas > 45_000) i.durdur() }
        i.calis(K, KIMLIK, N, bilgiZarfi())
        assertEquals("kart yerelde akmaya devam ediyor; kopukluk bildirimi cikmamali", emptyList<String>(), cikan.map { it.anahtar })
    }
}

/** Curutucu 5E'nin YASAYAN mutasyonlari icin eklenen testler (K05, K09, K16, K18, K26) + B4 / B18'in saf yarilari. */
class Curutucu5eEkTest {
    private val KIMLIK = "0123456789abcdef"

    @Test
    fun k05_connackYerineBaskaPaket_bicim() {
        val a = SahteAraci { _, ilk, _ -> if (ilk shr 4 == MqttPaket.CONNECT) byteArrayOf(0x40, 0x02, 0x00, 0x00) else null }      // PUBACK: govdesi CONNACK gibi 2 bayt, kod 0
        val b = MqttIstemci(a) { a.ms }.calis("okm-sinama", null, null, "ok/x/#", {}, {})
        assertEquals("bicim", b.tur)
        assertEquals(listOf(MqttPaket.CONNECT), a.turler())                       // abone olmaya calisilmadi
    }

    @Test
    fun k26_zarfCoz_anahtarBoyuTutmazsaBicim_etiketDegil() {
        val veri = Zarf.SIHIR + ByteArray(40) { 3 }
        assertEquals("bicim", try { Zarf.coz(ByteArray(31), ByteArray(0), veri); null } catch (e: ZarfHatasi) { e.tur })
        assertEquals("bicim", try { Zarf.coz(ByteArray(33), ByteArray(0), veri); null } catch (e: ZarfHatasi) { e.tur })
        assertEquals("etiket", try { Zarf.coz(ByteArray(32), ByteArray(0), veri); null } catch (e: ZarfHatasi) { e.tur })
    }

    @Test
    fun b4_ozetYerel_kayitDurumuIlerler_digerAlanlarKorunur_ilkHaberdeDeCalisir() {
        val onceki = YoklamaDurumu(mapOf("c" to 1L, "a" to 3L, "t" to 1790000000L, "k" to 2L, "o" to 81L, "y" to 1L), true)
        val yeni = Yoklama.ozetYerel(onceki, 1, 0)
        assertEquals(mapOf<String, Any?>("c" to 1L, "a" to 3L, "t" to 1790000000L, "k" to 1L, "o" to 0L, "y" to 1L), yeni.cevrimici)
        assertTrue(yeni.kopuk)                                                    // "haber yok" bayragina dokunulmaz
        val ilk = Yoklama.ozetYerel(null, 2, 81)
        assertEquals(mapOf<String, Any?>("c" to 1L, "k" to 2L, "o" to 81L), ilk.cevrimici); assertFalse(ilk.kopuk)
        // Yerel yoldan bildirilen bitis yoklamada yinelenmez; SONRAKI gercek degisiklik yine bildirilir.
        val cikan = ArrayList<String>()
        val s = Yoklama.degerlendir(yeni.let { YoklamaDurumu(it.cevrimici, false) }, mapOf("c" to 1L, "a" to 3L, "t" to 1L, "k" to 2L, "o" to 82L, "y" to 1L), { true }) { cikan.add(it.anahtar) }
        assertEquals(emptyList<String>(), cikan)
        Yoklama.degerlendir(s.durum, mapOf("c" to 1L, "a" to 3L, "t" to 1L, "k" to 1L, "o" to 82L, "y" to 1L), { true }) { cikan.add(it.anahtar) }
        assertEquals(listOf("bld.kayit_bitti_yerel"), cikan)
    }

    @Test
    fun b8_adresSadeYazilir_onEkBoslukVeSondakiBolu_olmadan() {
        val dizin = Files.createTempDirectory("curutucu5e-ek").toFile()
        try {
            val depo = BildirimDeposu(dizin)
            depo.adresYaz(KIMLIK, "http://192.168.100.100:8080/")
            assertEquals("192.168.100.100:8080", depo.adresOku(KIMLIK))
            depo.adresYaz(KIMLIK, " 10.0.0.5 ")
            assertEquals("10.0.0.5:80", depo.adresOku(KIMLIK))
            assertEquals("192.168.1.7:80", YerelYoklama.sade("192.168.1.7"))
            assertEquals(null, YerelYoklama.sade("8.8.8.8")); assertEquals(null, YerelYoklama.sade("olcum.local")); assertEquals(null, YerelYoklama.sade(null))
        } finally {
            dizin.deleteRecursively()
        }
    }

    @Test
    fun b3_ayniCalismadakiBosluk_yineSayilir_pcDavranisiAcilabilir() {
        val cikan = ArrayList<Bildirim>()
        val k = BildirimKarar({ cikan.add(it) }, { 0.0 }, onceki = Pair(3L, 2L))
        fun olay(n: Long) = mapOf<String, Any?>("n" to n, "a" to 4L, "t" to 1L, "o" to "deneme")
        k.mqttMesaj("olay", olay(2)); k.mqttMesaj("olay", olay(3))
        assertEquals(0L, k.kacirilan)
        k.mqttMesaj("olay", olay(6))                                              // servis BAGLIYKEN kacan iki olay sayilir
        assertEquals(2L, k.kacirilan)
        assertEquals(1, cikan.count { it.sinif == "kacirilan" })
        val pc = BildirimKarar({}, { 0.0 }, onceki = Pair(3L, 2L), acilisBoslugu = true)
        pc.mqttMesaj("olay", olay(2))
        assertEquals(1L, pc.kacirilan)                                            // PC: yeni acilisin n=1'i kacirilmis sayilir
    }

    @Test
    fun b6_bekleyenYayinSiniri_asilincaBicim() {
        assertEquals(64, MqttIstemci.BEKLEYEN_AZAMI)
    }

    @Test
    fun k09_olayMesaji_durumGorulduSayilmaz() {
        // Yoklama yalniz DURUM mesajini karsilastirir: olay mesaji "okunan durum" olarak verilirse ozet bozulur.
        val K = ByteArray(32) { (it * 7 + 1).toByte() }
        val anahtar = ByteArray(32) { (200 - it).toByte() }
        val onek = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
        var sayac = 0
        fun muhurle(a: ByteArray, aad: ByteArray, duz: ByteArray): ByteArray {
            val nonce = ByteArray(12).also { it[0] = (++sayac).toByte() }
            val c = Cipher.getInstance("ChaCha20-Poly1305")
            c.init(Cipher.ENCRYPT_MODE, SecretKeySpec(a, "ChaCha20"), IvParameterSpec(nonce)); c.updateAAD(aad)
            return Zarf.SIHIR + nonce + c.doFinal(duz)
        }
        val hx = anahtar.joinToString("") { "%02x".format(it) }
        val zarf = muhurle(K, Zarf.bilgiAad(KIMLIK, 3), "{\"u\":\"mqtts://araci.sinama.example:8883\",\"k\":\"\",\"p\":\"\",\"o\":\"$onek\",\"a\":\"$hx\"}".toByteArray())
        fun yayin(son: String, json: String): ByteArray {
            val konu = "ok/$onek/$son"
            return MqttPaket.paket(3 shl 4, MqttPaket.dize(konu) + muhurle(anahtar, konu.toByteArray(), json.toByteArray()))
        }
        val a = SahteAraci { arc, ilk, _ ->
            when (ilk shr 4) {
                MqttPaket.CONNECT -> byteArrayOf(0x20, 0x02, 0x00, 0x00)
                MqttPaket.SUBSCRIBE -> {
                    arc.kuyruk.addLast(byteArrayOf(0x90.toByte(), 0x03, 0x00, 0x01, 0x01))
                    arc.kuyruk.addLast(yayin("olay", "{\"n\":1,\"a\":3,\"o\":\"deneme\"}"))
                    arc.kuyruk.addLast(yayin("durum", "{\"c\":1,\"a\":3,\"t\":5,\"k\":2,\"o\":81,\"y\":1}"))
                    null
                }
                MqttPaket.PINGREQ -> byteArrayOf(0xd0.toByte(), 0x00)
                else -> null
            }
        }
        val gorulen = ArrayList<Map<String, Any?>>()
        val i = Izleyici({ a }, BildirimKarar({}, { 0.0 }), Any(), { a.ms }, { "okm-sinama" })
        val b = i.calis(K, KIMLIK, 3, zarf, tekSefer = true, durumGoruldu = { gorulen.add(it) })
        assertEquals("durum-okundu", b.tur)
        assertEquals(1, gorulen.size)
        assertEquals(81L, gorulen[0]["o"])
    }
}
