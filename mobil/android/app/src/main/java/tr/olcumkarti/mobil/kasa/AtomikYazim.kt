package tr.olcumkarti.mobil.kasa

import java.io.File
import java.io.FileOutputStream
import java.nio.channels.FileChannel
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.nio.file.StandardOpenOption

/**
 * Dayanikli, atomik dosya yazimi: gecici dosya -> fsync -> atomik yeniden adlandirma -> dizin fsync.
 * Yarida kesilirse hedef ya ESKI ya YENI icerigin tamamidir; gecici dosya kalintisi okumayi etkilemez.
 */
internal object AtomikYazim {
    const val GECICI_EK = ".gecici"

    fun gecici(hedef: File): File = File(hedef.parentFile, hedef.name + GECICI_EK)

    fun yaz(hedef: File, veri: ByteArray) {
        val dizin = hedef.parentFile ?: throw KasaHatasi("ic-hata")
        dizin.mkdirs()
        val g = gecici(hedef)
        FileOutputStream(g).use { a ->
            a.write(veri)
            a.flush()
            a.fd.sync()
        }
        Files.move(g.toPath(), hedef.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
        dizinEsitle(dizin)
    }

    /** Yeniden adlandirmanin kendisi de diske insin. Dizin acilamayan dosya sistemlerinde sessizce gecilir. */
    private fun dizinEsitle(dizin: File) {
        try {
            FileChannel.open(dizin.toPath(), StandardOpenOption.READ).use { it.force(true) }
        } catch (_: Exception) {
        }
    }
}
