# Alt proje 1 — açık işler ve ertelenenler

> Durum: 2026-10-01. Kapsam: 1A-1 · 1A-2 · 1B · 1C-1 · 1C-2 · 1C-3 · 1C-4.
> Geri dönüldüğünde **buradan** başlanır. Her maddenin kaynağı köşeli parantezde.
> - "DEVIR x" mühendislik günlüğündeki girdidir.
> - "inceleme" o dilimin bağımsız son incelemesidir.
>
> 1A-1, 1A-2, 1B ve 1C-1'in çalışma defterleri silindi. Maddeleri DEVIR'den ve
> oturum dökümünden kurtarıldı; bu dosya artık tek kayıt.
> Kapanan madde **silinmez**: üstü çizilir, kapanış commit'i yazılır.

Öncelik:
- **Y** — veri doğruluğunu ya da kullanıcının gördüğünü etkiler; geri dönünce önce bunlar.
- **O** — nadir durumda yanlış davranış.
- **D** — kozmetik, test boşluğu, belge.

## Önce bakılacaklar (Y)

| # | Ne | Neden önemli | Dilim |
|---|---|---|---|
| ~~Y1~~ | ~~Kayıtsız bir pil testinin DCIR olayları ve `KN_DCIR` noktaları, o sırada açık bir ÖLÇÜM oturumuna düşebilir. Bu, `p1` açılış taraması sırasında ya da kuyruk doluyken verilirse olur~~ | ~~Ölçüm kaydına yabancı olay girer, PC onu pil olayı sanar. Düzeltme: `kyn_olay` yalnız PİL oturumuna yazsın~~ | 1C-1 [inceleme M7] — **Kapandı (dal `1-duzeltme`):** olay mesajı hedef oturum türünü taşır (`KM_PIL_OLAY`, `kyn_olay(m, tür, …)`); `KN_DCIR` yalnız PİL oturumunda kalır (`kn_ek_suz`). B71.PL8, B72.Y1 |
| ~~Y2~~ | ~~`plan_basliyor` NVS'e oturum açma isteğinden **sonra** yazılıyor. Arada elektrik giderse plan açılışta BEKLİYOR görünür, kendi DEVAM almış oturumunu "meşgul" sayıp ATLANDI olur, o kayıt bitişsiz sürer~~ | ~~Kullanıcı planlı kaydın kendiliğinden biteceğini sanır. Düzeltme: isteği göndermeden önce yaz, gönderemezse geri al. 1C-4 düzeltmesiyle pencere ms'ye indi, kapanmadı~~ | 1C-4 [inceleme M3] — **Kapandı (dal `1-duzeltme`):** incelemenin önerisi ("önce yaz") kaydı yine bitişsiz bırakıyordu → KANITLI bağlantı: çekirdek 0 oturumu açmadan önce NVS'e plan no + sıra yazar, açılışta yayınlar; çekirdek 1 `plan_acilis` ile benimser. B71.R14–R16, PK1–PK5, B72.Y2 |
| ~~Y3~~ | ~~Plan NVS'i açılamaz ya da yazılamazsa (örneğin NVS kalibrasyon geçmişiyle dolarsa) `plan_kur` yine başarı döner, kart "plan kuruldu" der~~ | ~~Plan yalnız RAM'de; yeniden başlamada sessizce kaybolur. Düzeltme: `KP_NVS` hatası~~ | 1C-4 [inceleme M4] — **Kapandı (dal `1-duzeltme`):** `plan_kur` NVS hatasında `KP_NVS`, önceki plan RAM'e ve NVS'e geri; alan hatasında durum yazılmaz. B71.R17 (kısmi hata), B72.Y3 |
| ~~Y4~~ | ~~Kalibrasyon geçmişinin `adet` anahtarı kaybolursa `kgc_ac` 1 numaranın üzerine yazar~~ | ~~Kalibrasyon geçmişinin başı sessizce ezilir. Düzeltme: `k1…k40`'ı tarayıp sayıyı yeniden kur~~ | 1B [inceleme M1] — **Kapandı (dal `1-duzeltme`):** `adet` okunamazsa k1…k40 taranır (ortadaki bozuk kayıt durdurmaz), geri yazılır. B71.C14 |
| ~~Y5~~ | ~~Yazma hatası yolunda ayrıntılı örnek sayılmadan düşüyor (`KA_KAYIP_ONCE` + düşen yok); yeniden denemede aynı kayıt iki kez yazılabiliyor ve PC `ayrinti_ornekler` bunu ayıklamıyor~~ | ~~Nadir, ama olunca çift ya da sayılmamış örnek~~ | 1C-2 [inceleme] — **Kapandı (dal `1-duzeltme`):** yazılamayan örnek sayılır, boşluğu açan kayıt `KA_KAYIP_ONCE`; PC ayrıntı örneklerini VE noktaları sıra başına bir kez verir (yeniden deneme kopyası). B71.A11–A13 |
| ~~Y6~~ | ~~Bozuk kalibrasyon kaydı `/kal/liste`'de sessizce atlanıyor. Doğrusu `{"no":n,"bozuk":true}`~~ | ~~PC eksik geçmişi tam sanır~~ | 1B [inceleme M2] — **Kapandı (dal `1-duzeltme`):** kart bozuk kaydı `{"no":n,"bozuk":true}` yazar; PC'de sağlam kopyası varsa o kalır (`kartta_bozuk`), yoksa bozuk işaretiyle. B72.Y6a/Y6b |
| Y7 | Ekli oturumda (ÖLÇÜM + skop günlüğü) kayıt sırası tam zaman sırası değil. Görev noktaları mesajlardan önce boşaltıyor, ~100 ms. Yakalamanın ölçümde bıraktığı boşluk AYRINTI'da bayraksız | PC yakalamayı yanlış zamana koyabilir. Alt proje 2: META `t_ms` ile yerleştir | 1C-3 [inceleme] |

