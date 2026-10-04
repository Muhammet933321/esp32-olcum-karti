// CURUTUCU 5B — logcat_tara.mjs'in KACIRDIGI sir bicimleri (L1) ve yanlis alarmlari (L2).
import { describe, it, expect } from "vitest";
import { tara } from "../../araclar/logcat_tara.mjs";

const PAROLA = "sinama parolasi #1 ç";                 // bosluk, '#', ASCII disi: gercekci web parolasi
const K_HEX = "00112233445566778899aabbccddeeff102132435465768798a9babbdcddfeef";
const K = Buffer.from(K_HEX, "hex");
const bulundu = (satir) => tara(`10-04 12:00:00.000 1234 1234 D Etiket: ${satir}`, [PAROLA, K_HEX]).length > 0;

describe("curutucu 5B: logcat tarayicisi", () => {
  it("L1: bilinen sir (--sir) su bicimlerde de bulunmali", () => {
    const hexBosluklu = K_HEX.match(/../g).join(" ");
    const bicimler = {
      "K: Kotlin contentToString (isaretli ondalik)": "[" + Array.from(K, (b) => (b > 127 ? b - 256 : b)).join(", ") + "]",
      "K: JS Uint8Array dokumu (ondalik)": Array.from(K).join(","),
      "K: bosluklu onaltilik": hexBosluklu,
      "K: iki noktali onaltilik": K_HEX.match(/../g).join(":"),
      "K: 0x onekli": K_HEX.match(/../g).map((x) => "0x" + x).join(", "),
      "K: 76 sutunda bolunmus base64 (iki satir)": K.toString("base64").slice(0, 20) + "\n" + K.toString("base64").slice(20),
      "parola: URL kodlu": encodeURIComponent(PAROLA),
      "parola: form kodlu (+)": encodeURIComponent(PAROLA).replace(/%20/g, "+"),
      "parola: JSON kacisli (\\u00e7)": JSON.stringify(PAROLA).replace("ç", "\\u00e7"),
      "parola: UTF-16LE onaltilik": Buffer.from(PAROLA, "utf16le").toString("hex"),
    };
    const kacan = Object.entries(bicimler).filter(([, s]) => !bulundu(s)).map(([ad]) => ad);
    expect(kacan).toEqual([]);
  });

  it("L1b: --sir VERILMEDEN, desenler su satirlari yakalamali", () => {
    const satirlar = {
      "K base64 (anahtar alani)": `anahtar=${K.toString("base64")}`,
      "sifre sozcugu": "sifre=sinama-deger-123456",
      "imza sorgusu satir basinda": "_i=" + "ab".repeat(20),
      "63 onaltilik (kirpilmis imza)": "imza " + K_HEX.slice(0, 63),
    };
    const kacan = Object.entries(satirlar).filter(([, s]) => tara(s).length === 0).map(([ad]) => ad);
    expect(kacan).toEqual([]);
  });

  it("L2: zararsiz satirlar alarm vermemeli", () => {
    const satirlar = {
      "APK ozeti (sha256)": "PackageManager: digest " + "c0".repeat(32),
      "parola yok mesaji": "Esles: parola: yok",
    };
    const alarm = Object.entries(satirlar).filter(([, s]) => tara(s).length > 0).map(([ad]) => ad);
    expect(alarm).toEqual([]);
  });
});
