// B73 / 2F — ortak/src/rapor.js: oturum raporunun icerigi. Beklenenler bu dosyada src'den
// BAGIMSIZ duz donguyle (kaba kuvvet) hesaplanir: noktalar kayit.js volt/amper ile cevrilir,
// enerji parca basina saat cinsinden duz toplanir (src ms toplayip sonda boler).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as K from "../src/kayit.js";
import { oturumRaporu, RAPOR_ETIKET, ALAN_ETIKET } from "../src/rapor.js";
import { ceviri, SOZLUK } from "../src/sozluk.js";

const V = JSON.parse(readFileSync(new URL("./vektor/disari.json", import.meta.url), "utf8"));
const hexten = (s) => Uint8Array.from(s.match(/../g) ?? [], (h) => parseInt(h, 16));
const birlestir = (...p) => {
  const b = new Uint8Array(p.reduce((a, x) => a + x.length, 0));
  let a = 0;
  for (const x of p) { b.set(x, a); a += x.length; }
  return b;
};
const u32 = (...xs) => {
  const b = new Uint8Array(4 * xs.length);
  const v = new DataView(b.buffer);
  xs.forEach((x, i) => v.setUint32(4 * i, x, true));
  return b;
};
const bitirYuk = (n, s) => { const b = new Uint8Array(8); new DataView(b.buffer).setUint32(0, n, true); b[4] = s; return b; };
const utf8 = (s) => new TextEncoder().encode(s);
const yakin = (a, b, ne) => assert.ok(Math.abs(a - b) <= 1e-12 * Math.max(1, Math.abs(b)), `${ne}: ${a} != ${b}`);

class Akis {
  constructor(sira = 0) { this.sira = sira; this.parca = []; }
  ekle(tur, oturum, yuk) { this.sira += 1; this.parca.push(K.kayitPaketle(tur, this.sira, oturum, yuk)); return this.sira; }
  bayt() { return birlestir(...this.parca); }
}

const KAL = {
  normal: { n: 1, pga: 4096, kazanc: 1, sifir_ham: 3, tau: 0 },
  yuksek: { n: 2, pga: 4096, kazanc: 1, sifir_ham: -2, tau: 0 },
  i_ofset: 1, i_pga: 32, sont_ohm: 1, i_duzeltme: 1, sebeke_hz: 50, faz_kal_us: [0, 0],
};
const BASLA = (tur, hiz, unix, kart, acilis, kalNo = 2) => K.baslaPaketle({ oturum_turu: tur, kal_bicim: 1,
  hiz_ms: hiz, unix_s: unix, kart_ms: kart, acilis, surum: "A3-2F", kal: KAL, kal_no: kalNo });
const P = (ms, o = {}) => ({ kart_ms: ms, n: 10, bayrak: 0, v_ort_kod: 100.5, v_min_kod: 99, v_maks_kod: 102,
  i_ort_kod: 800.25, i_min_kod: 790, i_maks_kod: 810, w_ort: 1.5, w_min: 1.25, w_maks: 1.75, ...o });

function kur(a, id) {
  const kay = K.akisCoz(a.bayt());
  return [K.oturumlariKur(kay).get(id), kay];
}

