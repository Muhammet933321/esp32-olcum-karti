// Oturum raporunun DUZ METNI (5F; tasarim A41 "paylas: rapor"). Rapor nesnesi ortak/src/rapor.js
// `oturumRaporu`ndan gelir (PC paneliyle AYNI hesap); burasi yalniz yazar: her alan sozlukteki
// etiketiyle (birim etiketin icinde), ic ice bolumler girintiyle. Hesap YOK, yuvarlama disinda sayi
// degismez. Saf: Worker'da ve Node'da calisir.
import { sayiYaz } from "@ortak/disari.js";
import { ALAN_ETIKET, RAPOR_ETIKET } from "@ortak/rapor.js";
import { ceviri } from "@ortak/sozluk.js";
import { ceviriMobil } from "./sozluk_mobil.js";

// Okuyana bir sey soylemeyen ic alanlar.
const ATLA = new Set(["surum", "dil"]);
const GIRINTI = "  ";
// Ortak sozlukte etiketi olmayan rapor alanlari (telefonun sozlugunden).
const EK_ETIKET = {
  bicimSurum: "m.ps.bicim_surum", tekrarAdet: "m.ps.tekrar_adet", sureS: "m.ps.sure_s",
  noktaMs: "m.ps.nokta_ms", sira: "m.ps.sira", metin: "m.ps.metin", genel: "m.ps.genel",
};

function etiket(anahtar, dil) {
  if (Object.hasOwn(RAPOR_ETIKET, anahtar)) return ceviri(RAPOR_ETIKET[anahtar], dil);
  if (Object.hasOwn(ALAN_ETIKET, anahtar)) return ceviri(ALAN_ETIKET[anahtar], dil);
  if (Object.hasOwn(EK_ETIKET, anahtar)) return ceviriMobil(EK_ETIKET[anahtar], dil);
  return anahtar;
}

// Tamsayi aynen; kesirli sayi 6 basamak, sondaki sifirlar atilir (tr'de ondalik virgul).
export function sayiMetni(x, dil) {
  if (!Number.isFinite(x)) return "—";
  if (Number.isInteger(x)) return String(x);
  const y = sayiYaz(x, 6, dil === "tr" ? "," : ".");
  const z = y.replace(/([.,]\d*?)0+$/, "$1").replace(/[.,]$/, "");
  return z;                            // eksi sifir: sayiYaz zaten isaretsiz yazar
}

const kodlu = (v) => v !== null && typeof v === "object" && !Array.isArray(v) && typeof v.metin === "string" && Object.hasOwn(v, "kod");
const duz = (v) => v === null || v === undefined || typeof v !== "object" || kodlu(v);

function degerMetni(v, dil) {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "boolean") return ceviriMobil(v ? "m.ps.evet" : "m.ps.hayir", dil);
  if (typeof v === "number") return sayiMetni(v, dil);
  if (kodlu(v)) return v.kod === null || v.kod === undefined ? v.metin : `${v.metin} (${v.kod})`;
  // Metin TEK satirda kalir (curutucu 5E B16): satir sonu iceren not rapora sahte "alan: deger" satiri sokamaz.
  return String(v).replace(/\s*[\r\n\u0085\u2028\u2029]+\s*/g, " / ").replace(/[\u0000-\u001f\u007f]/g, " ");
}

function yaz(satirlar, ad, v, dil, derinlik) {
  const bas = GIRINTI.repeat(derinlik);
  if (duz(v)) { satirlar.push(`${bas}${ad}: ${degerMetni(v, dil)}`); return; }
  if (Array.isArray(v)) {
    if (v.length === 0) { satirlar.push(`${bas}${ad}: —`); return; }
    if (v.every(duz)) { satirlar.push(`${bas}${ad}: ${v.map((x) => degerMetni(x, dil)).join(", ")}`); return; }
    satirlar.push(`${bas}${ad}:`);
    v.forEach((x, i) => {
      if (duz(x) || Array.isArray(x)) { yaz(satirlar, String(i + 1), x, dil, derinlik + 1); return; }
      satirlar.push(`${bas}${GIRINTI}${i + 1}.`);
      nesne(satirlar, x, dil, derinlik + 2);
    });
    return;
  }
  satirlar.push(`${bas}${ad}:`);
  nesne(satirlar, v, dil, derinlik + 1);
}

function nesne(satirlar, o, dil, derinlik) {
  for (const [k, v] of Object.entries(o)) {
    yaz(satirlar, etiket(k, dil), v, dil, derinlik);
  }
}

// Rapor nesnesi -> metin (satir sonu \n, sonda \n). Ust duzey bolumler arasinda bos satir.
export function raporMetni(rapor, dil = "tr") {
  const satirlar = [ceviriMobil("m.ps.rapor_baslik", dil), ""];
  for (const [k, v] of Object.entries(rapor)) {
    if (ATLA.has(k)) continue;
    yaz(satirlar, etiket(k, dil), v, dil, 0);
    satirlar.push("");
  }
  while (satirlar.length && satirlar[satirlar.length - 1] === "") satirlar.pop();
  return `${satirlar.join("\n")}\n`;
}
