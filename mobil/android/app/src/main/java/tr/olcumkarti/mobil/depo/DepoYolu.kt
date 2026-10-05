package tr.olcumkarti.mobil.depo

/**
 * Ham kayit dosyasinin WebView'e YEREL akitilmasi (tasarim A24): buyuk dosya kopruden base64 ile
 * degil, `https://localhost/_depo/<kimlik>/kayitlar.kyt` adresinden `fetch` ile okunur. Bu adres
 * AGA CIKMAZ: MainActivity istegi yakalar ve dosyayi uygulamanin ozel dizininden verir.
 * Kural (saf, JVM'de sinanir): adres TAM bu bicimde olmali — sorgu / parca / ek yol / baska dosya
 * adi / buyuk harf / kacis dizisi YOK. Uymayan adres bu yoldan HICBIR dosya okutamaz.
 */
object DepoYolu {
    const val ON_EK = "https://localhost/_depo/"
    private val BICIM = Regex("^https://localhost/_depo/([0-9a-f]{16})/kayitlar[.]kyt$")

    /** Depo adresi mi (bicimi yanlis olsa da)? Oyleyse istek Capacitor'in dosya sunucusuna BIRAKILMAZ. */
    fun depoAdresi(url: String?): Boolean = url != null && url.startsWith(ON_EK)

    /** Gecerli depo adresinden kart kimligi; degilse null. */
    fun kimlik(url: String?): String? = if (url == null) null else BICIM.matchEntire(url)?.groupValues?.get(1)
}
