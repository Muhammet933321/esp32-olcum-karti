// Telefonda sure olcumleri (Ayarlar > Gelismis'e tasinacak; simdilik "Karti bul" ekraninda).
// PBKDF2: eslestirmede kullanilan AYNI kod (ortak/src/imza.js, saf JS) ve kartin bildirdigi tur
// sayisiyla; parola sabit bir SINAMA degeri (gercek parola burada hic kullanilmaz).
import { pbkdf2 } from "@ortak/imza.js";

const SINAMA_PAROLASI = "sinama-parolasi-olcum";

export function pbkdf2Olc(tur, { tekrar = 3, simdi = () => performance.now() } = {}) {
  const tuz = new Uint8Array(16);
  const sureler = [];
  for (let i = 0; i < tekrar; i++) {
    const t0 = simdi();
    pbkdf2(SINAMA_PAROLASI, tuz, tur).fill(0);
    sureler.push(Math.round(simdi() - t0));
  }
  const sirali = [...sureler].sort((a, b) => a - b);
  return { tur, sureler, enAz: sirali[0], ortanca: sirali[Math.floor(sirali.length / 2)], enCok: sirali[sirali.length - 1] };
}
