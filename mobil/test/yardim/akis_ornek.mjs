// Sinama akisi kurucusu: ortak/src/kayit.js paketleyicileriyle GERCEK bicimde kayit akisi.
// Kalibrasyon ikili kesir secildi (ortak/test/disari.test.js ile ayni): volt = kod / 8, amper = kod / 1024
// — beklenen degerler elle hesaplanabilir.
import * as K from "../../../ortak/src/kayit.js";

export const KAL = {
  normal: { n: 1, pga: 4096, kazanc: 1, sifir_ham: 0, tau: 0 },
  yuksek: { n: 2, pga: 4096, kazanc: 1, sifir_ham: 0, tau: 0 },
  i_ofset: 0, i_pga: 32, sont_ohm: 1, i_duzeltme: 1, sebeke_hz: 50, faz_kal_us: [0, 0],
};

const utf8 = (s) => new TextEncoder().encode(s);
const u32 = (x) => { const b = new Uint8Array(4); new DataView(b.buffer).setUint32(0, x, true); return b; };
const birlestir = (...p) => {
  const b = new Uint8Array(p.reduce((a, x) => a + x.length, 0));
  let a = 0;
  for (const x of p) { b.set(x, a); a += x.length; }
  return b;
};

export const nokta = (ms, vKod, iKod, w) => K.noktaPaketle({
  kart_ms: ms, n: 10, bayrak: 0, v_ort_kod: vKod, v_min_kod: vKod - 8, v_maks_kod: vKod + 8,
  i_ort_kod: iKod, i_min_kod: iKod - 16, i_maks_kod: iKod + 16, w_ort: w, w_min: w / 2, w_maks: w * 2,
});

export class Akis {
  constructor(sira = 0) { this.sira = sira; this.parca = []; }
  ekle(tur, oturum, yuk) { this.sira += 1; this.parca.push(K.kayitPaketle(tur, this.sira, oturum, yuk)); return this.sira; }
  bayt() { return birlestir(...this.parca); }

  // Oturum acar; donus: oturum numarasi (= BASLA kaydinin sirasi).
  basla({ tur = K.OTURUM_OLCUM, hizMs = 1000, unix = 1790000000, kartMs = 5000, acilis = 3 } = {}) {
    const id = this.sira + 1;
    this.ekle(K.T_BASLA, id, K.baslaPaketle({ oturum_turu: tur, kal_bicim: 1, hiz_ms: hizMs, unix_s: unix, kart_ms: kartMs, acilis, surum: "A3-test", kal: KAL, kal_no: 2 }));
    return id;
  }

  // `adet` nokta, `hizMs` arayla; volt = v0 + k * dv, amper sabit. Her NOKTA kaydinda en cok 20 nokta.
  noktalar(id, { ilk = 0, adet, kartMs = 6000, hizMs = 1000, v0 = 10, dv = 0, amper = 0.5 }) {
    for (let a = 0; a < adet; a += 20) {
      const p = [u32(ilk + a)];
      for (let j = a; j < Math.min(adet, a + 20); j++) {
        const v = v0 + j * dv;
        p.push(nokta(kartMs + j * hizMs, v * 8, amper * 1024, v * amper));
      }
      this.ekle(K.T_NOKTA, id, birlestir(...p));
    }
  }

  ad(id, metin) { this.ekle(K.T_NOT, 0, K.notPaketle(id, K.KNT_AD, 0, 0, utf8(metin))); }
  etiket(id, metin) { this.ekle(K.T_NOT, 0, K.notPaketle(id, K.KNT_ETIKET, 0, 0, utf8(metin))); }
  not(id, metin, ms = 0) { this.ekle(K.T_NOT, 0, K.notPaketle(id, K.KNT_NOT, ms, 0, utf8(metin))); }

  bitir(id, noktaAdedi, sebep = 1) {
    const b = new Uint8Array(8);
    new DataView(b.buffer).setUint32(0, noktaAdedi, true);
    b[4] = sebep;
    this.ekle(K.T_BITIR, id, b);
  }
}

// Iki oturumlu ornek: A = bitmis olcum ("Aku sarj", 60 nokta, 10.0 -> 17.375 V (adim 0.125 V: kodlar TAMSAYI), 0.5 A),
// B = acik olcum (5 nokta, 12 V sabit, 0.25 A). Donus: { bayt, a, b }.
export function ikiOturum() {
  const akis = new Akis(100);
  const a = akis.basla({ unix: 1790000000 });
  akis.noktalar(a, { adet: 60, v0: 10, dv: 0.125, amper: 0.5 });
  akis.ad(a, "Akü şarj");
  akis.etiket(a, "akü,deneme");
  akis.not(a, "yük bağlandı", 6000 + 10000);
  akis.bitir(a, 60);
  const b = akis.basla({ unix: 1790003600, kartMs: 900000, acilis: 3 });
  akis.noktalar(b, { adet: 5, kartMs: 901000, v0: 12, dv: 0, amper: 0.25 });
  return { bayt: akis.bayt(), a, b };
}
