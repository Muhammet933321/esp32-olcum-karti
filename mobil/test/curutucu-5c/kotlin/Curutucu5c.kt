package tr.olcumkarti.mobil.ag

import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicInteger

// CURUTUCU 5C — gercek P0 / SseAyirici'ya karsi JVM kaniti (Gradle KOSMAZ, ag YOK: gonder enjekte).
// Cikti "ad=deger" satirlari ve sonunda KIRMIZI sayisi. Beklenen (dogru) davranis yorumda.

private var kirmizi = 0
private fun iddia(ad: String, kosul: Boolean, ayrinti: String) {
    if (!kosul) kirmizi++
    println((if (kosul) "YESIL  " else "KIRMIZI ") + ad + " :: " + ayrinti)
}

fun main() {
    // ── K1: kart OLMAYAN bir adresin 200'u "durduruldu" sayiliyor VE gercek kartin yeniden denemesi birakiliyor ──
    // Senaryo: bagli adres = kart (ilk denemede 503 "mesgul" — P0-S'in var olma sebebi), ikinci adres
    // (onbellekteki eski IP ya da 192.168.4.1'de oturan BASKA bir cihaz) POST /komut'a hemen 200 diyor.
    // Dogru davranis: kart 2xx verene dek denenir; sonuc kartin adresidir.
    run {
        val kartDeneme = AtomicInteger(0)
        val kartBasari = AtomicInteger(0)
        val p0 = P0({ adres ->
            if (adres == "kart") {
                Thread.sleep(30)
                if (kartDeneme.incrementAndGet() == 1) 503 else { kartBasari.incrementAndGet(); 204 }
            } else {
                200                                   // kart degil: yonlendirici / baska ESP / eski IP'deki cihaz
            }
        })
        val s = p0.durdur(listOf("kart", "baska"))
        Thread.sleep(1500)                            // kartin butun yeniden denemelerine yetecek sure
        println("K1 tamam=${s.tamam} adres=${s.adres} kartDeneme=${kartDeneme.get()} kartBasari=${kartBasari.get()}")
        iddia("K1a p0 'tamam' dediyse KART durmus olmali", !s.tamam || kartBasari.get() > 0,
            "tamam=${s.tamam}, kartin 2xx verdigi deneme sayisi=${kartBasari.get()}")
        iddia("K1b kart 503 dedikten sonra yeniden denenmeli (baska adresin basarisi onu BIRAKTIRMAMALI)", kartDeneme.get() >= 2,
            "karta giden deneme=${kartDeneme.get()}")
    }

    // ── K2: kart p0'a 204 der (bos govde). 200 / 201 / 202 de 'basari' sayiliyor mu? ──
    run {
        val sonuclar = ArrayList<String>()
        for (kod in intArrayOf(200, 201, 202, 204, 299)) {
            val s = P0({ kod }).durdur(listOf("x"))
            sonuclar.add("$kod->${s.tamam}")
        }
        println("K2 " + sonuclar.joinToString(" "))
        iddia("K2 yalniz 204 basari sayilmali (kartin p0 yaniti; tasarim A9 'basari 204')",
            sonuclar == listOf("200->false", "201->false", "202->false", "204->true", "299->false"), sonuclar.joinToString(" "))
    }

    // ── K3: KALICI hata (wifi-yok / ozel-degil / bicim) de 4 kez deneniyor ve sonuc 900 ms gecikiyor ──
    // Wi-Fi kapaliyken dokunus: "ULASILAMADI" ancak ~0.9 s sonra gorunur; hazirla her denemede yeniden kosar.
    run {
        for (tur in listOf("wifi-yok", "ozel-degil", "bicim", "cleartext")) {
            val sayac = AtomicInteger(0)
            val t0 = System.nanoTime()
            val s = P0({ _ -> sayac.incrementAndGet(); throw AgHatasi(tur) }).durdur(listOf("192.168.1.7", "192.168.4.1"))
            val ms = (System.nanoTime() - t0) / 1_000_000
            println("K3 tur=$tur tamam=${s.tamam} gonderme=${sayac.get()} sure_ms=$ms")
            iddia("K3 kalici hata '$tur' yeniden denenmemeli (adres basina 1 deneme, < 200 ms)", sayac.get() <= 2 && ms < 200,
                "gonderme=${sayac.get()} (2 adres), sure=${ms} ms")
        }
    }

    // ── K4: asili gonder'ler — durdur() donduktan sonra geride kalan is parcaciklari ──
    // 20 hizli dokunus x 3 adres, her gonder 800 ms asili (baglanti zaman asimi) ve ag hatasi: is parcacigi sayisi.
    run {
        val canli = AtomicInteger(0)
        val azami = AtomicInteger(0)
        val gonder: (String) -> Int = { _ ->
            val n = canli.incrementAndGet()
            azami.accumulateAndGet(n) { a, b -> maxOf(a, b) }
            try { Thread.sleep(800) } finally { canli.decrementAndGet() }
            throw AgHatasi("zaman-asimi")
        }
        // Eklentinin GERCEK yolu: tek P0Tur (KartAgPlugin.p0Tur). Suren tura baglanilir.
        val tur = P0Tur(P0(gonder, { }))
        val bitti = java.util.concurrent.CountDownLatch(20)
        for (i in 0 until 20) {
            tur.durdur(listOf("a", "b", "c")) { bitti.countDown() }
            Thread.sleep(20)
        }
        bitti.await(15, java.util.concurrent.TimeUnit.SECONDS)
        Thread.sleep(300)
        println("K4 durdur'lar dondu; hala calisan gonder=${canli.get()} es zamanli azami=${azami.get()}")
        iddia("K4 art arda dokunusta es zamanli p0 baglantisi sinirli olmali (<= 12)", azami.get() <= 12,
            "es zamanli azami=${azami.get()} (20 dokunus x 3 adres, sinir yok)")
    }

    // ── K5: SseAyirici — 'kimlik' olayinin verisi varsayilan olaya KARISIYOR mu (bos satirsiz ad degisimi) ──
    run {
        val a = SseAyirici()
        val girdi = "event: kimlik\ndata: JETON-SINAMA\nevent: message\ndata: D 1.0 2.0 3.0 0 0 1 1 0 0\n\n"
        val olaylar = a.besle(girdi.toByteArray(Charsets.UTF_8))
        val tasinan = olaylar.filter { it.ad.isEmpty() || it.ad == "message" }.joinToString("|") { it.veri.replace("\n", "\\n") }
        println("K5 tasinan=$tasinan")
        iddia("K5 kimlik olayinin verisi JS'e tasinan satirlara girmemeli", !tasinan.contains("JETON-SINAMA"), tasinan)
        val b = SseAyirici()
        val olay2 = b.besle("Event: kimlik\ndata: JETON-SINAMA\n\n".toByteArray(Charsets.UTF_8))
        val tas2 = olay2.filter { it.ad.isEmpty() || it.ad == "message" }.joinToString("|") { it.veri }
        println("K5b tasinan=$tas2")
        iddia("K5b alan adi buyuk harfle ('Event:') yazilan kimlik olayi tasinmamali", !tas2.contains("JETON-SINAMA"), tas2)
    }

    println("KIRMIZI=$kirmizi")
}
