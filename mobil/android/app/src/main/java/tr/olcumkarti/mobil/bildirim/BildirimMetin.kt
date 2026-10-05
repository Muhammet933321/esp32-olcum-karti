package tr.olcumkarti.mobil.bildirim

import java.math.BigDecimal
import java.math.RoundingMode
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

/**
 * Bildirimin METNI (tasarim A43): `Bildirim` (anahtar + degerler) -> ekranda gorunecek cumle.
 * Sablonlar strings.xml'de (res/values/bildirim.xml tr, values-en en; PC'nin sozlugunden uretilir:
 * mobil/araclar/bildirim_metin_uret.py); `sozluk(ad)` secili dildeki sablonu verir ("bld.kopuk" ->
 * kaynak adi "bld_kopuk"), yoksa null. Yer tutucular "{ad}".
 * PC'nin `bildirim_metin.metin` / `kod_metni` / `_sayi` / `_sure` / `_saat_yazi` islevlerinin karsiligi:
 * ayni senaryoda PC ile AYNI cumle (mobil/test/vektor/bildirim_metin.json; BildirimMetinTest).
 * Saf Kotlin: Android sinifi yok.
 */
class BildirimMetin(
    private val dil: String,
    private val sozluk: (anahtar: String) -> String?,
    private val saatDilimi: TimeZone = TimeZone.getDefault(),
) {
    fun baslik(): String = metin("bld.baslik", emptyMap())

    fun kur(b: Bildirim): String = metin(b.anahtar, b.degerler.mapValues { yazi(it.value) })

    private fun metin(anahtar: String, deg: Map<String, String>): String {
        var s = sozluk(anahtar) ?: return anahtar
        for ((ad, d) in deg) s = s.replace("{$ad}", d)
        return s
    }

    private fun yazi(v: Any?): String = when (v) {
        null -> "?"
        is Kod -> kod(v)
        is Sayi -> sayi(v)
        is Sure -> sure(v.ms)
        is SaatEki -> metin(v.anahtar, mapOf("saat" to saat(v.unix)))
        else -> v.toString()
    }

    /** onek + kod sozlukte varsa o; yoksa onek + "bilinmeyen" ({kod} ile). */
    private fun kod(k: Kod): String {
        val kodYazi = k.kod?.toString() ?: "?"
        return sozluk(k.onek + kodYazi) ?: metin(k.onek + "bilinmeyen", mapOf("kod" to kodYazi))
    }

    /** x / bolen, `basamak` ondalik (yarim-cift yuvarlama: Python bicimlemesiyle ayni); tr'de virgul. */
    private fun sayi(s: Sayi): String {
        val x = s.x as? Long ?: return "?"
        val y = BigDecimal(x.toDouble() / s.bolen).setScale(s.basamak, RoundingMode.HALF_EVEN).toPlainString()
        return if (dil == "tr") y.replace('.', ',') else y
    }

    private fun sure(ms: Any?): String {
        val m = ms as? Long ?: return "?"
        if (m < 0) return "?"
        val sn = m / 1000
        return "%d:%02d:%02d".format(Locale.ROOT, sn / 3600, sn / 60 % 60, sn % 60)
    }

    private fun saat(unix: Long): String =
        SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.ROOT).apply { timeZone = saatDilimi }.format(Date(unix * 1000))
}
