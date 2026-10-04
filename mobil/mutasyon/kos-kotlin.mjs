// Kotlin mutasyon kosucusu (hafif; JVM birim testleri). Liste: mutasyon/kotlin-liste.mjs
//   node mutasyon/kos-kotlin.mjs [--neden ONEK]
// kos.mjs gibi kaynagi bir KOPYADA bozar; fark: TEK kopya kurulur, Gradle bir kez "taban" icin kosar
// (yesil olmali), sonra her mutasyon sirayla uygulanir -> test -> GERI ALINIR (artimli derleme).
// Sonuc: OLDU (Gradle kirmizi VE beklenen test kirmizi) | YASIYOR | UYGULANAMADI | SUPHELI (kirmizi
// ama beklenen test degil: derleme hatasi ya da baska test). OLDU disinda cikis kodu 1.
// Gradle agir: makine paylasiliyorsa baska kosu yokken calistir.

import { spawnSync } from "node:child_process";
import { cpSync, existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, rmdirSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve, sep } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { uygula } from "./kos.mjs";

const MOBIL = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const KOPYALANMAZ = ["node_modules", "dist", "android/app/build", "android/build", "android/.gradle",
  "android/capacitor-cordova-android-plugins/build", "tasarim-adaylari"];
const SONUC_DIZINI = "android/app/build/test-results/testDebugUnitTest";

function secenek(ad) {
  const i = process.argv.indexOf(ad);
  return i >= 0 ? process.argv[i + 1] : null;
}

function kopyaKur() {
  const kok = mkdtempSync(join(tmpdir(), "mobil-kmut-"));
  const hedef = join(kok, "mobil");
  cpSync(MOBIL, hedef, {
    recursive: true,
    filter: (kaynak) => {
      const g = kaynak.slice(MOBIL.length + 1).split(sep).join("/");
      return !KOPYALANMAZ.some((k) => g === k || g.startsWith(k + "/"));
    },
  });
  const bag = join(hedef, "node_modules");
  symlinkSync(join(MOBIL, "node_modules"), bag, "junction");
  return { kok, hedef, bag };
}

function testKos(hedef) {
  const s = spawnSync(`"${join(hedef, "android", "gradlew.bat")}"`, ["testDebugUnitTest", "--console=plain", "-q", "--offline"],
    { cwd: join(hedef, "android"), encoding: "utf8", timeout: 900000, shell: true });
  // Kirmizi testlerin adlari sonuc XML'lerinden (sinif.yontem).
  const kirmizi = [];
  const dizin = join(hedef, SONUC_DIZINI);
  if (existsSync(dizin)) {
    for (const ad of readdirSync(dizin).filter((a) => a.endsWith(".xml"))) {
      const xml = readFileSync(join(dizin, ad), "utf8");
      const sinif = /<testsuite name="([^"]+)"/.exec(xml)?.[1]?.split(".").pop();
      for (const m of xml.matchAll(/<testcase name="([^"]+)"[^>]*>\s*<(?:failure|error)/g)) kirmizi.push(`${sinif}.${m[1]}`);
    }
  }
  const satirlar = ((s.stdout || "") + (s.stderr || "")).split(/\r?\n/).filter((l) => l.trim());
  return { kod: s.status, kirmizi, cikti: satirlar.slice(-12).join(" | ") };
}

async function ana() {
  let liste = (await import(pathToFileURL(join(MOBIL, "mutasyon", "kotlin-liste.mjs")).href)).default;
  const neden = secenek("--neden");
  if (neden) liste = liste.filter((m) => m.ad.startsWith(neden));
  if (liste.length === 0) { console.log("UYGULANAMADI: suzgece uyan mutasyon yok"); process.exit(1); }
  const k = kopyaKur();
  let kotu = 0;
  try {
    const taban = testKos(k.hedef);
    // process.exit burada KULLANILMAZ: finally (kopyanin silinmesi) atlanirdi.
    if (taban.kod !== 0) {
      console.log(`UYGULANAMADI: taban kirmizi (${taban.kirmizi.join(", ") || "derleme"}) :: ${taban.cikti}`);
      kotu = liste.length;
    }
    for (const m of taban.kod === 0 ? liste : []) {
      const yol = join(k.hedef, m.dosya);
      let sonuc, ayrinti = "";
      if (!existsSync(yol)) { sonuc = "UYGULANAMADI"; ayrinti = "dosya yok"; } else {
        const asil = readFileSync(yol, "utf8");
        const u = uygula(asil, m.bul, m.koy);
        if (u.hata) { sonuc = "UYGULANAMADI"; ayrinti = u.hata; } else {
          writeFileSync(yol, u.metin);
          const t = testKos(k.hedef);
          writeFileSync(yol, asil);
          if (t.kod === 0) sonuc = "YASIYOR";
          else if (t.kod === null) { sonuc = "UYGULANAMADI"; ayrinti = "zaman asimi"; }
          else if (m.kirmizi && !t.kirmizi.includes(m.kirmizi)) { sonuc = "SUPHELI"; ayrinti = `beklenen ${m.kirmizi} kirmizi degil (${t.kirmizi.slice(0, 3).join(", ") || "derleme hatasi?"})`; }
          else sonuc = "OLDU";
        }
      }
      if (sonuc !== "OLDU") kotu++;
      console.log(`${sonuc.padEnd(12)} ${m.ad}${ayrinti ? "  — " + ayrinti : ""}`);
    }
  } finally {
    // Kopyadaki dosya kilitlerini birakmasi icin yalniz BU kopyada derleme yapan surecler bekletilmez:
    // Gradle sureci (daemon) kopya dizinini acik tutabilir; silme yeniden denemeli.
    try { rmdirSync(k.bag); } catch { /* yok */ }
    rmSync(k.kok, { recursive: true, force: true, maxRetries: 5, retryDelay: 500 });
  }
  console.log(`\n${liste.length - kotu}/${liste.length} oldu`);
  process.exit(kotu ? 1 : 0);
}

await ana();
