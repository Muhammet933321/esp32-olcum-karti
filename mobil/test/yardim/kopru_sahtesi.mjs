// Kotlin KartAg eklentisinin Node'daki sahtesi: ayni cagri bicimi ({url, yontem, basliklar, govde(base64),
// zamanAsimiMs, azamiGovde} -> {kod, basliklar, govde(base64), adres}); istegi node:http ile YALNIZ
// 127.0.0.1'e yollar. Hata, eklenti gibi `code` = tur ile atilir.
import http from "node:http";

function hata(tur) {
  const e = new Error(tur);
  e.code = tur;
  return e;
}

export function kopruSahtesi() {
  const cagrilar = [];
  async function istek(c) {
    cagrilar.push(c);
    const u = new URL(c.url);
    if (u.hostname !== "127.0.0.1") throw hata("baglanti");      // testler baska yere GITMEZ
    const govde = c.govde ? Buffer.from(c.govde, "base64") : null;
    return new Promise((coz, reddet) => {
      const basliklar = { ...c.basliklar };
      if (govde) basliklar["Content-Length"] = String(govde.length);
      const r = http.request({ host: u.hostname, port: u.port, path: u.pathname + u.search, method: c.yontem, headers: basliklar }, (y) => {
        const parcalar = [];
        let boy = 0;
        y.on("data", (p) => {
          parcalar.push(p);
          boy += p.length;
          if (boy > c.azamiGovde) { r.destroy(); reddet(hata("govde-buyuk")); }
        });
        y.on("end", () => {
          const bas = {};
          for (const [a, d] of Object.entries(y.headers)) bas[a.toLowerCase()] = Array.isArray(d) ? d[0] : d;
          coz({ kod: y.statusCode, basliklar: bas, govde: Buffer.concat(parcalar).toString("base64"), adres: u.host });
        });
        y.on("error", () => reddet(hata("baglanti")));
      });
      r.setTimeout(c.zamanAsimiMs, () => { r.destroy(); reddet(hata("zaman-asimi")); });
      r.on("error", () => reddet(hata("baglanti")));
      if (govde) r.write(govde);
      r.end();
    });
  }
  return { istek, cagrilar };
}
