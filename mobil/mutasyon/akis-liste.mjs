// 5C-1 mutasyonlari (canli akis): her iddianin onu YALANLAYAN degisikligi.
//   node mutasyon/kos.mjs --liste mutasyon/akis-liste.mjs
const AYIR = "src/cekirdek/akis_ayir.js";
const CANLI = "src/cekirdek/canli.js";
const AG = "src/cekirdek/ag.js";
const T_AYIR = "test/akis_ayir.test.js";
const T_CANLI = "test/canli.test.js";

export default [
  // ── akis_ayir.js ──
  {
    ad: "5C-akis: D satirinda fazla alan kabul ediliyor",
    dosya: AYIR, bul: "if (p.length !== 10) return null;", koy: "if (p.length < 10) return null;", test: T_AYIR,
  },
  {
    ad: "5C-akis: D satirinda menzil / ADC hata siniri denetlenmiyor",
    dosya: AYIR, bul: "if (o.menzil > 1 || o.adcHata > 3) return null;", koy: "", test: T_AYIR,
  },
  {
    ad: "5C-akis: 13 ile 15 arasi alanli G de kabul ediliyor",
    dosya: AYIR, bul: '!(tur === "G" && n === G_ESKI_ALAN)', koy: '!(tur === "G" && n >= G_ESKI_ALAN)', test: T_AYIR,
  },
  {
    ad: "5C-akis: eski G'de eksik alanlar null degil 0",
    dosya: AYIR, bul: "o[alanlar[i]] = null;", koy: "o[alanlar[i]] = 0;", test: T_AYIR,
  },
  {
    ad: "5C-akis: isaretli alanlar (son_hata, son_not) eksi kabul etmiyor",
    dosya: AYIR, bul: 'Object.freeze(["son_hata", "son_not"])', koy: "Object.freeze([])", test: T_AYIR,
  },
  {
    ad: "5C-akis: nan basan D satiri atiliyor",
    dosya: AYIR, bul: "return SAYI_DEGIL.test(s) ? NaN : null;", koy: "return null;", test: T_AYIR,
  },
  {
    ad: "5C-akis: dev satir kisaltilmadan tasiniyor",
    dosya: AYIR, bul: "if (satir.length > SATIR_AZAMI) return diger(satir.slice(0, SATIR_AZAMI));", koy: "", test: T_AYIR,
  },
  {
    ad: "5C-akis: satir turu nesne prototipinden de bulunuyor",
    dosya: AYIR, bul: "else if (Object.hasOwn(ALANLAR, p[0]))", koy: "else if (ALANLAR[p[0]])", test: T_AYIR,
  },
  {
    ad: "5C-akis: G / GP durum alani sinir disi kabul ediliyor",
    dosya: AYIR, bul: "if (Object.hasOwn(DURUM_AZAMI, tur) && o.durum > DURUM_AZAMI[tur]) return null;", koy: "", test: T_AYIR,
  },
  // ── canli.js ──
  {
    ad: "5C-akis: yeniden baglanma beklemesi hep 1 s",
    dosya: CANLI, bul: "const ms = YENIDEN_MS[Math.min(deneme, YENIDEN_MS.length - 1)];", koy: "const ms = YENIDEN_MS[0];", test: T_CANLI,
  },
  {
    ad: "5C-akis: veri gelince bekleme 1 s'ye donmuyor",
    dosya: CANLI, bul: "      acikMs = simdiMs();", koy: "      acikMs = null;", test: T_CANLI,
  },
  {
    ad: "5C-akis: dolu kartta 10 s yerine 1 s sonra deneniyor",
    dosya: CANLI, bul: "yenidenKur(DOLU_BEKLE_MS, false);", koy: "yenidenKur(YENIDEN_MS[0], false);", test: T_CANLI,
  },
  {
    ad: "5C-akis: baska akisin olaylari da isleniyor",
    dosya: CANLI, bul: "return akisKimlik !== null && veri.kimlik === akisKimlik;", koy: "return akisKimlik !== null;", test: T_CANLI,
  },
  {
    ad: "5C-akis: akisAc donmeden gelen olaylar kayboluyor",
    dosya: CANLI, bul: "if (bekleyen.length < BEKLEYEN_AZAMI) bekleyen.push({ ad, veri });", koy: "", test: T_CANLI,
  },
  {
    ad: "5C-akis: durdur akisi kapatmiyor (kartin yuvasi dolu kalir)",
    dosya: CANLI, bul: 'if (k !== null) kapatSessiz(k);\n    halYap("kapali");', koy: 'halYap("kapali");', test: T_CANLI,
  },
  {
    ad: "5C-akis: durdurma sirasinda acilan akis sahipsiz kaliyor",
    dosya: CANLI, bul: "      kapatSessiz(s.kimlik);\n", koy: "", test: T_CANLI,
  },
  {
    ad: "5C-akis: yeniden baglanmada eski imzali adres kullaniliyor",
    dosya: CANLI, bul: "url = await urlAl();", koy: "url = canliKur.eski || (canliKur.eski = await urlAl());", test: T_CANLI,
  },
  {
    ad: "5C-akis: sessizlik bekcisi fiilen yok",
    dosya: CANLI, bul: "    }, SESSIZ_MS);", koy: "    }, SESSIZ_MS * 1000);", test: T_CANLI,
  },
  {
    ad: "5C-akis: kart bagli degilken de akis aciliyor",
    dosya: CANLI, bul: 'if (d.durum !== "bagli") throw new CanliHatasi(', koy: "if (false) throw new CanliHatasi(", test: T_CANLI,
  },
  {
    ad: "5C-akis: canli kendiliginden kesif baslatiyor (yenidenBul varsayilan acik)",
    dosya: CANLI, bul: "akisUrlAl = null, yenidenBul = false,", koy: "akisUrlAl = null, yenidenBul = true,", test: T_CANLI,
  },
  {
    ad: "5C-akis: akis 401'inde acilis tazelenmiyor",
    dosya: CANLI, bul: 'yenidenKur(ms, yeniSebep === "http" && yeniKod === 401);', koy: "yenidenKur(ms, false);", test: T_CANLI,
  },
  {
    ad: "5C-akis: acilinca kayit durumu (G?) sorulmuyor",
    dosya: CANLI, bul: 'Promise.resolve().then(() => kart.istek("POST", "/komut", [], kodla("G?"))).catch(() => {});', koy: "", test: T_CANLI,
  },
  {
    ad: "5C-akis: eklentinin soyledigi tur denetimsiz duruma giriyor (adres sizabilir)",
    dosya: CANLI, bul: 'return TUR_DESENI.test(t) ? t : "ic-hata";', koy: 'return t || "ic-hata";', test: T_CANLI,
  },
  {
    ad: "5C-akis: http kodu denetimsiz duruma giriyor",
    dosya: CANLI, bul: "(Number.isInteger(k) && k >= 100 && k <= 599 ? k : null)", koy: "(k ?? null)", test: T_CANLI,
  },
  {
    ad: "5C-akis: tek olayda satir siniri yok",
    dosya: CANLI, bul: "const n = Math.min(veri.satirlar.length, OLAY_SATIR_AZAMI);", koy: "const n = veri.satirlar.length;", test: T_CANLI,
  },
  {
    ad: "5C-akis: seri 5 dakikadan eski noktalari da veriyor",
    dosya: CANLI, bul: "while (atla < adet && hT[(ilk + atla) % kap] <= esik) atla += 1;", koy: "", test: T_CANLI,
  },
  {
    ad: "5C-akis: dinleyicinin hatasi akisi bozuyor",
    dosya: CANLI, bul: "try { fn(durum()); } catch { /* arayuz hatasi akisi etkilemez */ }", koy: "fn(durum());", test: T_CANLI,
  },
  {
    ad: "5C-akis: komut beyaz listesi uygulanmiyor",
    dosya: CANLI, bul: 'if (!komutGecerli(metin)) throw new CanliHatasi("komut-yasak");', koy: "", test: T_CANLI,
  },
  {
    ad: "5C-akis: Gb deseni sona bagli degil (satir sonuyla ikinci komut gecer)",
    dosya: CANLI, bul: "const GB_DESENI = /^Gb(0|[1-9][0-9]{1,4})$/;", koy: "const GB_DESENI = /^Gb(0|[1-9][0-9]{1,4})/;", test: T_CANLI,
  },
  {
    ad: "5C-akis: Gb araligi (0 | 50…60000) denetlenmiyor",
    dosya: CANLI, bul: "return GB_HIZLARI.includes(Number(m[1]));", koy: "return true;", test: T_CANLI,
  },
  // ── ag.js akis sarmalayicisi ──
  {
    ad: "5C-akis: akisAc yolu denetlemiyor (/akis disi adres eklentiye gider)",
    dosya: AG, bul: 'if (yol !== "/akis" && !yol.startsWith("/akis?")) throw new KartAgHatasi("bicim");', koy: "", test: T_CANLI,
  },
  {
    ad: "5C-akis: akisAc hedef kuralini uygulamiyor",
    dosya: AG, bul: "    urlDenetle(url, { yerelDongu });\n    const yol =", koy: "    const yol =", test: T_CANLI,
  },
  {
    ad: "5C-akis: akisAc eklentinin yanitini suzmeden donduruyor",
    dosya: AG, bul: "return { kimlik: s.kimlik };", koy: "return s;", test: T_CANLI,
  },
  {
    ad: "5C-akis: akisKapat hata atiyor",
    dosya: AG, bul: "} catch { /* akis zaten kapali ya da eklenti yanit vermedi */ }", koy: "} catch (e) { throw e; }", test: T_CANLI,
  },
  {
    ad: "5C-akis: akisAc eklentinin ret kodunu denetimsiz tur yapiyor",
    dosya: AG, bul: '      const tur = e && typeof e.code === "string" && HATA_TURLERI.includes(e.code) ? e.code : "ic-hata";\n      throw new KartAgHatasi(tur);\n    }\n    if (!s || typeof s.kimlik',
    koy: '      throw new KartAgHatasi(e && e.code ? e.code : "ic-hata");\n    }\n    if (!s || typeof s.kimlik', test: T_CANLI,
  },
];
