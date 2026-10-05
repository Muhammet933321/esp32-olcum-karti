package tr.olcumkarti.mobil

import tr.olcumkarti.mobil.depo.DepoYolu

// CURUTUCU 5D — gercek WebKapi + DepoYolu'na karsi JVM kaniti (Gradle KOSMAZ, ag YOK, Android YOK).
// Cikti "YESIL / KIRMIZI ad :: ayrinti" satirlari ve sonunda KIRMIZI sayisi (cikis kodu = KIRMIZI sayisi).
//
// MainActivity.shouldInterceptRequest'in akisi (kaynaktan):
//   1) !WebKapi.izinli(url)          -> 403
//   2) DepoYolu.depoAdresi(url)      -> depoYaniti (yalniz TAM bicimli adres dosya verir)
//   3) aksi halde                    -> super.shouldInterceptRequest = Capacitor'in yerel sunucusu
// Capacitor'in yerel sunucusu (node_modules/@capacitor/android/.../WebViewLocalServer.java: isLocalFile,
// Bridge.CAPACITOR_FILE_START = "/_capacitor_file_") yolu "/_capacitor_file_" ile baslayan her istekte
// AndroidProtocolHandler.openFile(<mutlak yol>) ile UYGULAMANIN OKUYABILDIGI HER DOSYAYI verir.
// Yani 1. ve 2. adimdan gecen bir "/_capacitor_file_/..." adresi, DepoYolu'nun dar kuralinin YANINDAN
// ozel dizindeki baska dosyalari (durum.json, kasa dosyalari) WebView'e okutur.

private var kirmizi = 0
private fun iddia(ad: String, kosul: Boolean, ayrinti: String) {
    if (!kosul) kirmizi++
    println((if (kosul) "YESIL  " else "KIRMIZI ") + ad + " :: " + ayrinti)
}

/** MainActivity'nin karari: "403" | "depo" | "capacitor" (Capacitor'in yerel sunucusuna birakildi). */
private fun karar(url: String): String = when {
    !WebKapi.izinli(url) -> "403"
    DepoYolu.depoAdresi(url) -> "depo"
    else -> "capacitor"
}

fun main() {
    val k = "0123456789abcdef"
    val ozel = "/data/user/0/tr.olcumkarti.mobil/files"

    // Denetim: dar kural calisiyor.
    iddia("D0 gecerli depo adresi depoya gider", karar("https://localhost/_depo/$k/kayitlar.kyt") == "depo" &&
        DepoYolu.kimlik("https://localhost/_depo/$k/kayitlar.kyt") == k, "beklenen: depo")
    iddia("D0b depo on ekli baska dosya dosya vermez", DepoYolu.kimlik("https://localhost/_depo/$k/durum.json") == null, "kimlik null")

    // D1: Capacitor'in dosya on eki kapidan geciyor.
    val adresler = listOf(
        "https://localhost/_capacitor_file_$ozel/kart/$k/durum.json",
        "https://localhost/_capacitor_file_$ozel/kart/$k/kayitlar.kyt",
        "https://localhost/_capacitor_file_$ozel/kasa/anahtar",
        "https://localhost/_capacitor_content_/media/external/file/1",
    )
    for (u in adresler) {
        val s = karar(u)
        iddia("D1 ozel dizindeki dosyayi veren Capacitor adresi ENGELLENMELI", s == "403", "$u -> $s")
    }

    println("KIRMIZI=$kirmizi")
    System.exit(if (kirmizi > 0) 1 else 0)
}
