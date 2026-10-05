package tr.olcumkarti.mobil.bildirim

import java.nio.charset.CharacterCodingException
import java.nio.charset.CodingErrorAction
import javax.crypto.Cipher
import javax.crypto.spec.IvParameterSpec
import javax.crypto.spec.SecretKeySpec

/**
 * Zarf hatasi. `tur` loga / bildirime gidebilen TEK bilgidir; anahtar, konu, icerik hata metnine GIRMEZ
 * (tasarim A45, kullanici sarti S3).
 *   bicim: sihir yok / kisa / anahtar boyu yanlis      etiket: dogrulama tutmadi (yanlis anahtar, bozuk
 *   veri, YANLIS KONU)      icerik: duz metin gecerli UTF-8 JSON nesnesi degil ya da alanlar eksik
 */
class ZarfHatasi(val tur: String) : Exception(tur)

/** `/bildirim/bilgi`'nin cozulmus hali: yalniz BELLEKTE yasar (A31); toString sir YAZMAZ. */
class AraciBilgisi(val uri: String, val kullanici: String, val parola: String, val onek: String, val anahtar: ByteArray) {
    override fun toString(): String = "AraciBilgisi(***)"
}

/**
 * Bildirim zarfi "OKB1" (1E K5, K10): `ortak/src/zarf.js` zarfAc / bilgiCoz'un Kotlin karsiligi.
 *   bayt 0..3 "OKB1" · 4..15 nonce · 16.. sifreli metin + 16 B etiket (ChaCha20-Poly1305 IETF, RFC 8439)
 *   AAD: MQTT yukunde KONU ADI; /bildirim/bilgi yanitinda "OK1-bildirim\n<kimlik>\n<n>"
 * Kripto PLATFORMUN (javax.crypto "ChaCha20-Poly1305": Android API 28+, JDK 11+) — kendi kripto yok.
 * `ortak/test/vektor/kripto.json` "zarf" vektorleriyle bayt bayt sinanir (ZarfTest).
 */
object Zarf {
    val SIHIR = byteArrayOf(0x4f, 0x4b, 0x42, 0x31)
    const val NONCE = 12
    const val ETIKET = 16
    const val ANAHTAR = 32
    const val EN_AZ = 4 + NONCE + ETIKET
    private val ONEK = Regex("^[0-9a-f]{32}$")
    private val ANAHTAR_HEX = Regex("^[0-9a-fA-F]{64}$")

    /** Zarfi ac -> duz metin baytlari. AAD verilen baytlardir. */
    fun coz(anahtar: ByteArray, aad: ByteArray, veri: ByteArray): ByteArray {
        if (anahtar.size != ANAHTAR || veri.size < EN_AZ) throw ZarfHatasi("bicim")
        for (i in SIHIR.indices) if (veri[i] != SIHIR[i]) throw ZarfHatasi("bicim")
        return try {
            val c = Cipher.getInstance("ChaCha20-Poly1305")
            c.init(Cipher.DECRYPT_MODE, SecretKeySpec(anahtar, "ChaCha20"), IvParameterSpec(veri, 4, NONCE))
            c.updateAAD(aad)
            c.doFinal(veri, 4 + NONCE, veri.size - 4 - NONCE)
        } catch (e: java.security.GeneralSecurityException) {
            throw ZarfHatasi("etiket")
        }
    }

    /** MQTT yuku: AAD = konu adi; icerik JSON NESNESI olmali. */
    fun ac(anahtar: ByteArray, konu: String, veri: ByteArray): Map<String, Any?> =
        nesne(coz(anahtar, konu.toByteArray(Charsets.UTF_8), veri))

    fun bilgiAad(kimlik: String, n: Int): ByteArray = "OK1-bildirim\n$kimlik\n$n".toByteArray(Charsets.UTF_8)

    /** Kartin /bildirim/bilgi yaniti (anahtar = cihaz anahtari K). */
    fun bilgiCoz(k: ByteArray, kimlik: String, n: Int, govde: ByteArray): AraciBilgisi {
        val d = nesne(coz(k, bilgiAad(kimlik, n), govde))
        fun metin(ad: String): String = d[ad] as? String ?: throw ZarfHatasi("icerik")
        val uri = metin("u"); val kullanici = metin("k"); val parola = metin("p"); val onek = metin("o"); val a = metin("a")
        if (uri.isEmpty() || !ONEK.matches(onek) || !ANAHTAR_HEX.matches(a)) throw ZarfHatasi("icerik")
        return AraciBilgisi(uri, kullanici, parola, onek, ByteArray(ANAHTAR) { a.substring(2 * it, 2 * it + 2).toInt(16).toByte() })
    }

    private fun nesne(duz: ByteArray): Map<String, Any?> {
        val metin = try {
            // KATI UTF-8: gecersiz dizi U+FFFD'ye cevrilmez (JS TextDecoder fatal ile ayni).
            Charsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT)
                .decode(java.nio.ByteBuffer.wrap(duz)).toString()
        } catch (e: CharacterCodingException) {
            throw ZarfHatasi("icerik")
        }
        return try { DuzJson.nesne(metin) } catch (e: JsonHatasi) { throw ZarfHatasi("icerik") }
    }
}
