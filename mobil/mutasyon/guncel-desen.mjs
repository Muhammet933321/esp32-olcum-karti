// Kaynak degistikce ESKIYEN mutasyon desenlerinin guncel halleri (2026-10-05).
//
// Neden var: bir mutasyonun `bul` dizgisi kaynakta TAM BIR KEZ gecmezse kosucu onu "UYGULANAMADI" diye ATLAR —
// "oldu" sayilmaz ama gozden de kacar. `node mutasyon/desen-denetle.mjs` bunu testleri kosmadan bulur; ilk
// kosusunda eski dilimlerden 20 girdinin (sonraki duzeltmeler yuzunden) sessizce eskidigi goruldu. O girdiler
// farkli dosyalara dagilmis oldugu icin guncel desenleri BURADA, ada gore toplandi: iddia (ad) ayni kaldi,
// yalniz kaynaktaki yeri guncellendi. Anahtar: girdinin adinin BASI (liste.mjs'in ekledigi on ek dahil).
const S = String.raw;

const KARTAG_URL = 'val govde64 = call.getString("govde")\n        if (url == null) { call.reject("bicim", "bicim"); return }';
const KART_ISTEK = '    const b = baglanti, c = cihaz;\n    if (!b) throw new KartHatasi("bagli-degil");\n    if (!c || b.kimlik !== c.kimlik) throw new KartHatasi("eslesmemis");\n    const taban = tabanAl(b);';
const AG_HATA = 'sonuc = await sureli(eklenti.istek(istek), istek.zamanAsimiMs + SURE_PAYI_MS);\n    } catch (e) {\n      if (e instanceof KartAgHatasi) throw e;\n      const tur = e && typeof e.code === "string" && HATA_TURLERI.includes(e.code) ? e.code : "ic-hata";';
const TIK = "    if (!onde || !bagli || suren || sifirlaniyor) return false;";
const YUKLENEN = "if (!yuklenen || yuklenen.kimlik !== kimlik || yuklenen.boy !== boy || yuklenen.akisKimlik !== akisKimlik || yuklenen.kusak !== kusak()) {";

