package tr.olcumkarti.mobil.bildirim

import java.io.ByteArrayOutputStream

/** MQTT bicim hatasi. Mesaj sabit: gelen baytlar (konu, yuk) hata metnine GIRMEZ (S3). */
class MqttHatasi(val tur: String) : Exception(tur)

/** Cozulmus PUBLISH. */
class Yayin(val konu: String, val yuk: ByteArray, val kalici: Boolean, val qos: Int, val paketNo: Int?)

/**
 * Asgari MQTT 3.1.1 ABONESI icin paketler (tasarim §2.3 C; emsal `kopru/mqtt_istemci.py` — ayni
 * baytlar: `mobil/test/vektor/mqtt.json` Python'dan uretildi, MqttPaketTest karsilastirir).
 * Yalniz gereken: CONNECT, SUBSCRIBE, PUBACK, PINGREQ, DISCONNECT uretimi; CONNACK / SUBACK / PUBLISH /
 * PINGRESP ayristirma. Uygulama HICBIR konuya yayin yapmaz (A32): PUBLISH ureten kod YOK.
 * Saf Kotlin: JVM'de sinanir.
 */
object MqttPaket {
    const val CONNECT = 1
    const val CONNACK = 2
    const val PUBLISH = 3
    const val PUBACK = 4
    const val SUBSCRIBE = 8
    const val SUBACK = 9
    const val PINGREQ = 12
    const val PINGRESP = 13
    const val DISCONNECT = 14
    const val UZUNLUK_AZAMI = 268_435_455

    fun uzunlukKodla(n: Int): ByteArray {
        if (n < 0 || n > UZUNLUK_AZAMI) throw MqttHatasi("bicim")
        val c = ByteArrayOutputStream(4)
        var k = n
        while (true) {
            val b = k % 128
            k /= 128
            c.write(if (k > 0) b or 0x80 else b)
            if (k == 0) return c.toByteArray()
        }
    }

    /** -> (deger, tuketilen bayt) | null (henuz tam degil); 4 baytta bitmiyorsa MqttHatasi. */
    fun uzunlukCoz(veri: ByteArray, bas: Int, son: Int): Pair<Int, Int>? {
        var deger = 0
        var carpan = 1
        var i = 0
        while (i < 4 && bas + i < son) {
            val b = veri[bas + i].toInt() and 0xff
            deger += (b and 0x7f) * carpan
            if (b and 0x80 == 0) return Pair(deger, i + 1)
            carpan *= 128
            i++
        }
        if (i >= 4) throw MqttHatasi("bicim")
        return null
    }

    fun dize(metin: String): ByteArray {
        val b = metin.toByteArray(Charsets.UTF_8)
        if (b.size > 0xffff) throw MqttHatasi("bicim")
        return byteArrayOf((b.size shr 8).toByte(), b.size.toByte()) + b
    }

    fun paket(ilkBayt: Int, govde: ByteArray = ByteArray(0)): ByteArray =
        byteArrayOf(ilkBayt.toByte()) + uzunlukKodla(govde.size) + govde

    private fun u16(n: Int): ByteArray = byteArrayOf((n shr 8).toByte(), n.toByte())

    /** Temiz oturum; kullanici / parola verilmisse bayraklariyla. Vasiyet YOK (yalniz abone). */
    fun connect(istemciId: String, kullanici: String?, parola: String?, keepaliveS: Int): ByteArray {
        if (keepaliveS < 0 || keepaliveS > 0xffff) throw MqttHatasi("bicim")
        var bayrak = 0x02
        var yuk = dize(istemciId)
        if (kullanici != null) { bayrak = bayrak or 0x80; yuk += dize(kullanici) }
        if (parola != null) { bayrak = bayrak or 0x40; yuk += dize(parola) }
        return paket(CONNECT shl 4, dize("MQTT") + byteArrayOf(4, bayrak.toByte()) + u16(keepaliveS) + yuk)
    }

