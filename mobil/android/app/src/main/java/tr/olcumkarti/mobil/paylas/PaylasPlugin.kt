package tr.olcumkarti.mobil.paylas

import android.content.ClipData
import android.content.Intent
import androidx.core.content.FileProvider
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import java.io.File
import java.util.Base64
import java.util.concurrent.Executors

/**
 * Dosya paylasimi (tasarim A41; 5F). Ince kabuk: ad / boy / sira denetimi PaylasDeposu'nda (JVM'de sinanir).
 * Dosya uygulamanin onbellegine yazilir ve Android'in PAYLASIM PENCERESI acilir: nereye gidecegini kullanici
 * secer. Alici uygulama yalniz O dosyayi, yalniz OKUMA izniyle gorur (FileProvider; file_paths.xml yalniz
 * `cache/paylas/`i acar). Bu sinif aga cikmaz. Hata TUR adiyla doner; gunluk yok.
 */
@CapacitorPlugin(name = "Paylas")
class PaylasPlugin : Plugin() {
    private val sira = Executors.newSingleThreadExecutor { r -> Thread(r, "paylas") }
    private val depo: PaylasDeposu by lazy { PaylasDeposu(File(context.cacheDir, DIZIN)) }

    private fun kos(call: PluginCall, islem: () -> JSObject) {
        try {
            sira.execute {
                try {
                    call.resolve(islem())
                } catch (e: PaylasHatasi) {
                    call.reject(e.tur, e.tur)
                } catch (e: Throwable) {
                    call.reject("ic-hata", "ic-hata")
                }
            }
        } catch (e: Exception) {
            call.reject("ic-hata", "ic-hata")
        }
    }

    /** Uygulama acilirken onceki paylasimin dosyasi silinir (onbellekte olcum verisi BEKLEMEZ). */
    override fun load() {
        try { sira.execute { try { depo.temizle() } catch (_: Exception) {} } } catch (_: Exception) {}
    }

    @PluginMethod
    fun baslat(call: PluginCall) = kos(call) {
        depo.baslat(call.getString("ad"))
        JSObject()
    }

    @PluginMethod
    fun yaz(call: PluginCall) = kos(call) {
        val parca = try { Base64.getDecoder().decode(call.getString("parca") ?: throw PaylasHatasi("bicim")) } catch (e: IllegalArgumentException) { throw PaylasHatasi("bicim") }
        depo.yaz(call.getString("ad"), parca)
        JSObject()
    }

    @PluginMethod
    fun gonder(call: PluginCall) = kos(call) {
        val mime = call.getString("mime")
        if (mime == null || mime !in PaylasDeposu.MIMELER) throw PaylasHatasi("bicim")
        val boy = (call.data.opt("boy") as? Number)?.toLong() ?: throw PaylasHatasi("bicim")
        val dosya = depo.bitir(call.getString("ad"), boy)
        val adres = FileProvider.getUriForFile(context, context.packageName + ".fileprovider", dosya)
        val niyet = Intent(Intent.ACTION_SEND).setType(mime).putExtra(Intent.EXTRA_STREAM, adres)
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        niyet.clipData = ClipData.newRawUri(dosya.name, adres)
        val secici = Intent.createChooser(niyet, null).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        val etkinlik = activity ?: throw PaylasHatasi("ic-hata")
        etkinlik.runOnUiThread { try { etkinlik.startActivity(secici) } catch (_: Exception) {} }
        JSObject().put("acildi", true)
    }

    override fun handleOnDestroy() {
        sira.shutdown()
    }

    companion object {
        const val DIZIN = "paylas"
    }
}
