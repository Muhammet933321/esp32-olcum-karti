package tr.olcumkarti.mobil.paylas

import java.io.File
import java.io.FileOutputStream

/** Paylasim hatasi: `tur` sabit ad (bicim, sira, cok-buyuk, boy, ic-hata); yol / icerik TASIMAZ. */
class PaylasHatasi(val tur: String) : Exception(tur)

/**
 * Paylasilacak dosyanin gecici deposu (tasarim A41; 5F): uygulamanin ONBELLEGINDE tek dizin (`cache/paylas/`).
 * WebView dosyayi parca parca verir: `baslat` (dizini BOSALTIR — onceki paylasimin dosyasi kalmaz) -> `yaz`…
 * -> `bitir` (boy denetimi). Dosya adi disaridan gelir ve dosya sistemine gider: yalniz harf / rakam / . _ -
 * ve bilinen uzanti (csv, kyt, txt); ".." ve dizin ayraci yok. Toplam boy sinirli. Saf JVM.
 */
class PaylasDeposu(private val kok: File) {
    private var acik: String? = null
    private var yazilan = 0L

    private fun dosya(ad: String?): File {
        if (ad == null || !AD.matches(ad) || ad.contains("..")) throw PaylasHatasi("bicim")
        return File(kok, ad)
    }

    /** Onceki paylasimdan kalan her seyi siler, yeni dosyayi BOS acar. */
    fun baslat(ad: String?) {
        val hedef = dosya(ad)
        temizle()
        if (!kok.isDirectory && !kok.mkdirs()) throw PaylasHatasi("ic-hata")
        try { FileOutputStream(hedef, false).use { } } catch (e: Exception) { throw PaylasHatasi("ic-hata") }
        acik = ad
        yazilan = 0
    }

    fun yaz(ad: String?, parca: ByteArray) {
        val hedef = dosya(ad)
        if (acik == null || acik != ad) throw PaylasHatasi("sira")
        if (parca.size > PARCA_AZAMI) throw PaylasHatasi("bicim")
        if (yazilan + parca.size > AZAMI) { temizle(); throw PaylasHatasi("cok-buyuk") }
        try { FileOutputStream(hedef, true).use { it.write(parca) } } catch (e: Exception) { throw PaylasHatasi("ic-hata") }
        yazilan += parca.size
    }

    /** Yazim bitti: beklenen boy tutuyorsa dosyayi doner (paylasima hazir); tutmuyorsa siler. */
    fun bitir(ad: String?, boy: Long): File {
        val hedef = dosya(ad)
        if (acik == null || acik != ad) throw PaylasHatasi("sira")
        acik = null
        if (boy <= 0 || boy != yazilan || hedef.length() != boy) { temizle(); throw PaylasHatasi("boy") }
        return hedef
    }

    fun temizle() {
        acik = null
        yazilan = 0
        kok.listFiles()?.forEach { it.delete() }
    }

    companion object {
        val AD = Regex("^[A-Za-z0-9][A-Za-z0-9._-]{0,79}\\.(csv|kyt|txt)$")
        /** WebView 512 KiB'lik parcalar yollar; pay birakilir. */
        const val PARCA_AZAMI = 1 shl 20
        const val AZAMI = 64L * 1024 * 1024
        val MIMELER = setOf("text/csv", "text/plain", "application/octet-stream")
    }
}
