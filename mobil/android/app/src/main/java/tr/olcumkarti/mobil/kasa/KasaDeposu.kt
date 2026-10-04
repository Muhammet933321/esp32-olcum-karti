package tr.olcumkarti.mobil.kasa

import java.io.File

/**
 * Kasa dizini (`files/kasa/`): `<kimlik>.anahtar` (sarili kayit) + `<kimlik>.sayac`.
 * Kimlik dosya adina gider: HER islemden once 16 kucuk onaltilik hane oldugu denetlenir (dizin disina
 * cikilamaz). Saf JVM: `Sarici` ve kok dizin enjekte edilir. Es zamanlilik cagiranin isi (eklenti tek is
 * parcacigi).
 *
 * @param anahtarYokEt son kayit da silinince sarma anahtarini (Keystore) yok eder (A19)
 */
class KasaDeposu(private val kok: File, private val sarici: Sarici, private val anahtarYokEt: () -> Unit = {}) {

    /** Liste satiri: anahtar YOK. `bozuk` ise n/ad okunamadi (dosya bozuk ya da sarma anahtari kayip). */
    class Ozet(val kimlik: String, val n: Int, val ad: String, val bozuk: Boolean)

    private fun dosya(kimlik: String?, ek: String): File {
        if (!KasaKayit.kimlikGecerli(kimlik)) throw KasaHatasi("bicim")
        return File(kok, kimlik + ek)
    }

    fun anahtarYaz(kimlik: String?, n: Int, ad: String, anahtar: ByteArray) {
        val hedef = dosya(kimlik, ANAHTAR_EK)
        val paket = KasaKayit.paketle(kimlik!!, n, ad, anahtar, sarici)
        try {
            AtomikYazim.yaz(hedef, paket)
        } catch (e: KasaHatasi) {
            throw e
        } catch (e: Exception) {
            throw KasaHatasi("ic-hata")
        }
    }

    fun anahtarOku(kimlik: String?): Kayit {
        val d = dosya(kimlik, ANAHTAR_EK)
        if (!d.exists()) throw KasaHatasi("yok")
        if (d.length() > KasaKayit.AZAMI_DOSYA) throw KasaHatasi("bozuk")
        val veri = try { d.readBytes() } catch (e: Exception) { throw KasaHatasi("bozuk") }
        return KasaKayit.coz(kimlik!!, veri, sarici)
    }

    fun liste(): List<Ozet> {
        val adlar = kok.list() ?: return emptyList()
        val cikti = ArrayList<Ozet>()
        for (ad in adlar.sorted()) {
            if (!ad.endsWith(ANAHTAR_EK)) continue
            val kimlik = ad.removeSuffix(ANAHTAR_EK)
            if (!KasaKayit.kimlikGecerli(kimlik)) continue
            try {
                val k = anahtarOku(kimlik)
                k.anahtar.fill(0)
                cikti.add(Ozet(kimlik, k.n, k.ad, false))
            } catch (e: KasaHatasi) {
                cikti.add(Ozet(kimlik, 0, "", true))
            }
        }
        return cikti
    }

    /** Kaydi, sayaci ve o kimlige ait gecici dosyalari siler; hic kayit kalmadiysa sarma anahtarini da. */
    fun sil(kimlik: String?) {
        if (!KasaKayit.kimlikGecerli(kimlik)) throw KasaHatasi("bicim")
        val adlar = kok.list() ?: emptyArray()
        for (ad in adlar) {
            if (ad.startsWith("$kimlik.") && !File(kok, ad).delete()) throw KasaHatasi("ic-hata")
        }
        val kalan = (kok.list() ?: emptyArray()).any { it.endsWith(ANAHTAR_EK) }
        if (!kalan) {
            try { anahtarYokEt() } catch (e: Exception) { throw KasaHatasi("ic-hata") }
        }
    }

    fun sayacOku(kimlik: String?): Long = SayacDosyasi(dosya(kimlik, SAYAC_EK)).oku()

    fun sayacYaz(kimlik: String?, isaret: Long): Long = SayacDosyasi(dosya(kimlik, SAYAC_EK)).yaz(isaret)

    companion object {
        const val ANAHTAR_EK = ".anahtar"
        const val SAYAC_EK = ".sayac"
    }
}
