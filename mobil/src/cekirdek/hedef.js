// Kart adresi kurali (A3, A5, S5): uygulama YALNIZ ozel (RFC 1918) ve baglanti-yerel IPv4 adreslerine
// ve `olcum.local` adina gider. Herkese acik IP, baska ad, IPv6, tuhaf IP yazimlari REDDEDILIR.
// Kotlin ikizi: android/.../ag/Hedef.kt — ikisi test/vektor/hedef.tsv'yi gecer. Asil kapi Kotlin'dedir
// (aga cikan tek kod KartAg); buradaki, istegi hic kurmadan kullaniciya dogru hatayi soylemek icin.

export const KART_ADI = "olcum.local";
export const VARSAYILAN_PORT = 80;

export class HedefHatasi extends Error {
  constructor(tur) {
    super(tur);
    this.name = "HedefHatasi";
    this.tur = tur;            // "bicim" | "ozel-degil" | "ad-izinsiz"
  }
}

// Yalniz kati noktali-onluk: dort parca, ASCII rakam, bas sifir yok, 0..255.
function sekizliler(ip) {
  if (typeof ip !== "string") return null;
  const p = ip.split(".");
  if (p.length !== 4) return null;
  const s = [];
  for (const x of p) {
    if (!/^(0|[1-9][0-9]{0,2})$/.test(x) || x.length > 3) return null;
    const n = Number(x);
    if (n > 255) return null;
    s.push(n);
  }
  return s;
}

export function ozelAdres(ip) {
  const s = sekizliler(ip);
  if (!s) return false;
  const [a, b] = s;
  return a === 10 || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || (a === 169 && b === 254);
}

function yerelDonguAdresi(ip) {
  return ip === "127.0.0.1";
}

// metin -> { ad, port }. yerelDongu: YALNIZ hata ayiklama derlemesinde (adb reverse ile sahte kart).
export function hedefAyir(metin, { yerelDongu = false } = {}) {
  if (typeof metin !== "string") throw new HedefHatasi("bicim");
  let s = metin.replace(/^ +| +$/g, "");
  if (/^http:\/\//i.test(s)) {
    s = s.slice(7);
    if (s.endsWith("/")) s = s.slice(0, -1);
  }
  // Yazdirilabilir ASCII disi, bosluk, yol/sorgu/parca, kullanici adi, ters egik, koseli ayrac: ret.
  if (s === "" || /[^\x21-\x7e]/.test(s) || /[/?#@\\[\]]/.test(s)) throw new HedefHatasi("bicim");
  let ad = s;
  let port = VARSAYILAN_PORT;
  const k = s.indexOf(":");
  if (k >= 0) {
    ad = s.slice(0, k);
    const p = s.slice(k + 1);
    if (!/^[1-9][0-9]{0,4}$/.test(p) || Number(p) > 65535) throw new HedefHatasi("bicim");
    port = Number(p);
  }
  if (sekizliler(ad)) {
    if (ozelAdres(ad) || (yerelDongu && yerelDonguAdresi(ad))) return { ad, port };
    throw new HedefHatasi("ozel-degil");
  }
  if (ad.toLowerCase() === KART_ADI) return { ad: KART_ADI, port };
  // Rakamla baslayan ve yalniz rakam/nokta/onaltilik harf iceren: bozuk IP yazimi (ad degil).
  if (ad === "" || /^[0-9][0-9a-fx.]*$/i.test(ad)) throw new HedefHatasi("bicim");
  throw new HedefHatasi("ad-izinsiz");
}

export function hedefYazi({ ad, port }) {
  return port === VARSAYILAN_PORT ? ad : `${ad}:${port}`;
}
