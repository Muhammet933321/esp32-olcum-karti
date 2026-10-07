// sablon_karsilastir.mjs — DOM sablonu tuzaklarinin KESIN denetimi (acilis.py cagirir).
//
// PC'de Vue kok sablonu TARAYICININ ayristirdigi #uyg'nin innerHTML'inden derler (in-DOM sablon:
// oznitelik adlari kucultulur, tablolar / <p> ic ice kurallari uygulanir, kendinden kapanan etiket
// acik sayilir). Telefon paketi ayni sablonu HAM metinden derler (araclar/panel_paketle.mjs). Ikisi
// ayni render kodunu uretmiyorsa telefon PC'den farkli cizer.
//
// Kullanim: node sablon_karsilastir.mjs <tarayici-innerHTML-dosyasi>
// Cikti (stdout, tek satir JSON): { ayni, ham_bayt, tarayici_bayt, ilk_fark? }
import { readFileSync } from "node:fs";
import { kokSablonuAyikla, sablonDerle, PANEL_HTML } from "../araclar/panel_paketle.mjs";

const tarayici = readFileSync(process.argv[2], "utf8");
const { sablon } = kokSablonuAyikla(readFileSync(PANEL_HTML, "utf8"));
const a = sablonDerle(sablon, "ham").kod;
const b = sablonDerle(tarayici, "tarayici").kod;
const sonuc = { ayni: a === b, ham_bayt: a.length, tarayici_bayt: b.length };
if (a !== b) {
  const sa = a.split("\n");
  const sb = b.split("\n");
  const i = sa.findIndex((s, k) => s !== sb[k]);
  sonuc.ilk_fark = { satir: i + 1, ham: (sa[i] || "").slice(0, 300), tarayici: (sb[i] || "").slice(0, 300) };
}
process.stdout.write(JSON.stringify(sonuc) + "\n");