export const GUNCEL = {
  "5A-7 G1: Log.wtf": { bul: KARTAG_URL, koy: KARTAG_URL + '; android.util.Log.wtf("KartAg", url)' },
  "5A-6: eklenti adresi logcat'e yaziyor": { bul: KARTAG_URL, koy: KARTAG_URL + '; android.util.Log.d("KartAg", url)' },
  "5A-7 A1: yol karakter kumesi": {
    bul: S`const m = typeof url === "string" ? /^http:\/\/([^/?#]*)(\/[\x21-\x7e]*)?$/.exec(url) : null;`,
    koy: S`const m = typeof url === "string" ? /^http:\/\/([^/?#]*)(\/[^ ]*)?$/.exec(url) : null;`,
  },
  "5B-C: C5: istek, baglanti kimligi": { bul: KART_ISTEK, koy: KART_ISTEK.replace("if (!c || b.kimlik !== c.kimlik) throw", "if (!c) throw") },
  "5B: eslesmemisken imzali istek denetimi kalkti": { bul: KART_ISTEK, koy: KART_ISTEK.replace('    if (!c || b.kimlik !== c.kimlik) throw new KartHatasi("eslesmemis");\n', "") },
  "5A-4: kartFetch hedef kuralini": {
    bul: "  async function kartFetch(url, secenek = {}) {\n    urlDenetle(url, { yerelDongu });\n",
    koy: "  async function kartFetch(url, secenek = {}) {\n",
  },
  "5A-4: eklenti hatasinin ham kodu": { bul: AG_HATA, koy: AG_HATA.replace('HATA_TURLERI.includes(e.code) ? e.code : "ic-hata"', "true ? e.code : null") },
  "5D-esit: onay varsayilan ACIK": {
    bul: "const onayli = () => { try { return onayAcik() === true; } catch { return false; } };",
    koy: "const onayli = () => true;",
  },
  "5D-esit: onay icin gevsek dogruluk": {
    bul: "const onayli = () => { try { return onayAcik() === true; } catch { return false; } };",
    koy: "const onayli = () => { try { return Boolean(onayAcik()); } catch { return false; } };",
  },
  "5D-esit: onay acikken de Go gitmiyor": { bul: "        onay: turOnayli\n", koy: "        onay: false\n" },
  "5D-esit: her simdi() yeni tur baslatiyor": { bul: "    if (suren) return suren;\n    if (sifirlaniyor)", koy: "    if (sifirlaniyor)" },
  "5D-esit: tik arka planda da esitliyor": { bul: TIK, koy: "    if (!bagli || suren || sifirlaniyor) return false;" },
  "5D-esit: tik kart bagli degilken de esitliyor": { bul: TIK, koy: "    if (!onde || suren || sifirlaniyor) return false;" },
  "5D-kayit: dosya her listede yeniden cozuluyor": { bul: YUKLENEN, koy: "if (true) {" },
  "5D-kayit: akis kimligi degisince yeniden cozulmuyor": { bul: " || yuklenen.akisKimlik !== akisKimlik || yuklenen.kusak", koy: " || yuklenen.kusak" },
  "5D-D-B11: okuma ekrandaki kartin kopyasini": {
    bul: '    if ((await hazirla(gorunenKimlik)) === null) return null;\n    try { return await istemci.cagir("okuma", { oturum: no, tA, tB }); }',
    koy: '    try { return await istemci.cagir("okuma", { oturum: no, tA, tB }); }',
  },
  "5D-K: sifirla dizini birakiyor": {
    bul: '        if (!sil(d) && d.exists()) throw DepoHatasi("yazilamadi")\n',
    koy: "",
  },
  // 5E / 5F: curutucu 5E duzeltmelerinden sonra yeri degisen desenler
  "5E-4J: izlemeBaslat: kimlik denetimsiz": { bul: " : { kimlik: kimlikli(kimlik) });", koy: " : { kimlik });" },
  "5E-4J: izleyici: zarf her tikte yenileniyor": { bul: "    if (bagliKimlik !== kimlik) {\n      bagliKimlik = kimlik;\n      sifirla();", koy: "    if (true) {\n      bagliKimlik = kimlik;\n      sifirla();" },
  "5E-4J: izleyici: baglanti kopunca sifirlanmiyor": { bul: "      bagliKimlik = null;\n      sifirla();\n      return;", koy: "      return;" },
  "5E-4J: izleyici: ayni kayit durumu her tikte iletiliyor": { bul: "    if (g !== sonG) {\n      sonG = g;", koy: "    if (true) {\n      sonG = g;" },
  "5E-4J: izleyici: kayit bitince de izleme baslatiliyor": { bul: "if (baslat && KAYITTA.includes(durum)) {", koy: "if (baslat) {" },
  "5E-4J: izleyici: izleme baslatilamazsa yerel durum iletilmiyor": { bul: "try { basladi = (await bildirim.izlemeBaslat(kimlik)).basladi === true; } catch { basladi = false; }", koy: "basladi = (await bildirim.izlemeBaslat(kimlik)).basladi === true;" },
  "5E-4J: soru: 'ac' ayari asmiyor": { bul: "basladi = (await bildirim.izlemeBaslat(kimlik, { buKayit: true })).basladi === true;", koy: "basladi = (await bildirim.izlemeBaslat(kimlik)).basladi === true;" },
  "5F-J: rapor: sondaki sifirlar atilmiyor": { bul: "const z = y.replace(/([.,]\\d*?)0+$/, \"$1\").replace(/[.,]$/, \"\");", koy: "const z = y;" },
  "5E-4K: onek disi konu isleniyor": { bul: "val kalan = if (y.konu.startsWith(onek)) y.konu.substring(onek.length) else \"\"", koy: "val kalan = y.konu.substring(minOf(onek.length, y.konu.length))" },
  "5E-4K: anahtar siniri yok": { bul: "if (cozulen == 0 && (atilan >= ATILAN_SINIR || (tekSefer && kalan == \"durum\"))) bitir(\"anahtar\")", koy: "" },
  "5E-4K: cozulen mesaj varken de anahtar eskidi deniyor": { bul: "if (cozulen == 0 && (atilan >= ATILAN_SINIR ||", koy: "if ((atilan >= ATILAN_SINIR ||" },
  "5E-4B: dongu: baglanip kopan oturum bastan saymiyor": { bul: "deneme = if (b.baglandi && simdiMs() - bas >= KARARLI_MS) 1 else deneme + 1", koy: "deneme = deneme + 1" },
  "5E-4B: dongu: deneme sayaci artmiyor": { bul: "deneme = if (b.baglandi && simdiMs() - bas >= KARARLI_MS) 1 else deneme + 1", koy: "deneme = 1" },
  "5E-4D: adres dosyasina gecersiz adres yaziliyor": { bul: "val sade = YerelYoklama.sade(adres) ?: throw ZarfHatasi(\"bicim\")", koy: "val sade = adres ?: throw ZarfHatasi(\"bicim\")" },
  "5E-2K: SUBACK'ten once gelen kalici mesaj atiliyor": { bul: "                    bekleyenYayin.add(p)\n", koy: "" },
  "5E-K: MQTT ayristirici tampon siniri yok": { bul: "            if (boy > azami + 5 || n > azami + 5) throw MqttHatasi(\"buyuk\")\n", koy: "" },
};

// Listeyi guncel desenlerle dondurur (ada gore; eslesmeyen girdi oldugu gibi kalir).
export function guncelle(liste) {
  const anahtarlar = Object.keys(GUNCEL);
  return liste.map((m) => {
    const a = anahtarlar.find((k) => m.ad.startsWith(k));
    return a ? { ...m, bul: GUNCEL[a].bul, koy: GUNCEL[a].koy } : m;
  });
}
