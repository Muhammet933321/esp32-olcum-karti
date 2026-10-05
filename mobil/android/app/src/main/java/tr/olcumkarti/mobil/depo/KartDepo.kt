package tr.olcumkarti.mobil.depo

import java.io.File
import java.io.FileOutputStream
import java.io.RandomAccessFile
import java.nio.channels.FileChannel
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.nio.file.StandardOpenOption
import java.util.Calendar

/** Depo hatasi: `tur` kopruye giden TEK bilgidir (yol, istisna mesaji gitmez). */
class DepoHatasi(val tur: String) : Exception(tur)

/**
 * Kartin kayitlarinin telefondaki kopyasi (tasarim §2.2, A20, A23). `ortak/src/esitle.js` DEPO
 * arayuzunun dosya tarafi; PC ile AYNI uc dosya: `<kok>/<kimlik>/kayitlar.kyt`, `durum.json`,
 * `kalibrasyon.json` (+ zaman damgali `kalibrasyon-YYYYAAGG-SSDDSS.json` arsivleri).
 *
 * Sozlesme (esitle.js):
 *  - veriEkle DAYANIKLI: donunce baytlar diskte (fsync). Yarida kesilirse dosyada yarim kuyruk
 *    kalabilir; onu ACILISTA esitleyici ileri sarar / kirpar (bu sinif icerige bakmaz).
 *  - veriKirp dayanikli; n > boy ise sifirla uzatir (Python truncate).
 *  - durumYaz / kalYaz ATOMIK: okuyan ya eski ya yeni icerigin TAMAMINI gorur.
 *  - Kimlik yalniz 16 kucuk onaltilik hane: dosya yolu baska hicbir girdiden kurulmaz.
 * Saf Kotlin (Android sinifi yok): JVM'de sinanir. Es zamanlilik cagiranin isi (eklenti tek is parcacigi).
 */
