// ACIL DURDUR seridinin GORUNURLUGU ve verinin tazeligi (kullanici karari, 2026-10-05; tasarim A8'in guncel hali).
//
// `p0`'in kestigi tek sey kartin yuku (Q1) ve o yalniz PIL TESTINDE calisir; normal olcumde akim dis kaynaktan
// gecer, p0 onu kesemez. Bu yuzden:
//   * pil testinin SURMEDIGI kesin biliniyorsa serit GIZLI
//   * pil testi suruyorsa YA DA durum bilinmiyorsa (kart ulasilamiyor, veri eski, durum okunamadi / eskidi,
//     uygulama yeni acildi ve henuz okumadi) serit GORUNUR.   Suphede HER ZAMAN goster.
// Kaynak: kartin kendi pil durumu (`GET /pil`, ilk satiri `durum=…`) — oturum turu tek basina yetmez (oturumsuz
// pil testi olabilir). Kabuk durumu PIL_YOKLAMA_MS'de bir ve kayit durumu (G satiri) her degistiginde yeniden okur;
// G degisince yeni okuma gelene dek durum BILINMIYOR sayilir.
// Saf: zaman ve ag enjekte; Node'da sinanir.

// Canli akis saniyede ~5 satir yollar; bu kadar suredir HIC veri gelmediyse baglanti "veri gelmiyor" sayilir
// (akisin TCP okuma zaman asimi ~40 s: durum ona degil, son verinin yasina bagli).
export const VERI_ESKI_MS = 5000;
export const PIL_YOKLAMA_MS = 30000;
// Okunan pil durumu bundan eskiyse BILINMIYOR (bir yoklama kacsa da serit geri gelir).
export const PIL_TAZE_MS = 45000;
export const PIL_YOLU = "/pil";
// Nokta istemeden yalniz durum satirlari: kartin pil halkasindaki her siradan buyuk.
export const PIL_SIRA = "2147483647";

// Kartin pil_durum_metni degerleri (kod/olcum-karti-a3: PIL_*). Yalniz CALISIYOR "suruyor"dur.
export const PIL_DURUMLARI = Object.freeze(["BEKLEMEDE", "CALISIYOR", "BITTI", "DURDURULDU", "HATA"]);
export const PIL_BILINMIYOR = Object.freeze({ durum: null, okunduMs: null });

// `/pil` yaniti -> durum adi | null (taninmayan / eksik / bicimsiz: BILINMIYOR). Yalniz baslik bolumune bakilir.
export function pilDurumuCoz(metin) {
  if (typeof metin !== "string") return null;
  const bas = metin.split("\n--\n")[0];
  let durum = null;
  for (const satir of bas.split("\n")) {
    if (!satir.startsWith("durum=")) continue;
    if (durum !== null) return null;                    // iki durum satiri: guvenme
    durum = satir.slice(6).trim();
  }
  return PIL_DURUMLARI.includes(durum) ? durum : null;
}

// Pil testinin SURMEDIGI kesin mi? Kosullarin HEPSI tutmali; biri bile tutmazsa "bilinmiyor / suruyor".
//   bagli       : kart bu baglantida dogrulanmis ve eslesmis
//   akisHal     : canli akisin hali ("acik" olmali — "eski", "hata", "baglaniyor", "dolu" degil)
//   veriYasMs   : son veriden beri gecen sure (taze olmali)
//   pil         : { durum, okunduMs } — son /pil okumasi
//   oturumTuru  : etkin kaydin turu (2 = pil oturumu -> suruyor say)
export function pilSurmuyorKesin({ bagli = false, akisHal = null, veriYasMs = null, pil = null, oturumTuru = null, simdiMs = 0 } = {}) {
  if (bagli !== true || akisHal !== "acik") return false;
  if (!Number.isFinite(veriYasMs) || veriYasMs < 0 || veriYasMs > VERI_ESKI_MS) return false;
  if (oturumTuru === 2) return false;
  if (!pil || typeof pil.durum !== "string" || !PIL_DURUMLARI.includes(pil.durum) || pil.durum === "CALISIYOR") return false;
  if (!Number.isFinite(pil.okunduMs)) return false;
  const yas = simdiMs - pil.okunduMs;
  return yas >= 0 && yas <= PIL_TAZE_MS;
}

// Serit gorunur mu? (Suphede goster.)
export function durdurGorunur(girdi) {
  return !pilSurmuyorKesin(girdi);
}

// Akis "acik" gorunuyor ama veri eskidiyse gercek hal "eski"dir.
export function akisHali(hal, sonGorulmeMs, simdiMs) {
  if (hal !== "acik") return hal;
  if (!Number.isFinite(sonGorulmeMs)) return hal;
  return simdiMs - sonGorulmeMs > VERI_ESKI_MS ? "eski" : "acik";
}
