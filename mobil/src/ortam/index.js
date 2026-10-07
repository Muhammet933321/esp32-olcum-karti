// Telefon ortaminin GIRISI (5P P3). src/giris.js panelden (arayuz3/app.js) ONCE cagirir:
//
//   const ortam = await ortamKur({ kuresel });   // kuresel: kuresel nesne — `__olcumOrtam` buraya kurulur
//
// Kuresel nesnenin ADI bu agacta yazilamaz (test/gizlilik.test.js — tek istisna giris.js); bu yuzden onu
// cagiran verir. Verilmezse kurulum REDDEDILIR: ortamsiz panel telefonda PC dallarina (kopru yoklamasi,
// servis iscisi) girerdi (giris.js de bu durumda paneli acmaz).
//
// Cekirdek nesneler cekirdek/uygulama.js'in TEKIL nesneleridir (S1: tek kart / kasa, tek canli akis, tek
// eşitleyici, tek bildirim izleyicisi). Arka plan isleri (K17) burada baslar — eski App.vue / kabuk_durum.js
// neyi kurduysa: kart arama, eşitleme (baglaninca / kayit bitince / 60 s, yalniz ondeyken), bildirim
// izleyicisi, pil durumu (30 s), bildirim dili.
//
// "Bu telefon" bolumunun dosyalari (src/telefon/) tembel ve ISTEGE BAGLI (import.meta.glob: dosya yoksa
// derleme kirilmaz): index.js `bolum()` (Ayarlar), olay.js `baglantiDinle` / `mesgulMu` (eski kabugun
// baglantiDegisti / mesgulYap'i).

import { depoKur } from "../cekirdek/depo.js";
import { KartDepo, Paylas, Yazdir } from "../cekirdek/eklenti.js";
import { yerelOnbellek } from "../cekirdek/kesif.js";
import { paylasKur } from "../cekirdek/paylas.js";
import {
  acilDurdur, bildirimAl, bildirimIzle, canliAl, esitlemeAl, izlemeSorusu, kartAl, pilOku,
} from "../cekirdek/uygulama.js";
import { metin } from "./metin.js";
import { ortamOlustur } from "./ortam.js";
import { vueCizici } from "./soru_cizim.js";

export const KURESEL_AD = "__olcumOrtam";

const TELEFON = import.meta.glob(["../telefon/index.js", "../telefon/olay.js"]);
const BOLUM_YOLU = "../telefon/index.js";
const OLAY_YOLU = "../telefon/olay.js";

let kurulu = null;                      // { ortam, arka }

export class OrtamHatasi extends Error {
  constructor(tur, mesaj) {
    super(mesaj);
    this.name = "OrtamHatasi";
    this.tur = tur;
  }
}

function belgeAl() {
  return typeof document !== "undefined" ? document : null;
}

function yerelAl() {
  try { return typeof localStorage !== "undefined" ? localStorage : null; } catch { return null; }
}

// Son baglanilan kartin kimligi (kesif onbellegi): kart bu agda degilken kopyasi bununla bulunur.
function sonKimlik() {
  const y = yerelAl();
  if (!y) return null;
  try { const k = yerelOnbellek(y).oku(); return k ? k.kimlik : null; } catch { return null; }
}

// Ortami kurar, `kuresel.__olcumOrtam`'a yerlestirir, arka plani baslatir. Ikinci cagri AYNI ortami doner.
export async function ortamKur({ kuresel = null, belge = belgeAl() } = {}) {
  if (!kuresel || (typeof kuresel !== "object" && typeof kuresel !== "function")) {
    throw new OrtamHatasi("kuresel-yok", metin("or.kuresel_yok", "tr"));
  }
  if (kurulu) {
    if (kuresel[KURESEL_AD] !== kurulu.ortam) Object.defineProperty(kuresel, KURESEL_AD, { value: kurulu.ortam, configurable: true, enumerable: false, writable: false });
    return kurulu.ortam;
  }
  const dilAl = () => (belge && belge.documentElement && belge.documentElement.lang === "en" ? "en" : "tr");

  // "Bu telefon"un iki haberi (varsa): eslestirme surerken kart yeniden ARANMAZ; baglanti bitince akis yeniden.
  let olay = null;
  if (typeof TELEFON[OLAY_YOLU] === "function") {
    try { olay = await TELEFON[OLAY_YOLU](); } catch { olay = null; }
  }
  const bolumYukle = TELEFON[BOLUM_YOLU];

  const { ortam, arka } = ortamOlustur({
    kartAl, canliAl, esitlemeAl, izlemeSorusu, pilOku, acilDurdur,
    depoAl: (kimlik) => depoKur(KartDepo, kimlik),
    bildirimIzle,
    bildirimDil: (dil) => bildirimAl().ayarYaz({ dil }),
    paylas: paylasKur({ eklenti: Paylas }),
    yazdirEklenti: Yazdir,
    ayarBolumuYukle: typeof bolumYukle === "function" ? bolumYukle : null,
    sonKimlik,
    yerel: yerelAl(),
    belge,
    mesgulMu: () => Boolean(olay && typeof olay.mesgulMu === "function" && olay.mesgulMu()),
    ciz: vueCizici({ belge, dilAl }),
  });
  if (olay && typeof olay.baglantiDinle === "function") {
    olay.baglantiDinle((b) => { arka.baglantiDegisti(b).catch(() => {}); });
  }
  Object.defineProperty(kuresel, KURESEL_AD, { value: ortam, configurable: true, enumerable: false, writable: false });
  kurulu = { ortam, arka };
  arka.baslat();
  return ortam;
}

// "Bu telefon" bolumu ve testler icin: kurulu ortamin arka plani (baglan, baglantiDegisti, durum, dinle) | null.
export function arkaPlanAl() {
  return kurulu ? kurulu.arka : null;
}
