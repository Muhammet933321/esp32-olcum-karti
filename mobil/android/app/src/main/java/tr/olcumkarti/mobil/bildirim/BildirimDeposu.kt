package tr.olcumkarti.mobil.bildirim

import tr.olcumkarti.mobil.kasa.AtomikYazim
import tr.olcumkarti.mobil.kasa.KasaKayit
import java.io.File
import java.nio.ByteBuffer

/**
 * Bildirimin diskteki iki dosyasi, kasa dizininde (`files/kasa/`; eslesme kaldirilinca KasaDeposu.sil
 * `<kimlik>.` ile baslayan HER dosyayi siler — bunlar da gider):
 *   `<kimlik>.zarf` : kartin `/bildirim/bilgi` yaniti, OLDUGU GIBI (K ile sifreli; A31). Cozulmus araci
 *                     bilgisi diske HIC yazilmaz.
 *   `<kimlik>.olay` : islenen son olayin (acilis, sira) cifti — yeniden baslayinca kacirilan olay sayimi icin.
 *   `<kimlik>.adres`: kartin son baglanilan yerel adresi (ozel IPv4) — servisin A36 yoklamasi icin.
 *   `<kimlik>.durum`: yoklama ozeti (YoklamaDurumu) — iki yoklama arasinda neyin degistigini bulmak icin.
 * Kimlik dosya adina gider: her islemden once 16 kucuk onaltilik hane oldugu denetlenir.
 * Hata `ZarfHatasi("bicim")`; yol / icerik hata metnine girmez. Saf JVM.
 */
class BildirimDeposu(private val kok: File) {
    private fun dosya(kimlik: String?, ek: String): File {
        if (!KasaKayit.kimlikGecerli(kimlik)) throw ZarfHatasi("bicim")
        return File(kok, kimlik + ek)
    }

    /** Zarfi yazar (atomik). Bicimi (sihir, boy) tutmayan veri YAZILMAZ. */
    fun zarfYaz(kimlik: String?, zarf: ByteArray) {
        val hedef = dosya(kimlik, ZARF_EK)
        if (zarf.size < Zarf.EN_AZ || zarf.size > ZARF_AZAMI) throw ZarfHatasi("bicim")
        for (i in Zarf.SIHIR.indices) if (zarf[i] != Zarf.SIHIR[i]) throw ZarfHatasi("bicim")
        try { AtomikYazim.yaz(hedef, zarf) } catch (e: Exception) { throw ZarfHatasi("ic-hata") }
    }

    /** Zarf; yoksa ya da okunamiyorsa / boyu tutmuyorsa null (cagiran "ayar yenilenmeli" der). */
    fun zarfOku(kimlik: String?): ByteArray? {
        val d = dosya(kimlik, ZARF_EK)
        if (!d.isFile || d.length() < Zarf.EN_AZ || d.length() > ZARF_AZAMI) return null
        return try { d.readBytes() } catch (e: Exception) { null }
    }

    fun zarfVar(kimlik: String?): Boolean = zarfOku(kimlik) != null

    fun zarfSil(kimlik: String?) {
        val d = dosya(kimlik, ZARF_EK)
        if (d.exists() && !d.delete()) throw ZarfHatasi("ic-hata")
    }

    fun olayOku(kimlik: String?): Pair<Long, Long>? {
        val d = dosya(kimlik, OLAY_EK)
        if (!d.isFile || d.length() != 16L) return null
        return try {
            val b = ByteBuffer.wrap(d.readBytes())
            val a = b.long; val n = b.long
            if (a < 0 || n < 0) null else Pair(a, n)
        } catch (e: Exception) { null }
    }

    /** Yazilamazsa SESSIZCE gecer: bildirim akisi bir sayac dosyasi yuzunden durmaz. */
    fun olayYaz(kimlik: String?, a: Long, n: Long) {
        val hedef = dosya(kimlik, OLAY_EK)
        try { AtomikYazim.yaz(hedef, ByteBuffer.allocate(16).putLong(a).putLong(n).array()) } catch (_: Exception) {}
    }

    /** Yoklama ozeti (`<kimlik>.durum`); yoksa / bozuksa null. */
    fun durumOku(kimlik: String?): YoklamaDurumu? {
        val d = dosya(kimlik, DURUM_EK)
        if (!d.isFile || d.length() > DURUM_AZAMI) return null
        return YoklamaDurumu.coz(try { d.readText(Charsets.UTF_8) } catch (e: Exception) { null })
    }

    /** Yazilamazsa SESSIZCE gecer (en kotu sonuc: bir bildirimin yinelenmesi). */
    fun durumYaz(kimlik: String?, durum: YoklamaDurumu?) {
        val hedef = dosya(kimlik, DURUM_EK)
        if (durum == null) return
        try { AtomikYazim.yaz(hedef, durum.json().toByteArray(Charsets.UTF_8)) } catch (_: Exception) {}
    }

    /** Kartin son baglanilan YEREL adresi (A36 yoklamasi icin); gecersizse / yoksa null. */
    fun adresOku(kimlik: String?): String? {
        val d = dosya(kimlik, ADRES_EK)
        if (!d.isFile || d.length() > YerelYoklama.ADRES_AZAMI) return null
        val a = try { d.readText(Charsets.US_ASCII) } catch (e: Exception) { return null }
        return if (YerelYoklama.url(a) != null) a else null
    }

