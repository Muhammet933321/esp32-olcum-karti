// CURUTUCU 5B: kartin dayatabildigi en buyuk PBKDF2 turunun (TUR_EN_COK = 1 000 000) ana is parcacigini
// ne kadar kilitledigini olcer (saf JS, es zamanli). 100 000 tur olculur, 1 000 000'a oranlanir.
//   node test/curutucu-5b/tur-olc.mjs
import { TUR_EN_COK, pbkdf2 } from "../../../ortak/src/imza.js";

const tuz = new Uint8Array(16).fill(3);
const olc = (tur) => { const t = performance.now(); pbkdf2("sinama-parolasi-1", tuz, tur); return performance.now() - t; };
olc(2000);
const t20 = olc(20000), t100 = olc(100000);
console.log(`20000 tur: ${t20.toFixed(0)} ms   100000 tur: ${t100.toFixed(0)} ms   ${TUR_EN_COK} tur (oranla): ${(t100 * TUR_EN_COK / 100000 / 1000).toFixed(1)} s`);
