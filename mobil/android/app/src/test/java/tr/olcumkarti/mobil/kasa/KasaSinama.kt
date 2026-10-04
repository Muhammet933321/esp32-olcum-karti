package tr.olcumkarti.mobil.kasa

import java.io.File
import java.nio.file.Files
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

/** Test saricisi: JDK'nin AES-256-GCM'i, bellekteki anahtar. Uretimdeki KeystoreSarici ile ayni cikti duzeni. */
class BellekSarici(anahtar: ByteArray = ByteArray(32) { (0xA0 + it).toByte() }) : Sarici {
    private var anahtar: SecretKeySpec? = SecretKeySpec(anahtar, "AES")
    var yokEtSayisi = 0

    override fun sar(duz: ByteArray, aad: ByteArray): ByteArray {
        val iv = ByteArray(12).also { SecureRandom().nextBytes(it) }
        val c = Cipher.getInstance("AES/GCM/NoPadding")
        c.init(Cipher.ENCRYPT_MODE, anahtar ?: throw IllegalStateException(), GCMParameterSpec(128, iv))
        c.updateAAD(aad)
        return iv + c.doFinal(duz)
    }

    override fun ac(sarili: ByteArray, aad: ByteArray): ByteArray {
        val c = Cipher.getInstance("AES/GCM/NoPadding")
        c.init(Cipher.DECRYPT_MODE, anahtar ?: throw IllegalStateException(), GCMParameterSpec(128, sarili, 0, 12))
        c.updateAAD(aad)
        return c.doFinal(sarili, 12, sarili.size - 12)
    }

    fun yokEt() {
        anahtar = null
        yokEtSayisi++
    }
}

object Sinama {
    const val K1 = "0123456789abcdef"
    const val K2 = "fedcba9876543210"

    /** Belirgin sinama anahtari: 0x11, 0x12, ... (gercek anahtar DEGIL). */
    fun anahtar(taban: Int = 0x11): ByteArray = ByteArray(32) { (taban + it).toByte() }

    fun geciciDizin(): File = Files.createTempDirectory("kasa-test").toFile()

    fun tur(blok: () -> Unit): String = try {
        blok()
        "tamam"
    } catch (e: KasaHatasi) {
        // Hata nesnesi yalniz tur tasir: mesaj = tur, neden (cause) yok.
        check(e.message == e.tur) { "mesaj turden farkli" }
        check(e.cause == null) { "hata bir neden tasiyor" }
        e.tur
    }

    fun icerir(saman: ByteArray, igne: ByteArray): Boolean {
        if (igne.isEmpty() || saman.size < igne.size) return false
        for (i in 0..saman.size - igne.size) {
            var ayni = true
            for (j in igne.indices) if (saman[i + j] != igne[j]) { ayni = false; break }
            if (ayni) return true
        }
        return false
    }
}
