// 5E bagimsiz curutucu — ELLE denenen ve YASAYAN mutasyonlar (2026-10-05). Bicim mobil/mutasyon/*-liste.mjs ile ayni:
//   dosya: mobil/'e gore; bul: kaynakta TAM BIR KEZ gecen dizgi; koy: yerine konan.
// Kotlin: `cd android && ./gradlew testDebugUnitTest -q` (butun JVM testleri) YESIL kaldi.
// JS: `npx vitest run --exclude 'test/curutucu-5e/**'` 559/559 YESIL kaldi.
// Denenen 57 mutasyonun 36'si oldu (BULGULAR.md "Olen mutasyonlar"); buradaki 21'i icin test YOK.
const B = "android/app/src/main/java/tr/olcumkarti/mobil/bildirim/";
const C = "src/cekirdek/";
const E = "src/ekran/";

export const KOTLIN = [
  { ad: "5E-C K01: Izleyici: bildirim anahtari cikista sifirlanmiyor", dosya: B + "Izleyici.kt",
    bul: "            bilgi.anahtar.fill(0)\n", koy: "" },
  { ad: "5E-C K05: MqttIstemci: ilk paketin CONNACK oldugu denetlenmiyor", dosya: B + "MqttIstemci.kt",
    bul: "            if (c.first shr 4 != MqttPaket.CONNACK) return MqttBitis(\"bicim\")\n", koy: "" },
  { ad: "5E-C K09: Izleyici: olay mesaji da 'durum goruldu' diye veriliyor (yoklama olayi durum sanar)", dosya: B + "Izleyici.kt",
    bul: "if (kalan == \"durum\") durumGoruldu(icerik)", koy: "durumGoruldu(icerik)" },
  { ad: "5E-C K14: BildirimDeposu.adresOku: boy siniri yok", dosya: B + "BildirimDeposu.kt",
    bul: "if (!d.isFile || d.length() > YerelYoklama.ADRES_AZAMI) return null", koy: "if (!d.isFile) return null" },
  { ad: "5E-C K16: BildirimAyar.oku: ayar dosyasinda boy siniri yok", dosya: B + "BildirimDeposu.kt",
    bul: "if (dosya.isFile && dosya.length() <= 1024)", koy: "if (dosya.isFile)" },
  { ad: "5E-C K18: Uretici: Redmi / Poco 'diger' sayiliyor (yanlis pil yonergesi)", dosya: B + "BildirimDeposu.kt",
    bul: "\"xiaomi\" in u || \"redmi\" in u || \"poco\" in u -> \"xiaomi\"", koy: "\"xiaomi\" in u -> \"xiaomi\"" },
  { ad: "5E-C K20: TlsBaglanti: el sikismada zaman asimi yok (susan sunucuda sonsuza dek bekler)", dosya: B + "TlsBaglanti.kt",
    bul: "                soket.soTimeout = BAGLANTI_MS\n", koy: "" },
  { ad: "5E-C K21: TlsBaglanti: TCP baglantisinda zaman asimi yok", dosya: B + "TlsBaglanti.kt",
    bul: "duz.connect(InetSocketAddress(adres.ad, adres.port), BAGLANTI_MS)", koy: "duz.connect(InetSocketAddress(adres.ad, adres.port))" },
  { ad: "5E-C K26: Zarf.coz: anahtar boyu denetlenmiyor (hata turu 'bicim' yerine 'etiket')", dosya: B + "Zarf.kt",
    bul: "if (anahtar.size != ANAHTAR || veri.size < EN_AZ) throw ZarfHatasi(\"bicim\")", koy: "if (veri.size < EN_AZ) throw ZarfHatasi(\"bicim\")" },
  { ad: "5E-C K32: Izleyici: istemci alani oturum bitince temizlenmiyor", dosya: B + "Izleyici.kt",
    bul: "                istemci = null\n", koy: "" },
];

export const JS = [
  { ad: "5E-C J02: soru: kayitBasladi kusak denetimi yok (biten kaydin sorusu sonradan cikiyor)", dosya: C + "bildirim.js",
    bul: "if (k !== kusak || d.anlik || d.calisiyor || !d.zarf) return;", koy: "if (d.anlik || d.calisiyor || !d.zarf) return;" },
  { ad: "5E-C J03: soru: yeni kayit onceki sonucu (acildi / acilamadi) silmiyor", dosya: C + "bildirim.js",
    bul: "    const k = ++kusak;\n    yay(\"yok\");\n", koy: "    const k = ++kusak;\n" },
  { ad: "5E-C J05: durum: calisiyor tur denetimsiz", dosya: C + "bildirim.js",
    bul: "calisiyor: y.calisiyor === true,", koy: "calisiyor: Boolean(y.calisiyor)," },
  { ad: "5E-C J06: durum: zarf tur denetimsiz", dosya: C + "bildirim.js",
    bul: "zarf: y.zarf === true,", koy: "zarf: Boolean(y.zarf)," },
  { ad: "5E-C J09: soru: 'hayir' acilmakta / acilmis izlemenin sonucunu da siliyor", dosya: C + "bildirim.js",
    bul: "hayir: () => { if (hal === \"soruluyor\") yay(\"yok\"); },", koy: "hayir: () => { yay(\"yok\"); }," },
  { ad: "5E-C J11: izlemeBaslat donusu: neden suzulmeden geciyor", dosya: C + "bildirim.js",
    bul: "neden: typeof y.neden === \"string\" && TUR.test(y.neden) ? y.neden : \"\" };", koy: "neden: y.neden };" },
  { ad: "5E-C J12: yerel: 'iletildi' tur denetimsiz", dosya: C + "bildirim.js",
    bul: ".iletildi === true;", koy: ".iletildi;" },
  { ad: "5E-C J13: rapor: kodu olmayan deger 'metin (null)' yaziliyor", dosya: C + "rapor_metin.js",
    bul: "return v.kod === null || v.kod === undefined ? v.metin : `${v.metin} (${v.kod})`;", koy: "return `${v.metin} (${v.kod})`;" },
  { ad: "5E-C J15: rapor: bos metin '—' yerine bos birakiliyor", dosya: C + "rapor_metin.js",
    bul: "if (v === null || v === undefined || v === \"\") return \"—\";", koy: "if (v === null || v === undefined) return \"—\";" },
  { ad: "5E-C J18: kayitlar.kalOku: gecersiz UTF-8 kalibrasyon gecmisi kabul", dosya: C + "kayitlar.js",
    bul: "new TextDecoder(\"utf-8\", { fatal: true })", koy: "new TextDecoder(\"utf-8\")" },
  { ad: "5E-C J23: ayar ekrani: 3 s'lik yenileme islem surerken de okuyor", dosya: E + "BildirimAyar.vue",
    bul: "setInterval(() => { if (!mesgul.value) oku(); }, 3000)", koy: "setInterval(() => { oku(); }, 3000)" },
];

export default [...KOTLIN, ...JS];
