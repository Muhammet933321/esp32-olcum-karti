package tr.olcumkarti.mobil.bildirim

import java.security.SecureRandom

/**
 * Bir izleme oturumunun nasil bittigi. `tur` SABIT bir addir (A45, sart S3: araci adresi, kullanici, konu,
 * anahtar hicbir alana girmez); `sinif` cagirana NE YAPACAGINI soyler:
 *   ayar     : zarf (K ile acilmadi) · adres (araci adresi gecersiz) · kimlik-ret (CONNACK 4/5) · anahtar
 *              (mesajlar cozulmuyor) -> "bildirim ayari yenilenmeli, uygulamayi kartin aginda ac" (A31);
 *              zarf dosyasi DEGISMEDEN yeniden denenmez
 *   internet : ag · koptu · sessiz · zaman-asimi -> "telefonun interneti yok" (A34); kart icin alarm DEGIL
 *   guven    : tls (sertifika / ad dogrulanamadi, S2) -> baglanilmaz, seyrek yeniden denenir
 *   araci    : ret (baska CONNACK kodu) · abone-ret · bicim -> seyrek yeniden denenir
 *   tamam    : durduruldu · durum-okundu · sure (tek seferlik okumanin iki bitisi) · gerek-kalmadi
 *              (`surdur` GEREKSIZ_MS boyunca "hayir" dedi: kayit bitti — A28)
 */
class IzlemeBitis(val tur: String, val kod: Int = 0, val baglandi: Boolean = false) {
    val sinif: String
        get() = when (tur) {
            "zarf", "adres", "kimlik-ret", "anahtar" -> "ayar"
            "ag", "koptu", "sessiz", "zaman-asimi" -> "internet"
            "tls" -> "guven"
            "durduruldu", "durum-okundu", "sure", "gerek-kalmadi" -> "tamam"
            else -> "araci"
        }

    override fun toString(): String = "IzlemeBitis($tur)"
}

/**
 * Zarf -> araci -> karar zinciri (tasarim A30–A34): kartin `/bildirim/bilgi` zarfini K ile acar, araciya TLS
 * ile baglanir, `ok/<onek>/#`'a abone olur, her mesaji kendi zarfindan cikarip `BildirimKarar`'a verir.
 *  - cozulmus araci bilgisi YALNIZ bu cagri boyunca bellekte; anahtar cikista sifirlanir
 *  - onek disi ve bilinmeyen alt konu (durum / olay disi) yok sayilir; etiketi tutmayan mesaj ATILIR ve
 *    sayilir (A32). Hic mesaj cozulemeden ATILAN_SINIR mesaj atildiysa (tek seferlik okumada: kalici durum
 *    cozulemediyse) anahtar degismistir (kartta QR!): oturum "anahtar" ile biter
 *  - `tekSefer` (WorkManager isi, A30): kalici durum mesaji islenince ya da `sureMs` dolunca kapanir
 *  - `karar` cagrilari `kilit` altinda (servis ayni karar nesnesine yerel haberleri baska is parcacigindan verir)
 * Saf Kotlin: baglanti fabrikasi ve saat enjekte, JVM'de sahte araciyla sinanir.
 */