/** Sicramali, ic boslukli, DEVAM'li olcum oturumu. */
function sicramaOturumu({ bitir = true } = {}) {
  const a = new Akis(70);
  const id = a.ekle(K.T_BASLA, 71, BASLA(K.OTURUM_OLCUM, 1000, 1790000000, 20000, 5));
  const ms = [21000, 22000, 23000, 24000, 25000, 30000, 31000, 32000, 33000, 34000];   // 25000->30000: bosluk
  const ns = ms.map((m, k) => P(m, {
    v_ort_kod: 100 + k * 3.25, i_ort_kod: 700 + k * 11.5, w_ort: 1 + k / 4,
    ...(k === 3 ? { v_min_kod: -800, i_maks_kod: 4000, w_min: -7.5 } : {}),     // tek orneklik sicramalar
    ...(k === 6 ? { v_maks_kod: 2000, i_min_kod: -3000, w_maks: 99.25 } : {}),
    ...(k === 4 ? { bayrak: K.KN_KAYIP_ONCE } : {}),
    ...(k === 5 ? { bayrak: K.KN_DURAKLAMA | K.KN_YUKSEK } : {}),
    ...(k === 8 ? { n: 0, bayrak: K.KN_V_HATA | K.KN_I_HATA } : {}),
  }));
  a.ekle(K.T_NOKTA, id, birlestir(u32(0), ...ns.slice(0, 6).map(K.noktaPaketle)));
  a.ekle(K.T_NOKTA, id, birlestir(u32(6), ...ns.slice(6).map(K.noktaPaketle)));
  a.ekle(K.T_DEVAM, id, u32(6, 1790000040, 3000, 10));
  const ns2 = [4000, 5000, 6000, 7000].map((m, k) => P(m, { v_ort_kod: 50 + k, w_ort: 2 + k }));
  a.ekle(K.T_NOKTA, id, birlestir(u32(10), ...ns2.map(K.noktaPaketle)));
  a.ekle(K.T_NOT, 0, K.notPaketle(id, K.KNT_AD, 0, 0, utf8("Sıçrama denemesi")));
  a.ekle(K.T_NOT, 0, K.notPaketle(id, K.KNT_ETIKET, 0, 0, utf8("test, sıçrama")));
  a.ekle(K.T_NOT, 0, K.notPaketle(id, K.KNT_NOT, 0, 0, utf8("genel not")));
  a.ekle(K.T_NOT, 0, K.notPaketle(id, K.KNT_NOT, 23000, 0, utf8("kayda değer an")));
  if (bitir) a.ekle(K.T_BITIR, id, bitirYuk(16, 1));
  return kur(a, id);
}

/** Kaba kuvvet: noktalarin fiziksel degerleri, acilis ve gecen zamani (src'siz). */
function kabaNoktalar(o) {
  const kal = o.basla.kal;
  const dv = o.devamlar.map((d) => d.nokta_sira).sort((x, y) => x - y);
  const capa = [{ kart: o.basla.kart_ms, ofset: 0 },
    ...o.devamlar.map((d) => ({ kart: d.kart_ms, ofset: (d.unix_s - o.basla.unix_s) * 1000 }))];
  return [...o.noktalar].sort((x, y) => x[0] - y[0]).map(([s, p]) => {
    const ac = dv.filter((d) => d <= s).length;
    const kn = p.bayrak & K.KN_YUKSEK ? kal.yuksek : kal.normal;
    const bos = p.n === 0;
    return {
      s, ac, rel: p.kart_ms - capa[ac].kart, gecen: capa[ac].ofset + p.kart_ms - capa[ac].kart,
      v: bos ? NaN : K.volt(p.v_ort_kod, kn, false), vmin: bos ? NaN : K.volt(p.v_min_kod, kn, true),
      vmaks: bos ? NaN : K.volt(p.v_maks_kod, kn, true), i: bos ? NaN : K.amper(p.i_ort_kod, kal, false),
      imin: bos ? NaN : K.amper(p.i_min_kod, kal, true), imaks: bos ? NaN : K.amper(p.i_maks_kod, kal, true),
      w: bos ? NaN : p.w_ort, wmin: bos ? NaN : p.w_min, wmaks: bos ? NaN : p.w_maks,
    };
  });
}

function kabaEnerji(nk, bosluk, deger) {
  let top = 0;
  let once = null;
  for (const p of nk) {
    const x = deger(p);
    if (Number.isNaN(x)) continue;
    if (once && once.ac === p.ac && p.rel - once.rel <= bosluk) top += (once.x + x) / 2 * (p.rel - once.rel) / 3_600_000;
    once = { ac: p.ac, rel: p.rel, x };
  }
  return top;
}

