// KartDepo eklentisinin (android/.../depo/KartDepoPlugin.kt + KartDepo.kt) Node sahtesi: AYNI yontem
// adlari, AYNI girdi / cikti bicimi (bayt = base64, hata = { code: tur }), AYNI sinirlar — gercek
// dosyalarla (verilen dizinde). JS testleri ve duman testi bunu kullanir; Kotlin tarafi JVM'de ayrica sinanir.
//
//   const e = depoSahtesi(dizin, { simdi: () => new Date(...) });
//   e.cagrilar            // [ad, veri] dizisi (testin gozlemi)
//   e.bozDurum(kimlik, b) // durum.json'a ham bayt yaz (bozuk dosya senaryosu)
import { existsSync, mkdirSync, readFileSync, readdirSync, renameSync, rmSync, statSync, truncateSync, writeFileSync, appendFileSync } from "node:fs";
import { join } from "node:path";

const KIMLIK = /^[0-9a-f]{16}$/;
const AZAMI = 1 << 20;
const DOSYA = "kayitlar.kyt", DURUM = "durum.json", KAL = "kalibrasyon.json";

class Red extends Error {
  constructor(tur) { super(tur); this.code = tur; }
}

export function depoSahtesi(kok, { simdi = () => new Date() } = {}) {
  const cagrilar = [];
  const dizin = (kimlik) => {
    if (typeof kimlik !== "string" || !KIMLIK.test(kimlik)) throw new Red("bicim");
    return join(kok, kimlik);
  };
  const hazir = (kimlik) => { const d = dizin(kimlik); mkdirSync(d, { recursive: true }); return d; };
  const coz = (s) => {
    if (typeof s !== "string" || !/^[A-Za-z0-9+/]*={0,2}$/.test(s) || s.length % 4 !== 0) throw new Red("bicim");
    return Buffer.from(s, "base64");
  };
  const tam = (v) => { if (!Number.isInteger(v) || v < 0) throw new Red("bicim"); return v; };
  const ver = (b) => (b === null ? { var: false } : { veri: Buffer.from(b).toString("base64"), var: true });
  const kucukOku = (yol) => (existsSync(yol) ? readFileSync(yol) : null);
  const atomik = (yol, b) => {
    if (b.length > AZAMI) throw new Red("bicim");
    writeFileSync(yol + ".gecici", b);
    renameSync(yol + ".gecici", yol);
  };
  const boy = (kimlik) => { const f = join(dizin(kimlik), DOSYA); return existsSync(f) ? statSync(f).size : 0; };
  const iki = (n) => String(n).padStart(2, "0");

  const yontem = {
    veriBoyu: ({ kimlik }) => ({ boy: boy(kimlik) }),
    veriOku: ({ kimlik, bas, azami }) => {
      tam(bas);
      if (!Number.isInteger(azami) || azami < 1 || azami > AZAMI) throw new Red("bicim");
      const f = join(dizin(kimlik), DOSYA);
      if (!existsSync(f)) return ver(Buffer.alloc(0));
      return ver(readFileSync(f).subarray(bas, bas + azami));
    },
    veriEkle: ({ kimlik, veri }) => {
      const b = coz(veri);
      if (b.length > AZAMI) throw new Red("bicim");
      appendFileSync(join(hazir(kimlik), DOSYA), b);
      return { boy: boy(kimlik) };
    },
    veriKirp: ({ kimlik, boy: n }) => {
      tam(n);
      const f = join(hazir(kimlik), DOSYA);
      if (!existsSync(f)) writeFileSync(f, Buffer.alloc(0));
      truncateSync(f, n);
      return {};
    },
    durumOku: ({ kimlik }) => ver(kucukOku(join(dizin(kimlik), DURUM))),
    durumYaz: ({ kimlik, veri }) => { atomik(join(hazir(kimlik), DURUM), coz(veri)); return {}; },
    kalOku: ({ kimlik }) => ver(kucukOku(join(dizin(kimlik), KAL))),
    kalYaz: ({ kimlik, veri }) => { atomik(join(hazir(kimlik), KAL), coz(veri)); return {}; },
    kalArsivle: ({ kimlik, veri }) => {
      const d = hazir(kimlik), t = simdi();
      const kokAd = `kalibrasyon-${t.getFullYear()}${iki(t.getMonth() + 1)}${iki(t.getDate())}-${iki(t.getHours())}${iki(t.getMinutes())}${iki(t.getSeconds())}`;
      let ad = `${kokAd}.json`;
      for (let n = 1; existsSync(join(d, ad)); n++) ad = `${kokAd}-${n}.json`;
      atomik(join(d, ad), coz(veri));
      return { ad };
    },
    sifirla: ({ kimlik }) => { rmSync(dizin(kimlik), { recursive: true, force: true }); return {}; },
    boyutlar: ({ kimlik }) => {
      const d = dizin(kimlik);
      const adlar = existsSync(d) ? readdirSync(d) : [];
      return {
        veri: boy(kimlik),
        toplam: adlar.reduce((t, a) => t + statSync(join(d, a)).size, 0),
        arsiv: adlar.filter((a) => a.startsWith("kalibrasyon-") && a.endsWith(".json")).length,
      };
    },
  };

  const e = { cagrilar };
  for (const [ad, fn] of Object.entries(yontem)) {
    e[ad] = async (veri) => {
      cagrilar.push([ad, veri]);
      return fn(veri || {});
    };
  }
  e.bozDurum = (kimlik, b) => writeFileSync(join(hazir(kimlik), DURUM), b);
  e.dosya = (kimlik, ad = DOSYA) => { const f = join(dizin(kimlik), ad); return existsSync(f) ? readFileSync(f) : null; };
  return e;
}
