// Kotlin (JVM birim testi) mutasyonlari: her iddianin onu YALANLAYAN degisikligi.
//   ad    : "<dilim>: ne bozuluyor"
//   dosya : mobil/'e gore; bul: kaynakta TAM BIR KEZ gecen dizgi; koy: yerine konan
//   kirmizi: bu mutasyonda kirmiziya donmesi beklenen test (elle dogrulandi, 2026-10-04)
// Test: cd android && ./gradlew.bat testDebugUnitTest  (her mutasyon ayri kosu, ~1 dk) — KIRMIZI beklenir.
// fsync'in kalkmasi JVM testinde gozlenemez (elektrik kesmesi gerekir): bilerek listede YOK.
const KASA = "android/app/src/main/java/tr/olcumkarti/mobil/kasa/";
const AG = "android/app/src/main/java/tr/olcumkarti/mobil/ag/";

export default [
  {
    ad: "5B-K: sayacta geri denetimi kalkti",
    dosya: KASA + "SayacDosyasi.kt",
    bul: 'if (isaret < eski) throw KasaHatasi("geri")',
    koy: "",
    kirmizi: "SayacDosyasiTest.kucukDegerGeri_dosyaDegismez",
  },
  {
    ad: "5B-K: sayacta ESIT yazim kabul ediliyor (ikinci yazar ayni blogu kullanir — curutucu 5B S4)",
    dosya: KASA + "SayacDosyasi.kt",
    bul: 'if (vardi && isaret == eski) throw KasaHatasi("geri")',
    koy: "",
    kirmizi: "SayacDosyasiTest.esitYazimGeri_buyukKabul",
  },
  {
    ad: "5B-K: dosya yokken ilk yazim (0 dahil) 'geri' sayiliyor",
    dosya: KASA + "SayacDosyasi.kt",
    bul: "if (vardi && isaret == eski) throw",
    koy: "if (isaret == eski) throw",
    kirmizi: "SayacDosyasiTest.dosyaYokkenHerDegerIlkYazimdir_sifirDahil",
  },
  {
    ad: "5B-K: sil once sayaci siliyor (yarida kalirsa eski K sayac 0 ile yasar)",
    dosya: KASA + "KasaDeposu.kt",
    bul: "if (it == kimlik + ANAHTAR_EK) 0 else 1",
    koy: "if (it == kimlik + ANAHTAR_EK) 1 else 0",
    kirmizi: "KasaDeposuTest.silOnceAnahtariSiler_yaridaKalirsaAnahtarYasamaz",
  },
  {
    ad: "5B-K: bozuk saglamali sayac dosyasi kabul ediliyor",
    dosya: KASA + "SayacDosyasi.kt",
    bul: 'if (satirlar[1] != saglama(satirlar[0])) throw KasaHatasi("bozuk")',
    koy: "",
    kirmizi: "SayacDosyasiTest.bozukVeYarimDosyaBozuk_sifirDonmez",
  },
  {
    ad: "5B-K: kimlik deseni gevsedi (yol kacisi)",
    dosya: KASA + "KasaKayit.kt",
    bul: "kimlik.all { it in '0'..'9' || it in 'a'..'f' }",
    koy: "true",
    kirmizi: "KasaDeposuTest.kotuKimlikHerIslemdeBicim_dizinDisinaCikilamaz",
  },
  {
    ad: "5B-K: AAD'den kimlik cikti",
    dosya: KASA + "KasaKayit.kt",
    bul: "SIHIR + byteArrayOf(SURUM) + kimlik.toByteArray(Charsets.US_ASCII)",
    koy: "SIHIR + byteArrayOf(SURUM)",
    kirmizi: "KasaKayitTest.yanlisKimlikleAcilmaz",
  },
  {
    ad: "5B-K: anahtar uzunlugu denetimi kalkti",
    dosya: KASA + "KasaKayit.kt",
    bul: 'if (anahtar.size != ANAHTAR_BOYU) throw KasaHatasi("bicim")',
    koy: "",
    kirmizi: "KasaKayitTest.anahtarUzunluguTam32",
  },
  {
    ad: "5B-K: sil sayac dosyasini birakiyor",
    dosya: KASA + "KasaDeposu.kt",
    bul: 'ad.startsWith("$kimlik.")',
    koy: "ad == kimlik + ANAHTAR_EK",
    kirmizi: "KasaDeposuTest.silSonrasiYokVeSayacSifir",
  },
  {
    ad: "5A-K: HttpIstek toplam sure bekcisi kurulmuyor",
    dosya: AG + "HttpIstek.kt",
    bul: "}, zamanAsimiMs.toLong(), TimeUnit.MILLISECONDS)",
    koy: "}, Long.MAX_VALUE / 2, TimeUnit.MILLISECONDS)",
    kirmizi: "HttpIstekTest.baslikDamlatanSunucuToplamSureyleKesilir",
  },
  {
    ad: "5A-K: cozulen adres ozel adres suzgecinden gecmiyor",
    dosya: AG + "HedefCoz.kt",
    bul: "adresler.firstOrNull { Hedef.ozelAdres(it) }",
    koy: "adresler.firstOrNull()",
    kirmizi: "HedefCozTest.adCozulurVeCozulenAdresDeKuraldanGecer",
  },
  {
    ad: "5C-K: 4096 bayti asan SSE satiri bos satir gibi isleniyor (olay yarim veriyle dagitilir)",
    dosya: AG + "SseAyirici.kt",
    bul: "if (uzun) {",
    koy: "if (false) {",
    kirmizi: "SseAyiriciTest.satirSiniri4096Bayt_uzunSatirinOlayiAtilirSonrakiSaglam",
  },
  {
    ad: "5C-K: adli olaylar (kimlik: oturum jetonu) da satir olarak JS'e tasiniyor",
    dosya: AG + "Akis.kt",
    bul: 'if (o.ad.isEmpty() || o.ad == "message") satirlar.add(o.veri)',
    koy: "satirlar.add(o.veri)",
    kirmizi: "AkisTest.kartGibiAkis_satirlarSirayla_kimlikOlayiTasinmaz_baglantiBitinceKapandi",
  },
  {
    ad: "5C-K: kapat() baglantiyi kesmiyor (bloklu okuma surer, kartin yuvasi dolu kalir)",
    dosya: AG + "Akis.kt",
    bul: "try { baglanti?.disconnect() } catch (_: Exception) {}",
    koy: "",
    kirmizi: "AkisTest.kapat_blokluOkumayiHemenKeser_tekBitis_sonrasindaSatirYok",
  },
];