// ── istatistik: ham veriden, sicramalar gorunur ──────────────────────
test("istatistik HAM noktalardan: min = noktalarin min'leri, maks = maks'lari (tek orneklik sicrama gorunur)", () => {
  const [o] = sicramaOturumu();
  const r = oturumRaporu(o);
  const nk = kabaNoktalar(o);
  const gecerli = nk.filter((p) => !Number.isNaN(p.v));
  for (const [k, ort, mn, mx] of [["v", "v", "vmin", "vmaks"], ["i", "i", "imin", "imaks"], ["w", "w", "wmin", "wmaks"]]) {
    const s = r.istatistik[k];
    const min = Math.min(...gecerli.map((p) => p[mn]));
    const maks = Math.max(...gecerli.map((p) => p[mx]));
    const ortalama = gecerli.reduce((a, p) => a + p[ort], 0) / gecerli.length;
    const rms = Math.sqrt(gecerli.reduce((a, p) => a + p[ort] ** 2, 0) / gecerli.length);
    assert.equal(s.adet, gecerli.length, k);
    assert.equal(s.min, min, `${k} min`);
    assert.equal(s.maks, maks, `${k} maks`);
    yakin(s.ort, ortalama, `${k} ort`);
    yakin(s.rms, rms, `${k} rms`);
    assert.equal(s.tepeTepe, maks - min, `${k} tepeTepe`);
    assert.equal(s.minSira, gecerli.find((p) => p[mn] === min).s, `${k} minSira`);
    assert.equal(s.maksSira, gecerli.find((p) => p[mx] === maks).s, `${k} maksSira`);
    assert.equal(s.minGecenMs, gecerli.find((p) => p[mn] === min).gecen);
    // sicrama ortalamalarin araliginin DISINDA: ozet (ortalama) kullanilsa gorunmezdi
    assert.ok(min < Math.min(...gecerli.map((p) => p[ort])) && maks > Math.max(...gecerli.map((p) => p[ort])), k);
  }
  assert.equal(r.istatistik.v.min, (-800 - 3) / 8);
  assert.equal(r.istatistik.w.maks, 99.25);
});

test("enerji: yamuk, bosluk (> hiz x 2.5) ve DEVAM siniri HARIC; mAh = ∫A, Wh = ∫W (kartin W'si)", () => {
  const [o] = sicramaOturumu();
  const r = oturumRaporu(o);
  const nk = kabaNoktalar(o);
  const wh = kabaEnerji(nk, 2500, (p) => p.w);
  const mah = kabaEnerji(nk, 2500, (p) => (Number.isNaN(p.v) ? NaN : p.i)) * 1000;
  yakin(r.enerji.wh, wh, "wh");
  yakin(r.enerji.mah, mah, "mah");
  // bosluk dahil edilseydi farkli olurdu (testin kendisi isiriyor mu)
  const hepsi = kabaEnerji(nk.map((p) => ({ ...p, ac: 0, rel: p.gecen })), Infinity, (p) => p.w);
  assert.ok(Math.abs(hepsi - wh) > 1e-3, "bosluklu ve bosluksuz enerji ayni: test bos");
  // olculen sure (W gecerli, bosluk degil): acilis 0'da 21-25 s (4000) + 30-32 s (2000) +
  // 32->34 s (n=0 nokta atlanir, dt 2000 <= 2500: 2000); acilis 1'de 3 x 1000 -> 11000 ms
  assert.equal(r.zaman.olculenMs, 11000);
});

test("sure ve bosluk: toplam (bosluklar dahil), bosluk adedi/suresi, baslangic/bitis unix + ISO", () => {
  const [o] = sicramaOturumu();
  const r = oturumRaporu(o);
  assert.deepEqual(r.zaman.baslangic, { unixS: 1790000000, iso: "2026-09-21T14:13:20.000Z" });
  // son nokta: DEVAM (unix +40 s, kart 3000) -> 7000: 40000 + 4000
  assert.equal(r.zaman.toplamMs, 44000);
  assert.deepEqual(r.zaman.bitis, { acilis: 1, gecenMs: 44000, unixS: 1790000044, iso: "2026-09-21T14:14:04.000Z" });
  // ic bosluk 25000 -> 30000 (5000) + DEVAM gecisi 14000 -> 41000 (27000)
  assert.equal(r.zaman.boslukAdet, 2);
  assert.equal(r.zaman.boslukMs, 5000 + 27000);
});

