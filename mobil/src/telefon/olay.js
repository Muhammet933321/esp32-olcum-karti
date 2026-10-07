// "Bu telefon" bolumunun uygulamaya verdigi iki haber (telefon ortami — mobil/src/ortam — dinler):
//
//   baglantiDinle(fn)   -> birak()    Kart bolumunde baglanti / eslesme / kaldirma bitti: fn({ durum, adres, kimlik })
//                                     (eski kabugun baglantiDegisti'si: canli akis yeni duruma gore kurulur)
//   mesgulMu()          -> boolean    Eslestirme suruyor: o sirada kart YENIDEN ARANMAZ (kart.baglan() suren
//                                     eslestirmenin baglantisini sifirlardi — eski kabugun mesgulYap'i)
//
// Dinleyici hatasi bolumu bozmaz. Ozet sir tasimaz (adres + kimlik + durum; anahtar / parola YOK).

const dinleyenler = new Set();
let mesgul = 0;

export function baglantiDinle(fn) {
  if (typeof fn !== "function") throw new TypeError("fn gerekli");
  dinleyenler.add(fn);
  return () => { dinleyenler.delete(fn); };
}

export function baglantiBildir(b) {
  const ozet = b ? { durum: b.durum, adres: b.adres || null, kimlik: b.kimlik || null } : null;
  for (const fn of dinleyenler) {
    try { fn(ozet); } catch { /* dinleyicinin kusuru bolumu etkilemez */ }
  }
  return ozet;
}

export function mesgulYap(v) {
  mesgul = Math.max(0, mesgul + (v ? 1 : -1));
}

export function mesgulMu() {
  return mesgul > 0;
}
