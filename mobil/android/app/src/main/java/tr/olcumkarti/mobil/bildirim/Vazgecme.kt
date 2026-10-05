package tr.olcumkarti.mobil.bildirim

/**
 * Anlik izlemenin VAZGECME suresi (curutucu 5E K-7): araci karti kesintisiz SURE_MS boyunca "cevrimdisi"
 * diyorsa servis kendini durdurur. Kart kayit surerken temelli kapandiysa son bilinen durum hep "kayit
 * suruyor" kalir; sure olmasa servis (ve kalici bildirimi) kullanici durdurana dek yasardi.
 * Bir sey KAYBOLMAZ: "karttan haber yok" bildirimi durur, 15 dakikalik yoklama (A30) kartin donusunu bildirir
 * ve kayit suruyorsa anlik izlemeyi yeniden baslatir. Kart bir an bile cevrimici gorulurse sure sifirlanir;
 * durum BILINMIYORSA (araciya bagli degil / henuz okunmadi) sure islemez ama sifirlanmaz da.
 * Saf Kotlin, saat disaridan.
 */
class Vazgecme(private val sureMs: Long = SURE_MS) {
    private var kopukBas: Long? = null

    /** @param cevrimici araciya gore kart: true / false / null (bilinmiyor). */
    fun doldu(cevrimici: Boolean?, simdiMs: Long): Boolean {
        if (cevrimici == true) { kopukBas = null; return false }
        if (cevrimici == null) return false
        val bas = kopukBas ?: simdiMs.also { kopukBas = it }
        return simdiMs - bas >= sureMs
    }

    companion object {
        /** 6 saat: uzun bir ag / elektrik kesintisini bekler; yoklama zaten 15 dakikada bir bakar. */
        const val SURE_MS = 6 * 60 * 60 * 1000L
    }
}
