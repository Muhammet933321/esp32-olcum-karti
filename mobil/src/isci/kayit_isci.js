// Web Worker kabugu (A24): kayit dosyasini YEREL adresten okur (cekirdek/depo_oku.js — aga cikmaz)
// ve cozer; ana is parcacigi donmaz. Mantik cekirdek/kayit_veri.js'te (Node'da sinanir).
// Mesaj: { no, is, ...arguman } -> { no, tamam, sonuc | tur }.
import { yerelOku } from "../cekirdek/depo_oku.js";
import { islemciKur } from "../cekirdek/kayit_veri.js";

const islemci = islemciKur({ getir: yerelOku });

self.onmessage = async (e) => {
  const { no, is, ...arguman } = e.data || {};
  try {
    self.postMessage({ no, tamam: true, sonuc: await islemci.isle(is, arguman) });
  } catch (h) {
    self.postMessage({ no, tamam: false, tur: h && typeof h.tur === "string" ? h.tur : "ic-hata" });
  }
};
