// Ö6 — grafik ölçümü (tasarim A27): 800 bin noktalik URETILMIS seride betikli 200 yakinlastirma /
// kaydirma karesi; kare suresi ortanca / p95 / en uzun. Olcut: p95 < 33 ms. "Akici gorunuyor" kanit
// degildir: olcum uygulamanin icinde, tekrarlanabilir (seri ve betik BELIRLENIMCI — rastgelelik yok).
//
//   const seri = seriUret(NOKTA);                   // { t, v, i }  Float64Array
//   const kareler = kareBetigi(seri.t[0], seri.t[NOKTA - 1], KARE);
//   const s = await grafikOlc({ grafik, seriler: grafikSerileri(seri), kareler, simdi, kareBekle });
//     -> { nokta, kare, hazirlikMs, cizim: { ortanca, p95, enUzun }, aralik: { ortanca, p95, enUzun }, gecti }
//
// Iki sure olculur ve IKISI de yazilir:
//   cizim  : `grafik.ciz()` cagrisinin suresi (JS + tuval komutlari). Piramit seciminin maliyeti burada.
//   aralik : art arda iki animasyon karesi arasi (ekranin gercekten yenilenme araligi). Ekran 60 Hz ise
//            16.7 ms'nin altina INEMEZ — olcut bu sayiya uygulanir (kullanicinin gordugu budur).
// hazirlikMs: serilerin grafige verilmesi (piramitlerin kurulmasi dahil), bir kez.

export const NOKTA = 800000;
export const KARE = 200;
export const OLCUT_MS = 33;

// Belirlenimci seri: 100 ms arayla nokta; yavas sinus + hizli sinus + LCG gurultusu + seyrek sicramalar
// (tek orneklik sicrama piramidin min / maks'inda kalmali — gercek kayit gibi).
export function seriUret(n = NOKTA) {
  if (!Number.isInteger(n) || n < 2) throw new RangeError("n >= 2 tamsayi olmali");
  const t = new Float64Array(n), v = new Float64Array(n), i = new Float64Array(n);
  let tohum = 12345;
  const gurultu = () => { tohum = (Math.imul(tohum, 1103515245) + 12345) >>> 0; return tohum / 4294967296 - 0.5; };
  for (let k = 0; k < n; k++) {
    t[k] = k * 100;
    v[k] = 12 + 0.8 * Math.sin(k / 9000) + 0.05 * Math.sin(k / 7) + 0.02 * gurultu() + (k % 50021 === 0 ? 1.5 : 0);
    i[k] = 1.5 + 0.5 * Math.sin(k / 4000) + 0.03 * gurultu();
  }
  return { t, v, i };
}

export function grafikSerileri(seri) {
  return [
    { ad: "V", t: seri.t, y: seri.v, birim: "V", renk: "volt", eksen: "sol" },
    { ad: "I", t: seri.t, y: seri.i, birim: "A", renk: "amper", eksen: "sag" },
  ];
}

// Betik: [t0, t1] pencereleri. Dort bolum (esit): tamamdan 1/2000'e YAKINLAS (ustel), dar pencereyle
// saga KAYDIR, orta genislikte sola KAYDIR, yeniden tamama UZAKLAS. Her pencere [bas, son] icinde.
export function kareBetigi(bas, son, adet = KARE) {
  if (!(son > bas) || !Number.isInteger(adet) || adet < 4) throw new RangeError("aralik ve adet gecersiz");
  const tam = son - bas, dar = tam / 2000, orta = tam / 40;
  const ceyrek = Math.floor(adet / 4);
  const kareler = [];
  const ekle = (merkez, gen) => {
    const g = Math.min(tam, Math.max(gen, dar));
    const t0 = Math.min(son - g, Math.max(bas, merkez - g / 2));
    kareler.push([t0, t0 + g]);
  };
  const m0 = bas + tam * 0.37;
  for (let k = 0; k < ceyrek; k++) ekle(m0, tam * Math.pow(dar / tam, k / (ceyrek - 1 || 1)));
  for (let k = 0; k < ceyrek; k++) ekle(m0 + (k + 1) * dar * 0.4, dar);
  for (let k = 0; k < ceyrek; k++) ekle(m0 - (k + 1) * orta * 0.15, orta);
  const kalan = adet - 3 * ceyrek;
  for (let k = 0; k < kalan; k++) ekle(m0, orta * Math.pow(tam / orta, (k + 1) / kalan));
  return kareler;
}

// Sureler -> { ortanca, p95, enUzun } (ms, 0.1 ms'ye yuvarli). Bos dizi: null.
export function ozetle(sureler) {
  const s = sureler.filter((x) => Number.isFinite(x) && x >= 0).sort((a, b) => a - b);
  if (s.length === 0) return null;
  const yuvarla = (x) => Math.round(x * 10) / 10;
  const yuzde = (p) => s[Math.min(s.length - 1, Math.ceil(p * s.length) - 1)];
  return { ortanca: yuvarla(yuzde(0.5)), p95: yuvarla(yuzde(0.95)), enUzun: yuvarla(s[s.length - 1]) };
}

// grafik: ortak Grafik (veriAyarla, durumAyarla, ciz). simdi(): ms (performance.now).
// kareBekle(): bir sonraki animasyon karesine cozulen soz. iptal(): true donerse olcum yarida kesilir (null).
export async function grafikOlc({ grafik, seriler, kareler, simdi, kareBekle, iptal = () => false }) {
  const h0 = simdi();
  grafik.veriAyarla(seriler);
  grafik.ciz();
  const hazirlikMs = simdi() - h0;
  const cizim = [], aralik = [];
  await kareBekle();
  let onceki = simdi();
  for (const [t0, t1] of kareler) {
    if (iptal()) return null;
    grafik.durumAyarla({ t0, t1 });
    const c0 = simdi();
    grafik.ciz();
    cizim.push(simdi() - c0);
    await kareBekle();
    const simdiki = simdi();
    aralik.push(simdiki - onceki);
    onceki = simdiki;
  }
  const c = ozetle(cizim), a = ozetle(aralik);
  return {
    nokta: seriler.length ? seriler[0].t.length : 0, kare: kareler.length, hazirlikMs: Math.round(hazirlikMs),
    cizim: c, aralik: a, gecti: a !== null && a.p95 < OLCUT_MS,
  };
}
