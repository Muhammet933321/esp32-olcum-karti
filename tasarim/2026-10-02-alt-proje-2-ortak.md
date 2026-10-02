# Alt proje 2 — `ortak/` (tek kopya hesap kodu, düz JS)

> Üst tasarım: `2026-09-29-yazilim-sistemi.md` §4 (alt projeler), §5 (kayıt modeli), §6 (güvenlik),
> §7 (kalibrasyon), §9 (`ortak/`), §10 (doğrulama), Ö1. Alt proje 1 bitti (1A–1E, `main` `7fcc6e2`).
> **Kararlar devredilmiş yetkiyle verildi** (kullanıcı 2026-10-02 gecesi: "sen kendin en mantıklısına
> karar ver ve onunla ilerle, soru sorma"). Sabah gözden geçirilecek; hiçbiri geri alınamaz değil.

## Amaç

Web paneli (3), PC uygulaması (4) ve Android (5) **aynı hesap kodunu** kullansın: kayıt okuma,
imza, eşitleme, kalibrasyon, istatistik, özet katmanları, osiloskop ölçümleri, dışa aktarma.
Python'daki başvuru uygulamaları (`kopru/kayit_bicim.py`, `kayit_esitle.py`, `imza.py`,
`chacha.py`, `bildirim.py`) kartla zaten doğrulandı; JS onlarla **bayt bayt aynı** sonucu vermeli.

## Kararlar

| # | Karar | Gerekçe |
|---|---|---|
| O1 | **Konum ve biçim:** depo kökünde `ortak/`; `ortak/src/*.js` ES modülleri, `ortak/package.json` yalnız `{"type":"module","private":true}` — **bağımlılık YOK**, npm kurulumu yok | Proje kuralı (stdlib/bağımlılıksız); tarayıcı, Node ve Capacitor aynı dosyayı yükler |
| O2 | **Test:** Node 24'ün yerleşik `node:test` + `node:assert`; `ortak/test/*.test.js` | Bağımlılıksız; zincirden `node --test` |
| O3 | **Çapraz uygulama vektörleri:** her dilimin Python üreteci (`uretim/ortak_vektor_<dilim>.py`) başvuru Python koduyla JSON vektör üretir → `ortak/test/vektor/<dilim>.json` (depoda). Zincir: üreteç `--denetle` ile vektörlerin Python'la HÂLÂ aynı olduğunu, `node --test` JS'nin onlarla aynı olduğunu ölçer | "JS ve firmware aynı test vektörlerini kullanır" (§10). Python başvurusu kartla doğrulandı; zincir iki yönü de tutar |
| O4 | **Zincir adımı B73 "ortak/"** (`uretim/test_ortak.py`): vektör denetimi + `node --test` + iddia sayısı | Görünür, kilitli sayım; mutasyon adımı B73 |
| O5 | **Sayılar:** gerilim/akım `Number` (çift duyarlık); ham kodlar ve sayaçlar tamsayı; 64 bit gereken yerde (mikrosaniye, birikimli enerji pJ) `BigInt` ya da bölünmüş hesap — Python'la aynı sonuç ölçütü | Python `float` ile aynı IEEE-754 sonucu → vektörler birebir |
| O6 | **Kripto saf JS** (SHA-256, HMAC, PBKDF2, ChaCha20-Poly1305): `crypto.subtle` YOK (§6: yerel ağda http, güvenli bağlam yok) | §6 |
| O7 | **Ağ (eşitleme istemcisi) `fetch` enjeksiyonla**: modül `fetch` işlevini parametre alır; Node testinde yerel sahte kart (Node `http`) | Tarayıcı/Node/Capacitor aynı kod; test ağsız |
| O8 | **Grafik çekirdeği (uPlot sarmalayıcı) bu alt projede YAPILMAZ → alt proje 3'e** | uPlot dış dosya (indirme kullanıcı izni ister) ve tarayıcıda sınanır (`tarayici.py`); 3'ün görsel tasarım turuyla birlikte |

## Dilimler (sıra)