test("kimlik, notlar, sayaclar, bitis sebebi (sozlukten, TR/EN), uyarilar", () => {
  const [o] = sicramaOturumu();
  const r = oturumRaporu(o);
  assert.equal(r.kimlik.oturumNo, o.id);
  assert.deepEqual(r.kimlik.tur, { kod: 1, metin: ceviri("oturum.tur.1", "tr") });
  assert.equal(r.kimlik.ad, "Sıçrama denemesi");
  assert.deepEqual(r.kimlik.etiketler, ["test", "sıçrama"]);
  assert.equal(r.kimlik.hizMs, 1000);
  assert.equal(r.kimlik.firmware, "A3-2F");
  assert.deepEqual(r.notlar.map((n) => [n.metin, n.genel, n.gecenMs]), [["genel not", true, null], ["kayda değer an", false, 3000]]);
  assert.deepEqual(r.sayac, { nokta: 14, ayrintiOrnek: 0, devam: 1, olay: 0, not: 2, skopAdet: 0 });
  assert.deepEqual(r.bitis, { sebep: { kod: 1, metin: "kullanıcı durdurdu" }, noktaAdedi: 16 });
  assert.equal(oturumRaporu(o, { dil: "en" }).bitis.sebep.metin, "stopped by user");
  const u = Object.fromEntries(r.uyarilar.map((x) => [x.kod, x.sayi]));
  assert.deepEqual(u, { kayip_once: 1, duraklama: 1, bos_nokta: 1, v_hata: 1, i_hata: 1, devam: 1, nokta_eksik: 2 });
  for (const x of r.uyarilar) {
    assert.equal(x.metin, ceviri(`uyari.${x.kod}`, "tr", { sayi: x.sayi }));
    assert.ok(!x.metin.includes("{sayi}"));
  }
});

test("acik oturum (BITIR yok): sebep yok + 'acik' uyarisi", () => {
  const [o] = sicramaOturumu({ bitir: false });
  const r = oturumRaporu(o);
  assert.deepEqual(r.bitis, { sebep: { kod: null, metin: ceviri("sebep.acik", "tr") }, noktaAdedi: null });
  assert.ok(r.uyarilar.some((x) => x.kod === "acik"));
  assert.ok(!r.uyarilar.some((x) => x.kod === "nokta_eksik"), "BITIR yoksa beklenen = en buyuk sira + 1");
});

test("bilinmeyen sebep kodu: ceviriKod 'bilinmeyen' + kod", () => {
  const a = new Akis(0);
  const id = a.ekle(K.T_BASLA, 1, BASLA(9, 1000, 0, 0, 1));
  a.ekle(K.T_BITIR, id, bitirYuk(0, 42));
  const [o] = kur(a, id);
  const r = oturumRaporu(o, { dil: "en" });
  assert.equal(r.bitis.sebep.metin, "unknown reason (42)");
  assert.equal(r.kimlik.tur.metin, "Unknown session type (9)");
});

