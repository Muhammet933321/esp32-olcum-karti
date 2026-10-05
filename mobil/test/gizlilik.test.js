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

const yorumsuzXml = (metin) => metin.replace(/<!--[^]*?-->/g, "");

const JS_KAYNAK = agac("src", [".js", ".vue"]);
const YEREL_KAYNAK = agac("android/app/src/main/java", [".kt", ".java"]);
// WebView'in ag yollarini BILEREK deneyen tek dosya (cihazdaki kapi olcumu).
const SINAMA_DOSYASI = "src/cekirdek/web_sinama.js";
// WebRTC arayuzlerini KALDIRAN dosya (adlari liste olarak icerir, cagirmaz).
const RTC_KAPAT_DOSYASI = "src/cekirdek/rtc_kapat.js";
// A24 (5D-3): ham kayit dosyasinin YEREL okunmasi ve arka planda cozulmesi. Uc dosya, her birinin
// icerigi asagida AYRICA ve DAR denetlenir (genel yasaktan muaf, kendi kuralina tabi).
const DEPO_OKU_DOSYASI = "src/cekirdek/depo_oku.js";      // tek `fetch`: yalniz /_depo/<kimlik>/kayitlar.kyt
const ISCI_KUR_DOSYASI = "src/cekirdek/isci_kur.js";      // tek `new Worker`: yalniz paketteki kendi betigimiz
const ISCI_DOSYASI = "src/isci/kayit_isci.js";            // Worker kabugu: `self.onmessage` / `self.postMessage`
const A24_DOSYALARI = [DEPO_OKU_DOSYASI, ISCI_KUR_DOSYASI, ISCI_DOSYASI];

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

  it("WebRTC arayuzleri kaldiriliyor: yerelde belge basinda + JS'te ILK ice aktarim; iki liste ayni", async () => {
    const { RTC_ADLARI, rtcKapat } = await import("../src/cekirdek/rtc_kapat.js");
    const sahte = { RTCPeerConnection: function () {}, webkitRTCPeerConnection: function () {}, RTCDataChannel: function () {} };
    rtcKapat(sahte);
    for (const ad of RTC_ADLARI) {
      expect(sahte[ad], ad).toBe(undefined);
      expect(() => { "use strict"; sahte[ad] = function () {}; }, ad).toThrow();     // geri konamaz
      expect(Object.getOwnPropertyDescriptor(sahte, ad).configurable, ad).toBe(false);
    }
    expect(RTC_ADLARI).toContain("RTCPeerConnection");
    expect(RTC_ADLARI).toContain("webkitRTCPeerConnection");
    // Kotlin listesi ayni adlar.
    const kt = oku("android/app/src/main/java/tr/olcumkarti/mobil/WebKapi.kt");
    const ktAdlar = [.../val RTC_ADLARI = listOf\(([\s\S]*?)\)/.exec(kt)[1].matchAll(/"(\w+)"/g)].map((m) => m[1]);
    expect(ktAdlar).toEqual([...RTC_ADLARI]);
    // Yerel: belge basi betigi KOSULSUZ (yalniz ozellik destegi kosulu) ve her kokene.
    const m = oku("android/app/src/main/java/tr/olcumkarti/mobil/MainActivity.java");
    expect(m).toMatch(/\n {12}WebViewCompat\.addDocumentStartJavaScript\(bridge\.getWebView\(\), WebKapi\.INSTANCE\.getRTC_KAPAT\(\), Collections\.singleton\("\*"\)\);\n/);
    // JS: main.js'in ILK ice aktarimi.
    const ilk = oku("src/main.js").split("\n").find((l) => l.startsWith("import "));
    expect(ilk).toMatch(/^import "\.\/cekirdek\/rtc_kapat\.js";/);
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
    // Kuresel nesnenin ADI da yasak (curutucu 5B C1): `const { fetch: x } = window`, `window["fe" + "tch"]`,
    // `const w = globalThis; w.fetch(...)` gibi dolayli yollar adin kendisi olmadan yazilamaz.
    // (`self-test` gibi tireli sozcuk metindir, ad degil.)
    // Curutucu 5D (Y11, Y12): degiskenden dinamik ice aktarma (`import(url)`), gorsel / ses / oge uzerinden istek
    // (`new Image().src = …`, `createElement`) de yasak. SABIT metinli `import("./x.js")` serbest (paket ici dosya).
    const YASAK = /\bfetch\b|XMLHttpRequest|WebSocket|EventSource|sendBeacon|RTCPeerConnection|RTCDataChannel|importScripts|\bWorker\b|\bglobalThis\b|\bwindow\b|\bself\b(?!-)|\beval\b|new Function|\bImage\b|\bAudio\b|createElement|\.src\s*=|\bimport\s*\((?!\s*["'])/;
    // TEK istisna (5B): ortak/src/imza.js'in bekledigi ortam nesnesinin ANAHTARI. Yalniz su bicim:
    //   { fetch: <ad>Fetch   ya da   { fetch: ag.<ad>Fetch      (deger, KartAg'a giden bir sarmalayici)
    // Cagri, baska bir deger ya da baska bir bicim istisnaya GIRMEZ (asagida kendi sinamasi).
    const ortamAnahtari = (kod) => kod.replace(/\{ fetch: (?:ag\.)?[a-z][A-Za-z]*Fetch\b/g, "{ ORTAM");
    for (const yol of JS_KAYNAK) {
      if (yol === SINAMA_DOSYASI || yol === RTC_KAPAT_DOSYASI || A24_DOSYALARI.includes(yol)) continue;
      expect(ortamAnahtari(yorumsuz(oku(yol))), yol).not.toMatch(YASAK);
    }
    for (const temiz of ["const o = { fetch: imzaliFetch, kaydet };", "ac(c, t, { fetch: ag.kartFetch, simdiMs });",
      'S("WebView ağ sınaması", "WebView network self-test")', "yerelOnbellek(localStorage)",
      'const m = await import("./kayit_veri.js");', "component: () => import('./ekran/Kayit.vue')"]) {
      expect(ortamAnahtari(temiz), temiz).not.toMatch(YASAK);
    }
    for (const kirli of [
      "const o = { fetch: fetch };", "const o = { fetch: window.fetch };", "const o = { fetch };", "fetch(url);",
      "const o = { fetch: (u) => fetch(u) };", "const o = { fetch: globalThis.fetch };", "x = { fetch: ag.kartFetch }; fetch(u);",
      "const o = { fetch: dis.kartFetch };", "const o = { fetch: Fetch };",
      // curutucu 5B C1: yapi bozma ve dolayli erisim — kuresel nesnenin adi olmadan yazilamaz.
      "const { fetch: disFetch } = window; disFetch(u);", "const { fetch: disFetch } = globalThis;", "const { fetch: disFetch } = self;",
      "const w = window; w[ad](u);", "globalThis[\"fe\" + \"tch\"](u);", "self.postMessage(x);",
      "await import(arguman.url);", "import(yol)", "new Image().src = url;", "g.src = adres;", "document.createElement(\"script\")", "new Audio(u)",
    ]) {
      expect(ortamAnahtari(kirli), kirli).toMatch(YASAK);
    }
  });
});

describe("A24: yerel dosya okuma ve Worker — genel yasagin DAR istisnalari", () => {
  // Muaf uc dosyada da: baska ag yolu, dinamik ice aktarma (sabit metinli olsa bile), gorsel / oge istegi YOK.
  const YASAK_DIGER = /XMLHttpRequest|WebSocket|EventSource|sendBeacon|RTCPeerConnection|RTCDataChannel|importScripts|\bglobalThis\b|\bwindow\b|\beval\b|new Function|\bImage\b|\bAudio\b|createElement|\.src\s*=|\bimport\s*\(|\bnavigator\b|\blocation\b/;

  it("uc dosya da kaynak agacinda; baska hicbir dosya muaf degil", () => {
    for (const d of A24_DOSYALARI) expect(JS_KAYNAK, d).toContain(d);
    expect(A24_DOSYALARI.length).toBe(3);
  });

  it("depo_oku.js: TEK fetch, adres bicimi denetlendikten SONRA, cerezsiz ve yonlendirmesiz; baska ag yolu yok", () => {
    const k = yorumsuz(oku(DEPO_OKU_DOSYASI));
    expect(k.match(/\bfetch\b/g).length).toBe(1);
    expect(k).toContain('fetch(url, { cache: "no-store", credentials: "omit", redirect: "error" })');
    expect(k.indexOf("DEPO_ADRESI.test(url)")).toBeGreaterThan(0);
    expect(k.indexOf("DEPO_ADRESI.test(url)")).toBeLessThan(k.indexOf("fetch(url"));
    expect(k).toContain('if (typeof url !== "string" || !DEPO_ADRESI.test(url)) throw new DepoOkuHatasi("bicim");');
    // Kalibin KENDISI sabit (curutucu 5D Y10: seceneklerle genisletilen kalip eski "kotu adres" listesinden geciyordu).
    expect(k).toContain("export const DEPO_ADRESI = /^\\/_depo\\/[0-9a-f]{16}\\/kayitlar\\.kyt$/;");
    expect(k.match(/DEPO_ADRESI/g).length).toBe(2);           // tanim + tek kullanim
    expect(k).not.toMatch(YASAK_DIGER);
    expect(k).not.toMatch(/\bWorker\b|\bself\b/);
    expect(k).not.toMatch(/^import /m);                       // bagimliligi yok: adres baska yerden gelemez
  });

  it("isci_kur.js: TEK Worker, betik paketteki kendi dosyamiz (sabit yol); fetch / self yok", () => {
    const k = yorumsuz(oku(ISCI_KUR_DOSYASI));
    expect(k.match(/\bWorker\b/g).length).toBe(1);
    expect(k).toContain('new Worker(new URL("../isci/kayit_isci.js", import.meta.url), { type: "module" })');
    expect(k).not.toMatch(YASAK_DIGER);
    expect(k).not.toMatch(/\bfetch\b|\bself\b/);
    expect(k).not.toMatch(/^import /m);
  });

  it("kayit_isci.js: self yalniz onmessage / postMessage; fetch YOK (okuma depo_oku.js'ten); Worker kurmaz", () => {
    const k = yorumsuz(oku(ISCI_DOSYASI));
    const selfKullanimlari = k.match(/\bself\b\.?\w*/g);
    expect([...new Set(selfKullanimlari)].sort()).toEqual(["self.onmessage", "self.postMessage"]);
    expect(k).toContain("const islemci = islemciKur({ getir: yerelOku });");
    expect(k).not.toMatch(YASAK_DIGER);
    expect(k).not.toMatch(/\bfetch\b|\bWorker\b/);
    expect(k.match(/^import .*$/gm)).toEqual([
      'import { yerelOku } from "../cekirdek/depo_oku.js";',
      'import { islemciKur } from "../cekirdek/kayit_veri.js";',
    ]);
  });

  it("yerelOku: bicime uymayan adreste istek HIC yapilmaz; uyan adreste TEK istek, govde bayt bayt", async () => {
    const { DEPO_ADRESI, yerelOku } = await import("../src/cekirdek/depo_oku.js");
    const { depoAdresi } = await import("../src/cekirdek/kayit_istemci.js");
    const cagrilar = [];
    const asil = globalThis.fetch;
    let yanit = () => new Response(new Uint8Array([1, 2, 255]), { status: 200 });
    globalThis.fetch = async (...a) => { cagrilar.push(a); return yanit(); };
    try {
      const K = "0123456789abcdef";
      const kotu = [
        null, undefined, 5, "", "/", `/_depo/${K}`, `/_depo/${K}/`, `/_depo/${K}/durum.json`, `/_depo/${K}/kayitlar.kyt?x=1`,
        `/_depo/${K}/kayitlar.kyt#a`, `/_depo/${K}/../${K}/kayitlar.kyt`, "/_depo/../kasa/x", `/_depo/0123456789ABCDEF/kayitlar.kyt`,
        `https://localhost/_depo/${K}/kayitlar.kyt`, `//evil.example/_depo/${K}/kayitlar.kyt`, `http://192.168.1.7/_depo/${K}/kayitlar.kyt`,
        `/_depo/${K}/kayitlar.kyt\n`, ` /_depo/${K}/kayitlar.kyt`, `/_depo/${K}/kayitlarXkyt`, "http://192.168.1.7/kayit/veri",
        "/_capacitor_file_/data/user/0/x/files/kasa/a.bin", `/_capacitor_file_/_depo/${K}/kayitlar.kyt`, "/_capacitor_content_/media/1",
        "http://10.0.0.1/", `http://10.0.0.1/_depo/${K}/kayitlar.kyt`, "https://example.com/", "data:text/plain,x", "blob:https://localhost/1",
      ];
      for (const u of kotu) await expect(yerelOku(u), String(u)).rejects.toMatchObject({ tur: "bicim" });
      expect(cagrilar.length).toBe(0);
      expect([...(await yerelOku(depoAdresi(K)))]).toEqual([1, 2, 255]);
      expect(cagrilar).toEqual([[`/_depo/${K}/kayitlar.kyt`, { cache: "no-store", credentials: "omit", redirect: "error" }]]);
      expect(DEPO_ADRESI.test(depoAdresi(K))).toBe(true);     // istemcinin urettigi adres = okuyucunun kabul ettigi
      yanit = () => new Response(null, { status: 404 });
      expect((await yerelOku(depoAdresi(K))).length).toBe(0);  // henuz esitlenmemis: bos kopya
      for (const kod of [403, 500, 206, 204]) {
        yanit = () => new Response(null, { status: kod });
        await expect(yerelOku(depoAdresi(K)), String(kod)).rejects.toMatchObject({ tur: "okunamadi" });
      }
      globalThis.fetch = async () => { throw new TypeError("gizli yol /data/user/0"); };
      const h = await yerelOku(depoAdresi(K)).catch((e) => e);
      expect(h.tur).toBe("okunamadi");
      expect(h.message).not.toContain("gizli");
    } finally {
      globalThis.fetch = asil;
    }
  });
});

describe("A24: yerel akitmanin MainActivity'ye baglanmasi (curutucu 5D Y13, Y14)", () => {
  it("depo on ekli HER istek depoYaniti'na gider (Capacitor'in dosya sunucusuna BIRAKILMAZ) ve kapi denetiminden SONRA", () => {
    const m = yorumsuz(oku("android/app/src/main/java/tr/olcumkarti/mobil/MainActivity.java"));
    const kapi = m.indexOf("if (!WebKapi.INSTANCE.izinli(request.getUrl().toString())) {");
    const depo = m.indexOf("if (DepoYolu.INSTANCE.depoAdresi(url)) return depoYaniti(url, request.getMethod());");
    const devret = m.indexOf("return super.shouldInterceptRequest(view, request);");
    expect(kapi).toBeGreaterThan(0);
    expect(depo).toBeGreaterThan(kapi);
    expect(devret).toBeGreaterThan(depo);
    expect(m.match(/super\.shouldInterceptRequest/g).length).toBe(1);
  });

  it("dosya yalniz DepoYolu.dosyaKimligi (GET + tam bicim) izin verirse acilir; baska her halde 404", () => {
    const m = yorumsuz(oku("android/app/src/main/java/tr/olcumkarti/mobil/MainActivity.java"));
    expect(m).toContain("String kimlik = DepoYolu.INSTANCE.dosyaKimligi(url, yontem);");
    expect(m).toContain("File dosya = kimlik == null ? null");
    expect(m.match(/new FileInputStream\(/g).length).toBe(1);
    expect(m).toContain("new FileInputStream(dosya)");
    expect(m.match(/, 404, "Yok",/g).length).toBe(2);
    const d = yorumsuz(oku("android/app/src/main/java/tr/olcumkarti/mobil/depo/DepoYolu.kt"));
    expect(d).toContain('fun dosyaKimligi(url: String?, yontem: String?): String? = if (yontem == "GET") kimlik(url) else null');
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

  it("Android 12+: bulut yedegi VE cihazdan cihaza aktarim kurallari her alani disliyor (A46; kasa dosyalari tasinmaz)", () => {
    const m = oku("android/app/src/main/AndroidManifest.xml");
    // allowBackup=false Android 12+ cihazdan cihaza aktarimi ENGELLEMEZ: ayri kural dosyasi gerekir.
    expect(m).toContain('android:dataExtractionRules="@xml/veri_cikarma"');
    expect(m).toContain('android:fullBackupContent="false"');
    const x = yorumsuzXml(oku("android/app/src/main/res/xml/veri_cikarma.xml"));
    const ALANLAR = ["root", "file", "database", "sharedpref", "external"];
    for (const bolum of ["cloud-backup", "device-transfer"]) {
      const b = new RegExp(`<${bolum}[^>]*>([^]*?)</${bolum}>`).exec(x);
      expect(b, bolum).not.toBe(null);
      expect(b[1], bolum).not.toContain("<include");
      const dislanan = [...b[1].matchAll(/<exclude domain="([a-z_]+)" path="([^"]*)"/g)].map((e) => `${e[1]} ${e[2]}`);
      expect(dislanan, bolum).toEqual(ALANLAR.map((a) => `${a} .`));
    }
    expect(x).not.toContain("<include");
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