**D0 (1D çalışmasında bulundu, bu dalda kapandı):** `N?` ve AP kipindeki açılış afişi AP WiFi
parolasını `Serial` aynasıyla basıyordu. Ayna her satırı `/akis` SSE'siyle ağa taşıdığı için parola ağa
çıkıyordu. Artık yalnız ham UART'a gidiyor (`Serial.ham`, B72.D0).

## Kartta / tezgahta yapılmamış doğrulamalar

| # | Ne | Neden yapılmadı | Dilim |
|---|---|---|---|
| T1 | Osiloskop yakalamalarında 1 kHz frekans / dalga biçimi doğruluğu | Skop girişinde sinyal yok (RC düzeneği sökülü). Biçim ve boru hattı ölçüldü, dalga doğruluğu ölçülmedi | 1C-3 |
| T2 | Gerçek fiş çekme: USB + PİL kapalı, 5 kez, elle | Elle iş | 1A-2 |
| T3 | ADS takılınca `--durma` tekrarı ve Python çözücünün volt/amper çevriminin `D` satırıyla karşılaştırılması | ADS takılı değil | 1A-2 |
| T4 | Kalibrasyon komutları (`z g Z i s f F R`) kartta hiç çalıştırılmadı. Tezgah `--kal` yalnız listeleme yolunu sınıyor | ADS takılı değil | 1B |
| T5 | Pil testi kartta yalnız "ret" yolundan sınandı (`p1` gerilim yok diye reddediliyor) | ADS ve analog ön uç yok | 1C-1 |
| T6 | Dolu kalibrasyon geçmişinde tarama süresi (`kgc_esle` en fazla 39 NVS okuması) | Geçmiş dolu değil | 1B |
| T7 | Tezgahta "plan sürerken `Gd` + `Gb`" (elle kayıt plan bitişini geçmeli) ve "DOLU'da oturumsuz pil testi + plan" durumları yok | Kaynak iddiası var, kart senaryosu yok | 1C-4 [inceleme M6] |
| T8 | Tezgah `--skop`, `Gb` sürerken günlüğü ve aynı oturumda yeniden `Gt`'yi kartta sınamıyor (PC tarafı B29'da) | — | 1C-3 |
| T9 | B10 (kayan nokta FMA) gerçek ESP32 derleyicisiyle tekrarlanmadı | Etkisi örnek başına ≤ 1 µW; PC kartın toplamını okuyor → kabul edildi | 1A-1/1A-2 |

