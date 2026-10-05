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
import { bildirimIzleyici, bildirimKur, izlemeSorusuKur } from "./bildirim.js";
import { durdurKur } from "./durdur.js";
import { KART_ADI } from "./hedef.js";
import { Bildirim, KartAg, KartDepo, Kasa, Kesif, Paylas } from "./eklenti.js";
import { onayOku, onayYaz } from "./esitleme_ayar.js";
import { PIL_SIRA, PIL_YOLU, pilDurumuCoz } from "./pil_durum.js";
import { paylasKur } from "./paylas.js";
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
// Adres kaynagi SAF ve ESZAMANLI. Sira: BAGLI adres (bu baglantida kimligi dogrulanmis kart — "asil"),
// kesif onbellegindeki son adres, kartin adi (olcum.local: IP degismisse de karta gider; ad yalniz ozel
// adrese cozulur, p0 imzasizdir). Bozuk / eksik girdi ATMAZ; ayni adres bir kez. Kartin erisim noktasi
// adresini durdur.js ekler: toplam en cok 4 adres (ag.js P0_AZAMI_ADRES).
export function durdurAdresleri(bagliAdres, onbellekKaydi) {
  const cikti = [];
  for (const a of [bagliAdres, onbellekKaydi && onbellekKaydi.adres, KART_ADI]) {
    if (typeof a === "string" && a !== "" && !cikti.includes(a)) cikti.push(a);
  }
  return cikti;
}

// { liste, asil }: asil = bagli adres (yoksa null — o zaman hicbir adres "asil" degildir).
function adresler() {
  let bagli = null;
  let kayit = null;
  try { bagli = kurulu ? kurulu.durum().adres : null; } catch { bagli = null; }
  try { kayit = yerelOnbellek(localStorage).oku(); } catch { kayit = null; }
  return { liste: durdurAdresleri(bagli, kayit), asil: typeof bagli === "string" && bagli !== "" ? bagli : null };
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
  return modul.canliKur({ kart: p.kart, ag: p.ag, eklenti: KartAg, simdiMs: Date.now, yenidenBul: true });
}

// ── kayit esitleme (5D: cekirdek/esitleme.js + depo.js) ──────────────────
// Tembel ice aktarma: ortak/src/esitle.js + kayit.js acilis paketine girmez.
let esitlemeSoz = null;

async function esitlemeKurulum() {
  const [e, d] = await Promise.all([import("./esitleme.js"), import("./depo.js")]);
  return e.esitlemeKur({
    kartAl,
    depoAl: (kimlik) => d.depoKur(KartDepo, kimlik),
    onayAcik: esitlemeOnayi,                     // A21: varsayilan KAPALI; her turda yeniden okunur
    sonKimlik,
  });
}

export function esitlemeAl() {
  if (!esitlemeSoz) {
    const yeni = esitlemeKurulum();
    esitlemeSoz = yeni;
    yeni.catch(() => { if (esitlemeSoz === yeni) esitlemeSoz = null; });
  }
  return esitlemeSoz;
}

export function esitlemeOnayi() {
  try { return onayOku(localStorage); } catch { return false; }
}

export function esitlemeOnayiYaz(acik) {
  try { return onayYaz(localStorage, acik); } catch { return false; }
}

// Son baglanilan kartin kimligi (kesif onbellegi): kart bu agda degilken kopyasi bununla bulunur.
function sonKimlik() {
  try { const k = yerelOnbellek(localStorage).oku(); return k ? k.kimlik : null; } catch { return null; }
}

// Ayarlar'in depolama satiri: bagli kartin — o yoksa son baglanilan kartin — kopyasinin boyutu.
// Hic kart bilinmiyorsa null.
export async function kopyaBoyutu() {
  let kimlik = null;
  try { const d = (await kartAl()).durum(); kimlik = d && typeof d.kimlik === "string" ? d.kimlik : null; } catch { kimlik = null; }
  if (kimlik === null) kimlik = sonKimlik();
  if (typeof kimlik !== "string") return null;
  const { depoKur } = await import("./depo.js");
  return depoKur(KartDepo, kimlik).boyutlar();
}