class KartDepo @JvmOverloads constructor(
    private val kok: File,
    private val simdi: () -> Calendar = { Calendar.getInstance() },
    private val sil: (File) -> Boolean = { it.delete() },      // test: silme sirasini / yarida kalmayi gozlemek icin
) {

    private fun dizin(kimlik: String?): File {
        if (kimlik == null || !KIMLIK.matches(kimlik)) throw DepoHatasi("bicim")
        return File(kok, kimlik)
    }

    private fun hazir(kimlik: String?): File {
        val d = dizin(kimlik)
        if (!d.isDirectory && !d.mkdirs() && !d.isDirectory) throw DepoHatasi("yazilamadi")
        return d
    }

    fun veriBoyu(kimlik: String?): Long = File(dizin(kimlik), DOSYA).let { if (it.isFile) it.length() else 0L }

    /** `bas`tan en cok `azami` bayt. Sona gelindiyse bos dizi. */
    fun veriOku(kimlik: String?, bas: Long, azami: Int): ByteArray {
        if (bas < 0 || azami < 1 || azami > OKUMA_AZAMI) throw DepoHatasi("bicim")
        val f = File(dizin(kimlik), DOSYA)
        if (!f.isFile) return ByteArray(0)
        try {
            RandomAccessFile(f, "r").use { r ->
                val boy = r.length()
                if (bas >= boy) return ByteArray(0)
                val n = minOf(azami.toLong(), boy - bas).toInt()
                val b = ByteArray(n)
                r.seek(bas)
                r.readFully(b)
                return b
            }
        } catch (e: java.io.IOException) {
            throw DepoHatasi("okunamadi")
        }
    }

    /** Sona ekler ve fsync eder. Donus: yeni boy. */
    fun veriEkle(kimlik: String?, b: ByteArray): Long {
        if (b.size > YAZMA_AZAMI) throw DepoHatasi("bicim")
        val d = hazir(kimlik)
        val f = File(d, DOSYA)
        val yeni = !f.exists()
        try {
            FileOutputStream(f, true).use { a ->
                a.write(b)
                a.flush()
                a.fd.sync()
            }
            if (yeni) dizinEsitle(d)
        } catch (e: java.io.IOException) {
            throw DepoHatasi("yazilamadi")
        }
        return f.length()
    }

    fun veriKirp(kimlik: String?, n: Long) {
        if (n < 0 || n > KIRPMA_AZAMI) throw DepoHatasi("bicim")
        val d = hazir(kimlik)
        try {
            RandomAccessFile(File(d, DOSYA), "rw").use { r ->
                r.setLength(n)
                r.fd.sync()
            }
        } catch (e: java.io.IOException) {
            throw DepoHatasi("yazilamadi")
        }
    }

    fun durumOku(kimlik: String?): ByteArray? = kucukOku(File(dizin(kimlik), DURUM))
    fun durumYaz(kimlik: String?, b: ByteArray) = atomikYaz(File(hazir(kimlik), DURUM), b)
    fun kalOku(kimlik: String?): ByteArray? = kucukOku(File(dizin(kimlik), KAL_DOSYA))
    fun kalYaz(kimlik: String?, b: ByteArray) = atomikYaz(File(hazir(kimlik), KAL_DOSYA), b)

    /** Eski kalibrasyon dosyasinin zaman damgali, dayanikli kopyasi. Donus: dosya adi. */
    fun kalArsivle(kimlik: String?, b: ByteArray): String {
        val d = hazir(kimlik)
        val t = simdi()
        val kokAd = String.format(
            java.util.Locale.ROOT, "kalibrasyon-%04d%02d%02d-%02d%02d%02d",
            t.get(Calendar.YEAR), t.get(Calendar.MONTH) + 1, t.get(Calendar.DAY_OF_MONTH),
            t.get(Calendar.HOUR_OF_DAY), t.get(Calendar.MINUTE), t.get(Calendar.SECOND),
        )
        var ad = "$kokAd.json"
        var n = 1
        while (File(d, ad).exists()) {
            if (n > ARSIV_AZAMI) throw DepoHatasi("yazilamadi")
            ad = "$kokAd-$n.json"
            n += 1
        }
        atomikYaz(File(d, ad), b)
        return ad
    }

    /** "Kopyayi sifirla" (A23) / eslesmeyi kaldirirken: kartin butun dosyalari silinir. */
    fun sifirla(kimlik: String?) {
        val d = dizin(kimlik)
        val dosyalar = d.listFiles() ?: return
        // Sira ONEMLI: once veri, EN SON durum.json. Yarida kalirsa (durum var, veri yok / kisa) esitleyici
        // "depo kisa" der ve DURUR. Tersi (veri var, durum yok) durumu sifirdan saydirir ve kartin akisi
        // 1. siradan baslamiyorsa eldeki dosyayi SESSIZCE 0'a kirptirirdi.
        for (f in dosyalar.sortedBy { if (it.name == DURUM) 1 else 0 }) if (!sil(f) && f.exists()) throw DepoHatasi("yazilamadi")
        if (!sil(d) && d.exists()) throw DepoHatasi("yazilamadi")
    }

    /** Depolama satiri (Ayarlar): veri boyu + dizinin toplam boyu + arsiv sayisi. */
    fun boyutlar(kimlik: String?): Map<String, Any> {
        val d = dizin(kimlik)
        val dosyalar = d.listFiles() ?: emptyArray()
        return mapOf(
            "veri" to veriBoyu(kimlik),
            "toplam" to dosyalar.sumOf { it.length() },
            "arsiv" to dosyalar.count { it.name.startsWith("kalibrasyon-") && it.name.endsWith(".json") },
        )
    }

    /** Ham dosyanin yolu (WebKapi'nin yerel akitmasi icin). Dosya yoksa null. */
    fun veriDosyasi(kimlik: String?): File? = File(dizin(kimlik), DOSYA).takeIf { it.isFile }

    private fun kucukOku(f: File): ByteArray? {
        if (!f.isFile) return null
        if (f.length() > KUCUK_AZAMI) throw DepoHatasi("bozuk")
        return try { f.readBytes() } catch (e: java.io.IOException) { throw DepoHatasi("okunamadi") }
    }

    /** Gecici dosya -> fsync -> atomik yeniden adlandirma -> dizin fsync. */
    private fun atomikYaz(hedef: File, b: ByteArray) {
        if (b.size > KUCUK_AZAMI) throw DepoHatasi("bicim")
        val g = File(hedef.parentFile, hedef.name + GECICI_EK)
        try {
            FileOutputStream(g).use { a ->
                a.write(b)
                a.flush()
                a.fd.sync()
            }
            Files.move(g.toPath(), hedef.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
            dizinEsitle(hedef.parentFile!!)
        } catch (e: java.io.IOException) {
            throw DepoHatasi("yazilamadi")
        }
    }

    private fun dizinEsitle(dizin: File) {
        try {
            FileChannel.open(dizin.toPath(), StandardOpenOption.READ).use { it.force(true) }
        } catch (_: Exception) {
        }
    }

    companion object {
        const val DOSYA = "kayitlar.kyt"
        const val DURUM = "durum.json"
        const val KAL_DOSYA = "kalibrasyon.json"
        const val GECICI_EK = ".gecici"
        /** Tek kopru cagrisinda okunan / yazilan en cok bayt (base64 ile kopruden gecer). */
        const val OKUMA_AZAMI = 1 shl 20
        const val YAZMA_AZAMI = 1 shl 20
        /** durum.json / kalibrasyon.json tavani. */
        const val KUCUK_AZAMI = 1 shl 20
        /** Kartin kayit bolumu 11.4 MB; kopya birkac kat buyuyebilir ama sinirsiz degil. */
        const val KIRPMA_AZAMI = 1L shl 30
        const val ARSIV_AZAMI = 1000
        val KIMLIK = Regex("^[0-9a-f]{16}$")
    }
}