// ── pil ──────────────────────────────────────────────────────────────
function pilOturumu() {
  const a = new Akis(200);
  const id = a.ekle(K.T_BASLA, 201, BASLA(K.OTURUM_PIL, 500, 1790500000, 90000, 12, 3));
  a.ekle(K.T_OLAY, id, K.olayPaketle({ tur: K.KO_PIL_AYAR, kart_ms: 90001, kesme_v: 3, ocv: 4.125, azami_s: 36000,
    dcir_aralik_ms: 3000, dcir_ms: 200, kayit_hz: 2 }));
  a.ekle(K.T_NOKTA, id, birlestir(u32(0), ...[90500, 91000, 91500, 92000].map((m) => K.noktaPaketle(P(m)))));
  const dc = (no, ms) => K.olayPaketle({ tur: K.KO_DCIR, kart_ms: ms, no, v_once: 4, i_once: 1, v_ani: 3.875,
    v_oturmus: 3.75, r_ani: 0.125, r_oturmus: 0.25, mah: no * 10, wh: no / 8 });
  a.ekle(K.T_OLAY, id, dc(1, 91200));
  a.ekle(K.T_NOKTA, id, birlestir(u32(4), ...[92500, 93000].map((m) => K.noktaPaketle(P(m)))));
  a.ekle(K.T_OLAY, id, dc(2, 92800));
  a.ekle(K.T_OLAY, id, K.olayPaketle({ tur: K.KO_PIL_SONUC, kart_ms: 93003, durum: 2, hata: 0, mah: 12.5, wh: 0.0625,
    ocv: 4.125, v_son: 3, sure_ms: 3003, dcir_sayisi: 2 }));
  a.ekle(K.T_BITIR, id, bitirYuk(6, 4));
  return kur(a, id);
}

test("pil: ayar + sonuc (durum/hata metni sozlukten) + DCIR listesi + olaylar kayit sirasiyla", () => {
  const [o] = pilOturumu();
  const r = oturumRaporu(o);
  assert.deepEqual(r.pil.ayar, { kesme_v: 3, ocv: 4.125, azami_s: 36000, dcir_aralik_ms: 3000, dcir_ms: 200, kayit_hz: 2 });
  assert.equal(r.pil.sonuc.durum, 2);
  assert.equal(r.pil.sonuc.durumMetin, ceviri("pil.durum.2", "tr"));
  assert.equal(r.pil.sonuc.hataMetin, ceviri("pil.hata.0", "tr"));
  assert.equal(r.pil.sonuc.mah, 12.5);
  assert.deepEqual(r.pil.dcir.map((d) => [d.no, d.r_ani, d.mah, d.gecenMs]), [[1, 0.125, 10, 1200], [2, 0.125, 20, 2800]]);
  assert.deepEqual(r.olaylar.map((x) => x.tur.kod), [1, 2, 2, 3]);
  assert.deepEqual(r.olaylar.map((x) => x.tur.metin), [1, 2, 2, 3].map((k) => ceviri(`olay.${k}`, "tr")));
  assert.ok(r.olaylar.every((x, k, d) => k === 0 || d[k - 1].sira < x.sira));
  assert.equal(r.olaylar[3].gecenMs, 3003);
  assert.equal(r.olaylar[3].iso, "2026-09-27T09:06:43.003Z");   // Python: fromtimestamp(1790500003.003, utc)
  assert.deepEqual(r.bitis.sebep, { kod: 4, metin: "pil testi bitti" });
  assert.equal(oturumRaporu(o, { dil: "en" }).pil.sonuc.durumMetin, "finished (cut-off voltage reached)");
});

// ── kalibrasyon ──────────────────────────────────────────────────────
const kalKaydi = (no, degis = {}) => ({ no, unix: 1789000000, acilis: 3, tur: 2, kaynak: 0, not: "ince",
  kal: { normal: { n: 1, pga: 4096, kazanc: 1, sifir_ham: 0, tau: 0 }, yuksek: { n: 2, pga: 4096, kazanc: 1, sifir_ham: 0, tau: 0 },
    i_ofset: 0, i_pga: 32, sont_ohm: 1, i_duzeltme: 1, sebeke_hz: 50, faz0: 0, faz1: 0, ...degis } });

