package tr.olcumkarti.mobil.kasa

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyStore
import java.security.ProviderException
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Android Keystore'daki DISA VERILEMEZ AES-256-GCM anahtariyla sarma (A14). Kullanici dogrulamasi istenmez
 * (servis ekran kilitliyken de acabilmeli). IV'yi Keystore uretir (rastgele, 12 B). JVM testinde KOSMAZ.
 *
 * @param strongBoxDene cihaz StrongBox bildiriyorsa once orada uretilir; olmazsa TEE / yazilim.
 */
class KeystoreSarici(private val strongBoxDene: Boolean) : Sarici {

    private fun depo(): KeyStore = KeyStore.getInstance(SAGLAYICI).apply { load(null) }

    private fun mevcut(): SecretKey? = depo().getKey(TAKMA_AD, null) as? SecretKey

    private fun uret(strongBox: Boolean): SecretKey {
        val b = KeyGenParameterSpec.Builder(TAKMA_AD, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .setUserAuthenticationRequired(false)
        if (strongBox) b.setIsStrongBoxBacked(true)
        val u = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, SAGLAYICI)
        u.init(b.build())
        return u.generateKey()
    }

    private fun mevcutYaDaUret(): SecretKey {
        mevcut()?.let { return it }
        if (strongBoxDene) {
            try {
                return uret(true)
            } catch (e: ProviderException) {
                // StrongBoxUnavailableException (ProviderException alt sinifi) ve StrongBox'in diger uretim
                // hatalari: asagida StrongBox olmadan uretilir.
            }
        }
        return uret(false)
    }

    override fun sar(duz: ByteArray, aad: ByteArray): ByteArray {
        val c = Cipher.getInstance(DONUSUM)
        c.init(Cipher.ENCRYPT_MODE, mevcutYaDaUret())
        val iv = c.iv
        if (iv == null || iv.size != IV_BOYU) throw IllegalStateException()
        c.updateAAD(aad)
        return iv + c.doFinal(duz)
    }

    override fun ac(sarili: ByteArray, aad: ByteArray): ByteArray {
        if (sarili.size < IV_BOYU + ETIKET_BIT / 8) throw IllegalStateException()
        val anahtar = mevcut() ?: throw IllegalStateException()   // anahtar kayip: cagiran `bozuk` der
        val c = Cipher.getInstance(DONUSUM)
        c.init(Cipher.DECRYPT_MODE, anahtar, GCMParameterSpec(ETIKET_BIT, sarili, 0, IV_BOYU))
        c.updateAAD(aad)
        return c.doFinal(sarili, IV_BOYU, sarili.size - IV_BOYU)
    }

    /** Sarma anahtarini yok eder (son kayit silinince, A19). Yoksa sessiz. */
    fun yokEt() {
        val d = depo()
        if (d.containsAlias(TAKMA_AD)) d.deleteEntry(TAKMA_AD)
    }

    companion object {
        const val TAKMA_AD = "olcum-kasa-v1"
        private const val SAGLAYICI = "AndroidKeyStore"
        private const val DONUSUM = "AES/GCM/NoPadding"
        private const val IV_BOYU = 12
        private const val ETIKET_BIT = 128
    }
}
