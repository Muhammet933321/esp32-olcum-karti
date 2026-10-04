// CURUTUCU: JS (hedef.js, ag.js urlDenetle) ile Kotlin (Hedef.kt + hazirla'nin saf kopyasi) AYNI girdiye
// ayni karari veriyor mu? Gercek Kotlin kaynagi derlenmis olmali (kotlin/derle.sh). Ag yok.
//   node test/curutucu/fark.mjs <derleme-dizini> [adet]
import { spawnSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { hedefAyir, ozelAdres, HedefHatasi } from "../../src/cekirdek/hedef.js";
import { urlDenetle, KartAgHatasi } from "../../src/cekirdek/ag.js";

const DIZIN = process.argv[2];
const ADET = Number(process.argv[3] || 20000);
const AT = String.fromCharCode(64);

let tohum = 0x5a17;
const rs = () => { tohum ^= tohum << 13; tohum >>>= 0; tohum ^= tohum >>> 17; tohum ^= tohum << 5; tohum >>>= 0; return tohum; };
const sec = (d) => d[rs() % d.length];

const ALFABE = [..."0123456789", ".", ".", ":", ":", "/", "/", AT, "\\", "[", "]", " ", "\t", "\n", "\r", "\0", "x", "X", "a", "f",
  "o", "l", "c", "u", "m", "O", "L", "h", "t", "p", "H", "T", "P", "-", "+", "%", "#", "?", ";", "１", "İ", "ı",
  "K", "١", " ", "﻿", "　", "\u0085", " ", "%2e", "%2E", "。", "．", "0x", "::", "ffff"];
const AYIR_TOHUM = ["192.168.1.7", "192.168.1.7:8080", "10.0.0.5:1", "olcum.local", "OLCUM.LOCAL:81", "http://192.168.1.5/",
  "HTTP://192.168.1.5:81/", "8.8.8.8", "172.16.0.1", "169.254.1.1:65535", "127.0.0.1", "http://olcum.local", "0xC0A80101",
  "192.168.1.5:080", "192.168.1.5:+80", "192.168.1.5:-1", " 192.168.1.5 ", "olcum.local.", "192.168.01.1", "[::ffff:192.168.1.1]", ""];
const URL_TOHUM = ["http://192.168.1.5/x", "http://192.168.1.5:8080/a?b=1", "http://olcum.local/eslestir/bilgi", "http://8.8.8.8/",
  "HTTP://10.0.0.1", `http://192.168.1.5:80${AT}8.8.8.8/`, `http://192.168.1.5#${AT}8.8.8.8/`, `http://192.168.1.5\\${AT}8.8.8.8/`,
  "http://[::ffff:8.8.8.8]/", "http:///x", "http://192.168.1.5:-1/", "http://192.168.1.5:+80/", "http://192.168.1.5:080/",
  "http://192.168.1.5./", "http://192%2e168.1.5/", "http://１９２.168.1.5/", "http://192.168.1.5\t/", "http://192.168.1.5/a\r\nX: y",
  "url:http://192.168.1.5/", " http://192.168.1.5/ ", "http://192.168.1.5?x", "http://192.168.1.5:/", "http://192.168.1.5:٨٠/",
  `http://a${AT}b${AT}192.168.1.5/`, "http:192.168.1.5", "http:/192.168.1.5", "http://8.8.8.8:80#" + AT + "192.168.1.5", "http://192.168.1.5:80:8.8.8.8/",
  "http://olcum.local.evil.example/", `http://olcum.local${AT}evil.example/`, "http://OLCUM.LOCAL:81/x", "https://192.168.1.5/", "http://8.8.8.8\\.192.168.1.5/",
  "http://192.168.1.5/a b", "http://192.168.1.5/ç", "http://192.168.1.5;8.8.8.8/", "http://192.168.1.5&8.8.8.8/", "http://192.168.1.5,8.8.8.8/", "http://0/", "http://3232235777/"];

function boz(s) {
  let c = [...s];
  for (let n = 1 + (rs() % 3); n > 0; n--) {
    const i = c.length ? rs() % (c.length + 1) : 0;
    const is = rs() % 4;
    if (is === 0) c.splice(i, 0, sec(ALFABE));
    else if (is === 1 && c.length) c.splice(Math.min(i, c.length - 1), 1);
    else if (is === 2 && c.length) c[Math.min(i, c.length - 1)] = sec(ALFABE);
    else c.splice(i, 0, sec(AYIR_TOHUM));
  }
  return c.join("");
}
const hex = (s) => [...Array(s.length).keys()].map((i) => s.charCodeAt(i).toString(16).padStart(4, "0")).join("");
const hexCoz = (h) => h.match(/.{4}/g)?.map((x) => String.fromCharCode(parseInt(x, 16))).join("") ?? "";

const girdiler = [];
for (const s of AYIR_TOHUM) { girdiler.push(["ayir", s]); girdiler.push(["ozel", s]); }
for (const s of URL_TOHUM) girdiler.push(["url", s]);
for (let i = 0; i < ADET; i++) {
  girdiler.push(["ayir", boz(sec(AYIR_TOHUM))]);
  girdiler.push(["ozel", boz(sec(AYIR_TOHUM))]);
  girdiler.push(["url", boz(sec(URL_TOHUM))]);
}
// Dosya satir tabanli: hex kodlu oldugu icin satir sonu sorunu yok.
const gYol = join(DIZIN, "fark-girdi.txt");
const cYol = join(DIZIN, "fark-cikti.txt");
writeFileSync(gYol, girdiler.map(([t, s]) => `${t}\t${hex(s)}`).join("\n") + "\n");
const k = spawnSync("bash", ["test/curutucu/kotlin/derle.sh", join(DIZIN, "out"), "fark", gYol, cYol], { encoding: "utf8" });
if (k.status !== 0) { console.log("Kotlin kosusu basarisiz:", k.stderr); process.exit(2); }
const kotlin = readFileSync(cYol, "utf8").split("\n");

const OZEL_URL = /^http:\/\/((?:\d{1,3}\.){3}\d{1,3}|olcum\.local):([1-9]\d{0,4})(?=[/?]|$)/;
let ayirFark = 0, ozelFark = 0, delik = 0;
const sinif = new Map();
const ekle = (ad, s) => { const l = sinif.get(ad) || []; if (l.length < 4) l.push(JSON.stringify(s)); sinif.set(ad, l); sinif.set(ad + "#", (sinif.get(ad + "#") || 0) + 1); };

girdiler.forEach(([tur, s], i) => {
  const kt = kotlin[i];
  if (tur === "ayir") {
    let js; try { const h = hedefAyir(s); js = `${h.ad}:${h.port}`; } catch (e) { if (!(e instanceof HedefHatasi)) throw e; js = `!${e.tur}`; }
    if (js !== kt) { ayirFark++; ekle(`AYIR FARKI js=${js} kotlin=${kt}`, s); }
  } else if (tur === "ozel") {
    const js = ozelAdres(s) ? "1" : "0";
    if (js !== kt) { ozelFark++; ekle(`OZEL FARKI js=${js} kotlin=${kt}`, s); }
  } else {
    let js; try { const h = urlDenetle(s); js = `OK ${h.ad}:${h.port}`; } catch (e) { if (!(e instanceof KartAgHatasi)) throw e; js = `!${e.tur}`; }
    const ktKabul = kt.startsWith("OK ");
    if (ktKabul) {
      // ASIL SORU: Kotlin kabul ettiyse yeniden kurulan URL GERCEKTEN ozel adrese mi gidiyor?
      // Iki bagimsiz ayristirici: kati desen + WHATWG URL (OkHttp gibi hosgorulu: "\" = "/", sekme atilir).
      const kurulan = hexCoz(kt.slice(3));
      const m = OZEL_URL.exec(kurulan);
      let w = null; try { w = new URL(kurulan); } catch { /* ayristirilamadi */ }
      const tamam = m && (m[1] === "olcum.local" || ozelAdres(m[1])) && w && w.hostname === m[1] && w.username === "" && w.password === "";
      if (!tamam) { delik++; ekle("DELIK: Kotlin kabul etti ama kurulan URL ozel adrese gitmiyor", [s, kurulan]); }
      if (!js.startsWith("OK ")) ekle(`URL: Kotlin KABUL, JS ret (${js})`, [s, kurulan]);
      else if (`http://${js.slice(3)}` !== (m ? `http://${m[1]}:${m[2]}` : "")) ekle("URL: ikisi kabul ama HEDEF farkli", [s, js, kurulan]);
    } else if (js.startsWith("OK ")) ekle(`URL: JS KABUL, Kotlin ret (${kt})`, s);
    else if (kt.startsWith("COKTU")) ekle(`URL: Kotlin ${kt}`, s);
  }
});

console.log(`girdi: ${girdiler.length}`);
console.log(`Hedef.ayir  JS/Kotlin farki : ${ayirFark}`);
console.log(`ozelAdres   JS/Kotlin farki : ${ozelFark}`);
console.log(`Kotlin kabul + ozel OLMAYAN hedef (DELIK): ${delik}`);
for (const [ad, l] of sinif) if (!ad.endsWith("#")) console.log(`\n[${sinif.get(ad + "#")} kez] ${ad}\n   ${l.join("\n   ")}`);
process.exit(ayirFark || ozelFark || delik ? 1 : 0);