test("kalibrasyon: kal_no gecmiste aranir; sifir ofsetleri HARIC karsilastirilir; durumlar", () => {
  const [o] = sicramaOturumu();
  const gecmis = { surum: 1, adet: 3, kayitlar: [kalKaydi(1, { sont_ohm: 0.005 }), kalKaydi(2), { no: 3, bozuk: true }] };
  const r = oturumRaporu(o, { kalibrasyonGecmisi: gecmis });
  assert.equal(r.kalibrasyon.kalNo, 2);
  assert.equal(r.kalibrasyon.durum.kod, "bulundu");
  assert.equal(r.kalibrasyon.kayit.turMetin, ceviri("kal.tur.2", "tr"));
  assert.equal(r.kalibrasyon.kayit.kaynakMetin, ceviri("kal.kaynak.0", "tr"));
  assert.deepEqual(r.kalibrasyon.kopya.normal, KAL.normal);
  assert.ok(!r.uyarilar.some((x) => x.kod === "kal_farkli"), "yalniz sifirlar farkli: AYNI sayilmali");
  const farkli = { kayitlar: [kalKaydi(2, { i_duzeltme: 1.0625 })] };
  const rf = oturumRaporu(o, { kalibrasyonGecmisi: farkli });
  assert.deepEqual(rf.uyarilar.find((x) => x.kod === "kal_farkli").metin,
    ceviri("uyari.kal_farkli", "tr", { no: 2 }));
  assert.equal(oturumRaporu(o, { kalibrasyonGecmisi: { kayitlar: [kalKaydi(7)] } }).kalibrasyon.durum.kod, "yok");
  assert.equal(oturumRaporu(o, { kalibrasyonGecmisi: { kayitlar: [{ no: 2, bozuk: true }] } }).kalibrasyon.durum.kod, "bozuk");
  assert.equal(oturumRaporu(o).kalibrasyon.durum.kod, "gecmis_yok");
  const [p] = pilOturumu();
  assert.equal(oturumRaporu(p, { kalibrasyonGecmisi: gecmis }).kalibrasyon.durum.kod, "bozuk", "kal_no 3 = bozuk kayit");
  const a = new Akis(0);
  const id = a.ekle(K.T_BASLA, 1, BASLA(1, 1000, 0, 0, 1, 0));
  const [z] = kur(a, id);
  assert.equal(oturumRaporu(z, { kalibrasyonGecmisi: gecmis }).kalibrasyon.durum.kod, "numarasiz");
});

test("basliksiz oturum (BASLA/TEKRAR yok): V/A yok, W var, 'baslik_yok', kalibrasyon kopya_yok", () => {
  const a = new Akis(0);
  a.ekle(K.T_NOKTA, 77, birlestir(u32(0), ...[1000, 2000, 3000].map((m) => K.noktaPaketle(P(m)))));
  const [o] = kur(a, 77);
  const r = oturumRaporu(o);
  assert.equal(r.istatistik.v.adet, 0);
  assert.equal(r.istatistik.v.min, null);
  assert.equal(r.istatistik.w.adet, 3);
  assert.equal(r.kalibrasyon.durum.kod, "kopya_yok");
  assert.ok(r.uyarilar.some((x) => x.kod === "baslik_yok"));
  assert.equal(r.kimlik.tur.kod, null);
  assert.deepEqual(r.zaman.bitis.gecenMs, 2000, "BASLA yoksa capa ilk nokta");
});