class Izleyici(
    private val baglan: (AraciAdresi) -> MqttBaglanti,
    private val karar: BildirimKarar,
    private val kilit: Any,
    private val simdiMs: () -> Long = { System.nanoTime() / 1_000_000 },
    private val istemciId: () -> String = ::rastgeleKimlik,
) {
    @Volatile private var dur = false
    @Volatile private var istemci: MqttIstemci? = null

    /** Bu oturumda zarfindan cikan / atilan mesaj sayisi (tani; icerik degil). */
    @Volatile var cozulen = 0
        private set
    @Volatile var atilan = 0
        private set

    /** Baska is parcacigindan: oturumu bitirir. */
    fun durdur() {
        dur = true
        istemci?.durdur()
    }

    fun calis(
        k: ByteArray, kimlik: String, n: Int, zarf: ByteArray,
        tekSefer: Boolean = false, sureMs: Long = TEK_SEFER_MS, baglandi: () -> Unit = {},
        surdur: () -> Boolean = { true },
        durumGoruldu: (Map<String, Any?>) -> Unit = {},
    ): IzlemeBitis {
        val bilgi = try { Zarf.bilgiCoz(k, kimlik, n, zarf) } catch (e: ZarfHatasi) { return IzlemeBitis("zarf") }
        try {
            val adres = try { AraciAdresi.coz(bilgi.uri) } catch (e: AraciHatasi) { return IzlemeBitis("adres") }
            if (dur) return IzlemeBitis("durduruldu")
            val son = simdiMs() + sureMs
            val yol = try { baglan(adres) } catch (e: AraciHatasi) {
                // Curutucu 5E B5: araciya ULASILAMIYOR ve kaydin bittigi biliniyor -> izlemeye gerek kalmadi
                // (karar yalniz bagli oturumun tikinde verilirse internet yokken servis sonsuza dek denerdi).
                if (!surdur()) return IzlemeBitis("gerek-kalmadi")
                return IzlemeBitis(if (e.tur == "tls") "tls" else "ag")
            }
            val i = MqttIstemci(yol, simdiMs)
            istemci = i
            if (dur) i.durdur()
            val onek = "ok/" + bilgi.onek + "/"
            var bagli = false
            var bitisTuru: String? = null
            var gereksiz = -1L                         // `surdur`un ilk "hayir" dedigi an; -1 = gerekli

            fun bitir(tur: String) {
                if (bitisTuru == null) bitisTuru = tur
                i.durdur()
            }

            val b = try {
                i.calis(
                    istemciId(), bilgi.kullanici.ifEmpty { null }, bilgi.parola.ifEmpty { null }, "$onek#",
                    baglandi = {
                        bagli = true
                        synchronized(kilit) { karar.mqttBagliOldu(true) }
                        baglandi()
                    },
                    mesaj = { y ->
                        // Yalniz kartin yayinladigi iki konu islenir ve sayilir (curutucu 5E B2): bilinmeyen alt
                        // konuya birakilmis cop mesajlar "anahtar eskidi" saydiramaz.
                        val kalan = if (y.konu.startsWith(onek)) y.konu.substring(onek.length) else ""
                        if (kalan == "durum" || kalan == "olay") {
                            val icerik = try { Zarf.ac(bilgi.anahtar, y.konu, y.yuk) } catch (e: ZarfHatasi) { null }
                            if (icerik == null) {
                                atilan++
                                // Tek seferlik okumada (yoklama) araci yalniz BIR kalici mesaj yollar: cozulemeyen
                                // kalici DURUM tek basina "anahtar eskidi" demektir (B1; A31).
                                if (cozulen == 0 && (atilan >= ATILAN_SINIR || (tekSefer && kalan == "durum"))) bitir("anahtar")
                            } else {
                                cozulen++
                                synchronized(kilit) { karar.mqttMesaj(kalan, icerik) }
                                if (kalan == "durum") durumGoruldu(icerik)
                                if (tekSefer && kalan == "durum") bitir("durum-okundu")
                            }
                        }
                    },
                    tik = {
                        synchronized(kilit) { karar.tik() }
                        if (tekSefer && simdiMs() >= son) bitir("sure")
                        // A28: kayit bitti -> servis durur; ama HEMEN degil: "kayit bitti" olayinin ayrintisi
                        // durumdan sonra gelebilir (GEREKSIZ_MS boyunca dinlemeye devam).
                        if (surdur()) gereksiz = -1L
                        else if (gereksiz < 0) gereksiz = simdiMs()
                        else if (simdiMs() - gereksiz >= GEREKSIZ_MS) bitir("gerek-kalmadi")
                    },
                )
            } finally {
                istemci = null
                if (bagli) synchronized(kilit) { karar.mqttBagliOldu(false) }
            }
            return when {
                b.tur == "durduruldu" -> IzlemeBitis(bitisTuru ?: "durduruldu", baglandi = bagli)
                // Oturum koptu / reddedildi ve kayit bitmis: yeniden denemeye gerek yok (B5'in ikinci yarisi).
                !surdur() -> IzlemeBitis("gerek-kalmadi", baglandi = bagli)
                b.tur == "ret" && (b.kod == 4 || b.kod == 5) -> IzlemeBitis("kimlik-ret", b.kod, bagli)
                else -> IzlemeBitis(b.tur, b.kod, bagli)
            }
        } finally {
            bilgi.anahtar.fill(0)
        }
    }

    companion object {
        /** Tek seferlik okuma (A30) abone olduktan sonra en cok bu kadar bekler. */
        const val TEK_SEFER_MS = 20_000L
        /** Hic mesaj cozulemeden bu kadar mesaj atildiysa anahtar eskimistir. */
        const val ATILAN_SINIR = 3
        /** `surdur` bu kadar sure kesintisiz "hayir" derse oturum biter. */
        const val GEREKSIZ_MS = 10_000L

        /**
         * Oturum `b` ile bittikten sonra kac ms beklenip yeniden denenecegi; null = denenmez (ayar yenilenene
         * ya da cagiran durdurana dek). `deneme`: art arda kacinci basarisizlik (1'den). Baglanip sonra kopan
         * oturum 1'den sayar (cagiran sifirlar).
         */
        fun bekleme(b: IzlemeBitis, deneme: Int): Long? {
            val d = deneme.coerceAtLeast(1)
            return when (b.sinif) {
                "ayar", "tamam" -> null
                "internet" -> INTERNET_MS[minOf(d, INTERNET_MS.size) - 1]
                else -> SEYREK_MS[minOf(d, SEYREK_MS.size) - 1]
            }
        }

        private val INTERNET_MS = longArrayOf(2_000, 5_000, 10_000, 30_000, 60_000)
        private val SEYREK_MS = longArrayOf(60_000, 300_000, 900_000)

        /** Araciya gorunen istemci kimligi: rastgele; telefonu / karti / kullaniciyi TANITMAZ. */
        fun rastgeleKimlik(): String {
            val b = ByteArray(8)
            SecureRandom().nextBytes(b)
            return "okm-" + b.joinToString("") { "%02x".format(it) }
        }
    }
}