    fun subscribe(paketNo: Int, konuFiltresi: String, qos: Int): ByteArray {
        if (qos != 0 && qos != 1) throw MqttHatasi("bicim")
        if (paketNo < 1 || paketNo > 0xffff) throw MqttHatasi("bicim")
        return paket((SUBSCRIBE shl 4) or 0x02, u16(paketNo) + dize(konuFiltresi) + byteArrayOf(qos.toByte()))
    }

    fun puback(paketNo: Int): ByteArray = paket(PUBACK shl 4, u16(paketNo))
    fun pingreq(): ByteArray = paket(PINGREQ shl 4)
    fun disconnect(): ByteArray = paket(DISCONNECT shl 4)

    /** CONNACK govdesi -> donus kodu (0 = kabul). */
    fun connackKodu(govde: ByteArray): Int {
        if (govde.size != 2) throw MqttHatasi("bicim")
        return govde[1].toInt() and 0xff
    }

    /** SUBACK govdesi -> (paket no, verilen QoS | 0x80 = ret). */
    fun suback(govde: ByteArray): Pair<Int, Int> {
        if (govde.size < 3) throw MqttHatasi("bicim")
        return Pair(((govde[0].toInt() and 0xff) shl 8) or (govde[1].toInt() and 0xff), govde[2].toInt() and 0xff)
    }

    fun publishCoz(ilk: Int, govde: ByteArray): Yayin {
        val qos = (ilk shr 1) and 3
        val kalici = ilk and 1 == 1
        if (qos == 3 || govde.size < 2) throw MqttHatasi("bicim")
        val n = ((govde[0].toInt() and 0xff) shl 8) or (govde[1].toInt() and 0xff)
        if (govde.size < 2 + n) throw MqttHatasi("bicim")
        val konu = try {
            Charsets.UTF_8.newDecoder().decode(java.nio.ByteBuffer.wrap(govde, 2, n)).toString()
        } catch (e: java.nio.charset.CharacterCodingException) {
            throw MqttHatasi("bicim")
        }
        var i = 2 + n
        var no: Int? = null
        if (qos > 0) {
            if (govde.size < i + 2) throw MqttHatasi("bicim")
            no = ((govde[i].toInt() and 0xff) shl 8) or (govde[i + 1].toInt() and 0xff)
            i += 2
        }
        return Yayin(konu, govde.copyOfRange(i, govde.size), kalici, qos, no)
    }

    /**
     * Akistan paket ayirir: `besle` ile ver, `sonraki()` tam paketi (ilk bayt, govde) dondurur; tam
     * gelmediyse null. Tek paket `azami` bayti asarsa MqttHatasi("buyuk"): araci (ya da araya giren)
     * bellegi dolduramaz. Bizim yuklerimiz kucuk (zarf + kisa JSON).
     */
    class Ayristirici(private val azami: Int = PAKET_AZAMI) {
        private var tampon = ByteArray(256)
        private var boy = 0

        fun bekleyen(): Int = boy

        fun besle(veri: ByteArray, n: Int = veri.size) {
            if (boy + n > tampon.size) {
                if (boy + n > azami + 5) throw MqttHatasi("buyuk")
                tampon = tampon.copyOf(maxOf(tampon.size * 2, boy + n))
            }
            System.arraycopy(veri, 0, tampon, boy, n)
            boy += n
        }

        fun sonraki(): Pair<Int, ByteArray>? {
            if (boy < 2) return null
            val u = uzunlukCoz(tampon, 1, boy) ?: return null
            if (u.first > azami) throw MqttHatasi("buyuk")
            val son = 1 + u.second + u.first
            if (boy < son) return null
            val ilk = tampon[0].toInt() and 0xff
            val govde = tampon.copyOfRange(1 + u.second, son)
            System.arraycopy(tampon, son, tampon, 0, boy - son)
            boy -= son
            return Pair(ilk, govde)
        }
    }

    const val PAKET_AZAMI = 16384
}