| Dilim | İçerik | Başvuru |
|---|---|---|
| **2A** | Kayıt okuyucu: çerçeve + CRC, bütün kayıt türleri (BAŞLA, NOKTA, DEVAM, BİTİR, TEKRAR, SAAT, OLAY, NOT, AYRINTI, SKOP), volt/amper çevrimi, `oturumlari_kur`, `ayrinti_ornekler`, skop yakalamaları | `kopru/kayit_bicim.py` |
| **2B** | Kripto + imza + zarf: SHA-256, HMAC, PBKDF2, ChaCha20-Poly1305; 1D kanonik istek imzası, eşleştirme kanıtları; 1E bildirim zarfı + `bilgi_coz` | `kopru/imza.py`, `chacha.py`, `bildirim.py`, `guvenlik.h` |
| 2C | Eşitleme istemcisi (`/kayit/liste`, `/kayit/veri` parça parça, onay, bozuk kayıt, `/kal/liste`) | `kopru/kayit_esitle.py` |
| 2D | İstatistik + özet katmanları (Ö1: tek örneklik sıçrama her yakınlaştırmada görünür), aralık Wh/mAh (boşluklar dahil) | yeni (§9 çizim kuralı) |
| 2E | Osiloskop ölçümleri (frekans, periyot, görev oranı, yükselme) + FFT | `arayuz3` skop kodu + yeni |
| 2F | Dışa aktarma (CSV Excel-TR: `;` + BOM; ham) + rapor içeriği + TR/EN sözlük | yeni |

2A ve 2B birbirinden bağımsız → **paralel**. 2C, 2A + 2B'ye bağlı. 2D yalnız sayı dizileriyle
çalışır → 2A/2B ile **paralel**.

### 2D ayrıntı kararları

| # | Karar | Gerekçe |
|---|---|---|
| D1 | Seri = `t` (Float64Array, ms) + `y` (Float64Array); boşluk = ardışık iki nokta arası > `bosluk_ms` (çağıran verir; kayıtta DEVAM sınırı ya da hız × 2.5) | Kayıt oturumları DEVAM'la bölünür; çizgi boşluğun üstünden geçmemeli (§9 "boşluk kesik çizimi") |
| D2 | **Özet piramidi**: düzey 0 ham; düzey k, `B^k` noktalık blokların min, maks, ilk/son zamanı (B = 8). Kurulum O(n) | 800 bin nokta (Ö6 riski) bellekte ~%15 ek |
| D3 | **Pencere sorgusu** `[t0, t1]`, `W` piksel: aralıktaki ham nokta ≤ 2·W ise **ham noktalar**; değilse blok/sütun ≥ 2 olan en ince düzey seçilir, her piksel sütunu o sütuna düşen blokların min+maksı; verisiz sütun `null` (kesik) | Ö1: tek örneklik sıçrama her yakınlaştırmada bir sütunun uç değeri olarak görünür (zaman hatası ≤ 1 sütun) |
| D4 | **İstatistik ve enerji HER ZAMAN ham veriden** (min/ort/maks/RMS/tepe-tepe; aralık Wh = ∫V·I dt yamuk kuralıyla, mAh = ∫I dt; boşluğun üstünden integral YOK) | §9 çizim kuralı: özetlenen yalnız ekran resmi |
| D5 | Başarım ölçütü (Node): 1 M noktada piramit < 500 ms, pencere sorgusu < 20 ms | Ö6'nın masaüstü ön ölçüsü; telefon ayrı tezgah kalemi |

## Doğrulama

- Her dilimde: RFC/başvuru vektörleri + Python'dan üretilen çapraz vektörler + sınır/bozuk girdi
  (kesik çerçeve, yanlış CRC, bilinmeyen tür, aşırı uzun alan) — JS **reddetmeli**, çökmemeli.
- 2A'da kartın gerçek akışı: kart tezgahında eşitlenen dosya hem Python hem JS ile çözülüp
  karşılaştırılır (tezgah kalemi).
- Mutasyon: her yeni iddianın yalanlayıcısı (`mutasyon.py` adım B73).

## Kapsam dışı

Grafik çekirdeği (→ 3) · ekranlar (3, 5) · PC uygulamasının disk/MQTT kısmı (4).
