// Uygulamanin TEK kart / kasa nesnesi (tasarim S1, A15). Ekranlar kartKur / kasaKur CAGIRMAZ; buradan
// alir. Her ekran gecisinde yeni bir kasaKur kurulsaydi iki kasa nesnesi ayni sayac dosyasina yazar ve
// ayni sayaci iki kez kullanabilirdi (curutucu 5B, S4).
//
//   const kart = await kartAl();      // ilk cagrida kurar; sonra (es zamanli cagrilarda da) HEP ayni nesne
//   const canli = await canliAl();    // tekil canli akis nesnesi (cekirdek/canli.js); modul yoksa reddeder
//   acilDurdur();                     // ACIL DURDUR (A8–A11): modul yuklenirken HAZIR, hicbir seyi beklemez
//
// Kurulum yarida kalirsa (eklenti yanit vermedi) soz saklanmaz: sonraki cagri yeniden dener.

import { agKur } from "./ag.js";
import { durdurKur } from "./durdur.js";
import { KartAg, Kasa, Kesif } from "./eklenti.js";
import { kartKur } from "./kart.js";
import { kasaKur } from "./kasa.js";
import { kesifKur, yerelOnbellek } from "./kesif.js";

let soz = null;
let kurulu = null;                      // kurulmus kart nesnesi (varsa): bagli adres ESZAMANLI okunur

async function kur() {
  const d = await KartAg.wifiDurumu();
  const yerelDongu = d.hataAyiklama === true;
  const ag = agKur(KartAg, { yerelDongu });
  const kesif = kesifKur({ kartFetch: ag.kartFetch, eklenti: Kesif, onbellek: yerelOnbellek(localStorage), yerelDongu });
  const kart = kartKur({ ag, kesif, kasa: kasaKur(Kasa) });
  kurulu = kart;
  return { kart, ag };
}

function parcalar() {
  if (!soz) {
    const yeni = kur();
    soz = yeni;
    yeni.catch(() => { if (soz === yeni) soz = null; });
  }
  return soz;
}

export function kartAl() {
  return parcalar().then((p) => p.kart);
}

// ── ACIL DURDUR (A8–A11) ─────────────────────────────────────────────────
// Adres kaynagi SAF ve ESZAMANLI: bagli adres (kart kuruluysa) + kesif onbellegindeki son adres.
// Bozuk / eksik girdi ATMAZ; ayni adres bir kez. Kartin erisim noktasi adresini durdur.js ekler.
export function durdurAdresleri(bagliAdres, onbellekKaydi) {
  const cikti = [];
  for (const a of [bagliAdres, onbellekKaydi && onbellekKaydi.adres]) {
    if (typeof a === "string" && a !== "" && !cikti.includes(a)) cikti.push(a);
  }
  return cikti;
}

function adresler() {
  let bagli = null;
  let kayit = null;
  try { bagli = kurulu ? kurulu.durum().adres : null; } catch { bagli = null; }
  try { kayit = yerelOnbellek(localStorage).oku(); } catch { kayit = null; }
  return durdurAdresleri(bagli, kayit);
}

const durdurDinleyenler = new Set();
// Modul duzeyinde: kart / kasa / kesif KURULMADAN hazir. Kendi ag sarmalayicisi (yalniz p0 icin);
// wifiDurumu BEKLENMEZ — hedef kurali yerel taraftadir.
const durdurNesnesi = durdurKur({
  p0: agKur(KartAg).p0,
  adresler,
  degisti: (hal) => { for (const fn of durdurDinleyenler) { try { fn(hal); } catch { /* arayuz hatasi durdurmayi etkilemez */ } } },
});

// Dugmenin dokunus isleyicisi DOGRUDAN bunu cagirir: tek satir, bekleme yok.
export function acilDurdur() {
  return durdurNesnesi.durdur();
}

export const durdurDurumu = () => durdurNesnesi.durum();

export function durdurDinle(fn) {
  durdurDinleyenler.add(fn);
  return () => { durdurDinleyenler.delete(fn); };
}

// ── canli akis (5C-1: cekirdek/canli.js) ─────────────────────────────────
// Ice aktarma TEK yerde ve tembel: dosya yoksa derleme KIRILMAZ (glob bos doner), canliAl reddeder
// ve ekranlar "akis hazir degil" der.
const canliModulleri = import.meta.glob("./canli.js");
const CANLI_YOLU = "./canli.js";
let canliSoz = null;

export class UygulamaHatasi extends Error {
  constructor(tur) {
    super(tur);
    this.name = "UygulamaHatasi";
    this.tur = tur;
  }
}

async function canliKurulum() {
  const yukle = canliModulleri[CANLI_YOLU];
  if (typeof yukle !== "function") throw new UygulamaHatasi("canli-yok");
  const [modul, p] = await Promise.all([yukle(), parcalar()]);
  if (!modul || typeof modul.canliKur !== "function") throw new UygulamaHatasi("canli-yok");
  return modul.canliKur({ kart: p.kart, ag: p.ag, eklenti: KartAg, simdiMs: Date.now });
}

export function canliAl() {
  if (!canliSoz) {
    const yeni = canliKurulum();
    canliSoz = yeni;
    yeni.catch(() => { if (canliSoz === yeni) canliSoz = null; });
  }
  return canliSoz;
}
