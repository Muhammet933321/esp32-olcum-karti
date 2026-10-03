package tr.olcumkarti.mobil.ag

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.util.Base64
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import tr.olcumkarti.mobil.BuildConfig
import java.net.HttpURLConnection
import java.net.Inet4Address
import java.net.Proxy
import java.net.URL
import java.util.concurrent.Executors

/**
 * Karta giden TEK ag yolu (tasarim §2.1, A3–A5). WebView kendi basina aga cikmaz (CSP).
 *  - hedef yalniz ozel/baglanti-yerel IPv4 ya da `olcum.local` (cozulen adres yine ozel olmali)
 *  - baglanti etkin Wi-Fi agina bagli, vekilsiz, yonlendirme izlenmez
 *  - hata, TUR adiyla doner; istisna mesaji kopruye ve gunluge gitmez
 */
@CapacitorPlugin(name = "KartAg")
class KartAgPlugin : Plugin() {
    private val havuz = Executors.newCachedThreadPool()

    private fun wifiAgi(): Network? {
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        @Suppress("DEPRECATION")
        for (ag in cm.allNetworks) {
            val y = cm.getNetworkCapabilities(ag) ?: continue
            if (y.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) return ag
        }
        return null
    }

    /** Dogrulanmis baglanti kurucu + IP'ye cevrilmis URL. */
    private fun hazirla(url: String): Pair<String, (URL) -> HttpURLConnection> {
        val u = try { URL(url) } catch (e: Exception) { throw AgHatasi("bicim") }
        if (u.protocol != "http" || u.userInfo != null) throw AgHatasi("bicim")
        val port = if (u.port < 0) Hedef.VARSAYILAN_PORT else u.port
        val h = try {
            Hedef.ayir("${u.host}:$port", BuildConfig.DEBUG)
        } catch (e: Hedef.Hata) {
            throw AgHatasi(e.tur)
        }
        // Yerel dongu (yalniz hata ayiklama derlemesi, adb reverse): Wi-Fi'ye baglanmaz.
        if (h.ad == "127.0.0.1") {
            return Pair(url) { x -> x.openConnection(Proxy.NO_PROXY) as HttpURLConnection }
        }
        val ag = wifiAgi() ?: throw AgHatasi("wifi-yok")
        var ip = h.ad
        if (h.ad == Hedef.KART_ADI) {
            val adresler = try { ag.getAllByName(h.ad) } catch (e: Exception) { throw AgHatasi("ad-cozulmedi") }
            ip = adresler.filterIsInstance<Inet4Address>().mapNotNull { it.hostAddress }
                .firstOrNull { Hedef.ozelAdres(it) } ?: throw AgHatasi("ozel-degil")
        }
        val dosya = u.file ?: ""
        return Pair("http://$ip:${h.port}$dosya") { x -> ag.openConnection(x, Proxy.NO_PROXY) as HttpURLConnection }
    }

    @PluginMethod
    fun istek(call: PluginCall) {
        val url = call.getString("url")
        val yontem = call.getString("yontem") ?: "GET"
        val zamanAsimi = (call.getInt("zamanAsimiMs") ?: 5000).coerceIn(100, 60000)
        val azami = (call.getInt("azamiGovde") ?: HttpIstek.AZAMI_GOVDE).coerceIn(1, HttpIstek.AZAMI_GOVDE_SINIR)
        val basliklar = HashMap<String, String>()
        call.getObject("basliklar")?.let { o -> for (ad in o.keys()) basliklar[ad] = o.getString(ad) ?: "" }
        val govde64 = call.getString("govde")
        if (url == null) { call.reject("bicim", "bicim"); return }
        havuz.execute {
            try {
                val govde = govde64?.let { Base64.decode(it, Base64.NO_WRAP) }
                val (hedefUrl, ac) = hazirla(url)
                val y = HttpIstek(ac).yap(yontem, hedefUrl, basliklar, govde, zamanAsimi, azami)
                val bas = JSObject()
                for ((ad, deger) in y.basliklar) bas.put(ad, deger)
                val sonuc = JSObject()
                sonuc.put("kod", y.kod)
                sonuc.put("basliklar", bas)
                sonuc.put("govde", Base64.encodeToString(y.govde, Base64.NO_WRAP))
                sonuc.put("adres", URL(hedefUrl).let { "${it.host}:${it.port}" })
                call.resolve(sonuc)
            } catch (e: AgHatasi) {
                call.reject(e.tur, e.tur)
            } catch (e: Exception) {
                call.reject("ic-hata", "ic-hata")
            }
        }
    }

    @PluginMethod
    fun wifiDurumu(call: PluginCall) {
        val sonuc = JSObject()
        sonuc.put("wifi", wifiAgi() != null)
        sonuc.put("hataAyiklama", BuildConfig.DEBUG)
        call.resolve(sonuc)
    }
}
