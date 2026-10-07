package tr.olcumkarti.mobil.paylas

import android.content.Context
import android.os.Bundle
import android.os.CancellationSignal
import android.os.ParcelFileDescriptor
import android.print.PageRange
import android.print.PrintAttributes
import android.print.PrintDocumentAdapter
import android.print.PrintManager
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin

/** Yazdirma is adi: kuyrukta ve "PDF olarak kaydet"in onerdigi dosya adinda gorunur. Saf JVM (sinanir). */
object YazdirAdi {
    const val VARSAYILAN = "olcum-karti"
    const val AZAMI = 80
    private val IZINLI = Regex("[^A-Za-z0-9._ -]")
    private val HARF_RAKAM = Regex("[A-Za-z0-9]")

    fun temizle(ad: String?): String {
        val s = IZINLI.replace(ad ?: "", "_").trim().take(AZAMI)
        return if (HARF_RAKAM.containsMatchIn(s)) s else VARSAYILAN
    }
}

/** Asil uyarlayiciya aktarir; yazdirma oturumu bitince (yazdirildi / iptal / hata) BIR KEZ haber verir. */
class BitinceHaberVer(private val asil: PrintDocumentAdapter, private val bitti: () -> Unit) : PrintDocumentAdapter() {
    private var haberVerildi = false

    override fun onStart() = asil.onStart()

    override fun onLayout(eski: PrintAttributes?, yeni: PrintAttributes?, iptal: CancellationSignal?,
                          geri: LayoutResultCallback?, ek: Bundle?) = asil.onLayout(eski, yeni, iptal, geri, ek)

    override fun onWrite(sayfalar: Array<out PageRange>?, hedef: ParcelFileDescriptor?, iptal: CancellationSignal?,
                         geri: WriteResultCallback?) = asil.onWrite(sayfalar, hedef, iptal, geri)

    override fun onFinish() {
        try { asil.onFinish() } finally {
            if (!haberVerildi) { haberVerildi = true; bitti() }
        }
    }
}

/**
 * 5P (K12): panelin rapor "Yazdir"i. `window.print()` Android WebView'da hicbir sey yapmaz; bunun yerine
 * Android yazdirma penceresi WebView'in O ANKI icerigiyle acilir ("PDF olarak kaydet" dahil). Panel,
 * yazdirmadan once raporu gorunur kilar (`yazdirmaOncesi`) — ne yazdirilacagi panelin isi; burasi yalniz
 * pencereyi acar. Aga cikmaz; hata TUR adiyla doner, gunluk yok.
 */
@CapacitorPlugin(name = "Yazdir")
class YazdirPlugin : Plugin() {
    @PluginMethod
    fun yazdir(call: PluginCall) {
        val ad = YazdirAdi.temizle(call.getString("ad"))
        val etkinlik = activity
        if (etkinlik == null) {
            call.reject("ic-hata", "ic-hata")
            return
        }
        etkinlik.runOnUiThread {
            try {
                val yonetici = etkinlik.getSystemService(Context.PRINT_SERVICE) as PrintManager
                // Pencere KAPANANA dek (onFinish) yanit verilmez: panel yazdirmadan once acik temaya
                // geciyor ve yanit gelince geri aliyor — erken yanit PDF'i koyu temada cizdirirdi.
                val asil = bridge.webView.createPrintDocumentAdapter(ad)
                yonetici.print(ad, BitinceHaberVer(asil) { call.resolve(JSObject().put("acildi", true)) },
                    PrintAttributes.Builder().build())
            } catch (e: Exception) {
                call.reject("ic-hata", "ic-hata")
            }
        }
    }
}
