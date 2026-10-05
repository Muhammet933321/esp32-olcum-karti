// "Kaydi baslat" / "Kaydi durdur" dugmesinin mantigi (A39, A40). Saf; DOM'suz sinanir
// (KayitDugmesi.vue yalniz sonucu sablona baglar).
//
//   dugmeHali({ baglanti, akis, suruyor, oturumTuru })
//     -> { is: "baslat" | "durdur", kapali, neden, nedenDeger, aciklama }
//   const onayci = durdurOnayi({ degisti: (bekliyor) => { ... } });
//   dokunus(hal, onayci) -> "baslat" | "durdur" | null   (null: hicbir sey yapma)
//
// Komut yolu AKISTAN BAGIMSIZDIR (imzali POST /komut): dugme kartin BAGLI (eslesmis) olmasina bakar,
// akisin acik olmasina DEGIL — akis "hata"dayken de "Kaydi durdur" basilabilir.
// "Durdur" IKI dokunus ister (uzun bir kaydi yanlislikla kesmemek icin); ACIL DURDUR degildir.

import { kayitDugmesi } from "./canli_gorunum.js";
import { oturumKilidi } from "./durum_gorunum.js";

export const ONAY_MS = 4000;

export function dugmeHali({ baglanti = null, akis = null, suruyor = false, oturumTuru = null } = {}) {
  const d = kayitDugmesi(akis ? akis.kayit : null);
  const kilit = oturumKilidi(oturumTuru);
  const komutYolu = Boolean(baglanti) && baglanti.durum === "bagli" && Boolean(akis) && akis.hazir === true;
  const durumKapali = d.is === "kapali";            // dolu / hata / tariyor: kart kayit BASLATAMAZ
  return {
    is: d.is === "durdur" ? "durdur" : "baslat",
    kapali: suruyor === true || !komutYolu || durumKapali || kilit.saltOkuma,
    neden: durumKapali ? d.neden : null,
    nedenDeger: durumKapali ? d.nedenDeger || null : null,
    aciklama: kilit.saltOkuma ? kilit.aciklama : null,
  };
}

// "Durdur"un onay adimi: ilk dokunus onay ISTER (ONAY_MS sonra kendiliginden vazgecilir), ikincisi gonderir.
export function durdurOnayi({ degisti, zamanla = (fn, ms) => setTimeout(fn, ms), zamaniBirak = (z) => clearTimeout(z) }) {
  if (typeof degisti !== "function") throw new TypeError("degisti gerekli");
  let bekliyor = false;
  let z = null;
  const yap = (v) => { bekliyor = v; degisti(v); };

  function iptal() {
    if (z !== null) zamaniBirak(z);
    z = null;
  }

  // -> true: ikinci dokunus (komut SIMDI gonderilir) | false: ilk dokunus (onay istendi)
  function bas() {
    iptal();
    if (!bekliyor) {
      yap(true);
      z = zamanla(() => { z = null; yap(false); }, ONAY_MS);
      return false;
    }
    yap(false);
    return true;
  }

  return { bas, birak: iptal };
}

// Dokunus -> yapilacak is. KAPALI dugme hicbir sey yapmaz (sablondaki `disabled` atlansa da).
export function dokunus(hal, onayci) {
  if (!hal || hal.kapali) return null;
  if (hal.is === "durdur") return onayci.bas() ? "durdur" : null;
  return "baslat";
}
