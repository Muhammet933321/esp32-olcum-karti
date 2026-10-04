// akis_ayir.js (5C-1): kartin SSE satirlari -> nesne. Bicimler kartin kaynagindan (olcum-karti-a3.ino):
//   D  "D %.4f %.6f %.5f %.4f %.7f %lu %lu %u %u"   volt amper watt joule wh millis ornek menzil adc_hata
//   G  13 alan (A3-4B ve oncesi) ya da 15 alan (A3-W2: + son_not, mesaj_dusen)
//   K  "K %lu %lu %lu"        GA / GT "… %lu %lu %lu %lu"        GP "GP %u %lu %lu %lu %lu"
import { describe, it, expect } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { ALANLAR, G_ESKI_ALAN, KDR, PLAN, SATIR_AZAMI, satirAyir } from "../src/cekirdek/akis_ayir.js";

const D = "D 12.0345 0.501234 6.03212 123.4567 0.0342935 987654 97 0 0";
const G15 = "G 2 41 120 61300 61276 137 4 0 1850 24100 3 912 0 -3 1";
const G13 = "G 2 41 120 61300 61276 137 4 0 1850 24100 3 912 -2";

describe("satirAyir: D", () => {
  it("dokuz alan adlariyla ve sayi olarak cikar", () => {
    expect(satirAyir(D)).toEqual({
      tur: "D", v: 12.0345, a: 0.501234, w: 6.03212, joule: 123.4567, wh: 0.0342935,
      ms: 987654, ornek: 97, menzil: 0, adcHata: 0,
    });
  });

  it("eksi deger, yuksek menzil ve ADC hata bitleri", () => {
    const d = satirAyir("D -0.0012 -1.250000 0.00150 0.0000 0.0000000 4294967295 1 1 3");
    expect(d).toMatchObject({ tur: "D", v: -0.0012, a: -1.25, ms: 4294967295, menzil: 1, adcHata: 3 });
  });

  it("nan / inf basan kart: deger NaN, satir yine D (grafikte bosluk)", () => {
    const d = satirAyir("D nan -nan inf 1.0000 0.0002778 500 3 0 3");
    expect(d.tur).toBe("D");
    expect(Number.isNaN(d.v) && Number.isNaN(d.a) && Number.isNaN(d.w)).toBe(true);
    expect(d.joule).toBe(1);
  });

  it("bozuk / yarim D satiri 'diger' olur, ATMAZ", () => {
    for (const s of [
      "D", "D 12.0", "D 12.0345 0.501234 6.03212 123.4567 0.0342935 987654 97 0",          // eksik alan
      D + " 7",                                                                            // fazla alan
      "D 12,03 0.5 6.0 1.0 0.1 5 1 0 0", "D 1e3 0.5 6.0 1.0 0.1 5 1 0 0", "D x 0.5 6.0 1.0 0.1 5 1 0 0",
      "D 12.0 0.5 6.0 1.0 0.1 5.5 1 0 0", "D 12.0 0.5 6.0 1.0 0.1 -5 1 0 0",               // ms tamsayi ve >= 0
      "D 12.0 0.5 6.0 1.0 0.1 5 1 2 0", "D 12.0 0.5 6.0 1.0 0.1 5 1 0 4",                  // menzil 0|1, hata 0..3
      "D 12.0 0.5 6.0 1.0 0.1 99999999999 1 0 0",                                          // 11 hane
    ]) {
      expect(satirAyir(s), s).toEqual({ tur: "diger", ham: s });
    }
  });
});

