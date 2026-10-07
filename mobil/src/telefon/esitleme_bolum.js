// Bu telefon › Esitleme (A21, A23; 5P K14 — panelin Depolama bolumunun telefondaki karsiligi):
// "Bu telefon da onaylasin" anahtari (VARSAYILAN KAPALI), telefondaki kopyanin boyutu, "Kopyayi sifirla"
// (iki adim). Mantik eski ekran/EsitlemeAyar.vue'dan tasindi; sablon EsitlemeBolumu.vue.

import { boyutYaz } from "../ekran/esitleme_ayar_gorunum.js";
import { METIN_KARISIMI, hataTuru } from "./ortak.js";

export const ESITLEME_BOLUMU = {
  name: "TelefonEsitlemeBolumu",
  mixins: [METIN_KARISIMI],
  props: { b: { type: Object, required: true } },
  data() {
    return { onay: false, boyut: null, eminim: false, suruyor: false, sonuc: null, hata: null };
  },
  created() {
    try { this.onay = this.b.esitlemeOnayi() === true; } catch { this.onay = false; }
  },
  mounted() {
    this.boyutOku();
  },
  methods: {
    async boyutOku() {
      try {
        const b = await this.b.kopyaBoyutu();
        this.boyut = b ? boyutYaz(b.toplam) : null;
      } catch {
        this.boyut = null;
      }
    },
    // Saklanan deger geri okunur: yazilamadiysa anahtar eski haline doner (yalan gostermez).
    onayDegistir(acik) {
      try { this.onay = this.b.esitlemeOnayiYaz(acik === true) === true; } catch { /* degismedi */ }
    },
    sifirlaBasla() { this.eminim = true; },
    sifirlaVazgec() { this.eminim = false; },
    async sifirla() {
      if (!this.eminim || this.suruyor) return;
      this.eminim = false;
      this.suruyor = true;
      this.sonuc = null;
      this.hata = null;
      try {
        await this.b.kopyaSifirla();
        this.sonuc = { anahtar: "m.es.sifirlandi", degerler: null };
      } catch (e) {
        this.hata = { anahtar: "m.es.sifirla_hata", degerler: { tur: hataTuru(e) } };
      } finally {
        this.suruyor = false;
      }
      await this.boyutOku();
    },
  },
};
