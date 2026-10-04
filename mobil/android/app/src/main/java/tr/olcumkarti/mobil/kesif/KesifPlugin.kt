package tr.olcumkarti.mobil.kesif

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.os.Handler
import android.os.Looper
import com.getcapacitor.JSArray
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import tr.olcumkarti.mobil.ag.Hedef
import java.net.Inet4Address

/**
 * Agda servis taramasi (NSD / mDNS-SD), tasarim A1. Kart `_http._tcp` port 80'i `olcum` adiyla
 * duyurur; TXT `kimlik=<16 onaltilik>`. Buradan donen her sey yalnizca ADAYDIR: kimlik
 * `/eslestir/bilgi` ile dogrulanir (kesif.js). Ozel olmayan adres aday bile olmaz.
 */
@CapacitorPlugin(name = "Kesif")
class KesifPlugin : Plugin() {

    @PluginMethod
    fun nsdTara(call: PluginCall) {
        val sure = (call.getInt("sureMs") ?: 1200).coerceIn(200, 5000).toLong()
        val nsd = context.getSystemService(Context.NSD_SERVICE) as NsdManager
        val ana = Handler(Looper.getMainLooper())
        val kilit = Any()
        val bulunan = LinkedHashMap<String, JSObject>()
        val kuyruk = ArrayDeque<NsdServiceInfo>()
        var cozuluyor = false
        var bitti = false

        // Eski surumlerde ayni anda tek cozumleme yapilabilir: sirayla.
        fun sonrakiniCoz() {
            val s: NsdServiceInfo
            synchronized(kilit) {
                if (bitti || cozuluyor || kuyruk.isEmpty()) return
                s = kuyruk.removeFirst()
                cozuluyor = true
            }
            @Suppress("DEPRECATION")
            nsd.resolveService(s, object : NsdManager.ResolveListener {
                override fun onResolveFailed(info: NsdServiceInfo, kod: Int) {
                    synchronized(kilit) { cozuluyor = false }
                    sonrakiniCoz()
                }

                override fun onServiceResolved(info: NsdServiceInfo) {
                    @Suppress("DEPRECATION")
                    val ip = (info.host as? Inet4Address)?.hostAddress
                    if (ip != null && Hedef.ozelAdres(ip)) {
                        val o = JSObject()
                        o.put("ad", info.serviceName)
                        o.put("ip", ip)
                        o.put("port", info.port)
                        val kimlik = info.attributes["kimlik"]?.let { String(it, Charsets.US_ASCII) }
                        if (kimlik != null) o.put("kimlik", kimlik)
                        // Anahtar kimligi de icerir: ayni adresi baska kimlikle duyuran, gercek kaydi EZEMEZ.
                        synchronized(kilit) { if (bulunan.size < AZAMI_KAYIT) bulunan["$ip:${info.port}:$kimlik"] = o }
                    }
                    synchronized(kilit) { cozuluyor = false }
                    sonrakiniCoz()
                }
            })
        }

        val dinleyici = object : NsdManager.DiscoveryListener {
            override fun onStartDiscoveryFailed(tur: String, kod: Int) {}
            override fun onStopDiscoveryFailed(tur: String, kod: Int) {}
            override fun onDiscoveryStarted(tur: String) {}
            override fun onDiscoveryStopped(tur: String) {}
            override fun onServiceLost(info: NsdServiceInfo) {}
            override fun onServiceFound(info: NsdServiceInfo) {
                if (!info.serviceName.lowercase().startsWith(SERVIS_ADI)) return
                synchronized(kilit) { if (kuyruk.size < AZAMI_KAYIT) kuyruk.addLast(info) }
                sonrakiniCoz()
            }
        }

        try {
            nsd.discoverServices(SERVIS_TURU, NsdManager.PROTOCOL_DNS_SD, dinleyici)
        } catch (e: Exception) {
            call.resolve(JSObject().put("servisler", JSArray()))
            return
        }
        ana.postDelayed({
            try { nsd.stopServiceDiscovery(dinleyici) } catch (_: Exception) {}
            val dizi = JSArray()
            synchronized(kilit) {
                bitti = true
                for (o in bulunan.values) dizi.put(o)
            }
            call.resolve(JSObject().put("servisler", dizi))
        }, sure)
    }

    companion object {
        const val SERVIS_TURU = "_http._tcp."
        const val SERVIS_ADI = "olcum"
        const val AZAMI_KAYIT = 64      // kesif.js NSD_AZAMI_KAYIT ile ayni; siralama ve aday siniri orada
    }
}
