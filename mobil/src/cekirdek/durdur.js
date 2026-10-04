// ACIL DURDURMA dugmesinin mantigi (tasarim A8–A11, Ö7). Tek dokunus, onaysiz, imzasiz.
// KURAL: durdur() cagrildigi anda — ilk await'ten ONCE, ayni gorev turunda — eklentiye gider. Kasa
// kilidi, imza, sayac yazimi, esitleme, kimlik dogrulamasi, yeniden deneme kuyrugu ARAYA GIREMEZ:
// bu modul onlarin hicbirini ice aktarmaz ve hicbirini beklemez. Adresler ESZAMANSIZ okunmaz.
//
//   const d = durdurKur({ p0: ag.p0, adresler: () => [bagliAdres, onbellekAdresi] });
//   d.durdur();              // -> Promise<{ tamam, adres, sureMs }>, ASLA reddetmez
//   d.durum()                // "bos" | "gonderiliyor" | "durduruldu" | "ulasilamadi"
//
// Eslesmemis telefonda da calisir (A11): adres biliniyorsa yeter. Kartin kendi erisim noktasi adresi
// her zaman listeye eklenir (sahada telefon dogrudan karta bagliysa).

export const KART_AP_ADRESI = "192.168.4.1";

export function durdurKur({ p0, adresler, degisti = null }) {
  if (typeof p0 !== "function" || typeof adresler !== "function") throw new TypeError("p0 ve adresler gerekli");
  let hal = "bos";
  let sira = 0;
  const bildir = (h) => { hal = h; if (degisti) { try { degisti(h); } catch { /* arayuz hatasi durdurmayi etkilemez */ } } };

  function durdur() {
    const no = ++sira;
    let liste = [];
    try { liste = adresler(); } catch { liste = []; }
    const hedefler = [...(Array.isArray(liste) ? liste : []), KART_AP_ADRESI];
    const soz = p0(hedefler);                     // ILK is: eklenti cagrisi, hicbir bekleme olmadan
    bildir("gonderiliyor");
    return Promise.resolve(soz).then(
      (s) => { if (no === sira) bildir(s && s.tamam === true ? "durduruldu" : "ulasilamadi"); return s; },
      () => { if (no === sira) bildir("ulasilamadi"); return { tamam: false, adres: null, sureMs: 0 }; },
    );
  }

  return { durdur, durum: () => hal };
}
