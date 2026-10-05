// Mutasyon listelerinin HIZLI on denetimi: her girdinin `bul` dizgisi kaynakta TAM BIR KEZ geciyor mu?
// Kaynak degistikten sonra eskiyen girdileri (kosucuda "UYGULANAMADI") testleri kosmadan bulur.
//   node mutasyon/desen-denetle.mjs            -> eskiyenleri yazar; hepsi tamamsa cikis 0
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import js from "./liste.mjs";
import kotlin from "./kotlin-liste.mjs";

const kok = fileURLToPath(new URL("..", import.meta.url));
const oku = (yol) => readFileSync(kok + yol, "utf8").replace(/\r\n/g, "\n");
let eskiyen = 0;
for (const [ad, liste] of [["js", js], ["kotlin", kotlin]]) {
  for (const m of liste) {
    let adet;
    try { adet = oku(m.dosya).split(m.bul.replace(/\r\n/g, "\n")).length - 1; } catch { adet = -1; }
    if (adet !== 1) { eskiyen += 1; process.stdout.write(`${ad} ${adet === -1 ? "DOSYA-YOK" : `desen x${adet}`}  ${m.ad}\n`); }
  }
}
process.stdout.write(`${js.length + kotlin.length} girdi, ${eskiyen} eskimis\n`);
process.exit(eskiyen === 0 ? 0 : 1);
