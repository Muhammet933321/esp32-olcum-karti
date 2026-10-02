// B73 test yardimcisi (test DEGIL): sozluk.test.js ve sozluk_es.test.js'in ORTAK dizge cozucusu —
// "kullanilmayan anahtar yok" ve "ters yon" denetimleri iki sozlukte AYNI kuralla olculsun.
/** Kucuk JS sozcuk cozucu: yorumlari atlar; '...', "..." icerigini ve `...${ oneklerini toplar.
 *  (Regex sabitlerinde tirnak yok varsayimi: kaynak boyle yazildi, bozulursa asagidaki
 *  "dizge sayisi" denetimi kirmiziya doner.) */
export function dizgeler(src) {
  const literal = new Set();
  const sablon = new Set();
  let i = 0;
  while (i < src.length) {
    const c = src[i];
    if (c === "/" && src[i + 1] === "/") { const j = src.indexOf("\n", i); i = j < 0 ? src.length : j; continue; }
    if (c === "/" && src[i + 1] === "*") { i = src.indexOf("*/", i + 2) + 2; continue; }
    if (c === '"' || c === "'" || c === "`") {
      let j = i + 1;
      let s = "";
      let onek = null;
      while (j < src.length && src[j] !== c) {
        if (src[j] === "\\") { s += src[j + 1]; j += 2; continue; }
        if (c === "`" && src[j] === "$" && src[j + 1] === "{" && onek === null) onek = s;
        if (src[j] === "\n" && c !== "`") throw new Error(`kapanmamis dizge: ${src.slice(i, i + 40)}`);
        s += src[j];
        j++;
      }
      if (c === "`") { if (onek !== null) sablon.add(onek); } else literal.add(s);
      i = j + 1;
      continue;
    }
    i++;
  }
  return { literal, sablon };
}
