// "Bu telefon" bolumunun GERCEK baglami: cekirdek modullere tek giris (testte sahte baglam verilir).
// Kart / kasa nesnesi BURADA KURULMAZ — uygulama.js'in tekil nesnesi kullanilir (S1, A15).
//
//   const b = gercekBaglam();     // her cagrida AYNI nesne

import { registerPlugin } from "@capacitor/core";
import {
  acilDurdur, bildirimAl, bildirimIzle, bildirimKimligi, esitlemeAl, esitlemeOnayi, esitlemeOnayiYaz, kartAl, kopyaBoyutu,
} from "../cekirdek/uygulama.js";
import { agKur } from "../cekirdek/ag.js";
import { Kasa, KartAg, Kesif } from "../cekirdek/eklenti.js";
import { HedefHatasi } from "../cekirdek/hedef.js";
import { kesifKur, KesifHatasi, yerelOnbellek } from "../cekirdek/kesif.js";
import { durdurOlc, pbkdf2Olc } from "../cekirdek/olcum.js";
import { webSinama } from "../cekirdek/web_sinama.js";
import { version as PAKET_SURUMU } from "../../package.json";
import { mesgulYap, baglantiBildir } from "./olay.js";
import { kesifTanisi } from "./tani.js";

// Capacitor App eklentisi kurulu degilse getInfo reddeder: paketin surumune dusulur.
const UygulamaBilgisi = registerPlugin("App");

const kareBekle = () => new Promise((coz) => { requestAnimationFrame(() => setTimeout(coz, 0)); });

let tek = null;

export function gercekBaglam() {
  if (tek) return tek;
  tek = Object.freeze({
    kartAl,
    kareBekle,
    baglantiBildir,
    mesgulYap,
    // Kasadaki kaydin kart listesindeki numarasi (listede "bu telefon" isareti). Okunamazsa null.
    async kendiN(kimlik) {
      try {
        const y = await Kasa.liste({});
        const k = (y && Array.isArray(y.kayitlar) ? y.kayitlar : []).find((x) => x && x.kimlik === kimlik);
        return k && Number.isSafeInteger(k.n) ? k.n : null;
      } catch {
        return null;
      }
    },
    kesifTanisi: ({ elle }) => kesifTanisi({
      KartAg, Kesif, agKur, kesifKur, onbellek: yerelOnbellek(localStorage), KesifHatasi, HedefHatasi,
    }, { elle }),
    // Esitleme
    esitlemeOnayi,
    esitlemeOnayiYaz,
    kopyaBoyutu,
    async kopyaSifirla() { await (await esitlemeAl()).sifirla(); },
    // Bildirimler
    bildirim: () => bildirimAl(),
    bildirimKimligi,
    bildirimSon: () => bildirimIzle.son(),
    // Gelismis
    durdurOlc: () => durdurOlc(acilDurdur),
    pbkdf2Olc: (tur) => pbkdf2Olc(tur),
    webSinama,
    async uygulamaSurumu() {
      try {
        const i = await UygulamaBilgisi.getInfo();
        if (i && typeof i.version === "string" && i.version !== "") return i.build ? `${i.version} (${i.build})` : i.version;
      } catch { /* eklenti yok: paket surumu */ }
      return PAKET_SURUMU;
    },
  });
  return tek;
}
