package tr.olcumkarti.mobil.ag

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.os.SystemClock
import android.security.NetworkSecurityPolicy
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
import com.getcapacitor.JSArray
import java.util.Collections
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors
import java.util.concurrent.RejectedExecutionException
import java.util.concurrent.ScheduledFuture
import java.util.concurrent.ThreadPoolExecutor
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

/**
 * Karta giden TEK ag yolu (tasarim §2.1, A3–A5). WebView kendi basina aga cikmaz (CSP).
 *  - hedef yalniz ozel/baglanti-yerel IPv4 ya da `olcum.local` (cozulen adres yine ozel olmali)
 *  - baglanti etkin Wi-Fi agina bagli, vekilsiz, yonlendirme izlenmez
 *  - hata, TUR adiyla doner; istisna mesaji kopruye ve gunluge gitmez
 */
@CapacitorPlugin(name = "KartAg")
class KartAgPlugin : Plugin() {
    // Sinirli havuz: asili istekler is parcacigi biriktiremez; kuyruk dolarsa istek "mesgul" ile reddedilir.
    private val havuz = ThreadPoolExecutor(2, 8, 30, TimeUnit.SECONDS, ArrayBlockingQueue(32))

    private fun wifiAgi(): Network? {
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        @Suppress("DEPRECATION")
        for (ag in cm.allNetworks) {
            val y = cm.getNetworkCapabilities(ag) ?: continue
            // Wi-Fi ustundeki VPN agi da WIFI tasimasini bildirir: o ag secilirse ozel adrese giden
            // istek tunele girer. Yalniz VPN OLMAYAN Wi-Fi agi.
            if (y.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) && y.hasCapability(NetworkCapabilities.NET_CAPABILITY_NOT_VPN)) return ag
        }
        return null
    }

    /** Dogrulanmis baglanti kurucu + IP'ye cevrilmis URL (kural: HedefCoz, JVM'de sinanir). */
    private fun hazirla(url: String): Pair<String, (URL) -> HttpURLConnection> {
        var ag: Network? = null
        val c = HedefCoz.coz(url, BuildConfig.DEBUG) { ad ->
            val a = wifiAgi() ?: throw AgHatasi("wifi-yok")
            ag = a
            a.getAllByName(ad).filterIsInstance<Inet4Address>().mapNotNull { it.hostAddress }
        }
        // Ag guvenligi ayari bu adrese sifresiz HTTP'ye izin vermiyorsa bunu ACIKCA soyle (aksi halde
        // genel bir baglanti hatasi gibi gorunur).
        if (!NetworkSecurityPolicy.getInstance().isCleartextTrafficPermitted(c.ip)) throw AgHatasi("cleartext")
        // Yerel dongu (yalniz hata ayiklama derlemesi, adb reverse): Wi-Fi'ye baglanmaz.
        if (c.yerelDongu) return Pair(c.url) { x -> x.openConnection(Proxy.NO_PROXY) as HttpURLConnection }
        val wifi = ag ?: wifiAgi() ?: throw AgHatasi("wifi-yok")
        return Pair(c.url) { x -> wifi.openConnection(x, Proxy.NO_PROXY) as HttpURLConnection }
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
        val is_ = Runnable {
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
        try { havuz.execute(is_) } catch (e: RejectedExecutionException) { call.reject("mesgul", "mesgul") }
    }

    // Suren bir p0 turu varken gelen dokunus AYNI tura baglanir (P0Tur): is parcacigi birikmez.
    private val p0Tur = P0Tur(P0({ adres -> p0Gonder(adres) }))

    /**
     * ACIL DURDURMA (A8–A11). Ortak is parcacigi havuzunu KULLANMAZ (dolu kuyruk p0'i bekletemez):
     * kendi is parcaciklari. Imzasiz; kimlik dogrulamasi yok (taninmayan karta p0'in zarari yok).
     * Donus: { tamam, adres?, basarili: [204 veren adresler], deneme, sureMs }. Ilk adres "asil"dir.
     */
    @PluginMethod
    fun p0(call: PluginCall) {
        val dizi = call.getArray("adresler")
        val adresler = ArrayList<String>()
        if (dizi != null) for (i in 0 until dizi.length()) { val a = dizi.optString(i, ""); if (a.isNotEmpty()) adresler.add(a) }
        val t0 = SystemClock.elapsedRealtime()
        // asilVar: ilk adres bu baglantida dogrulanmis kart mi (JS soyler). Degilse ilk 204 sonuctur.
        val asilVar = call.getBoolean("asilVar", true) != false
        p0Tur.durdur(adresler, asilVar) { s ->
            val basarili = JSArray()
            for (a in s.basarili) basarili.put(a)
            val o = JSObject()
            o.put("tamam", s.tamam)
            if (s.adres != null) o.put("adres", s.adres)
            o.put("basarili", basarili)
            o.put("deneme", s.deneme)
            o.put("sureMs", SystemClock.elapsedRealtime() - t0)
            call.resolve(o)
        }
    }

    private fun p0Gonder(adres: String): Int {
        val (url, ac) = hazirla("http://$adres/komut")
        val basliklar = mapOf("X-Olcum" to "1", "Content-Type" to "text/plain")
        return HttpIstek(ac).yap("POST", url, basliklar, "p0".toByteArray(Charsets.US_ASCII), P0.BAGLANTI_SURESI_MS, 1024).kod
    }

    // ── CANLI AKIS (A6, A7) ─────────────────────────────────────────────────────────────────────
    // Her akis kendi is parcaciginda (ortak havuzu tutmaz). Olaylar: "akis" { kimlik, satirlar } ve
    // "akisDurum" { kimlik, hal: acik | kapandi | dolu | hata, tur?, kod? }. Adres (imza tasir) hicbir
    // olaya girmez. Hedef kurali + Wi-Fi baglama `hazirla` ile (istek ile ayni yol).
    private val akislar = ConcurrentHashMap<String, Akis>()
    private val akisNo = AtomicInteger(0)
    private val arkaPlandaKapanan: MutableSet<String> = Collections.synchronizedSet(HashSet())
    private val akisZamanlayici = Executors.newSingleThreadScheduledExecutor { r -> Thread(r, "akis-zaman").apply { isDaemon = true } }
    @Volatile private var arkaPlanIsi: ScheduledFuture<*>? = null

    private fun akisDurumBildir(kimlik: String, hal: String, tur: String?, kod: Int) {
        val o = JSObject()
        o.put("kimlik", kimlik)
        o.put("hal", hal)
        if (tur != null) o.put("tur", tur)
        if (kod > 0) o.put("kod", kod)
        notifyListeners("akisDurum", o)
    }

    @PluginMethod
    fun akisAc(call: PluginCall) {
        val url = call.getString("url")
        if (url == null) { call.reject("bicim", "bicim"); return }
        if (akislar.size >= AKIS_AZAMI) { call.reject("mesgul", "mesgul"); return }
        val kimlik = "a" + akisNo.incrementAndGet()
        val akis = Akis({ u -> val (hedefUrl, ac) = hazirla(u); ac(URL(hedefUrl)) }, object : Akis.Dinleyici {
            override fun satirlar(satirlar: List<String>) {
                val dizi = JSArray()
                for (s in satirlar) dizi.put(s)
                val o = JSObject()
                o.put("kimlik", kimlik)
                o.put("satirlar", dizi)
                notifyListeners("akis", o)
            }

            override fun durum(hal: String, tur: String?, kod: Int) {
                if (hal != "acik") akislar.remove(kimlik)
                akisDurumBildir(kimlik, hal, tur, kod)
            }
        })
        akislar[kimlik] = akis
        val sonuc = JSObject()
        sonuc.put("kimlik", kimlik)
        call.resolve(sonuc)
        Thread({ akis.calis(url) }, "akis-$kimlik").apply { isDaemon = true }.start()
    }

    @PluginMethod
    fun akisKapat(call: PluginCall) {
        val kimlik = call.getString("kimlik")
        // hepsi: WebView yeniden yuklendiyse onceki sayfanin akislari sahipsiz kalmistir. Kapanacaklar
        // SIMDI (cagri aninda) belirlenir: bu cagridan SONRA acilan akis etkilenmez.
        if (call.getBoolean("hepsi", false) == true) {
            val eskiler = ArrayList(akislar.values)
            akisZamanlayici.execute { for (a in eskiler) a.kapat() }
        }
        // Soket kapatma ag isidir: cagrinin is parcaciginda degil, zamanlayicida (hemen).
        if (kimlik != null) akislar[kimlik]?.let { a -> akisZamanlayici.execute { a.kapat() } }
        call.resolve()
    }

    private fun akislariKapat(arkaPlan: Boolean) {
        for ((kimlik, akis) in akislar) {
            if (arkaPlan) arkaPlandaKapanan.add(kimlik)
            akis.kapat()
        }
    }

    /** Arka plan: kartin 4 akis yuvasindan birini tutmamak icin acik akislar <= 5 s icinde kapanir (A6). */
    override fun handleOnPause() {
        super.handleOnPause()
        arkaPlanIsi?.cancel(false)
        arkaPlanIsi = akisZamanlayici.schedule({ akislariKapat(true) }, ARKA_PLAN_KAPAT_MS, TimeUnit.MILLISECONDS)
    }

    /** One gelince: arka planda kapanan akislar JS'e (yeniden) bildirilir; JS yeni imzali adresle acar. */
    override fun handleOnResume() {
        super.handleOnResume()
        arkaPlanIsi?.cancel(false)
        arkaPlanIsi = null
        val kapananlar = synchronized(arkaPlandaKapanan) { val k = ArrayList(arkaPlandaKapanan); arkaPlandaKapanan.clear(); k }
        for (kimlik in kapananlar) akisDurumBildir(kimlik, "kapandi", null, 0)
    }

    override fun handleOnDestroy() {
        arkaPlanIsi?.cancel(false)
        akisZamanlayici.execute { akislariKapat(false) }
        super.handleOnDestroy()
    }

    @PluginMethod
    fun wifiDurumu(call: PluginCall) {
        val sonuc = JSObject()
        sonuc.put("wifi", wifiAgi() != null)
        sonuc.put("hataAyiklama", BuildConfig.DEBUG)
        call.resolve(sonuc)
    }

    companion object {
        const val AKIS_AZAMI = 2                   // ayni anda acik akis (kartta 4 yuva var; uygulama 1 kullanir)
        const val ARKA_PLAN_KAPAT_MS = 4000L       // arka plana gecince: 5 s'den ONCE
    }
}
