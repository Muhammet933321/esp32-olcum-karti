package tr.olcumkarti.mobil.depo

import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import java.io.File
import java.util.Base64
import java.util.concurrent.Executors

/**
 * Kayit kopyasinin deposu (tasarim §2.2). Ince kabuk: mantik KartDepo'da (JVM'de sinanir). Butun
 * islemler TEK is parcaciginda SIRALI kosar: ekleme / kirpma / durum yazimi ic ice gecmez. Bayt
 * dizileri kopruden base64 gecer (parca basina en cok 1 MiB); buyuk dosyanin TAMAMI kopruden degil,
 * yerel akitmayla okunur (A24). Hata TUR adiyla doner; yol ve istisna mesaji kopruye gitmez.
 */
@CapacitorPlugin(name = "KartDepo")
class KartDepoPlugin : Plugin() {
    private val sira = Executors.newSingleThreadExecutor { r -> Thread(r, "kart-depo") }
    private val depo: KartDepo by lazy { KartDepo(File(context.filesDir, DIZIN)) }

    private fun kos(call: PluginCall, islem: (KartDepo, String?) -> JSObject) {
        try {
            sira.execute {
                try {
                    call.resolve(islem(depo, call.getString("kimlik")))
                } catch (e: DepoHatasi) {
                    call.reject(e.tur, e.tur)
                } catch (e: Throwable) {
                    call.reject("ic-hata", "ic-hata")
                }
            }
        } catch (e: Exception) {
            call.reject("ic-hata", "ic-hata")
        }
    }

    private fun bayt(call: PluginCall, ad: String): ByteArray {
        val s = call.getString(ad) ?: throw DepoHatasi("bicim")
        return try { Base64.getDecoder().decode(s) } catch (e: IllegalArgumentException) { throw DepoHatasi("bicim") }
    }

    private fun uzun(call: PluginCall, ad: String): Long {
        // JS sayisi kopruden Int / Long / Double gelebilir; tamsayi olmayan reddedilir.
        val d = call.data.opt(ad) as? Number ?: throw DepoHatasi("bicim")
        val v = d.toDouble()
        if (v.isNaN() || v != Math.floor(v) || v < 0 || v > 9.0e15) throw DepoHatasi("bicim")
        return v.toLong()
    }

    private fun b64(b: ByteArray?): JSObject {
        val o = JSObject()
        if (b != null) o.put("veri", Base64.getEncoder().encodeToString(b))
        o.put("var", b != null)
        return o
    }

    @PluginMethod fun veriBoyu(call: PluginCall) = kos(call) { d, k -> JSObject().put("boy", d.veriBoyu(k)) }

    @PluginMethod fun veriOku(call: PluginCall) = kos(call) { d, k ->
        b64(d.veriOku(k, uzun(call, "bas"), uzun(call, "azami").coerceAtMost(Int.MAX_VALUE.toLong()).toInt()))
    }

    @PluginMethod fun veriEkle(call: PluginCall) = kos(call) { d, k -> JSObject().put("boy", d.veriEkle(k, bayt(call, "veri"))) }

    @PluginMethod fun veriKirp(call: PluginCall) = kos(call) { d, k -> d.veriKirp(k, uzun(call, "boy")); JSObject() }

    @PluginMethod fun durumOku(call: PluginCall) = kos(call) { d, k -> b64(d.durumOku(k)) }

    @PluginMethod fun durumYaz(call: PluginCall) = kos(call) { d, k -> d.durumYaz(k, bayt(call, "veri")); JSObject() }

    @PluginMethod fun kalOku(call: PluginCall) = kos(call) { d, k -> b64(d.kalOku(k)) }

    @PluginMethod fun kalYaz(call: PluginCall) = kos(call) { d, k -> d.kalYaz(k, bayt(call, "veri")); JSObject() }

    @PluginMethod fun kalArsivle(call: PluginCall) = kos(call) { d, k -> JSObject().put("ad", d.kalArsivle(k, bayt(call, "veri"))) }

    @PluginMethod fun sifirla(call: PluginCall) = kos(call) { d, k -> d.sifirla(k); JSObject() }

    @PluginMethod fun boyutlar(call: PluginCall) = kos(call) { d, k ->
        val o = JSObject()
        for ((ad, v) in d.boyutlar(k)) o.put(ad, v)
        o
    }

    companion object {
        /** `files/kart/<kimlik>/` (yedeklemeye girmez: allowBackup=false + bos veri cikarma kurallari). */
        const val DIZIN = "kart"
    }
}
