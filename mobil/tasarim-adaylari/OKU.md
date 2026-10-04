# Görsel tasarım adayları (A44)

Üç durağan maket; uygulama koduna dokunmaz. Tarayıcıda (ya da telefonda) doğrudan açılır, ağ gerekmez.

| Dosya | Aday | Asıl / karşıt tema | DURDUR düğmesi |
|---|---|---|---|
| `aday-a.html` | A — Tezgah | Koyu / Açık | sekmelerin hemen üstünde tam genişlik kırmızı şerit. |
| `aday-b.html` | B — Sade | Açık / Koyu | üst çubukta sağda, hap biçiminde. |
| `aday-c.html` | C — Ön panel | Ön panel (koyu) / Ön panel (açık) | sağ altta yuvarlak kırmızı düğme (sekmelerin üstündeki eylem bandında). |

Her dosyada 6 çerçeve (360 × 760): üst satır asıl tema, alt satır karşıt tema; sütunlar Durum · Canlı · Kayıt görünümü.

Dosyalar `uret.mjs` ile ÜRETİLİR (`node uret.mjs`); elle düzenleme. Renkler `arayuz3/style.css`'in
`koyu` · `acik` · `onpanel` bloklarından birebir. Burada türetilenler: `onpanel-acik` takımı (panelde yok)
ve DURDUR dolgusu (`#c62828` / `#c2361f` + beyaz). `--cok-soluk` hiçbir adayda metin rengi olarak kullanılmadı
(koyu temada kart üstünde 4.5'in altında).

## Ölçüm sonuçları (dokunma alanı, %130 yazı boyutu)

Başsız Edge (Chromium), pencere 1400 × 2000, 3 dosya × 6 çerçeve = 18 çerçeve; her biri dört koşulda:
kök yazı boyutu %100 ve %130, eş aralıklı yazı Consolas (0.55 em) ve "Courier New" (0.60 em — Android'in
eş aralıklı yazısının genişliği). Araç: olc.mjs (node olc.mjs aday-a.html "msedge.exe yolu").

| Ölçülen | Sonuç |
|---|---|
| Çerçeve boyutu | 18/18 tam 360 × 760 |
| En küçük dokunma alanı (bütün button'lar: sekmeler, seçiciler, geri, gezgin şeridi, düğmeler) | **48.0 px** (%100); %130'da 62.4 px — 48'in altında hiçbiri yok |
| DURDUR boyutu (%100) | A 328 × 56 · B 118.8 × 56 · C 72 × 72 (daire) |
| DURDUR en üstte mi (elementFromPoint), çerçeve içinde mi | 72/72 koşulda evet |
| Düğmelerin görünür alanda birbirine binmesi | 0 |
| Yatay taşma / kırpılan metin / ebeveyninden taşan öğe / ikinci satıra saran rakam | 0 (dört koşulda da) |
| %100'de dikey kaydırma gereği | 0 px (her ekran tek sayfaya sığıyor) |
| %130'da dikey kaydırma | A 95–224 px · B 137–215 px · C 103–231 px — yalnız içerik alanı kayar; üst çubuk, DURDUR ve sekmeler yerinde kalır |

%130 notları: C'de "KAYDI BAŞLAT" iki satıra iner (düğme büyür, taşma yok); C'nin LED çubuğu daralır.
İlk ölçümde bulunan ve düzeltilenler: B'de "Kayıt" başlığı %130'da kırpılıyordu (DURDUR dolgusu azaltıldı);
C'de 3.5 rem gerilim rakamı %130'da göstergeden taşıyordu (3 rem + etiket üst satıra); üçlü V/A/W
hücrelerinde "12.482 V" ikinci satıra sarıyordu (birim etikete alındı).

## Kontrast (WCAG 2.x, hesap `uret.mjs` içinde; 4.5 altı çift betiği kırmızı bitirir)

Sayfa etiketi (çerçevelerin dışı): `#1b1d20` / `#c5c7ca` = 9.97

### Aday A — Koyu

| Nerede | Metin | Zemin | Oran |
|---|---|---|---|
| asıl metin · sayfa | `#dee7ef` | `#0b0f14` | 15.36 |
| asıl metin · kart | `#dee7ef` | `#131c25` | 13.75 |
| asıl metin · çubuk / gömük ekran | `#dee7ef` | `#101821` | 14.29 |
| ikincil metin · sayfa | `#94a3b3` | `#0b0f14` | 7.46 |
| ikincil metin · kart | `#94a3b3` | `#131c25` | 6.68 |
| ikincil metin · çubuk / gömük ekran | `#94a3b3` | `#101821` | 6.94 |
| etkin sekme | `#4cc4e0` | `#101821` | 8.75 |
| vurgu metni · sayfa | `#4cc4e0` | `#0b0f14` | 9.41 |
| vurgu metni · kart | `#4cc4e0` | `#131c25` | 8.42 |
| seçili seçenek | `#4cc4e0` | `#0d2a34` | 7.35 |
| ana düğme yazısı | `#05131a` | `#4cc4e0` | 9.22 |
| DURDUR yazısı | `#ffffff` | `#c62828` | 5.62 |
| bağlantı metni (iyi) | `#74d99b` | `#0c2a1c` | 8.90 |
| V rakamı · kart | `#6ea8fe` | `#131c25` | 7.12 |
| A rakamı · kart | `#f2a33c` | `#131c25` | 8.26 |
| W rakamı · kart | `#35d39a` | `#131c25` | 8.96 |

En düşük: **5.62**

### Aday A — Açık

| Nerede | Metin | Zemin | Oran |
|---|---|---|---|
| asıl metin · sayfa | `#18202a` | `#f4f5f7` | 15.05 |
| asıl metin · kart | `#18202a` | `#ffffff` | 16.42 |
| asıl metin · çubuk / gömük ekran | `#18202a` | `#ffffff` | 16.42 |
| ikincil metin · sayfa | `#5b6775` | `#f4f5f7` | 5.29 |
| ikincil metin · kart | `#5b6775` | `#ffffff` | 5.77 |
| ikincil metin · çubuk / gömük ekran | `#5b6775` | `#ffffff` | 5.77 |
| etkin sekme | `#0b5d67` | `#ffffff` | 7.57 |
| vurgu metni · sayfa | `#0b5d67` | `#f4f5f7` | 6.94 |
| vurgu metni · kart | `#0b5d67` | `#ffffff` | 7.57 |
| seçili seçenek | `#0b5d67` | `#e3f1f2` | 6.53 |
| ana düğme yazısı | `#ffffff` | `#0b5d67` | 7.57 |
| DURDUR yazısı | `#ffffff` | `#c62828` | 5.62 |
| bağlantı metni (iyi) | `#15784f` | `#e4f4ec` | 4.82 |
| V rakamı · kart | `#2f63c6` | `#ffffff` | 5.64 |
| A rakamı · kart | `#a85a06` | `#ffffff` | 5.08 |
| W rakamı · kart | `#15784f` | `#ffffff` | 5.48 |

En düşük: **4.82**

### Aday B — Açık

| Nerede | Metin | Zemin | Oran |
|---|---|---|---|
| asıl metin · sayfa | `#18202a` | `#f4f5f7` | 15.05 |
| asıl metin · kart | `#18202a` | `#ffffff` | 16.42 |
| asıl metin · çubuk / gömük ekran | `#18202a` | `#ffffff` | 16.42 |
| ikincil metin · sayfa | `#5b6775` | `#f4f5f7` | 5.29 |
| ikincil metin · kart | `#5b6775` | `#ffffff` | 5.77 |
| ikincil metin · çubuk / gömük ekran | `#5b6775` | `#ffffff` | 5.77 |
| etkin sekme etiketi (hap zemini) | `#18202a` | `#e3f1f2` | 14.18 |
| vurgu metni · sayfa | `#0b5d67` | `#f4f5f7` | 6.94 |
| seçili seçenek | `#0b5d67` | `#e3f1f2` | 6.53 |
| ana düğme yazısı | `#ffffff` | `#0b5d67` | 7.57 |
| DURDUR yazısı | `#ffffff` | `#c62828` | 5.62 |
| bağlantı metni (iyi) · sayfa | `#15784f` | `#f4f5f7` | 5.02 |
| V rakamı · sayfa | `#2f63c6` | `#f4f5f7` | 5.17 |
| A rakamı · sayfa | `#a85a06` | `#f4f5f7` | 4.66 |
| W rakamı · sayfa | `#15784f` | `#f4f5f7` | 5.02 |

En düşük: **4.66**

### Aday B — Koyu

| Nerede | Metin | Zemin | Oran |
|---|---|---|---|
| asıl metin · sayfa | `#dee7ef` | `#0b0f14` | 15.36 |
| asıl metin · kart | `#dee7ef` | `#131c25` | 13.75 |
| asıl metin · çubuk / gömük ekran | `#dee7ef` | `#101821` | 14.29 |
| ikincil metin · sayfa | `#94a3b3` | `#0b0f14` | 7.46 |
| ikincil metin · kart | `#94a3b3` | `#131c25` | 6.68 |
| ikincil metin · çubuk / gömük ekran | `#94a3b3` | `#101821` | 6.94 |
| etkin sekme etiketi (hap zemini) | `#dee7ef` | `#0d2a34` | 12.01 |
| vurgu metni · sayfa | `#4cc4e0` | `#0b0f14` | 9.41 |
| seçili seçenek | `#4cc4e0` | `#0d2a34` | 7.35 |
| ana düğme yazısı | `#05131a` | `#4cc4e0` | 9.22 |
| DURDUR yazısı | `#ffffff` | `#c62828` | 5.62 |
| bağlantı metni (iyi) · sayfa | `#74d99b` | `#0b0f14` | 11.11 |
| V rakamı · sayfa | `#6ea8fe` | `#0b0f14` | 7.96 |
| A rakamı · sayfa | `#f2a33c` | `#0b0f14` | 9.22 |
| W rakamı · sayfa | `#35d39a` | `#0b0f14` | 10.01 |

En düşük: **5.62**

### Aday C — Ön panel (koyu)

| Nerede | Metin | Zemin | Oran |
|---|---|---|---|
| asıl metin · sayfa | `#e4e6e8` | `#16181b` | 14.22 |
| asıl metin · kart | `#e4e6e8` | `#1d2024` | 13.07 |
| asıl metin · çubuk / gömük ekran | `#e4e6e8` | `#101214` | 15.00 |
| ikincil metin · sayfa | `#9aa1a8` | `#16181b` | 6.81 |
| ikincil metin · kart | `#9aa1a8` | `#1d2024` | 6.26 |
| ikincil metin · çubuk / gömük ekran | `#9aa1a8` | `#101214` | 7.18 |
| etkin sekme | `#f5a524` | `#101214` | 9.20 |
| vurgu metni · sayfa | `#f5a524` | `#16181b` | 8.72 |
| vurgu metni · kart | `#f5a524` | `#1d2024` | 8.01 |
| seçili seçenek | `#f5a524` | `#33260f` | 7.22 |
| ana düğme yazısı | `#1b1203` | `#f5a524` | 9.07 |
| DURDUR yazısı | `#ffffff` | `#c2361f` | 5.47 |
| bağlantı metni (iyi) · çubuk | `#7fd99a` | `#101214` | 10.99 |
| V rakamı · gömük ekran | `#8fb6ff` | `#101214` | 9.21 |
| A rakamı · gömük ekran | `#ffc46b` | `#101214` | 11.94 |
| W rakamı · gömük ekran | `#6fe3a8` | `#101214` | 11.83 |

En düşük: **5.47**

### Aday C — Ön panel (açık)

| Nerede | Metin | Zemin | Oran |
|---|---|---|---|
| asıl metin · sayfa | `#1c1e21` | `#eceae6` | 13.90 |
| asıl metin · kart | `#1c1e21` | `#f7f6f3` | 15.46 |
| asıl metin · çubuk / gömük ekran | `#1c1e21` | `#dedbd5` | 12.09 |
| ikincil metin · sayfa | `#4d535a` | `#eceae6` | 6.47 |
| ikincil metin · kart | `#4d535a` | `#f7f6f3` | 7.20 |
| ikincil metin · çubuk / gömük ekran | `#4d535a` | `#dedbd5` | 5.63 |
| etkin sekme | `#7d4700` | `#dedbd5` | 5.48 |
| vurgu metni · sayfa | `#7d4700` | `#eceae6` | 6.30 |
| vurgu metni · kart | `#7d4700` | `#f7f6f3` | 7.01 |
| seçili seçenek | `#7d4700` | `#f6e3c2` | 6.02 |
| ana düğme yazısı | `#1b1203` | `#f5a524` | 9.07 |
| DURDUR yazısı | `#ffffff` | `#c2361f` | 5.47 |
| bağlantı metni (iyi) · çubuk | `#0f5f3d` | `#dedbd5` | 5.58 |
| V rakamı · gömük ekran | `#234fa8` | `#dedbd5` | 5.52 |
| A rakamı · gömük ekran | `#7d4700` | `#dedbd5` | 5.48 |
| W rakamı · gömük ekran | `#0f5f3d` | `#dedbd5` | 5.58 |

En düşük: **5.47**
