// Uygulamanin TEK kart / kasa nesnesi (tasarim S1, A15). Ekranlar kartKur / kasaKur CAGIRMAZ; buradan
// alir. Her ekran gecisinde yeni bir kasaKur kurulsaydi iki kasa nesnesi ayni sayac dosyasina yazar ve
// ayni sayaci iki kez kullanabilirdi (curutucu 5B, S4).
//
//   const kart = await kartAl();      // ilk cagrida kurar; sonra (es zamanli cagrilarda da) HEP ayni nesne
//
// Kurulum yarida kalirsa (eklenti yanit vermedi) soz saklanmaz: sonraki cagri yeniden dener.

import { agKur } from "./ag.js";
import { KartAg, Kasa, Kesif } from "./eklenti.js";
import { kartKur } from "./kart.js";
import { kasaKur } from "./kasa.js";
import { kesifKur, yerelOnbellek } from "./kesif.js";

let soz = null;

async function kur() {
  const d = await KartAg.wifiDurumu();
  const yerelDongu = d.hataAyiklama === true;
  const ag = agKur(KartAg, { yerelDongu });
  const kesif = kesifKur({ kartFetch: ag.kartFetch, eklenti: Kesif, onbellek: yerelOnbellek(localStorage), yerelDongu });
  return kartKur({ ag, kesif, kasa: kasaKur(Kasa) });
}

export function kartAl() {
  if (!soz) {
    const yeni = kur();
    soz = yeni;
    yeni.catch(() => { if (soz === yeni) soz = null; });
  }
  return soz;
}
