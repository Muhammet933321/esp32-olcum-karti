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
  // ── akis (5C-1): Kotlin `akisAc` / `akisKapat` + "akis" / "akisDurum" olaylarinin taklidi ──────────
  // Kotlin tarafiyla AYNI kurallar (Akis.kt, SseAyirici.kt): yalniz varsayilan olayin `data:` satirlari
  // tasinir; `kimlik` olayi (jeton!), `id:`, `retry:`, yorum tasinmaz; `event: dolu` -> hal "dolu";
  // satir > 4096 bayt atilir; her akis TEK bitis olayi verir (kapandi | dolu | hata).
  const akisCagrilari = [];
  const dinleyiciler = { akis: new Set(), akisDurum: new Set() };
  const akislar = new Map();
  let akisNo = 0;
  const yay = (olay, veri) => { for (const fn of [...dinleyiciler[olay]]) fn(veri); };

  function addListener(olay, fn) {
    if (!dinleyiciler[olay]) throw hata("bicim");
    dinleyiciler[olay].add(fn);
    return Promise.resolve({ remove: async () => { dinleyiciler[olay].delete(fn); } });
  }

  async function akisAc(c) {
    akisCagrilari.push(c);
    const u = new URL(c.url);
    if (u.hostname !== "127.0.0.1") throw hata("baglanti");      // testler baska yere GITMEZ
    if (u.pathname !== "/akis") throw hata("bicim");
    const kimlik = `a${++akisNo}`;
    const a = { bitti: false, istek: null };
    akislar.set(kimlik, a);
    const bitir = (hal, ek = {}) => {
      if (a.bitti) return;
      a.bitti = true;
      yay("akisDurum", { kimlik, hal, ...ek });
    };
    a.bitir = bitir;
    a.istek = http.request({
      host: u.hostname, port: u.port, path: u.pathname + u.search, method: "GET",
      headers: { "X-Olcum": "1", Accept: "text/event-stream" },
    }, (y) => {
      if (y.statusCode !== 200) {
        y.resume();
        bitir("hata", { tur: "http", kod: y.statusCode });
        a.istek.destroy();
        return;
      }
      // "acik": ilk `dolu` OLMAYAN olayda (kart once `kimlik` olayini yollar) — dolu kart "acik" gorunmez.
      let tampon = Buffer.alloc(0), olay = "", veri = [], dolu = false, acik = false;
      y.on("data", (p) => {
        if (a.bitti) return;
        tampon = Buffer.concat([tampon, p]);
        const satirlar = [];
        for (let i = tampon.indexOf(10); i >= 0; i = tampon.indexOf(10)) {
          let l = tampon.subarray(0, i);
          tampon = tampon.subarray(i + 1);
          if (l.length > 4096) continue;
          if (l.length && l[l.length - 1] === 13) l = l.subarray(0, l.length - 1);
          const s = l.toString("utf8");
          if (s === "") {
            if (olay === "dolu") {
              dolu = true;
            } else if (veri.length) {
              if (!acik) { acik = true; yay("akisDurum", { kimlik, hal: "acik" }); }
              if (olay === "") satirlar.push(veri.join("\n"));
            }
            olay = "";
            veri = [];
          } else if (s.startsWith("data:")) {
            veri.push(s.slice(s[5] === " " ? 6 : 5));
          } else if (s.startsWith("event:")) {
            olay = s.slice(6).trim();
          }
        }
        if (tampon.length > 4096) tampon = Buffer.alloc(0);
        if (satirlar.length) yay("akis", { kimlik, satirlar });
      });
      y.on("end", () => bitir(dolu ? "dolu" : "kapandi"));
      y.on("error", () => bitir("hata", { tur: "baglanti" }));
      y.on("close", () => bitir("hata", { tur: "baglanti" }));
    });
    a.istek.on("error", () => bitir("hata", { tur: "baglanti" }));
    a.istek.end();
    return { kimlik };
  }

  async function akisKapat(c) {
    const a = akislar.get(c && c.kimlik);
    if (!a || a.bitti) return;
    a.bitir("kapandi");
    a.istek.destroy();
  }

  return { istek, cagrilar, akisAc, akisKapat, addListener, akisCagrilari, akisYay: yay };
}
