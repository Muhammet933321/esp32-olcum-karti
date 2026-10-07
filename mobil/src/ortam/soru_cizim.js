// Anlik izleme sorusunun kutusu: Vue render islevi (sablon derleyicisi YOK — CSP K1), panelin sinif ve
// belirtecleriyle (.uyari, button.birincil, --kart, --golge-2). Kutu belgenin GOVDESINE eklenir (panelin
// `#uyg`'sine dokunmaz) ve YALNIZ kendi dugumunu kaldirir: Vue `render(vnode, govde)` kabin mevcut
// cocuklarini silmez, sona ekler.
// Katman (modal) DEGIL: alta sabit, ince bir serit; ekrani ortmez, ACIL DURDUR seridinin uzerine binmez
// (serit icerigin ustunde, akista). Metinler sozluk_mobil.js'ten (eski ekranin anahtarlari).

import { h, render } from "vue";
import { ceviriMobil } from "../cekirdek/sozluk_mobil.js";

const KUTU_STIL = "position:fixed;left:12px;right:12px;bottom:12px;z-index:50;margin:0;"
  + "background-color:var(--kart);box-shadow:var(--golge-2);max-width:640px;margin-inline:auto";
const DUGMELER_STIL = "display:flex;gap:8px;flex-wrap:wrap;margin-top:8px";
const DUGME_STIL = "min-height:44px;min-width:88px";

const SONUC_ANAHTARI = Object.freeze({ acildi: "m.bl.soru_acildi", acilamadi: "m.bl.soru_acilamadi" });

// g (soru.js) -> vnode | null. Saf (DOM'a dokunmaz).
export function soruDugumu(g, dil = "tr") {
  if (!g) return null;
  if (g.soru) {
    return h("div", {
      id: "ortam-izleme-soru", class: "uyari", role: "alertdialog", "aria-modal": "false",
      "aria-labelledby": "ortam-izleme-soru-metin", "aria-busy": g.mesgul ? "true" : "false", style: KUTU_STIL,
    }, [
      h("p", { id: "ortam-izleme-soru-metin", style: "margin:0" }, ceviriMobil("m.bl.soru", dil)),
      h("div", { style: DUGMELER_STIL }, [
        h("button", { type: "button", class: "birincil", "data-ortam-soru": "evet", disabled: g.mesgul === true, style: DUGME_STIL, onClick: g.evet },
          ceviriMobil("m.bl.soru_evet", dil)),
        h("button", { type: "button", "data-ortam-soru": "hayir", disabled: g.mesgul === true, style: DUGME_STIL, onClick: g.hayir },
          ceviriMobil("m.bl.soru_hayir", dil)),
      ]),
    ]);
  }
  const anahtar = SONUC_ANAHTARI[g.hal];
  if (!anahtar) return null;
  return h("div", { id: "ortam-izleme-soru", class: "uyari", role: "status", style: KUTU_STIL },
    [h("p", { id: "ortam-izleme-soru-metin", style: "margin:0" }, ceviriMobil(anahtar, dil))]);
}

// ciz(g): soru.js'in cizicisi. Govde yoksa (belge hazir degil) hicbir sey yapmaz.
export function vueCizici({ belge, dilAl = () => "tr" }) {
  return (g) => {
    const govde = belge && belge.body;
    if (!govde) return;
    render(soruDugumu(g, dilAl() === "en" ? "en" : "tr"), govde);
  };
}
