// Telefonda sure olcumleri (Ayarlar > Gelismis).
// PBKDF2: eslestirmede kullanilan AYNI kod — ortak/src/imza.js `pbkdf2` -> kripto.js
// `pbkdf2HmacSha256`: SAF JS (WebCrypto `crypto.subtle` DEGIL, Kotlin DEGIL), WebView'in JS motorunda
// ana is parcaciginda calisir. Parola sabit bir SINAMA degeri (gercek parola burada hic kullanilmaz).
// Sonucun DOGRU oldugu da gosterilir: turetilen 32 bayt, Python `hashlib.pbkdf2_hmac`'in ayni girdiyle
// verdigi degerle karsilastirilir (hizli ama yanlis bir hesap olcum sayilmaz).
import { pbkdf2 } from "@ortak/imza.js";
import { hex } from "@ortak/kripto.js";

export const SINAMA_PAROLASI = "sinama-parolasi-olcum";
export const SINAMA_TUZU = new Uint8Array(16);            // 16 sifir bayt
// hashlib.pbkdf2_hmac("sha256", b"sinama-parolasi-olcum", bytes(16), 20000, 32).hex()
export const BEKLENEN_20000 = "3f042897317e112506e74084a8529f73c13d0720f75925a0d42d209d464cc676";

export function pbkdf2Olc(tur, { tekrar = 3, simdi = () => performance.now() } = {}) {
  const sureler = [];
  let ozet = "";
  for (let i = 0; i < tekrar; i++) {
    const t0 = simdi();
    const P = pbkdf2(SINAMA_PAROLASI, SINAMA_TUZU, tur);
    sureler.push(Math.round(simdi() - t0));
    ozet = hex(P);
    P.fill(0);
  }
  const sirali = [...sureler].sort((a, b) => a - b);
  return {
    tur, sureler, enAz: sirali[0], ortanca: sirali[Math.floor(sirali.length / 2)], enCok: sirali[sirali.length - 1],
    ozet,
    // Yalniz 20 000 tur icin basvuru degeri var; baska turda dogrulama yapilamaz (null).
    dogru: tur === 20000 ? ozet === BEKLENEN_20000 : null,
  };
}

// ACIL DURDURMA suresi (Ö7, hedef < 1 s): `durdur` (uygulama.js acilDurdur) art arda cagrilir; her
// cagrinin suresi (dokunusun JS'e vardigi andan kartin yanitina) ve basari sayisi. p0 pil testini
// keser; test surmuyorken zararsizdir. Aralarda kisa bekleme: kartin web cekirdegi sirayla calisir.
export async function durdurOlc(durdur, { tekrar = 20, araMs = 250, simdi = () => performance.now(), bekle = (ms) => new Promise((c) => setTimeout(c, ms)) } = {}) {
  const sureler = [];
  let basari = 0;
  for (let i = 0; i < tekrar; i++) {
    const t0 = simdi();
    const s = await durdur();
    sureler.push(Math.round(simdi() - t0));
    if (s && s.tamam === true) basari++;
    if (i < tekrar - 1) await bekle(araMs);
  }
  const sirali = [...sureler].sort((a, b) => a - b);
  return { tekrar, basari, sureler, enAz: sirali[0], ortanca: sirali[Math.floor(sirali.length / 2)], enCok: sirali[sirali.length - 1] };
}
