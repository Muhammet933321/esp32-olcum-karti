// Bu telefon › Bildirimler (A31, A37, A38, A42): bildirim ayarinin (zarfin) karttan alinmasi, bildirim izni,
// anlik izleme (+ pil kisitlamasi, nedeni yazilarak, ureticiye gore pil yoneticisi adimlari), 7 olay sinifi,
// deneme bildirimi. Mantik eski ekran/BildirimAyar.vue'dan tasindi (gorunum: ekran/bildirim_gorunum.js);
// araci adresi / kullanicisi bu bolume HIC gelmez. Sablon BildirimBolumu.vue.

import { bildirimGorunumu, hataMetni, sinifCevir } from "../ekran/bildirim_gorunum.js";
import { METIN_KARISIMI } from "./ortak.js";

// Izin / pil penceresinden donunce ve servis durumu degisince ekran kendini yeniler.
export const YOKLAMA_MS = 3000;

export const BILDIRIM_BOLUMU = {
  name: "TelefonBildirimBolumu",
  mixins: [METIN_KARISIMI],
  props: {
    b: { type: Object, required: true },
    yoklamaMs: { type: Number, default: YOKLAMA_MS },
  },
  data() {
    return {
      durum: null, kimlik: null, son: null, mesgul: false, yenileniyor: false, sonuc: null, hata: null, yonergeAcik: false,
      zamanlayici: null,
    };
  },
  computed: {
    g() { return bildirimGorunumu(this.durum, { kimlik: this.kimlik, son: this.son }); },
  },
  mounted() {
    this.oku();
    if (this.yoklamaMs > 0) this.zamanlayici = setInterval(() => { if (!this.mesgul) this.oku(); }, this.yoklamaMs);
  },
  beforeUnmount() {
    if (this.zamanlayici !== null) clearInterval(this.zamanlayici);
    this.zamanlayici = null;
  },
  methods: {
    async oku() {
      try {
        this.kimlik = await this.b.bildirimKimligi();
        if (this.son === null) this.son = this.b.bildirimSon();
        this.durum = await this.b.bildirim().durum(this.kimlik);
      } catch {
        this.durum = null;
      }
    },
    // Bir islem: tek seferde bir tane; sonuc / hata satiri yenilenir, ardindan durum yeniden okunur.
    async yap(is) {
      if (this.mesgul) return;
      this.mesgul = true;
      this.sonuc = null;
      this.hata = null;
      try {
        this.sonuc = (await is()) || null;
      } catch (e) {
        this.hata = hataMetni(e && e.tur);
      } finally {
        this.mesgul = false;
        await this.oku();
      }
    },
    yenile() {
      return this.yap(async () => {
        this.yenileniyor = true;
        try { this.son = await this.b.bildirim().yenile(); } finally { this.yenileniyor = false; }
        return this.son === "yazildi" ? { anahtar: "m.bl.yenile_tamam" } : null;
      });
    },
    izinIste() { return this.yap(async () => { await this.b.bildirim().izinIste(); }); },
    pilIste() { return this.yap(async () => { await this.b.bildirim().pilMuafiyetiIste(); }); },
    anlikCevir() { return this.yap(async () => { await this.b.bildirim().ayarYaz({ anlik: !this.durum.anlik }); }); },
    sinifDegistir(sinif) {
      return this.yap(async () => { await this.b.bildirim().ayarYaz({ kapali: sinifCevir(this.durum.kapali, sinif) }); });
    },
    ayarlariAc() { return this.yap(async () => { await this.b.bildirim().uygulamaAyarlariAc(); }); },
    deneme() {
      return this.yap(async () => ({ anahtar: (await this.b.bildirim().deneme()) ? "m.bl.deneme_tamam" : "m.bl.deneme_izin_yok" }));
    },
  },
};
