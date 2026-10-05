package tr.olcumkarti.mobil

/**
 * WebView'in ag kapisi. Kural (tasarim A47, kullanici sarti 2026-10-04): AGA CIKAN TEK YOL KartAg.
 * WebView yalniz paketteki dosyalari (`https://localhost/...`) ve yerel semalari (data, blob, about)
 * yukler; baska HER adres — herkese acik ya da yerel, http ya da https — istek olarak da gezinti
 * olarak da ENGELLENIR. CSP (index.html) ayni kuralin ikinci katmani.
 * Saf Kotlin: birim testinde kosar. Ayristirma elle: `java.net.URI`/`Uri` normallestirmesine guvenilmez.
 */
object WebKapi {
    /** WebRTC arayuzleri (src/cekirdek/rtc_kapat.js RTC_ADLARI ile AYNI liste; test karsilastirir). */
    val RTC_ADLARI = listOf(
        "RTCPeerConnection", "webkitRTCPeerConnection", "RTCDataChannel", "RTCSessionDescription",
        "RTCIceCandidate", "RTCRtpSender", "RTCRtpReceiver", "RTCRtpTransceiver",
    )

    /**
     * Belge basinda (her cercevede, sayfa betiklerinden ONCE) calisan betik: WebRTC arayuzlerini
     * kaldirir. Olculdu: bu WebView CSP `webrtc 'block'` yonergesini uygulamiyor.
     */
    val RTC_KAPAT: String = RTC_ADLARI.joinToString("") {
        "try{Object.defineProperty(window,'$it',{value:undefined,writable:false,configurable:false})}catch(e){}"
    }

    private val YEREL_SEMALAR = listOf("data:", "blob:", "about:")
    private const val KOKEN = "https://localhost"

    fun izinli(url: String?): Boolean {
        if (url == null) return false
        val u = url.trim()
        val kucuk = u.lowercase()
        if (YEREL_SEMALAR.any { kucuk.startsWith(it) }) return true
        if (!kucuk.startsWith(KOKEN)) return false
        // Kokenden sonra yalniz yol / sorgu / parca baslayabilir: "https://localhost.evil.com",
        // "https://localhost:8080", kullanici-adi bicimi (localhost + at isareti + baska alan) REDDEDILIR.
        if (u.length == KOKEN.length) return true
        val sonraki = u[KOKEN.length]
        if (sonraki != '/' && sonraki != '?' && sonraki != '#') return false
        // Ters egik cizgi ve kontrol karakteri: ayristirici farklarina kapi birakma.
        if (u.any { it == '\\' || it.code < 0x20 }) return false
        // Capacitor'in dosya / icerik on ekleri (`/_capacitor_file_/<mutlak yol>`, `/_capacitor_content_/…`)
        // uygulamanin okuyabildigi HER dosyayi verir (kasa, durum.json): KAPALI. Uygulama convertFileSrc
        // kullanmaz; ham kayit dosyasi yalniz DepoYolu'nun dar adresinden okunur. Yuzde kacisi yolda
        // (parcadan once) hic kabul edilmez: `/%5Fcapacitor_file_/` gibi kacisli bicimler de boylece duser.
        val yol = kucuk.substringBefore('#')
        if (yol.contains('%') || yol.contains("/_capacitor_")) return false
        return true
    }
}
