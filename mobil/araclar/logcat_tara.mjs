// Logcat sir tarayicisi (tasarim A45; kullanici sarti). Cihazdan alinan logcat dosyasinda sir ya da
// sir tasiyan bicim arar; bulursa SATIR NUMARASI + DESEN ADI yazar — degerin kendisini ASLA yazmaz.
//
//   node araclar/logcat_tara.mjs <logcat dosyasi> [--sir <metin>]...
//   cikis 0: temiz   1: bulgu var   2: kullanim hatasi / dosya okunamadi / bos dosya
//
// --sir: sinamada kullanilan bilinen sir (parola, K'nin onaltiligi ...). Aranan bicimler:
//   * duz; URL kodlu (%XX), form kodlu ('+' = bosluk), JSON kacisli (\uXXXX, \")
//   * onaltilik: bitisik, bosluklu, iki noktali, 0x onekli; UTF-16LE baytlarinin onaltiligi
//   * ondalik bayt dokumu: Kotlin contentToString "[1, -2, 3]" (isaretli) ve JS "1,254,3"
//   * base64 / base64url (uc hizalama: baska verinin icine gomulu olsa da bulunur)
//   * yukaridakilerin IKI SATIRA bolunmus hali (76 sutunda kirilan base64, uzun onaltilik)
// Sir onaltilik yaziliysa ham baytlari da aranir (K, Kasa eklentisine base64 gider).
// --sir OLMADAN yalniz DESENLER calisir. "onaltilik-40-ozet-olabilir" her uzun onaltiligi yakalar:
// APK / sertifika sha256 ozeti de alarm verir (guvenli taraf — satira bakip karar verilir).
// Dosya UTF-8 ya da UTF-16 olabilir (PowerShell yonlendirmesi UTF-16 yazar).

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SIR_EN_AZ = 6;                  // daha kisa "sir" her satirda rastlantiyla gecer