// ── olay zamani: DEVAM + kayitlar ────────────────────────────────────
test("DEVAM'li oturumda olay acilisi: kayitlar verilirse kesin, verilmezse belirsiz + uyari", () => {
  const a = new Akis(0);
  const id = a.ekle(K.T_BASLA, 1, BASLA(1, 1000, 1790000000, 1000, 3));
  a.ekle(K.T_OLAY, id, K.olayPaketle({ tur: K.KO_PLAN, kart_ms: 1001, bas_unix: 1790000000, sure_s: 60, hiz_ms: 1000, plan_no: 4 }));
  a.ekle(K.T_NOKTA, id, birlestir(u32(0), ...[2000, 3000, 4000, 5000].map((m) => K.noktaPaketle(P(m)))));
  a.ekle(K.T_DEVAM, id, u32(4, 1790000010, 1500, 4));
  a.ekle(K.T_NOKTA, id, birlestir(u32(4), ...[2500, 3500, 4500].map((m) => K.noktaPaketle(P(m)))));
  a.ekle(K.T_OLAY, id, K.olayPaketle({ tur: K.KO_SKOP_KAL, kart_ms: 3000, mv: Array.from({ length: 17 }, (_, k) => k * 200) }));
  const [o, kay] = kur(a, id);
  const kesin = oturumRaporu(o, { kayitlar: kay });
  assert.deepEqual(kesin.olaylar.map((x) => [x.acilis, x.gecenMs]), [[0, 1], [1, 11500]]);
  assert.deepEqual(kesin.olaylar[1].alanlar.mv, Array.from({ length: 17 }, (_, k) => k * 200));
  assert.ok(!kesin.uyarilar.some((x) => x.kod === "zaman_belirsiz"));
  const sezgi = oturumRaporu(o);
  assert.deepEqual(sezgi.olaylar.map((x) => [x.acilis, x.gecenMs]), [[0, 1], [null, null]]);
  assert.equal(sezgi.uyarilar.find((x) => x.kod === "zaman_belirsiz").sayi, 1);
  assert.equal(sezgi.olaylar[0].tur.metin, ceviri("olay.5", "tr"));
});

// ── ayrintili ────────────────────────────────────────────────────────
test("ayrintili oturum: istatistik ve enerji ORNEKLERDEN; bosluk > 16.38 ms ve DEVAM haric; KA uyarilari", () => {
  const v = V.ayrinti[0];
  const kay = K.akisCoz(hexten(v.veri));
  const o = K.oturumlariKur(kay).get(v.oturum);
  const r = oturumRaporu(o);
  assert.equal(r.kimlik.ayrintili, true);
  const kal = o.basla.kal;
  const dv = o.devamlar.map((d) => d.nokta_sira);
  const capa = [o.basla.kart_ms, ...o.devamlar.map((d) => d.kart_ms)];
  const orn = K.ayrintiOrnekler(o).map(([s, us, vk, ik, b, ac]) => ({
    s, ac, t: us / 1000 - capa[ac],
    v: b & K.KAO_V_HATA ? NaN : K.volt(vk, b & K.KAO_YUKSEK ? kal.yuksek : kal.normal, true),
    i: b & K.KAO_I_HATA ? NaN : K.amper(ik, kal, true), b,
  }));
  assert.equal(r.sayac.ayrintiOrnek, orn.length);
  const gv = orn.filter((x) => !Number.isNaN(x.v));
  assert.equal(r.istatistik.v.min, Math.min(...gv.map((x) => x.v)));
  assert.equal(r.istatistik.v.maks, Math.max(...gv.map((x) => x.v)));
  assert.equal(r.istatistik.v.adet, gv.length);
  let wh = 0;
  let mah = 0;
  let once = null;
  for (const x of orn) {
    if (Number.isNaN(x.v) || Number.isNaN(x.i)) continue;
    if (once && once.ac === x.ac && x.t - once.t <= 16.38) {
      wh += (once.v * once.i + x.v * x.i) / 2 * (x.t - once.t) / 3_600_000;
      mah += (once.i + x.i) / 2 * (x.t - once.t) / 3_600;
    }
    once = x;
  }
  yakin(r.enerji.wh, wh, "wh");
  yakin(r.enerji.mah, mah, "mah");
  const u = Object.fromEntries(r.uyarilar.map((x) => [x.kod, x.sayi]));
  assert.equal(u.silme, 1);
  assert.equal(u.kayip_once, 1);
  assert.equal(u.v_hata, orn.filter((x) => x.b & K.KAO_V_HATA).length);
  assert.equal(r.zaman.boslukAdet, 3, "iki ic bosluk (silme, kayip) + DEVAM");
  assert.ok(dv.length === 1);
});

