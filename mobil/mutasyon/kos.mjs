// Mutasyon kosucusu (mobil/). Kaynagi bir KOPYADA bozar, ilgili testi kosar, KIRMIZI bekler.
// Asil agaca dokunmaz. Kullanim:
//   node mutasyon/kos.mjs [--neden ONEK] [--liste dosya.mjs]
// Sonuc: OLDU (test kirmizi — iddia isiriyor) | YASIYOR (test yesil — bos iddia) |
//        UYGULANAMADI (desen kaynakta yok ya da birden cok). Son ikisinde cikis kodu 1.
// ortak/ ve uretim/ kopyalanmaz: gecici dizine BAGLANTI (junction) ile gelir, mutasyon hedefi OLAMAZ.

import { spawnSync } from "node:child_process";
import { cpSync, existsSync, mkdtempSync, readFileSync, rmSync, rmdirSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve, sep } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const MOBIL = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const KOK = resolve(MOBIL, "..");
const KOPYALANMAZ = new Set(["node_modules", "dist", "android", ".gradle"]);
const BAGLANTILAR = [["ortak", join(KOK, "ortak")], ["uretim", join(KOK, "uretim")]];

function secenek(ad) {
  const i = process.argv.indexOf(ad);
  return i >= 0 ? process.argv[i + 1] : null;
}

export function uygula(metin, bul, koy) {
  const ilk = metin.indexOf(bul);
  if (ilk < 0) return { hata: "desen yok" };
  if (metin.indexOf(bul, ilk + 1) >= 0) return { hata: "desen birden cok" };
  return { metin: metin.slice(0, ilk) + koy + metin.slice(ilk + bul.length) };
}

function kopyaKur() {
  const kok = mkdtempSync(join(tmpdir(), "mobil-mut-"));
  const hedef = join(kok, "mobil");
  cpSync(MOBIL, hedef, {
    recursive: true,
    filter: (kaynak) => !KOPYALANMAZ.has(kaynak.slice(MOBIL.length + 1).split(sep)[0]),
  });
  const baglar = [[join(hedef, "node_modules"), join(MOBIL, "node_modules")]];
  for (const [ad, asil] of BAGLANTILAR) baglar.push([join(kok, ad), asil]);
  for (const [yol, asil] of baglar) symlinkSync(asil, yol, "junction");
  return { kok, hedef, baglar: baglar.map((b) => b[0]) };
}

function kopyaSil(k) {
  // Once baglantilar: rmdir yalniz BAGLANTIYI kaldirir, asil dizinin icine girmez.
  for (const yol of k.baglar) { try { rmdirSync(yol); } catch { /* yok */ } }
  rmSync(k.kok, { recursive: true, force: true });
}

function testKos(hedef, test) {
  const komut = typeof test === "string"
    ? [process.execPath, [join(hedef, "node_modules", "vitest", "vitest.mjs"), "run", test]]
    : [test.komut[0], test.komut.slice(1)];
  const s = spawnSync(komut[0], komut[1], { cwd: hedef, encoding: "utf8", timeout: 300000 });
  return { kod: s.status, cikti: (s.stdout || "") + (s.stderr || "") };
}

export function biriniKos(m) {
  const k = kopyaKur();
  try {
    const yol = join(k.hedef, m.dosya);
    if (!existsSync(yol)) return { sonuc: "UYGULANAMADI", ayrinti: "dosya yok" };
    const u = uygula(readFileSync(yol, "utf8"), m.bul, m.koy);
    if (u.hata) return { sonuc: "UYGULANAMADI", ayrinti: u.hata };
    writeFileSync(yol, u.metin);
    const t = testKos(k.hedef, m.test);
    if (t.kod === null) return { sonuc: "UYGULANAMADI", ayrinti: "test zaman asimi / calismadi" };
    // Iddiasiz cokme (sozdizimi hatasi, ice aktarma hatasi) "oldu" SAYILMAZ: en az bir testin
    // iddiasi kirmizi olmali. vitest ozetinde "N failed" Tests satiri aranir.
    if (t.kod !== 0 && !/Tests\s+.*\d+ failed/.test(t.cikti) && typeof m.test === "string") {
      return { sonuc: "SUPHELI", ayrinti: "test iddiasiz coktu (derleme/ice aktarma hatasi?)" };
    }
    return { sonuc: t.kod === 0 ? "YASIYOR" : "OLDU", ayrinti: "" };
  } finally {
    kopyaSil(k);
  }
}

async function ana() {
  const listeYolu = resolve(secenek("--liste") || join(MOBIL, "mutasyon", "liste.mjs"));
  const neden = secenek("--neden");
  let liste = (await import(pathToFileURL(listeYolu).href)).default;
  if (neden) liste = liste.filter((m) => m.ad.startsWith(neden));
  let kotu = 0;
  for (const m of liste) {
    const r = biriniKos(m);
    if (r.sonuc !== "OLDU") kotu++;
    console.log(`${r.sonuc.padEnd(12)} ${m.ad}${r.ayrinti ? "  — " + r.ayrinti : ""}`);
  }
  console.log(`\n${liste.length - kotu}/${liste.length} oldu`);
  process.exit(kotu ? 1 : 0);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await ana();
