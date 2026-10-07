// Bu telefon › Gelismis: kesif tanisi ("Karti ara" — her aday ve agdaki duyurular), ACIL DURDUR suresi (20
// tekrar), PBKDF2 suresi (eslestirmedeki ayni saf JS kodu), WebView ag sinamasi, surumler (uygulama + kartin
// sundugu panel `/kunye.json`). Mantik eski ekran/KartBul.vue'dan (Ayarlar › Gelismis) tasindi; sablon
// GelismisBolumu.vue.

import { pbkdf2Gorunumu } from "../ekran/olcum_gorunum.js";
import { METIN_KARISIMI, hataTuru } from "./ortak.js";
import { kaynakAnahtari, sonucAnahtari } from "./tani.js";

// Eslestirmenin varsayilan PBKDF2 tur sayisi (kart bulunmadan da olculur).
export const PBKDF2_VARSAYILAN_TUR = 20000;

const WEB = Object.freeze({ engellendi: "m.ws.engellendi", "bos-yuklendi": "m.ws.bos", GECTI: "m.ws.gecti" });
export const webAnahtari = (s) => (Object.hasOwn(WEB, s) ? WEB[s] : "m.ws.gecti");

// Kartin `/kunye.json`u (arayuz-uret.py panel_kunyesi) -> {surum, dosya}; bicimsizse null (panelin kunyeCoz'u).
export function kunyeCoz(v) {
  if (!v || typeof v !== "object" || !/^[0-9a-f]{12}$/.test(v.surum || "")) return null;
  if (!Number.isInteger(v.dosya)) return null;
  return { surum: v.surum, dosya: v.dosya };
}

export const GELISMIS_BOLUMU = {
  name: "TelefonGelismisBolumu",
  mixins: [METIN_KARISIMI],
  props: { b: { type: Object, required: true } },
  data() {
    return {
      // kesif tanisi
      elle: "", araniyor: false, tani: null,
      // olcumler
      durdurSuruyor: false, durdurSonuc: null,
      pbkdf2Suruyor: false, pbkdf2Sonuc: null,
      webSuruyor: false, webSonuc: [],
      // surumler
      uygulama: "", panel: null, panelNeden: null, panelOkunuyor: false,
    };
  },
  computed: {
    taniSatirlari() {
      const d = this.tani ? this.tani.denenenler : [];
      return d.map((x, i) => ({ anahtar: `${i}:${x.adres}`, adres: x.adres, kaynak: this.t(kaynakAnahtari(x.kaynak)), sonuc: this.t(sonucAnahtari(x.sonuc)) }));
    },
    taniKaynak() { return this.tani && this.tani.sonuc ? this.t(kaynakAnahtari(this.tani.sonuc.kaynak)) : ""; },
    txtYazi() {
      const s = this.tani && this.tani.sonuc;
      if (!s || s.kaynak !== "nsd") return "";
      return this.t(s.txtKimlik === s.kimlik ? "m.kb.txt_uyuyor" : "m.kb.txt_uymuyor");
    },
    panelYazi() {
      if (this.panelOkunuyor) return this.t("m.bt.yukleniyor");
      if (this.panel) return this.t("m.bt.panel_surum", { surum: this.panel.surum, dosya: this.panel.dosya });
      return this.panelNeden ? this.yaz(this.panelNeden) : "—";
    },
  },
  mounted() {
    this.surumOku();
  },
  methods: {
    webYazi(s) { return this.t(webAnahtari(s)); },
    async kesifAra() {
      if (this.araniyor) return;
      this.araniyor = true;
      this.tani = null;
      try {
        this.tani = await this.b.kesifTanisi({ elle: this.elle });
      } catch {
        this.tani = { sonuc: null, denenenler: [], duyurular: [], hata: "m.kb.hata_bilinmeyen" };
      } finally {
        this.araniyor = false;
      }
    },
    async durdurSina() {
      if (this.durdurSuruyor) return;
      this.durdurSuruyor = true;
      this.durdurSonuc = null;
      try { this.durdurSonuc = await this.b.durdurOlc(); } finally { this.durdurSuruyor = false; }
    },
    // Tur: kart bulunduysa tanida gorulen kartin bildirdigi (yoksa 20 000). Hesap es zamanli: once ilerleme cizilsin.
    async pbkdf2Sina() {
      if (this.pbkdf2Suruyor) return;
      this.pbkdf2Suruyor = true;
      this.pbkdf2Sonuc = null;
      const s = this.tani && this.tani.sonuc;
      const tur = s && Number.isInteger(s.tur) ? s.tur : PBKDF2_VARSAYILAN_TUR;
      try {
        await this.b.kareBekle();
        this.pbkdf2Sonuc = pbkdf2Gorunumu(this.b.pbkdf2Olc(tur));
      } finally {
        this.pbkdf2Suruyor = false;
      }
    },
    async webSina() {
      if (this.webSuruyor) return;
      this.webSuruyor = true;
      this.webSonuc = [];
      try { this.webSonuc = await this.b.webSinama(); } finally { this.webSuruyor = false; }
    },
    async surumOku() {
      try { this.uygulama = await this.b.uygulamaSurumu(); } catch { this.uygulama = ""; }
      await this.panelOku();
    },
    // Panel surumu: kartin arayuz goruntusunun kunyesi, imzali istekle (eslesmis + bagli kart).
    async panelOku() {
      this.panelOkunuyor = true;
      this.panel = null;
      this.panelNeden = null;
      try {
        const k = await this.b.kartAl();
        const d = k.durum();
        if (!d || d.durum !== "bagli") {
          this.panelNeden = { anahtar: "m.bt.panel_bagli_degil", degerler: null };
          return;
        }
        const y = await k.istek("GET", "/kunye.json");
        this.panel = kunyeCoz(await y.json());
        if (!this.panel) this.panelNeden = { anahtar: "m.bt.panel_okunamadi", degerler: { tur: "bicim" } };
      } catch (e) {
        this.panelNeden = { anahtar: "m.bt.panel_okunamadi", degerler: { tur: hataTuru(e) } };
      } finally {
        this.panelOkunuyor = false;
      }
    },
  },
};
