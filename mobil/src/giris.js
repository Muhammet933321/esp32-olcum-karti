import "./cekirdek/rtc_kapat.js";       // ILK ice aktarim: WebRTC arayuzleri baska hicbir kod calismadan kalkar
// 5P (P1) — telefon uygulamasinin girisi: PC paneli (arayuz3/) + telefon ortami.
// Sira (plan P1): rtc_kapat -> Vue -> telefon ortami (__olcumOrtam) -> panel (arayuz3/app.js).
// Vue npm'in RUNTIME surumu (derleyicisiz, `new Function` yok — CSP K1); panel kuresel `Vue` bekliyor
// (app.js `const { createApp } = Vue`, ekranlar `Vue.markRaw`). Sablonlar derlemede render'a cevrildi
// (araclar/panel_paketle.mjs).
// Gizlilik kapisi (test/gizlilik.test.js): src/ agacinda kuresel nesnenin ADI yasak; tek istisna bu
// dosyadaki `const KURESEL = globalThis;` satiri. Ortam (src/ortam) kuresel nesneyi buradan PARAMETRE alir.
import * as Vue from "vue";

const KURESEL = globalThis;
KURESEL.Vue = Vue;

// Telefon ortami (P3). Dosya henuz yoksa derleme KIRILMAZ: glob bos esleme verir, panel ortamsiz acilir.
const ORTAM_MODULU = import.meta.glob("./ortam/index.js");

/* Acilmama kutusu (src/acilis_bekci.js) belgeye gelen olayi dinler; ayrinti (hata metni) kutuya yazilir. */
function hataBildir(ne, h) {
  const ayrinti = h && h.message ? ` (${h.message})` : "";
  document.dispatchEvent(new CustomEvent("arayuz-hata", { detail: ne + ayrinti }));
}

async function basla() {
  const ortamYukle = ORTAM_MODULU["./ortam/index.js"];
  if (ortamYukle) {
    try {
      const m = await ortamYukle();
      await m.ortamKur({ kuresel: KURESEL });
    } catch (h) {
      // Ortamsiz panel telefonda PC dallarina (kopru yoklamasi, servis iscisi) girerdi: panel ACILMAZ.
      hataBildir("Telefon ortamı", h);
      return;
    }
  }
  try {
    await import("../../arayuz3/app.js");
  } catch (h) {
    hataBildir("app.js", h);
  }
}

basla();