## Sonraki alt projelere devredilenler

| Ne | Nereye | Dilim |
|---|---|---|
| Onay ve `/kayit/veri` okuması kimliksiz; ağdaki herkes onay yollayabilir (yalnız verilmiş sıralar) | **1D** (eşleştirme + imzalı istek) | 1A-1, 1A-2 |
| Cihazdan saat alma (bugün yalnız NTP; internetsiz ağda plan kurulamaz, çevrimdışı unix 0) | **1D** | 1B M7, 1C-4 K4 |
| ~~Açılıştan kaydın sürmesine 2.5–6.3 s; büyüğü `setup()`'taki WiFi beklemesi. Ağ kurulumu görev içine taşınmalı~~ | **Kapandı (1E-2, 2026-10-02):** STA beklemesi ağ görevine (`ag_bekle_tamamla`); `setup()` yalnız radyoyu açar. Kartta: sıfırlamadan ilk `D`ye 6.35 s → **1.32 s**; 20 sıfırlamada kayıt aynı oturumla sürdü. AP'ye düşüş yolu kartta sınanmadı (ev ağı kapatılmadı) | 1A-2 |
| ~~"Pil testi kesildi" bildirimi~~ | **Kapandı (1E):** `pil_bitti` olayı `pil_durdur`'dan; kayıtsız test de bildirilir | 1C-1 |
| PC'de W'nin hizalamalı hesabı (örnek zamanında ~1.8 ms kayma; V–I başlangıç kayması saklanmıyor) ve grafik | **2** (`ortak/`) / 3 | 1C-2 |
| Eski kayda başka kalibrasyon uygulama, dönem uyarısı, "daha yeni ince ayar öner" | **2** + 3 | 1B |
| Kayıt ekranları; `G` arayüzde yok. Ayrıca ad/not web ucu, `/pil`, `PilHalka` panelden kalkması ve yakalama gösterimi | **3** | 1A-2, 1C-1, 1C-3 |
| Plan gösterimi (panel / PC / telefon) | **3–5** | 1C-4 |
| `Gn` ile yazılan notun sıra numarası kartta basılmıyor (`Gx` için eşitlenen dosyadan okunuyor); `G` satırında `son_not` alanı | **3** | 1C-1 |
| B34 ADC doğrusalsızlık düzeltmesi | **Karar bekliyor** (kullanıcı) | 1B |

## Nadir durumda yanlış davranış (O)

