package tr.olcumkarti.mobil.bildirim

import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.net.SocketTimeoutException

/** Sanal saat + betikli araci. `yanit(ilkBayt, govde)` istemcinin her paketine verilecek baytlari doner. */
internal class SahteAraci(val yanit: (SahteAraci, Int, ByteArray) -> ByteArray?) : MqttBaglanti {
    var ms = 1_000_000L
    val gelen = ArrayList<Pair<Int, ByteArray>>()           // istemciden gelen paketler
    val kuyruk = ArrayDeque<ByteArray>()                    // istemciye gidecek baytlar
    var kapandi = false
    var akisBitti = false
    var okumaHatasi = false
    var zamanAsiminda: ((SahteAraci) -> Unit)? = null       // her bos okumada (sanal sure ilerledikten sonra)
    private var sure = 500
    private var okuma = 0
    private val bas = ms
    private val ayr = MqttPaket.Ayristirici()

    override val giris = object : InputStream() {
        override fun read(): Int = throw UnsupportedOperationException()
        override fun read(b: ByteArray): Int {
            // Guvenlik siniri: bozuk bir istemci (mutasyon) sanal saatle SONSUZA dek donebilir; test asili
            // kalmak yerine DUSER (1 saat sanal sure ya da 200 bin okuma).
            if (++okuma > 200_000 || ms - bas > 3_600_000) throw IllegalStateException("istemci bitmedi: test siniri")
            if (okumaHatasi) throw IOException("gizli-ayrinti")
            val p = kuyruk.removeFirstOrNull()
            if (p != null) { System.arraycopy(p, 0, b, 0, p.size); return p.size }
            if (akisBitti) return -1
            ms += sure                                       // SANAL bekleme
            zamanAsiminda?.invoke(this@SahteAraci)
            throw SocketTimeoutException()
        }
    }
    override val cikis = object : OutputStream() {
        private val t = ByteArrayOutputStream()
        override fun write(b: Int) { t.write(b) }
        override fun flush() {
            ayr.besle(t.toByteArray()); t.reset()
            while (true) {
                val p = ayr.sonraki() ?: break
                gelen.add(p)
                yanit(this@SahteAraci, p.first, p.second)?.let { kuyruk.addLast(it) }
            }
        }
    }
    override fun okumaSuresi(ms: Int) { sure = ms }
    override fun kapat() { kapandi = true }
    fun turler(): List<Int> = gelen.map { it.first shr 4 }
}
