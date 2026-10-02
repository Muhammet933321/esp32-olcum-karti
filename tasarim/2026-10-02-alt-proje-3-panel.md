# Alt proje 3 — Web paneli (PC öncelikli; kartın ve PC uygulamasının sunduğu panel)

> Üst tasarım: `2026-09-29-yazilim-sistemi.md` §9 (ekranlar, `ortak/`, rapor, dil), §10, Ö1/Ö6.
> Alt proje 2 (`ortak/`) bitti (`main` 606bb80). **Görsel yön kullanıcının devriyle seçildi**
> (2026-10-02: "ben karar veremedim, sen karar ver"; adaylar
> https://claude.ai/artifact/NHA6NxtMTM1n5aW5MkcATb). Seçilen birleşik maket depo dışında:
> `.yedek/olcum-karti/panel-secilen-tasarim.html`.

## Kararlar

| # | Karar | Gerekçe |
|---|---|---|
| P1 | **Tek düzen, geçişli görünümler.** Düzen = A (sol gezinme şeridi) + B'nin aranabilir kayıt listesi (tür, tarih, süre, **nerede**) + C'nin iki imleci (A/B, aralarında ΔV · ort · mAh · Wh). **Görünümler:** Koyu (A, varsayılan) · Açık (B'nin renkleri) · Ön panel (C'nin grafit + turuncu renkleri, cihaz rakamları). Ayarlar'dan seçilir, tarayıcıda hatırlanır (cihaz başına) | Kullanıcı birden çok tasarım arasında geçiş istedi (2026-10-02). Düzen geçişi her özelliği 3 kez yazdırıp sınatırdı; görünüm geçişi CSS değişkeni, her ekranda kendiliğinden çalışır. Kartta maliyet yalnız birkaç KB, işlemci yükü yok (çizim tarayıcıda) |
| P2 | **Yazı tipi sistemden** (`system-ui` / `ui-monospace`, Windows'ta Segoe UI + Cascadia/Consolas); dış yazı tipi YOK | Kart AP kipinde internetsiz → Google Fonts gelmez; yazı tipini karta gömmek dosya indirmeyi gerektirir (kullanıcı izni). İstenirse IBM Plex ileride gömülür (~60 KB) |
| P3 | **Grafik çekirdeği bizim** (`ortak/src/grafik.js`, `<canvas>`, bağımlılık yok) — ana tasarımdaki uPlot YERİNE | uPlot dış dosya (indirme izni); `ozet.js` Ö1'i zaten BİREBİR sağlıyor (sütun uçları); çizim + etkileşim ~600 satır. Bugünkü panel de kendi kanvasını çiziyor |
| P4 | **Derleme yok, tarayıcının ES modülleri:** `app.js` ekran başına `ekran/*.js` modüllerine bölünür; Vue 3 global yapısı (vendor) kalır; `ortak/src` panelle birlikte karta yazılır (`arayuz-uret.py`) | §9 "derleme adımı yok"; aynı dosyalar kart, köprü ve PC'den sunulur |
| P5 | **Bütçe iddiası:** kartın arayüz görüntüsü (gzip) ≤ 600 KB (bölüm 1.5 MB); `ortak/` dahil | Bugün ~350 KB ham arayüz + 216 KB ham `ortak/`; büyüme sınırı ölçülür |
| P6 | **Kayıtlar tarayıcıda:** eşitleme `ortak/src/esitle.js` + IndexedDB deposu (`depo` arayüzü); grafik/istatistik/dışa aktarma `ortak/`'tan | Tek kopya hesap kodu (§9); PC uygulaması (4) diske yazan depoyu takar |
| P7 | **Dil:** TR + EN, `ortak/src/sozluk.js`; yeni ekranlarda gömülü metin yok, eskiler taşındıkça | §9 Dil |

## Dilimler (sıra)

| Dilim | İçerik | Kabul |
|---|---|---|
| **3A** | Görünüm altyapısı: tasarım belirteçleri (`--…`) üç görünüm için, Ayarlar'da seçim + hatırlama; `app.js`'i davranış DEĞİŞMEDEN modüllere bölme iskeleti; `ortak/` karta yazılır | B7 (test_arayuz3.js) yeşil; başsız tarayıcıda üç görünüm render, konsol hatası yok; bütçe iddiası |
| 3B | Grafik çekirdeği `grafik.js`: çok kanallı çizgi, Ö1 (özet piramidi), boşluk kesik, tekerlek/sürükleme/iki parmak, gezgin şeridi, iki imleç + okuma | Node: sahte kanvas bağlamının çizim çağrılarında Ö1 (sıçrama her yakınlaştırmada) ; başsız tarayıcıda etkileşim |
| 3C | Kayıtlar + Kayıt görünümü: liste (arama, etiket, nerede), eşitleme (IndexedDB), grafik + imleçler, aralık istatistiği, notlar, dışa aktarma (CSV/ham), rapor sayfası | Sahte karta karşı uçtan uca (Python sahte kartı); gerçek kart tezgahı |
| 3D | Canlı (yenilenmiş), kayıt başlat/durdur/plan | Bugünkü iddialar korunur |
| 3E | Osiloskop (`skop.js` ölçümleri + FFT, yakalama günlüğü) | — |
| 3F | Pil testi (yeni kaydediciyle) | — |
| 3G | Karşılaştırma (çok kayıt; eksen zaman / mAh / başlangıçtan beri) | — |
| 3H | Ayarlar: bağlantı, güvenilir cihazlar, bildirimler, kalibrasyon geçmişi, depolama, dil, görünüm, Gelişmiş (konsol) | — |

## Doğrulama

B7 (`test_arayuz3.js`) ve B22 tarayıcı denetimleri genişler; her dilimde başsız tarayıcı (Edge) ile
üç görünümde render + telefon genişliği + konsol hatası yok; yeni iddiaların yalanlayıcı mutasyonu.
Kart tezgahında: panel kartta açılır (STA + AP), ölçüm döngüsünde yeni blokaj yok (`K` satırı).

## Kapsam dışı

Android ekranları (5) · PC uygulamasının disk/bildirim kısmı (4) · yazı tipi gömme (P2, izinle).