- [1A-1] `menzil` bölmesi nokta çizelgesini kaydırıyor; DURAKLAMA ile birleşince noktanın başlangıcı bilinmeyebilir. Bir "nokta süresi" alanı düşünülmeli.
- [1A-1] `ky_nokta` KG_HATA sonrası tampon doluyken reddettiği noktayı `dusen`'e saymıyor.
- [1A-1, 1C-2] `kg_ilerle` / ön silme: silme başarısızsa sektör tablosu zaten düşürülmüş, yeniden denemede `silinen_sektor` iki kez sayılır; ön silme hatasında geri çekilme yok (`temiz_ms` güncellenmiyor).
- [1A-2] `Gb` kayıt sürerken yeniden verilirse kuyruktaki 1–2 eski nokta yeni oturuma girebilir. [1C-2] Oturum sınırında halkadaki örnekler de öyle (ms mertebesi; zaman damgası gösterir).
- [1A-2] Bölüm doluyken baş sektörde yarım yazma varsa açık oturum sürdürülemez → durum 4 (BEKLİYOR). Yedek sektör ayrılmadı. Kullanıcı durdurduysa ilk geçerli onayda BITIR yazılır, yoksa DEVAM.
- [1B M8] Kuyruk doluysa oturumsuz kayıt kalabilir.
- [1C-2] PSRAM ayrılamazsa `Gb0` yine kabul ediliyor; yalnız `GA` düşen sayısı gösterir.
- [1C-2] NaN watt, ham kodu geçerli örneğe V/I hata bayrağı koyuyor.
- [1C-2] 16.38 ms'den kısa skop duraklaması işaretlenmiyor (zaman doğru, sebep kayboluyor).
- [1C-2] İzin yarışı: ön silme sürerken bir skop yakalaması ~%5 olasılıkla 25 ms'lik duruşa denk gelir; hazır alan dolunca biter.
- [1C-3] `Gtd`, SKOP oturumu öğrenilmeden ya da açılış taramasında gelirse kuyruktaki `KM_SKOP_BASLAT` kimsenin yazmadığı bir oturum açar; kullanıcı `Gd` demeli.
- [1C-3] Ayar komutları pratikte çoğu an uçuştaki yakalamaya takılır. `Gt0`'da kip OTO'ya çekilirse tetiksiz yakalama kaydedilir.
- [1C-3] SKOP_KAL tablosu, kalibrasyon tablosu geçersizken de yazılıyor; PC ayırt edemez.
- [1C-4 M1] Planın oturumu DEVAM için yer beklerken (KDR_BEKLIYOR) her saniye etkisiz bir "bitir" isteği ve seri/SSE mesajı gidiyor; yer açılınca oturum ~1 s fazla sürüyor.
- [1C-4] Açılışta "sürüyor" ama oturumu bilinmeyen plan (sonuç gelmeden elektrik gitti) bitti sayılır. O ms'lik pencerede açılmış bir kayıt otomatik bitmez.
- [1C-4] Plan artık beklemiyorken geç açılan oturum sebep 7 ile kapatılır; `Gp-` yarışında yanlış sebep etiketi olabilir.
- [1A-1, kabul] Sektörde ilk bozuk kayıttan sonrası okunamaz (yeniden senkron yok). Bilinçli tasarım.
- [1A-1, kabul] Yavaş hızda bitmemiş noktadaki örnekler kesmede kaybolur (1/dk'da en fazla 1 dk).
- [1A-1, kabul] `kart_ms` 49.7 günde sarar; tüketici SAAT kayıtlarıyla çözer.

## Kozmetik, test boşluğu, belge (D)

- [1A-1] `KayitNoktaci.bekleyen` hiç 0 dışında bir değer almıyor (ölü alan; 2026-10-01'de yeniden bakıldı, hâlâ öyle).
- [1A-1] Noktacıda `watt` NaN/Inf ise `(int64_t)` dönüşümü tanımsız. Yapıştırıcı NaN'ı hata sayıp dönüşümü atlatıyor, ama `kayit_nokta.h`'de `isfinite` yok.
- [1A-1] `kg_oku` 0/0/0 hem "yeni yok" hem "kap küçük" demek; asgari kap belgelenmeli.
- [1A-1] Python `basla_coz` / sürüm çözümü `rstrip(b"\0")` ilk NUL'dan sonraki çöpü tutar; ilk NUL'da kesilmeli.
- [1A-1] "Kullanmadan önce hep sil" için mutasyon yok (inceleyici elle denedi, test ısırıyor).
- [1A-2] `--esit` yalnız "eşitlenen ⊆ flaş" denetliyor; tamlık denetimi yok.
- [1B M3] `/kal/liste` kayıt başına ~20 `sendContent` yapıyor.
- [1B M5] Bayat yorumlar (`kayit_oturum.h`, spec §5 "116 baytlık TEKRAR" → 118).
- [1B M6] `kn<no>` boş metinle notu siliyor (bilinçli sayılabilir).
- [1B M9] `Gb`'de NVS yazma duraklaması.
- [1B M10] Sürüm 1'den uçtan uca devam sınanmıyor; ESP yapıştırıcısı yalnız kaynak iddiasıyla sınanıyor.
- [1B M11] Okuyucular tam blob boyu istiyor (B34 büyütmesi için).
- [1C-1 M9] `kayit_mesaj_dusen` sayacı hiçbir yerde okunmuyor (G satırında yok).
- [1C-1 M12] `ky_olay`, `kyn_pil_bitir` ve `kyn_not`'un DOLU yolları testsiz; iki kuyruk arasında en fazla bir nokta olaydan sonra yazılabilir.
- [1C-1 M13] `kayit_komut` ve `kayit_not_komut` yığında ikişer ~254 B `KayitMesaj` tutuyor.
- [1C-2] 4095/4096 dt sınırı, `kg_on_sil_adim`'daki `kg__sektor_dusur`, C tarafında `micros` sarması doğrudan sınanmıyor.
- [1C-3] `GT` "yazılamayan" sayacı günlük başına atlananla açılıştan beri `skop_hata`'yı karıştırıyor; kullanıcının kestiği yakalama da "yazılamayan" sayılıyor.
- [1C-3] `kyn_skop` açıklaması `kyn_pil_bitir`'inkinden ayrılmalı; `ky_devam`'da yalnız ÖLÇÜM için ayrıntılı koruması yok (bugün ulaşılamaz); `SKOP_AZAMI_ADET <= KAYIT_SKOP_AZAMI` için derleme denetimi yok.
- [1C-4 M5] `GP`: saatsiz SÜRÜYOR düz 2 görünüyor; atlandı/kaçırıldı/bitti geçişleri o an yazılmıyor (yalnız `G?`); ATLANDI eşitlenen veride iz bırakmıyor; bekleyen planın üzerine yazmak sessiz.
- [1C-4 M6] Çekirdek 0'ın `KM_PLAN_BITIR` mantığı yalnız kaynak metin iddiasıyla sınanıyor (platformsuz `kyn_plan_bitir` yok); `plan__yaz` sırası ve `plan_ac` kırpması mutasyonsuz.

## Bilinçli kabul edilen sınırlamalar (geri dönmek gerekmez, bilinsin)

- [1A-2] Biçimleme mantıksal: silinen veri, eski sektörler arka planda silinene kadar (dolu bölümde ~24 dk) esptool ile flaştan okunabilir. Kartın hiçbir ucu onu vermez.
- [1A-2, 1C-2] Arka plan temizliği ve boşta ön silme 500 ms'de bir 25 ms iki çekirdeği durdurur. Açılıştan / eşitlemeden sonra ~4 dk canlı ölçümde takılma görülebilir; GF! + doldurmadan sonra temizlik ~24 dk sürer, her yeniden başlama temizliği baştan alır.
- [1A-2] Onay NVS'e kısıtlı yazılıyor (16 sıra ya da 30 s). Elektrik kesilirse onay en fazla o kadar geri gider; kayıp ya da tekrar yok.
- [1C-2] Onaylı veri kartta erken siliniyor (veri PC'de; tek cihaz eşitlemesi varsayımı).
- [1C-2] Her açılışta en fazla 480 boş sektör yeniden silinir. NOR ömrü için ihmal edilebilir.
- [1C-4] İstek numarası 8 bit; 255 plandan sonra sarmada eski geç bir sonuç karışabilir (pratikte yok).
- [1A-1] Zayıf silinmiş/programlanmış NOR hücresi davranışı emülatörde modellenmiyor; tezgah kesme denemeleri kapsıyor.

## 1D — eşleştirme + imzalı istekler (kararlar ONAYLANDI 2026-10-01; dal `1-birlesik`)

| # | Ne | Durum |
|---|---|---|
| D0 | ⚠ **`main`'deki firmware'de ön-cesi sızıntı:** `N?` AP WiFi parolasını `Serial` aynası üzerinden açık `/akis` SSE'sine (ağa) basıyor. Düzeltme yalnız 1D dalında (`Serial.ham`). | **Öncelikli** — 1D onaylanmasa da bu tek satır `main`'e alınmalı |
| ~~D1~~ | ~~Kart tezgahı hiç koşulmadı~~ → **2026-10-01 akşam koşuldu: ilk koşu 15/18**, üç gerçek bulgu: (a) PBKDF2 50 000 tur 4.76 s; (b) her `Ez`/`Em` P'yi yeniden hesaplatıp çekirdek 1'i 4.7 s donduruyordu, sonraki seri komutlar bekliyordu; (c) tezgahın SSE dinleyicisi `olcum.local` çözümü (~3 s) bitmeden `Ep` gönderiyordu, "anahtar SSE'de yok" denetimi BOŞ yere geçebilirdi. Tanı koşusunda anahtar SSE'ye DÜŞMÜYOR (doğrulandı). Üçü de düzeltildi (B71.U19, B72.F98–F101), **son koşu 19/19**. Kart ardından tam yedekten `main` firmware'ine (A3-1C4) döndürüldü | Kapandı |
| ~~D2~~ | ~~Varsayılan tur ölçülmedi~~ → kartta ayrı bir ölçüm eskiziyle beş PBKDF2 yolu karşılaştırıldı (hepsi `hashlib` ile aynı sonuç): her turda HMAC kurulumu 85 µs/tur · mbedTLS PBKDF2 56.7 · `hmac_reset` 56.3 · yazılım SHA 43.3 · **ipad/opad kopyası 30.5** (seçildi). Firmware içinde ~38 µs/tur: 25 000 tur 956 ms (pay %4), **varsayılan 20 000 = 764 ms**. 50 000 bu çipte < 1 s OLAMAZ (en iyi yol 1.9 s) | Kapandı (karar spec K4'te; kullanıcı onayına açık) |
| ~~D3~~ | ~~Parolalı eşleştirmenin BAŞARI yolu kartta sınanmadı~~ | **Kapandı (2026-10-01 gece):** kullanıcı web parolasını 12 karaktere çıkardı (USB `Ns`). Kartta (`A3-1D`) parolalı eşleştirme başarılı (karşılıklı kanıt), imzalı `/kayit/liste` 200, imzalı `/cihaz/liste` anahtarı göstermiyor; test cihazı silindi (`cihaz=0`). Yan bulgu: kart WPA3-yalnız telefon hotspot'una bağlandı, ağ adının sonundaki BOŞLUK kayıtta korunmalı (tanı: kanal/bayt taraması) |
| ~~D4~~ | ~~Onay bekleyen kritik kararlar (spec 1–7)~~ | **Kapandı:** kullanıcı önerilerin hepsini onayladı (2026-10-01); en kısa parola 10 → **12** (B71.U5, B72.I8) |
| D5 | Ertelenen küçükler (son inceleme #8, #10–#12, #14–#19) | Aşağıdaki liste |

**D5 — son incelemenin ertelenen küçükleri** (hiçbiri bugün sömürülebilir değil; birleştirmeden önce ya da 1E'de):

- [1D #8] GET dışındaki her yöntem "GET" diye imzalanıyor; PUT/PATCH/DELETE gövdesi özetlenmiyor (kartta böyle bir uç yok).
- [1D #10] `/saat`'in üst sınırı yok; `strtoul` bitişi denetlenmiyor (`"-1"` → 2106).
- [1D #11] `Ex<n>` önce kesiyor, sonra denetliyor (`Ex257`, `Ex-255` cihaz 1'i siler; yalnız USB).
- [1D #12] `EK` satırı üç `ham()` çağrısında basılıyor; araya IDF günlüğü girerse hex ayrı satıra düşer ve köprü süzgeci yakalamaz. Çözüm: tek çağrı + köprüye 64-hex satır süzgeci.
- [1D #14] Eşleştirme numarası (`eno`) ardışık `uint8`: üçüncü kişi bekleyen eşleştirmeyi tüketip ortak geri çekilmeyi büyütebilir. Çözüm: rastgele `eno`.
- [1D #15] 401 metni "cihaz kayıtlı değil" ile "imza geçersiz"i ayırıyor (cihaz numarası taranabilir).
- [1D #16] İstemci dosyası `fsync`'siz `os.replace` ediliyor; `.tmp` adı süreçler arası ortak; POSIX'te `chmod`'dan önce K'li geçici dosya oluşuyor.
- [1D #17] İmza her uçta sorgu dizgisinde kabul ediliyor (K9 yalnız EventSource diyor). İmzalı `/akis` adresi tek kullanımlık: tarayıcının otomatik yeniden bağlanması 401 alır (alt proje 3).
- [1D #18] `N?` zorunlu/misafir/saat kaynağını göstermiyor · `/eslestir/bilgi` `X-Olcum` istemiyor · `yardim()` E'yi listelemiyor · kapı kodu `kok_sayfa`'nın eski yorumuyla işlevin arasında · `ac()` kartın kimliğini cihaz dosyasıyla karşılaştırmıyor · `ac()`'taki `HTTPError` kapatılmıyor · spec "çekirdek 1 E'yi kuyrukla yollar" diyor, kod muteks kullanıyor.
- [1D #19] F80 üst sınırı sınamıyor; boş `X-Imza` başlığının kartta imzasız sayılması ölçülmedi (zararsız: imzasız yol daha serbest değil).
- [1D karar] Kartın `/komut` ucu gömülü satır sonuna karşı düzeltilmedi: kuyruk komutu bölmeden çalıştırıyor, yalnız seri girişi bölüyor. Kuyruk ileride bölmeye başlarsa aynı açık doğar.

## 1E — MQTT bildirimleri (dal `1e-mqtt`, 2026-10-01 gece)

Tasarım `tasarim/2026-10-01-1e-mqtt-bildirim.md` (K1–K12 + "Uygulama sırasında verilen kararlar").

| # | Ne | Durum |
|---|---|---|
| ~~E1~~ | ~~Gerçek TLS hiç denenmedi~~ | **Kapandı (2026-10-02):** EMQX Serverless'a TLS ile bağlandı (CA demeti zinciri doğruladı), el sıkışma 0.9–2.0 s, el sıkışma sırasında `loop_azami` değişmedi (7.1–7.6 ms vs taban 7.2–7.4 ms), 120 s kopmasız. HiveMQ ücretsiz Serverless'ı kaldırdığı için aracı EMQX (K2) |
| ~~E2~~ | ~~Ö4 gerçek ağda, 10 tekrar~~ | **Kapandı (RTS sıfırlamasıyla):** 16/16 vasiyet 4.0–7.9 s (ortanca ~7 s, hepsi ≤ 10 s). Gerçek fiş çekme (USB + PİL kapalı) elle yapılmadı; RTS ile aynı yol (TCP kapanmadan kopuş) |
| E6 | Dahili yığının en düşük değeri açılış + el sıkışma anında 54–60 KB (bağlıyken 82–83 KB; K11 ≥ 60 KB bağlıyken tutuyor). Ağır web yükü + el sıkışma çakışırsa TLS ayırması başarısız olabilir (kart yeniden dener) | İzle; gerekirse 3 KB olay kuyruğu ve paket tamponu PSRAM'e |
| E7 | İlk gerçek aracı koşusunda 16 sıfırlamadan birinin `basladi` olayı aboneye ULAŞMADI; hedefli tekrar 6/6 geldi. Kartın `olay` sayacı o an kaydedilmedi → kayıp kartta mı (uçuştaki olay + sıfırlama) aracıda mı ayırt edilemiyor | Bir sonraki tezgahta her sıfırlamadan önce `Q?` olay sayacını kaydet |
| E3 | Eşik (`esik`) 500 binde sabit; kullanıcı ayarı yok | Gerekirse `Qe<binde>` (küçük) |
| E4 | Olay kuyruğu RAM'de (16); kart yeniden başlarsa gönderilmemiş olaylar kaybolur (spec kapsam dışı: kalıcı kuyruk) | Bilinçli |
| E5 | Telefon/PC bildirim arayüzü yok; PC'de yalnız `kopru/bildirim.py dinle` | Alt proje 4/5 |
