// Esitleme ayari (A21): "Bu telefon da onaylasin" anahtari. VARSAYILAN KAPALI: telefon bir kopyadir,
// arsiv PC'dedir; onay acilirsa kart, PC'nin henuz almadigi kayitlari silebilir. Yerel depoda saklanir
// (sir degil). Yalniz kesin "1" ACIK sayilir: bozuk / eksik / okunamayan deger KAPALI demektir.
export const ONAY_ANAHTARI = "esitleme.onay";

export function onayOku(depo) {
  try { return depo.getItem(ONAY_ANAHTARI) === "1"; } catch { return false; }
}

// Donus: saklanan deger (yazilamadiysa eski deger).
export function onayYaz(depo, acik) {
  try {
    if (acik === true) depo.setItem(ONAY_ANAHTARI, "1");
    else depo.removeItem(ONAY_ANAHTARI);
  } catch { /* depo kapali: ayar degismez */ }
  return onayOku(depo);
}
