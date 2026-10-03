// Hedef kurali (A3, A5, S5): JS ve Kotlin AYNI vektor dosyasini gecer (test/vektor/hedef.tsv).
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { hedefAyir, hedefYazi, ozelAdres, HedefHatasi } from "../src/cekirdek/hedef.js";

function vektorler() {
  const coz = (s) => s.replaceAll("{BOSLUK}", " ").replaceAll("{AT}", "@")
    .replaceAll("{SATIR}", "\n").replaceAll("{TERS}", "\\");
  return readFileSync(new URL("./vektor/hedef.tsv", import.meta.url), "utf8")
    .split("\n").filter((l) => l && !l.startsWith("#"))
    .map((l) => { const [tur, girdi, beklenen] = l.split("\t"); return { tur, girdi: coz(girdi), beklenen }; });
}

function ayirSonuc(girdi, secenek) {
  try {
    const h = hedefAyir(girdi, secenek);
    return `${h.ad}:${h.port}`;
  } catch (e) {
    if (e instanceof HedefHatasi) return `!${e.tur}`;
    throw e;
  }
}

describe("hedef kurali", () => {
  const V = vektorler();

  it("vektor dosyasi dolu (ozel >= 40, ayir >= 45, dongu >= 5)", () => {
    expect(V.filter((v) => v.tur === "ozel").length).toBeGreaterThanOrEqual(40);
    expect(V.filter((v) => v.tur === "ayir").length).toBeGreaterThanOrEqual(45);
    expect(V.filter((v) => v.tur === "dongu").length).toBeGreaterThanOrEqual(5);
  });

  it("ozelAdres: yalniz 10/8, 172.16/12, 192.168/16, 169.254/16 — kati yazim", () => {
    for (const v of V.filter((x) => x.tur === "ozel")) {
      expect(ozelAdres(v.girdi), JSON.stringify(v.girdi)).toBe(v.beklenen === "1");
    }
  });

  it("hedefAyir: ozel IP ve olcum.local kabul; herkese acik IP, baska ad, bozuk yazim ret", () => {
    for (const v of V.filter((x) => x.tur === "ayir")) {
      expect(ayirSonuc(v.girdi), JSON.stringify(v.girdi)).toBe(v.beklenen);
    }
  });

  it("yerel dongu YALNIZ secenekle ve yalniz 127.0.0.1", () => {
    for (const v of V.filter((x) => x.tur === "dongu")) {
      expect(ayirSonuc(v.girdi, { yerelDongu: true }), JSON.stringify(v.girdi)).toBe(v.beklenen);
    }
    expect(ayirSonuc("127.0.0.1")).toBe("!ozel-degil");
    expect(ayirSonuc("127.0.0.1", {})).toBe("!ozel-degil");
  });

  it("metin olmayan girdi bicim hatasi; hedefYazi varsayilan portu yazmaz", () => {
    for (const g of [null, undefined, 5, {}, ["192.168.1.1"]]) expect(ayirSonuc(g)).toBe("!bicim");
    expect(hedefYazi({ ad: "192.168.1.7", port: 80 })).toBe("192.168.1.7");
    expect(hedefYazi({ ad: "192.168.1.7", port: 8080 })).toBe("192.168.1.7:8080");
  });
});
