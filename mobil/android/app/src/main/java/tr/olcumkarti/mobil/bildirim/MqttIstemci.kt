package tr.olcumkarti.mobil.bildirim

import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.net.SocketTimeoutException

/** Araciya acik bir bayt yolu (gercekte TLS soketi; testte bellek ici boru). */
interface MqttBaglanti {
    val giris: InputStream
    val cikis: OutputStream
    /** Okuma en cok bu kadar bekler; dolunca SocketTimeoutException (baglanti ACIK kalir). */
    fun okumaSuresi(ms: Int)
    fun kapat()
}

/**
 * Oturumun nasil bittigi. `tur` SABIT bir addir; araci adresi, kullanici, konu, yuk HICBIR alana girmez
 * (tasarim A45, sart S3).
 *   durduruldu : cagiran istedi                     koptu  : baglanti kapandi / G-C hatasi
 *   sessiz     : PINGREQ'e 7.5 s yanit yok (A34: telefonun interneti)      ret : CONNACK kodu != 0 (`kod`)
 *   abone-ret  : araci aboneligi reddetti           bicim  : araci protokole uymadi (QoS 2, bozuk paket …)
 *   zaman-asimi: CONNACK / SUBACK suresinde gelmedi
 */
class MqttBitis(val tur: String, val kod: Int = 0)

/**
 * Asgari MQTT 3.1.1 ABONESI (tasarim §2.3 C, A28–A34). Tek is parcaciginda, bloklu: `calis` oturum
 * bitene dek donmez. Yalniz abone olur ve PUBACK / PINGREQ yollar; PUBLISH GONDERMEZ (A32).
 *  - temiz oturum; keepalive KEEPALIVE_S (araci 1.5 katinda vasiyeti ilan eder)
 *  - KEEPALIVE_S suresince bir sey gondermediysek PINGREQ; gonderdikten sonra SESSIZLIK_MS icinde araci
 *    HICBIR paket yollamadiysa "sessiz" (telefonun interneti gitmis olabilir — kart icin alarm DEGIL)
 *  - QoS 1 PUBLISH: once PUBACK, sonra `mesaj` (araci yeniden gonderirse cagiran (a, n) ile ayiklar)
 * Saf Kotlin (soket yok): JVM'de bellek ici boruyla sinanir.
 */
class MqttIstemci(
    private val baglanti: MqttBaglanti,
    private val simdiMs: () -> Long = { System.nanoTime() / 1_000_000 },
) {
    @Volatile private var dur = false

    /** Baska is parcacigindan: oturumu bitirir (okuma en gec TIK_MS sonra fark eder). */
    fun durdur() {
        dur = true
    }

    fun calis(istemciId: String, kullanici: String?, parola: String?, filtre: String, baglandi: () -> Unit, mesaj: (Yayin) -> Unit, tik: () -> Unit = {}): MqttBitis {
        val ayristirici = MqttPaket.Ayristirici()
        val tampon = ByteArray(4096)
        var sonGiden = simdiMs()
        var pingZamani = -1L                       // yanit beklenen PINGREQ'in ani; -1 = bekleyen yok

        fun gonder(b: ByteArray) {
            baglanti.cikis.write(b)
            baglanti.cikis.flush()
            sonGiden = simdiMs()
        }

        /** Bir paket okur; `son` anina dek gelmediyse null. Akis bittiyse IOException. */
        fun paketAl(son: Long): Pair<Int, ByteArray>? {
            while (true) {
                ayristirici.sonraki()?.let { return it }
                val kalan = son - simdiMs()
                if (kalan <= 0) return null
                baglanti.okumaSuresi(minOf(kalan, TIK_MS.toLong()).toInt().coerceAtLeast(1))
                val n = try { baglanti.giris.read(tampon) } catch (e: SocketTimeoutException) { 0 }
                if (n < 0) throw IOException("bitti")
                if (n > 0) { ayristirici.besle(tampon, n); pingZamani = -1L }      // araci canli
                if (dur) return null
            }
        }

        try {
            gonder(MqttPaket.connect(istemciId, kullanici, parola, KEEPALIVE_S))
            val c = paketAl(simdiMs() + EL_SIKISMA_MS) ?: return MqttBitis(if (dur) "durduruldu" else "zaman-asimi")
            if (c.first shr 4 != MqttPaket.CONNACK) return MqttBitis("bicim")
            val kod = MqttPaket.connackKodu(c.second)
            if (kod != 0) return MqttBitis("ret", kod)

            gonder(MqttPaket.subscribe(1, filtre, 1))
            val bekleyenYayin = ArrayList<Pair<Int, ByteArray>>()
            val son = simdiMs() + EL_SIKISMA_MS
            while (true) {
                val p = paketAl(son) ?: return MqttBitis(if (dur) "durduruldu" else "zaman-asimi")
                if (p.first shr 4 == MqttPaket.SUBACK) {
                    val s = MqttPaket.suback(p.second)
                    if (s.first != 1) return MqttBitis("bicim")
                    if (s.second == 0x80) return MqttBitis("abone-ret")
                    break
                }
                if (p.first shr 4 == MqttPaket.PUBLISH) bekleyenYayin.add(p)      // SUBACK'ten once gelen kalici mesaj
            }
            baglandi()

            fun yayinIsle(p: Pair<Int, ByteArray>): MqttBitis? {
                val y = MqttPaket.publishCoz(p.first, p.second)
                if (y.qos == 2) return MqttBitis("bicim")
                if (y.qos == 1) gonder(MqttPaket.puback(y.paketNo!!))
                // Isleyicinin hatasi oturumu DUSURMEZ (tek bozuk mesaj izlemeyi bitirmesin) ve disari cikmaz.
                try { mesaj(y) } catch (_: RuntimeException) {}
                return null
            }
            for (p in bekleyenYayin) yayinIsle(p)?.let { return it }

            while (!dur) {
                tik()                                  // en gec TIK_MS'de bir (cagiranin saat isleri)
                if (dur) break
                val simdi = simdiMs()
                if (pingZamani >= 0 && simdi - pingZamani >= SESSIZLIK_MS) return MqttBitis("sessiz")
                if (pingZamani < 0 && simdi - sonGiden >= KEEPALIVE_S * 1000L) {
                    gonder(MqttPaket.pingreq())
                    pingZamani = simdiMs()
                }
                val p = paketAl(simdiMs() + TIK_MS) ?: continue
                if (p.first shr 4 == MqttPaket.PUBLISH) yayinIsle(p)?.let { return it }
                // PINGRESP, beklenmeyen SUBACK / PUBACK: yutulur (canlilik paketAl'da isaretlendi)
            }
            try { gonder(MqttPaket.disconnect()) } catch (_: IOException) {}
            return MqttBitis("durduruldu")
        } catch (e: MqttHatasi) {
            return MqttBitis("bicim")
        } catch (e: IOException) {
            return MqttBitis(if (dur) "durduruldu" else "koptu")
        } finally {
            try { baglanti.kapat() } catch (_: Exception) {}
        }
    }

    companion object {
        /** Kartla ayni (1E K8): 5 s; araci 7.5 s'de vasiyeti ilan eder. */
        const val KEEPALIVE_S = 5
        /** PINGREQ'ten sonra bu kadar sessizlik = "telefonun interneti" (A34). */
        const val SESSIZLIK_MS = 7500L
        const val EL_SIKISMA_MS = 10_000L
        const val TIK_MS = 500
    }
}
