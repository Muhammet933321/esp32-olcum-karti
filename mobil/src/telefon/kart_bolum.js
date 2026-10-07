// Bu telefon › Kart (5P K13, K14): baglanti durumu (adres, kimlik), Baglan (elle adres istege bagli), imzali
// deneme, eslestirme (ad + WEB parolasi — Wi-Fi parolasi DEGIL), eslesmeyi kaldir, kartin eslesmis cihaz
// listesi (imzali GET /cihaz/liste) + iki adimli kaldirma (imzali POST /cihaz/sil?n=), kart saatini ver.
// Mantik eski ekran/Baglanti.vue + Esles.vue + esles_durum.js'ten tasindi; sablon KartBolumu.vue.
//
// PAROLA KURALI (A13, panelin ES3'u): parola Vue durumuna GIRMEZ — alan `ref` ile okunur ve kart.esles
// cagrilmadan ONCE bosaltilir; yalniz o cagri boyunca yerel degiskende yasar. Hicbir yere yazilmaz, gunluge
// gitmez; hata olarak yalniz sozluk anahtari tutulur.

import { adGecerli, PAROLA_EN_AZ } from "@ortak/imza.js";
import { utf8Kodla } from "@ortak/kripto.js";
import { ESLES_HATA, baglantiHatasi, kaldirGorunur, kaldirMesaji } from "../ekran/esles_durum.js";
import { METIN_KARISIMI, hataTuru, ikinciAdim, zamanYaz } from "./ortak.js";

export const AD_AZAMI_BAYT = 24;

const DURUM = Object.freeze({
  bagli: "m.bg.durum_bagli", eslesmemis: "m.bg.durum_eslesmemis", bulunamadi: "m.bg.durum_bulunamadi",
  "kimlik-uymuyor": "m.bg.durum_kimlik", "kasa-bozuk": "m.bg.kasa_bozuk",
});
// /eslestir/bilgi `saat`: 0 yok, 1 NTP, 2 cihazdan.
const SAAT = Object.freeze(["m.bt.saat_0", "m.bt.saat_1", "m.bt.saat_2"]);

// Cihaz adi: 1–24 BAYT (kart UTF-8 bayt sayar), denetim karakteri yok. Donus: null (gecerli) | sozluk anahtari.
export function adDenetle(ad) {
  return typeof ad === "string" && adGecerli(ad) ? null : "m.es.hata_ad";
}

// Parola kisa mi (kart UTF-8 BAYT sayar). Kisa parola karta HIC gitmez.
export function parolaKisa(parola) {
  return typeof parola !== "string" || utf8Kodla(parola).length < PAROLA_EN_AZ;
}

// kart.esles hatasi -> { anahtar, degerler } (sozluk anahtari; istisnanin kendisi TUTULMAZ).
export function eslesHataMetni(e) {
  const tur = hataTuru(e);
  if (tur === "bekle" && Number.isInteger(e.saniye)) return { anahtar: "m.es.hata_bekle_saniye", degerler: { saniye: e.saniye } };
  return { anahtar: Object.hasOwn(ESLES_HATA, tur) ? ESLES_HATA[tur] : "m.es.hata_bilinmeyen", degerler: null };
}

// kart.baglan / kart.durum sonucu -> ekranda tutulan ozet (bilgi'den yalniz saat kaynagi).
export function baglantiOzeti(s) {
  if (!s || typeof s.durum !== "string" || s.durum === "bagli-degil") return null;
  const saat = s.bilgi && Number.isInteger(s.bilgi.saat) ? s.bilgi.saat : null;
  return { durum: s.durum, adres: s.adres || null, kimlik: s.kimlik || null, saat };
}

// Imzali GET /cihaz/liste JSON'u -> [{n, ad, eklenme, son}] numara sirasinda (panelin cihazListe'siyle ayni
// kaynak). Bicimsiz kayit atlanir; bicimsiz yanit -> [] degil HATA (liste "bos" sanilmasin).
export function cihazListesiCoz(j) {
  if (!j || typeof j !== "object" || !Array.isArray(j.cihazlar)) throw new TypeError("cihazlar");
  const tam = (x) => (Number.isSafeInteger(x) && x >= 0 ? x : 0);
  return j.cihazlar
    .filter((c) => c && Number.isSafeInteger(c.n) && c.n > 0 && typeof c.ad === "string")
    .map((c) => ({ n: c.n, ad: c.ad, eklenme: tam(c.eklenme), son: tam(c.son) }))
    .sort((a, b) => a.n - b.n);
}

