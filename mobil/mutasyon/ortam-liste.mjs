// 5P P3 mutasyonlari (telefon ortami: src/ortam/*, cekirdege eklenen kucuk yollar). Kosum (mobil/ icinden):
//   node mutasyon/kos.mjs --liste mutasyon/ortam-liste.mjs   (mutasyon/liste.mjs'e de katilir: --neden 5P-P3)
// Her girdi test/ortam_*.test.js'in bir iddiasini YALANLAR; test kirmiziya donmeli.
const TAS = "test/ortam_tasiyici.test.js";
const IST = "test/ortam_istek.test.js";
const ARKA = "test/ortam_arka_plan.test.js";
const SOZ = "test/ortam_sozlesme.test.js";
const KOP = "test/ortam_kopya.test.js";
const CEK = "test/ortam_cekirdek.test.js";

export default [
  { ad: "5P-P3: tasiyici: akis dolu panelin uyarisina yazilmiyor", dosya: "src/ortam/tasiyici.js",
    bul: '      uyariYaz(b, metin("or.dolu", dil));\n', koy: "", test: TAS },
  { ad: "5P-P3: tasiyici: eslesmemis kart ac()'ta reddedilmiyor", dosya: "src/ortam/tasiyici.js",
    bul: "    if (red) {\n", koy: "    if (false) {\n", test: TAS },
  { ad: "5P-P3: tasiyici: komut hatasinda kartin sebebi kayboluyor", dosya: "src/ortam/tasiyici.js",
    bul: 'kodla(komut), { hamYanit: true });', koy: "kodla(komut));", test: TAS },
  { ad: "5P-P3: tasiyici: p0 imzali komut yolundan gidiyor", dosya: "src/ortam/tasiyici.js",
    bul: '    if (komut === "p0") {\n', koy: '    if (komut === "p0-yok") {\n', test: TAS },
  { ad: "5P-P3: istek: yanit tavani istek basina verilmiyor (64 KiB)", dosya: "src/ortam/istek.js",
    bul: "        azamiGovde: azamiGovde(a.yol, a.argumanlar), zamanAsimiMs: ISTEK_SURE_MS, hamYanit: true,",
    koy: "        zamanAsimiMs: ISTEK_SURE_MS, hamYanit: true,", test: IST },
  { ad: "5P-P3: istek: p0 imzali yoldan gidiyor", dosya: "src/ortam/istek.js",
    bul: 'if (yontem === "POST" && a.yol === "/komut" && P0_GOVDE.test(', koy: 'if (false && P0_GOVDE.test(', test: IST },
  { ad: "5P-P3: istek: iptal edilmis istek yine gidiyor", dosya: "src/ortam/istek.js",
    bul: "    if (sinyal && sinyal.aborted) throw iptalHatasi(sinyal);\n    const a = yolAyir(tamYol);",
    koy: "    const a = yolAyir(tamYol);", test: IST },
  { ad: "5P-P3: istek: HTTP hatasi Response yerine ret", dosya: "src/ortam/istek.js",
    bul: "zamanAsimiMs: ISTEK_SURE_MS, hamYanit: true,", koy: "zamanAsimiMs: ISTEK_SURE_MS,", test: IST },
  { ad: "5P-P3: arka plan: arka plana gecince akis acik kaliyor", dosya: "src/ortam/arka_plan.js",
    bul: "    pilGecersiz();\n    akisKapat();\n    yay();", koy: "    pilGecersiz();\n    yay();", test: ARKA },
  { ad: "5P-P3: arka plan: eslestirme surerken kart araniyor", dosya: "src/ortam/arka_plan.js",
    bul: "    if (mesgul()) return Promise.resolve(", koy: "    if (false) return Promise.resolve(", test: ARKA },
  { ad: "5P-P3: arka plan: kayit bitince eşitlenmiyor", dosya: "src/ortam/arka_plan.js",
    bul: "if (oncekiKod === KDR_KAYIT && kod !== KDR_KAYIT && esit)", koy: "if (false && esit)", test: ARKA },
  { ad: "5P-P3: arka plan: panel istemeden akis aciliyor", dosya: "src/ortam/arka_plan.js",
    bul: "  let panelIster = false;", koy: "  let panelIster = true;", test: ARKA },
  { ad: "5P-P3: ortam: serit panelin 'pil suruyor'unu yok sayiyor", dosya: "src/ortam/ortam.js",
    bul: "    if (pilSuruyor === true) return true;\n", koy: "", test: SOZ },
  { ad: "5P-P3: soru: her komut anlik izleme sorusunu aciyor", dosya: "src/ortam/soru.js",
    bul: 'if (typeof metin !== "string" || !GB.test(metin)) return;', koy: 'if (typeof metin !== "string") return;', test: SOZ },
  { ad: "5P-P3: kopya: panel telefon kopyasina yazabiliyor", dosya: "src/ortam/kopya.js",
    bul: "      durumYaz: saltOkuma,", koy: "      durumYaz: (x) => d.durumYaz(x),", test: KOP },
  { ad: "5P-P3: kopya: eşitleme hatasi panelin durumuna eslenmiyor", dosya: "src/ortam/kopya.js",
    bul: '  "kopya-uyusmuyor": "akis",\n', koy: "", test: KOP },
  { ad: "5P-P3: canli: ham satirlar dinleyiciye gitmiyor", dosya: "src/cekirdek/canli.js",
    bul: "      hamYay(veri.satirlar[i]);\n", koy: "", test: CEK },
  { ad: "5P-P3: kart: hamYanit HTTP hatasini donmuyor", dosya: "src/cekirdek/kart.js",
    bul: "        if (hamYanit && e instanceof HttpHatasi && e.durum !== 401 && e.yanit) return e.yanit;\n", koy: "", test: CEK },
  { ad: "5P-P3: kart: ek azamiGovde kartFetch'e gecmiyor", dosya: "src/cekirdek/kart.js",
    bul: "Object.keys(fetchEk).length ? { ...secenek, ...fetchEk } : secenek", koy: "secenek", test: CEK },
  { ad: "5P-P3: paylas: MIME uzantiya uymasa da gidiyor", dosya: "src/cekirdek/paylas.js",
    bul: '    if (genisTurDenetle(ad, mime) === null) throw new PaylasHatasi("bicim");      // MIME uzantiya uymali\n', koy: "", test: CEK },
];