export const DESENLER = Object.freeze([
  // imzali istegin basliklari / sorgu bicimi (EventSource): hic gunluge dusmemeli
  { ad: "imza-basligi", re: /X-(?:Imza|Sayac|Cihaz)(?![A-Za-z0-9])/i },
  { ad: "imza-sorgusu", re: /(?:^|[?&\s"'(,;])_[isc]=/ },
  // 40+ onaltilik: K, P, imza, kanit — kirpilmis (63 hane) olsa da. sha256 ozeti de buraya duser.
  { ad: "onaltilik-40-ozet-olabilir", re: /(?<![0-9A-Fa-f])[0-9A-Fa-f]{40,}(?![0-9A-Fa-f])/ },
  { ad: "kanit", re: /kanit["']?\s*[=:]/i },
  // parola / password sozcugu ve ardindan bir DEGER ("yok", "null" ... deger degildir)
  { ad: "parola", re: /(?:parola|password|passwd)[A-Za-z_]*["']?\s*[:=]\s*["']?(?!(?:yok|null|none|bos|undefined)(?![A-Za-z0-9]))[^\s"']/i },
  // anahtar= / sifre= / secret= / key= (apiKey=, API_KEY= dahil; "monkey=" degil) ve ardindan bir DEGER
  { ad: "gizli-alan", re: /(?:[Aa]nahtar|ANAHTAR|[SsŞş]ifre|[Ss]ecret|SECRET|(?<![A-Za-z])key|Key|KEY)["']?\s*[:=]\s*["']?(?!(?:yok|null|none|bos|undefined)(?![A-Za-z0-9]))[^\s"']/ },
  // Capacitor kopru gunlugu: her eklenti cagrisinin TUM verisi
  { ad: "kopru-gunlugu", re: /methodData/ },
  // "kimlik" sozcugunun yaninda 16 onaltilik (kart kimligi)
  { ad: "kart-kimligi", re: /kimlik[^0-9A-Za-z]{0,12}(?<![0-9A-Fa-f])[0-9a-f]{16}(?![0-9A-Fa-f])/i },
  // ozel IPv4 + kart yolu
  { ad: "ozel-adres-yolu", re: /(?<![0-9.])(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}(?::\d{1,5})?\/(?:eslestir|komut|kayit)/ },
]);

// Baytlarin, daha uzun bir verinin icinde hangi hizada dururlarsa dursunlar base64 yazimlarinda
// DEGISMEDEN gorunen parcalari (uc hizalama).
function base64Parcalari(bayt) {
  const parcalar = [];
  for (let kayma = 0; kayma < 3; kayma++) {
    const tam = Buffer.concat([Buffer.alloc(kayma), bayt]).toString("base64").replace(/=+$/, "");
    const bas = [0, 2, 3][kayma];
    const son = (kayma + bayt.length) % 3 === 0 ? tam.length : tam.length - 1;
    const parca = tam.slice(bas, son);
    if (parca.length >= 8) parcalar.push(parca);
  }
  return parcalar;
}

// %XX dizilerini UTF-8 olarak cozer; bozuk kacis satiri DUSURMEZ (decodeURIComponent atardi).
function yuzdeCoz(s) {
  return s.replace(/(?:%[0-9A-Fa-f]{2})+/g, (m) => Buffer.from(m.replace(/%/g, ""), "hex").toString("utf8"));
}

// JSON / JS dizgi kacislari: \uXXXX ve \" \' \\ \/
function kacisCoz(s) {
  return s.replace(/\\u([0-9A-Fa-f]{4})/g, (_, h) => String.fromCharCode(parseInt(h, 16))).replace(/\\(["'\\/])/g, "$1");
}

// Satirdaki tamsayilar bayt dizisi olarak: ",0,17,254," — isaretli (-128..-1) ve isaretsiz yazim AYNI
// bayta iner; bayt olamayacak sayi diziyi keser.
function ondalikDokum(satir) {
  const sayilar = satir.match(/-?\d+/g) || [];
  return "," + sayilar.map((t) => { const n = Number(t); return n >= -128 && n <= 255 ? n & 255 : "x"; }).join(",") + ",";
}

function sirArayici(sir) {
  const bayt = Buffer.from(sir, "utf8");
  const duz = [sir];
  const kucuk = [bayt.toString("hex")];                 // satirin kucuk harfli halinde aranir
  const b64 = base64Parcalari(bayt);
  const diziler = [bayt];                               // ondalik dokumu aranacak bayt dizileri
  if (/^(?:[0-9A-Fa-f]{2})+$/.test(sir)) {
    kucuk.push(sir.toLowerCase());
    b64.push(...base64Parcalari(Buffer.from(sir, "hex")));
    diziler.push(Buffer.from(sir, "hex"));
  } else {
    kucuk.push(Buffer.from(sir, "utf16le").toString("hex"));
  }
  const ondalik = diziler.map((b) => "," + Array.from(b).join(",") + ",");
  return (satir) => {
    // duz + kodlanmis metin (parola bir URL'de, form govdesinde ya da JSON dizgisinde gecebilir)
    const metinler = [satir, yuzdeCoz(satir), yuzdeCoz(satir.replace(/\+/g, " ")), kacisCoz(satir)];
    if (duz.some((d) => metinler.some((m) => m.includes(d)))) return true;
    // onaltilik: ayraclar (bosluk, ':', ',', "0x") atilinca bitisik yazima iner
    const k = satir.toLowerCase();
    const ayracsiz = [k, k.replace(/[^0-9a-f]/g, ""), k.replace(/0x/g, "").replace(/[^0-9a-f]/g, "")];
    if (kucuk.some((d) => ayracsiz.some((m) => m.includes(d)))) return true;
    const dokum = ondalikDokum(satir);
    if (ondalik.some((d) => dokum.includes(d))) return true;
    const standart = satir.replace(/-/g, "+").replace(/_/g, "/");     // base64url -> standart alfabe
    return b64.some((d) => satir.includes(d) || standart.includes(d));
  };
}

// Logcat satir onu (threadtime: "10-04 12:00:00.000  1234  1234 D Etiket: " | brief: "D/Etiket( 1234): ").
// Iki satira bolunmus bir deger aranirken IKINCI satirin onu atilir.
const SATIR_ONU = /^(?:\d\d-\d\d\s+\d\d:\d\d:\d\d\.\d+\s+\d+\s+\d+\s+[VDIWEFA]\s+[^:]*:\s?|[VDIWEFA]\/[^(]*\(\s*\d+\):\s?)/;

/** -> [{ satir, desen }]; satir 1'den baslar. Bulgu DEGERI tasimaz. */
export function tara(metin, sirlar = []) {
  const arayicilar = sirlar.map((s, i) => ({ ad: `sir-${i + 1}`, var: sirArayici(s) }));
  const bulgular = [];
  const satirlar = metin.split(/\r?\n/);
  const tek = arayicilar.map((a) => satirlar.map((s) => a.var(s)));
  for (let i = 0; i < satirlar.length; i++) {
    for (const d of DESENLER) if (d.re.test(satirlar[i])) bulgular.push({ satir: i + 1, desen: d.ad });
    for (let j = 0; j < arayicilar.length; j++) {
      if (tek[j][i]) { bulgular.push({ satir: i + 1, desen: arayicilar[j].ad }); continue; }
      // Iki satira bolunmus sir: hicbir satirda tek basina yok, birlesimde var -> ILK satirda bildirilir.
      if (i + 1 >= satirlar.length || tek[j][i + 1]) continue;
      const birlesik = satirlar[i].trimEnd() + satirlar[i + 1].replace(SATIR_ONU, "");
      if (arayicilar[j].var(birlesik)) bulgular.push({ satir: i + 1, desen: arayicilar[j].ad });
    }
  }
  return bulgular;
}

/** Dosya baytlari -> metin (UTF-8 / UTF-16 LE-BE, BOM'lu ya da BOM'suz). */
export function metinCoz(bayt) {
  const b = Buffer.from(bayt);
  if (b.length >= 2 && b[0] === 0xff && b[1] === 0xfe) return b.subarray(2).toString("utf16le");
  if (b.length >= 2 && b[0] === 0xfe && b[1] === 0xff) return Buffer.from(b.subarray(2)).swap16().toString("utf16le");
  // BOM'suz UTF-16LE: ASCII agirlikli metinde tek konumlu baytlarin cogu 0'dir.
  const n = Math.min(b.length, 512);
  let sifir = 0;
  for (let i = 1; i < n; i += 2) if (b[i] === 0) sifir++;
  if (n >= 8 && sifir > n / 4) return b.toString("utf16le");
  return b.toString("utf8");
}

function ana(argumanlar) {
  const sirlar = [];
  let dosya = null;
  for (let i = 0; i < argumanlar.length; i++) {
    if (argumanlar[i] === "--sir") {
      const s = argumanlar[++i];
      if (typeof s !== "string" || s.length < SIR_EN_AZ) {
        console.error(`--sir en az ${SIR_EN_AZ} karakterlik bir deger ister`);
        return 2;
      }
      sirlar.push(s);
    } else if (dosya === null) {
      dosya = argumanlar[i];
    } else {
      console.error("tek bir logcat dosyasi verilmeli");
      return 2;
    }
  }
  if (dosya === null) {
    console.error("kullanim: node araclar/logcat_tara.mjs <logcat dosyasi> [--sir <metin>]...");
    return 2;
  }
  let metin;
  try {
    metin = metinCoz(readFileSync(dosya));
  } catch {
    console.error("logcat dosyasi okunamadi");
    return 2;
  }
  if (metin.trim() === "") {
    console.error("logcat dosyasi BOS — olcum yapilmamis sayilir");
    return 2;
  }
  const bulgular = tara(metin, sirlar);
  for (const b of bulgular) console.log(`satir ${b.satir}: ${b.desen}`);
  const satirSayisi = metin.split(/\r?\n/).length;
  console.log(bulgular.length ? `${bulgular.length} bulgu (${satirSayisi} satir, ${sirlar.length} sir)` : `temiz (${satirSayisi} satir, ${sirlar.length} sir)`);
  return bulgular.length ? 1 : 0;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) process.exit(ana(process.argv.slice(2)));
