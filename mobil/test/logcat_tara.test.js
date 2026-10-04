// araclar/logcat_tara.mjs — logcat sir tarayicisi (A45, kullanici sarti): her desen ailesi kirli
// satirda KIRMIZI, gercekci temiz satirlar yesil, bulunan DEGER ciktiya yazilmaz.
import { describe, it, expect } from "vitest";
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { DESENLER, metinCoz, tara } from "../araclar/logcat_tara.mjs";

const ARAC = fileURLToPath(new URL("../araclar/logcat_tara.mjs", import.meta.url));
const ON = "10-04 11:20:31.123  4321  4321 I Capacitor: ";
const HEX64 = "9f".repeat(32);
const KIMLIK = "00112233aabbccdd";
const SIR = "sinama-gizli-parola-77";

const adlar = (bulgular) => bulgular.map((b) => b.desen);

const KIRLI = {
  "imza-basligi": [`${ON}basliklar {"X-Imza":"kisa"}`, `${ON}x-sayac: 1790000000000`, `${ON}X-Cihaz=3`],
  "imza-sorgusu": [`${ON}GET /akis?_c=1&_s=1790000000001`, `${ON}/akis?x=1&_i=ab`],
  "onaltilik-64": [`${ON}anahtar ${HEX64}`, `${ON}${HEX64.toUpperCase()}`, `${ON}uzun ${"0a".repeat(40)} son`],
  kanit: [`${ON}POST /eslestir/kanit?eno=1&kanit=kisa`, `${ON}{"kart_kanit": "kisa"}`],
  parola: [`${ON}parola=birsey`, `${ON}{"password": "x"}`, `${ON}Parola : deger`, `${ON}webParola="q"`],
  "kopru-gunlugu": [`10-04 11:20:31.123  4321  4321 V Capacitor/Plugin: To native (Capacitor plugin): callbackId: 9, pluginId: Kasa, methodName: anahtarYaz, methodData: {}`],
  "kart-kimligi": [`${ON}kimlik ${KIMLIK}`, `${ON}{"kimlik":"${KIMLIK}"}`, `${ON}beklenenKimlik=${KIMLIK}`],
  "ozel-adres-yolu": [`${ON}http://192.168.1.20/eslestir/bilgi`, `${ON}10.0.0.7:8080/komut`, `${ON}GET 172.20.3.4/kayit/liste`],
};

const TEMIZ = [
  "10-04 11:20:30.001  4321  4321 D Capacitor: Starting BridgeActivity",
  "10-04 11:20:30.120  4321  4321 D Capacitor: Loading app at https://localhost",
  "10-04 11:20:30.455  4321  4366 I chromium: [INFO:CONSOLE(1)] \"\", source: https://localhost/assets/index-C1a2b3c4.js (1)",
  "10-04 11:20:30.460  4321  4321 W cr_AwContents: Application attempted to call on a destroyed WebView",
  "10-04 11:20:31.000  4321  4321 I tr.olcumkarti.mobil: Compiler allocated 4219KB to compile void android.view.ViewRootImpl.performTraversals()",
  "10-04 11:20:31.500  4321  4380 D OpenGLRenderer: endAllActiveAnimators on 0xb400007a3c5d1200 (RippleDrawable) with handle 0xb4000079ec8a6de0",
  "10-04 11:20:32.000  4321  4321 I Choreographer: Skipped 31 frames!  The application may be doing too much work on its main thread.",
  // Uzun ondalik sayilar, 32 onaltilik (acilis degeri gibi; sir degil), zaman damgalari
  "10-04 11:20:32.100  4321  4321 D gralloc4: id 1790000000000123456789 boyut 12345678901234567890123456789012",
  `10-04 11:20:32.200  4321  4321 D x: ozet ${"ab".repeat(16)} tamam`,
  // Kimlik sozcugu ama 16 onaltilik degil; 16 onaltilik ama kimlik sozcugu yok
  "10-04 11:20:32.300  4321  4321 D x: kimlik dogrulandi",
  `10-04 11:20:32.400  4321  4321 D x: handle ${KIMLIK}`,
  // Ozel adres ama kart yolu degil; kart yolu ama ozel adres degil
  "10-04 11:20:32.500  4321  4321 D ConnectivityService: gateway 192.168.1.1 dns 192.168.1.1",
  "10-04 11:20:32.600  4321  4321 D x: /kayit ekrani acildi",
  // 'password' sozcugu deger olmadan
  "10-04 11:20:32.700  4321  4321 I InputMethodManager: startInput: password field focused",
  "10-04 11:20:32.800  4321  4321 I x: parola alani temizlendi",
  "",
].join("\n");