    /** Yalniz ozel IPv4 adresi yazilir (ad / herkese acik IP: ZarfHatasi("bicim")). */
    fun adresYaz(kimlik: String?, adres: String?) {
        val hedef = dosya(kimlik, ADRES_EK)
        if (adres == null || YerelYoklama.url(adres) == null) throw ZarfHatasi("bicim")
        try { AtomikYazim.yaz(hedef, adres.toByteArray(Charsets.US_ASCII)) } catch (e: Exception) { throw ZarfHatasi("ic-hata") }
    }

    /** Zarfi olan kartlar (dosya adindan; icerik acilmaz). */
    fun kimlikler(): List<String> =
        (kok.list() ?: emptyArray()).filter { it.endsWith(ZARF_EK) }.map { it.removeSuffix(ZARF_EK) }.filter { KasaKayit.kimlikGecerli(it) }.sorted()

    companion object {
        const val ZARF_EK = ".zarf"
        const val OLAY_EK = ".olay"
        const val DURUM_EK = ".durum"
        const val ADRES_EK = ".adres"
        const val DURUM_AZAMI = 512
        /** Kartin yaniti birkac yuz bayt; bundan buyugu zarf degildir. */
        const val ZARF_AZAMI = 2048
    }
}

/**
 * Kullanicinin bildirim ayari (A30, A38, A42): `anlik` = kayit surerken on plan servisiyle anlik izleme
 * (kapaliyken yalniz 15 dk'lik yoklama); `kapali` = gosterilmeyecek bildirim siniflari; `dil` = bildirim dili.
 * VARSAYILAN: anlik KAPALI (kalici bildirim ve pil muafiyeti isteyen sey kullanici acmadan baslamaz — A37),
 * butun siniflar ACIK.
 */
class BildirimAyar(val anlik: Boolean = false, val kapali: Set<String> = emptySet(), val dil: String = "tr") {
    fun acik(sinif: String): Boolean = sinif !in kapali

    fun json(): String {
        val k = SINIFLAR.filter { it in kapali }.joinToString(",") { "\"$it\"" }
        return "{\"anlik\":$anlik,\"kapali\":[$k],\"dil\":\"$dil\"}"
    }

    companion object {
        /** PC ile ayni siniflar (kopru/pc_bildirim.py SINIFLAR). */
        val SINIFLAR = listOf("kopuk", "bitti", "dolu", "esik", "yeniden_basladi", "kacirilan", "deneme")
        val DILLER = listOf("tr", "en")

        /** Gecersiz alan / bilinmeyen sinif AYIKLANIR; dosya bozuksa varsayilan (uygulama calismaya devam eder). */
        fun coz(metin: String?): BildirimAyar {
            val d = try { DuzJson.nesne(metin ?: return BildirimAyar()) } catch (e: JsonHatasi) { return BildirimAyar() }
            val anlik = d["anlik"] as? Boolean ?: false
            val kapali = (d["kapali"] as? List<*>)?.filterIsInstance<String>()?.filter { it in SINIFLAR }?.toSet() ?: emptySet()
            val dil = (d["dil"] as? String)?.takeIf { it in DILLER } ?: "tr"
            return BildirimAyar(anlik, kapali, dil)
        }

        fun oku(dosya: File): BildirimAyar =
            if (dosya.isFile && dosya.length() <= 1024) coz(try { dosya.readText(Charsets.UTF_8) } catch (e: Exception) { null }) else BildirimAyar()

        fun yaz(dosya: File, ayar: BildirimAyar) {
            try { AtomikYazim.yaz(dosya, ayar.json().toByteArray(Charsets.UTF_8)) } catch (e: Exception) { throw ZarfHatasi("ic-hata") }
        }
    }
}

/**
 * Telefon ureticisinin SINIFI (A37): pil yoneticisi yonergesi buna gore secilir. WebView'e yalniz bu sinif
 * gider — model / surum / seri GITMEZ.
 */
object Uretici {
    fun sinifi(uretici: String?, marka: String?): String {
        val u = ((uretici ?: "") + " " + (marka ?: "")).lowercase()
        return when {
            "honor" in u -> "honor"
            "huawei" in u -> "huawei"
            "xiaomi" in u || "redmi" in u || "poco" in u -> "xiaomi"
            "samsung" in u -> "samsung"
            else -> "diger"
        }
    }
}

/**
 * Bildirim sinifi -> Android kanali (A38): `uyari` sesli (haber yok, bellek doldu, esik), `bilgi` (kayit / pil
 * bitti, kart yeniden basladi, kacirilan, deneme); `izleme` servisin sessiz kalici bildirimi.
 */
object Kanal {
    const val IZLEME = "izleme"
    const val UYARI = "uyari"
    const val BILGI = "bilgi"

    fun sinifin(sinif: String): String = when (sinif) {
        "kopuk", "dolu", "esik" -> UYARI
        else -> BILGI
    }
}
