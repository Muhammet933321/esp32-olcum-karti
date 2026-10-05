package tr.olcumkarti.mobil.kasa

import android.content.pm.PackageManager
import com.getcapacitor.JSArray
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import java.io.File
import java.util.concurrent.Executors

/**
 * Anahtar kasasi (tasarim A14, A16, A19, S1). Ince kabuk: mantik KasaKomut / KasaDeposu / SayacDosyasi'nda
 * (JVM'de sinanir). Butun islemler TEK is parcaciginda SIRALI kosar: dosya islemleri ic ice gecmez ve
 * sayac dosyasinin tek yazari burasidir. Hata TUR adiyla doner; istisna mesaji kopruye ve gunluge gitmez.
 */
@CapacitorPlugin(name = "Kasa")
class KasaPlugin : Plugin() {
    private val sira = Executors.newSingleThreadExecutor { r -> Thread(r, "kasa") }

    private val komut: KasaKomut by lazy {
        val strongBox = context.packageManager.hasSystemFeature(PackageManager.FEATURE_STRONGBOX_KEYSTORE)
        val sarici = KeystoreSarici(strongBox)
        KasaKomut(KasaDeposu(File(context.filesDir, "kasa"), sarici) { sarici.yokEt() })
    }

    private fun nesne(e: Map<*, *>): JSObject {
        val o = JSObject()
        for ((ad, d) in e) o.put(ad as String, cevir(d))
        return o
    }

    private fun cevir(d: Any?): Any? = when (d) {
        is Map<*, *> -> nesne(d)
        is List<*> -> JSArray().also { dizi -> for (x in d) dizi.put(cevir(x)) }
        else -> d
    }

    private fun kos(call: PluginCall, islem: (KasaKomut) -> Map<String, Any>) {
        try {
            sira.execute {
                try {
                    call.resolve(nesne(islem(komut)))
                } catch (e: KasaHatasi) {
                    call.reject(e.tur, e.tur)
                } catch (e: Throwable) {
                    call.reject("ic-hata", "ic-hata")
                }
            }
        } catch (e: Exception) {
            call.reject("ic-hata", "ic-hata")
        }
    }

    @PluginMethod
    fun anahtarYaz(call: PluginCall) {
        val kimlik = call.getString("kimlik")
        val n = call.getInt("n")
        val ad = call.getString("ad")
        val anahtar = call.getString("anahtar")
        kos(call) { it.anahtarYaz(kimlik, n, ad, anahtar) }
    }

    @PluginMethod
    fun anahtarOku(call: PluginCall) {
        val kimlik = call.getString("kimlik")
        kos(call) { it.anahtarOku(kimlik) }
    }

    @PluginMethod
    fun liste(call: PluginCall) {
        kos(call) { it.liste() }
    }

    @PluginMethod
    fun sil(call: PluginCall) {
        val kimlik = call.getString("kimlik")
        kos(call) {
            val sonuc = it.sil(kimlik)
            // Eslesme kaldirildi: o karti izleyen servis DURUR (curutucu 5E B20) — kaldirilmis kart izlenmez,
            // silinen ozet dosyalari yeniden olusmaz.
            if (kimlik != null && tr.olcumkarti.mobil.bildirim.IzlemeServisi.calisanKimlik == kimlik) {
                tr.olcumkarti.mobil.bildirim.IzlemeServisi.durdur(context)
            }
            sonuc
        }
    }

    @PluginMethod
    fun sayacOku(call: PluginCall) {
        val kimlik = call.getString("kimlik")
        kos(call) { it.sayacOku(kimlik) }
    }

    @PluginMethod
    fun sayacYaz(call: PluginCall) {
        val kimlik = call.getString("kimlik")
        val isaret = call.getString("isaret")
        kos(call) { it.sayacYaz(kimlik, isaret) }
    }

    override fun handleOnDestroy() {
        sira.shutdown()
    }
}
