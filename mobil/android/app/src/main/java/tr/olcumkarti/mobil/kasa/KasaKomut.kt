package tr.olcumkarti.mobil.kasa

import java.util.Base64

/**
 * Eklenti yontemlerinin govdesi: kopruden gelen ham degerler (eksik / yanlis turde olabilir) -> sonuc eslemi.
 * Saf JVM: eklenti (KasaPlugin) yalniz JSON cevirir. Her hata KasaHatasi (tur); baska hicbir istisna cikmaz.
 */
class KasaKomut(private val depo: KasaDeposu) {

    private fun <T> sar(blok: () -> T): T = try {
        blok()
    } catch (e: KasaHatasi) {
        throw e
    } catch (e: Exception) {
        throw KasaHatasi("ic-hata")
    }

    fun anahtarYaz(kimlik: String?, n: Int?, ad: String?, anahtar64: String?): Map<String, Any> = sar {
        if (n == null || ad == null || anahtar64 == null) throw KasaHatasi("bicim")
        val anahtar = try { Base64.getDecoder().decode(anahtar64) } catch (e: IllegalArgumentException) { throw KasaHatasi("bicim") }
        try {
            depo.anahtarYaz(kimlik, n, ad, anahtar)
        } finally {
            anahtar.fill(0)
        }
        emptyMap()
    }

    fun anahtarOku(kimlik: String?): Map<String, Any> = sar {
        val k = depo.anahtarOku(kimlik)
        try {
            mapOf("kimlik" to k.kimlik, "n" to k.n, "ad" to k.ad, "anahtar" to Base64.getEncoder().encodeToString(k.anahtar))
        } finally {
            k.anahtar.fill(0)
        }
    }

    fun liste(): Map<String, Any> = sar {
        mapOf("kayitlar" to depo.liste().map { o ->
            if (o.bozuk) mapOf("kimlik" to o.kimlik, "bozuk" to true)
            else mapOf("kimlik" to o.kimlik, "n" to o.n, "ad" to o.ad)
        })
    }

    fun sil(kimlik: String?): Map<String, Any> = sar {
        depo.sil(kimlik)
        emptyMap()
    }

    fun sayacOku(kimlik: String?): Map<String, Any> = sar {
        mapOf("isaret" to depo.sayacOku(kimlik).toString())
    }

    fun sayacYaz(kimlik: String?, isaret: String?): Map<String, Any> = sar {
        if (!KasaKayit.kimlikGecerli(kimlik)) throw KasaHatasi("bicim")
        mapOf("isaret" to depo.sayacYaz(kimlik, SayacDosyasi.ayristir(isaret)).toString())
    }
}
