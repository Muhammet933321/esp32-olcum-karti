// "Ekrana gomulu metin yok" ayiklayicisi (tasarim §4 Ekranlar / A43). Bir .vue dosyasinda sozlukten
// GECMEDEN ekrana gidebilecek metinleri bulur:
//   1. sablonda harf iceren duz metin dugumu
//   2. cevrilmesi gereken duz ozellik (aria-label, title, placeholder, label, alt, helper-text ...),
//      cift ya da tek tirnakla
//   3. bagli ozellik / v-text / v-html / {{ }} icindeki dizgi sabiti — sozluk anahtari bicimi
//      ("m.kb.baslik") ya da kisa bir karsilastirma belirteci ('nsd') degilse
//   4. <script> icinde BOSLUK ve harf iceren dizgi sabiti (anahtarlar, turler, yollar bosluk icermez)
// Bulunanlarin listesini doner (bos = temiz).

const HARF = /\p{L}/u;
const ANAHTAR = /^[a-z][a-z0-9_-]*(\.[a-z0-9_-]+)+$/;          // sozluk anahtari: "m.kb.baslik"
const BELIRTEC = /^[a-z0-9_-]{1,24}$/;                          // 'nsd', 'kimlik-uymuyor', 'large'
const METIN_OZELLIKLERI = "aria-label|title|placeholder|label|alt|helper-text|error-text|header|sub-header|message|text";

function dizgiSabitleri(ifade) {
  const cikti = [];
  for (const m of ifade.matchAll(/'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)"|`((?:[^`\\]|\\.)*)`/g)) {
    cikti.push(m[1] ?? m[2] ?? m[3]);
  }
  return cikti;
}

const sablonSabitiTemiz = (s) => !HARF.test(s) || ANAHTAR.test(s) || BELIRTEC.test(s);

export function gomuluMetinler(vue) {
  const bulunan = [];
  const s = /<template>([\s\S]*)<\/template>/.exec(vue);
  if (s) {
    const sablon = s[1].replace(/<!--[\s\S]*?-->/g, "");
    // 3a. {{ }} icindeki dizgi sabitleri
    for (const b of sablon.matchAll(/\{\{([\s\S]*?)\}\}/g)) {
      for (const d of dizgiSabitleri(b[1])) if (!sablonSabitiTemiz(d)) bulunan.push(`{{ "${d}" }}`);
    }
    // 1. duz metin dugumleri
    for (const d of sablon.matchAll(/>([^<]+)</g)) {
      const metin = d[1].replace(/\{\{[\s\S]*?\}\}/g, "").trim();
      if (HARF.test(metin)) bulunan.push(metin);
    }
    // 2. duz ozellikler (iki tirnak turu)
    for (const o of sablon.matchAll(new RegExp(`\\s(${METIN_OZELLIKLERI})=(?:"([^"]*)"|'([^']*)')`, "g"))) {
      const deger = o[2] ?? o[3];
      if (HARF.test(deger)) bulunan.push(`${o[1]}="${deger}"`);
    }
    // 3b. bagli ozellikler ve v-text / v-html
    for (const o of sablon.matchAll(/\s(:[\w.-]+|v-bind:[\w.-]+|v-text|v-html)=(?:"([^"]*)"|'([^']*)')/g)) {
      for (const d of dizgiSabitleri(o[2] ?? o[3])) if (!sablonSabitiTemiz(d)) bulunan.push(`${o[1]}="${d}"`);
    }
  }
  // 4. betik
  for (const b of vue.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)) {
    const kod = b[1].split("\n").filter((l) => !/^\s*(\/\/|import )/.test(l)).join("\n");
    for (const d of dizgiSabitleri(kod)) if (HARF.test(d) && /\s/.test(d.trim())) bulunan.push(`betik: "${d}"`);
  }
  return bulunan;
}
