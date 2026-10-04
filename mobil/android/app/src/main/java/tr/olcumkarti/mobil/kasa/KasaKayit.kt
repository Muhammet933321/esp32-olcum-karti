package tr.olcumkarti.mobil.kasa

import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction

/** Kimlik dogrulamali sifreleme. Uretimde Android Keystore (KeystoreSarici); testte bellekte AES-GCM. */
interface Sarici {
    /** @return IV + sifreli metin + etiket */
    fun sar(duz: ByteArray, aad: ByteArray): ByteArray

    /** Etiket tutmuyorsa ya da anahtar yoksa ATAR. */
    fun ac(sarili: ByteArray, aad: ByteArray): ByteArray
}

/** Cozulmus kayit. `anahtar` K'dir: toString'e, hata metnine, dosya adina GIRMEZ. */
class Kayit(val kimlik: String, val n: Int, val ad: String, val anahtar: ByteArray) {
    override fun toString(): String = "Kayit"
}

/**
 * Sarili kayit bicimi (surumlu, kendini dogrulayan):
 *   sihir "OKKS" (4) + surum (1) + Sarici ciktisi (IV + AES-GCM(n, adUzunluk, ad, anahtar) + etiket)
 * AAD = sihir + surum + kimlik: baska kimligin dosyasi bu kimligin adina kopyalanirsa ACILMAZ.
 * Saf Kotlin (Android sinifi yok): JVM'de sinanir.
 */
object KasaKayit {
    const val ANAHTAR_BOYU = 32
    const val AD_AZAMI_BAYT = 24
    const val SURUM: Byte = 1
    const val AZAMI_DOSYA = 512
    private val SIHIR = byteArrayOf(0x4f, 0x4b, 0x4b, 0x53)   // "OKKS"
    private const val BAS = 5

    fun kimlikGecerli(kimlik: String?): Boolean =
        kimlik != null && kimlik.length == 16 && kimlik.all { it in '0'..'9' || it in 'a'..'f' }

    private fun aad(kimlik: String): ByteArray = SIHIR + byteArrayOf(SURUM) + kimlik.toByteArray(Charsets.US_ASCII)

    fun paketle(kimlik: String, n: Int, ad: String, anahtar: ByteArray, sarici: Sarici): ByteArray {
        if (!kimlikGecerli(kimlik)) throw KasaHatasi("bicim")
        if (n < 1 || n > 255) throw KasaHatasi("bicim")
        if (anahtar.size != ANAHTAR_BOYU) throw KasaHatasi("bicim")
        val adBayt = ad.toByteArray(Charsets.UTF_8)
        if (adBayt.size > AD_AZAMI_BAYT) throw KasaHatasi("bicim")
        val duz = ByteArray(2 + adBayt.size + ANAHTAR_BOYU)
        try {
            duz[0] = n.toByte()
            duz[1] = adBayt.size.toByte()
            adBayt.copyInto(duz, 2)
            anahtar.copyInto(duz, 2 + adBayt.size)
            val sarili = try { sarici.sar(duz, aad(kimlik)) } catch (e: Exception) { throw KasaHatasi("ic-hata") }
            val cikti = ByteArrayOutputStream(BAS + sarili.size)
            cikti.write(SIHIR)
            cikti.write(SURUM.toInt())
            cikti.write(sarili)
            return cikti.toByteArray()
        } finally {
            duz.fill(0)
        }
    }

    /** Her tutarsizlik (sihir, surum, kirpik, etiket, ic uzunluk, anahtar kaybi) `bozuk`. */
    fun coz(kimlik: String, dosya: ByteArray, sarici: Sarici): Kayit {
        if (!kimlikGecerli(kimlik)) throw KasaHatasi("bicim")
        if (dosya.size <= BAS || dosya.size > AZAMI_DOSYA) throw KasaHatasi("bozuk")
        for (i in SIHIR.indices) if (dosya[i] != SIHIR[i]) throw KasaHatasi("bozuk")
        if (dosya[4] != SURUM) throw KasaHatasi("bozuk")
        val duz = try {
            sarici.ac(dosya.copyOfRange(BAS, dosya.size), aad(kimlik))
        } catch (e: Exception) {
            throw KasaHatasi("bozuk")
        }
        try {
            if (duz.size < 2 + ANAHTAR_BOYU) throw KasaHatasi("bozuk")
            val n = duz[0].toInt() and 0xff
            val adBoy = duz[1].toInt() and 0xff
            if (n < 1 || adBoy > AD_AZAMI_BAYT || duz.size != 2 + adBoy + ANAHTAR_BOYU) throw KasaHatasi("bozuk")
            val ad = try {
                Charsets.UTF_8.newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(duz, 2, adBoy)).toString()
            } catch (e: Exception) {
                throw KasaHatasi("bozuk")
            }
            return Kayit(kimlik, n, ad, duz.copyOfRange(2 + adBoy, duz.size))
        } finally {
            duz.fill(0)
        }
    }
}
