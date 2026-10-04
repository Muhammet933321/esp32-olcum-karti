// PBKDF2 olcumu: OLCULEN kod saf JS (ortak/) ve sonucu Python hashlib ile bayt bayt ayni.
// Telefonda 20 000 tur 28-44 ms olculdu (kart 764 ms): "hizli ama yanlis" olmadigi burada ve telefonda
// (ekrandaki "dogru" isareti) sabitlenir.
import { describe, it, expect } from "vitest";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { BEKLENEN_20000, SINAMA_PAROLASI, SINAMA_TUZU, pbkdf2Olc } from "../src/cekirdek/olcum.js";

function python(kod) {
  for (const komut of ["python", "python3", "py"]) {
    try { return execFileSync(komut, ["-c", kod], { encoding: "utf8" }).trim(); } catch { /* sonraki */ }
  }
  return null;
}

describe("PBKDF2 olcumu", () => {
  it("20 000 tur: saf JS sonucu sabit basvuru degeriyle ayni ve `dogru` isareti true", () => {
    const o = pbkdf2Olc(20000, { tekrar: 2 });
    expect(o.ozet).toBe(BEKLENEN_20000);
    expect(o.dogru).toBe(true);
    expect(o.sureler.length).toBe(2);
    expect(o.enAz).toBeLessThanOrEqual(o.ortanca);
    expect(o.ortanca).toBeLessThanOrEqual(o.enCok);
  });

  it("basvuru degeri Python hashlib.pbkdf2_hmac'ten (ayni parola + tuz + 20 000 tur + 32 bayt)", () => {
    expect(SINAMA_TUZU).toEqual(new Uint8Array(16));
    const py = python(`import hashlib;print(hashlib.pbkdf2_hmac("sha256", b"${SINAMA_PAROLASI}", bytes(16), 20000, 32).hex())`);
    expect(py, "python bulunamadi").not.toBe(null);
    expect(py).toBe(BEKLENEN_20000);
  });

  it("baska turda sonuc farkli ve `dogru` null (basvuru yok); tur gercekten kullaniliyor", () => {
    const o = pbkdf2Olc(10000, { tekrar: 1 });
    expect(o.dogru).toBe(null);
    expect(o.ozet).not.toBe(BEKLENEN_20000);
    expect(o.ozet).toMatch(/^[0-9a-f]{64}$/);
  });

  it("olculen uygulama saf JS: olcum.js ortak/'tan alir; ortak kripto WebCrypto (subtle) kullanmaz", () => {
    const olcum = readFileSync(new URL("../src/cekirdek/olcum.js", import.meta.url), "utf8");
    expect(olcum).toMatch(/import \{ pbkdf2 \} from "@ortak\/imza\.js";/);
    const kod = (yol) => readFileSync(new URL(yol, import.meta.url), "utf8").split("\n").filter((l) => !/^\s*\/\//.test(l)).join("\n");
    for (const yol of ["../../ortak/src/kripto.js", "../../ortak/src/imza.js"]) expect(kod(yol), yol).not.toMatch(/subtle/);
  });
});
