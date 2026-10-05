// 5C curutucu duzeltmelerini (DURUM 2026-10-05, bulgu 1–10) ve pil testinde salt okumayi (A40)
// koruyan mutasyonlar: her duzeltmenin onu GERI ALAN degisikligi. Kosum (mobil/ icinden):
//   node mutasyon/kos.mjs --neden 5C-D
const DURDUR = "test/durdur.test.js";
const KABUK = "test/kabuk.test.js";
const CANLI = "test/canli.test.js";
const DUGME = "test/kayit_dugme.test.js";
const AG = "test/ag.test.js";

export default [
  // ── bulgu 1 / 9: p0 sonucu ───────────────────────────────────────────────
  {
    ad: "5C-D1: asil adres bilinirken BASKA adresin 204'u de 'durduruldu' sayiliyor",
    dosya: "src/cekirdek/durdur.js",
    bul: 'basarili.includes(asil) || sonuc.adres === asil ? "durduruldu" : "baska-yanit"',
    koy: '"durduruldu"',
    test: DURDUR,
  },
  {
    ad: "5C-D1: tamam=false da 'durduruldu' sayiliyor",
    dosya: "src/cekirdek/durdur.js",
    bul: 'if (!sonuc || sonuc.tamam !== true) return "ulasilamadi";',
    koy: "",
    test: DURDUR,
  },
  {
    ad: "5C-D9: art arda dokunusta SON turun sonucu gecerli (basarili turu basarisiz tur eziyor)",
    dosya: "src/cekirdek/durdur.js",
    bul: "if (DERECE[h] > DERECE[enIyi]) enIyi = h;",
    koy: "enIyi = h;",
    test: DURDUR,
  },
  {
    ad: "5C-D9: eklenti koprusu eszamanli atinca durdur() istisna firlatiyor",
    dosya: "src/cekirdek/durdur.js",
    bul: "      bitti(null, asil);                          // eklenti koprusu atti: dokunus isleyicisine istisna CIKMAZ\n      return Promise.resolve(YOK);",
    koy: "      throw new Error('p0');",
    test: DURDUR,
  },
  {
    ad: "5C-D1: kartin erisim noktasi adresi listeye eklenmiyor",
    dosya: "src/cekirdek/durdur.js",
    bul: "const hedefler = [...liste, KART_AP_ADRESI];",
    koy: "const hedefler = [...liste];",
    test: DURDUR,
  },
  {
    ad: "5C-D1: eklentinin 'basarili' listesi suzulmuyor (gonderilmeyen adres kabul ediliyor)",
    dosya: "src/cekirdek/ag.js",
    bul: 'ham.filter((a) => typeof a === "string" && gonderilen.includes(a))',
    koy: "ham",
    test: DURDUR,
  },
  // ── bulgu 2: IP degisimi ─────────────────────────────────────────────────
  {
    ad: "5C-D2: 30 s kurali karti KOSULSUZ aramiyor (kart 'bagli' gorunuyorsa kesif kosmaz)",
    dosya: "src/ekran/kabuk_durum.js",
    bul: "await ara({ zorla: true });",
    koy: "await ara({ zorla: false });",
    test: DUGME,
  },
  {
    ad: "5C-D2: durdur adreslerinde olcum.local yok",
    dosya: "src/cekirdek/uygulama.js",
    bul: "for (const a of [bagliAdres, onbellekKaydi && onbellekKaydi.adres, KART_ADI]) {",
    koy: "for (const a of [bagliAdres, onbellekKaydi && onbellekKaydi.adres]) {",
    test: KABUK,
  },
  {
    ad: "5C-D2: 'asil' adres bildirilmiyor (hicbir adres asil degil: baska adresin yaniti durduruldu olur)",
    dosya: "src/cekirdek/uygulama.js",
    bul: 'asil: typeof bagli === "string" && bagli !== "" ? bagli : null',
    koy: "asil: null",
    test: KABUK,
  },
  // ── bulgu 3: bekleyen hiz ────────────────────────────────────────────────
  {
    ad: "5C-D3: bekleyen hizin omru yok (eski Gb'nin hizi cok sonraki kayda yapisir)",
    dosya: "src/ekran/kabuk_durum.js",
    bul: "t - bekleyenHiz.t <= HIZ_OMRU_MS && ",
    koy: "",
    test: DUGME,
  },
  {
    ad: "5C-D3: reddedilen Gb'nin hizi unutulmuyor",
    dosya: "src/ekran/kabuk_durum.js",
    bul: "if (bekleyenHiz === bekleyen) bekleyenHiz = null; throw e;",
    koy: "throw e;",
    test: DUGME,
  },
  // ── bulgu 4: eski olcum ──────────────────────────────────────────────────
  {
    ad: "5C-D4: akis akmiyorken de son olcum ekrana veriliyor",
    dosya: "src/ekran/durum_gorunum.js",
    bul: 'return hal === "acik" && son && typeof son === "object" ? son : null;',
    koy: 'return son && typeof son === "object" ? son : null;',
    test: DUGME,
  },
  // ── bulgu 5: geri cekilme ────────────────────────────────────────────────
  {
    ad: "5C-D5: kabugun yeniden aramasi geri cekilme sayacini sifirliyor",
    dosya: "src/cekirdek/canli.js",
    bul: "    if (!koru) {\n",
    koy: "    if (true) {\n",
    test: CANLI,
  },
  {
    ad: "5C-D5: kararlilik sarti yok (tek satir yollayip kapatan kart 1 s dongusune sokar)",
    dosya: "src/cekirdek/canli.js",
    bul: "if (acikMs !== null && simdiMs() - acikMs >= KARARLI_MS) {",
    koy: "if (acikMs !== null) {",
    test: CANLI,
  },
  {
    ad: "5C-D5: G? her acilista soruluyor (kayit durumu bilinse de)",
    dosya: "src/cekirdek/canli.js",
    bul: "if (kayit === null || simdiMs() - kayitMs >= KAYIT_ESKI_MS) {",
    koy: "if (true) {",
    test: CANLI,
  },
  // ── bulgu 6: serit ve kayit dugmesi ──────────────────────────────────────
  {
    ad: "5C-D6: ULASILAMADI kendiliginden siliniyor (kalici degil)",
    dosya: "src/bilesen/durdur_gorunum.js",
    bul: 'return hal === "durduruldu" ? DURDURULDU_SURE_MS : 0;',
    koy: "return DURDURULDU_SURE_MS;",
    test: KABUK,
  },
  {
    ad: "5C-D6: serit yeni hali gostermiyor",
    dosya: "src/bilesen/durdur_gorunum.js",
    bul: "    gosterilen = yeni;\n    goster(yeni);",
    koy: "    gosterilen = yeni;",
    test: KABUK,
  },
  {
    ad: "5C-D6: kayit dugmesi 'kapali' halde (dolu / hata / tariyor) basilabiliyor",
    dosya: "src/ekran/kayit_dugme.js",
    bul: "suruyor === true || !komutYolu || durumKapali || kilit.saltOkuma",
    koy: "suruyor === true || !komutYolu || kilit.saltOkuma",
    test: DUGME,
  },
  {
    ad: "5C-D6: 'Kaydi durdur' tek dokunusla durduruyor (onay adimi yok)",
    dosya: "src/ekran/kayit_dugme.js",
    bul: '  if (hal.is === "durdur") return onayci.bas() ? "durdur" : null;',
    koy: '  if (hal.is === "durdur") return "durdur";',
    test: DUGME,
  },
  {
    ad: "5C-D6: kapali dugmenin dokunusu is yapiyor",
    dosya: "src/ekran/kayit_dugme.js",
    bul: "  if (!hal || hal.kapali) return null;",
    koy: "  if (!hal) return null;",
    test: DUGME,
  },
  // ── bulgu 7: grafikte veri yok ───────────────────────────────────────────
  {
    ad: "5C-D7: gerilim okunamazken (adc_hata bit0) deger grafige giriyor",
    dosya: "src/cekirdek/canli.js",
    bul: "const v = (hata & 1) === 0 && Number.isFinite(d.v) ? d.v : NaN;",
    koy: "const v = Number.isFinite(d.v) ? d.v : NaN;",
    test: CANLI,
  },
  {
    ad: "5C-D7: NaN noktalar seriden cikarilmiyor (cizgi NaN / 0'a iner)",
    dosya: "src/ekran/canli_gorunum.js",
    bul: "    const d = verisizleriAt(t, seri[alan].subarray(bas, n));",
    koy: "    const d = { t, y: seri[alan].subarray(bas, n) };",
    test: DUGME,
  },
  // ── pil testinde salt okuma (A40) ────────────────────────────────────────
  {
    ad: "5C-D-PIL: pil testi surerken kayit dugmeleri acik",
    dosya: "src/ekran/durum_gorunum.js",
    bul: 'if (tur === OTURUM_TURU.PIL) return { saltOkuma: true,',
    koy: 'if (tur === OTURUM_TURU.PIL) return { saltOkuma: false,',
    test: DUGME,
  },
  {
    ad: "5C-D-PIL: tur BILINMIYORKEN dugmeler kapaniyor (liste okunamazsa kayit durdurulamaz)",
    dosya: "src/ekran/durum_gorunum.js",
    bul: "  return { saltOkuma: false, rozet: null, aciklama: null };",
    koy: "  return { saltOkuma: true, rozet: null, aciklama: null };",
    test: DUGME,
  },
  {
    ad: "5C-D-PIL: oturum turu baska oturumun kaydindan okunuyor",
    dosya: "src/ekran/durum_gorunum.js",
    bul: 'o && typeof o === "object" && o.id === oturum',
    koy: 'o && typeof o === "object"',
    test: DUGME,
  },
  {
    ad: "5C-D-PIL: kayit bitince tur sifirlanmiyor (sonraki olcum kaydi 'pil testi' gorunur)",
    dosya: "src/ekran/kabuk_durum.js",
    bul: "      turSorulan = null;\n      oturumTuru.value = null;\n      return;",
    koy: "      return;",
    test: DUGME,
  },
];