// ── skop ─────────────────────────────────────────────────────────────
test("skop oturumu: yakalama sayilari, eksik uyarisi, bitis = son yakalamanin sonu", () => {
  const a = new Akis(500);
  const id = a.ekle(K.T_BASLA, 501, BASLA(K.OTURUM_SKOP, 0, 1790000000, 1000, 4));
  const meta = { t_ms: 1500, sure_ms: 40, hz: 50000, tdiv_us: 100, adim: 0.5, ofset: 1, tetik: 1, esik: 2048,
    histerezis: 40, kip: 0, tetiklendi: 1, kenar: 0, on_yuzde: 25, onay: 2 };
  a.ekle(K.T_SKOP, id, K.skopPaketle({ no: 1, ilk: 0, toplam: 2, parca: 0, meta, kodlar: [1, 2] }));
  a.ekle(K.T_SKOP, id, K.skopPaketle({ no: 2, ilk: 0, toplam: 4, parca: 0, meta: { ...meta, t_ms: 2500 }, kodlar: [1, 2] }));
  a.ekle(K.T_BITIR, id, bitirYuk(0, 1));
  const [o] = kur(a, id);
  const r = oturumRaporu(o);
  assert.deepEqual([r.skop.adet, r.skop.tam, r.skop.eksik], [2, 1, 1]);
  assert.deepEqual(r.skop.yakalamalar.map((y) => [y.no, y.tam, y.gecenMs, y.hz]), [[1, true, 500, 50000], [2, false, 1500, 50000]]);
  assert.equal(r.uyarilar.find((x) => x.kod === "skop_eksik").sayi, 1);
  assert.equal(r.zaman.toplamMs, 1540);
  assert.equal(r.kimlik.tur.metin, ceviri("oturum.tur.3", "tr"));
});

// ── bicim ────────────────────────────────────────────────────────────
test("rapor duz JSON: gidis-donus ayni (Map / tipli dizi / NaN / undefined yok)", () => {
  const oturumlar = [sicramaOturumu()[0], sicramaOturumu({ bitir: false })[0], pilOturumu()[0]];
  for (const v of [...V.olcum, ...V.pil, ...V.ayrinti]) {
    oturumlar.push(K.oturumlariKur(K.akisCoz(hexten(v.veri))).get(v.oturum));
  }
  const sade = (x) => {
    if (x === undefined) throw new Error("undefined alan");
    if (typeof x === "number") assert.ok(Number.isFinite(x), "sonlu olmayan sayi");
    if (Array.isArray(x)) x.forEach(sade);
    else if (x && typeof x === "object") {
      assert.equal(Object.getPrototypeOf(x), Object.prototype, "duz nesne degil");
      Object.values(x).forEach(sade);
    }
  };
  for (const o of oturumlar) {
    for (const dil of ["tr", "en"]) {
      const r = oturumRaporu(o, { dil });
      sade(r);
      assert.deepEqual(JSON.parse(JSON.stringify(r)), r);
    }
  }
});

test("RAPOR_ETIKET / ALAN_ETIKET: her etiket sozlukte; raporun ust alanlari etiketli", () => {
  for (const a of [...Object.values(RAPOR_ETIKET), ...Object.values(ALAN_ETIKET)]) assert.ok(a in SOZLUK, a);
  const r = oturumRaporu(pilOturumu()[0]);
  for (const alan of ["kimlik", "notlar", "zaman", "sayac", "istatistik", "enerji", "pil", "kalibrasyon", "olaylar", "skop", "uyarilar"]) {
    assert.ok(alan in r && alan in RAPOR_ETIKET, alan);
  }
  for (const alan of [...Object.keys(r.pil.ayar), ...Object.keys(r.pil.dcir[0]).filter((x) => x in ALAN_ETIKET)]) {
    assert.ok(alan in ALAN_ETIKET, alan);
  }
  for (const k of ["v", "i", "w"]) for (const a of Object.keys(r.istatistik[k])) assert.ok(a in RAPOR_ETIKET, a);
});
