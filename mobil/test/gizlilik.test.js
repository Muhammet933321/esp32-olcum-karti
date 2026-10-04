// Gunlukte sir yok (A45). Capacitor kopru gunlugu, her eklenti cagrisinin TUM verisini (adres, imza
// basliklari, govde; ileride Kasa'ya giden anahtar) logcat'e yazar — 2026-10-04'te telefonda goruldu:
// `Capacitor: callback: …, pluginId: KartAg, methodName: istek, methodData: {"url": …}`.
// Bu yuzden kopru gunlugu HER derlemede kapali olmali.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";

const oku = (yol) => readFileSync(new URL(yol, import.meta.url), "utf8");

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
