// TAKLIT kart: parolayi BILMEYEN saldirganin karti. Istemcinin kanitini denetlemeden kabul eder ve
// bir "kart kaniti" doner. `kanitDogru: false` (gercek saldirgan): kanit rastgele — istemci bunu
// reddetmeli ve cihazi SAKLAMAMALI. `kanitDogru: true` yalniz testin kendini sinamasi icindir
// (mutasyon): o zaman taklit parolayi biliyormus gibi dogru kaniti hesaplar ve eslestirme GECER;
// yani testi kirmizi yapan tek sey kart kanitinin degeridir.
import http from "node:http";
import { randomBytes } from "node:crypto";
import { kanitKart, pbkdf2 } from "../sahte-kart/imza_dogrula.mjs";

export function taklitKartAc({ kimlik = "0123456789abcdef", parola = "", tur = 10000, kanitDogru = false, port = 0 } = {}) {
  const tuz = randomBytes(16), acilis = randomBytes(16).toString("hex"), nk = randomBytes(16);
  const durum = { kanitIstegi: 0, imzali: 0 };
  let nc = Buffer.alloc(16);
  const sunucu = http.createServer((istek, yanit) => {
    const u = new URL(istek.url, "http://x");
    const json = (n) => { const g = JSON.stringify(n); yanit.writeHead(200, { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(g) }); yanit.end(g); };
    istek.resume();
    if (istek.headers["x-imza"] !== undefined) durum.imzali += 1;
    if (u.pathname === "/eslestir/bilgi") return json({ surum: "OK1", kimlik, acilis, tuz: tuz.toString("hex"), tur, zorunlu: 0, misafir: 0, saat: 1, cihaz_azami: 8 });
    if (u.pathname === "/eslestir/baslat") { nc = Buffer.from(u.searchParams.get("nc") || "", "hex"); return json({ eno: 1, nk: nk.toString("hex") }); }
    if (u.pathname === "/eslestir/kanit") {
      durum.kanitIstegi += 1;
      const kanit = kanitDogru ? kanitKart(pbkdf2(parola, tuz, tur), kimlik, nk, nc, 1) : randomBytes(32);
      return json({ n: 1, kart_kanit: kanit.toString("hex") });
    }
    yanit.writeHead(404);
    yanit.end();
  });
  return new Promise((coz) => {
    sunucu.listen(port, "127.0.0.1", () => coz({
      port: sunucu.address().port, durum,
      kapat: () => new Promise((c) => { sunucu.closeAllConnections(); sunucu.close(c); }),
    }));
  });
}
