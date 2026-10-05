package tr.olcumkarti.mobil.bildirim

/**
 * Anlik izlemenin YENIDEN BAGLANMA dongusu (tasarim A28, A31, A34): izleme oturumlarini art arda kosar,
 * arada `Izleyici.bekleme` kadar bekler ve her durum degisikligini `durum`a bildirir (servisin kalici
 * bildirimi bununla guncellenir).
 *   baglaniyor : oturum aciliyor          izleniyor : araciya abone, kart dinleniyor
 *   internet   : telefonun interneti yok / koptu (A34 — kart icin alarm DEGIL); hizla yeniden denenir
 *   guven      : sertifika / ad dogrulanamadi (S2)          araci : araci reddetti / protokol
 * Bitis:
 *   kayit-bitti : kayit bitti, izlemeye gerek kalmadi (A28: servis kendini durdurur)
 *   ayar        : zarf / anahtar / araci kimligi gecersiz — uygulama kartin aginda acilana dek DENENMEZ (A31)
 *   durduruldu  : cagiran durdurdu
 * `bekle(ms)`: en cok ms bekler; `uyandir` (ag geri geldi) ya da `durdur` beklemeyi keser.
 * Saf Kotlin: oturum ve bekleme enjekte, JVM'de sinanir.
 */
class IzlemeDongusu(
    private val oturum: (baglandi: () -> Unit) -> IzlemeBitis,
    private val bekle: (ms: Long) -> Unit,
    private val durum: (String) -> Unit,
) {
    @Volatile private var dur = false

    fun durdur() {
        dur = true
    }

    fun calis(): String {
        var deneme = 0
        while (!dur) {
            durum("baglaniyor")
            val b = oturum { durum("izleniyor") }
            if (dur) break
            when (b.sinif) {
                "tamam" -> return if (b.tur == "gerek-kalmadi") "kayit-bitti" else "durduruldu"
                "ayar" -> return "ayar"
            }
            // Baglanip sonra kopan oturum bastan sayar: uzun sure izledikten sonraki ilk kopma HIZLI denenir.
            deneme = if (b.baglandi) 1 else deneme + 1
            durum(b.sinif)
            bekle(Izleyici.bekleme(b, deneme) ?: return "durduruldu")
        }
        return "durduruldu"
    }
}
