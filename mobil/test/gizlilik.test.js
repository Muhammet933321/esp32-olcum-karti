// Gunlukte sir yok (A45) + aga cikan tek yol KartAg (A47, kullanici sarti 2026-10-04).
// Capacitor kopru gunlugu, her eklenti cagrisinin TUM verisini (adres, imza basliklari, govde;
// ileride Kasa'ya giden anahtar) logcat'e yazar — 2026-10-04'te telefonda goruldu. Bu yuzden kopru
// gunlugu HER derlemede kapali olmali.
// Kaynak taramalari ELLE yazilmis dosya listesiyle degil, src/ ve android/ AGACIYLA calisir
// (curutucu 5A-7: listede olmayan dosyaya eklenen cagri kaciyordu).
import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join, relative } from "node:path";

const KOK = fileURLToPath(new URL("..", import.meta.url));
const oku = (yol) => readFileSync(join(KOK, yol), "utf8");

function agac(dizin, sonlar) {
  const cikti = [];
  for (const ad of readdirSync(join(KOK, dizin))) {
    const yol = join(dizin, ad);
    if (statSync(join(KOK, yol)).isDirectory()) cikti.push(...agac(yol, sonlar));
    else if (sonlar.some((s) => ad.endsWith(s))) cikti.push(relative(".", yol).split("\\").join("/"));
  }
  return cikti;
}

// Yorumlar taranmaz (aciklamalarda "fetch", "Log" gecer): tam satir yorumlari ve blok yorumlari atilir.
function yorumsuz(metin) {
  return metin.replace(/\/\*[\s\S]*?\*\//g, "").split("\n").filter((l) => !/^\s*(\/\/|\*)/.test(l)).join("\n");
}

const JS_KAYNAK = agac("src", [".js", ".vue"]);
const YEREL_KAYNAK = agac("android/app/src/main/java", [".kt", ".java"]);
// WebView'in ag yollarini BILEREK deneyen tek dosya (cihazdaki kapi olcumu).
const SINAMA_DOSYASI = "src/cekirdek/web_sinama.js";

describe("aga cikan tek yol KartAg (WebView kapisi)", () => {
  const IZINLI_YONERGELER = {
    "default-src": ["'self'"],
    "script-src": ["'self'"],
    "style-src": ["'self'", "'unsafe-inline'"],
    "img-src": ["'self'", "data:", "blob:"],
    "connect-src": ["'self'"],
    "frame-src": ["'none'"],
    "object-src": ["'none'"],
    "base-uri": ["'none'"],
    "form-action": ["'none'"],
    "webrtc": ["'block'"],
  };

  it("CSP: yonerge kumesi TAM olarak beklenen (eksik de fazla da kirmizi)", () => {
    const m = /http-equiv="Content-Security-Policy" content="([^"]+)"/.exec(oku("index.html"));
    expect(m, "CSP meta etiketi yok").not.toBe(null);
    const yonerge = Object.fromEntries(m[1].split(";").map((y) => y.trim().split(/ +/)).map(([ad, ...d]) => [ad, d]));
    expect(yonerge).toEqual(IZINLI_YONERGELER);
  });

  it("yerel kapi: MainActivity her istegi ve gezintiyi WebKapi'den geciriyor; cerez yoneticisi kaldirilmis", () => {
    const m = oku("android/app/src/main/java/tr/olcumkarti/mobil/MainActivity.java");
    const kesit = (ad) => m.slice(m.indexOf(ad), m.indexOf("}", m.indexOf("return super." + ad)));
    for (const ad of ["shouldInterceptRequest", "shouldOverrideUrlLoading"]) {
      expect(m.indexOf("return super." + ad), ad).toBeGreaterThan(0);
      expect(kesit(ad), ad).toContain("if (!WebKapi.INSTANCE.izinli(request.getUrl().toString()))");
    }
    // Istemci KOSULSUZ takilir: satir, girintisiyle birlikte, bir deyimin BASINDA durur.
    expect(m).toMatch(/\n {8}bridge\.setWebViewClient\(new BridgeWebViewClient\(bridge\) \{\n/);
    expect(m).toMatch(/\n {8}CookieHandler\.setDefault\(null\);\n/);
    expect(m.indexOf("CookieHandler.setDefault(null);")).toBeGreaterThan(m.indexOf("super.onCreate("));
    // onCreate'te kosul / erken donus yok.
    expect(yorumsuz(m)).not.toMatch(/\bif \(saved|\breturn;/);
  });

  it("Capacitor: disari gezinti izni yok, karisik icerik yok, WebView hata ayiklamasi kapali", () => {
    const k = JSON.parse(oku("capacitor.config.json"));
    expect(k.server?.allowNavigation ?? []).toEqual([]);
    expect(k.android.allowMixedContent).toBe(false);
    expect(k.android.webContentsDebuggingEnabled).toBe(false);
  });

  it("src/ agacinda WebView'in kendi ag cagrisi yok (yalniz sinama dosyasi dener)", () => {
    expect(JS_KAYNAK.length).toBeGreaterThan(5);
    expect(JS_KAYNAK).toContain(SINAMA_DOSYASI);
    const YASAK = /\bfetch\b|XMLHttpRequest|WebSocket|EventSource|sendBeacon|RTCPeerConnection|RTCDataChannel|importScripts|\bWorker\b|\bglobalThis\s*\[|\bwindow\s*\[|\bself\s*\[|\beval\b|new Function/;
    for (const yol of JS_KAYNAK) {
      if (yol === SINAMA_DOSYASI) continue;
      expect(yorumsuz(oku(yol)), yol).not.toMatch(YASAK);
    }
  });
});

describe("gunluk ve yedek ayarlari", () => {
  it("Capacitor kopru gunlugu kapali (loggingBehavior: none)", () => {
    expect(JSON.parse(oku("capacitor.config.json")).loggingBehavior).toBe("none");
  });

  it("yedekleme kapali (A46)", () => {
    const m = oku("android/app/src/main/AndroidManifest.xml");
    expect(m).toContain('android:allowBackup="false"');
    expect(m).not.toContain('android:allowBackup="true"');
  });

  it("servis ayri surecte calismaz (S1: sayac dosyasina tek surec yazar)", () => {
    expect(oku("android/app/src/main/AndroidManifest.xml")).not.toMatch(/android:process\s*=/);
  });

  it("src/ agacinda console kullanimi yok", () => {
    for (const yol of JS_KAYNAK) expect(yorumsuz(oku(yol)), yol).not.toMatch(/\bconsole\b/);
  });

  it("yerel kodda (Kotlin/Java) gunluk ve yigin izi cagrisi yok", () => {
    expect(YEREL_KAYNAK.length).toBeGreaterThan(5);
    const YASAK = /\bLog\s*\.\s*\w+\s*\(|\bLogger\b|printStackTrace|\bprintln\s*\(|System\s*\.\s*(out|err)|\bTimber\b/;
    for (const yol of YEREL_KAYNAK) expect(yorumsuz(oku(yol)), yol).not.toMatch(YASAK);
  });
});