export const KART_BOLUMU = {
  name: "TelefonKartBolumu",
  mixins: [METIN_KARISIMI],
  props: { b: { type: Object, required: true } },
  emits: ["baglanti-degisti"],
  data() {
    return {
      elle: "",
      suruyor: false,
      baglanti: null,              // { durum, adres, kimlik, saat } | null
      kasaBozuk: false,
      mesaj: null,                 // { anahtar, degerler } — durum satiri
      mesajHata: false,
      // eslestirme
      ad: "",
      esliyor: false,
      mesgulTutuyor: false,
      eslesHata: null,
      eslesTamam: false,
      // iki adimli onay: "kaldir" | "sil<n>" | null
      onay: null,
      // kartin cihaz listesi
      liste: [],
      listeYuklendi: false,
      listeHata: null,
      kendiN: null,
    };
  },
  computed: {
    durumYazi() {
      if (this.kasaBozuk) return this.t("m.bg.kasa_bozuk");
      if (!this.baglanti) return this.t("m.bt.durum_yok");
      return this.t(DURUM[this.baglanti.durum] || "m.bg.durum_bulunamadi");
    },
    bagli() { return Boolean(this.baglanti) && this.baglanti.durum === "bagli"; },
    eslesmeAcik() { return Boolean(this.baglanti) && this.baglanti.durum === "eslesmemis" && !this.eslesTamam; },
    kaldirAcik() { return kaldirGorunur(this.baglanti, this.kasaBozuk); },
    bulunamadi() { return Boolean(this.baglanti) && this.baglanti.durum === "bulunamadi"; },
    saatYazi() {
      const s = this.baglanti ? this.baglanti.saat : null;
      return Number.isInteger(s) && s >= 0 && s < SAAT.length ? this.t(SAAT[s]) : "";
    },
    adHatasi() { return adDenetle(this.ad) !== null; },
    satirlar() {
      return this.liste.map((c) => ({
        ...c, kendi: c.n === this.kendiN, eklenmeYazi: zamanYaz(c.eklenme), sonYazi: zamanYaz(c.son),
      }));
    },
    listeBos() { return this.listeYuklendi && this.liste.length === 0 && !this.listeHata; },
  },
  created() {
    this.ad = this.t("m.es.ad_varsayilan");
  },
  mounted() {
    this.durumOku();
  },
  beforeUnmount() {
    this.mesgulBirak();
  },
  methods: {
    // Uygulamanin bildigi baglanti (Baglan'a basmadan adres / kimlik / eslesme durumu).
    async durumOku() {
      try {
        const k = await this.b.kartAl();
        this.baglanti = baglantiOzeti(k.durum());
      } catch {
        this.baglanti = null;
      }
      if (this.bagli) await this.listeYukle();
    },
    bildir() {
      const ozet = this.b.baglantiBildir(this.baglanti);
      this.$emit("baglanti-degisti", ozet);
    },
    // Bir islem: tek seferde bir tane; hata yalniz TUR adiyla.
    async calistir(is) {
      if (this.suruyor) return;
      this.suruyor = true;
      this.mesaj = null;
      this.mesajHata = false;
      try {
        await is(await this.b.kartAl());
      } catch (e) {
        const h = baglantiHatasi(e);
        if (h.kasaBozuk) { this.kasaBozuk = true; this.baglanti = null; }
        this.mesaj = { anahtar: h.anahtar, degerler: h.degerler };
        this.mesajHata = true;
      } finally {
        this.suruyor = false;
      }
    },
    baglan() {
      return this.calistir(async (k) => {
        this.kasaBozuk = false;
        this.onay = null;
        this.eslesTamam = false;
        this.eslesHata = null;
        this.liste = [];
        this.listeYuklendi = false;
        this.baglanti = baglantiOzeti(await k.baglan({ elle: this.elle.trim() })) || { durum: "bulunamadi", adres: null, kimlik: null, saat: null };
        this.bildir();
        if (this.bagli) await this.listeYukle();
      });
    },
    dene() {
      return this.calistir(async (k) => {
        const y = await k.istek("GET", "/kayit/liste");
        const j = await y.json();
        this.mesaj = { anahtar: "m.bg.imzali_tamam", degerler: { oturum: j && Array.isArray(j.oturumlar) ? j.oturumlar.length : 0 } };
      });
    },
    // ── eslestirme ──────────────────────────────────────────────────────
    async eslestir() {
      if (this.esliyor) return;
      const alan = this.$refs.parola;
      const parola = alan ? alan.value : "";
      if (alan) alan.value = "";                 // alan HEMEN bosaltilir: sonuc ne olursa olsun ekranda kalmaz
      this.eslesHata = null;
      const adHata = adDenetle(this.ad);
      if (adHata) { this.eslesHata = { anahtar: adHata, degerler: null }; return; }
      if (parolaKisa(parola)) { this.eslesHata = { anahtar: "m.es.hata_parola_kisa", degerler: null }; return; }
      this.esliyor = true;
      this.mesgulTutuyor = true;
      this.b.mesgulYap(true);                    // eslestirme suresince kart yeniden ARANMAZ
      try {
        const k = await this.b.kartAl();
        await this.b.kareBekle();                // PBKDF2 saf JS ve es zamanli: once ilerleme cizilsin
        await k.esles(this.ad, parola);
        this.eslesTamam = true;
        this.baglanti = { ...this.baglanti, durum: "bagli" };
        this.bildir();
      } catch (e) {
        this.eslesHata = eslesHataMetni(e);
      } finally {
        this.esliyor = false;
        this.mesgulBirak();
      }
      if (this.eslesTamam) await this.listeYukle();
    },
    // Mesgul isareti TEK kez birakilir (bilesen eslestirme surerken kapanirsa da).
    mesgulBirak() {
      if (!this.mesgulTutuyor) return;
      this.mesgulTutuyor = false;
      this.b.mesgulYap(false);
    },
    // ── iki adimli onay ─────────────────────────────────────────────────
    onayIste(anahtar) { this.onay = anahtar; },
    onayVazgec() { this.onay = null; },
    kaldir() {
      if (!ikinciAdim(this.onay, "kaldir")) return Promise.resolve();
      this.onay = null;
      return this.calistir(async (k) => {
        const s = await k.eslesmeyiKaldir();
        this.mesaj = { anahtar: kaldirMesaji(s.kartta), degerler: null };
        this.baglanti = null;
        this.kasaBozuk = false;
        this.eslesTamam = false;
        this.liste = [];
        this.listeYuklendi = false;
        this.kendiN = null;
        this.bildir();
      });
    },
    // ── kartin cihaz listesi ────────────────────────────────────────────
    async listeYukle() {
      this.listeHata = null;
      try {
        const k = await this.b.kartAl();
        const y = await k.istek("GET", "/cihaz/liste");
        this.liste = cihazListesiCoz(await y.json());
        this.kendiN = this.baglanti && this.baglanti.kimlik ? await this.b.kendiN(this.baglanti.kimlik) : null;
      } catch (e) {
        this.liste = [];
        this.listeHata = { anahtar: "m.bt.liste_hata", degerler: { tur: hataTuru(e) } };
      } finally {
        this.listeYuklendi = true;
      }
    },
    // Ikinci adim: YALNIZ silahli satirin cihazi kaldirilir. Bu telefonun kendi satiri buradan silinmez
    // (o "Eslesmeyi kaldir"dir: yerel anahtar da silinmeli).
    cihazSil(n) {
      if (!ikinciAdim(this.onay, `sil${n}`) || n === this.kendiN) return Promise.resolve();
      this.onay = null;
      return this.calistir(async (k) => {
        try {
          await k.istek("POST", "/cihaz/sil", [["n", String(n)]]);
          this.mesaj = { anahtar: "m.bt.silindi", degerler: { n } };
        } catch (e) {
          this.mesaj = { anahtar: "m.bt.sil_hata", degerler: { n, tur: hataTuru(e) } };
          this.mesajHata = true;
        }
        await this.listeYukle();
      });
    },
    // ── kart saati (A18) ────────────────────────────────────────────────
    saatVer() {
      return this.calistir(async (k) => {
        const verildi = await k.saatVer();
        this.mesaj = { anahtar: verildi ? "m.bt.saat_verildi" : "m.bt.saat_gerekmedi", degerler: null };
        if (verildi && this.baglanti) this.baglanti = { ...this.baglanti, saat: 2 };
      });
    },
  },
};
