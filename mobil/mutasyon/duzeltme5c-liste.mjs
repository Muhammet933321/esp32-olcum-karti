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
  {
    ad: "5C-D-AD: asil bilinmiyorken de eklentiye 'asil var' deniyor (cozulemeyen olcum.local sonucu bekletir)",
    dosya: "src/cekirdek/ag.js",
    bul: 'asilVar: typeof asil === "string" && asil !== "" && liste[0] === asil',
    koy: "asilVar: true",
    test: DURDUR,
  },
  {
    ad: "5C-D-AD: durdur.js asil adresi ag katmanina vermiyor",
    dosya: "src/cekirdek/durdur.js",
    bul: "soz = p0(hedefler, { asil });",
    koy: "soz = p0(hedefler);",
    test: DURDUR,
  },
  // ── bulgu 2: IP degisimi ─────────────────────────────────────────────────
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
  // ── bulgu 7: grafikte veri yok ───────────────────────────────────────────
  {
    ad: "5C-D7: gerilim okunamazken (adc_hata bit0) deger grafige giriyor",
    dosya: "src/cekirdek/canli.js",
    bul: "const v = (hata & 1) === 0 && Number.isFinite(d.v) ? d.v : NaN;",
    koy: "const v = Number.isFinite(d.v) ? d.v : NaN;",
    test: CANLI,
  },
];
