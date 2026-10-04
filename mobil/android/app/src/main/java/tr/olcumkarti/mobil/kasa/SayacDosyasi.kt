package tr.olcumkarti.mobil.kasa

import java.io.File
import java.util.zip.CRC32

/**
 * Imza sayacinin diskteki ISARETI (A16). Bicim: "<ondalik>\n<crc32, 8 onaltilik hane>\n".
 *  - dosya yok          -> 0
 *  - yarim / bozuk      -> `bozuk` (sessizce 0 DONULMEZ: sayac geri giderse kart istegi tekrar diye reddeder)
 *  - yazim              -> diskteki degerden kucukse `geri`; degilse dayanikli + atomik
 * Tek yazar varsayilir (S1: yalniz Kasa eklentisi, tek is parcacigi). Saf JVM: gecici dizinde sinanir.
 */
class SayacDosyasi(private val dosya: File) {

    fun oku(): Long {
        if (!dosya.exists()) return 0L
        if (dosya.length() > AZAMI_BOY) throw KasaHatasi("bozuk")
        val metin = try { String(dosya.readBytes(), Charsets.ISO_8859_1) } catch (e: Exception) { throw KasaHatasi("bozuk") }
        val satirlar = metin.split("\n")
        if (satirlar.size != 3 || satirlar[2].isNotEmpty()) throw KasaHatasi("bozuk")
        val deger = try { ayristir(satirlar[0]) } catch (e: KasaHatasi) { throw KasaHatasi("bozuk") }
        if (deger.toString() != satirlar[0]) throw KasaHatasi("bozuk")
        if (satirlar[1] != saglama(satirlar[0])) throw KasaHatasi("bozuk")
        return deger
    }

    /** @return yazilan isaret */
    fun yaz(isaret: Long): Long {
        if (isaret < 0) throw KasaHatasi("bicim")
        val eski = oku()
        if (isaret < eski) throw KasaHatasi("geri")
        val metin = isaret.toString()
        try {
            AtomikYazim.yaz(dosya, "$metin\n${saglama(metin)}\n".toByteArray(Charsets.US_ASCII))
        } catch (e: KasaHatasi) {
            throw e
        } catch (e: Exception) {
            throw KasaHatasi("ic-hata")
        }
        return isaret
    }

    companion object {
        private const val AZAMI_BOY = 64L

        /** Yalniz 1..19 ondalik hane ve Long sinirinda; degilse `bicim`. */
        fun ayristir(metin: String?): Long {
            if (metin == null || metin.isEmpty() || metin.length > 19 || !metin.all { it in '0'..'9' }) throw KasaHatasi("bicim")
            return metin.toLongOrNull() ?: throw KasaHatasi("bicim")
        }

        internal fun saglama(metin: String): String {
            val c = CRC32()
            c.update(metin.toByteArray(Charsets.US_ASCII))
            return String.format("%08x", c.value)
        }
    }
}