describe("satirAyir: G / GA / GT / GP / K / A", () => {
  it("15 alanli G (yeni firmware)", () => {
    expect(satirAyir(G15)).toEqual({
      tur: "G", durum: 2, oturum: 41, nokta: 120, sonraki: 61300, onay: 61276, doluluk: 137, onaysiz: 4,
      dusen: 0, yaz_azami_us: 1850, sil_azami_us: 24100, sil_adet: 3, tarama_ms: 912, son_hata: 0,
      son_not: -3, mesaj_dusen: 1,
    });
  });

  it("13 alanli G (eski firmware): son iki alan null", () => {
    const g = satirAyir(G13);
    expect(g).toMatchObject({ tur: "G", durum: 2, oturum: 41, son_hata: -2 });
    expect(g.son_not).toBe(null);
    expect(g.mesaj_dusen).toBe(null);
    expect(Object.keys(g)).toEqual(["tur", ...ALANLAR.G]);
  });

  it("14 ya da 16 alanli, kesirli ya da durumu sinir disi G 'diger'", () => {
    for (const s of [G13 + " 0", G15 + " 0", "G 2 41", "G", G15.replace("61300", "613.5"), "G 9 41 120 61300 61276 137 4 0 1850 24100 3 912 0 -3 1",
      "G -1 41 120 61300 61276 137 4 0 1850 24100 3 912 0"]) {
      expect(satirAyir(s).tur, s).toBe("diger");
    }
  });

  it("GA, GT, GP, K", () => {
    expect(satirAyir("GA 480 0 0 2")).toEqual({ tur: "GA", hazir_sektor: 480, ayrintili_ornek: 0, dusen_ornek: 0, kayit_ici_silme: 2 });
    expect(satirAyir("GT 1 5000 12 0")).toEqual({ tur: "GT", etkin: 1, aralik_ms: 5000, yakalama: 12, yazilamayan: 0 });
    expect(satirAyir("GP 2 1790000000 600 1000 44")).toEqual({ tur: "GP", durum: 2, bas_unix: 1790000000, sure_s: 600, hiz_ms: 1000, oturum: 44 });
    expect(satirAyir("K 12 11418 3")).toEqual({ tur: "K", kayip_ms: 12, loop_azami_us: 11418, loop_uzun_adet: 3 });
    for (const s of ["GA 480 0 0", "GT 1 5000 12 0 9", "GP 2 x 600 1000 44", "K 12 11418", "GP 8 1 1 1 1"]) expect(satirAyir(s).tur, s).toBe("diger");
  });

  it("A (ayar) satiri: menzil, oto, rapor araligi", () => {
    const s = "A menzil=YUKSEK oto=1 n_kazanc=1.000000 n_sifir=0 y_kazanc=1.000000 y_sifir=0 sont=0.005000 i_duz=1.000000 i_ofset=0 rapor=200";
    expect(satirAyir(s)).toEqual({ tur: "A", menzil: 1, oto: 1, rapor_ms: 200 });
    expect(satirAyir("A menzil=NORMAL oto=0 rapor=20")).toEqual({ tur: "A", menzil: 0, oto: 0, rapor_ms: 20 });
    expect(satirAyir("A menzil=NORMAL oto=0").tur).toBe("diger");
    expect(satirAyir("A menzil=ORTA oto=0 rapor=20").tur).toBe("diger");
  });

  it("sabitler kartin kaynagiyla ayni", () => {
    expect(KDR).toEqual({ TARIYOR: 0, BOS: 1, KAYIT: 2, DOLU: 3, BEKLIYOR: 4, HATA: 5 });
    expect(PLAN).toEqual({ YOK: 0, BEKLIYOR: 1, SURUYOR: 2, BITTI: 3, ATLANDI: 4, KACIRILDI: 5, SAAT_YOK: 6, BASLATILAMADI: 7 });
    expect(ALANLAR.G.length).toBe(15);
    expect(G_ESKI_ALAN).toBe(13);
  });
});

describe("satirAyir: bilinmeyen ve dusman girdi", () => {
  it("bilinmeyen satir ATILMAZ: { tur: 'diger', ham }", () => {
    for (const s of ["* G plan basladi", "! G: istek kuyrugu dolu", "Olcum Karti — A3-W2", "S2 512 860 0.001 12 1000 0 1", "", "   ", "DD 1 2", "g 1 2"]) {
      expect(satirAyir(s)).toEqual({ tur: "diger", ham: s });
    }
  });

  it("bas ve son bosluk / satir sonu kirpilir; ic bosluk tek ayrac sayilir", () => {
    expect(satirAyir("  " + D + " \r").tur).toBe("D");
    expect(satirAyir("K  12   11418 3").tur).toBe("K");
  });

  it("metin olmayan girdi ve dev satir cokertmez; ham kisaltilir", () => {
    for (const x of [null, undefined, 5, {}, [], Symbol("x")]) expect(satirAyir(x)).toEqual({ tur: "diger", ham: "" });
    const dev = "D " + "9".repeat(100000);
    const s = satirAyir(dev);
    expect(s.tur).toBe("diger");
    expect(s.ham.length).toBe(SATIR_AZAMI);
    // Sinirin hemen ustu: gecerli gorunse de ayristirilmaz.
    const uzun = D + " ".repeat(SATIR_AZAMI);
    expect(satirAyir(uzun).tur).toBe("diger");
  });

  it("nesne prototipinden gelen adlar satir turu sayilmaz", () => {
    for (const s of ["constructor 1 2", "toString", "__proto__ 1", "hasOwnProperty 1 2 3"]) expect(satirAyir(s).tur, s).toBe("diger");
  });
});

// Kartin kaynagi bu calisma agacinda varsa (mutasyon kopyasinda yok): alan SAYILARI snprintf bicimiyle ayni.
const INO = fileURLToPath(new URL("../../kod/olcum-karti-a3/olcum-karti-a3.ino", import.meta.url));
describe.skipIf(!existsSync(INO))("kartin kaynagi ile alan sayilari", () => {
  const kaynak = existsSync(INO) ? readFileSync(INO, "utf8") : "";
  const say = (onek) => {
    const m = new RegExp(`"${onek} (%[^"]*)"`).exec(kaynak);
    return m ? m[1].trim().split(/\s+/).length : -1;
  };
  it("D 9, K 3, GA 4, GT 4, GP 5; G 13 ya da 15", () => {
    expect(say("D")).toBe(9);
    expect(say("K")).toBe(ALANLAR.K.length);
    expect(say("GA")).toBe(ALANLAR.GA.length);
    expect(say("GT")).toBe(ALANLAR.GT.length);
    expect(say("GP")).toBe(ALANLAR.GP.length);
    expect([G_ESKI_ALAN, ALANLAR.G.length]).toContain(say("G"));
  });
});
