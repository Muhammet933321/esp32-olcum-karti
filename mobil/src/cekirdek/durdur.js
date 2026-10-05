// ACIL DURDURMA dugmesinin mantigi (tasarim A8–A11, Ö7). Tek dokunus, onaysiz, imzasiz.
// KURAL: durdur() cagrildigi anda — ilk await'ten ONCE, ayni gorev turunda — eklentiye gider. Kasa
// kilidi, imza, sayac yazimi, esitleme, kimlik dogrulamasi, yeniden deneme kuyrugu ARAYA GIREMEZ:
// bu modul onlarin hicbirini ice aktarmaz ve hicbirini beklemez. Adresler ESZAMANSIZ okunmaz.
//
//   const d = durdurKur({ p0: ag.p0, adresler: () => ({ liste: [bagliAdres, onbellekAdresi], asil: bagliAdres }) });
//   d.durdur();              // -> Promise<{ tamam, adres, basarili, sureMs }>, ASLA reddetmez, ASLA atmaz
//   d.durum()                // "bos" | "gonderiliyor" | "durduruldu" | "baska-yanit" | "ulasilamadi"
//
// `adresler()` bir dizi (asil adres bilinmiyor) ya da { liste, asil } doner. ASIL adres = bu baglantida
// kimligi dogrulanmis kart; listenin BASINDA durur (eklenti de ilk adresi asil sayar).
//   asil 204 verdi                               -> "durduruldu"
//   asil bilinmiyor, herhangi bir adres 204      -> "durduruldu"
//   asil biliniyor ama yalniz BASKA adres 204    -> "baska-yanit" (kartin durdugu DOGRULANAMADI)
//   hicbiri                                      -> "ulasilamadi"
// Art arda dokunus: suren turlarin EN IYI sonucu gecerlidir (bir tur karti durdurduysa sonraki turun
// basarisizligi seridi kirmiziya cevirmez).
//
// Eslesmemis telefonda da calisir (A11): adres biliniyorsa yeter. Kartin kendi erisim noktasi adresi
// her zaman listeye eklenir (sahada telefon dogrudan karta bagliysa).

export const KART_AP_ADRESI = "192.168.4.1";

const DERECE = Object.freeze({ ulasilamadi: 0, "baska-yanit": 1, durduruldu: 2 });
const YOK = Object.freeze({ tamam: false, adres: null, basarili: Object.freeze([]), sureMs: 0 });

// Bir turun sonucu -> hal. Saf.
export function durdurHali(sonuc, asil) {
  if (!sonuc || sonuc.tamam !== true) return "ulasilamadi";
  if (typeof asil !== "string" || asil === "") return "durduruldu";
  const basarili = Array.isArray(sonuc.basarili) ? sonuc.basarili : [];
  return basarili.includes(asil) || sonuc.adres === asil ? "durduruldu" : "baska-yanit";
}

export function durdurKur({ p0, adresler, degisti = null }) {
  if (typeof p0 !== "function" || typeof adresler !== "function") throw new TypeError("p0 ve adresler gerekli");
  let hal = "bos";
  let suren = 0;                                  // yaniti beklenen tur sayisi
  let enIyi = "ulasilamadi";                      // suren turlarin en iyi sonucu
  const bildir = (h) => { hal = h; if (degisti) { try { degisti(h); } catch { /* arayuz hatasi durdurmayi etkilemez */ } } };

  function bitti(sonuc, asil) {
    const h = durdurHali(sonuc, asil);
    if (DERECE[h] > DERECE[enIyi]) enIyi = h;
    suren -= 1;
    // Kart durduysa HEMEN soylenir; degilse suren baska tur varken hukum verilmez.
    if (enIyi === "durduruldu" || suren === 0) bildir(enIyi);
  }

  function durdur() {
    let liste = [];
    let asil = null;
    try {
      const a = adresler();
      if (Array.isArray(a)) liste = a;
      else if (a && Array.isArray(a.liste)) { liste = a.liste; asil = typeof a.asil === "string" && a.asil !== "" ? a.asil : null; }
    } catch { liste = []; asil = null; }
    const hedefler = [...liste, KART_AP_ADRESI];
    if (suren === 0) enIyi = "ulasilamadi";
    suren += 1;
    let soz;
    try {
      soz = p0(hedefler, { asil });               // ILK is: eklenti cagrisi, hicbir bekleme olmadan
    } catch {
      bitti(null, asil);                          // eklenti koprusu atti: dokunus isleyicisine istisna CIKMAZ
      return Promise.resolve(YOK);
    }
    bildir("gonderiliyor");
    return Promise.resolve(soz).then(
      (s) => { bitti(s, asil); return s; },
      () => { bitti(null, asil); return YOK; },
    );
  }

  return { durdur, durum: () => hal };
}
