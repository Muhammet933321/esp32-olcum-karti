// CURUTUCU 5B — logcat_tara.mjs'in KACIRDIGI sir bicimleri (L1) ve yanlis alarmlari (L2).
import { describe, it, expect } from "vitest";
import { tara } from "../../araclar/logcat_tara.mjs";

const PAROLA = "sinama parolasi #1 ç";                 // bosluk, '#', ASCII disi: gercekci web parolasi
const K_HEX = "00112233445566778899aabbccddeeff102132435465768798a9babbdcddfeef";
const K = Buffer.from(K_HEX, "hex");
const bulundu = (satir) => tara(`10-04 12:00:00.000 1234 1234 D Etiket: ${satir}`, [PAROLA, K_HEX]).some((b) => b.desen.startsWith("sir-"));   // GUCLENDIRILDI: yalniz SIR bulgusu sayilir

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
      "K: bolunmus onaltilik, ikinci satir da logcat onlu": K_HEX.slice(0, 30) + "\n10-04 12:00:00.001 1234 1234 D Etiket: " + K_HEX.slice(30),
      "parola: JSON tirnak kacisli": JSON.stringify(JSON.stringify(PAROLA)),
    };
    const kacan = Object.entries(bicimler).filter(([, s]) => !bulundu(s)).map(([ad]) => ad);
    expect(kacan).toEqual([]);
    // Her bicim YALNIZ dogru sirla bulunur: baska sirlar verilince ayni satirlarda sir bulgusu yok.
    const baska = ["sinama baska parola #2 ş", "ff".repeat(32)];
    for (const [ad, s] of Object.entries(bicimler)) {
      const b = tara(`10-04 12:00:00.000 1234 1234 D Etiket: ${s}`, baska).filter((x) => x.desen.startsWith("sir-"));
      expect(b, ad).toEqual([]);
    }
    // Bolunmus sir ILK satirda, bir kez bildirilir.
    const iki = tara("on\n" + K_HEX.slice(0, 30) + "\n" + K_HEX.slice(30) + "\nson", [K_HEX]).filter((x) => x.desen === "sir-1");
    expect(iki).toEqual([{ satir: 2, desen: "sir-1" }]);
    // Sir bir satirda TAM duruyorsa onceki satirla birlesimi ayrica bildirilmez.
    expect(tara("on\n" + K_HEX, [K_HEX]).filter((x) => x.desen === "sir-1")).toEqual([{ satir: 2, desen: "sir-1" }]);
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
    // DUZELTMEYLE GUCLENDIRILDI: her satir KENDI deseniyle yakalanir (baska bir desenin rastlantisiyla degil).
    const desenler = Object.values(satirlar).map((s) => tara(s).map((b) => b.desen));
    expect(desenler[0]).toContain("gizli-alan");
    expect(desenler[1]).toEqual(["gizli-alan"]);
    expect(desenler[2]).toContain("imza-sorgusu");
    expect(desenler[3]).toEqual(["onaltilik-40-ozet-olabilir"]);
  });

  it("L2: zararsiz satirlar alarm vermemeli", () => {
    // DUZELTMEYLE GUNCELLENDI (bulgu 8): sha256 ozeti alarm vermeye DEVAM eder (guvenli taraf; 64 onaltilik
    // K / imza ile ayirt edilemez) — ama desen ADI bunu soyler.
    expect(tara("PackageManager: digest " + "c0".repeat(32))).toEqual([{ satir: 1, desen: "onaltilik-40-ozet-olabilir" }]);
    const satirlar = {
      "parola yok (iki noktasiz)": "Esles: parola yok",
      "parola yok mesaji": "Esles: parola: yok",
    };
    const alarm = Object.entries(satirlar).filter(([, s]) => tara(s).length > 0).map(([ad]) => ad);
    expect(alarm).toEqual([]);
  });
});
