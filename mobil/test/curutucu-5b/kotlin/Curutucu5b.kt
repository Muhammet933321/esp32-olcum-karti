package tr.olcumkarti.mobil.kasa

import java.io.File
import java.nio.file.Files

// CURUTUCU 5B — gercek KasaKomut / KasaDeposu / SayacDosyasi'na karsi JVM kaniti (Gradle KOSMAZ).
// Cikti "ad=deger" satirlari; ayrisma.test.js ayni girdileri kasa_sahtesi.mjs'e verip karsilastirir.

private class DuzSarici : Sarici {                      // sifreleme sinanmiyor: AAD'yi one ekler, acarken denetler
    override fun sar(duz: ByteArray, aad: ByteArray): ByteArray = byteArrayOf(aad.size.toByte()) + aad + duz
    override fun ac(sarili: ByteArray, aad: ByteArray): ByteArray {
        val n = sarili[0].toInt()
        if (!sarili.copyOfRange(1, 1 + n).contentEquals(aad)) throw IllegalStateException()
        return sarili.copyOfRange(1 + n, sarili.size)
    }
}

private fun tur(blok: () -> Any?): String = try { blok(); "tamam" } catch (e: KasaHatasi) { e.tur } catch (e: Throwable) { "BASKA:" + e.javaClass.simpleName }

fun main() {
    val kok = Files.createTempDirectory("curutucu5b").toFile()
    val depo = KasaDeposu(File(kok, "kasa"), DuzSarici())
    val komut = KasaKomut(depo)
    val k1 = "00112233aabbccdd"
    val k2 = "ffeeddcc99887766"
    val a44 = java.util.Base64.getEncoder().encodeToString(ByteArray(32) { it.toByte() })   // 43 karakter + "="
    val a43 = a44.trimEnd('=')

    // --- KasaKomut <-> kasa_sahtesi ayrismasi ---
    println("ad25=" + tur { komut.anahtarYaz(k1, 1, "a".repeat(25), a44) })
    println("ad24=" + tur { komut.anahtarYaz(k1, 1, "a".repeat(24), a44) })
    println("adTurkce13=" + tur { komut.anahtarYaz(k1, 1, "ç".repeat(13), a44) })          // 13 karakter = 26 bayt
    println("dolguFazla=" + tur { komut.anahtarYaz(k1, 1, "x", "$a43==") })
    println("dolgusuz=" + tur { komut.anahtarYaz(k1, 1, "x", a43) })
    println("isaret19=" + tur { komut.sayacYaz(k1, "9999999999999999999") })
    println("isaretBasSifir=" + tur { komut.sayacYaz(k1, "0005") })
    println("isaretBasSifirOku=" + komut.sayacOku(k1)["isaret"])
    // liste sirasi: once k2, sonra k1 yazilir
    komut.sil(k1)
    komut.anahtarYaz(k2, 2, "iki", a44)
    komut.anahtarYaz(k1, 1, "bir", a44)
    @Suppress("UNCHECKED_CAST")
    println("listeIlk=" + ((komut.liste()["kayitlar"] as List<Map<String, Any>>)[0]["kimlik"]))

    // --- sayac: ESIT deger 'geri' degil (ikinci yazar yakalanmaz) ---
    komut.sayacYaz(k1, "5000")
    println("esitYazim=" + tur { komut.sayacYaz(k1, "5000") })
    println("kucukYazim=" + tur { komut.sayacYaz(k1, "4999") })

    // --- sil yarida: .sayac gitti, .anahtar kaldi (surec iki silme arasinda oldu) ---
    File(File(kok, "kasa"), "$k1.sayac").delete()
    println("yarimSilAnahtar=" + tur { komut.anahtarOku(k1) })
    println("yarimSilSayac=" + komut.sayacOku(k1)["isaret"])
    println("listeSirasi=" + (File(kok, "kasa").list() ?: emptyArray()).joinToString(","))
    kok.deleteRecursively()
}