// ── kayitlar (5D-3: cekirdek/kayitlar.js + kayit_istemci.js; cozme Web Worker'da) ──
let kayitlarSoz = null;

async function kayitlarKurulum() {
  const [k, i, d, w] = await Promise.all([import("./kayitlar.js"), import("./kayit_istemci.js"), import("./depo.js"), import("./isci_kur.js")]);
  const istemci = i.kayitIstemciKur({
    isciKur: w.kayitIsciKur,
    // Worker kurulamazsa ayni islemci ana is parcaciginda: dosya yine YEREL adresten (depo_oku.js) okunur.
    yedekKur: async () => {
      const [v, o] = await Promise.all([import("./kayit_veri.js"), import("./depo_oku.js")]);
      return v.islemciKur({ getir: o.yerelOku });
    },
  });
  return k.kayitlarKur({
    istemci, kartAl,
    depoAl: (kimlik) => d.depoKur(KartDepo, kimlik),
    sonKimlik,
  });
}

export function kayitlarAl() {
  if (!kayitlarSoz) {
    const yeni = kayitlarKurulum();
    kayitlarSoz = yeni;
    yeni.catch(() => { if (kayitlarSoz === yeni) kayitlarSoz = null; });
  }
  return kayitlarSoz;
}

// ── bildirimler (5E-4: cekirdek/bildirim.js; zarf ACILMADAN eklentiye gider) ──
let bildirimNesnesi = null;

export function bildirimAl() {
  if (!bildirimNesnesi) bildirimNesnesi = bildirimKur({ kartAl, eklenti: Bildirim });
  return bildirimNesnesi;
}

// Kabugun saniyelik tikine verilir (kabukDurumu({ bildirimIzle })).
export const bildirimIzle = bildirimIzleyici({ bildirim: { adresYaz: (k, a) => bildirimAl().adresYaz(k, a), yenile: () => bildirimAl().yenile(), izlemeBaslat: (k) => bildirimAl().izlemeBaslat(k), yerel: (k, d, o) => bildirimAl().yerel(k, d, o) } });

// Kayit bu telefondan baslatilinca sorulan "bu kayit icin anlik izleme acilsin mi?" (tekil; Durum ve Canli ayni soruyu gosterir).
export const izlemeSorusu = izlemeSorusuKur({
  bildirim: { durum: (k) => bildirimAl().durum(k), izinIste: () => bildirimAl().izinIste(), izlemeBaslat: (k, s) => bildirimAl().izlemeBaslat(k, s) },
  kimlikAl: () => bildirimKimligi(),
});

// Bildirim ayarinin baktigi kart: bagli olan, yoksa son baglanilan.
export async function bildirimKimligi() {
  try { const d = (await kartAl()).durum(); if (d && typeof d.kimlik === "string") return d.kimlik; } catch { /* son kimlige dus */ }
  return sonKimlik();
}

// Kartin pil testi durumu (ACIL DURDUR seridinin gorunurlugu icin): imzali `GET /pil` — yalniz durum satirlari
// (nokta istenmez). Donus: durum adi | null (okunamadi / taninmadi). Hata yukari CIKAR (kabuk BILINMIYOR sayar).
export async function pilOku() {
  const yanit = await (await kartAl()).istek("GET", PIL_YOLU, [["sira", PIL_SIRA]]);
  return pilDurumuCoz(await yanit.text());
}

// ── paylasim (5F: cekirdek/paylas.js; dosya uygulamanin onbellegine yazilir, Android'in paylasim penceresi acilir) ──
let paylasNesnesi = null;

export function paylasAl() {
  if (!paylasNesnesi) paylasNesnesi = paylasKur({ eklenti: Paylas });
  return paylasNesnesi;
}

export function canliAl() {
  if (!canliSoz) {
    const yeni = canliKurulum();
    canliSoz = yeni;
    yeni.catch(() => { if (canliSoz === yeni) canliSoz = null; });
  }
  return canliSoz;
}
