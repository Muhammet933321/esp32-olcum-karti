// Gunlukte sir yok (A45). Capacitor kopru gunlugu, her eklenti cagrisinin TUM verisini (adres, imza
// basliklari, govde; ileride Kasa'ya giden anahtar) logcat'e yazar — 2026-10-04'te telefonda goruldu:
// `Capacitor: callback: …, pluginId: KartAg, methodName: istek, methodData: {"url": …}`.
// Bu yuzden kopru gunlugu HER derlemede kapali olmali.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";

const oku = (yol) => readFileSync(new URL(yol, import.meta.url), "utf8");

describe("aga cikan tek yol KartAg (WebView kapisi)", () => {
  const csp = /http-equiv="Content-Security-Policy" content="([^"]+)"/.exec(oku("../index.html"))[1];
  const yonerge = Object.fromEntries(csp.split(";").map((y) => y.trim().split(/ +/)).map(([ad, ...d]) => [ad, d]));

  it("CSP: her kaynak turu yalniz paket; baglanti/cerceve/nesne/form/taban disari KAPALI", () => {
    expect(yonerge["default-src"]).toEqual(["'self'"]);
    expect(yonerge["script-src"]).toEqual(["'self'"]);
    expect(yonerge["connect-src"]).toEqual(["'self'"]);
    expect(yonerge["frame-src"]).toEqual(["'none'"]);
    expect(yonerge["object-src"]).toEqual(["'none'"]);
    expect(yonerge["base-uri"]).toEqual(["'none'"]);
    expect(yonerge["form-action"]).toEqual(["'none'"]);
    expect(yonerge["img-src"]).toEqual(["'self'", "data:", "blob:"]);
    // Hicbir yonergede sema/alan joker'i, http(s) kaynagi ya da unsafe-eval yok.
    expect(csp).not.toMatch(/\*|https?:|unsafe-eval/);
    for (const [ad, d] of Object.entries(yonerge)) if (ad !== "style-src") expect(d, ad).not.toContain("'unsafe-inline'");
  });

  it("yerel kapi: MainActivity her istegi ve gezintiyi WebKapi'den geciriyor; cerez yoneticisi kaldirilmis", () => {
    const m = oku("../android/app/src/main/java/tr/olcumkarti/mobil/MainActivity.java");
    const kesit = (ad) => m.slice(m.indexOf(ad), m.indexOf("}", m.indexOf("return super." + ad)));
    for (const ad of ["shouldInterceptRequest", "shouldOverrideUrlLoading"]) {
      expect(m.indexOf("return super." + ad), ad).toBeGreaterThan(0);
      expect(kesit(ad), ad).toContain("if (!WebKapi.INSTANCE.izinli(request.getUrl().toString()))");
    }
    expect(m).toContain("bridge.setWebViewClient(");
    expect(m).toContain("CookieHandler.setDefault(null);");
    expect(m.indexOf("CookieHandler.setDefault(null);")).toBeGreaterThan(m.indexOf("super.onCreate("));
  });

  it("Capacitor: disari gezinti izni yok, karisik icerik yok, WebView hata ayiklamasi kapali", () => {
    const k = JSON.parse(oku("../capacitor.config.json"));
    expect(k.server?.allowNavigation ?? []).toEqual([]);
    expect(k.android.allowMixedContent).toBe(false);
    expect(k.android.webContentsDebuggingEnabled).toBe(false);
  });

  it("uretim kodunda WebView'in kendi ag cagrisi yok (fetch/XHR/WebSocket/EventSource yalniz sinama dosyasinda)", () => {
    for (const yol of ["../src/cekirdek/ag.js", "../src/cekirdek/kesif.js", "../src/cekirdek/hedef.js", "../src/cekirdek/eklenti.js", "../src/ekran/KartBul.vue", "../src/main.js", "../src/App.vue"]) {
      expect(oku(yol), yol).not.toMatch(/\bfetch\(|XMLHttpRequest|WebSocket|EventSource|sendBeacon/);
    }
  });
});

describe("gunluk ve yedek ayarlari", () => {
  it("Capacitor kopru gunlugu kapali (loggingBehavior: none)", () => {
    expect(JSON.parse(oku("../capacitor.config.json")).loggingBehavior).toBe("none");
  });

  it("yedekleme kapali (A46)", () => {
    const m = oku("../android/app/src/main/AndroidManifest.xml");
    expect(m).toContain('android:allowBackup="false"');
    expect(m).not.toContain('android:allowBackup="true"');
  });

  it("servis ayri surecte calismaz (S1: sayac dosyasina tek surec yazar)", () => {
    expect(oku("../android/app/src/main/AndroidManifest.xml")).not.toMatch(/android:process\s*=/);
  });

  it("uretim kodunda console.* ve Log.* cagrisi yok (gunluk yalniz Gunluk sarmalayicisindan)", () => {
    for (const yol of ["../src/cekirdek/ag.js", "../src/cekirdek/kesif.js", "../src/cekirdek/hedef.js", "../src/ekran/KartBul.vue"]) {
      expect(oku(yol), yol).not.toMatch(/console\.(log|info|warn|error|debug)/);
    }
    for (const yol of ["ag/KartAgPlugin.kt", "ag/HttpIstek.kt", "ag/Hedef.kt", "kesif/KesifPlugin.kt"]) {
      expect(oku(`../android/app/src/main/java/tr/olcumkarti/mobil/${yol}`), yol).not.toMatch(/\bLog\.[a-z]\(|println\(/);
    }
  });
});
