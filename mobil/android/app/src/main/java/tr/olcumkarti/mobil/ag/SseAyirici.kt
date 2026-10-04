package tr.olcumkarti.mobil.ag

/** Tamamlanmis bir SSE olayi. `ad` bos = varsayilan olay (kartin veri satirlari). */
class SseOlay(val ad: String, val veri: String)

/**
 * Bayt akisindan SSE olaylari (A6, A7). Saf: Android sinifi yok, JVM'de sinanir.
 *  - satir sonu LF, CRLF ya da yalniz CR; yarim satir sonraki beslemede tamamlanir
 *  - `data:` satirlari bos satirda olay olur (cok satirli veri yeni satirla birlesir); `event:` olayin adi
 *  - `id:`, `retry:`, yorum (`: kalp`) ve bilinmeyen alanlar olaya GIRMEZ
 *  - satir > SATIR_AZAMI bayt: satir ATILIR ve icinde bulundugu olay dagitilmaz (yarim veri tasinmaz);
 *    tampon hicbir zaman SATIR_AZAMI'yi asmaz. Olayin toplam verisi > VERI_AZAMI ise olay atilir.
 */
class SseAyirici {
    private val satir = ByteArray(SATIR_AZAMI)
    private var boy = 0
    private var tasti = false
    private var oncekiCr = false
    private var ilkSatir = true
    private var ad = ""
    private val veri = StringBuilder()
    private var veriVar = false
    private var bozuk = false

    fun tamponBoyu(): Int = boy

    fun besle(b: ByteArray, bas: Int = 0, n: Int = b.size): List<SseOlay> {
        val cikti = ArrayList<SseOlay>()
        for (i in bas until bas + n) {
            val c = b[i]
            if (c == LF && oncekiCr) {          // CRLF'nin ikinci yarisi: satir zaten bitti
                oncekiCr = false
                continue
            }
            oncekiCr = c == CR
            if (c == LF || c == CR) {
                satirBitti(cikti)
            } else if (boy < SATIR_AZAMI) {
                satir[boy++] = c
            } else {
                tasti = true
            }
        }
        return cikti
    }

    private fun satirBitti(cikti: MutableList<SseOlay>) {
        val uzun = tasti
        var s = if (uzun) "" else String(satir, 0, boy, Charsets.UTF_8)
        boy = 0
        tasti = false
        if (ilkSatir) {
            ilkSatir = false
            if (s.startsWith("﻿")) s = s.substring(1)
        }
        if (uzun) {
            bozuk = true
            return
        }
        if (s.isEmpty()) {
            if (veriVar && !bozuk) cikti.add(SseOlay(ad, veri.toString()))
            ad = ""
            veri.setLength(0)
            veriVar = false
            bozuk = false
            return
        }
        if (s[0] == ':') return                 // yorum (kalp atisi)
        val k = s.indexOf(':')
        val alan = if (k < 0) s else s.substring(0, k)
        var deger = if (k < 0) "" else s.substring(k + 1)
        if (deger.startsWith(" ")) deger = deger.substring(1)
        when (alan) {
            "data" -> {
                if (veriVar) veri.append('\n')
                veriVar = true
                if (veri.length + deger.length > VERI_AZAMI) bozuk = true else veri.append(deger)
            }
            "event" -> ad = deger
        }
    }

    companion object {
        const val SATIR_AZAMI = 4096
        const val VERI_AZAMI = 8192
        private const val LF = '\n'.code.toByte()
        private const val CR = '\r'.code.toByte()
    }
}
