// CURUTUCU 5B — kasa_sahtesi.mjs ile GERCEK Kotlin KasaKomut ayni girdide ayni sonucu vermeli.
// KOTLIN sutunu `bash test/curutucu-5b/kotlin/derle.sh <dizin>` ciktisindan (2026-10-04, JVM) aynen alindi.
import { describe, it, expect } from "vitest";
import { kasaKur } from "../../src/cekirdek/kasa.js";
import { kasaDiski, kasaSahtesi } from "../yardim/kasa_sahtesi.mjs";

const K1 = "00112233aabbccdd", K2 = "ffeeddcc99887766";
const A44 = Buffer.from(Uint8Array.from({ length: 32 }, (_, i) => i)).toString("base64");
const A43 = A44.replace(/=+$/, "");
const tur = async (soz) => { try { await soz; return "tamam"; } catch (e) { return e.code || e.tur || "BASKA"; } };

const KOTLIN = {
  ad25: "bicim", ad24: "tamam", adTurkce13: "bicim", dolguFazla: "bicim", dolgusuz: "tamam",
  isaret19: "bicim", isaretBasSifir: "tamam", listeIlk: K1, esitYazim: "tamam", kucukYazim: "geri",
};

describe("curutucu 5B: kasa sahtesi <-> Kotlin KasaKomut", () => {
  it("A1: ayni girdide ayni tur / sonuc", async () => {
    const ek = kasaSahtesi(kasaDiski());
    const sahte = {};
    sahte.ad25 = await tur(ek.anahtarYaz({ kimlik: K1, n: 1, ad: "a".repeat(25), anahtar: A44 }));
    sahte.ad24 = await tur(ek.anahtarYaz({ kimlik: K1, n: 1, ad: "a".repeat(24), anahtar: A44 }));
    sahte.adTurkce13 = await tur(ek.anahtarYaz({ kimlik: K1, n: 1, ad: "ç".repeat(13), anahtar: A44 }));
    sahte.dolguFazla = await tur(ek.anahtarYaz({ kimlik: K1, n: 1, ad: "x", anahtar: A43 + "==" }));
    sahte.dolgusuz = await tur(ek.anahtarYaz({ kimlik: K1, n: 1, ad: "x", anahtar: A43 }));
    sahte.isaret19 = await tur(ek.sayacYaz({ kimlik: K1, isaret: "9999999999999999999" }));
    const ek2 = kasaSahtesi(kasaDiski());
    sahte.isaretBasSifir = await tur(ek2.sayacYaz({ kimlik: K1, isaret: "0005" }));
    await ek2.anahtarYaz({ kimlik: K2, n: 2, ad: "iki", anahtar: A44 });
    await ek2.anahtarYaz({ kimlik: K1, n: 1, ad: "bir", anahtar: A44 });
    sahte.listeIlk = (await ek2.liste()).kayitlar[0].kimlik;
    await ek2.sayacYaz({ kimlik: K1, isaret: "5000" });
    sahte.esitYazim = await tur(ek2.sayacYaz({ kimlik: K1, isaret: "5000" }));
    sahte.kucukYazim = await tur(ek2.sayacYaz({ kimlik: K1, isaret: "4999" }));
    expect(sahte).toEqual(KOTLIN);
  });

  it("A2: kasa.js cihazSakla, gercek eklentinin reddedecegi adi (25+ UTF-8 bayt) kendisi reddetmeli", async () => {
    // Sahte kabul ettigi icin kasa.test.js bunu goremez; telefonda eklenti 'bicim' doner.
    const kasa = kasaKur(kasaSahtesi(kasaDiski()));
    const cihaz = { kimlik: K1, n: 1, K: new Uint8Array(32).fill(7), ad: "ç".repeat(13), sayac: 0, acilis: "ab".repeat(16) };
    expect(await tur(kasa.cihazSakla(cihaz))).toBe("bicim");
  });
});
