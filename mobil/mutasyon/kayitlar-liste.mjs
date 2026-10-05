// 5D-3 — kayit verisi, istemci, Kayitlar / kayit gorunumu, yerel dosya okuma. Kosum (mobil/ icinden):
//   node mutasyon/kos.mjs --neden 5D-kayit
const V = "src/cekirdek/kayit_veri.js";
const I = "src/cekirdek/kayit_istemci.js";
const K = "src/cekirdek/kayitlar.js";
const G = "src/ekran/kayitlar_gorunum.js";
const O = "src/cekirdek/depo_oku.js";
const TV = "test/kayit_veri.test.js";
const TK = "test/kayitlar.test.js";
const TG = "test/gizlilik.test.js";

export default [
  // ── kayit_veri.js ──
  { ad: "5D-kayit: son siralar hesaplanmiyor (kartta daha yeni veri var 'eksik' isareti bozulur)", dosya: V,
    bul: "if (k.oturum && k.sira > (sonSira.get(k.oturum) || 0)) sonSira.set(k.oturum, k.sira);", koy: "", test: TV },
  { ad: "5D-kayit: bozuk kart dizini listeyi dusuruyor", dosya: V,
    bul: 'const kartGecerli = kart && typeof kart === "object" && Array.isArray(kart.oturumlar) ? kart : null;', koy: "const kartGecerli = kart;", test: TV },
  { ad: "5D-kayit: yerel kopyanin yeri 'telefon' degil (panelin 'tarayici'si)", dosya: V,
    bul: "listeBirlestir({ kart: kartGecerli, yereller, yerelNerede: YEREL_NEREDE })", koy: "listeBirlestir({ kart: kartGecerli, yereller })", test: TV },
  { ad: "5D-kayit: arama suzgeci uygulanmiyor", dosya: V,
    bul: 'arama: typeof arama === "string" ? arama : ""', koy: 'arama: ""', test: TV },
  { ad: "5D-kayit: tur suzgeci uygulanmiyor", dosya: V,
    bul: 'tur: TURLER.includes(tur) ? tur : "hepsi" }', koy: 'tur: "hepsi" }', test: TV },
  { ad: "5D-kayit: piramit arka planda kurulmuyor (ana is parcacigi kurar)", dosya: V,
    bul: "    oz: ozetKur(s.t, s.y),", koy: "", test: TV },
  { ad: "5D-kayit: zarf (min / maks) isareti seriden dusuyor", dosya: V,
    bul: "...(s.zarf ? { zarf: true, kalinlik: s.kalinlik } : {}),", koy: "", test: TV },
  { ad: "5D-kayit: gecerli olcum sayisi hep nokta sayisi (ADC'siz oturum 'gecerli' gorunur)", dosya: V,
    bul: "if ((v && Number.isFinite(v.y[k])) || (i && Number.isFinite(i.y[k]))) gecerli += 1;", koy: "gecerli += 1;", test: TK },
  { ad: "5D-kayit: sonlu olmayan aralikta okuma deneniyor", dosya: V,
    bul: ' || !Number.isFinite(tA) || !Number.isFinite(tB)) return null;\n  const ok', koy: ") return null;\n  const ok", test: TV },
  { ad: "5D-kayit: dosya okunamazsa eski veri siliniyor", dosya: V,
    bul: 'try { ham = await getir(a.url); } catch { throw new KayitVeriHatasi("okunamadi"); }', koy: 'try { ham = await getir(a.url); } catch { veri = null; throw new KayitVeriHatasi("okunamadi"); }', test: TV },
  { ad: "5D-kayit: bilinmeyen is sessizce kabul ediliyor", dosya: V,
    bul: '      default:\n        throw new KayitVeriHatasi("bicim");', koy: "      default:\n        return null;", test: TV },
  { ad: "5D-kayit: sure milisaniyeli yaziliyor (dar ekran)", dosya: V,
    bul: "zamanYazi(ms, 1000)", koy: "zamanYazi(ms, 1)", test: TV },
  // ── kayit_istemci.js ──
  { ad: "5D-kayit: depo adresi kimligi denetlemiyor", dosya: I,
    bul: 'return typeof kimlik === "string" && KIMLIK.test(kimlik) ? `${DEPO_YOLU}${kimlik}/kayitlar.kyt` : null;', koy: "return `${DEPO_YOLU}${kimlik}/kayitlar.kyt`;", test: TV },
  { ad: "5D-kayit: yanitlar numarayla eslesmiyor (ilk bekleyene gider)", dosya: I,
    bul: "        const b = bekleyen.get(m.no);", koy: "        const b = [...bekleyen.values()].at(-1);", test: TV },
  { ad: "5D-kayit: isci cokunce bekleyen cagrilar asili kaliyor", dosya: I,
    bul: '    for (const [, b] of bekleyen) b.reddet(new KayitIstemciHatasi("ic-hata"));', koy: "", test: TV },
  { ad: "5D-kayit: isci cokunce yeniden isci kurulmaya calisiliyor (yedege gecilmiyor)", dosya: I,
    bul: "    if (isci || isciDenendi) return isci;", koy: "    if (isci) return isci;", test: TV },
  { ad: "5D-kayit: postMessage hatasinda cagri asili kaliyor", dosya: I,
    bul: '        bekleyen.delete(n);\n        reddet(new KayitIstemciHatasi("ic-hata"));', koy: "        bekleyen.delete(n);", test: TV },
  // ── kayitlar.js ──
  { ad: "5D-kayit: dosya her listede yeniden cozuluyor", dosya: K,
    bul: "if (!yuklenen || yuklenen.kimlik !== kimlik || yuklenen.boy !== boy || yuklenen.akisKimlik !== akisKimlik) {", koy: "if (true) {", test: TK },
  { ad: "5D-kayit: dosya buyuyunce yeniden cozulmuyor (yeni kayitlar gorunmez)", dosya: K,
    bul: "yuklenen.kimlik !== kimlik || yuklenen.boy !== boy || yuklenen.akisKimlik", koy: "yuklenen.kimlik !== kimlik || yuklenen.akisKimlik", test: TK },
  { ad: "5D-kayit: akis kimligi degisince yeniden cozulmuyor", dosya: K,
    bul: " || yuklenen.akisKimlik !== akisKimlik) {", koy: ") {", test: TK },
  { ad: "5D-kayit: eslesmemis / bagli olmayan karta da dizin istegi gidiyor", dosya: K,
    bul: "    if (k.bagli) {\n      try { dizin", koy: "    if (true) {\n      try { dizin", test: TK },
  { ad: "5D-kayit: disarida son kimlik kullanilmiyor (liste bos)", dosya: K,
    bul: "    if (kimlik === null) { try { kimlik = sonKimlik(); } catch { kimlik = null; } }", koy: "", test: TK },
  { ad: "5D-kayit: bozuk durum.json kopyayi gizliyor", dosya: K,
    bul: '      if (!(e && e.tur === "bozuk")) throw hata(e);', koy: "      throw hata(e);", test: TK },
  { ad: "5D-kayit: art arda cagrilar ayni anda kosuyor (dosya iki kez cozulur)", dosya: K,
    bul: "    const yeni = onceki.catch(() => {}).then(is);", koy: "    const yeni = is();", test: TK },
  // ── gorunum ──
  { ad: "5D-kayit: yalniz kartta olan oturum da acilabilir gorunuyor", dosya: G,
    bul: "    acilabilir: s.yerelde === true,", koy: "    acilabilir: true,", test: TK },
  { ad: "5D-kayit: bilinmeyen tur prototip adina gidiyor", dosya: G,
    bul: "const tur = Object.hasOwn(TUR, s.tur) ? TUR[s.tur] : TUR.bilinmeyen;", koy: "const tur = TUR[s.tur] || TUR.bilinmeyen;", test: TK },
  { ad: "5D-kayit: sonlu olmayan sayi 'NaN' yaziliyor", dosya: G,
    bul: 'return Number.isFinite(x) ? x.toFixed(hane) : "—";', koy: "return Number(x).toFixed(hane);", test: TK },
  { ad: "5D-kayit: Kayit ekrani ADC'siz oturumda bos grafik ciziyor", dosya: "src/ekran/Kayit.vue",
    bul: '    if (g.gecerli === 0) { hal.value = "olcumsuz"; return; }', koy: "", test: TK },
  { ad: "5D-kayit: eski okuma yaniti yenisini eziyor", dosya: "src/ekran/Kayit.vue",
    bul: "    if (no === okumaNo) okuma.value = ok;", koy: "    okuma.value = ok;", test: TK },
  { ad: "5D-kayit: Kayitlar'da eski liste yaniti yeni aramayi eziyor", dosya: "src/ekran/Kayitlar.vue",
    bul: "    if (no !== sira) return;              // daha yeni bir istek var: eski yanit ekrani EZMEZ\n", koy: "", test: TK },
  { ad: "5D-kayit: alt rotada ust sekme bulunmuyor (baslik 'Durum')", dosya: "src/ekran/sekmeler.js",
    bul: "const asil = Object.hasOwn(ALT_ROTALAR, ad) ? ALT_ROTALAR[ad] : ad;", koy: "const asil = ad;", test: TK },
  { ad: "5D-kayit: Ayarlar'in kopya boyutu kartsizken 'bilinmiyor'", dosya: "src/cekirdek/uygulama.js",
    bul: "  if (kimlik === null) kimlik = sonKimlik();\n", koy: "", test: TK },
  // ── yerel okuma (A24) ──
  { ad: "5D-kayit: yerelOku adresi denetlemeden istek yapiyor", dosya: O,
    bul: 'if (typeof url !== "string" || !DEPO_ADRESI.test(url)) throw new DepoOkuHatasi("bicim");', koy: "", test: TG },
  { ad: "5D-kayit: yerelOku adres kalibi gevsek (sorgu / baska dosya gecer)", dosya: O,
    bul: "export const DEPO_ADRESI = /^\\/_depo\\/[0-9a-f]{16}\\/kayitlar\\.kyt$/;", koy: "export const DEPO_ADRESI = /^\\/_depo\\//;", test: TG },
  { ad: "5D-kayit: yerelOku 200 disi yaniti da veri sayiyor", dosya: O,
    bul: '  if (y.status !== 200) throw new DepoOkuHatasi("okunamadi");', koy: "", test: TG },
  { ad: "5D-kayit: yerelOku yonlendirmeyi izliyor / cerez gonderiyor", dosya: O,
    bul: '{ cache: "no-store", credentials: "omit", redirect: "error" }', koy: '{ cache: "no-store" }', test: TG },
  { ad: "5D-kayit: isci kabugu dosyayi kendi fetch'iyle okuyor (adres denetimi atlanir)", dosya: "src/isci/kayit_isci.js",
    bul: "const islemci = islemciKur({ getir: yerelOku });", koy: "const islemci = islemciKur({ getir: (u) => fetch(u).then((y) => y.arrayBuffer()) });", test: TG },
];
