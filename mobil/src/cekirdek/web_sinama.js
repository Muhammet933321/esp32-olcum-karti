// WebView'in KENDI BASINA aga cikamadiginin cihazda olcumu (kural: aga cikan tek yol KartAg).
// Her yol denenir; sonuc "engellendi" ya da "GECTI". Hedef zararsiz, herkese acik bir ornek adres;
// engel calisiyorsa oraya hicbir istek gitmez.
export const SINAMA_ADRESLERI = Object.freeze(["http://example.com/", "https://example.com/"]);

const bekle = (ms) => new Promise((c) => setTimeout(c, ms));

async function fetchDene(adres) {
  try {
    const y = await fetch(adres, { mode: "no-cors", cache: "no-store" });
    // Kapi 403 dondururse govde bos ve durum 403'tur; "opaque" (durum 0) GECTI demektir.
    return y.status === 403 ? "engellendi" : "GECTI";
  } catch {
    return "engellendi";
  }
}

function xhrDene(adres) {
  return new Promise((coz) => {
    try {
      const x = new XMLHttpRequest();
      x.open("GET", adres);
      x.timeout = 4000;
      x.onload = () => coz(x.status >= 200 && x.status < 400 ? "GECTI" : "engellendi");
      x.onerror = () => coz("engellendi");
      x.ontimeout = () => coz("engellendi");
      x.send();
    } catch {
      coz("engellendi");
    }
  });
}

function resimDene(adres) {
  return new Promise((coz) => {
    const r = new Image();
    r.onload = () => coz("GECTI");
    r.onerror = () => coz("engellendi");
    setTimeout(() => coz("engellendi"), 4000);
    r.src = `${adres}favicon.ico?${Date.now()}`;
  });
}

function betikDene(adres) {
  return new Promise((coz) => {
    const b = document.createElement("script");
    b.onload = () => coz("GECTI");
    b.onerror = () => coz("engellendi");
    setTimeout(() => coz("engellendi"), 4000);
    b.src = `${adres}x.js?${Date.now()}`;
    document.head.appendChild(b);
  });
}

async function cerceveDene(adres) {
  const c = document.createElement("iframe");
  c.style.display = "none";
  let yuklendi = false;
  c.onload = () => { yuklendi = true; };
  c.src = adres;
  document.body.appendChild(c);
  await bekle(2500);
  // Engellenen cerceve ya hic yuklenmez ya da bos (403) yuklenir; iki durumda da icerik yoktur.
  // Capraz koken oldugu icin icerik okunamaz: karar yerel kapinin 403'une dayanir (birim testi).
  c.remove();
  return yuklendi ? "bos-yuklendi" : "engellendi";
}

// Gezinti: engel calisiyorsa sayfa yerinde kalir ve bu islev DONER.
async function gezintiDene(adres) {
  window.location.href = adres;
  await bekle(1500);
  return window.location.origin === "https://localhost" ? "engellendi" : "GECTI";
}

export async function webSinama() {
  const sonuc = [];
  for (const adres of SINAMA_ADRESLERI) {
    sonuc.push({ yol: "fetch", adres, sonuc: await fetchDene(adres) });
    sonuc.push({ yol: "xhr", adres, sonuc: await xhrDene(adres) });
    sonuc.push({ yol: "img", adres, sonuc: await resimDene(adres) });
    sonuc.push({ yol: "script", adres, sonuc: await betikDene(adres) });
    sonuc.push({ yol: "iframe", adres, sonuc: await cerceveDene(adres) });
  }
  sonuc.push({ yol: "gezinti", adres: SINAMA_ADRESLERI[0], sonuc: await gezintiDene(SINAMA_ADRESLERI[0]) });
  return sonuc;
}
