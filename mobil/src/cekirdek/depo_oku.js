// Ham kayit dosyasinin YEREL okunmasi (tasarim A24). Bu dosya, src/ agacinda WebView'in kendi istek
// yapabildigi TEK yerdir ve yalniz SU adresi okur:   /_depo/<16 onaltilik>/kayitlar.kyt
// O adres aga CIKMAZ: MainActivity istegi yakalar, dosyayi uygulamanin ozel dizininden verir
// (DepoYolu.kt ayni bicimi ikinci kez denetler; WebKapi paket disi her adresi zaten engeller).
// Adres bicime uymuyorsa istek HIC yapilmaz. Ana is parcaciginda da Worker'da da ayni islev.
export const DEPO_ADRESI = /^\/_depo\/[0-9a-f]{16}\/kayitlar\.kyt$/;

export class DepoOkuHatasi extends Error {
  constructor(tur) {
    super(tur);
    this.name = "DepoOkuHatasi";
    this.tur = tur;
  }
}

// -> Uint8Array (dosya yoksa: bos). Bicimsiz adres: DepoOkuHatasi("bicim"), istek YOK.
export async function yerelOku(url) {
  if (typeof url !== "string" || !DEPO_ADRESI.test(url)) throw new DepoOkuHatasi("bicim");
  let y;
  try { y = await fetch(url, { cache: "no-store", credentials: "omit", redirect: "error" }); } catch { throw new DepoOkuHatasi("okunamadi"); }
  if (y.status === 404) return new Uint8Array(0);          // henuz esitlenmemis: bos kopya
  if (y.status !== 200) throw new DepoOkuHatasi("okunamadi");
  try { return new Uint8Array(await y.arrayBuffer()); } catch { throw new DepoOkuHatasi("okunamadi"); }
}