describe("logcat_tara: tara()", () => {
  it("her desen ailesinin her kirli satiri kendi adiyla bulunur", () => {
    expect(Object.keys(KIRLI).sort()).toEqual(DESENLER.map((d) => d.ad).sort());
    for (const [ad, satirlar] of Object.entries(KIRLI)) {
      for (const s of satirlar) expect(adlar(tara(s)), s).toContain(ad);
    }
  });

  it("gercekci temiz logcat: bulgu yok", () => {
    expect(tara(TEMIZ)).toEqual([]);
  });

  it("satir numarasi 1'den baslar; bulgu nesnesi degeri TASIMAZ", () => {
    const b = tara(`${TEMIZ}\n${ON}anahtar ${HEX64}\n`);
    expect(b).toEqual([{ satir: TEMIZ.split("\n").length + 1, desen: "onaltilik-64" }]);
  });

  it("--sir: duz, onaltilik ve base64 bicimleri (gomulu hizalamalar dahil)", () => {
    const b = Buffer.from(SIR, "utf8");
    const bicimler = {
      duz: `${ON}deger ${SIR} son`,
      hex: `${ON}${b.toString("hex")}`,
      HEX: `${ON}${b.toString("hex").toUpperCase()}`,
      base64: `${ON}${b.toString("base64")}`,
      "base64 url": `${ON}${b.toString("base64url")}`,
      "gomulu +1": `${ON}${Buffer.concat([Buffer.from("x"), b, Buffer.from("yz")]).toString("base64")}`,
      "gomulu +2": `${ON}${Buffer.concat([Buffer.from("xy"), b, Buffer.from("z")]).toString("base64")}`,
      "gomulu +3": `${ON}${Buffer.concat([Buffer.from("xyz"), b]).toString("base64")}`,
    };
    for (const [ad, satir] of Object.entries(bicimler)) {
      expect(adlar(tara(satir, [SIR])), ad).toContain("sir-1");
      expect(adlar(tara(satir, ["baska-sinama-sirri"])), ad).not.toContain("sir-1");
    }
    expect(tara(TEMIZ, [SIR])).toEqual([]);
  });

  it("--sir onaltilik verilmisse (K gibi) HAM baytlarin base64'u de aranir (Kasa'ya giden bicim)", () => {
    const K = Buffer.from(Array.from({ length: 32 }, (_, i) => (i * 37 + 11) & 0xff));
    const satir = `${ON}{"anahtar":"${K.toString("base64")}"}`;
    expect(adlar(tara(satir, [K.toString("hex")]))).toContain("sir-1");
    expect(adlar(tara(satir, [K.toString("hex").toUpperCase()]))).toContain("sir-1");
    expect(tara(satir, ["00".repeat(32)])).toEqual([]);
    // base64url alfabesi ('-' ve '_'): standart yazimda '+' ve '/' iceren bir anahtar da bulunur.
    const K2 = Buffer.from(Array.from({ length: 32 }, (_, i) => (i % 2 ? 0xff : 0xfb)));
    const url = K2.toString("base64url");
    expect(url).toMatch(/[-_]/);
    expect(K2.toString("base64")).toMatch(/[+/]/);
    expect(adlar(tara(`${ON}{"anahtar":"${url}"}`, [K2.toString("hex")]))).toContain("sir-1");
  });

  it("metinCoz: UTF-16 (PowerShell yonlendirmesi) dosyasi da okunur", () => {
    const satir = `${ON}anahtar ${HEX64}\n`;
    const le = Buffer.concat([Buffer.from([0xff, 0xfe]), Buffer.from(satir, "utf16le")]);
    expect(adlar(tara(metinCoz(le)))).toEqual(["onaltilik-64"]);
    expect(adlar(tara(metinCoz(Buffer.from(satir, "utf16le"))))).toEqual(["onaltilik-64"]);       // BOM'suz
    expect(adlar(tara(metinCoz(Buffer.from(satir, "utf8"))))).toEqual(["onaltilik-64"]);
  });
});

describe("logcat_tara: komut satiri", () => {
  function kos(icerik, ...ek) {
    const dizin = mkdtempSync(join(tmpdir(), "logcat-"));
    try {
      const dosya = join(dizin, "logcat.txt");
      writeFileSync(dosya, icerik);
      const s = spawnSync(process.execPath, [ARAC, dosya, ...ek], { encoding: "utf8" });
      return { kod: s.status, cikti: s.stdout + s.stderr };
    } finally {
      rmSync(dizin, { recursive: true, force: true });
    }
  }

  it("temiz dosya: cikis 0", () => {
    expect(kos(TEMIZ).kod).toBe(0);
    expect(kos(TEMIZ, "--sir", SIR).kod).toBe(0);
  });

  it("kirli dosya: cikis 1; satir numarasi + desen ADI yazilir, DEGER yazilmaz", () => {
    const kirli = `${TEMIZ}\n${ON}anahtar ${HEX64}\n${ON}kimlik ${KIMLIK}\n${ON}deger ${SIR}\n${ON}parola=cok-ozel-sinama\n`;
    const r = kos(kirli, "--sir", SIR);
    expect(r.kod).toBe(1);
    const n = TEMIZ.split("\n").length;
    expect(r.cikti).toContain(`satir ${n + 1}: onaltilik-64`);
    expect(r.cikti).toContain(`satir ${n + 2}: kart-kimligi`);
    expect(r.cikti).toContain(`satir ${n + 3}: sir-1`);
    expect(r.cikti).toContain(`satir ${n + 4}: parola`);
    for (const deger of [HEX64, KIMLIK, SIR, "cok-ozel-sinama", "anahtar"]) expect(r.cikti, deger).not.toContain(deger);
  });

  it("kullanim hatasi: dosya yok / dosya adi yok / cok kisa sir -> cikis 2 (temiz SAYILMAZ)", () => {
    expect(spawnSync(process.execPath, [ARAC], { encoding: "utf8" }).status).toBe(2);
    expect(spawnSync(process.execPath, [ARAC, join(tmpdir(), "boyle-bir-logcat-yok.txt")], { encoding: "utf8" }).status).toBe(2);
    expect(kos(TEMIZ, "--sir", "abc").kod).toBe(2);
    expect(kos(TEMIZ, "--sir").kod).toBe(2);
    expect(kos("").kod).toBe(2);                         // bos logcat: olcum yapilmamis demektir
  });
});
