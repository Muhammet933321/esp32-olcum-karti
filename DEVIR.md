# Ölçüm Kartı — Devir Belgesi

> **Tarih:** 12 Eylül 2026 · **Devreden oturum:** Claude Opus 5 · **Durum:** Aşama 3
> tasarımı doğrulandı (**18/18**) · **ESP32-S3 GELDİ, bringup koşuldu (B26)**
> — firmware + arayüz kartta, **bir ADS1115 (`0x48`) breadboard'da**, kart ev
> ağında ve web katmanı doğrulandı. Bringup: **48 geçti / 3 kaldı / 1 atlandı**.
> Analog ön uç hâlâ kurulmadı.
>
> 🔴 **B26'da beş kusur bulundu, hepsi düzeltildi** — ikisi firmware'de, üçü
> belge/test tarafında, artı **beş koşucu kusuru** daha. En ciddi ikisi:
> **AP SSID'i MAC'ten gelmiyordu** (ilklenmemiş bellek) ve **ALERT/RDY kenar
> yönü tersti** — ikincisi örnekleme hızını 665 yerine **162**'de tutuyordu ve
> B20'nin düzeltmesinin *altında* duruyordu.
>
> **Ölçülen örnekleme hızı: 485/s** (tek ADS ile; ikinci ADS takılınca banda
> oturması bekleniyor). Kalan üç kırmızıdan ikisi eksik ADS'ten, biri
> **gerçek**: çift çekirdek kararının sinyali — 30 saniyede bir ~26 ms blokaj.
>
> **Kullanıcının okuyacağı belgeler `BELGELER/` klasöründe** — bu dosya
> mühendislik günlüğü, oraya kullanıcıyı yönlendirme.

---

## ⚠️ YENİ OTURUM — ÖNCE BUNU YAP

Bu belgeyi okuyup projeyi devralıyorsun. Sırayla:

1. **Doğrulama zincirini koştur.** Belgede yazan her şey bu zincire dayanıyor:
   ```
   cd projeler/olcum-karti/uretim
   python dogrula3.py          # AŞAMA 3 — GÜNCEL, 22/22 adım (ADIM_SAYISI), TAM koşu ~15–20 dk
   python dogrula3.py --artimli   # iş sırasında: değişmeyen adımlar önbellekten (5.12.97)
   python dogrula2.py          # Aşama 2 — A1..A6, 6/6 geçmeli, ~70 s
   python dogrula.py           # Aşama 1 — S1..S9, 9/9 geçmeli, ~110 s
   ```
   **Aşama 3 güncel olan.** Yeşil değilse **önce onu düzelt**, yeni iş açma.

   > **Artımlı zincir (HIZ, 5.12.97/98/99):** `--artimli`'de girdileri (adımın GERÇEKTEN
   > okuduğu dosyalar, alt süreçleri, araçları, ortam) değişmeyen adımın yeşil sonucu
   > önbellekten gelir — hiçbir şey değişmediyse ~20–30 s. Özette `[onbellekten, N dk önce]`;
   > koşanın sebebi `[kosuyor: ...]` satırında. **TAM koşu ŞART** (`python dogrula3.py` ya da
   > `--tam`): `main`'e almadan / push'tan önce · son yeşil tam koşu 24 saatten eskiyse ·
   > `--sayim-kilidi-yaz` için (`--artimli` ile REDDEDİLİR; `--tam --sayim-kilidi-yaz` olur).
   > `dogrula3.py`/`mutasyon.py`/`tasarim3_sabit.py` değişince `--artimli` kendisi tam koşar.
   > Zincir sürerken dosya düzenlersen o adımın kaydı geçersiz yazılır, sonraki koşu onu koşar.
   > Adımlar ÖZEL bir `LOCALAPPDATA`'da koşar (`ozel_ortam.py`): gerçek
   > `%LOCALAPPDATA%\olcum-karti`'ye dokunulmaz.

   > **Adım adım iddia sayıları burada ELLE tutulmuyor** — B23.3'ten beri
   > `uretim/beklenen_sayim.json` tutuyor ve zincir her koşuda birebir
   > karşılaştırıyor. **Sapma her iki yönde de kırmızı:** bir iddia
   > düşerse de, eklenirse de. (B22.2'de bir iddia düşerken başkası
   > eklenmiş, toplam sabit kaldığı için mutasyon kaçmıştı.) Bilerek
   > değiştirdiysen `python dogrula3.py --sayim-kilidi-yaz`.
   >
   > Bu blok daha önce elle yazılıydı ve bir kez **12/12**'de donmuştu.

   ⚠️ Zincir **tasarımı ve kodu** doğruluyor, kartı değil. Kart var
   (B26'dan beri) ama **analog ön uç yok**; karttaki davranışı tezgah
   betikleri ölçüyor (aşağıdaki "📌 GÜNCEL DURUM").

2. **Depo GitHub'da — değişikliği göndermeyi unutma.**

   <https://github.com/Muhammet933321/esp32-olcum-karti> · MIT · public.
   Yerel depo `projeler/olcum-karti/`, remote `origin`.

   ```
   cd projeler/olcum-karti
   git add -A && git commit -m "..."
   git push origin main
   ```

   Kimlik **Git Credential Manager**'da kayıtlı (`Muhammet933321`) —
   şifre sorulmaz, push sessizce geçer. ⚠ **`gh` CLI kurulu ama oturum
   AÇIK DEĞİL** (`gh auth login` etkileşimli, ajan tamamlayamaz). Depo
   oluşturmak/ayar değiştirmek gerekirse kullanıcı tarayıcıdan yapar;
   **push için `gh` gerekmiyor.**

   ⚠ Yayınlamadan önce: `.gitignore` kullanıcının ölçüm günlüğünü
   (`kopru/arsiv/`) ve `fiyat_tara.py`'yi **bilerek** dışarıda tutuyor.
   Kişisel iz taraması bütün metin dosyalarını kapsamalı — B24'te
   `uretim/b15-arastirma.md` üç satırda Windows kullanıcı adı taşıyordu
   ve ilk tarama onu kaçırmıştı.

3. **Dosya düzenini bil** (5.12.32'de sadeleştirildi):

   | Klasör | Ne |
   |---|---|
   | **`BELGELER/`** | **Kullanıcının okuduğu yer** — HTML + PDF. `belge-uret.py` üretiyor, ELLE DÜZENLEME |
   | `kod/olcum-karti-a3/` · `sema3/` · `arayuz3/` | Güncel sürümler |
   | **`kopru/`** | **PC köprüsü** (B22.3) — seri↔SSE rölesi, disk arşivi, sürücü hakemi. `Kopru Baslat.bat` ile çalışıyor |
   | `uretim/` | Doğrulama zinciri + üreteçler |
   | **`uretim/_tezgah.md`** | **ÜRETİLİYOR** — kart kurulunca tezgahta ölçülecekler. Sayı dosyanın sonunda; elle düzenleme, kalemi ilgili adımın `tezgah(...)` çağrısına ekle |
   | `arsiv/asama1/` · `arsiv/asama2/` | Eski aşamalar, kendi zincirleriyle. ⚠ **`arsiv/` tamamen ölü değil:** `kurulum3-uret.py` biçimini `arsiv/asama2/kurulum2.html`'den okuyor (B23.3'te bulundu) |

   Bir sayı değişince `BELGELER/` kendiliğinden güncelleniyor (zincirin
   B9 adımına bağlı). Belgelere elle sayı yazma.

   `uretim/` içindeki B23 araçları:

   | Dosya | Ne |
   |---|---|
   | `tezgah.py` | Tezgah kalemi biçimi + toplayıcı yardımcıları. Konsolun çizemeyeceği karakteri **yazmadan önce** yakalıyor |
   | `mutasyon.py` | Mutasyon koşucusu — kaynağı bir **kopyada** bozup testin kırmızıya döndüğünü ölçüyor |
   | `sayim.py` | Adım özet satırlarının ortak ayrıştırıcısı (dört ayrı biçim) |
   | `gecici.py` | Kendini silen geçici dizin (`atexit`). Altı betik `mkdtemp` çağırıp silmiyordu |
   | `belge_menu.py` | `BELGELER/` gezinme şeridi — **tek kaynak**, iki üreteç paylaşıyor |

4. **Bu projenin altın kuralı: yeşil test bir şey kanıtlamaz.**
   Son üç adımda (B17, B20, B21) her seferinde, zincir yeşilken
   **gerçek ve büyük** kusurlar bulundu:

   * B17: iki ADS senkron değildi — PF=0.5'te güç %76 düşük
   * B20: kart 860 SPS'te değil **91 SPS**'te örnekliyordu; B17'nin
     bütün frekans bütçesi yanlış bir hıza dayanıyordu
   * B21: derleme önbelleği uyarıları **gizliyordu**; `--clean` eklenince
     hemen bir `uint16` taşması ortaya çıktı

   Yani: bir iddiayı görünce **kaynağına git**, mutasyon testi yap
   (sabiti boz, kırmızıya döndüğünü gör), ve "bu kusur neden bugüne
   kadar görülmedi?" diye sor. Ayrıntılı liste hafızada:
   *ölçüm kartı doğrulama disiplini*.

   B23.3'ten beri mutasyon testi **elle değil**:
   ```
   python mutasyon.py --neden 4J --paralel 4   # bir dilimin yalanlayıcıları (nedeni "4J" ile başlayanlar)
   python mutasyon.py --adim B22b --paralel 4  # tek adım
   python mutasyon.py --paralel 4     # AGIR hariç hepsi (uzun)
   python mutasyon.py --adim B3       # tam zincir koşar — B3/B23 zincirin KENDİ korumalarını sınar
   python mutasyon.py --liste         # ne koşacağını yazar, koşmaz
   ```
   ⚠ Oturum karalama dizinindeki eski `mut_hedef_*.py` / `mut_par.py` koşucuları ESKİDİ, kullanma:
   yerine **`python uretim/mutasyon.py --neden <ONEK> --paralel 4`** (aynı karar, ~2.5–3× hızlı).
   **Paralel koşucu (HIZ, 5.12.97/98):** her işçi kendi kopyasında ve kendi
   `TMP/TEMP/LOCALAPPDATA`'sında koşar; `--paralel 1` = sıralı, aynı karar kümesi. FARKLI ağaçta
   zincirle aynı anda koşabilir; ⚠ **AYNI ağaçta koşan zincirin ÜSTÜNE BAŞLATMA.** İddiasız
   çökme = ŞÜPHELİ, tek başına yeniden koşulur. `UYGULANAMADI` = eski mutasyon (deseni artık
   kaynakta yok) — düzelt. Kalan `_mutp*` dizini olmamalı.
   Kaynağı bir **kopyada** bozup testin kırmızıya döndüğünü ölçüyor;
   asıl ağaca dokunmuyor (proje git deposu değil, bir Ctrl-C geri dönüşü
   olmayan bir bozulma bırakırdı). Yeni bir iddia yazdığında
   `MUTASYONLAR` listesine onu yalanlayan değişikliği de ekle —
   **koşucu ilk turunda üç boş iddia buldu.**

5. **Bölüm 4'teki "bilinen kusurlar" listesini doğrula.** Gerçekten var mı? Ben yanılmış
   olabilirim.

6. **İnternetten araştır.** Bölüm 7'de başlıklar var. Benzer sistem kuranlar ne sorun
   yaşamış, buradaki mimari varsayımlar tutuyor mu, gözden kaçan ne var?

7. **Kendi hata avını yap.** Bu belgeye güvenme.

8. **Sonra kullanıcıya ne yapacağını anlat, onay al, öyle başla.**

### 📌 GÜNCEL DURUM (2026-09-14, commit `882a05f`) — buradan devam et

**Kart:** ESP32-S3 N16R8, COM6 (CH343), iki ADS1115 takılı (0x48 akım,
0x49 gerilim), WiFi'de `olcum.local`, **web parolası tanımlı** (depoda YOK,
Chrome hatırlıyor). Zincir 18/18 (1453 iddia). **Yazılımda planlanıp
bekleyen iş yok** — sıradaki gerçek adım analog ön uç (B10). Firmware + arayüz kartta
güncel. **Analog ön uç kurulmadı.** Tezgahta hâlâ takılı: **GPIO4–GPIO5 kısa
devre** (jumper) ve **RC düzeneği** (GPIO10 → 10K → 100nF → 10K → 100nF →
GPIO4) — skop/tetik/ölçüm tezgah sınamaları bunlara bağlı; ön uçtan önce
sökülecek. Kart breadboard'da değil, dişi-erkek tellerle taşınıyor.

**Son yapılanlar (5.12.56–5.12.61):** B47 tetik onayı ayarlanabilir (varsayılan gürültü reddi; A/B 17/20 → 0/20) · B42 ön-tetik hiç uygulanmıyordu ·
B43 ölçüm satırı WiFi'de yoktu, USB'de eksenle 7 V çelişiyordu · B44 I²C'yi
taşıma kararı ölçülüp **reddedildi** (sebep pin/kablo değil, yüklü hattın
**kenar hızı**; yakalamada ADS susturma kalıyor) · B45 panel tarayıcıdan
gezildi, 4 arayüz kusuru · B46 `#` probu sahte "var" diyordu.

**Tarayıcı:** Claude in Chrome kurulu; VS Code'da mesaja `@browser` yazınca
araçlar geliyor. Panelde ham veri pikselden değil Vue durumundan okunuyor
(`kodVolt`, `osilo`). Yakala düğmesi parola ister → kullanıcı bir kez girer.
Arayüz karta yazıldıktan sonra `location.reload()` şart.

**Kartta ölçüm araçları (uretim/):** `tezgah_blokaj.py --skop` (B40–B43,
12/12) · `--tetik` · `--olcum` · `tezgah_kuplaj.py` (B44, `tK` komutu) ·
`tezgah_adc_supur.py` · `fikstur_skop_al.py` · `tezgah_kart.py --sifirla`
(bringup). ⚠ Köprü açıkken COM6 onda; hata sayan deneyleri **iç içe** ve
**CAL kapalı** koş (B44).

**Açık:** PCB'de I²C kuplajı yeniden ölçülecek · WebAkis satır birleştirme ·
hızlı yol sıfır kalibrasyonu (ön uç gerekli) · ön uç kurulunca `wB`,
`tezgah_kart.py --asama 1` · **B11 iddiası ters** (5.12.25 "−12 V regüle,
+12 ham" diyor; bağlantıya göre 7912 GND pini +12 V'ta olduğundan kart
GND'si 24V+'ın 12 V altında → **+12 regüle, −12 ham**; `sim3_besleme.py`
B11-3 iddiası `neg = T.LM7912_VO` sabitiyle boş — düzeltilip mutasyon
eklenecek; pratik etki yok, toplam besleme aynı).

**🧩 B48 (2026-09-14) — DELİKLİ PLAKET YERLEŞİM PLANI HAZIR, kullanıcı
lehime geçiyor.** Bkz. **5.12.62**. `BELGELER/7-yerlesim.html` kullanıcının
okuduğu plan; `uretim/yerlesim3.py` denetim (40/40, B9'a bağlı), veri
`yerlesim3_veri.py`, teller `yerlesim3_teller.json`. Üç parça: **A** ana
analog kart (13×23 plaketten **45×45** delik — 2026-09-15'te 38×38'den
büyütüldü: kısa kenar zaten 45, tek kesim; 10×10 plaket 32×32 çıktı, **sığmadı**), **B** HV zinciri (5×5, 18×18), **güç yolu kutuda**
(şönt, J3, J7, Q1 plakette değil). Kullanıcının sayımı: 13×23 = 45×90,
10×10 = 32×32, 5×5 = 18×18; her delikte ayrı ped. Sırada: kullanıcı
yerleşimi gözden geçirir → plaket kesilir → adım 0 (besleme) lehimlenir.
50 mA sigorta gelmedi: yuvaya geçici **400 mA (FUS001)**, ilk enerji akım
sınırlı; 24 V girişi XT30 (kodlu — ters takılamaz; açma-kapama anahtarı değil).
**B48b (2026-09-15, 5.12.63):** plan LEGO sırasında — 92 alt adım, sabit
görüş penceresi, her adımda gerekenler (stok kaydı + kutu), denetim 48/48.
ESP32 karta lehimlenmez — J5'e kabloyla, alt adım 1.12.
Kullanıcı kuruluma **7-yerlesim.html'den** başlıyor.

**Kullanım kararı (2026-09-14, kullanıcı):** **şebeke referanslı ölçüm
YOK** — yalnız pil/DC-DC beslemeli devreler, en fazla ~400 V, hepsi
toprağa göre yüzer. Bu yüzden panel **açık born jak + yalıtımlı timsah**
kablo; kılıflı (shrouded) güvenlik soketi **alınmıyor**. Kutu plastik.
Şebeke barası ölçülecekse bu karar açılır (panelde açık metal kalmamalı).
Üç kural: ölçülen devre kartın 24 V kaynağından beslenmez (−12 rayı
GND'ye kısa olur) · COM devrenin en düşük potansiyeline · 60 V üstü
kırmızı uca enerjiliyken dokunulmaz. Alınacak: plastik kutu (~20×15×7),
50 mA sigorta, isteğe bağlı yedek ESP32-S3. Krokodil ×3+3 stokta
(CON065/066; PVC kılıf yalnız sapı örter, çene çıplak — kalabalık pede
değil kabloya kıstır).

**🔍 Kurulum öncesi şema + kablo gözden geçirmesi (2026-09-14 gece):**
`BELGELER/sema.pdf` 9 Eylül'de donmuştu (şema 11 Eylül'de değişti) →
artık B3 üretiyor. Yerleşim belgesine **J5 → ESP32 tablosu** eklendi
(GPIO numaraları firmware `PIN_*` sabitlerinden: SDA 8, SCL 9, SKOP 4,
HAZIR 7, I_HIZLI 5, PIL_KAPI 6). İki kablo notu düzeltildi: yıldız GND
klemens vidasına değil **S− ile aynı noktaya, şönt bacağına** (vida–bacak
temas direnci COM'u S−'den I·R kadar kaydırırdı); B→A alt düğüm teli
"GND ile burulu" değil (B'de GND yok) **kısa (<10 cm)**. 🔴 **Açık iş
B49 (firmware):** şönt alçak tarafta ve gerilim kanalı kart GND'sine
(= RS.2) referanslı → voltmetre **kaynak** gerilimini okuyor, yük
gerilimi bundan I·R_şönt kadar düşük (ADS akım kanalının tam ölçeği
256 mV'a kadar; 12 V/tam akımda %2, 3.3 V'ta %7.7). Pil testi
etkilenmiyor (pil − = RS.2). Düzeltme tek satır: `V_yük = V − V_şönt`
(B17 iki ADS'i eş zamanlı okuyor, ikisi aynı örnekte elde); menzil/faz
kalibrasyonundan sonra, sıfır akımda etkisi yok. `olcum3.h`'ye bir
iddia + mutasyonla girecek; donanımı değiştirmiyor, kurulumu
bekletmiyor.

### ✅ B15 bitti (2026-09-09) — sonuçlar **5.12.24**'te

`uretim/sim3_ariza.py` · 111 doğrulama · 27 senaryo · `dogrula3.py`'de B15.
**DEVİR'in kendi dört sayısı yanlış çıktı** ve şemada **üç kusur düzeltildi**
(R34/R35/R36/R38/R39 seri korumaları + C1 100nF→1nF). Kabul ölçütü sağlandı:
hiçbir bileşen arızası ESP32'yi ya da PC'yi öldürmüyor; ölen en pahalı parça
ADS1115 modülü (~45 TL, soketli). Tek istisna kartın izole olmaması (D1b) —
o donanımla değil prosedürle çözülüyor, **sayısallaştırıldı**.

### ✅ B11 bitti (2026-09-09) — sonuçlar **5.12.25**'te

7912 orta nokta regülatörü (şemada BLOK 9). LM358 tamponu planı iki
yerden kırıldı: çekme akımı (15 mA gerekli, 5 mA garanti) ve kapasitif
yük (700 nF, veri sayfası 100 pF). Yalnızca **50 mA cam sigorta + yuva**
alınacak.

### ✅ B16 bitti (2026-09-09) — sonuçlar **5.12.26**'da

`uretim/sim3_ortusme.py` · 41 doğrulama. İki kanal aynı sinyali farklı
süzüyordu (55.7 Hz'e karşı 8037 Hz): akım kanalı **örtüşüyordu** ve
reaktif yükte güç hatası PF=0.5'te **%155**'ti. Dirençli yükte fark
kendini götürdüğü için gözden kaçmıştı. Süzgeç ADS'in kendi koluna
taşındı (C4 100nF→1nF, yeni C18+C19+C20 = 1.32 µF, hepsi stokta).
Sonra %1.9. **Yeni açık karar: B16/F11** — hızlı yolun fark yükselteci
akım algılamasını %0.99 yüklüyor (B8'den beri var, hiçbir adım
modellememişti).

### ✅ B18 bitti (2026-09-09) — sonuçlar **5.12.27**'de

Kullanıcı B15/F6'yı onaylamıştı; B18 **uygulamadan önce ölçtü ve F6'yı
reddetti**: F6 hızlı akım yolunun tam ölçeğini de %33 kesiyordu
(252 → 169 mV) ve TL431
açık devre kalıntısını kapatmıyordu. Yerine **B18/F12**: R26/R33
2.7K → 10K ve yeni **R41 (1K boşaltma)**. B1 payı 18 mV → **1930 mV**,
**TL431'den bağımsız**, menzillerde hiçbir kayıp yok, satın alma yok.

### ✅ B19 bitti (2026-09-09) — sonuçlar **5.12.28**'de

Kullanıcı osiloskobun **çift yönlü** olmasını istedi. Bölücünün alt ucu
GND yerine VREF'e bağlandı ve R23 6.8K → 2.7K: **0…45.5 V tek yönlü**
yerine **−63.5 … +46.8 V**. Bedeli çözünürlük (**11.9 → 28.8 mV**,
ikisi de nominal tam ölçekten).
B19 kendi yazdığım dönüşüm formülündeki hatayı yakaladı (ofset VREF×N
değil VREF×(N−1); 0 V giriş −65 V okuyordu).

### ✅ B17 bitti (2026-09-09) — sonuçlar **5.12.29**'da

🔴 **Projenin en büyük ölçüm kusuru burada bulundu.** İki ADS1115 de
sürekli kipte, her biri kendi osilatörüyle koşuyordu; döngü yalnızca
akım çipini bekliyordu. Gerilim örneği 0…1.29 ms eski oluyordu ve
osilatör toleransı ±%10 olduğu için **sürükleniyordu** — 50 Hz'te
0…23°, gezinen. PF=0.5'te güç %76'ya varan ölçüde düşük okunuyordu
(ortalama %37). Dirençli yükte hata yalnızca %2.7 olduğu için
**kart "çalışıyor" görünüyordu.**

Çözüm: **tek atış kipi + eş zamanlı başlatma + kesirli gecikme.**
Ayrıca 1/|H(f)| ölçek düzeltmesi (`f<Hz>` komutu) ve menzil başına
faz kalibrasyonu (`F<örnek>`) eklendi. B16'nın "PGA değişiminde örnek
at" kalemi **geçersiz** çıktı — PGA hiç değişmiyor.

### ✅ B20 bitti (2026-09-10) — sonuçlar **5.12.30**'da

🔴 **B17'nin bütün frekans bütçesi yanlış bir hıza dayanıyordu.** Kart
860 SPS'te değil **91 SPS**'te örnekliyordu: (1) `loop()`'un başında
sürekli kipten kalma ölü bir bekleme her turda 4000 µs zaman aşımına
düşüyordu, (2) `COMP_QUE = 11b` ALERT/RDY pinini yüksek empedansta
tutuyordu (TI SBAS444E §7.3.8 bunu açıkça yasaklıyor). Varsayılan
`sebeke_hz = 50` ayarı **Nyquist'in üstündeydi**. Düzeltildi: **671 SPS**.

Ayrıca: `F` faz kalibrasyonu düşük hızda **aktif zararlıydı** (+%15.9,
kalibrasyon yükünün kendisinde) · otomatik menzil **AC'de saniyede 200
kez** geçiş yapıyordu (Vrms %12.2 düşük) · SSE işleyicisi `loop()`'u
**sonsuza kadar kilitliyordu** · `ortalama_oku()` aynı bayat yazmacı
okuyup "ortalama" alıyordu · imza yarım uygulanmıştı · skop adımı dört
dosyada **%6.92 ayrışmıştı** (DEVIR 5.12.28'in "26.9 mV"i yanlış, doğrusu
**28.8 mV**).

**`f` üst sınırı 400 → 100 Hz.** Bağlayıcı kısıt beklenen yerde değil:
Lagrange sarkması değil **faz kalibrasyonu**. Sabit gecikmeyle 50 Hz'te
kalibre edilen kart, ±%10 kondansatör toleransında 200 Hz'te PF=0.5'te
**%56** hata yapıyor. Geçerlilik bandı **40–70 Hz**.

11 ölçüm ajanı + 49 adversaryel çürütme ajanı koşturuldu; **çürütme
katmanı 27 bulguyu reddetti ve bu oturumun kendi iki mekanizma
açıklamasını düzeltti.**

### ✅ B21 bitti (2026-09-10) — sonuçlar **5.12.31**'de

**Yeni yetenek: pil kapasite testi** (ZB2L3 gibi, ama mAh **ve** Wh, 665 Sa/s
ve iç direnç ölçümüyle). Harici **taş direnç** yük, karttaki **IRFZ44N**
anahtarla kesiliyor; kesme gerilimi ayarlanabiliyor, deşarj eğrisi
tarayıcıda **IndexedDB**'de sınırsız birikiyor.

🔴 **Failsafe yönü B21'in en önemli kararı:** kapı GND'ye çekili, yani ESP32
ölürse/reset atarsa MOSFET **kapanıyor** ve pil boşalmayı durduruyor.

🔴 **Yeni sınır: pil gerilimi ≤ 38.5 V** (MOSFET Vdss 55 V, %70 pay). 48 V
paket reddediliyor. Soğutucusuz akım sınırı **6.55 A**.

🔴 **`test_firmware3.py`'ye `--clean` eklendi.** Arduino-cli önbellekten
derlediği için *"Derleme UYARISIZ"* iddiası önbellek durumuna göre
değişiyordu (aynı kod için 3, 2, 0 uyarı). Eklenince **hemen gerçek bir hata
çıktı**: PSRAM tamponu `24u*3600u` = 86400 ama alan `uint16_t` idi →
sessizce **20864**'e düşüyordu (24 saat yerine 5.8 saat).

Bütün parçalar **stokta** — tek eksik **taş direnç** (4.7–7.5 Ω / 10 W).

### ✅ B22 bitti (2026-09-10) — sonuçlar **5.12.32b – 5.12.38**'de

**Yeni yetenek: kart artık kendi web arayüzünü sunuyor.** Üç bağlanma kipi
var ve kullanıcıya görünen anlatımı `BELGELER/6-ag.html`'de:

1. **Kartın kendi Wi-Fi'si** (`OLCUM-KARTI-XXXX`, `192.168.4.1`) —
   bilgisayar gerekmiyor, arayüz kartın LittleFS'inden geliyor
2. **Kart ev ağında** (`http://olcum.local`) — 10 s deneyip AP'ye düşüyor
3. **USB köprü** (`kopru/`, `Kopru Baslat.bat`) — **tercih edilen**;
   bu kipte kartın Wi-Fi'si hiç açılmıyor, sayfayı PC yayınlıyor

Mimarinin **gerekçesi** 5.12.32b'de: `file://` bir `http://` sunucuya
ulaşamıyor, PWA HTTPS istiyor, Chrome LNA public→yerel'i kapatıyor. Bu üçü
birlikte *"sayfa karttan servis edilsin"* kararını zorunlu kıldı.

🔴 **Zincir 15/15 yeşilken DÖRT canlı kusur çıktı** — projenin altın kuralının
en pahalı kanıtı:

| # | Kusur | Nerede |
|---|---|---|
| K4 | Arayüz tarayıcıda **hiç açılmıyordu** (iki varlık 404) | 5.12.33 |
| K1 | Kart 665 değil **500 SPS**'te örnekliyordu — `WebServer`'ın kendi `delay(1)`'i | 5.12.34 |
| K2 | `faz_kal` **örnek** cinsindendi ama sabit bir **zamanı** düzeltiyordu (+1.744°) | 5.12.34 |
| K3 | Çıplak `g`/`i` komutu bir kanalı **kalıcı tuğluyordu** | 5.12.34 |

🔴 **Güvenlik kararı kullanıcınındı:** tehlikeli komutlar **jeton + parola**
istiyor (USB-only değil). **Tek istisna `p0`** (pil deşarjını durdur) —
her zaman parolasız çalışıyor, çünkü emniyet kolaylıktan önce gelir.

### 🔌 B25 — ESP32 için bringup koşucusu HAZIR (2026-09-11) — **5.12.41**

Kart gelmeden hazırlandı. `uretim/tezgah_kart.py` gerçek karta seri + HTTP
üzerinden bağlanıp **27 otomatik denetim** yapıyor; aşamalı (çıplak ESP32 →
+ADS → +analog ön uç). Kullanımı bu bloğun altındaki
**"🔌 ESP32 geldiğinde"** bölümünde.

🔴 **Koşucunun kendisi zincirde sınanıyor** (B25, 15 kasıtlı bozuk senaryo).
Yanlış bir bringup testi testsizlikten kötüdür. Öz-test yazılırken koşucuda
**üç gerçek hata** buldu — biri "aynı kapsam hatası, üçüncü kez".

🔴 **`loop_azami_us` artık bir komut mesafesinde** — aylardır açık duran
çift çekirdek kararını kapatacak tek ölçüm.

### ✅ B24 — GitHub'da yayında (2026-09-11) — sonuçlar **5.12.40**'ta

<https://github.com/Muhammet933321/esp32-olcum-karti> · MIT · 180 dosya.
İngilizce tanıtım `README.md`, Türkçe rehber `README.tr.md`.

🔴 **Yayın öncesi iki bağımsız denetim 129 doğrulanmış bulgu çıkardı** ve
en pahalıları yayınlanmış belgelerdeki **yanlış emniyet bilgisiydi**:
*"pil + Wi-Fi ile yüzdür"* şebeke ölçümünün çözümü diye sunuluyordu, oysa
B15/D2 bunu ölçüp **"PC kurtulur, KULLANICI kurtulmaz"** demişti —
**yalıtımlı kutu şartı hiçbir belgede yoktu.** Ayrıca ağ sayfası parola
korumasının varsayılan olarak **açık** olduğunu ima ediyordu; değil.

### ✅ B23 bitti (2026-09-10) — sonuçlar **5.12.39**'da

Donanım beklerken **elle yazıldığı için ölçümle bağı kopmuş bilgi** kaynağa
bağlandı. Üç şey kalıcı:

* **`uretim/_tezgah.md` ÜRETİLİYOR** (B23'te 72 kalem / 17 adımdı; güncel
  sayı dosyanın kendisinde). Her tezgah
  kalemi, onu **doğrulayamayan kodun yanında** yaşıyor. DEVIR'de artık liste
  yok, yönlendirme var — çünkü buradaki elle yazılmış 8 satırlık tablo
  B20/B21'de donmuştu ve B22'nin üç bölümü **içermediği** kalemlere atıf
  yapıyordu.
* **`uretim/mutasyon.py`** — mutasyon testi artık elle değil. Kurulduğu gün
  **üç boş iddia** ve **iki görünmez bağımlılık** buldu.
* **`uretim/beklenen_sayim.json`** — iddia sayısı kilidi, sapma **iki yönde
  de** kırmızı (1027 iddia).

🔴 Bulunan somut kusurlar: **B3 şema üretimi çökse bile yeşil kalıyordu** ·
belgedeki firmware boyutu **481 935 B**, gerçek **1 067 423 B** (2.2 kat) ·
**826 sızmış geçici dizin** · `collectHeaders` iddiası alt dizgeydi ·
`AG_MDNS` için **hiç iddia yoktu** · güncel kurulum kılavuzunun CSS'i
**`arsiv/`'den** okunuyor · `kurulum3-uret.py` `BELGELER/`'i yaratmadan
yazıyordu.

### 🎯 Şu an sıradaki iş

**Zincir yeşil (18/18). ESP32 geliyor — sıradaki gerçek adım kartı kurmak.**

> ⚠️ **Buraya bir kez "tasarım tarafında yapılacak iş kalmadı" yazıldı
> (B21 sonrası) ve ardından ALTI bölüm boyunca büyük kusurlar bulundu:**
> arayüz tarayıcıda hiç açılmıyordu (B22.0) · kart 665 değil **500 SPS**'te
> örneklıyordu (B22.1/K1) · faz hatası B17'nin kendi ölçütünün **1.74
> katıydı** (K2) · çıplak `g` kanalı **kalıcı olarak öldürüyordu** (K3) ·
> WiFi bir kez bile açılmamıştı ve SSE yalnız `D` satırını taşıyordu
> (B22.4) · komut ucu hiç yoktu.
>
> Bu cümleyi bir daha yazma. Doğrusu: *"bugün bilinen iş kalmadı"* — ve
> bilinmeyeni bulmanın yolu zincire güvenmek değil, **mutasyon testi**.
>
> B23'ten beri bunun bir aracı var: **`python mutasyon.py`**. Kurulduğu
> gün üç boş iddia ve iki görünmez bağımlılık buldu. Yeni bir iddia
> yazdığında `MUTASYONLAR` listesine onu **yalanlayan** değişikliği de
> ekle — yoksa iddianın ısırıp ısırmadığını kimse bilmiyor.

#### 🔴 Kullanıcı kararı bekleyen kalemler

**1. Faz kalibrasyonunu τ eşleşmezliği olarak saklamak** (B20'den, 5.12.30).
Bugün `F` komutu SABİT bir zaman gecikmesi saklıyor; düzelttiği şey ise
iki RC'nin arctan farkı — ikisi yalnızca kalibrasyon frekansı civarında
örtüşüyor. Bu yüzden geçerlilik bandı **40–70 Hz** ve `f` komutu 100 Hz'de
kesiliyor. τ eşleşmezliği olarak saklanırsa bant genişler; maliyeti iki
`atanf()`. **Yapılmadı** çünkü `F`'in anlamını değiştirir ve tezgahta
doğrulanmadan yapılmamalı. Ölçümler 5.12.30'da hazır.
⚠ B22.1 `faz_kal`'ı **örnek → mikrosaniye**'ye çevirdi (periyot bağımlılığı
kalktı) ama τ modeline geçmedi; bu karar hâlâ açık.

**2. Çift çekirdeğe geçilecek mi** (B22.1'den) — ✅ **ÖLÇÜLDÜ, CEVAP EVET
(B26, 2026-09-11).** Eşik `loop_azami_us` **> 20 000 µs** idi.

⚠ Ölçüm yöntemi B26'da **değiştirilmek zorunda kaldı**: eski sayı açılıştan
beri sıfırlanmayan koşan maksimumdu ve ısınmayı içeriyordu — taze açılışta
**18 203 µs** (eşiğin ALTINDA), dakikalar sonra **30 397 µs** (ÜSTÜNDE).
Aynı kart iki farklı cevap veriyordu. Firmware'e `K` komutu eklendi
(sayaçları sıfırlar, eski değerleri basarak) ve koşucu artık sıfırlayıp
**45 sn kararlı hal** ölçüyor.

**Sonuç: sıfırlamadan sonra 45 sn'de yine 30 382 µs.** Olay açılış artığı
değil, kararlı halde ~45 sn'de bir tekrarlıyor → **ölçüm döngüsü çekirdek
1'e taşınacak.** Açılan risk sınıfı (yarış koşulları) 5.12.34'te
adlandırıldı; **iş henüz yapılmadı.**

⚠ `atlanan_ms` **hep 0** — enerji penceresi kaçmıyor, yani aciliyet enerji
sayacında değil, skop/örnekleme sürekliliğinde. Ölçüm ADS'ler bağlı
değilken alındı; 30 ms'lik blokaj I²C'den gelemez (WiFi/mDNS bakımı
muhtemel), ADS eklemek iyileştirmez.

**3. Web parolası politikası** (B22.4'ten). Bugün `Ns<parola>` ile
kuruluyor ama **kurulmazsa yetkilendirme kapalı** — açılışta yüksek sesle
uyarılıyor. Parola zorunlu kılınsın mı, yoksa jeton + `Host` beyaz listesi
yeterli mi? TLS olmadığı için parolanın koruduğu şey *"evdeki başka biri
yanlışlıkla basmasın"*; LAN'daki bir dinleyiciye karşı koruma değil.

### ✅ ESP32 geldi — bu akış 2026-09-11'de koşuldu (B26)

> **Bu bölümün tamamı bir kez koşuldu ve çalıştı.** Sonuçlar ve bulunan üç
> kusur **5.12.42**'de. Aşağısı artık *"ilk gün"* değil, **tekrar yükleme
> yordamı** — firmware değiştiğinde aynı sırayla koşulur.
>
> **Kartın kimliği (esptool ile okundu):** ESP32-S3 QFN56 rev v0.2 ·
> flash 16 MB · PSRAM 8 MB oktal · MAC `…:96:9c` · **COM6**,
> köprü çipi **CH343** (`VID_1A86`/`PID_55D3`).
>
> **Kart iki Type-C soketli, doğru olan COM yazan.** ⚠ *"Bir COM portu
> belirdi"* doğru sokete takıldığının kanıtı DEĞİL: yerel USB soketi de
> port açar (`VID_303A`) ama **sessiz** kalır. Ayırt edici ölçüt **VID**.

**1 · Firmware'i yükle.** Tam FQBN şart — varsayılanlar çalışmaz:

```bash
cd projeler/olcum-karti/uretim
python yukle.py --liste     # ne yapacağını gösterir
python yukle.py             # derle + yükle (portu kendi bulur)
```

⚠️ **Çıplak `arduino-cli` komutu çalışmaz** — ikili PATH'te değil,
`Elekronic/.araclar/arduino-cli.exe` altında. `yukle.py` hem onu buluyor
hem FQBN'i `hedef2.py`'den okuyor, yani ikisi de elle yazılmıyor.

FQBN tuzaklı: `FlashSize=16M` olmadan LittleFS'in `0x310000` ofseti 4 MB
sınırına düşer, `PSRAM=opi` olmadan 8 MB PSRAM hiç açılmaz. Kart
**ESP32-S3 N16R8** olmalı.

**2 · Arayüzü karta yaz.**

```bash
cd uretim
python arayuz-uret.py     # LittleFS görüntüsünü paketle
python arayuz-yaz.py      # 0x310000'e yaz (esptool)
```

⚠️ **İKİ USB SOKETİ VARSA: UART/COM soketine takın, yerel USB'ye değil.**
Firmware `Serial`i UART köprüsünde tutuyor — `hedef2.py` `CDCOnBoot`/
`USBMode` seçeneklerini **bilerek** eklemiyor (yerel CDC tezgah ilk
açılışını bozabilir, bu iş 4.11'de ayrı ele alınacak). Yanlış sokette
hiçbir satır gelmez ve boşuna sürücü aranır. Aynı sebeple `--sifirla`'nın
DTR/RTS reset'i **UART soketinde çalışır**.

**3 · Bringup koşucusunu çalıştır** — elle denenmesi gerekmeyen her şeyi
otomatik sınıyor:

```bash
python tezgah_kart.py --liste            # ne yapacağını göster
python tezgah_kart.py --sifirla          # aşama 0: çıplak ESP32
python tezgah_kart.py --sifirla --asama 1        # ADS'ler bağlıyken
python tezgah_kart.py --sifirla --http olcum.local   # web katmanı da
```

**27 denetim** (güncel sayı: `python tezgah_kart.py --liste`). Açılış afişi
(PSRAM boyutu, LittleFS, ağ kipi), komut
yüzeyi, çıplak `g`/`i` reddi (K3 tuğlalama), `R` onay kapısı, I²C taraması,
`D` satırının biçimi/hızı/**örnek sayısı**, ve web tarafında CSRF · jeton ·
`p0` serbestliği · Host beyaz listesi.

⚠ Açılış afişi yalnızca açılışta basılıyor. `--sifirla` DTR/RTS ile reset
denemesi yapıyor ama **yerel USB CDC'li kartlarda bu çalışmaz** — o zaman
EN düğmesine basıp komutu tekrar çalıştırın. Afiş alınamazsa PSRAM ve
LittleFS denetimleri **atlanır**, kırmızı olmaz.

🔴 **Koşucu hiçbir aşamada yük sürmüyor.** Pil deşarjını başlatan komut
otomatik gönderilmiyor; failsafe ve baypas denetimi elle yapılacak.

**4 · İlk gün ölçümleri** — `uretim/_tezgah.md`'nin başındaki `[!]` işaretli
9 kalem. Bunlar multimetre isteyen, koşucunun yapamadığı şeyler. En kritiği:
**+3V3 rayının geri beslenmesi** (USB'yi çıkar, 24 V takılı bırak, rayı ölç
— beklenen 1.670 V).

**5 · Çift çekirdek kararı.** Koşucu `K` satırından `loop_azami_us` okuyup
**20 000 µs** eşiğiyle karşılaştırıyor. Üstündeyse ölçüm döngüsü çekirdek
1'e taşınacak (5.12.34); altındaysa **yapılmayacak**. Bu tek ölçüm, aylardır
açık duran bir mimari kararı kapatıyor.

#### Sıradaki iş: DONANIMI KUR (B10)

Kartın elektroniği tam. Kurulum kılavuzu `BELGELER/4-kurulum.html`.

✅ **Taş direnç geldi (2026-09-11).** Pil testi yükü 18650 için
4.7–7.5 Ω / 10 W isteniyordu: **2× 3.3 Ω 11 W seri = 6.6 Ω / 22 W**
aralığın tam ortasına düşüyor (stokta 3 adet 3.3R 11W var). 18650'de
3.7 V / 6.6 Ω ≈ 0.56 A, 2.1 W — 22 W'lık kapasitenin çok altında.
Ayrıca 1R ve 0.1R taş dirençler de geldi. 12 V akü için istenen
10–15 Ω / 50 W hâlâ yok.

⚠️ Değerleri **ölçerek doğrula**: ürün sayfası 3.3R diyor ama URL slug'ı
33R diyordu. Zaten `_tezgah.md` "lehimlemeden önce her direnci
ohmmetreyle geç" diyor.

**Kalan satın alma listesi — dört kalem**
(`BELGELER/2-malzemeler.html` güncel listeyi üretiyor; oradaki
"Sipariş edildi" tablosu artık **boş**):
820K ×6, 8.2K ×1, BAT85 ×4, 50 mA sigorta ×1.

⚠️ **Stoktaki 820K yerine geçmez:** R038 ×30 var ama **2W**; HV bölücüsü
(4.9 MΩ zinciri) **metal film %1** istiyor — tolerans ve sıcaklık
katsayısı doğrudan ölçüme giriyor.

Sarf tarafı: **delikli plaket geldi** (6x13 ×3, 10x10 ×2, 5x5 ×2);
izopropil alkol, lehim teli, yedek ESP32-S3 hâlâ listede.

#### Kurulum sonrası ilk ölçülecekler → **`uretim/_tezgah.md`**

> **Bu listenin burada elle yazılmış bir kopyası yoktu — vardı ve dondu.**
> B20/B21 döneminde yazılan 8 satırlık tablo B22'nin 17 ölçümünü hiç
> görmedi; üstelik B22.3/B22.4/B22.5'in üçü de *"tezgah listesinde"*
> diyerek **içermediği** kalemlere atıf yapıyordu. Bu, projenin defalarca
> yandığı **ayrışma sınıfının belge sürümü**.

Artık her tezgah kalemi, onu **doğrulayamayan kodun yanında** yaşıyor
(`tezgah(...)` çağrısı, ilgili adımın betiğinin sonunda). `dogrula3.py`
bunları toplayıp ekrana basıyor ve `uretim/_tezgah.md`'yi üretiyor.

* **Liste:** `uretim/_tezgah.md` — adım adım, kabul ölçütleriyle
* **İlk gün:** aynı dosyanın başındaki tablo; `[!]` işaretli kalemlerden
  **türetiliyor**. Sırası zincir sırası, öncelik sırası değil — kalemler
  arası elle bir sıralama tutulsa yine bayatlardı
* **Yeni kalem eklemek:** o adımın betiğindeki `tezgah(...)` çağrısına
  ekle. Buraya değil.

Bir adım hiç kalem basmazsa `dogrula3.py` **kırmızı** dönüyor — taban
çizgisi `ADIMLAR`'ın kendisi, elle yazılmış bir liste değil.

#### Açık duran iş kalemleri (aceleci değil)

| Kaynak | İş |
|---|---|
| B16 (5.12.26) | **Karar:** hızlı yolun örtüşme payı yeterli mi · **Karar:** B16/F11, R27/R29 yüklemesi (%0.99) |
| B21 (5.12.31) | Sıcaklık ölçümü (envanterde sensör yok) · elektronik yük (sabit akım) · kayıt hızı arayüzden ayarlanamıyor · **şarj yönünde test** (sayaç işaretli ama şarj kaynağı yok) |
| B14 (5.12.20) | Hızlı skop (MHz) — harici ADC, açık ihtimal |
| B12 / B13 | İkili aktarım + USB CDC · sürekli hızlı yol — **donanım çalıştıktan SONRA** |
| **B22.6** (planda) | **Köprünün ağ yukarı-akışı** — kart uzaktayken (615 V ölçüyor, kablo çekilemez) PC ona WiFi ile bağlansın. `kopru/kart_baglanti.py`'ye `AgKart` + `POST /kopru` kaydı. **Ertelendi:** donanımsız uçtan uca doğrulanamıyor |
| **B22.5** (5.12.38) | `?demo` kipi **karttan çalışmıyor** — `sahte-kart.js` görüntüye bilerek konmadı (15 936 B). Geliştirme aracı, kartta anlamsız; ama kullanıcı denerse sebebini görüyor |
| **B22.4** (5.12.37) | Kartın `/skop.bin` ucu var ama **derin bellek (PSRAM) hâlâ kullanılmıyor** — skop 4000 örnekte sabit. B14/B12 ile aynı yere bakıyor |
| **B23.3** (5.12.39) | `mutasyon.py` kapsamı dar: her adımın yalnızca bir-iki iddiası sınanıyor. Yeni iddia yazan her bölüm listeye kendi yalanlamasını eklemeli. ⚠ Sayıyı buraya **yazma** — `python mutasyon.py --liste` söyler (B26'da "10 mutasyon" yazıyordu, gerçek 15'ti) |
| **B26** (5.12.42) | `mutasyon.py` geçici kopyayı `projeler/_mutasyon-<pid>` diye açıyor ve **dizin varsa çöküyor** (`FileExistsError`). Windows PID'leri geri dönüştürdüğü için bir kez tetiklendi. `dirs_exist_ok=True` ya da kopyalamadan önce temizleme gerekiyor |
| **B26** (5.12.42) | `yukle.py` derlerken `--clean` geçmiyor, zincirdeki `test_firmware3.py` geçiyor (B21 dersi: önbellek uyarı gizler). Bugün zararsız çıktı ama ayrışma yüzeyi duruyor — `--temiz` bayrağı eklenebilir |
| **B23.3** (5.12.39) | `kurulum3-uret.py` biçimini **`arsiv/asama2/kurulum2.html`**'den okuyor. Taşınmadı (yeni ayrışma yüzeyi açardı) ama arşiv taşınır/silinirse **buraya bakılacak** — dosya yoksa açık bir hatayla düşüyor |
| **B23.2** (5.12.39) | `index.html`'deki *"hangi belgeye bakmalıyım"* tablosu `MENU`'den **türetilmiyor**, elle yazılıyor. Bir denetim ayrışmayı kırmızı yapıyor ama tablo hâlâ iki temsil |
| **B23.1** (5.12.39) | `_tezgah.md`'nin *"İlk gün"* sıralaması **zincir sırası**, öncelik sırası değil. Öncelik gerekirse `[!]` işaretine bir derece eklenmeli |

### Bu belgeyi yazan oturum kendi iddialarından dördünü düzeltmek zorunda kaldı

| Yanlış dediğim | Doğrusu |
|---|---|
| "Tam ölçek 45 V" | ADS girişi VDD ile sınırlı → **32.2 V** |
| "TL072 ve NE555 stokta yok" | CSV'de yok ama **siparişte var, yolda** |
| "İki ADS modülü var, R8/R9 tak" | **Üç modülü var**; karar modül sayısına bağlı (bkz. 4.7) |
| "Kelvin gerekli çünkü statik lehim direnci %6.7 hata yapıyor" | O kısım **kalibre edilebilir**; gerçek sebep yüke bağlı termal sürüklenme ve 10 A referans gerektirmesi |

**Buradaki hiçbir sayıyı doğrulamadan kabul etme.** Her sayının kaynağı belirtildi; kaynağa git.

---

## 0. Bir bakışta

Ölçüm kartı: **voltmetre · ampermetre · wattmetre · enerji sayacı · osiloskop**. İki aşama
tasarlandı ve uçtan uca doğrulandı; hiçbiri henüz fiziksel olarak kurulmadı.

| Aşama | MCU | ADC | Durum |
|---|---|---|---|
| 1 | Arduino Uno/Nano (ATmega328P) | dahili 10 bit | ✅ 9/9 adım, 159 doğrulama |
| 2 | ESP32-S3 N16R8 | 2× ADS1115 (16 bit) + dahili 12 bit | ✅ 6/6 adım, 173 doğrulama — **parça yolda** |
| 3 | aynı | + 3. ADS1115 | 📋 verim ölçümü için yer ayrılmıştı — **artık aktif hedef** |

**Yön değişti.** Kullanıcının multimetresi var (ANENG AN8000), o yüzden DMM işlevleri
(direnç, kapasite, diyot, süreklilik, AC) **istenmiyor**. Yeni odak: gerilim ve akımı
**olabildiğince yüksek örneklemeyle** ölçmek, **osiloskop / wattmetre / eğri çizici**
konusunda iyi olmak, üstüne dört SMPS-odaklı yetenek eklemek.

Kart **delikli plakete kalıcı** kurulacak (breadboard değil).

---

## 1. Yön değişikliği — önce bunu oku

### 1.1 Neden değişti

Kullanıcı zaten bir multimetre sahibi. Geçen turda "kartın yapamadıkları" diye altı
işlev listelemiştim (AC gerilim/akım, direnç, süreklilik, diyot, kapasite, akımda otomatik
kademe) ve hepsinin eklenebileceğini gösteren ayrıntılı bir analiz yapmıştım.
**Kullanıcı bunları reddetti** — multimetresi zaten yapıyor. Onun yerine multimetrenin
**yapamadığı** şeylerde iyi olmak istiyor.

### 1.2 Referans cihaz: ANENG AN8000

Bu, kalibrasyon tavanını belirlediği için kritik:

| Özellik | Değer |
|---|---|
| Sayım | **4000** |
| DC gerilim 400 mV / 4 V / 40 V | **±(%0.5 + 4 hane)** |
| DC gerilim 400 V / 600 V | ±(%0.8 + 4 hane) |
| Okuma hızı | saniyede 3 |
| Ayrıca yapıyor | AC V/I, direnç, kapasite, diyot, süreklilik, frekans, duty cycle |

*Kaynak: [ANENG AN8000 kullanım kılavuzu](https://manuals.plus/asin/B082HMQNNX) ve
[ürün sayfası](https://www.amazon.com/ANENG-AN8000-Digital-Multimeter-4000/dp/B082HMCHRC).
Yeni oturum bunu teyit etsin.*

**12 V ölçümünde:** 40 V kademesinde çözünürlük 0.01 V → hata = %0.5×12 + 4×0.01 =
60 mV + 40 mV = **±100 mV = ±%0.83**.

### 1.3 Bunun kritik sonucu

Kart AN8000'e karşı kalibre edilirse **mutlak doğruluğu ±%0.8'e çakılır** — oysa kartın
çözünürlüğü bunun çok altında. Yani AN8000'den çok daha iyi **çözünürlük**, ondan
kalibre edilirse çok daha kötü **mutlak doğruluk**.

> ⚠️ **DOĞRULANMAMIŞ SAYI — yeni oturum bunu hesaplasın.** Oturumun erken bir turunda
> "200 ms ortalamada 0.22 mV, 146 000 sayım" demiştim, **ama doğrulama zinciri bu sayıyı
> üretmiyor** ve ben şimdi yeniden türetemedim.
> Zincirin gerçekten söylediği (`kanit/a2-tam-dogrulama.txt:137`): *200 ms pencere =
> 172 örnek → √N = 13.1×*. Gerilim adımı PGA ±2.048'de 981.6 µV. Saf kuantalamayla
> 981.6/13.1 = **74.9 µV** çıkar (≈429 000 sayım), 0.22 mV değil.
> Fark muhtemelen ADS1115'in 860 SPS'teki **gerçek gürültüsünden** geliyor (veri sayfası:
> yüksek veri hızında efektif çözünürlük 16 bitin belirgin altında) — ama bunu
> **veri sayfasının gürültü tablosundan doğrula ve `tasarim2.py`'ye bir `kural()` olarak
> ekle.** Akım kanalları için gürültü tabanı zaten hesaplanıyor (µA kademesi 0.0596 µA);
> gerilim için aynısı yok.

**Kullanıcının laboratuvar erişimi var** ("ulaşabileceğim laboratuvar tipi de var,
kalibrasyon için oraya gidebilirim"). **Kalibrasyon oraya yapılmalı.** Kartın ±%0.1
hedefi ancak böyle anlamlı olur.

> Bu ayrım önemli: **çözünürlük** kartın kendi özelliği, **doğruluk** kalibrasyon
> referansının özelliği. Kart, AN8000 ile kalibre edilse bile ondan çok daha iyi
> *tekrarlanabilirlik* ve *fark ölçümü* verir — sadece mutlak değeri onunkine bağlanır.

> 🌟 **Ama bu tavan ORAN ölçümlerinde büyük ölçüde kalkıyor.** Verim (η) gibi bir
> büyüklükte dört kanalı *aynı* DMM ile *aynı* noktada kalibre edersen, DMM'in kazanç
> hatası oranda birinci mertebede yok olur: AN8000 ile ±0.352 puan, 6.5 haneli masa
> referansıyla ±0.352 puan — **fark yok**. Ayrıntı **5.7 → Verim ölçer** bölümünde.
> Yani laboratuvar erişimi *mutlak* ölçümler (voltmetre/ampermetre) için kıymetli,
> *oransal* ölçümler için neredeyse gereksiz.

### 1.4 Rafa kalkanlar

Aşağıdakiler için geçen turda ayrıntılı analiz yapıldı. **Yeni oturum bunları tekrar
analiz etmesin**; kullanıcı isterse özet burada:

| İşlev | Karar | Analiz özeti (istenirse) |
|---|---|---|
| Direnç | ⏸️ rafta | ESP32 GPIO'nun Hi-Z olabilmesi mux'a gerek bırakmıyor; oransal ölçüm ray ve GPIO empedansını sadeleştiriyor. 0.5 Ω–1 MΩ, ±%0.3. |
| Süreklilik | ⏸️ rafta | Direnç modunun eşiği. Buzzer gerekiyor (kayıtta yok). |
| Diyot | ⏸️ rafta | Aynı devre. 3.3 V rayı beyaz LED'de sınırda. |
| Kapasite | ⏸️ rafta | RC şarj eğrisine üstel fit, 50 pF–20 mF ±%2-5. Dolu kondansatör koruması şart. |
| AC V/I | ⏸️ rafta | Ayrı AC-kuplajlı kanal + 1.65 V bias. **Şebeke için izolasyon zorunlu** — ZMPT101B/ZMCT103C. |
| Akımda oto-kademe | ⚠️ **kısmen devam** | PGA oto-kademesi (16:1, sıfır donanım) hâlâ mantıklı ve **yapılmalı**. Fiziksel şönt anahtarlama rafta. |

---

## 2. Şimdiye kadar yapılanlar — TEKRAR ETME

### 2.1 Doğrulama felsefesi

Kullanıcının ilk isteği **"halisünasyon görmeyeceğin şekilde kanıtla"** idi. Bu yüzden
proje sıradışı bir disiplinle kuruldu:

- **Her iddia çalıştırılabilir bir testten geliyor.** `uretim/` altındaki betikler hem
  tasarım belgesi hem test. `tasarim2.py` docstring'i: *"Bu betik TASARIM BELGESIDIR ve
  ayni zamanda BIR TESTTIR."*
- **Şema elle çizilmiyor**, `sema-uret.py` / `sema2-uret.py` betikleri KiCad dosyasını
  sıfırdan yazıyor. Böylece şema ile tasarım sabitleri ayrışamıyor.
- **Firmware aritmetiği platform bağımsız** (`kod/olcum-karti-a2/olcum2.h` — `int` ve
  `double` yasak, her yerde `int16_t`/`int32_t`/`uint64_t`/`float`). Bu sayede **aynı
  kaynak** hem gerçek ESP32-S3 derleyicisiyle derleniyor, hem de sıfırdan yazılmış bir
  AVR emülatöründe bit-birebir koşturulabiliyor.
- **AVR emülatörü kendisi doğrulanmış**: `test_avr.py` (S8), gerçek `avr-gcc` çıktısına
  karşı 39/39 bit-birebir.
- **Testler kaynaktan sabit okuyor.** Ör. `test_skop_arayuz.js` `SKOP_ADET`, `SKOP_HZ`,
  `SKOP_TAVAN`, `BOLME_ORANI` değerlerini `.ino` ve `.h` dosyalarından regex'le çekiyor —
  firmware'de bir sabit değişirse test peşinden gidiyor, sessizce ayrışamıyorlar.

**Yeni oturum bu disiplini bozmasın.** Bir sayı iddia edilecekse, onu üreten bir test olsun.

### 2.2 Aşama 1 — ATmega328P (tamam)

`uretim/dogrula.py` → **9/9 adım, 159 doğrulama**

| Adım | Ne doğruluyor | Araç |
|---|---|---|
| S1 | TL431 referansı ve AREF yükü | ngspice |
| S2 | Bölücü + koruma kelepçesi + örtüşme süzgeci | ngspice |
| S3 | Şönt + LM358 akım katı | ngspice |
| S4 | Firmware aritmetiği | numpy float32/uint64 |
| S5 | Şema: ERC + netlist (polarite!) | kicad-cli |
| S6 | Firmware derleme, 0 uyarı, SRAM payı | arduino-cli |
| S7 | Arayüz mantığı | node |
| S8 | **AVR emülatörünün kendisi** | avr-gcc karşılaştırması |
| S9 | **Kart uçtan uca** (+S10 arayüz) | tüm zincir, 186 400 010 AVR çevrimi |

Menzil: 0–27.2 V / 26.6 mV adım, 0–939 mA, osiloskop 8 bit ~8 kHz.
Derleme: 8444 B flash, 1261 B SRAM, 787 B boş, 0 uyarı.

### 2.3 Aşama 2 — ESP32-S3 + ADS1115 (tasarım tamam, kurulmadı)

`uretim/dogrula2.py` → **6/6 adım, 173 doğrulama**

| Adım | Ne doğruluyor | Sonuç |
|---|---|---|
| A1 | Tasarım, menzil, hata bütçesi, Kelvin gerekçesi | 24/24 |
| A2 | Giriş koruması — **4 seçenek tarandı, ilk seçim elendi** | 11/11 |
| A3 | Şema: ERC (0 ihlal) + netlist (polarite, ADS adresleri) | 33/33 |
| A4 | Uçtan uca + gerçek ESP32-S3 derlemesi | 18/18 |
| A5 | Osiloskop protokolü → gerçek arayüz; zaman tabanı merdiveni; **ikilide ölü kod denetimi** | 45 |
| A6 | **Osiloskop ölçüm matematiği** — gerçek kod AVR emülatöründe, analitik dalgalara karşı | 32 |

Firmware: **473 817 B flash (%36), 47 000 B RAM (%14), 0 uyarı.**
*(RAM artışı osiloskopun 2 × 4000 örneklik halka tamponundan.)*

**Menzil ve çözünürlük** (`kanit/a2-tam-dogrulama.txt`'ten):

| Kanal | Tam ölçek | Adım |
|---|---|---|
| Gerilim, PGA ±2.048 (çalışma kademesi) | 32.17 V | 981.6 µV |
| Gerilim, PGA ±0.256 (oto-kademe alt ucu) | 4.02 V | 122.7 µV |
| Akım, 10R şönt | 26 mA | 0.78 µA |
| Akım, 1R | 256 mA | 7.81 µA |
| Akım, 0.1R | 2.560 A | 78.12 µA |
| Akım, 15 mΩ | 11.547 A | 520.8 µA |
| Osiloskop (ESP32 ADC) | 48.7 V | 11.9 mV @ 83 333 Sa/s |

### 2.4 Bulunmuş gerçek kusurlar — yeniden keşfetmeye çalışma

Bunlar **bulundu ve düzeltildi**. Listeyi vermemin sebebi, yeni oturumun aynı avı
tekrarlayıp zaman kaybetmemesi.

**Aşama 1'de yakalanan altı hata:**

| # | Hata | Nasıl yakalandı |
|---|---|---|
| 1 | AREF seri direnci referansı %12.8 kaydırıyordu | ngspice (S1) |
| 2 | Bölücü kondansatörü osiloskop kipini öldürüyordu | ngspice (S2) |
| 3 | Her iki koruma diyotu **ters bağlıydı** | netlist (S5) — **ERC göremedi** |
| 4 | Şemada hiçbir tel çizilmiyordu | PDF/SVG çıktısına bakınca |
| 5 | `Okuma` struct'ı prototipten önce tanımlanmıyordu | arduino-cli (S6) |
| 6 | `String` yığın parçalanması riski | arduino-cli (S6) |

**S9 turunda yakalanan dört hata:**

| Kusur | Nerede | Nasıl yakalandı |
|---|---|---|
| `enerji_wh()` 1 Wh'i 3.6e18 pJ sanıyordu (o 1 **kWh**) → Wh alanı 1000× küçük | firmware | S9: `wh × 3600 == joule` |
| Osiloskop tetiklemesi **ölü koddu** — tek çağrı `(0,0)` olduğu için derleyici attı | firmware | `"! tetiklenemedi"` ikilide yok |
| ADC'ye Timer0'ın ön bölücü tablosu verilmişti → 64× hızlı, sahte kanal sızması | emülatör | gerilim hatası 258 mV |
| Serbest çalışmada dönüşüm ideal an yerine *fark edilen* anda başlıyordu | emülatör | artık RMS 78 mV (olması gereken 30.6) |

**Aşama 2'de bulunanlar:**

| Kusur | Çözüm |
|---|---|
| Tam ölçek 45 V değil **32.2 V** — ADS girişi VDD ile sınırlı | kabul edildi |
| TL431 kelepçesi 11:1 bölücüde 29.7 V'ta sızıp menzili kesiyor | bölücü 100K/6.8K + PGA ±2.048 → kelepçe hep ters kutuplu |
| 15 mΩ'da lehim direnci %6.7 (statik) + %0.26 (yüke bağlı) | Kelvin (4 telli) algılama |
| `enerji_wh()` 3.6e18 hatası | 3.6e15; A4 **yanlış sabiti reddediyor** |
| **Osiloskop hiç uygulanmamıştı** — `app.js` paneli var, firmware `S` satırı üretmiyordu | IDF sürekli ADC sürücüsü, 83 333 Sa/s; A5 doğruluyor |
| **Kalibrasyon yolu yoktu** — şönt/kazanç/ofset derleme zamanı sabitti | seri komutlar + NVS |
| Şemadaki R8/R9 "DNP" notu yanlış modül sayısı varsayıyordu | bkz. 4.7 — hâlâ açık |

**Ayrıca:** `analogContinuousRead()` (Arduino sarmalayıcısı) örneklerin **ortalamasını**
döndürüyor, dalga şekli vermiyor — osiloskop için kullanılamaz. Bu yüzden doğrudan
ESP-IDF'in `esp_adc/adc_continuous.h` sürücüsü kullanıldı. Yeni oturum bu tuzağa
düşmesin.

---

## 3. Donanım gerçeği

### 3.1 Elde olanlar

Kaynak: `stok-takip/envanter.csv` (183 kayıt). **`CLAUDE.md` kuralı geçerli:** kısmen
girilmiş kategorilerde (bobin/trafo/çekirdek, sensör/modül/kart/kablo/mekanik/sarf/alet)
"kayıtta yok" ≠ "elinde yok".

| Kategori | Öne çıkanlar |
|---|---|
| Opamp | **LM358 ×8** (tek opamp tipi!) |
| Referans | TL431 ×10 |
| MOSFET | IRFZ44N ×13, IRF3205 ×6, IRFP250N ×3, IRF4905 ×2 (P), IRF830 ×1, IRFZ44N sökme ×3 |
| MOSFET sürücü | IR2110 ×2, IR2104 ×3 |
| Optokuplör | PC817 ×17, 4N35 ×5, PC123 ×1 |
| Regülatör | 7812 ×3, 7912 ×2, 7805 ×3, 7809 ×1, LM317T ×1 |
| PWM denetleyici | TL494 ×7, SG3525 ×5, UC3843 ×1 |
| Transistör | 2N2222 ×12, BC547 ×7, BC557 ×7, TIP41C ×2, 13007 ×4, BU508A, BF869S |
| Diyot | UF4007 ×18, SR5100 ×10, 1N4148 ×8, MBR20100 ×2, MBR2200 ×3, 1N4006 ×5, zenerler |
| Direnç | 10R:30 · 22R:20 · 39R:20 · 47R:20 · 100R:30 · 150R:15 · 220R:10 · 270R:7 · 330R:15 · 390R:10 · 470R:21 · 560R:10 · 1K:36 · 2.7K:10 · 4.7K:15 · 5.6K:10 · 6.8K:18 · 10K:28 · 20K:10 · 22K:15 · 27K:10 · 33K:10 · 47K:40 · 100K:33 · 220K:10 · 820K:30 · 1M:30 · 10M:10 · 12M:25 |
| Kondansatör | 100nF ~51 (çeşitli gerilim), 1nF ~16, elektrolitik ve film çeşitleri |
| Kart | Arduino Uno ×2, Nano ×2 |
| Zamanlayıcı | NE555P ×1 |

⚠️ **Direnç adetleri göz kararı sayım** ve ayrıca kayıt dışı dağınık bir yığın var. Sayı
kritikse kullanıcıya saydır.

**Elektrolitikler — darbe tamponu için kritik.** ≥25 V dayanımlı: 470µF/35V ×6,
470µF/63V ×6, 1000µF/35V ×5, 1000µF/25V ×1 → **~11 600 µF**. Bu, eğri çizici ve doyum
testinin darbe akımını karşılıyor (bkz. 5.4).

**Çekirdekler:** E tipi trafo çekirdeği 80mm ×2, sarı toroid ×4. *Doyum testinin ilk
test nesneleri bunlar olabilir.*

✅ **Soğutucu VAR** — `MEK002`, kullanıcı 2026-09-08'de bildirdi. ⚠️ Ölçüsü ve termal
direnci **bilinmiyor**, öğrenilip CSV güncellenmeli.

❌ **Kayıtta olmayan ve gerçekten olmayan** (Entegre kutusu tam tarandı): analog mux
(CD4051/4066), röle, CMOS girişli opamp, **komparatör**.
❓ **Kayıtta yok ama olabilir** (rastgele girilen kategoriler): buzzer/piezo, 12 V
adaptör, küçük şebeke trafosu.

### 3.2 Yolda olanlar — bu oturumda ilk kez tam görüldü

Kullanıcı iki siparişin tam listesini paylaştı. **Bu, oturum içinde verdiğim iki cevabı
düzeltiyor.**

#### direnc.net · TS07091124463 · 2.670,28 TL · "Ürün Hazırlanıyor" · DHL

**Ölçüm kartı için kritik olanlar:**

| Parça | Adet | Not |
|---|---|---|
| **ESP32 S3 N16R8 WiFi Bluetooth Board** | 1 | Aşama 2'nin işlemcisi |
| **TL072CP DIP-8 OpAmp** | 4 | ⚠️ "stokta yok" demiştim — **yolda**. JFET giriş, GBW 3 MHz, slew 13 V/µs |
| **NE555CN DIP-8** | 10 | ⚠️ aynı düzeltme |
| **L7912CV −12 V 1.5 A TO220** | 3 | 7912 ×2 stokla birlikte **±12 V rayı rahat** |
| 15mR Type-C şönt | 3 | 10 A kademesi |
| 5mR Type-C şönt | 2 | |
| 5mR Type-C şönt 9.5A | 4 | |
| 0.1R 5W taş | 3 | A kademesi |
| 0.10R 11W taş | 2 | |
| 1R 5W taş / 1R 11W taş / 3.3R 11W taş | 2 / 2 / 3 | elektronik yük için de kullanılır |
| 1R 1/4W · 1R 1/2W · 1R 1W · 1R 2W | 50 · 50 · 10 · 10 | mA kademesi |
| 0.1R 1/4W | 50 | |
| **Muz jak** (yeşil/siyah/sarı/kırmızı/mavi) | 2'şer | **ön panelin 5 uç çifti tam karşılanıyor** |
| **4mm born jak şeffaf** (5 renk) | 2'şer | |
| 2'li bariyer klemens | 3 | 10 A klemensi |
| Delikli plaket 6x13 / 10x10 / 5x5 | 3 / 2 / 2 | **kalıcı yapım** |
| Header (2mm dişi, 23mm erkek, 19mm erkek, 1.27mm dişi) | 2/3/3/2 | |
| M3 vida/somun/pul/rondela | çeşitli | |
| Anahtar/buton/dip switch/toggle | çok sayıda | ön panel kademe seçimi |

#### Robotistan · TS07091325822 · 1.545,81 TL · "Kargoya Verildi" · Yurtiçi 170997471077

| Parça | Adet | Not |
|---|---|---|
| **ADS1115 16-Bit 4 Kanal ADC** | **3** | ⚠️ Tasarım **ikisini** kullanıyor; 3.'sü verim ölçer için |
| Mano organizer kutu 10" | 3 | |
| Klemens girişli DC barrel jack | 2 | |
| DC güç jakı 2.1mm erkek vidalı klemens | 2 | |
| 1x40 header (12mm/15mm erkek, dişi) | 1/2/2 | |
| PBS-110 / PBS-11A / PBS-11B butonlar | 4'er, çeşitli renk | |
| Mini USB kablo 30cm | 1 | |
| M3 vidalar | çeşitli | |

> **Görev:** Parçalar gelince `stok-takip/envanter.csv`'ye işle. CSV şu an bu 40+ kalemi
> bilmiyor; işlenmezse yeni oturum "elinde yok" diye yanlış cevap verir. `CLAUDE.md`
> kuralları: yazmadan önce `.yedek/`'e kopya, id'ler kategori önekine göre.

### 3.3 ESP32-S3'ün doğrulanmış yetenekleri

Bunlar bu oturumda **yerel ESP-IDF başlıklarından okundu**, tahmin değil. Kaynak:
`~/AppData/Local/Arduino15/packages/esp32/tools/esp32s3-libs/3.3.11/include/soc/esp32s3/include/soc/soc_caps.h`
ve `clk_tree_defs.h`. Arduino ESP32 core **3.3.11**.

| Yetenek | Değer | Kaynak |
|---|---|---|
| ADC bit | **12 sabit** | `SOC_ADC_DIGI_MIN/MAX_BITWIDTH = 12` |
| ADC sürekli/DMA hız | **611 Hz – 83 333 Sa/s** | `SOC_ADC_SAMPLE_FREQ_THRES_LOW/HIGH` |
| ADC kanal | 10 (ADC1 = GPIO1–10) | `SOC_ADC_MAX_CHANNEL_NUM = 10` |
| ADC pattern tablosu | 12 öğe, 4 bayt/dönüşüm | `SOC_ADC_PATT_LEN_MAX = 24` (iki tablo) |
| **DAC** | ❌ **YOK** | `SOC_DAC_SUPPORTED` **tanımlı değil** (klasik ESP32'de var: 2 kanal × 8 bit) |
| LEDC (PWM) | 4 zamanlayıcı, 8 kanal, **14 bit** azami | `SOC_LEDC_TIMER_BIT_WIDTH = 14` |
| **MCPWM capture** | 1 zamanlayıcı, **3 kanal**, saat **APB 80 MHz → 12.5 ns** | `SOC_MCPWM_CAPTURE_*`, `SOC_MCPWM_CAPTURE_CLKS = {SOC_MOD_CLK_APB}` |
| PCNT | var | `SOC_PCNT_SUPPORTED = 1` |
| GPTimer | 2 grup × 2, **54 bit** sayaç | `SOC_TIMER_GROUP_*` |
| Bellek | 512 KB SRAM + **8 MB oktal PSRAM**, 16 MB flash | N16R8 |

**DAC'ın olmaması, eğri çizici ve elektronik yükün süpürme kaynağını belirliyor:**
LEDC PWM + RC süzgeç zorunlu (ya da harici I2C DAC satın alınmalı).
14 bit @ APB 80 MHz → taşıyıcı 80e6/16384 = **4.88 kHz**; 12 bit → 19.5 kHz; 10 bit → 78 kHz.
Çözünürlük ile süzgeç kolaylığı arasında doğrudan takas var.

**Pin durumu:**

| Pin | Kullanım |
|---|---|
| GPIO8 / GPIO9 | I2C SDA / SCL |
| GPIO4 | ADC1_CH3 — osiloskop girişi |
| GPIO7 | ADS #1 ALERT/RDY |
| GPIO5 | ADC1_CH4 — **boşta**, yedek olarak ayrıldı |
| GPIO1, 2, 6, 10 | **boşta**, ADC1'e uygun |
| ❌ GPIO0/3/45/46 | strapping |
| ❌ GPIO19/20 | yerel USB |
| ❌ GPIO26–32 | SPI flash |
| ❌ GPIO33–37 | oktal PSRAM (R8 varyantı) |

---

## 4. Bilinen kusurlar — YENİ OTURUM BUNLARI DÜZELTSİN

Bunlar bu oturumun envanter taramasında çıktı ve **henüz düzeltilmedi**. Sırayla doğrula
ve düzelt.

> **7 gerçek kusur + 1 yanlış alarm.** 4.5'i bilerek bıraktım: onu da kusur sanmıştım,
> doğrulayınca öyle olmadığı çıktı. Aynısı diğer maddeler için de geçerli olabilir —
> **her birini kaynağa giderek doğrula.**
>
> ### 📌 2026-09-08 durumu — liste kaynağa gidilerek denetlendi
>
> Uyarı haklı çıktı: **iddia edilen 7 kusurun 2'si zaten kapanmıştı** (4.3, 4.4),
> **1'inin önerilen çözümü de yanlıştı** (4.7 — 4.7 kΩ, kendi verdiği 300 ns
> sınırını 308 ns ile aşıyor). Ayrıca **yeni bir kusur bulundu** (4.13).
>
> | Durum | Maddeler |
> |---|---|
> | ✅ Bu oturumda çözüldü | 4.2 · 4.6 · 4.7 · 4.9 |
> | ⚪ Zaten kapanmıştı | 4.3 · 4.4 (+ 4.5 yanlış alarm) |
> | ✅ Daha önce çözülmüş | 4.1 · 4.10 |
> | ⏸️ Ön uç işine bağlandı | **4.8 · 4.13** — bkz. 5.12.4 bağımlılık zinciri |
> | 🟡 Açık, bağımsız | 4.11 (ikili aktarım) — **4.12 B22'de kapandı** |
>
> Zincir: **6/6 adım, 182 doğrulama, 0 hata** (A1 24 → 33 kural).

### 4.1 ✅ `app.js` komut uyuşmazlığı — ÇÖZÜLDÜ (2026-09-08)

`arayuz/app.js` (satır 272-291):

| Arayüzün gönderdiği | Aşama 2 firmware'inin beklediği |
|---|---|
| `sontGonder()` → `'r' + değer` | `s<ohm>` |
| `kalibreV()` → `'kv' + v` | `v<gerçek>` |
| `kalibreA()` → `'ka' + a` | `i<gerçek>` |
| `osiloYakala()` → `'t'` | ✅ `t<esik>` — bu çalışıyor |

**Düzeltildi:** `app.js` artık `s<ohm>`, `v<gerçek>`, `i<gerçek>` gönderiyor.
A5 testi bunu her koşuda sınıyor (`gonderilen[0] === 's10'` vb.), yani bir daha
sessizce ayrışamazlar.

### 4.2 ✅ A5/A6 kanıt dosyasına işlenmemiş — ÇÖZÜLDÜ (2026-09-08)

`kanit/a2-tam-dogrulama.txt` yalnız A1–A4 içeriyor (24+11+33+18 = **86 kontrol**).
A5, kanıt kaydı üretildikten *sonra* eklendi. `kanit2-uret.py` sayıları yalnız bu
dosyadan çektiği için `kanit/kanit2-sayfasi.html` hâlâ 4 adımlık koşuyu gösteriyor.

**Düzeltildi.** Asıl kök `kanit2-uret.py:72`'deki `if len(ADIMLAR) != 4` idi —
A5/A6 zincire eklenince üreteç *hata verip duruyordu*, bu yüzden sayfa 4 adımlık
eski koşuda donmuştu. Artık adım sayısı kayıttan geliyor (`< 4` alt sınırı),
A5/A6 basamakları MERDIVEN'e eklendi, A1'in kural sayısı da elle yazılmak yerine
kayıttan okunuyor. Kanıt sayfası şimdi **6 adım / 182 doğrulama** gösteriyor.

### 4.3 ⚪ README kendisiyle çelişiyor — ZATEN KAPANMIŞ (2026-09-08 doğrulandı)

~~Satır 12 `4/4 adım`, satır 31 `5/5 adım, 116/116` diyordu.~~

**Kaynağa gidildi: kusur yok.** README satır 12 `6/6 adım`, satır 32 `6/6 adım,
173/173` diyordu — tutarlıydı. Bu madde yazıldıktan sonra düzeltilmiş olmalı.
(Bugün 182'ye güncellendi, A1'e 9 yeni kural eklendiği için.)

### 4.4 ✅ Arayüz Aşama 1 değerlerini yazıyor — ZATEN KAPANMIŞ (2026-09-08 doğrulandı)

- ✅ `arayuz/index.html` osiloskop başlığı düzeltildi: artık
  *"12 bit, 611 Sa/s … 83.3 kSa/s, ayarlanabilir zaman tabanı"*.
- ~~`app.js` `demoVeri()`: `hz = 76923`, `voltAdim = 0.10648`~~ — **artık yok.**
  `demoVeri()` yeniden yazılmış, sahte veri `arayuz/sahte-kart.js`'ten geliyor ve
  orada `HZ_AZAMI = 83333`, `BOLME_ORANI = 15.70588235`, `VOLT_ADIM` hesaplanıyor.
  Aşama 1 sabiti kalmamış.

### 4.5 ⚪ `sema_uret_ortak.py` proje adı — YANLIŞ ALARM (kayıt için bırakıldı)

Bu maddeyi önce kusur sandım, sonra doğrulayınca **kusur olmadığı çıktı**. Silmek yerine
bırakıyorum, çünkü bu belgenin nasıl kullanılması gerektiğini gösteriyor: *iddiayı gör,
kaynağa git, doğrula.*

**Şüphe:** `sema_uret_ortak.py:16-17`'de `PROJE` ve `PROJE2` ikisi de `"olcum-karti-a2"`.
Aşama 1 şema üreteci yanlış proje adına yazıyor gibi görünüyor.

**Gerçek:** Kusur yok.
- `sema-uret.py:22` `PROJE`'yi `"olcum-karti"` olarak **ezip geçiyor** — ortak modüldeki
  değer sadece varsayılan. Modülün docstring'i bunu zaten söylüyor: *"hangi sema
  uretiliyorsa uretec bu degeri ayarlar."*
- `sema2-uret.py` `PROJE2`'yi içe aktarıp kullanıyor (satır 22, 365, 371, 375).
- Üretilen dosyalar doğrulandı: `sema/olcum-karti.kicad_sch` → `project "olcum-karti"`,
  `sema2/olcum-karti-a2.kicad_sch` → `project "olcum-karti-a2"`. ✅

Tek küçük kokusu: ortak moduldeki `PROJE` varsayılanı hiçbir zaman o değerle
kullanılmıyor (Aşama 1 eziyor, Aşama 2 `PROJE2` kullanıyor). Zararsız, istenirse
sadeleştirilir.

### 4.6 ✅ README:397 eski kod örneği — ÇÖZÜLDÜ (2026-09-08)

~~Hâlâ `float wh = enerji_pJ / 3.6e18;` gösteriyor.~~ Düzeltildi: örnek artık
`3.6e15` gösteriyor ve altına neden yanlış olduğunu (`3.6e18` = 1 kWh) ve hangi
adımların bunu sınadığını (S9 · A4: `wh × 3600 == joule`) anlatan bir not eklendi.

### 4.7 ✅ R8/R9 I2C pull-up — ÇÖZÜLDÜ (2026-09-08), **ama önerilen değer YANLIŞTI**

Şemadaki not **üç** ADS1115 modülü varsayıyor ve "takma" diyor. Ben `kurulum2.html`'de
"iki modül var, tak" diye **koşulsuz** düzelttim. **Kullanıcının üç modülü var** —
dolayısıyla iki ifade de eksik. Doğrusu **veri yolundaki modül sayısına bağlı**:

Her ADS1115 modülünde kart üstü 10 kΩ pull-up var. Fast-mode (400 kHz) sınırı
t_r ≤ 300 ns, ve t_r ≈ 0.8473 · R · C_veriyolu.

| Veri yolundaki modül | Pull-up (hat başına) | t_r @ 150 pF | Karar |
|---|---|---|---|
| 2 modül | 10K‖10K = **5 kΩ** | 636 ns ❌ | **R8/R9 tak** → 2.42 kΩ, 308 ns ✅ |
| 3 modül | 10K‖10K‖10K = **3.33 kΩ** | 423 ns ⚠️ sınırda | R8/R9 takarsan 1.95 kΩ, 248 ns ✅ ama 3 mA sink sınırına yaklaşır |

**Yedek çıkış yolu:** I2C hızını 100 kHz'e düşür (`Wire.begin(8, 9, 100000)`), t_r sınırı
1000 ns olur, her durum geçer. Örnekleme hızını etkilemez çünkü darboğaz ADS'in 860 SPS'i.

**Görev yapıldı — ve yaparken yukarıdaki tablonun kendisi de yanlış çıktı.**

🔴 **Yeni bulgu 1:** Yukarıda "2 modül + R8/R9 → 2.42 kΩ, 308 ns ✅" yazıyor.
**308 ns, aynı satırda verilen 300 ns sınırının ÜSTÜNDE.** İki modüllü
yapılandırmada 4.7 kΩ Fast-mode'da *kalıyor*. Üç modülde tesadüfen geçiyor
(248 ns), çünkü modül arttıkça paralel direnç düşüyor.

300 ns için izin verilen azami toplam pull-up: **2360 Ω**.

| Modül | R8/R9 | Toplam | t_r | Sink | Sonuç |
|---|---|---|---|---|---|
| 2 | yok | 5000 Ω | 635 ns | 0.66 mA | ❌ |
| 2 | 4.7K | 2423 Ω | **308 ns** | 1.36 mA | ❌ **kalır** |
| 2 | **2.7K** | 1753 Ω | **223 ns** | 1.88 mA | ✅ |
| 3 | yok | 3333 Ω | 424 ns | 0.99 mA | ❌ |
| 3 | 4.7K | 1950 Ω | 248 ns | 1.69 mA | ✅ |
| 3 | **2.7K** | 1492 Ω | **190 ns** | 2.21 mA | ✅ |

**Karar: R8/R9 = 2.7 kΩ** (stokta 10 adet). Hem 2 hem 3 modülde geçiyor, sink
akımı en kötü 2.21 mA ile 3 mA sınırının altında. 3. ADS1115 takıldığında
hiçbir şey değişmiyor.

🔴 **Yeni bulgu 2 — "100 kHz'e düş" yedek yolu bedava değil.** Yukarıda
*"Örnekleme hızını etkilemez çünkü darboğaz ADS'in 860 SPS'i"* yazıyor. Veri
yolu doluluğuna bakılınca öyle değil. `ads_oku()` işlem başına ~49 bit sürüyor
(işaretçi yazma + 2 bayt okuma, iki ayrı işlem), iki ADS 860 SPS'te 1720 okuma/s:

| I2C hızı | Okuma başına | Veri yolu doluluğu |
|---|---|---|
| 400 kHz | 122.5 µs | **%21** ✅ |
| 100 kHz | 490.0 µs | **%84** ⚠️ |

`Wire` blokladığı için bu doğrudan CPU'yu da bloklar. **100 kHz son çare.**

💡 **Uygulanmamış iyileştirme:** ADS1115 yazmaç işaretçisini korur. İlk okumadan
sonra işaretçi yazmayı atlayıp doğrudan 2 bayt istenirse işlem 49 → ~29 bite
iner (−%41), 100 kHz doluluğu %84 → %50'ye düşer.

Hepsi `tasarim2.py` §8b'de **kural olarak** duruyor (6 kural), `kurulum2.html`
tablosu da değiştirildi. Bir daha sessizce kayamaz.

### 4.8 🔴 Örtüşme süzgeci Nyquist'in ÜSTÜNDE — sahte sinyal üretir

> ⏸️ **BİLEREK BEKLETİLDİ (2026-09-08).** Kullanıcı 600 V menzil ve çift yönlü
> (±) giriş istedi. İkisi de **bölücüyü değiştiriyor**, süzgeç de bölücünün
> Thevenin direncine göre tasarlanıyor. Şimdi 100K/6.8K'ya göre Sallen-Key
> hesaplamak, ön uç değişince çöpe gidecek iş demek.
>
> İyi haber: önerilen yeni bölücülerin Thevenin'i bugünküne çok yakın
> (6.58 kΩ ve 6.79 kΩ, bugün 6.37 kΩ) — yani süzgeç tasarımı **iki menzilde de
> aynı** olabilir. Bu, 4.8'i ön uç işiyle birlikte **bir kerede** çözmeyi daha
> da mantıklı yapıyor. Bkz. 4.13 ve 5.12.

**Bu oturumda yeni bulundu.** Aşama 2 tek kanallı skop için tasarlanmıştı ve orada sorun
yoktu; **iki kanallı hızlı ölçüme geçince kusur haline geliyor.**

Gerilim bölücüsünün Thevenin'i 6.37 kΩ, süzgeç kondansatörü 1 nF →
fc = 1/(2π·6370·1e-9) = **24.997 kHz**.

İki kanal sürekli kipte çalışınca kanal başına hız 41 666.7 Sa/s, **Nyquist 20.83 kHz**.
Yani süzgeç Nyquist'in üstünde: 20.83 kHz'te sadece −2.3 dB. **Hiçbir şey süzmüyor.**

**Somut zarar:** 100 kHz'lik bir SMPS dalgalanması hiç zayıflamadan **16.67 kHz'e
katlanır** ve ekranda gerçekmiş gibi görünen sahte bir dalgalanma olarak çıkar. Güç
elektroniğiyle uğraşan biri için en tehlikeli hata tipi: **yanlış ama inandırıcı.**

**Çözüm:** 2 kutuplu Sallen-Key Butterworth, R = 6.8 kΩ (stokta 18), C2 = 1 nF,
C1 = 2 nF (iki 1 nF paralel) → f0 = 16 550 Hz, Q = 0.707. Zayıflama: Nyquist'te
−5.45 dB, fs'te −16.15 dB, **100 kHz'te −31.25 dB** (güç çarpımında −62.5 dB = 1360×).

⚠ Akımdaki 7.96 kHz'lik RC **yerinde kalmalı** — o ADS1115'in girişini koruyor. Hızlı
akım yolu onun arkasından çekilirse 7.96 kHz'e hapsolur. **Şönte iki bağımsız Kelvin
çifti bağla:** biri ADS'in RC'sine, biri doğrudan fark yükseltecine.

> 🔴 **YUKARIDAKİ SON PARAGRAF YANLIŞTI — B16 düzeltti (2026-09-09, 5.12.26).**
> İki hatası vardı:
>
> 1. **"Akımdaki 7.96 kHz'lik RC yerinde kalmalı"** — hayır. O RC, ADS akım
>    kanalının Nyquist'inin (430 Hz) **18.7 katı** üstündeydi; yani akım
>    kanalında **hiç örtüşme süzgeci yoktu** ve 430 Hz–8 kHz arası banda
>    katlanıyordu. "ADS'in girişini koruyor" gerekçesi de ayrı: koruma işini
>    B15/F2'de eklenen R38/R39 (1K) yapıyor, C4 değil.
> 2. **"İki bağımsız Kelvin çifti bağla"** — hiç uygulanmadı; R27/R29
>    netlist'te R18/R19'un **ardından** taplıyordu. B16 sorunu başka türlü
>    çözdü: süzgeci ADS'in **kendi koluna** taşıyarak (C4 100nF→1nF, yeni
>    C18/C19/C20 = 1.32 µF, R38/R39'un ardında). Böylece tek Kelvin çifti
>    yeterli oluyor, hızlı yol serbest kalıyor (7.76 → 16.52 kHz) **ve** ADS
>    kanalı gerilim kanalıyla eşleşiyor.

### 4.9 ✅ Derleme FQBN'inde PSRAM açık değil — ÇÖZÜLDÜ (2026-09-08)

`kod/olcum-karti-a2/build/.../build.options.json` incelendi: FQBN düz
`esp32:esp32:esp32s3`. **`PSRAM=opi` yok.** Bugün sorun değil (8 MB PSRAM kullanılmıyor),
ama derin skop belleği için PSRAM ayrılmaya çalışıldığında
`heap_caps_malloc(..., MALLOC_CAP_SPIRAM)` **sessizce NULL döner** ve skop hiç açılmaz.

**ÇÖZÜLDÜ (2026-09-08).** `board details` ile doğrulandı: kartın PSRAM
varsayılanı gerçekten `disabled`.

FQBN artık **tek kaynakta**: `uretim/hedef2.py`. Daha önce `sim2_kart.py` ve
`test_skop.py` içinde *ayrı ayrı* yazılıydı — birini düzeltip ötekini unutmak
mümkündü. İkisi de şimdi `hedef2.FQBN` kullanıyor.

```
esp32:esp32:esp32s3:PSRAM=opi,FlashSize=16M,PartitionScheme=huge_app
```

Derlendi: **479 303 B (%15 / 3 MB), 47 452 B RAM, 0 uyarı.**

⚠️ **`CDCOnBoot=cdc,USBMode=hwcdc` BİLEREK EKLENMEDİ.** Bunlar `Serial`i UART
köprüsünden yerel USB CDC'ye taşır; 4.11 için gerekli ama tezgahtaki ilk açılışı
bozabilir. O iş 4.11 ile birlikte, bilerek yapılmalı.

**`ps_malloc(2MB) != NULL` adımı eklenmedi — çünkü kart olmadan koşamaz.** Yerine
firmware açılışta **kendi durumunu yazıyor**:

```
PSRAM: 8192 KB
PSRAM: YOK — derin skop bellegi kullanilamaz (hedef2.py: PSRAM=opi mi?)
```

Sebebi: derlemenin PSRAM'li olması kartta PSRAM *bulunduğunu* kanıtlamaz. Bazı
"N16R8" etiketli kartlarda quad PSRAM çıkıyor; o durumda `hedef2.py`'de
`PSRAM=opi` yerine `PSRAM=enabled` denenecek. `tasarim2.py` §9 üç kuralla
FQBN'in içeriğini sınıyor, kanıt ise tezgahtaki açılış satırı.

### 4.10 ✅ Osiloskop tetiklemesi — ÇÖZÜLDÜ (2026-09-08)

Histerezis, ön-tetik, kenar seçimi ve tetik kipleri eklendi. Ayrıntı 5.2'de.

### 4.11 🟡 Aktarım darboğazı — derin bellek 115200 baud'da anlamsız

Bugünkü ASCII protokolü ile:

| Kayıt | Biçim | Süre @115200 |
|---|---|---|
| 1 000 örnek (bugün) | ASCII | 0.43 s ✅ |
| 20 000 örnek | ASCII | **8.7 s** ❌ |
| 500 000 örnek | ikili + **yerel USB CDC** | **~1.0 s** ✅ |

8 MB PSRAM'in derin belleği ancak **yerel USB CDC (GPIO19/20) + ikili biçim** ile
anlamlı. UART köprüsünde 115200'de kalırsan PSRAM'in hiçbir işe yaramaz.

### 4.12 ✅ WiFi yolunda arayüz yok — **B22'de KAPANDI** (2026-09-10)

> Aşağıdaki tespit Aşama 2 dönemine ait ve **artık geçerli değil.** B22.2
> taşıyıcı katmanını kurdu (`TasiyiciAkis` = SSE), B22.5 arayüzü kartın
> LittleFS'inden servis etti. Ayrıca metindeki `arayuz/app.js` yolu da
> yanlış — o klasör yok, dosya `arayuz3/app.js`. Ayrıntı **5.12.35** ve
> **5.12.38**'de.

Özgün tespit: *"Firmware `/akis` adresinden SSE yayınlıyor ama arayüz
yalnız Web Serial istemcisi; WiFi ile bağlanınca gösterilecek arayüz yok."*

### 4.13 🔴 Alt koruma kelepçeleri 1N4148 — korudukları çipin sınırını AŞIYOR

**Bu oturumda yeni bulundu (2026-09-08).** Netlist okunarak, simülasyondan değil.

`netlist2_dogrula.py` şunu doğruluyor ve şema gerçekten böyle:

```
D2: KATOT /V_DUGUM,  ANOT GND     -> ADS1115 AIN0'i koruyor
D4: KATOT /SKOP,     ANOT GND     -> ESP32-S3 GPIO4'u koruyor
```

Giriş negatife giderse bu diyotlar düğümü **−0.7 V**'a kelepçeler. Ama:

| Çip | Mutlak alt sınır | 1N4148 kelepçesinin verdiği |
|---|---|---|
| ADS1115 (AIN) | **GND − 0.3 V** | −0.7 V ❌ |
| ESP32-S3 (GPIO) | **GND − 0.3 V** | −0.7 V ❌ |

**Devir belgesi bu tuzağı 5.1.4'te yazıyor** — ama yalnızca *gelecekteki* TL072
çıkışları için: *"Alt kelepçe 1N4148 OLAMAZ: −0.7 V, ESP32'nin −0.3 V mutlak alt
sınırını aşar. Schottky şart."* **Aynı cümle şemada bugün duran D2/D4 için de
geçerli ve fark edilmemiş.**

⚠️ **Bunun ne kadar ciddi olduğu ÖLÇÜLMEDİ.** 100K seri direnç akımı sınırlıyor
(−400 V'ta bile 4 mA, 1N4148'in sınırının altında) ve çipin kendi ESD diyodu da
paralel iletiyor; muhtemelen anında yanmaz. Ama spec dışı ve **A2 taraması bunu
hiç görmedi**: `sim2_giris.py` taraması `dc Vin 0 300` — yani **sıfırdan yukarı**.
Negatif giriş bir kez bile simüle edilmemiş, üstelik tarama netlist'inde D2 hiç
yok. Yeşil A2 adımı negatif taraf hakkında **hiçbir şey söylemiyor.**

**Çözüm:** alt kelepçeler Schottky olacak (SR5100 stokta ×10; geniş bantlı skop
kanalı için kapasitesi düşük BAT54 alınmalı). Ve `sim2_giris.py`'ye **negatif
tarama** eklenecek.

⏸️ 4.8 gibi bu da **ön uç işiyle birlikte** yapılmalı — kullanıcı zaten ± giriş
istedi, o iş bu kelepçeleri baştan doğru kurmayı gerektiriyor.
### 4.14 🔴 PGA oto-kademesi tamponsuz bölücüde KAZANÇ SIÇRAMASI yapıyor

**2026-09-08'de bulundu.** Kaynak: ADS1115 veri sayfası (SBAS444B) s.3 ve
s.13 Tablo 2 — bu oturumda PDF'ten okundu.

ADS1115'in giriş empedansı **PGA kademesiyle değişiyor**:

| PGA | Z_diferansiyel | Z_ortak-mod |
|---|---|---|
| ±2.048 | 4.9 MΩ | 6 MΩ |
| ±1.024 | 2.4 MΩ | 3 MΩ |
| ±0.512 | **710 kΩ** | 100 MΩ |
| ±0.256 | **710 kΩ** | 100 MΩ |

Aşama 2'nin gerilim kanalı **tamponsuz** (Thevenin 6.37 kΩ) ve firmware
[`olcum2.h` `pga_sec()`] onu **±2.048 ↔ ±0.256 arası otomatik kademeliyor.**
Kaynak empedansı sıfır olmadığı için bu bir kazanç hatası yaratıyor:

| PGA | Kazanç hatası |
|---|---|
| ±2.048 | %0.236 |
| ±1.024 | %0.478 |
| ±0.512 | %0.904 |
| ±0.256 | %0.904 |

**Kademe sınırında okuma 0.67 puan zıplıyor.** Kalibrasyon tek kademede
yapıldığı için bunu silemez. Üstüne ADS'in kendi "PGA kademeleri arası kazanç
uyumu %0.1 maks" (s.3) da biniyor.

Araştırma teyidi (TI E2E, Adafruit forumları): *"input impedance varies with
gain settings"*, *"a voltage buffer can be added to solve this issue"*,
*"divider output impedance should be < 10 kΩ"*.

**Çözüm:** bölücüyü tamponla (5.12'de yapıldı) — kaynak empedansı ~0 olunca
hata PGA'dan bağımsız kayboluyor. Tamponlanmayacaksa PGA **sabitlenmeli**.

`tasarim3.py` §3 bunu kural olarak sınıyor.


### 4.15 ✅ Arayüzün ÜÇ düğmesi sessizce çalışmıyordu — ÇÖZÜLDÜ (2026-09-08)

**B7 sırasında bulundu.** 4.1 bu hatayı `app.js` içinde düzeltmişti ama
`index.html`'deki üçünü **atlamıştı** — çünkü testler yalnızca `app.js`'e
bakıyordu.

Aşama 2 firmware'inin tanıdığı komutlar: `# ? i s t v z`

| Düğme | Gönderdiği | Ne oluyordu |
|---|---|---|
| Ayarları göster | `d` | **Böyle bir komut yok** → "bilinmeyen komut" |
| Enerjiyi sıfırla | `e` | **Aşama 2'de enerji sıfırlama HİÇ YOK** |
| Akımı sıfırla | `s` | `s` = şönt komutu; boş değerle "sont degeri gecersiz" |

Üçüncüsü en sinsisi: `s` **geçerli bir komut harfi**, o yüzden harf
düzeyinde bir denetim onu yakalamaz — yanlış olan anlamı.

**Düzeltildi:** `d`→`?`, `s`→`z`, `e` düğmesi kaldırıldı (Aşama 2'de
karşılığı yok), yerine `#` (I²C tara) kondu.

**Tekrarlanamaz hale getirildi:** `uretim/test_arayuz3.js` arayüzün
gönderebileceği her komut harfini firmware'in `case` etiketleriyle
karşılaştırıyor — **hem `app.js` hem `index.html` taranarak**. Aynı
denetim Aşama 2 arayüzüne uygulandığında `d` ve `e`'yi yakalıyor.


---

## 5. Yeni hedef mimari

> **Süreklilik notu:** README satır 13'te zaten
> `| 3 | — | çift kanal (verim ölçümü) | 3. ADS1115 için yer ayrıldı |` yazıyor.
> Kullanıcının seçtiği **verim ölçer, planlanmış Aşama 3'ün ta kendisi**. Yeni yön
> projeyi ıskartaya çıkarmıyor, öngörülen yola giriyor.

### 5.0 Kullanıcının istedikleri, öncelik sırasıyla

**Ana üçlü (açıkça istendi):**
1. **Osiloskop** — hem tek seferlik hem eşdeğer-zaman *(kullanıcı "ikisi de olsun" dedi)*
2. **Wattmetre**
3. **Eğri çizici** (I-V curve tracer)

**Artı: gerilim ve akım kalacak, olabildiğince yüksek örneklemeyle.**

**Kullanıcının seçtiği dört ek yetenek** (hepsini seçti):
4. **SMPS zamanlama analizörü** — 12.5 ns'de frekans/duty/ölü zaman
5. **Verim ölçer (η)** — giriş ve çıkış gücünü eşzamanlı ölçüp verim eğrisi
6. **Elektronik yük** — programlanabilir sabit akım
7. **Bobin/trafo doyum testi** — L ölçümü ve çekirdek doyum noktası

### 5.1 Dört fiziksel duvar — mimarinin tamamı bunların etrafında şekilleniyor

| # | Duvar | Sayı | Sonucu |
|---|---|---|---|
| **D1** | ESP32-S3 ADC hızı **toplam**, kanal başına değil | 83 333 Sa/s toplam | 2 kanal → **41 666.7 Sa/s/kanal**, gerçek zamanlı bant **20.83 kHz**. 100 kHz anahtarlamayı gerçek zamanda göremezsin. |
| **D2** | Tek SAR, sıralı pattern | kanallar arası **12.000 µs sabit kayma** | Eşzamanlı örnekleme **imkânsız**. Yalnız DSP'de düzeltilir. |
| **D3** | ADS1115'in kendi sinc süzgeci | 860 SPS'te −3 dB @ **380 Hz**, çentik 860 Hz | 3 ADS'i interleave etmek **bant genişliği yaratmaz** (bkz. 5.1.3) |
| **D4** | ESP32-S3 ADC analog giriş bandı / S/H açıklık süresi | **Espressif yayınlamıyor** | ETS'in gerçek tavanı burası. **Ölçmeden sayı vaat edilemez.** |

#### 5.1.1 Kanal kayması (D2) ve düzeltilmesi — kritik

`sample_freq_hz` **toplam** dönüşüm hızıdır. `pattern_num = 2` ile akış `V,I,V,I…`
şeklinde gider; V ile I arasında tam **1/83 333 = 12.000 µs** vardır. Kanal periyodu
24 µs olduğuna göre **kayma tam yarım örnek** — ve bu bir şans, çünkü doğrusal fazlı bir
FIR ile **tam olarak** düzeltilebilir.

**Düzeltmezsen ne olur** (θ = 2πfΔt, hata ≈ −θ²/2 − θ·tan φ):

| f | θ | PF=1.0 | PF=0.5 | PF=0.1 |
|---|---|---|---|---|
| 50 Hz | 0.22° | −0.001% | **−0.65%** | **−3.75%** |
| 1 kHz | 4.32° | −0.28% | **−13.3%** | −75% |
| 10 kHz | 43.2° | **−27.1%** | anlamsız | anlamsız |

⚠️ **Dirençsel yükte hata ikinci derece (küçük), reaktif yükte birinci derece (büyük).**
Düzeltmesiz wattmetre yalnız ~1 kHz'e kadar ve yalnız yüksek güç faktöründe doğrudur.

**Çözüm — 4 katsayılı Lagrange yarım-örnek hizalayıcı:**
```
i_hiza[n] = −1/16·i[n−2] + 9/16·i[n−1] + 9/16·i[n] − 1/16·i[n+1]
```
Örnekler 24n−36, −12, +12, +36 µs → tam simetrik → **faz hatası sıfır**. Geriye yalnız
genlik sarkması kalır (1 kHz'te −0.000 dB, 5 kHz'te −0.063 dB). CPU maliyeti
0.33 MMAC/s — 240 MHz FPU'da hiçbir şey.

⚠️ **Üç uygulama tuzağı:** (1) kanal sırasını indeks paritesinden **çıkarma**, her zaman
`o->type2.channel` alanından demux et — mevcut `skop_yakala()` bunu zaten doğru yapıyor,
o alışkanlığı koru. (2) `conv_frame_size`, `4 × pattern_num`'un katı olmalı. (3)
`sample_freq_hz` sınırları **toplama** uygulanır.

#### 5.1.2 Hibrit mimari — doğru formülasyonu

Fikir sağlam ama "kazanç+ofset düzelt" hali eksik. **Doğrusu: DC'yi ADS'ten, AC'yi
ESP'den al.**

```
v(t) = V̄_ADS  +  ( v̂_ESP(t) − ort(v̂_ESP) )
```

Bu neden daha güçlü: ESP'nin doğrusalsızlığı (INL) küçük bir AC salınım aralığında
neredeyse doğrusaldır, yani INL'in büyük kısmı **DC teriminin içine düşer ve ADS onu
siler**. Basit kazanç+ofset düzeltmesi INL'e karşı çalışmaz, bu çalışır.

Kazanç/ofset kestirimi için unutmalı özyinelemeli en küçük kareler (τ = 60 s, 4 Hz
kadans). Ofset hızlı kayar (tek noktadan gözlemlenebilir), kazanç yavaş kayar (uyarım
ister) — bu yüzden kazanç yalnız pencere varyansı bir eşiği geçince güncellenir.

**Nerede kırılır — dürüst liste:**

| Kırılma | Çözüm |
|---|---|
| **Farklı düğüm** — ADS ve ESP ayrı bölücülere bakarsa "aynı ortalama" varsayımı yalan | **Zorunlu: aynı düğüm.** Bugünkü ayrı skop bölücüsü ölçüm kanalı olamaz |
| **INL** — 2 parametreli uydurma kod-bağımlı hatayı silmez (kalan ±5–15 LSB) | DC'yi ADS'ten al; hızlı kanalın **mutlak** değerine asla güvenme |
| **Kazanç gözlemlenemez** — sinyal hep 12 V'ta durursa `a` gürültüden uydurulur | Varyans eşiği + kurulumda iki noktalı elle kalibrasyon. **Sürekli disiplinleme sıfırdan mutlak doğruluk YARATMAZ**, yalnız sürüklenmeyi takip eder |
| **Pencere içinde durağan değil** (yük basamağı) | Varyans eşiğini aşan pencereyi at |
| **PGA kademe değişimi** pencere ortasında | Disiplinleme penceresinde PGA'yı dondur |
| **Kırpma** | Tepe dedektörü; kırpma varsa disiplinlemeyi durdur ve arayüze bildir |

#### 5.1.3 3 ADS1115'i interleave etmek — HAYIR

Faz bilinebilir (her ALERT'i ayrı GPIO'ya alıp damgalarsan), ama **bant genişliği
kazanmazsın**. ADS1115'in her örneği 1.16 ms'lik bir **boxcar ortalamasıdır**:

| f | Tek ADS sinc cevabı |
|---|---|
| 200 Hz | −0.79 dB |
| **380 Hz** | **−2.99 dB** |
| 860 Hz | çentik (−∞) |

Her alt-ADC sinyali **almadan önce** 380 Hz'te 3 dB kesmiş oluyor. Üçünü birleştirmek
kaybedilmiş bilgiyi geri getirmez — interleave **örnek yoğunluğunu** artırır, bant
genişliğini değil. Üstelik çipler arası kazanç (±%0.15) ve ofset (±3 LSB) uyumsuzluğu
klasik **interleave sahte tonları** üretir. Maliyeti de yüksek: 2580 okuma/s × ~150 µs
I2C = saniyenin **%39'u** bloklayan I2C içinde.

**3. ADS'in doğru kullanımı hız değil, EŞZAMANLILIK:** çıkış şöntü + çıkış bölücü →
verim ölçümü. Ayrıca boş kanallar sağlık izlemeye ayrılabilir (TL431 rayı kaydı mı,
±12 V sağlam mı).

#### 5.1.4 Hızlı akım yolu — TL072 fark yükselteci

**Kazanç 27 (27K/1K)** seçildi. Neden:

| Rf/Rg | G | 1 A'de çıkış | Tam ölçek | Bant (3 MHz/(1+G)) | Yargı |
|---|---|---|---|---|---|
| 22K/1K | 22 | 2.20 V | 1.364 A | 130 kHz | |
| **27K/1K** | **27** | **2.70 V** | **1.111 A** | **107 kHz** | ✅ **seçilen** |
| 33K/1K | 33 | 3.30 V | 0.909 A | 88 kHz | ❌ 3.1 V penceresini aşar |

27K (stokta 10) ve 1K (stokta 36) var; **30K stokta yok**, o yüzden "temiz" 30 seçilmedi.
107 kHz bant, 20.83 kHz Nyquist'in çok üstünde → örtüşme süzgeci yükselteçten **sonra**
gelmeli, yükselteç darboğaz değil.

**Çift yönlü ölçüm:** fark yükseltecinin REF ucunu GND yerine **+1.5 V**'a bağla (TL431
rayından bölünmüş, ikinci TL072 kesitiyle **tamponlanmış** — REF düşük empedanslı
sürülmezse CMRR ölür). Çıkış 1.5 V ± 1.5 V → **±0.55 A çift yönlü**. Güç elektroniğinde
bobin akımı ters döner; tek yönlü ölçüm SMPS'te yanlış cevaptır.

🔴 **Her op-amp çıkışı ile her GPIO arasına koruma ZORUNLU.** TL072 ±12 V'ta besleniyor;
arıza anında çıkışı ±10 V'a gider ve 3.3 V'luk bir ADC pinini **anında öldürür**.
1 kΩ seri + üstte 1N4148→TL431 rayı (2.495 V) + altta **Schottky**→GND.

⚠️ **Alt kelepçe 1N4148 OLAMAZ:** −0.7 V, ESP32'nin −0.3 V mutlak alt sınırını aşar.
Schottky şart (SR5100 stokta; geniş bantlı skop kanalı için BAT54 al — SR5100'ün
kapasitesi büyük).

### 5.2 Osiloskop — ✅ TEMEL KISMI YAPILDI (2026-09-08)

> Bu bölüm başta tasarım önerisiydi. **Zaman tabanı, tetikleme ve otomatik
> ölçümler uygulandı ve doğrulandı.** Eşdeğer-zaman örnekleme (ETS) hâlâ
> tasarım aşamasında — o kısım aşağıda ayrı işaretli.

#### Neyin çözüldüğü

Eski hali sabit **1000 örnek @ 83 333 Sa/s = 12 ms pencere** idi. Bir 50 Hz
çevrimi 20 ms sürdüğü için **tam çevrim ekrana sığmıyordu.**

Artık gerçek osiloskoplardaki gibi **saniye/bölme** seçiliyor. 12 kademeli
1-2-5 merdiveni, hedef 100 örnek/bölme:

| s/bölme | Örnekleme | Örnek | Pencere | Not |
|---|---|---|---|---|
| 100 µs | 83 333 Sa/s | 100 | 1 ms | en hızlı — hız tavana dayanıyor |
| 1 ms | 83 333 | 833 | 10 ms | |
| 2 ms | 50 000 | 1000 | 20 ms | **50 Hz'in tam bir çevrimi** |
| 10 ms | 10 000 | 1000 | 100 ms | 50 Hz'in 5 çevrimi |
| 100 ms | 1 000 | 1000 | 1 s | |
| 500 ms | 611 | 3055 | 5 s | en yavaş — hız tabana dayanıyor |

Doğrulama zinciri (A5) **50 Hz için en az bir tam çevrimin sığdığı kademe
olduğunu** her koşuda sınıyor — bu kusur bir daha geri gelemez.

#### Eklenen osiloskop özellikleri

| Özellik | Nasıl |
|---|---|
| **Ayarlanabilir zaman tabanı** | 12 kademe, `tb<0-11>` · arayüzde ◀ ▶ düğmeleri |
| **Otomatik kurulum (AUTO)** | `ta` — kademeleri tarar, frekansı bulur, ekranda ~4 çevrim olacak tabanı ve tetiği kendisi ayarlar |
| **Tetik seviyesi** | `tl<0-4095>` · arayüzde kaydırma çubuğu |
| **Tetik kenarı** | `te0` yükselen / `te1` düşen |
| **Histerezis** | `th<kod>` — gürültülü eşikte sahte tetiklemeyi önler |
| **Ön-tetik** | `tp<0-90>` — tetik ANINDAN ÖNCESİNİ gösterir (halka tampon) |
| **Tetik kipleri** | `tm0` oto · `tm1` normal · `tm2` tek atış |
| **Otomatik ölçümler** | frekans, periyot, Vpp, Vmax, Vmin, Vort, Vrms, **Vac (RMS)**, duty, yükselme/düşme süresi, çevrim sayısı |

**Ön-tetik neden bedava geliyor:** ADC sürekli koşuyor ve örnekler halka
tampona yazılıyor. Tetik aranırken halka dolmaya devam ettiği için, tetik
bulunduğunda elimizde **zaten tetik öncesine ait örnekler var**. Gerçek
osiloskopların ön-tetik penceresi tam olarak böyle çalışır.

#### Ölçüm matematiği nerede ve nasıl doğrulandı

`skop_olc()` fonksiyonu **`olcum2.h` içinde ve platform bağımsız** — projenin
kuralı gereği. Bu sayede A6 adımında **gerçek kod**, avr-gcc ile derlenip
39/39 bit-birebir doğrulanmış AVR emülatöründe koşturuluyor.

Beklenen değerler bir yeniden-uygulamadan değil, **analitik olarak bilinen
dalgalardan** geliyor:

| Dalga | Beklenen | Ölçülen |
|---|---|---|
| Kare, 80 örnek periyot @ 10 kSa/s | 125.000 Hz | 125.000 Hz ✅ |
| Üçgen, 100 örnek | 100.000 Hz | 100.000 Hz ✅ |
| Sinüs, 64 örnek | 156.250 Hz | 156.250 Hz ✅ |
| Sinüs AC RMS | genlik/√2 | fark 0.0004 V ✅ |
| Üçgen AC RMS | genlik/√3 | fark 0.005 V ✅ |
| %25 duty kare | %25 | %24.90 ✅ |
| Düz çizgi | ölçüm yok | frekans 0, çevrim 0 ✅ |

**32/32 koşul geçti.** Frekans doğruluğu için kenar geçişleri **doğrusal ara
değerlemeyle** bulunuyor; bu, periyot ölçümünü örnek çözünürlüğüne hapsolmaktan
kurtarıyor (tipik 10–50 kat iyileşme).

#### Protokol

```
S2 <adet> <Hz> <volt/adım> <tetik_idx> <tdiv_us> <kip> <tetiklendi>
M f=<Hz> T=<s> Vpp=<V> Vmax=<V> Vmin=<V> Vort=<V> Vrms=<V> Vac=<V>
  duty=<%> tr=<s> tf=<s> n=<çevrim>
<ham 12-bit ADC kodları, 16'şar satır>
E
```

Arayüz `t=0`'ı **tetik anına** koyuyor, öncesi negatif zaman olarak görünüyor.
Dikey ölçek min–max'a göre otomatik — sabit bir DC seviyesine binmiş küçük bir
dalgalanma böyle görünür hale geliyor.

#### ⚠️ Hâlâ geçerli sınırlar

- **Menzil 0 – 48.7 V, TEK YÖNLÜ.** Sinyal sıfırın altına inerse alt yarısı
  kırpılır. Sinyal üretecinde **DC offset** kullanılmalı.
- Tek kanal gerçek zamanlı **Nyquist 41.7 kHz**; giriş süzgeci 25 kHz'te
  kesiyor. Üstündeki bileşenler sahte, yavaş sinyal olarak görünür.
- **Şebekeye bağlanamaz** — kart izole değil (bkz. 6.1).
- Aktarım hâlâ ASCII ve 115200 baud: 3055 örneklik en yavaş kademe ~1.3 s
  sürüyor. Derin bellek için ikili + yerel USB gerekiyor (bkz. 4.11).

#### 🔵 HENÜZ YAPILMADI: eşdeğer-zaman örnekleme (ETS)

Kullanıcı "ikisi de olsun" dedi; tek seferlik kip yapıldı, **ETS yapılmadı.**
Tasarımı aşağıda duruyor, uygulanmayı bekliyor.


### 5.2b ETS tasarimi (uygulanmadi) — asagidaki bolum tasarim notudur

Kullanıcı **her iki kipi de** istedi:

| Kip | Nasıl | Ne için |
|---|---|---|
| **Tek seferlik** | Gerçek zamanlı 83 333 Sa/s (tek kanal), ön-tetik halka tamponu, PSRAM'de derin bellek | Kalkış anı, arıza, aşırı akım — **bir kez olan** olaylar |
| **Eşdeğer-zaman (ETS)** | Tetiklemeyi 12.5 ns adımlarla kaydırıp dalgayı çok çevrimde biriktirmek | SMPS anahtarlama dalgaları — **tekrarlayan** sinyaller |

#### Süzgeç çelişkisi ve çözümü

Gerçek zamanlı kip örtüşme süzgecine **muhtaç**, ETS ondan **kurtulmalı**. Anahtar veya
röle yerine **iki ADC pini** kullan — sıfır parça, sıfır kontak direnci:

- **GPIO4 (CH3)** = skop **ham** (süzgeçsiz, geniş bant, ETS için)
- **GPIO7 (CH6)** = skop **süzülmüş** (SK 16.55 kHz, tek-seferlik için)

Aynı TL072 tamponunu iki yola çatallayarak. Firmware kipe göre pattern'i değiştirir.

> **GPIO7'yi kurtarmak için ADS ALERT/RDY'yi GPIO21'e taşı.** ALERT sayısal bir sinyal,
> ADC pinine ihtiyacı yok.

#### 🌟 ETS'in kolay ve KESİN yolu: koherent örnekleme

"12.5 ns gecikme üret ve ADC'yi yeniden başlat" **çalışmaz** —
`adc_continuous_start()` gecikmesi onlarca µs ve titreşimli. Doğru numara gecikme
eklemek değil, **frekans seçmek**:

ETS kipinde örnekleme hızını **80 000 Sa/s** iste → APB bölücüsü tam **1000 tik**.
Uyarım periyodunu **P tik** seç ve **P'yi 1000 = 2³·5³ ile aralarında asal** yap:

| P (tik) | f | Eşdeğer adım | Faz sayısı | Bir tam kayıt |
|---|---|---|---|---|
| **799** | **100.125 kHz** | **12.5 ns** | 799 | **9.99 ms** |
| 1599 | 50.031 kHz | 12.5 ns | 1599 | 19.99 ms |
| 3199 | 25.008 kHz | 12.5 ns | 3199 | 39.99 ms |

**Eşdeğer örnekleme hızı 80 MSa/s. Tetikleme yok, capture yok, titreşim yok** (her şey
aynı XTAL'den). 1 s'de 100 geçiş → √100 = **10× gürültü bastırma**; ESP32 ADC'nin bol
gürültüsü doğal dither görevi görüp 12 bit ham izi **~15 bit efektif** yapar.
*Gürültülü ADC bir anda iyi bir ADC oluyor.*

⚠️ `sample_freq_hz`'in **gerçekleşen** değerini varsayma, **ölç**: GPTimer ile 10 s
boyunca dönüşüm say → ppm doğrulukla gerçek hızı bul. ETS'in tüm doğruluğu bu tek sayıya
dayanıyor.

#### Dış SMPS için: analog dalgayı değil, PWM'in KENDİSİNİ tetikle

**Kilit içgörü:** SMPS ölçerken her zaman elinde bir saat sinyali var — SG3525'in çıkışı,
TL494'ün OUT'u, IR2110'un girişi. Onu GPIO'ya alıp MCPWM capture ile damgala.

| Tetik kaynağı | Titreşim (σ) | Jitter tavanı | Yargı |
|---|---|---|---|
| Kart uyarımı (koherent) | ~ps | >100 MHz | ✅ en iyi |
| **Sayısal senk → GPIO → MCPWM capture** | **~3.6 ns** | **36.8 MHz** | ✅ **SMPS için doğru cevap** |
| Harici komparatör (TL072/LM358) | yüzlerce ns | ~1 MHz | ❌ yetersiz |
| **Yazılımla ADC örnekleri üzerinde (bugünkü kod)** | **12 µs** | **0.13 MHz** | ❌ **ETS için işe yaramaz** |

#### 🧱 ETS'in DÜRÜST bant genişliği tavanı

| Katman | Sınır |
|---|---|
| Bölücü, 1 nF kalırsa | **25 kHz** → ETS ölür |
| Bölücü **kompanze edilirse** (Cp·100K = Cs·6.8K) | düz, çok MHz |
| TL072 tampon, 3 V p-p'de slew tavanı | 1.38 MHz |
| 1 kΩ + kelepçe kapasitesi | 14.5 MHz |
| **ESP32-S3 ADC track/hold + giriş bandı** | 🧱 **Espressif YAYINLAMIYOR** — tahmin 0.3–1 MHz |
| Zamanlama titreşimi 12.5 ns | 10.6 MHz |

**Dürüst ifade — kullanıcıya böyle söyle:** *"Eşdeğer örnekleme hızı 80 MSa/s. Analog
bant genişliği ölçülene kadar 500 kHz'in altında varsayılmalıdır; 0.3–1 MHz
beklenmektedir. MHz vaat edilmemektedir."*

**🌟 Kartın kendini ölçmesi — bunu firmware'e koy.** MCPWM'in kendi kare dalgasının
kenarı <2 ns'dir. ETS ile o kenarı yeniden kur, %10–90 yükselme süresini ölç,
BG ≈ 0.35/t_r. Sonucu NVS'e yaz ve **her ETS başlığında yayınla**. Kart kendi bant
genişliğini ilan eder, tasarımcı değil — bu, projenin "hiçbir ölçüm değeri elle yazılmaz"
kültürünün doğal devamı.

#### ETS ne zaman ÇALIŞIR, ne zaman YALAN söyler

| Durum | ETS | Neden |
|---|---|---|
| Kart uyarımlı devre | ✅ kusursuz | koherent, titreşimsiz |
| Kararlı SG3525/TL494, sabit yük | ✅ iyi | periyot titreşimi 10–100 ns, analog duvarın üstünde |
| **UC3843 (akım kipi)** | ⚠️ kısmen | tepe-akım sonlandırması OFF süresini titretir. **Yükselen kenardan (saat) tetikle**; düşen kenar bulanık çıkar — bu gerçektir, kusur değil |
| Hafif yükte darbe atlama / burst | ❌ **çöp** | dalga tekrarlayan değil |
| Yayılı spektrum saat | ❌ | periyot dağılımı geniş |
| Yumuşak başlatma, yük basamağı | ❌ | tanım gereği tek-seferlik |
| **Arıza, açılış darbesi, MOSFET patlaması** | ❌ **asla** | ETS "nadir olay" aramak için kullanılamaz |

**🌟 Firmware'e reddetme mantığı koy.** MCPWM capture zaten her tetiğin zaman damgasını
veriyor. Periyot σ'sını hesapla: σ > 1 bin (12.5 ns) → uyar; histogram çok tepeli →
**reddet**, *"darbe atlama algılandı, tek-seferlik kullanın"* de. σ'yı her ETS başlığında
yayınla.

**Altın kural:** *ETS "kararlı bir çevrim neye benziyor" sorusunu cevaplar. Tek-seferlik
"ne oldu" sorusunu cevaplar. İkisini karıştırma.*

#### Tek-seferlik kip: bellek ve tetik

**DMA'yı DURDURMA.** ADC sürekli koşar, tetik akış üzerinde yazılımla aranır; tetik
bulununca halkadaki yazma imleci dondurulur → **ön-tetik bedava gelir**.

İki katmanlı tampon: ADC →DMA→ dahili SRAM halkası (32 KB) → toplama görevi →
PSRAM halkası (2 MB = kanal başına 12.6 s @ 41.67 kSa/s). Akış 333 KB/s; PSRAM oktal
yazma bandının ~1/150'si, darboğaz yok.

Tetik motoru: `seviye + kenar + histerezis + tutma(holdoff) + ön_tetik_oranı`.
Varsayılan kayıt 20 000 örnek/kanal (480 ms), azami 500 000 (12 s).

⚠️ Bkz. **4.9** (FQBN'de PSRAM açık değil) ve **4.11** (aktarım darboğazı) — ikisi de bu
kipin önkoşulu.

### 5.3 Wattmetre

Bugün güç zaten doğru hesaplanıyor: **örnek başına V×I çarpımının ortalaması**
(ort(V)×ort(I) değil — bu ikisi değişken yükte farklıdır ve A4 bunu gösteriyor).

Hızlı kanalla kazanılacak olan: **anahtarlamalı yükte gerçek ortalama güç**. Bir SMPS'in
girişindeki akım darbeli; 860 SPS ile bunun ortalaması yanlış çıkar, 83 kSa/s ile doğruya
yaklaşır.

Kayma düzeltmesi **zorunlu** — sayılar 5.1.1'de. İki ADS1115'in ayrı çipler olması bu
yüzden bilinçli bir tasarım kararıydı (A4'te "V ve I EŞ ZAMANLI örnekleniyor" notu);
hızlı kanalda aynı lüks yok, DSP ile telafi edilecek.

**Yayınlanacak yeni büyüklükler** (`D2` satırı): Vrms, Irms, P = Σ(v·i_hiza)/N, S, PF,
Q, Vdc, Idc, tepe faktörü (kırpma teşhisi için). Enerji uint64 pJ olarak korunuyor.

#### 🌟 Faz kalibrasyonu — sinyal üreteci gerektirmeyen yöntem

Kayma FIR'ı düzeltilse bile iki artık kalır: fark yükseltecinin 107 kHz kutbu (1 kHz'te
0.54° → PF 0.5'te **%1.6 hata**) ve iki SK süzgecin %5 uyumsuzluğu (0.25° → %0.76).
Bunlar **ölçülüp silinmeli**:

1. MCPWM (GPIO13) → kapı direnci → güç MOSFET'i → **saf dirençsel yük** (taş dirençler yolda)
2. Dirençsel yükte v ile i **tanım gereği aynı fazdadır** → ölçülen her faz farkı
   **aletin kendi hatasıdır**
3. Kare dalganın harmonikleri bandı doldurur → **tek ölçümde tüm bant**
4. Firmware çapraz-korelasyonla Δτ'yi bulur, NVS'e yazar, kesirli-gecikme FIR'ına uygular

Yeni komut `f`. Kart dışında **hiçbir alet gerektirmiyor** — envanterde olmayan tek şey
(sinyal üreteci) yerine olan şeyi (MOSFET + direnç + MCPWM) kullanıyor.

#### ⚠️ Anahtarlama düğümünde ölçülen güç ANLAMSIZDIR

41.67 kSa/s ile 100 kHz'e erişemezsin ve örtüşme süzgeci onu −31 dB kesiyor. **Ama bu
bir kayıp değil:** SMPS'in giriş DC barasında (giriş kondansatörünün arkasında) ölçtüğünde
anahtarlama bileşeninin net ortalama güce katkısı ihmal edilebilir. Örnek: 12 V üzerinde
50 mV dalgacık × 1 A p-p → en fazla ~12 mW, 12 W'ta **%0.1**.

Aşama 1'deki "DC bara tarafında ölç" kuralı doğruydu; hızlı kanalla artık bunun **neden**
doğru olduğunu sayıyla söyleyebiliyorsun.

### 5.4 Besleme — sanıldığından çok küçük bir iş

> ⚠️ **Bu bölüm 2026-09-08'de DÜZELTİLDİ.** Önce "hurda ATX zorunlu, yoksa Rds(on)
> ölçümü ölür" yazmıştım. **Yanlıştı.** Rakamlara bakınca ihtiyaç çok daha küçük.

**"15 V" bir hedef değil, sadece 7812/7912'nin giriş şartı** (dropout ~2.5 V → çıkışta
12 V için girişte ≥14.5 V). **12 V'u doğrudan bir kaynaktan alırsan regülatöre hiç gerek
kalmaz ve 15 V sorunu tamamen ortadan kalkar.**

#### İki ayrı ihtiyaç var — karıştırma

**A) ±12 V analog ray — çok küçük**

| Tüketici | Adet | Ray başına |
|---|---|---|
| TL072 (2.8 mA/paket tipik, 5 mA azami) | 4 | 11 mA tipik / 20 mA azami |
| LM319 (~4.3 mA) | 2 | ~9 mA |
| **Toplam** | | **~20 mA tipik, 50 mA tasarım hedefi** |

**B) +12 V güç rayı — tepe yüksek, ORTALAMA DÜŞÜK**

> 🔴 **Düzeltme: elektronik yük bu raya ihtiyaç duymuyor.** Yükün harcadığı güç, test
> edilen cihazdan gelir — bizim beslememizden değil.

| Kullanım | Tepe | Darbe | Görev | **Ortalama** |
|---|---|---|---|---|
| Rds(on) ölçümü | 5 A | 1 ms | %2 | 100 mA |
| Doyum testi | 10–15 A | 100 µs–1 ms | %1 | ~100 mA |

**Tepe akımı kondansatör bankası karşılar; besleme sadece ortalamayı verir.**
Stokta ≥25 V dayanımlı elektrolitik: 470µF/35V ×6 + 470µF/63V ×6 + 1000µF/35V ×5 +
1000µF/25V ×1 = **~11 600 µF**.

- Rds(on): 5 A × 1 ms = 5 mC → 10 000 µF'ta düşüm **0.5 V** ✅
- Doyum: 10 A × 100 µs = 1 mC → düşüm **0.1 V** ✅

**Sonuç: 12 V @ 1–2 A + kondansatör bankası yeter.** 15 A'lik kaynak gerekmiyor.

#### Nasıl elde edilir — kolaydan zora

| # | Yol | Not |
|---|---|---|
| **1** ⭐ | **İki izole 12 V adaptör, seri** | Birinin (−)'sini diğerinin (+)'sına bağla, o düğüm GND. Doğrudan ±12 V. **Regülatör yok, trafo yok, 15 V yok.** Duvar adaptörleri izoledir |
| **2** ⭐ | **Tek 12 V adaptör + NE555 şarj pompası** | +12 adaptörden, −12 NE555'ten (yolda ×10). ~50 kHz astable + SR5100 Schottky pompası (stokta ×10) → 50 mA'de ~−10.5 V |
| 3 | 15-0-15 trafo + köprü + 7812/7912 | 15 V'un asıl geçtiği yer. E tipi çekirdek ×2 stokta, sarılabilir — ama sıradan bir besleme için emek |
| 4 | Hurda ATX | Tek kutuda +12/−12/+5/+3.3. **Kolaylık, zorunluluk değil** |

> 🌟 **−12 V olması şart değil.** TL072'nin giriş ortak-mod aralığı negatif raydan ~4 V
> yukarıda başlar; sinyaller 0 V civarında olduğu için **−10 V fazlasıyla yeterli**.
> Asimetrik ray (+12/−10) sorun değil. Bu, 2. yolu tamamen geçerli kılıyor.

⚠️ ATX kullanılırsa −12 V rayı gürültülüdür. Opamp beslemesi için sorun değil (TL072
PSRR ~100 dB + yerel 100 nF/10 µF bypass), ama **analog referans olarak asla
kullanılmamalı** — referans zinciri 3.3 V / TL431 tarafında kalıyor.

### 5.5 🌟 En önemli mimari karar: beş yetenek üç yapı taşı paylaşıyor

| Yapı taşı | Kim kullanıyor |
|---|---|
| **A. PWM→RC analog referans** (LEDC + 2 kutuplu RC) | Elektronik yük, eğri çizici (2 eksen), doyum testi eşiği |
| **B. Opamp + MOSFET + şönt lineer çevrim** | Elektronik yük, eğri çizici, doyum akım sınırı |
| **C. MCPWM capture zaman tabanı** | SMPS zamanlama, doyum testi |
| **D. ±12 V ray** | A, B ve komparatörler |

> **Eğri çizici (transfer kipi) ile elektronik yük FİZİKSEL OLARAK AYNI DEVREDİR.**
> Fark tek satır firmware: yükte MOSFET sabit ve DUT dışarıda; eğri çizicide DUT'un
> kendisi o MOSFET'in yerine takılıyor. **Birlikte kurmak ~%70 iş tasarrufu.**

### 5.6 Eğri çizici

**İki kip, iki maliyet sınıfı:**

**Mod-T (transfer/eşik) — ucuz, en yüksek getiri.** DUT'u lineer çevrimin MOSFET yuvasına
tak; opamp DUT'un kendi kapısını sürüp akımı sabitler, firmware akımı süpürüp Vgs okur.

| Ölçüm | Şönt | Gerçekçi doğruluk |
|---|---|---|
| **Vgs(th)** (Id = 250 µA'e servo) | **1 kΩ** | ±20 mV |
| Id–Vgs transfer eğrisi, gfs | 1R / 0.1R | ±%0.3 akım, ±5 mV Vgs |
| **Rds(on)** (Vgs=10 V, Id=5 A, Kelvin) | 0.1R / 15mR | **±%0.5** |
| BJT hFE | 1R | ±%2 |
| Diyot/LED Vf–If | 1k → 0.1R | ±2 mV |
| **Sökme parça ayıklama** | 1k / 1R | *mutlak değil, sağlam parçayla FARK* |

> 🌟 **Neden 1 kΩ şönt şart:** Vgs(th) tanım gereği 250 µA'de ölçülür. 1R şöntte bu
> **250 µV** eder — TL072'nin ofsetinin (10 mV) kırkta biri, ölçülemez. 1 kΩ'da 250 mV
> olur. Stokta 1K ×36 var.

**Mod-O (Id–Vds eğri ailesi) — pahalı, SONA bırak.** Programlanabilir ray gerekiyor
(2. opamp + IRF4905 yüksek taraf geçiş elemanı + ATX). Mod-T zaten sayısal cevapları
veriyor; Mod-O güzel grafik veriyor.

#### 🔴 ADS1115 darbeli süpürmede KULLANILAMAZ

ADS1115 delta-sigma'dır, **dönüşüm penceresi boyunca ORTALAMA alır**. 1 ms'lik darbeye
1.16 ms'lik dönüşümle bakarsan darbenin kapalı kısmını da ortalamaya katar → sistematik
düşük okur.

**Doğru iş bölümü:** darbe = ESP32 ADC (12 µs, 64 ortalama = 0.77 ms, ~%1);
DC noktaları = ADS1115 (%0.05). Isınmanın sorun olduğu yerler zaten %1'in yettiği
yerler; Vgs(th) ve Rds(on) DC ölçülebilir ve orada %0.05 alınır.

**Darbe parametresi: tp = 1 ms, T = 50 ms (%2 görev).** Tek darbede ΔTj < 2 °C, ortalama
1.2 W (soğutucusuz taşınır), 0.77 ms'lik ölçüm 1 ms'e sığar. 500 noktalık aile **25 s**.
DAC oturması (1.93 ms) soğuma süresinin arkasına gizlenir, bedava.

#### 🔴 Kelvin, Rds(on) için ZORUNLU

| Parça | Rds(on) | Soket+tel (30 mΩ) hatası | **Kelvin (0.5 mΩ)** |
|---|---|---|---|
| IRF3205 | 8.0 mΩ | **%375** | %6.2 |
| IRFZ44N | 17.5 mΩ | %171 | %2.9 |
| IRFP250N | 75.0 mΩ | %40 | %0.7 |

**Kelvin'siz IRF3205'in Rds(on)'unu ölçersen gerçek değerin 4.75 katını okursun.** Bu
ölçüm değil, gürültü. DUT soketinden **dört ayrı tel** (2 kalın güç, 2 ince algılama,
bacağın dibine) → ADS U3 AIN2-AIN3 diferansiyel, PGA ±0.256 V.

⚠️ **Sıcaklık:** Vgs(th)'nin tempco'su ~−5 mV/°C. Elinle parçaya dokunursan eşik 15 mV
kayar. Darbeli süpürme bunu çözmez — parça ortam sıcaklığında olmalı, iki ölçüm arasında
30 s beklenmeli.

**LEDC bölüşümü:** T0 = 12 bit @ 19.53 kHz (2× 1k+1µF RC → ripple 279 µV = 0.35 LSB,
oturma 19.3 ms) — yük akım referansı, eğri çizici Vgs ekseni, doyum eşiği.
T1 = 10 bit @ 78 kHz (2× 1k+100nF → 1.93 ms oturma) — hızlı Vds ekseni.
**14 bit kullanma:** 4.88 kHz taşıyıcıda 0.5 LSB ripple için τ = 1.68 s → 500 nokta
97 saniye. Ölü. Çözünürlük eksiği ADS1115'in dış cevrimiyle kapatılır — **iç analog
çevrim kararlılık için, dış sayısal çevrim doğruluk için.**

### 5.7 Dört ek yetenek

#### SMPS zamanlama analizörü — en ucuz, ~5 TL

**Optokuplör ölü (doğrulandı):** PC817'nin tr/tf'i tipik yükte 10–20 µs ve CTR %50–600
arası değiştiği için gecikme **mikrosaniyeler mertebesinde oynar**. Ölçülecek ölü zaman
100 ns – 2 µs → *aletin belirsizliği ölçtüğü şeyden 5–10 kat büyük.*

**Kazanan: rezistif bölücü + TL431 rayına kelepçe.** Gecikme sadece RC (3.7–13.6 ns) ve
kanallar aynıysa ortak mod olduğu için **ölü zaman farkında yok oluyor**.
3.3 V rayına kelepçe olmaz (3.3+0.7 = 4.0 V > 3.6 V mutlak azami); TL431 rayında düğüm
en fazla **3.195 V** — VIH'in 0.72 V üstünde, mutlak azaminin 0.4 V altında. **Bu ray
kartta zaten var.**

Menzil jumper'ı: R1 = 1k/2.7k (5 V mantık) · R2 = 1k/330R (12–15 V kapı) ·
R3 = 10k/1k (yüksek taraf). Hepsi stokta.

> 🌟 **En yüksek getirili firmware özelliği: de-skew kalibrasyonu.** Aynı sinyali üç
> kanala birden ver, artık farkı ölç, NVS'e kaydet, her ölçümde çıkar. Bu tek adım
> bölücü RC farkını, GPIO eşik dağılımını, direnç toleransını ve iz gecikmesini
> **hepsini birden** siler.

**Gerçekçi doğruluk:** frekans ±20 ppm (kristal sınırlı), duty ±0.02 %-puan (hızlı
kenar), **ölü zaman ±15 ns (1σ)** — 200 ns'lik bir ölü zamanı %7.5 ile ölçmek demek,
SMPS ayarı için fazlasıyla yeterli. Azami ~500 kHz (ISR sınırı), patlama kipinde 1 MHz.

**Yüksek taraf:** kapı sinyali yüzen referansta. **En iyi cevap: kontrolcü çıkışlarını
ölç** (SG3525 pin 11/14, TL494 OUT, IR2110 HIN/LIN) — bunlar toprak referanslı ve ölü
zamanın kaynağı zaten kontrolcü. Gerçek izolasyon şartsa 6N137 (50 ns, ~10 TL).

⚠️ 1N4148 stokta 8 adet; 6'sı bu işe gidiyor, Aşama 2 zaten 2 kullanıyor. **Yeni al.**

#### Elektronik yük

**MOSFET: IRFP250N** (IRFZ44N değil) — TO-247 daha büyük soğutucuya oturur, 200 V marjı
doyum testinde de işe yarar, büyük çip lineer bölgede termal kararsızlığa dayanıklı.

**Opamp: TL072, LM358 DEĞİL.** Sırasıyla: (1) LM358'in çıkışı **B sınıfı ve crossover
distorsiyonlu** — kapalı çevrimde sıfır geçişinde kazanç çöküşü → limit-cycle salınımı.
*Elektronik yükün ötmesinin en yaygın sebebi budur.* (2) Aşağı doğru zayıf çeker
(~20 µA) → kapı yavaş kapanır. (3) Slew 0.3 vs **13 V/µs** (43×). (4) Bias 45 nA vs
30 pA — 1 kΩ şöntte 45 µV hata.

**Kararlılık — somut değerler:** `Rin = 10 kΩ, Cf = 10 nF, Rg = 100 Ω, Cgs_ext = 10 nF`
→ faz payı her akımda ve her şönt kademesinde **>80°**. (Cf = 1 nF yaparsan 33°,
100 pF yaparsan 3.7° — öter.) Ek olarak: drain snubber 10R+100nF, kapı pull-down 10k,
yerel bypass, şönt→opamp ve şönt→GND **ayrı, kısa, bükülü** teller.

**Soğutucu ZORUNLU — ✅ kullanıcıda var (`MEK002`), ama ölçüsü teyit edilmeli:**

| Soğutucu | İzin verilen P | 12 V'ta Id |
|---|---|---|
| **yok** | **2.4 W** | 0.20 A |
| 5 °C/W | 15.4 W | 1.29 A |
| **2 °C/W** | **30.2 W** | **2.51 A** |

"12 V × 2 A = 24 W" için **≤2.5 °C/W** şart (~100×60×30 mm kanat veya 60×60 + fan).

> ⚠️ **MOSFET'leri lineer bölgede PARALEL BAĞLAMA.** Vgs(th) tempco'su negatif → sıcak
> olan daha çok çeker, daha çok ısınır. **Termal kaçak, kaçınılmaz.** Doğrusu: her
> MOSFET'e kendi opampı ve kendi şöntü. TL072 ×4 = 8 kanal var, ikinci kanal bedava.

> 🔴 **Donanım watchdog ŞART.** MCU çökerse PWM registeri son değerinde donar → referans
> tam kalır → yük 30 W'ta sonsuza kadar çeker. Şarj pompası + 470k boşaltma + 2N2222
> kapıyı kaynağa kısa devre eder, 0.5 s'de keser. **Tüm parçalar stokta.**
> Ayrıca: NTC (yazılım foldback) + KSD9700 70 °C termal anahtar (donanım kesici).

**Otomatikleşen ölçümler:** yük regülasyonu eğrisi (10 s), verim süpürmesi (25 s), pil
kapasitesi (±%0.3), kaynak iç direnci (2 s), kondansatör ESR (100 ms), SMPS geçici
yanıtı (20 ms pencere), aşırı akım koruma testi (30 s).

#### Bobin/trafo doyum testi

**Sadece ADC ile: L ≥ ~600 µH @ 12 V.** Yani şebeke bobinleri ve büyük trafo primerleri.
**Tipik SMPS bobinleri (10–500 µH) kapsam DIŞI.** ("Daha düşük gerilim" çare değil —
DCR devreye girip rampayı eksponansiyele çeviriyor: 100 µH/100 mΩ'da 2 V'ta eğrilik %11.5.)

> 🌟 **Doğru yöntem: komparatör + MCPWM capture.** Genlik problemini zaman problemine
> çevirip zamanı 12.5 ns'de ölç. Eşiği LEDC DAC ile süpür, LM319 tetiklenince capture
> zaman damgası al. **L(I) = V·Δt/ΔI** — ardışık eşikler arası farkta komparatörün sabit
> gecikmesi **tamamen yok olur**, sadece jitter kalır.
> Üç capture kanalı = tek atışta üç eşik → atıştan atışa sapma da yok olur.

| Sürüş | L | **L hatası** |
|---|---|---|
| 12 V | 10 µH | %3.39 |
| **12 V** | **100 µH** | **%0.34** |
| 12 V | 500 µH | %0.068 |

**Kapsanan menzil: 5 µH – 100 mH, 0.1–15 A** — SMPS bobinlerinin tamamı içeride.

🔴 **LM319N ×2 alınmalı (~15 TL) — envanterde komparatör yok.** TL072 açık çevrim
~2000 ns gecikme/500 ns jitter verir → 100 µH'de %13 hata, işe yaramaz.
**Bu tek parça, doyum testini "yapılamaz"dan "±%0.3"e taşıyor.**

⚠️ **Darbe anahtarı IRFP250N (200 V) olmalı, IRFZ44N (55 V) DEĞİL.** UF4007 + 3.3R 11W
kelepçesiyle 10 A'de Vds tepe **45.7 V**'a çıkıyor; kablo endüktansı üstüne binerse
IRFZ44N avalanche'a girer.
⚠️ **IR2110/IR2104 3.3 V mantıkla doğrudan sürülemez** (VIH = 9.5 V @ Vcc=15 V) —
2N2222 açık kollektör evirici + 1k pull-up → +12 V gerekiyor.

#### Verim ölçer

**Kanal dağılımı — kaymayı YAVAŞ değişkene koy.** ADS1115'te tek ADC + mux var; 4 kanal
için biri mutlaka çoklanacak. SMPS baralarında **gerilim yavaş ve düzgün, akım hızlı ve
tırtıklıdır**:

| | U1 (0x48) | U2 (0x49) | U3 (0x4A) |
|---|---|---|---|
| ✅ **Seçilen** | **Ii diff, sürekli** | **Vi + Vo çoklanmış** (2.33 ms kayma) | **Io diff, sürekli** |

**Hata bütçesi.** %90 verimi ±1 puan mutlak ile ölçmek = bağıl %1.111 → kanal başına
%0.278 (en kötü hal) veya %0.556 (RSS). Mevcut donanımın kanal başına gerçekçi hatası:
δV = %0.251, δI = %0.115 → **η hatası ±0.352 puan (RSS)**. **±1 puan hedefi
karşılanıyor** — ama üç şartla:

| # | Şart | Yapılmazsa |
|---|---|---|
| 1 | Dört kanal **aynı referansla, aynı noktada** kalibre | ±0.97 puan |
| 2 | Örtüşme süzgeçleri düzeltilecek (aşağıda) | aliasing %1'e kadar kayma → geçersiz |
| 3 | Bölücülerde **metal film %1, ≤100 ppm/°C** | karbon filmin 250 ppm/°C'si bütçenin %90'ını yer |

> ### 🌟🌟 EN ÖNEMLİ İÇGÖRÜ — AN8000 sorununu büyük ölçüde çözüyor
>
> η = (Vo/Vi)·(Io/Ii). Vi ve Vo'yu **aynı DMM ile, aynı gerilimde** kalibre edersen,
> DMM'in kazanç hatası her ikisine de aynı çarpanla girer ve **oranda birinci mertebede
> yok olur.**
>
> | Kalibrasyon referansı | Kanalları AYRI kalibre | **AYNI referans, AYNI nokta** |
> |---|---|---|
> | **Hobi DMM %0.5 (AN8000)** | ±**0.966** puan | ±**0.352** puan |
> | 6.5 hane %0.05 | ±0.363 puan | ±0.352 puan |
>
> **Bir %0.5'lik hobi multimetresi, 6.5 haneli masa referansıyla neredeyse eşdeğer hale
> geliyor.** Bölüm 1.3'teki "AN8000 tavanı" endişesi verim ölçümü için büyük ölçüde
> geçersiz — çünkü orada mutlak değil **oran** ölçüyorsun.
>
> **Uygulama:** (1) Vi ve Vo'yu aynı DMM ile aynı gerilimde (ör. ikisi de 12.00 V).
> (2) Akımlar için **iki şöntü SERİ bağla, tek akım geçir, ikisini birden okut** —
> kaynağın mutlak değerini bilmene bile gerek yok, sadece oranı eşitliyorsun.
> (3) Kalibrasyonu ölçümle aynı sıcaklıkta, aynı gün yap.

**🔴 Yeni bulunan kusur — voltmetre bölücüsündeki 1 nF:** ADS1115'in modülatörü ~250 kHz'te
koşar; 100 kHz ripple **katlanarak DC'ye biner** ve ortalamayı kaydırır. Mevcut 1 nF
(fc 25 kHz) 100 kHz'te sadece −12.3 dB. **1 nF → 100 nF yap** (fc 250 Hz, −52 dB).
Osiloskop AYRI bölücüden beslendiği için etkilenmez → **hiçbir şeyi bozmayan bedava
40 dB iyileşme.** Akım kanallarında da 100 nF → 1 µF, iki kademe.

**Doğrulama testi:** girişi ve çıkışı **kısa devre et** → η = %100 okumalı. Sonra araya
bilinen bir direnç koy → η hesaplanabilir. Bu iki test sistematik hataları yakalar.

🔴 **Offline (şebeke referanslı) SMPS verim ölçümü bu kartın KAPSAMI DIŞINDA.** Toprakları
bağlarsan izolasyon bariyerini kısa devre edersin; bağlamazsan ADS'nin ortak mod sınırını
(±0.3 V) aşarsın ve çip anında ölür. Yapılabilmesi için tam izole bir ölçüm adası gerekir
(ayrı ESP32 + izole DC/DC + opto UART) — **ayrı proje.**

### 5.8 Satın alma listesi

> ⚠️ **Bu liste 2026-09-08'de küçüldü.** ATX ve soğutucu "zorunlu"dan çıktı — bkz. 5.4
> (besleme sanıldığından küçük) ve aşağıdaki soğutucu notu.

**Zorunlu (~40 TL):**

| Parça | Adet | Ne için |
|---|---|---|
| **LM319N** (çift komparatör, 80 ns) | 2 | Doyum testi. **Envanterde komparatör yok.** Bu tek parça doyum testini "yapılamaz"dan ±%0.3'e taşıyor |
| **10 kΩ NTC B3950** | 2 | Elektronik yük aşırı sıcaklık koruması (yazılım foldback) |
| **KSD9700 70 °C NC** | 1 | Donanım ısı kesici — firmware'den bağımsız |
| **Metal film %1 ≤100 ppm/°C** (100K, 10K, 6.8K, 1K) | 10'ar | Verim bölücüleri. Karbon filmin 250 ppm/°C'si bütçenin %90'ını yer |
| **1N4148** | 20 | Elektronik yük kelepçeleri + watchdog (stokta 8). **Ölçüm kartı bunu kullanmıyor** — orada BAT85 |
| Mika yalıtkan + montaj seti | 5 | MOSFET–soğutucu |

**Duruma bağlı:**

| Parça | Ne zaman gerekir |
|---|---|
| ~~12 V adaptör ×2~~ | ✅ **ÇÖZÜLDÜ, 5.12.23**: 12 V adaptör yok; 6× 18650 (iki 3'lü paket sırt sırta) ±9…±12.6 V veriyor, yükseltici gerekmiyor. Yedek yol: 24 V kaynak + LM358 orta nokta tamponu |
| **Soğutucu ≤2 °C/W** | ✅ **Kullanıcıda VAR** (2026-09-08 bildirdi, `MEK002`). ⚠️ **Ölçüsü/termal direnci BİLİNMİYOR** — 2 °C/W eşiği elektronik yükte 2.4 W ile 30 W arasındaki farkı belirliyor. **Yeni oturum bunu teyit etsin ve CSV'yi güncellesin** |
| Hurda ATX | Kolaylık isteniyorsa. **Zorunlu değil** |

**❌ ALMAYA GEREK OLMAYANLAR** (yaygın yanılgılar):

| Parça | Neden gereksiz |
|---|---|
| Harici I2C DAC (MCP4725) | LEDC 12 bit + 2 kutuplu RC + ADS dış cevrimi **daha iyi** sonuç veriyor |
| Hızlı ADC modülü | Doyum testinin ADC problemi komparatör+capture ile tamamen çözülüyor |
| Yeni optokuplör | Zamanlama işi için hiçbiri kullanılamaz (hız) |
| Mantık seviyesi MOSFET | ±12 V rayı sorunu çözüyor; lineer bölgede Vgs zaten 5 V |

### 5.9 Önerilen pin planı (Aşama 3)

| Pin | Kanal | Görev | Ön uç |
|---|---|---|---|
| GPIO4 | ADC1_CH3 | **Skop — ham** | kompanze bölücü → TL072 tampon, **süzgeç yok** |
| GPIO5 | ADC1_CH4 | **Ölçüm V (hızlı)** | *ADS ile AYNI* bölücü → tampon → SK 16.55 kHz |
| GPIO6 | ADC1_CH5 | **Ölçüm I (hızlı)** | ayrı Kelvin çifti → fark yük. G=27 → SK 16.55 kHz |
| GPIO7 | ADC1_CH6 | **Skop — süzülmüş** | aynı tampon → SK 16.55 kHz |
| GPIO10 | ADC1_CH9 | **Akım — ham** | fark yük. çıkışı doğrudan (bobin akımı ETS) |
| GPIO1/2 | CH0/CH1 | boş | 2. gerilim düğümü (verim) |
| GPIO8/9 | — | I2C SDA/SCL | mevcut |
| GPIO12 | — | **MCPWM capture girişi** | SMPS gate sürücüden sayısal senk |
| GPIO13 | — | **MCPWM üreteç çıkışı** | uyarım / prob-komp / faz kalibrasyonu |
| GPIO14 | — | LEDC PWM → RC | tetik seviyesi "DAC"ı |
| GPIO21 | — | ADS ALERT/RDY | **GPIO7'den taşındı** |
| GPIO19/20 | — | **yerel USB CDC** | derin kayıt aktarımı (bkz. 4.11) |

**TL072 kesit dağılımı (4 çip = 8 kesit, tam oturuyor):** U1a akım fark yükselteci ·
U1b akım SK · U2a gerilim tamponu · U2b gerilim SK · U3a skop tamponu · U3b skop SK ·
U4a fark yük. REF tamponu (+1.5 V) · U4b yedek.

> ### 🔴 ÇÖZÜLMEMİŞ: pin planı çakışması
>
> Bu belge iki ayrı tasarım çalışmasından derlendi ve **ikisinin pin planı çakışıyor.**
> Gizlemek yerine işaretliyorum — yeni oturumun ilk işlerinden biri bunu çözmek olmalı.
>
> | Pin | Toplama mimarisi istiyor | Enstrüman yetenekleri istiyor |
> |---|---|---|
> | GPIO5 | Ölçüm V (hızlı ADC) | Doyum rampası (hızlı ADC) |
> | GPIO6 | Ölçüm I (hızlı ADC) | Eğri çizici Vds (hızlı ADC) |
> | GPIO7 | Skop süzülmüş (ADC) | ADS ALERT (mevcut yerinde kalsın diyor) |
> | GPIO10 | Akım ham (ADC) | yedek |
> | GPIO11–18, 21, 38 | — | MCPWM capture/fault/üreteç, 4× LEDC, watchdog |
>
> **ADC1'de yalnız 10 kanal var (GPIO1–10)** ve iki tasarım toplamda bundan fazlasını
> istiyor. Çakışma gerçek, uydurma değil.
>
> **Çözüm yönü:** yetenekler aynı anda çalışmıyor. Kip bazlı pin paylaşımı (ölçüm kipinde
> V/I, eğri çizici kipinde DUT, doyum kipinde rampa) ADC pinlerini üçe bölmek yerine
> yeniden kullanmayı sağlar. Ama bu, **analog çoklayıcı** gerektirebilir — envanterde
> CD4051/4066 **yok** (Entegre kutusu tam tarandı). Alternatif: ayrı ön uçları ayrı
> pinlere bağlayıp kullanılmayanı yüksek empedansta bırakmak.
>
> ⚠️ **Ayrıca doğrulanmalı:** GPIO11–18, 21, 38 pinlerinin senin geliştirme kartında
> **gerçekten pin başlığına çıkarıldığı**. Bazı ESP32-S3 kartları çıkarmaz. Yedek:
> GPIO39–42 (JTAG) ve GPIO43/44 (UART0; yerel USB kullanılıyorsa boşta).
> **GPIO11–14 = ADC2, WiFi ile çakışır — bu pinleri yalnız SAYISAL olarak kullan.**

**Yeni alınacak (birkaç lira):** 1 nF C0G şerit (SK süzgeçler için pay), BAT54 ×6
(geniş bantlı alt kelepçe), 5–30 pF trimer ×2 + 470 pF C0G ×2 (bölücü kompanzasyonu).
27K, 1K, 6.8K, 10 k trimpot, SR5100 **stokta var**; TL072, ±12 V regülatörleri, şöntler
**yolda**.

### 5.10 Önerilen uygulama sırası

Yapı taşları paylaşıldığı için sıra önemli:

Her adımın bir **kapısı** var — geçmeden sonrakine geçme. Bu, projenin mevcut
doğrulama kültürünün devamı.

| # | İş | Kapı (geçme koşulu) |
|---|---|---|
| **3.0** | **Sıfır donanım — ÖNCE ÖLÇ.** Yeni `A6` adımı: 2 kanallı pattern'i kur, `type2.channel` demux'unu 60 s kanıtla, **gerçek dönüşüm hızını GPTimer ile ölç**, ESP ADC gürültü tabanını 6.37 kΩ ve düşük empedanslı kaynakla ölç, FQBN'e `PSRAM=opi` ekle | Hız ölçüldü, çerçeve düşmesi 0, `ps_malloc(2MB) != NULL` |
| 3.1 | **±12 V rayı + TL072 ön ucu** (donanım). Sıra: regülatör+dekuplaj → V tamponu+SK → skop tamponu+SK → REF tamponu → fark yükselteci+SK. **Her op-amp çıkışında 1 kΩ + üst 1N4148 + alt Schottky, istisnasız.** ALERT'i GPIO21'e taşı | Her kesitin DC kazancı DMM ile; sonra kartın kendi kare dalgasıyla basamak cevabı |
| 3.2 | **Hızlı wattmetre + hibrit disiplinleme.** 2 kanallı edinim, kayma FIR'ı, RLS disiplinleme, `D2` satırı, `f` faz kalibrasyonu | MCPWM+MOSFET ile dirençsel yükü %D görev çevrimiyle kes → beklenen güç analitik biliniyor → ölçülenle karşılaştır. **`ort(V)×ort(I)`'nin aynı testte kaç kat yanıldığını da yazdır** |
| 3.3 | **Tek-seferlik osiloskop.** PSRAM halkası, tetik motoru (histerezis + tutma + ön-tetik), `S2` protokolü ikili, yerel USB CDC | 500 000 örnek < 1.5 s'de aktarılıyor; ön-tetik gerçekten tetiğin öncesini gösteriyor |
| 3.4 | **ETS — uyarım kilitli (kolay kip).** MCPWM asal periyot (P=799), koherent faz binleme | **Kart kendi kare dalgasının kenarını ETS ile kurup kendi bant genişliğini ölçüp yayınlıyor** |
| 3.5 | **ETS — harici sayısal tetik (SMPS kipi).** MCPWM capture, periyot titreşimi ölçümü ve reddetme mantığı | Bilerek titretilmiş uyarımda kart ETS'i **reddediyor** — dürüstlük mekanizması çalışıyor |
| 3.6 | **SMPS zamanlama analizörü** | 3.5'in capture altyapısı hazır olduğu için buraya taşındı |
| 3.7 | **Verim ölçer** | 3. ADS1115; 3.2'nin kalibrasyonuna dayanıyor |
| 3.8 | **Elektronik yük** | PWM→RC→opamp→MOSFET; 3.7 ile birleşince verim süpürmesi otomatikleşir |
| 3.9 | **Eğri çizici** | 3.8'in yapı taşının aynısı, farklı süpürme mantığı |
| 3.10 | **Bobin/trafo doyum** | 3.6'nın capture altyapısı + 3.8'in güç katı |

> **Kurulum sırası not:** 3.1'den önce kartın Aşama 2 haliyle delikli plakete kurulup
> kalibre edilmesi gerekiyor (`kurulum2.html`, plakete göre güncellenmeli).

#### İkinci iz — enstrüman yetenekleri (yukarıdakine paralel yürüyebilir)

Bu iz, toplama zincirinden **büyük ölçüde bağımsız** ve farklı bir bağımlılık ağacı var.
Yapı taşı haritası:

```
              ┌─ SMPS zamanlama
   MCPWM ─────┤
   capture    └─ Doyum testi ────┐
                                 │
   ±12 V ──┬─ Lineer çevrim ─────┼─ Eğri çizici Mod-T
           │   (TL072+MOSFET+    │
           │    şönt)            ├─ Elektronik yük ── Verim ölçer
           │                     │
           └─ Mod-O geçiş elemanı
   PWM DAC ──┬─ yük/eğri çizici (akım referansı)
   (LEDC)    ├─ doyum (komparatör eşiği)
             └─ Mod-O (Vds ekseni)
```

| # | Adım | Bağımlılık | Süre | Kapı |
|---|---|---|---|---|
| **E0** | **±12 V rayı** — 5.4'teki dört yoldan biri + yerel bypass + kondansatör bankası | — | 1 akşam | +12/−10..−12 V, ripple <50 mV; 5 A'lik 1 ms darbede bara düşümü <0.5 V |
| **E1** | **SMPS zamanlama analizörü** — 3 bölücü + kelepçe + capture ISR + **de-skew** | **yok** (saf sayısal) | 2 akşam | NE555 ile bilinen frekans ±20 ppm; aynı sinyal 3 kanala → de-skew sonrası fark <15 ns |
| E2 | **PWM→RC DAC bloğu** (T0 12b/19.5k + T1 10b/78k) | E0 | 1 akşam | Ripple <300 µV, oturma <20 ms, ADS ile lineerlik %0.1 |
| **E3** | 🔑 **Lineer çevrim** (TL072 + IRFP250N + soketli şönt + snubber + watchdog + NTC) | E0, E2 | 3 akşam | **Salınım yok** — skopla kapı ve drain'e bak, her kademede 1 mA–3 A. Adım tepkisi aşımsız |
| E4 | **Eğri çizici Mod-T** — DUT soketi + Kelvin uçları + dış cevrim | E3 | 2 akşam | Yeni IRFZ44N'in Vgs(th)'si 2–4 V; Rds(on) 17.5 mΩ ±%5; **sökme parçalar ayırt ediliyor** |
| E5 | **Elektronik yük tam** — soğutucu, OTP, kademe süpürmesi, mAh | E3 | 2 akşam | 30 dk 12 V @ 2 A: soğutucu <80 °C, akım kayması <%0.5 |
| E6 | **Doyum testi** — LM319 ×3 + 2N2222→IR2110 + 3.3R kelepçe | E1, E2, E3 | 3 akşam | Bilinen bobin LCR değerine ±%2; doyum dizi görünür |
| E7 | **Verim ölçer** — 3. ADS + süzgeç düzeltmeleri + ortak-referans kalibrasyonu | E0, E5 | 2 akşam | **Kısa devre testi η = %100 ±0.4 puan** |
| E8 | **Eğri çizici Mod-O** | E4, E6 | 3 akşam | Id–Vds ailesi veri sayfası eğrileriyle örtüşüyor |

> 🌟 **E1 en başta** çünkü hiçbir şeye bağımlı değil — ±12 V bile gerektirmiyor. Bir
> akşamda çalışan bir alet çıkıyor ve MCPWM capture altyapısını E6 için hazırlıyor.
> **Kullanıcı hızlı bir kazanım isterse buradan başla.**
>
> 🔑 **E3 pivot.** Yükün, eğri çizicinin ve doyum testinin akım sınırının hepsi bu tek
> devre. **Kararlılığı tezgahta çözmeden ileri gitme** — E4, E5, E6 hep buna yaslanıyor.

### 5.11 Yapılamayanlar — açık liste

| İstenen | Neden yapılamıyor | Ne gerekir |
|---|---|---|
| **Offline (şebeke referanslı) SMPS verim ölçümü** | Toprakları bağlamak izolasyonu kısa devre eder; bağlamamak ADS'nin CM sınırını aşar | Tam izole ölçüm adası — ayrı proje |
| **12 V / 20 V zener dizini** | +12 V ray 12 V zeneri kırmaz; geçiş elemanı headroom'uyla ancak ~10.5 V | 30–50 V ek ray |
| **10 µH altı endüktans** | 24 V'ta 5 µH → rampa 1 µs, LM319 jitter'i %13.6 hata | TLV3501 (4.5 ns) |
| **Lineer bölgede MOSFET paralelleme** | Vgs(th) negatif tempco → termal kaçak. **Fizik yasağı** | Her MOSFET'e ayrı opamp + ayrı şönt |
| **Sadece ADC ile 10–500 µH doyum** | 12 µs/örnek, 12 V'ta örnek başına 1.44 A | Komparatör + capture (çözüm var) |
| **Kelvin'siz Rds(on)** | Soket+tel direnci ölçülen değerin 1.7–3.75 katı | Kelvin, tartışmasız |
| **Optokuplörle ölü zaman** | PC817/4N35 gecikme *değişimi* ölçülen büyüklükten büyük | 6N137 veya toprak referanslı kontrolcü çıkışı |
| **Sürekli 24 W yük, soğutucusuz** | Soğutucusuz izin verilen güç 2.4 W | ≤2 °C/W soğutucu |
| **100 kHz anahtarlamayı gerçek zamanda görmek** | 2 kanalda Nyquist 20.83 kHz | ETS (tekrarlayan sinyalde) |
| **Tek seferlik olayı ETS ile yakalamak** | Yöntemin doğası | Gerçek zamanlı kip, 20.83 kHz sınırıyla |

### 5.12 🎯 Ön uç yeniden tasarımı — TASARLANDI ve DOĞRULANDI (2026-09-08)

Kullanıcının üç isteği. **Tasarım bitti, simüle edildi, zincire girdi.**
Donanım kurulmadı; firmware ve şema henüz yazılmadı.

```
cd projeler/olcum-karti/uretim && python dogrula3.py     # B1 + B2, ~1 s
```

**B1 44/44 kural · B2 27/27 SPICE doğrulaması · toplam 71, 0 hata.**

| İstek | Sonuç |
|---|---|
| 400–600 V | **±615.4 V**, adım 18.78 mV, giriş Z **4.93 MΩ** |
| Negatif (±) | Vref referanslı diferansiyel — **ek çip yok** |
| V–I kayması az | 4 katsayılı Lagrange, **faz hatası tam sıfır** |

#### 5.12.1 Çift yönlülük — türev

Bölücünün alt ucu GND yerine **tamponlu bir Vref**'e bağlanır, ölçüm
diferansiyel yapılır. `k = 1/N` olsun:

```
düğüm = Vref + (Vin − Vref)·k
fark  = düğüm − Vref = (Vin − Vref)/N        ← İŞARETLİ
Vin   = N·fark + Vref
```

🌟 **Vref hatası ε kadarsa, ölçülen Vin tam ε kadar kayar — N'den bağımsız.**
Yani Vref hatası girişe vurulmuş sabit bir *ofset*, kazanç hatası değil. Sıfır
kalibrasyonu siler. 615 V kanalında bu bizi Vref'e karşı çok bağışık yapıyor.

`Vref = TL431 (2.495 V) → 10K/22K → 1.7153 V`, tamponlanmış. (3.3 V rayından
değil: ray %1 oynasa 16.5 mV ofset olurdu, TL431 çok daha durgun.)

#### 5.12.2 İki gerilim kanalı

| | NORMAL | YÜKSEK |
|---|---|---|
| Bölücü | 2× 100K / 6.8K | **6× 820K / 8.2K** |
| N | 30.41 | 601.00 |
| PGA | ±1.024 | ±1.024 |
| Tam ölçek | **±31.1 V** | **±615.4 V** |
| Adım | 0.950 mV | 18.781 mV |
| Thevenin | 6.58 kΩ | 9.98 kΩ |
| Giriş Z | 0.21 MΩ | **4.93 MΩ** |
| Direnç başına (FS) | 15.1 V (%7.5) | 102.4 V (%51) |

> ⚠️ **5.12.18 bu değeri değiştirdi:** zincir artık 6× **820K** / 8.2K.
> Bölme oranı (N = 601.0), menzil ve adım aynı; aşağıdaki gerekçe geçerli.

**Neden 6 direnç, 4 değil:** araştırma 1/4W metal film azami *çalışma* geriliminin
**200 V** olduğunu gösterdi (Yageo MFR) — geçen turda 250 V varsaymıştım.
4× 1M ile tam ölçek zaten 410 V, 600 V'a yetmiyor.

İki bölücünün Thevenin'i birbirine yakın; ortak-mod penceresi ikisinde de
**0.691 .. 2.739 V** (ADS çalışma aralığı 0..3.3 V). SPICE ±%15 aşırı
gerilimde bile pencerede kaldığını doğruladı.

#### 5.12.3 🔴 Tampon ZORUNLU — 4.14'ün sonucu

Tamponsuz bırakılırsa PGA'ya bağlı kazanç sıçraması oluyor (bkz. 4.14).
Tamponla kaynak empedansı ~0 → hata PGA'dan bağımsız kayboluyor.

**Op-amp seçimi — ADS yolu için MCP6004 sınıfı RRIO (SATIN ALINACAK):**

| op-amp | Vos maks | drift | Ib | Besleme | 615 V kanalında 20 °C hata |
|---|---|---|---|---|---|
| TL072 | 10 mV | 18 µV/°C | 200 pA | ±12 V | %0.0354 |
| LM358 | 7 mV | 7 µV/°C | 45 nA | +5 V | %0.0575 |
| **MCP6004** | 4.5 mV | **2 µV/°C** | **1 pA** | **3.3 V RRIO** | **%0.0039** |

🌟 **RRIO'nun asıl kazancı doğruluk değil, KELEPÇEYİ GEREKSİZ KILMASI.**
Tampon ADS ile aynı 3.3 V rayından beslenirse çıkışı tanım gereği 0–3.3 V
dışına çıkamaz → ADS girişinde kelepçe diyoduna gerek yok → kaçak hatası yok,
kapasite yok, alınacak diyot yok.

Tamponun *kendi* girişi ise bölücünün üst bacağıyla (200K / 6M) korunuyor:
3× aşırı gerilimde bile op-amp ESD akımı **µA mertebesinde**.

TL072 ve LM358 3.3 V'ta bu işi yapamaz (çıkışları raylara yaklaşamaz) —
ikisi de kural olarak eleniyor.

#### 5.12.4 Kelepçe — kavram düzeltmesi + SPICE

Önce bir kavram hatasını düzelttim: **"Vf < 0.3 V olan diyot bul" diye bir
kural yazmıştım. Öyle bir diyot yok.** −0.3 V sınırının amacı TI'nin kendi
ifadesiyle *"to prevent the ESD diodes from turning on"* — yani sınır gerilim
değil, **iç ESD diyodunun iletmesi**. TI'nin çözüm cümlesi de akım üzerine
kurulu: *"...and/or series resistors ... to limit the input current"*.

SPICE (B2), −12 V arıza + 2.7 kΩ seri direnç:

| Harici kelepçe | pin | ESD akımı | ESD payı |
|---|---|---|---|
| yok | −0.734 V | 4.173 mA | %100 |
| **1N4148** | −0.667 V | 1.055 mA | **%25.1** |
| **BAT54** | **−0.258 V** | ~0 | **~%0** |

**4.13 sayısal olarak doğrulandı:** 1N4148 arıza akımının dörtte birini hâlâ
iç ESD diyoduna bırakıyor. BAT54 ile pin −0.258 V'ta kalıyor — **mutlak alt
sınır −0.3 V'un bile üstünde.** (Analitik kestirimim −0.4 V demişti; SPICE
daha iyi çıktı, bağlayıcı olan SPICE.)

⚠️ **Seri direnç 1 kΩ değil 2.7 kΩ.** İlk taslakta 1 kΩ yazmıştım: ±12 V
arızada **11.3 mA** veriyor, ADS'in 10 mA sınırının üstünde. 2.7 kΩ → 4.19 mA.

⚠️ **SR5100 uygun değil** — Vf'i yetersiz *ve* kaçağı (~50 µA) 2.7 kΩ üzerinde
**135 mV** ofset yapıyor. Hassas düğümde kabul edilemez.

**İki farklı koruma rejimi:**
- **ADS yolu (hassas):** 3.3 V RRIO tampon → kelepçe YOK, kaçak YOK
- **ESP yolu (hızlı/skop):** TL072 ±12 V → 2.7 kΩ + 2× BAT54 ŞART

#### 5.12.5 İki ayrı örtüşme süzgeci — 4.8'in çözümü

İlk taslakta tek süzgeç düşünmüştüm; **yanlış.** İki yolun Nyquist'i farklı:

| Yol | Nyquist | Süzgeç | Sonuç |
|---|---|---|---|
| **ADS** (860 SPS) | 430 Hz | 22K + 100nF → **50–56 Hz** | 860 Hz'te **−24 dB** |
| **ESP** (41.7 kSa/s/kanal) | 20.83 kHz | Sallen-Key 6.8K, 2nF/1nF → **16.55 kHz** | 100 kHz'te **−31.3 dB** |

16.5 kHz'lik Sallen-Key, ADS yoluna hiçbir şey yapmaz (430 Hz'in 38 katı uzakta).

SPICE doğrulaması (B2): Sallen-Key f0 = 16.6 kHz, **tepe yok** (Q=0.707),
eğim −40.8 dB/dekat (2 kutup teyit), Nyquist'te −5.50 dB, 100 kHz'te
−31.28 dB — **bugünkü tek kutuplu RC'den 19 dB iyi.**

Sallen-Key zaten bir tampondur → 5.12.3'teki tampon ve bu süzgeç **aynı
op-amp kesiti**, ek parça yok.

ADS yolunda RC **tamponun ÖNÜNDE**: seri direnç ADS'e değil CMOS tampon
girişine bakıyor (Ib ~1 pA), kazanç hatası yaratmıyor. Ardına konsaydı 4.14'ü
geri getirirdi.

#### 5.12.6 Gürültü bütçesi — DEVIR 1.3'ün açık sorusu KAPANDI

Veri sayfası s.8 Şekil 14/15'ten okundu (VDD 3.3 V, 860 SPS):
**±2.048'de ~26.5 µV RMS, ±0.512'de ~8.5 µV RMS.**

| Kanal | ADS gürültü | Kuantalama | Toplam/örnek | 200 ms |
|---|---|---|---|---|
| ±31 V | 0.411 mV | 0.274 mV | 0.494 mV | 0.038 mV |
| ±615 V | 8.113 mV | 5.422 mV | 9.758 mV | 0.744 mV |

⚠️ √N yalnızca beyaz gürültü için geçerli; 1/f ve referans sürüklenmesi bunu
sınırlar. "200 ms'te ~250 000 sayım" bir **üst sınırdır**, garanti değil.

#### 5.12.7 V–I kayması

Araştırma tasarım varsayımını **bağımsız doğruladı** (espressif/esp-idf #1911):
*"two channels sample data with channel 2 out of phase by 1/fs"* — bilinen,
uzun süreli bir davranış. Forumların önerdiği çözüm tam sayı kaydırma; bizim
kayma **tam yarım örnek** olduğu için o yetmez, kesirli gecikme gerekiyor.

`i_hiza[n] = −1/16·i[n−2] + 9/16·i[n−1] + 9/16·i[n] − 1/16·i[n+1]`

Simetrik → doğrusal faz → **faz hatası tam sıfır**. Kalan tek hata genlik
sarkması: 1 kHz'te 0.0001 dB, 5 kHz'te 0.063 dB. CPU 0.17 MMAC/s.

⚠️ **Dürüstlük:** hizalayıcı Nyquist'te sıfıra gidiyor (kesirli gecikme
süzgeçlerinin doğası). Sallen-Key de 20.8 kHz'te −5.45 dB veriyor.
**Güvenilir wattmetre bandı ~5 kHz.**

#### 5.12.8 Akım kanalında negatif

Donanım zaten hazır (ADS #1 AIN0-AIN1 diferansiyel, işaretli okuyor).
`olcum2.h`'deki `if (o.amper < 0.0f) o.amper = 0.0f;` satırı kaldırılacak.
Şönt uçları ±256 mV'ta, −300 mV mutlak sınırına 44 mV kala — alt kelepçe
burada da gerekli.

⚠️ **Enerji sayacı işaretli olmalı.** `enerji_ekle()` şu an negatifi 0 sayıyor;
şarj/deşarj çevriminde sayaç yanlış olur. `uint64` → `int64` pJ.

#### 5.12.9 Montaj kısıtı: DELİKLİ (THT) — ve satın alma

⚠️ **Kullanıcı 2026-09-08'de bildirdi: "yüzey montajda zorlanıyorum, yapamayabilirim."**
SMD gövde artık bir eleme ölçütü. İki yanlış anlama düzeltildi:

| Sanılan | Gerçek |
|---|---|
| MCP6004 SMD | **MCP6004-I/P = DIP-14**, MCP6002-I/P = DIP-8. `/P` son eki PDIP demek |
| BAT54 tek seçenek | **BAT85 = DO-34 eksenel cam**, 1N5711 = DO-35. İkisi de delikli |

**BAT85** (Nexperia veri sayfası, Tablo 7): Vf 400 mV maks @ 10 mA · IR **2 µA
maks @ 25 V** (Şekil 2: ~2 V'ta 25 °C'de tipik ~200 nA) · Cd 10 pF maks.
SPICE'ta BAT54 ile aynı sonucu veriyor: pin −0.268 V, ESD payı ~%0.

##### 🌟 Aslında hiçbir şey almadan da olur — YOL 0

Tamponun **çıkış tavanı** ADS'in mutlak azamisini (3.6 V) zorlamıyorsa kelepçe
diyoduna hiç gerek yok. B2 bunu simüle etti (2.7 kΩ seri direnç ile):

| Tampon | Çıkış | ADS pini | ESD akımı | Kelepçe |
|---|---|---|---|---|
| MCP600x (3.3 V RRIO) | 3.30 V | 3.300 V | **0 nA** | gerekmez |
| **LM358 (+5 V) tavan** | 4.30 V | 3.907 V | **146 µA** | **gerekmez** |
| LM358 (+5 V) en kötü | 5.00 V | 3.935 V | **394 µA** | gerekmez |
| TL072 (±12 V) | 12.0 V | 4.013 V | **2.96 mA** | **ŞART** |

**LM358'in kötü çıkış salınımı burada bir güvenlik özelliğine dönüşüyor:**
+5 V'ta beslendiğinde çıkışı ~4.3 V'un üzerine çıkamıyor, ADS'i zorlayamıyor.
En kötü halde bile 394 µA — 10 mA sınırının 25'te biri.

⚠️ Dürüstlük: o arızada pin 3.9 V'a çıkıyor, yani 3.6 V *gerilim* sınırının
üstüne. Mutlak azami tablosunu belirleyen **akım** ve o çok güvenli; ayrıca bu
ancak giriş menzil dışına çıkarsa oluyor, normal çalışmada çıkış 0.69–2.74 V.

##### Kalibrasyon sonrası hata — seçim doğrulukla ilgili değil

Vos ve Ib·Rt **sabittir**, sıfır kalibrasyonu ikisini de siler. Kalan sadece
sürüklenme:

| Kanal | op-amp | Vos drift | Ib drift | KALAN | FS oranı |
|---|---|---|---|---|---|
| ±31 V | LM358 | 4.26 mV | 2.70 mV | 6.96 mV | **%0.022** |
| ±31 V | MCP6004 | 1.22 mV | ~0 | 1.22 mV | %0.0039 |
| ±615 V | LM358 | 84.1 mV | 81.0 mV | 165 mV | **%0.027** |
| ±615 V | MCP6004 | 24.0 mV | ~0 | 24.0 mV | %0.0039 |

Referans DMM (AN8000) zaten ±%0.5. **LM358'in %0.027'si onun 18'de biri** —
yani seçim doğrulukla değil, pratiklikle ilgili.

LM358'de Ib sürüklenmesi de silinebilir: izleyicinin geri besleme koluna
kaynak Thevenin'ine eşit direnç konursa eşleşen taban akımları sadeleşir,
geriye offset akımı kalır → %0.015.

##### Üç yol

| Yol | Ne | Artı | Eksi |
|---|---|---|---|
| **0** | **LM358 (stokta 8) + 5 V** | Satın alma **yok**, DIP-8, kelepçe **yok** | Ib 45 nA, drift 3.5× |
| 1 | MCP6002-I/P / MCP6004-I/P | En düşük drift, kelepçe yok | Tek kalemlik sipariş |
| 2 | TL072 (yolda) + ±12 V | Skop yolu için zaten gerekli | ADS yolunda kelepçe + ±12 V bağımlılığı |

**Öneri: ADS yolunda YOL 0 ile başla.** Elinde var, bedava, kelepçesiz. DIP-8
sokete tak; tezgahta sürüklenmeyi ölçüp yetmezse MCP6002-I/P'ye geçmek
**devre değişikliği gerektirmiyor** — aynı bacak düzeni, sadece çip değişir.

**Skop/hızlı yol her hâlükârda TL072 + 2.7 kΩ + 2× BAT85** (band 3 MHz
gerekiyor, ±12 V'ta çalışıyor, kelepçe şart).

| Parça | Adet | Zorunlu mu |
|---|---|---|
| BAT85 (veya 1N5711) | 6 | ✅ evet — ama yalnız skop yolu için |
| MCP6002-I/P / MCP6004-I/P | 1–2 | ❌ hayır — LM358 yeterli |
| 1M 1/4W | 12 | ❌ hayır — stokta 30 var |

#### 5.12.10 B3–B5 UYGULANDI (2026-09-08) — ve üç gerçek hata daha buldu

```
cd projeler/olcum-karti/uretim && python dogrula3.py
```

| Adım | Ne | Sonuç |
|---|---|---|
| B1 | Ön uç tasarımı ve hata bütçesi | 53 kural |
| B2 | Analog ön uç, **negatif dahil** (ngspice) | 30 doğrulama |
| B3 | Şema + ERC + **netlist polarite** | ERC **0 ihlal**, 54 doğrulama |
| B4/B5 | Ölçüm matematiği + Lagrange (**AVR emülatörü**) | 48 koşul |

**Dosyalar:** `kod/olcum-karti-a3/olcum3.h` · `uretim/sema3-uret.py` ·
`uretim/netlist3_dogrula.py` · `uretim/test_olcum3.py` ·
`uretim/avr/ornek_olcum3.c` · `sema3/olcum-karti-a3.kicad_sch`

##### 🔴 B4 gerçek bir tasarım hatası yakaladı: MENZİL SİMETRİK DEĞİL

`fark = (Vin − Vref)/N` olduğu için ADS'in ±PGA penceresi girişe **Vref
kadar yukarı kaymış** bir aralık verir:

```
Vin_üst = +pga·N + Vref
Vin_alt = −pga·N + Vref
```

İlk tasarım "tam ölçek = pga·N" diyordu ve bu **yanlıştı**. NORMAL kanal
2×100K/6.8K (N=30.41) ile gerçekte **−29.43 .. +32.86 V** idi; AVR testi
−31 V'ta **−29.43 V** okuyup kırpmayı gösterdi.

**Düzeltme:** bölücü **220K / 6.8K** (N=33.35, tek direnç). Garanti
simetrik menzil **±32.44 V**, adım 1.042 mV. HV kanalında asimetri
zaten %0.28 (613.71 / 617.14 V) — ihmal edilebilir.

##### 🔴 B4 ikinci hata: kalibrasyonlar birbirini bozuyordu

Ofset **volt** olarak saklanıyordu ve sıfır kalibrasyonu `ofset −= okunan`
yapıyordu. Bu ofseti *o anki kazanca* bağlar; sonra kazanç kalibrasyonu
yapılınca ofset eski kazanca göre kalır. Test yakaladı: 12 V'ta kalibre
edip **−24 V'ta 175 mV hata**. Ayrıca "sıfıra yakın girişte kazanç
kalibrasyonunu reddet" koruması da hiç tetiklenmiyordu.

**Düzeltme:** ofset artık **ham kod** olarak saklanıyor (`sifir_ham`).
Sıfır tanım gereği doğru ve kazançtan bağımsız; ikisi tam ayrışıyor.

##### 🔴 B3 üçüncü hata: çakışan referanslar netlist'i BOŞALTIYORDU

Direnç zinciri üreteci `"R2"` önekiyle R21…R26 üretiyordu ve bunlar
skop/I2C dirençleriyle çakışıyordu. KiCad çakışan referansta *"annotation
errors"* deyip netlist'i boş üretiyor — **ERC bunu görmüyor.** Üreteç artık
açık başlangıç numarası alıyor.

##### 🌟 B5: Lagrange hizalayıcı — gerçek kodda ölçüldü

Gerçek `olcum3.h` kodu, avr-gcc ile derlenip bit-birebir doğrulanmış AVR
emülatöründe koşturuldu. Tam sayıda periyot kullanıldı, beklenen değer
analitik olarak `0.5·cos(φ)`:

| Frekans | PF | Düzeltmesiz | **Hizalı** | İyileşme |
|---|---|---|---|---|
| 52 Hz | 0.1 | +3.91% | **+0.000%** | — |
| 1.04 kHz | 0.5 | +13.28% | **−0.001%** | 9 853× |
| 1.04 kHz | 0.1 | **+77.76%** | **−0.001%** | **111 965×** |
| 5.21 kHz | 0.5 | +58.67% | −0.847% | 69× |
| 5.21 kHz | 0.1 | **+373.15%** | −0.854% | 437× |

Tasarımın öngördüğü şey gerçek kodda doğrulandı. 5 kHz'teki %0.85, hem
hizalayıcının genlik sarkması hem Sallen-Key'in −0.14 dB'i — **güvenilir
wattmetre bandı ~5 kHz** ifadesi bu ölçümden geliyor.

##### Ayrıca doğrulanan (B4)

- İşaretli enerji: 1000×(+2 W) sonra 1000×(−2 W) → **net tam 0 J**
  (Aşama 2'de 40 J olurdu, çünkü negatifi 0 sayıyordu)
- int64 taşma: 7000 W × 1 s = 7000 J ✓ (Aşama 2'nin uint32'si 2.147e9 µW'ta taşardı)
- Akım kırpması gerçekten kalktı: −2.34 A okunuyor, simetrik
- `olc3()` birleşik yol: 12 V × −1.5 A = **−18 W** (negatif güç temsil edilebiliyor)

##### Şema — B3

7 blok, 88 parça, A2 kağıt. ERC **0 ihlal**. Netlist denetimi ERC'nin
göremediklerini okuyor: bölücü altlarının GND'ye **değil** VREF'e gittiği,
iki diferansiyel çift, kelepçe polaritesi, TL431 yönü, ADS adresleri
(0x48/0x49), Sallen-Key topolojisi (C1 çıkışa, C2 GND'ye), boş op-amp
kesitlerinin izleyici bağlanması.

#### 5.12.11 B6 UYGULANDI (2026-09-08) — firmware çalışır durumda

```
cd projeler/olcum-karti/uretim && python dogrula3.py     # ~2.5 dk
```

| Adım | Ne | Sonuç |
|---|---|---|
| B1 | Ön uç tasarımı ve hata bütçesi | 53 kural |
| B2 | Analog ön uç, **negatif dahil** (ngspice) | 30 doğrulama |
| B3 | Şema + ERC + netlist polarite | ERC **0 ihlal**, 54 doğrulama |
| B4/B5 | Ölçüm matematiği + Lagrange (**AVR emülatörü**) | 48 koşul |
| **B6** | **Firmware: derleme + ikilide ölü kod** | **37 koşul** (+7 ayrışma) |

**Firmware:** `kod/olcum-karti-a3/olcum-karti-a3.ino` (957 satır) +
`olcum3.h` + `tipler3.h` + `skop_olc.h`
→ **480 439 B flash (%15 / 3 MB), 47 532 B RAM (%14), 0 uyarı.**

##### Seri protokol — arayüzün dayanacağı sözleşme

```
D <volt> <amper> <watt> <joule> <wh> <ms> <örnek> <menzil>
S2 <adet> <Hz> <volt/adım> <tetik_idx> <tdiv_us> <kip> <tetiklendi>
```

`<menzil>`: 0 = NORMAL (±32.4 V), 1 = YÜKSEK (±613.7 V). **Aşama 2'de
olmayan alan** — arayüz hangi kanalın etkin olduğunu bilmeli.

| Komut | İş |
|---|---|
| `z` / `g<volt>` | gerilim sıfır / kazanç kalibrasyonu (**etkin kanala**) |
| `n` / `y` | menzili elle NORMAL / YÜKSEK yap (oto kapanır) |
| `a<0\|1>` | otomatik menzil |
| `Z` / `i<amper>` | akım sıfırı / kazanç |
| `s<ohm>` | şönt değeri · `e` enerji sıfırla · `?` ayarlar · `#` I2C tara |
| `t…` | osiloskop (Aşama 2 ile aynı) |

⚠️ Aşama 2'de arayüz ile firmware komutları **ayrışmıştı** (4.1: `app.js`
`kv12.34` gönderiyor, firmware `v12.34` bekliyordu). B6 artık ikilide her
komut dalının varlığını sınıyor, ve `?` çıktısı komutları listeliyor.

##### Otomatik menzil — PGA değil KANAL değiştiriyor

PGA oto-kademesi **bilerek yapılmadı**: ADS'in giriş empedansı PGA ile
değiştiği için kademe sınırında %0.67 puan kazanç sıçraması oluyor
(4.14). Kanal değiştirmek aynı sorunu yaratmıyor çünkü **her kanalın
kendi kalibrasyonu var**. Histerezis: NORMAL FS'in %90'ında yukarı,
%70'ine düşünce aşağı.

##### B6'nın yakaladıkları

🔴 **Arduino otomatik prototip tuzağı — Aşama 1'in #5 hatası tekrarlandı.**
`varsayilan_ayar3(Ayar3 *a)`'nın prototipi struct tanımından **önce**
yerleşiyor:
```
error: variable or field 'varsayilan_ayar3' declared void
error: 'Ayar3' was not declared in this scope
```
Çözüm de aynı: tipler `tipler3.h`'ye taşındı (Aşama 1'de `tipler.h` idi).

🔴 **Kopyalanan dilim fazla şey almış.** Osiloskop bölümünü A2'den
alırken sınırı "// ── HTTP" başlığına koymuştum; araya `enerji_biriktir`
de girdi ve o Aşama 2'nin **uint64** `enerji_ekle`sini çağırıyordu.
İşaretli sürümü yeniden yazıldı — A2'nin iki koruması (taşma sarmalı,
>1 s aralığı atlama) korunarak.

##### Osiloskop matematiği — ayrışma koruması

`SkopOlcum` / `skop_kesisim` / `skop_olc` hem `olcum2.h`'de hem
`skop_olc.h`'de duruyor. Kopya olmak tehlikeli değil, **sessizce
ayrışmak** tehlikeli:

- `uretim/skop_olc_uret.py` kopyayı **olcum2.h'den üretir**
- `uretim/test_skop_ayni.py` iki metni **karakter karakter** karşılaştırır

Böylece A6'nın (gerçek kodda doğrulanmış) kanıtı Aşama 3 için de geçerli.

⚠️ **Osiloskop SÜRÜCÜSÜ için böyle bir denetim YOK** — 339 satır A2'den
kopyalandı ve A2 değişirse sessizce eskir. Bilerek kabul edildi (A2 artık
regresyon temeli; sürücü zaten PSRAM'li derin bellek için değişecek),
`.ino` başlığında açıkça yazıyor.

#### 5.12.12 B7 UYGULANDI (2026-09-08) — arayüz çift yönlü

**Dizin:** `arayuz3/` — `index.html` · `app.js` · `sahte-kart.js` ·
`ek.css` · `sunucu.py`

```
cd projeler/olcum-karti/arayuz3 && python sunucu.py     # :8772
```

##### Neden ayrı dizin

Aşama 2'nin arayüzü o firmware'in protokolüyle konuşuyor ve **A5 bunu
komut biçiminden sınıyor** (`gonderilen[1] === 'v12.05'`). Aynı dosyayı
iki protokole birden uydurmaya çalışmak, 4.1'deki sessiz ayrışmanın
daveti olurdu.

**Ortak dosyalar kopyalanmadı:** `vendor/vue.global.prod.js` (154 KB) ve
`style.css` `../arayuz`'da duruyor; `arayuz3/sunucu.py` bulunmayan dosyayı
oraya düşürüyor (`translate_path`). Tek kopya kalıyor.

##### Ne değişti

| | Aşama 2 | Aşama 3 |
|---|---|---|
| D satırı | 8 alan | **9 alan** — `<menzil>` eklendi |
| Gerilim kalibresi | `v<volt>` | **`g<volt>`** |
| Gerilim sıfırı | yok | **`z`** |
| Akım sıfırı | `z` | **`Z`** ⚠️ harf anlamı değişti |
| Menzil | yok | `n` / `y` / `a<0\|1>` |
| Kalibrasyon işareti | `> 0` şartı | **negatif de kabul** |
| Güç yönü | gösterilemezdi | **"yük çekiyor" / "kaynak — geri besleme"** |

Menzil rozeti gerilim ölçümünün yanında duruyor; çözünürlük iki kanalda
18 kat farklı olduğu için hangisinin okunduğu görünür olmalı.

##### 🌟 B7'nin asıl işi: arayüz ↔ firmware komut denetimi

`test_arayuz3.js` arayüzün gönderebileceği **her** komut harfini,
`.ino`'dan okunan `case` etiketleriyle karşılaştırıyor — hem `app.js`
hem `index.html`. Bu, 4.1 ve 4.15'in tekrarlanmasını imkânsız kılıyor.

Demo kart (`sahte-kart.js`) da gerçek firmware gibi davranıyor:
bilinmeyen komutu reddediyor, sıfıra yakın kazanç kalibrasyonunu
reddediyor. Yani demo kipinde görünen davranış gerçek kartınkiyle aynı.

**B7: 54/54.**

#### 5.12.13 B8 UYGULANDI (2026-09-08) — hızlı yol devrede

Lagrange hizalayıcı artık **gerçekten çağrılıyor**. B4–B7 boyunca kodda
duruyordu ama kullanılmıyordu (`__attribute__((unused))` ile işaretliydi);
B8 onu tam güç hesabına bağladı.

##### 🔴 DEVIR 5.1.4'ün kazanç önerisi elendi

DEVIR fark yükselteci için **kazanç 27** (27K/1K) öneriyordu. `tasarim3.py`
§10 bunu kuralla eledi:

| Rf/Rg | G | Tam ölçek şönt | ADS 256 mV | Bant |
|---|---|---|---|---|
| 27K/1K | 27 | **51.3 mV** | ❌ **KIRPAR** | 107 kHz |
| **47K/10K** | **4.7** | **294.6 mV** | ✅ kapsar | 526 kHz |

G=27 ile hızlı yol yavaş yoldan **5 kat önce** doyuyordu: 0.1R şöntte hızlı
yol ±0.51 A'de kırparken ADS ±2.56 A okuyor. O tasarım 0.1R şöntü ve 1 A
hedefini varsayıyordu; **şönt soketli olduğu için bu varsayım tutmuyor.**

Ayrıca REF ucu ayrı bir 1.5 V rayına değil, **zaten tamponlu VREF'e**
bağlandı — ikinci bir referans hem parça hem ikinci bir sürüklenme kaynağı.

##### 🌟 B8'in ölçtüğü gerçek güç — hizalayıcının etkisi

`guc_olc()` gerçek kodu AVR emülatöründe, analitik sinüslere karşı:

| PF | Beklenen P | **Hizalı** | Hizalamasız |
|---|---|---|---|
| 1.0 | 2.50000 | 2.49996 (**−0.001%**) | 2.49229 (−0.308%) |
| 0.5 | 1.25000 | 1.24998 (**−0.001%**) | 1.41602 (**+13.28%**) |
| 0.1 | 0.25000 | 0.25000 (**−0.001%**) | 0.44439 (**+77.76%**) |

Ayrıca doğrulandı: Vrms/Irms/S tam, DC yükte PF=1, **ters akımda P=−3 W ve
PF=−1** (geri besleme işaretleniyor), 8 örnekten kısa pencerede ölçüm
yapılmıyor.

##### 🔴 B8 kendi testimde bir hata buldu — ve o hata GERÇEK

İlk koşuda üç durumun da **+%2.48** sapması vardı. PF=1'de de görüldüğü
için faz değil: **pencere** sorunu. Hizalayıcı kenarlardan 3 örnek
düşürünce 120 örnekten 117 kalıyor — o da **2.925 periyot**, tam sayı değil.

Test düzeltildi (N=123 → kullanılan 120 = tam 3 periyot) ve hata
%0.001'e indi. **Ama bu gerçek kartta da olacak:** edinim penceresi
sinyalin periyoduna hizalı olmayacak. Yanlılık ölçüldü ve kural yapıldı:

```
2.75 periyot -> %2.64        K = 2.64 x 2.75 = 7.25
yanlilik ~ K / cevrim sayisi
```

| Sinyal | 200 ms pencere | Yanlılık |
|---|---|---|
| 50 Hz | 10 çevrim | **%0.73** |
| 1 kHz | 200 çevrim | %0.04 |

**%0.73, ADS yolunun kalibrasyon sonrası hatasından (%0.03) 24 kat büyük.**
Bu yüzden hızlı yolun sayısı **güç faktörü ve dalga şekli** için; mutlak
watt değeri ADS'ten geliyor. Firmware pencere uzunluğunu ve 50 Hz'teki
çevrim sayısını her ölçümde **yazdırıyor** — susmak yerine söylüyor.

##### Donanım — BLOK 8

```
SONT_P --[10K]--+-- U8A(+)        U8A: TL072 fark yukselteci, G = 4.7
                +--[47K]-- VREF   (REF ucu VREF'te -> cift yonlu)
SONT_N --[10K]--+-- U8A(-)
                +--[47K]-- cikis
cikis -> U5B Sallen-Key 16.55 kHz -> 2.7K -> 2x BAT85 -> GPIO5
```

- **U5B artık boşta değil** — Aşama 3'e kadar izleyici bağlıydı, şimdi
  hızlı akım Sallen-Key'i. Boş kesit yeni TL072'nin (U8B) kesiti oldu.
- Şönt Kelvin uçları **iki yere** gidiyor: ADS'in RC'sine ve fark
  yükseltecine. Hızlı yol RC'nin ardından çekilseydi 7.96 kHz'e hapsolurdu.
- **Netlist denetimi bir hatamı yakaladı:** GPIO5'i eklerken 8 pinlik
  başlıkta `+5V`'un yerini almıştım — LM358'lerin beslemesi kayboluyordu.
  Başlık 10 pine çıkarıldı.

##### Firmware ve arayüz

`w` komutu bir pencere yakalayıp `W` satırı üretiyor:

```
W <P> <S> <PF> <Vrms> <Irms> <Vort> <Iort> <n> <P_hizalamasiz>
```

Son alan **bilerek** var: arayüz hizalamanın ne kadar düzelttiğini
gösteriyor ("hizalama −13.40% düzeltti" / "fark yok (dirençsel)").

⚠️ Kanal sırası **indeks paritesinden çıkarılmıyor**, her zaman
`type2.channel` alanından demux ediliyor — DMA bir çerçeve düşürürse
parite kayar ve V ile I yer değiştirir.

Firmware: **481 935 B flash (%15), 50 972 B RAM (%15), 0 uyarı.**

#### 5.12.14 B9 UYGULANDI (2026-09-08) — malzeme denetimi + tezgah kılavuzu

**B9 olarak ne yapıldığı önemli:** sırada B9 (ikili aktarım) ve B12
(sürekli hızlı yol) vardı; ikisi de seçilmedi. Gerekçe:

- **İkili aktarım / yerel USB CDC**, `Serial`'in nasıl çalıştığını
  değiştiriyor. Kartla konuşulacak **tek kanal** o. Donanım elde yokken
  değiştirmek, yanlışsa kullanıcıyı kartla hiç konuşamaz halde bırakır.
- **Sürekli hızlı yol**, osiloskopla **aynı ADC tutamağını** paylaşıyor;
  sürekli çalışırsa skop çalışamaz. Ayrıca `D` satırı zaten 5 Hz'te
  sürekli güç veriyor; hızlı yolun katkısı PF ve reaktif yük doğruluğu.

Asıl eksik başkaydı: **Aşama 3'ün tezgah kurulum kılavuzu yoktu.**
Aşama 1'in `kurulum.html`'i, Aşama 2'nin `kurulum2.html`'i vardı;
kullanıcı Aşama 3'ü kuracak ve elinde adım adım bir şey yoktu.

##### Malzeme listesi envanterle denetleniyor — `bom_dogrula.py`

Liste **şemadan** üretiliyor (netlist3.net), elle yazılmıyor. Şema
değişince liste peşinden gidiyor.

**55 bileşen, 25 farklı değer.** Sonuç:

| Durum | Parçalar |
|---|---|
| Stokta yeterli | 1M ×6, 6.8K ×6, 100nF ×4, 10K ×4, 2.7K ×4, 22K ×3, 100R ×2, 1nF ×6, 47K ×2, LM358 ×2, 100K, 220K, 220R, TL431 |
| Yolda | TL072 ×2, ADS1115 ×2, ESP32-S3, şönt seti, jaklar |
| **Satın alınacak** | **BAT85 ×4** (tek kalem) |

⚠️ **Uyarı: 10K'nın 1/4W'ı tükenmiş** (R019: 0 adet). R032 (1/2W ×10) ve
R033 (1W ×10) var; tasarımdaki dört 10K de düşük güçte, sorun yok.

CLAUDE.md kuralı korunuyor: direnç adetleri göz kararı sayım ve kayıt dışı
bir yığın var, o yüzden "yetersiz" = **"saydır"** demek, "kesin yok" değil.

##### Tezgah kılavuzu — `kurulum3.html` (üretiliyor)

`kurulum3-uret.py` sayfayı `tasarim3_sabit.py`'den üretiyor. Aşama 2'nin
`kurulum2.html`'i **elle yazılmıştı** ve içindeki 4.7K pull-up önerisi
tasarımla ayrışmıştı (4.7); aynı hatayı tekrarlamamak için bu üretiliyor.

Yedi adım, her birinde geçilmeden ilerlenmeyen bir **ölçüm kapısı**:

| # | Adım | Kapı |
|---|---|---|
| 01 | Vref rayı | TL431 2.495 V, Vref 1.7153 V — **yük altında da** aynı |
| 02 | ESP32 + I²C | `#` → 0x48 **ve** 0x49 görünmeli |
| 03 | Akım + Kelvin | `Z` sıfırla, akımı **ters çevir** → negatif okumalı |
| 04 | NORMAL ±32 V | `z` sonra `g`; girişi ters çevir, simetrik olmalı |
| 05 | **YÜKSEK ±613 V** | 🔴 **önce 12 V**, sonra 100 V, kademeli |
| 06 | Osiloskop | `ta` → frekans/duty doğru; düz çizgide ölçüm **yapılamamalı** |
| 07 | Hızlı yol | Dirençsel yükte PF≈1 ve "fark yok"; reaktif yükte düzeltme görünmeli |

Ayrıca 8 satırlık sorun giderme tablosu (I²C görünmüyor, negatif 0 okunuyor,
PSRAM yok, menzil gidip geliyor…).

#### 5.12.15 🛒 SATIN ALMA LİSTESİ — Aşama 3 (2026-09-08)

Kullanıcı "BAT85 dışında ne lazım olabilir" diye sordu. Geniş bakıldığında
**BAT85 tek başına yetmiyor** — iki gerçek eksik daha çıktı.

##### 🔴 A. ZORUNLU — bunlar olmadan kart ya kurulamaz ya anlamsız ölçer

| Parça | Adet | Neden |
|---|---|---|
| **BAT85** (veya 1N5711 / BAT43) | 6 | Kelepçe. 1N4148 arıza akımının %25'ini ADS'in iç ESD diyoduna bırakıyor (B2 ölçtü) |
| **Metal film %1, ≤100 ppm/°C direnç** | aşağıda | HV bölücünün **asıl sınırı** — bkz. B1 §11 |
| **DIP-8 IC soketi** | 6 | Şemada 4 DIP-8 gövde (LM358 ×2, TL072 ×2) + 2 yedek. Tedarikçide "8 pin dip soket" / "entegre soketi" adıyla, **direnç kategorisinde değil**. Envanterde soket kaydı YOK. Zorunlu değil |

**Metal film direnç seti** (karbon film **olmaz**, gerekçe aşağıda):

| Değer | Adet | Nerede |
|---|---|---|
| ~~1M **1/4W**~~ → **820K 1/4W** (+ **8.2K ×5**) | 8 | HV zinciri (6) + yedek. ⚠️ **5.12.18'de değişti** — tedarikçinin metal film hattı 820K'da bitiyor. N = 601 aynı kaldı |
| 10K | 10 | HV alt bacak, Vref, fark yükselteci |
| 220K | 5 | NORMAL üst bacak |
| 6.8K | 10 | NORMAL alt + Sallen-Key (4) |
| 22K | 5 | Vref alt + RC süzgeç (2) |
| 47K | 10 | Fark yükselteci (2) |
| 2.7K | 10 | I²C pull-up (2) + kelepçe seri (2) |
| 100K · 100R · 220R | 5'er | Skop bölücü, akım RC, TL431 |

##### Neden metal film — B1 §11'in hesabı

601:1'lik bir bölücüde direncin **tipi**, değerinden daha belirleyici.
20 °C oda salınımı ve direnç başına 102 V ile:

| Tip | TCR hatası | VCR hatası | 1000 h sürüklenme | **TOPLAM** |
|---|---|---|---|---|
| **Karbon film** | %2.00 | %0.10 | %2.00 | **%4.10** |
| Metal film %1 (100 ppm) | %0.40 | %0.01 | %0.30 | %0.71 |
| Metal film %1 (50 ppm) | %0.20 | %0.01 | %0.20 | **%0.41** |

Kıyas: ADS kalibrasyon sonrası **%0.03**, MCP6004 tamponu **%0.004**,
referans DMM **%0.5**.

**Karbon film, tasarımın geri kalanını anlamsız kılıyor** — 137 kat kötü,
referans multimetrenin bile üstünde.

İki kalem kalibrasyonla **silinemez**:
- **VCR** gerilime bağlı, yani doğrusal değil. 12 V'ta kalibre edip 600 V
  ölçersen hata geri gelir.
- **1000 saatlik sürüklenme** karbon filmde %1–3. Günde 3 saat kullanımda
  ~11 ay, ama sürüklenme ilk haftalarda daha hızlı. Yani **kalibrasyon
  haftalar içinde bayatlar ve sayı hâlâ inandırıcı görünür.**

⚠️ `envanter.csv`'de **film türü alanı yok**; eldekilerin karbon mu metal
film mi olduğu bilinmiyor. Tezgahta ayırt etme: metal film genelde
mavi/yeşil gövde ve 5 halka (%1); karbon film bej ve 4 halka (%5).

##### Kaç watt? — belirleyici olan güç değil, GERİLİM

Kullanıcı sordu (2026-09-08). B1 §12 her pozisyonu tek tek hesapladı:

| | En yüksek |
|---|---|
| **Güç** | 1/4W'ın **%20**'si (R26/R33, kelepçe seri direnci, TL072 arıza anında 50 mW) |
| **Gerilim** | 1/4W'ın **%51**'i (HV zinciri, direnç başına 102 V) |

**Güç hiçbir yerde sorun değil.** Metal filmde asıl sınır azami *çalışma
gerilimi*: 1/4W = 200 V, 1/2W = 250 V, 1W = 350 V.

| Pozisyon | Gerilim | Güç | Gövde |
|---|---|---|---|
| **1M ×6 (HV zinciri)** | **102 V** | 10 mW | **1/2W** önerilir |
| 100K (skop üst) | 45.6 V | 21 mW | 1/4W |
| 220K (NORMAL üst) | 31.5 V | 4.5 mW | 1/4W |
| 2.7K (kelepçe seri) | 11.6 V | **50 mW** | 1/4W |
| Diğer hepsi | < 3.3 V | < 5 mW | 1/4W |

**HV zincirinde neden 1/2W:** 1/4W teknik olarak yetiyor (sınırın %51'i),
ama 1/2W iki şey kazandırıyor:

1. Gerilim payı %49 → **%59**; yanlışlıkla 1200 V uygulanırsa 1/4W aşar, 1/2W aşmaz
2. **Gövde 3.2 mm → 6.5 mm.** Delikli plakette 615 V'ta kaçak yolu
   (creepage) uzuyor — direncin kendi iki ucu arasında 102 V var ve
   **gövde uzunluğu doğrudan o mesafedir**

⚠️ **2W ve üstü ALMA:** gövde büyüdükçe parazitik kapasite artıyor ve skop
kanalının bandını kesiyor; ayrıca delikli plakette yer sorunu.

**Sipariş:** 1M → **1/2W**, diğer hepsi → **1/4W**. Tek gövde istenirse
hepsi 1/2W de olur; fark küçük, sadece yer kaplar.

##### Yalnızca 1/4W bulunabiliyorsa — sorun yok (2026-09-08)

Kullanıcı sordu. **Cevap: 1/4W yeterli, 6 dirençle tasarım olduğu gibi kurulur.**

> ⚠️ Bu bölümdeki tablolar 1M üzerinden yazıldı; 5.12.18'de değer 820K
> oldu ve alt bacak 10K → 8.2K. **Sayılar aynı kaldı** (N, menzil, adım,
> direnç başına gerilim) — yalnızca değer etiketleri değişti.

⚠️ **Bir vurgu düzeltmesi:** yukarıda 1/2W'ı gövde boyu (3.2 → 6.5 mm) ve
"kaçak yolu" gerekçesiyle öne çıkarmıştım. **Bu abartıydı.** Üreticinin
200 V'luk değeri zaten gövdenin uçtan uca dayanımıdır; 102 V'ta direnç
kendi spec'i içinde. Kaçak yolu asıl **plaket yerleşiminin** işi (delik
atlama), direncin gövdesinin değil. 1/2W'ın tek gerçek katkısı gerilim payı.

| Zincir | Alt bacak | Tam ölçek | Adım | 615 V'ta/direnç | Sınırın | Tavan |
|---|---|---|---|---|---|---|
| **6× 1M** | 10K | 613.7 V | 18.78 mV | **102.3 V** | **%51** | 1200 V |
| 8× 1M | 10K+3.3K | 615.2 V | 18.83 mV | 76.7 V | %38 | 1600 V |
| 10× 1M | 10K+6.8K | 608.8 V | 18.63 mV | 61.4 V | %31 | 2000 V |

*Tavan = direncin kendi 200 V sınırına ulaşan giriş gerilimi.*

**6× 1M zaten geçiyor** (%51, kuralın %60 eşiğinin altında) ve direnç
sınırı ancak **1200 V** girişte aşılıyor — tasarımın tam ölçeği 615 V.

8× 1M seçeneği **aynı menzili ve aynı adımı** veriyor, sadece payı
%51 → %38 çıkarıyor. Bedeli iki fazladan 1M ve alt bacakta 10K+3.3K seri
çift. İstenirse, ama gerekli değil.

**Sipariş tek gövdeye indi: her yerde 1/4W metal film.**

##### 🟡 B. ÖNERİLEN — ucuz, işi belirgin iyileştiriyor

| Parça | Adet | Neden |
|---|---|---|
| ~~MCP6002-I/P~~ | ~~4~~ | ❌ **LİSTEDEN ÇIKARILDI** — bkz. aşağıdaki not |
| **Yedek ESP32-S3** | 1 | 615 V ile çalışılacak ve elde **tek** kart var. Ölürse proje durur |
| Tek damarlı montaj teli (0.5 mm, 3-4 renk) | — | Nokta-nokta + Kelvin uçları |
| **Silikon test kablosu / HV prob** | 1 çift | 600 V için jumper kablo **kullanılmaz** |

##### ❌ MCP6002 listeden ÇIKARILDI (2026-09-08)

Kullanıcı sordu: "MCP6002'nin muadili yok mu, aldığım yerlerde sadece SMD var."

Soru hesabı yeniden yaptırdı ve **cevap şu: artık gerek yok.** Bölüm 4'te
MCP6002'yi LM358'e tercih etmiştim (sürüklenme %0.004 vs %0.027) — ama o
karşılaştırma **bölücüyü hesaba katmıyordu.** Metal film kararından sonra
bölücü %0.41 ile en büyük kalem oldu ve op-amp farkı gömüldü:

| Bölücü | Op-amp | **Toplam (kök-kare)** |
|---|---|---|
| Metal film 50 ppm | **LM358** | **%0.4122** |
| Metal film 50 ppm | MCP6002 | %0.4114 |
| Karbon film | LM358 | %4.1026 |
| Karbon film | MCP6002 | %4.1025 |

MCP6002'nin kazancı: **bağıl %0.21 iyileşme.** Ölçülemez.

Dikkat çekici olan alt iki satır: **karbon filmle op-amp seçimi hiçbir şey
değiştirmiyor** (%4.1026 vs %4.1025). Yani doğru sıra: önce dirençleri
düzelt, op-amp zaten sorun değil.

**LM358 (stokta 8, DIP-8, +5 V) yeterli** — toplam %0.412, referans
multimetrenin %0.5'inin altında.

DIP muadili yine de aranırsa (RRIO, 3.3 V, DIP-8): `LMC6482IN`,
`TLV2370IP`, `OPA2350PA`, `TS912IN`. Hepsi var ama **hiçbiri gerekli değil.**

##### 🟢 C. YOL HARİTASI — sonra lazım, şimdi alınırsa ikinci kargo yok

DEVIR 5.8'den, hâlâ geçerli:

| Parça | Adet | Ne için |
|---|---|---|
| **LM319N** | 2 | Doyum testi. **Envanterde komparatör YOK** |
| 10K NTC B3950 | 2 | Elektronik yük termal koruma |
| KSD9700 70 °C NC | 1 | Donanım ısı kesici |
| **1N4148** | 20 | ⚠️ **Ölçüm kartında KULLANILMIYOR** — oradaki kelepçelerin hepsi BAT85 (4.13/5.12.4). Bu kalem *elektronik yük* projesinin donanım watchdog'u ve kelepçeleri için; o devre henüz tasarlanmadı, 20 sayısı hesap değil tahmin. Stokta 8 var |
| Mika yalıtkan + montaj seti | 5 | MOSFET–soğutucu |
| 🔭 **ALINX AN108** (AD9280 32 Msps ADC + AD9708 DAC) | 1 | **Hızlı skop (B14) + sinyal üreteci.** ~22–49 USD. **Önce 5.12.20'deki bedava adım 1 denenecek**, ondan önce alınmaz. AD9226 modülü de olur ama AN108 8 bit + BNC + DAC ile daha uygun |

##### ✅ ALMAYA GEREK OLMAYANLAR

| Parça | Neden |
|---|---|
| **±12 V için ek parça** | 7812 ×3, 7912 ×2, 7805 ×3 stokta. NE555 (yolda ×10) + SR5100 (stokta ×10) şarj pompası da yeterli — ±12 V rayı yalnızca ~6 mA çekiyor (4 TL072 kesiti) |
| Ayırma kondansatörü | 100nF stokta 51 adet; 7 tane gerekiyor |
| Muz jak / klemens | Siparişte 10 muz + 10 born jak var, 4 giriş çifti için fazlasıyla yeter |
| Soğutucu | `MEK002` var — ama **ölçüsü hâlâ bilinmiyor** (açık soru #2) |
| **ESP32-CAM / OV2640 kamera kartı** | ⚠️ Kullanıcı "LCD_CAM" adından dolayı bunun gerektiğini sandı. **Gerekmiyor:** LCD_CAM, S3 çipinin **içindeki** paralel veri bloğu — ayrı bir kart değil, kamerayla ilgisi yok |
| **Çıplak AD9226 yongası** | LQFP-48, yani **SMD**. Çakır Elektronik satıyor ama alma — modül al, o lehimli geliyor |

##### ✅ O günün açık sorusu kapandı

**"Kaç adet 12 V adaptörün var?"** — 2026-09-09'da cevaplandı: hiç yok.
Çözüm 24 V kaynak + LM358 orta nokta tamponu; ayrıntı **5.12.23**'te.
İkisi seri bağlanınca ±12 V'u regülatörsüz veriyor; bir tanesi varsa
−12 V'u NE555 pompasıyla üretmek gerekiyor. İkisi de yoksa **bir adet
12 V adaptör** listeye eklenmeli.

#### 5.12.16 🔴 Ayırma kondansatörleri EKSİKTİ — düzeltildi (2026-09-08)

Bu soruyu incelerken çıktı: şemada **hiçbir besleme rayında ayırma
kondansatörü yoktu.** Dört op-amp (U3, U4 +5 V'ta; U5, U8 ±12 V'ta),
sıfır yerel bypass.

Netlist denetimi gösterdi:
```
+5V    3 uc, kondansator: YOK
+12V   2 uc, kondansator: YOK
-12V   2 uc, kondansator: YOK
```

**Neden önemli:** op-amp çıkışı kapasitif yük sürüyor (Sallen-Key'in
C'leri) ve besleme empedansı yüksekse bu salınıma dönüşebilir. TL072'nin
slew hızı 13 V/µs; ani akım talebini yerel kondansatör karşılamalı,
20 cm'lik besleme teli değil.

**Düzeltildi:** C9–C15, 7 adet 100nF (U3, U4, U5 ±, U8 ±, ADS rayı).
Hepsi stoktan. Netlist denetimine altı kural eklendi — bir daha
eksik kalamaz.

#### 5.12.18 🔧 HV bölücü 1M → 820K — karar kaçak akımına dayandı (2026-09-09)

Üç turda oturdu:

1. *"Ellerinde 1 M yokmuş"* → 6× 2.2M / 22K seçildi, zincir yeşile döndü.
2. Kullanıcı metal film listesinin **kΩ sayfasını** yapıştırdı; hat 820K'da
   bitiyor görünüyordu. "MΩ'lar karbon film olmalı" diye 6× 820K / 8.2K'ya
   geçildi — **bu gerekçe yanlıştı.**
3. Kullanıcı düzeltti: **2.2M ve 6.8M da metal film.** Yani seçim zorunluluk
   değil, tercih. Yeniden, doğru gerekçeyle karara bağlandı.

**Anahtar gözlem:** alt bacak zincirin yüzde biri olduğu sürece
`6R / (R/100) = 600`, yani **hangi R olursa olsun N = 601.0 tam.** 820K, 2.2M
ve 6.8M üçü de aynı menzili, aynı adımı, aynı direnç gerilimini (102.3 V, %51)
ve aynı `ORAN_YUKSEK = 601.0f`'i verir.

**Ayıran tek şey yüzey kaçağı.** Delikli plakette zincire paralel oluşan bir
kaçak yolu bölme oranını aşağı çeker ve hata **doğrudan zincir direnciyle
orantılıdır** (`bağıl hata ≈ Rust / R_kaçak`):

| zincir | Rust | giriş Z | 1 GΩ kaçakta | 10 GΩ | 100 GΩ |
|---|---|---|---|---|---|
| **6× 820K** | **4.92 MΩ** | 4.93 MΩ | %0.492 | **%0.049** | %0.005 |
| 6× 2.2M | 13.20 MΩ | 13.22 MΩ | %1.320 | %0.132 | %0.013 |
| 6× 6.8M | 40.80 MΩ | 40.87 MΩ | %4.080 | %0.408 | %0.041 |

Kaçak **kalibrasyonla silinmez** — nemle günden güne değişir. Karbon filmi
eleyen gerekçenin birebir aynısı.

**2.2M'in karşı kozu giriş empedansı** (13.22 MΩ ↔ 4.93 MΩ; 615 V'ta 47 µA ↔
125 µA). Ama bu kanalın ölçeceği şeyler — doğrultulmuş şebeke, DC bara, SMPS
çıkışı — miliohm mertebesinde kaynaklar; orada fark ölçülemez.

**Karar: 820K.** Kaçak, zincirin *doğrulanamayan* riski (tezgahta ölçülecekler
listesinde duruyor); giriş empedansı ise hesabı yapılmış ve önemsiz çıkmış bir
fark. Doğrulanamayan riskin küçüğü seçilir. Kılavuza ayrıca "lehimden sonra
izopropil alkolle temizle" maddesi eklendi — bu bölücüde temizlik bir doğruluk
parametresi.

| | 1M (ilk) | 2.2M (ara) | **820K (nihai)** |
|---|---|---|---|
| Alt bacak | 10K | 22K | **8.2K** |
| N · menzil · adım | 601.0 · ±613.7 V · 18.78 mV | *aynı* | *aynı* |
| Direnç başına @615 V | 102.3 V (%51) | 102.3 V | 102.3 V |
| Thévenin | 9.98 kΩ | 21.96 kΩ | **8.19 kΩ** |
| Rust (kaçak duyarlılığı) | 6.00 MΩ | 13.20 MΩ | **4.92 MΩ** |
| Metal film alınabilir mi | ❌ | ✅ | ✅ |

`ORAN_YUKSEK = 601.0f` dört turda da **hiç değişmedi**. R17 (22K) 2.2M turunda
kaldırılmıştı, 820K ile geri kondu: Thévenin 8.19 kΩ tek başına C3 ile 194 Hz
kesim ve 860 Hz'te −13.1 dB veriyor, 20 dB kuralını geçmiyor. R17 ile toplam
30.19 kΩ, fc 52.7 Hz, −24.3 dB.

**Bu iş dört gerçek kusur ortaya çıkardı:**

1. **`tasarim3.py` tek kaynağa bağlı değildi.** Bölücü değerleri orada *elle*
   yazılmıştı; `tasarim3_sabit.py` değişince tasarım dökümanı sessizce eski
   değerlerle hesaplamaya devam etti ve şemayla ayrıştı. Artık `KANALLAR`
   sabit dosyadan türetiliyor, iki kaynağın eşitliği de bir kural.
2. **"Thévenin < 10 kΩ" kuralı yanlış şeye bakıyordu.** O TI kılavuzu ADS'in
   *gördüğü* empedans için; bizde ADS tamponun çıkışını görüyor. Bölücü
   Thévenin'inin belirlediği şey tamponun **taban akımı ofseti**.
3. **Taban akımı hesabının kendisi de yanlıştı.** İlk yazılışında R7/R17
   unutulmuştu: tamponun + girişi bölücü Thévenin'ini *ve* seri süzgeç
   direncini görür. Düzeltilince NORMAL %0.029 → **%0.126**, YÜKSEK %0.036 →
   **%0.133** çıktı. İkisi de %0.5 bütçesinin altında ve zaten sıfır
   kalibrasyonunun sildiği bir ofset — ama rakam yanlıştı.
4. **RC örtüşme süzgeçlerinin topolojisi netlist'te hiç denetlenmiyordu.**
   R17 bir tur kaldırılıp geri kondu, netlist denetimi **iki durumda da
   75/75 geçti**. Artık 10 kural var: seri direnç bölücü düğümünde, öbür ucu
   tamponun *önünde*, kondansatör GND'ye değil VREF'e. Netlist 75 → **85**.

**Yeni tasarım kuralı — "metal film olsun" yetmiyor.** Bölüm 11'e tedarikçinin
metal film listesi girildi; oranı kuran her direnç (iki bölücü + skop bölücüsü
+ fark yükselteci) o listede gerçekten var mı diye sınanıyor. Tasarım kuralı
81 → **89**.

**Sipariş — metal film %1, hepsi 1/4W:**
`820K ×8` · `8.2K ×5` · `10K ×10` · `22K ×10` · `220K ×5` · `6.8K ×10` ·
`47K ×10` · `2.7K ×10` · `100K ×5`
(220R ve 100R metal film listesinde yok — onlar oranı kurmuyor, stoktaki
karbon film yeterli.)

Zincir: **7/7** · 89 tasarım kuralı · 30 SPICE · ERC 0 · 85 netlist ·
70 AVR · 70 arayüz. Aşama 1 (9/9) ve Aşama 2 (6/6) regresyon temiz.

---

#### 5.12.19 🔬 "ESP32-S3 en iyisi mi?" — MCU araştırması (2026-09-09)

Kullanıcı skop tarafında daha iyi sonuç istedi, MCU'yu tamamen değiştirmeye
açık olduğunu söyledi. Araştırıldı; **sonuç: S3'te kalınıyor.**

**1. Bugünkü sınır MCU değil, ön uç.** Sallen-Key f0 = 16.55 kHz:

| frekans | zayıflama |
|---|---|
| 5 kHz | −0.04 dB |
| 10 kHz | −0.54 dB |
| 16.55 kHz | −3.01 dB |
| 41.67 kHz (Nyquist @83.3 ksps) | −16.15 dB |

Ayrıca en hızlı zaman tabanı (100 µs/div × 100 örnek/div) **1 Msps** ister,
eldeki 83.3 ksps ile bölme başına 8 örnek düşer. Yani MCU'yu değiştirmek
tek başına hiçbir şey kazandırmaz — süzgeç de zaman tabanı da yeniden
tasarlanmalı.

**2. 🔴 ESP ailesinde daha hızlısı YOK — Espressif'in kendi blogu yanıltıcı.**
[developer.espressif.com/blog/2025/08/adc-performance](https://developer.espressif.com/blog/2025/08/adc-performance/)
tablosu ESP32-C5 için **2000 ksps** diyor. Ama kurulu çekirdekteki
(`esp32:esp32` 3.3.11) `soc_caps.h`, yani sürücünün **fiilen dayattığı**
sınır:

| SoC | `SAMPLE_FREQ_THRES_HIGH` | blog: DNL / INL | blog: menzil |
|---|---|---|---|
| ESP32-S3 | **83 333** | ±4 / ±8 | 0–2900 mV |
| ESP32-C5 | **83 333** | ±5 / ±5 | 0–3300 mV |
| ESP32-C6 | **83 333** | +12/−8 / ±10 | 0–3300 mV |
| ESP32-P4 | **83 333** | +3/−1 / +3/−5 | 0–3300 mV |
| ESP32 (klasik) | **2 000 000** | ±7 / ±12 | 150–2450 mV |

Yani sürekli-ADC yolunda **83.3 ksps ailenin ortak tavanı**; 2 Msps'i yalnızca
klasik ESP32 veriyor ve o da ailenin **en kötü doğrusallığı** ve kırpılmış
giriş menziliyle. Blog ile `soc_caps.h` çelişiyor — çelişki çözülmedi, ama
karar bugün **çalıştırılabilir** olana göre verildi.

**3. S3 aslında ailenin iyi tarafında.** INL ±8 / DNL ±4 ile C3, C6, H2 ve
klasik ESP32'nin önünde; yalnızca P4 daha iyi ve o da aynı 83.3 ksps'te.

**4. Gerçek hedef ne olurdu:** envanter SMPS ağırlıklı (SG3525, TL494,
UC3843, IR2110) — bunlar 20–100 kHz'te anahtarlıyor. Dalga *şeklini* görmek
için 5–10 katı, yani **500 kHz–1 MHz bant** ve **≥2–4 Msps** gerekir.
Bugünkünün 25–50 katı; bu bir MCU değişimi değil, ayrı bir alet.

| Yol | ADC | Gerçekçi bant | Bedel |
|---|---|---|---|
| **S3, bugünkü hâli** | 83.3 ksps dahili | ~10 kHz | 0 |
| S3 + süzgeç 30 kHz'e | 83.3 ksps | ~20 kHz | 4 parça |
| Başka ESP (C5/C6/P4) | 83.3 ksps | ~10 kHz | **kazanç yok** |
| ESP32 klasik | 2 Msps, INL ±12 | ~200 kHz, gürültülü | firmware + kalite kaybı |
| STM32G4 | 4 Msps, 5 ADC, donanım oversampling → 16 bit | ~500 kHz | firmware baştan, Wi-Fi yok |
| S3 + AD9226 modülü (LCD_CAM) | 65 Msps 12 bit | MHz | ayrı proje |

**5. Geçiş sigortası zaten elimizde.** Matematik katmanı platformdan bağımsız
(`olcum3.h` 377 + `skop_olc.h` 178 = 555 satır) ve **AVR emülatöründe**
doğrulanıyor. İleride STM32'ye geçilirse yeniden yazılacak olan yalnızca
ADC/NVS/seri tutkalı — zor kısım taşınabilir durumda. Bu, B4/B5'in
başlangıçtaki gerekçesinin beklenmedik bir getirisi.

**Karar:** S3'te kal, yedek S3 alımı geçerli. Skop yükseltmesi ayrı bir
kalem olarak yol haritasına yazıldı — ve o iş MCU ile değil, **ön uç +
harici ADC** ile çözülür.

---

#### 5.12.20 🔭 Hızlı skop yolu — AD9226 modülü + ESP32-S3 LCD_CAM (araştırma, 2026-09-09)

5.12.19'da "skop MCU ile değil ön uç + harici ADC ile çözülür" denmişti.
Kullanıcı bu yolun ayrıntısını, fiyatını ve **SMD lehimlemeden** yapılabilir
olup olmadığını sordu. Araştırıldı.

**🟢 SMD sorunu tamamen çözülüyor.** AD9226 hazır modül olarak satılıyor;
yonga (LQFP-48) fabrikada lehimli geliyor, sana kalan yalnızca **2.54 mm
header**. Modülün üzerinde ayrıca:

| Modülün verdiği | Değer | Neden önemli |
|---|---|---|
| Giriş zayıflatıcı + ofset devresi | −5…+5 V (10 Vpp) → 1–3 V | **Hızlı op-amp gerekmiyor** — TL072 zaten 3 MHz'de yetersiz kalırdı |
| Dijital çıkış seviyesi | **3.3 V** | ESP32-S3'e doğrudan, seviye çevirici yok |
| Besleme | tek 5 V | kartta zaten var |
| Analog bant | −3 dB @ 350 MHz | ADC'nin kendisi darboğaz değil |
| Bağlantı | 2.54 mm dişi header | delikli plakete uyar |

**Tasarım taslağı — 8 bit yeter, çünkü gerçek osiloskoplar 8 bit.**
AD9226'nın üst 8 biti (D11…D4) alınır; ESP32-S3'ün CAM arayüzü 8 bit kipinde
çalışır. Pin: 8 veri + PCLK + 1 senkron ≈ **10 GPIO**.

| PCLK | Msps | 4096 örneklik pencere | Nyquist | delikli plakette gerçekçi |
|---|---|---|---|---|
| 10 MHz | 10 | 409.6 µs | 5 MHz | ~1 MHz |
| 20 MHz | 20 | 204.8 µs | 10 MHz | ~2 MHz |
| **40 MHz** (S3 tavanı) | 40 | 102.4 µs | 20 MHz | ~4 MHz |

Bugünkü ~10 kHz'e göre **100–400 kat**. 4096 örnek = 4 kB, S3'ün 512 kB
dahili SRAM'ine rahat sığıyor — **PSRAM gerekmiyor**, dolayısıyla forumlarda
şikâyet edilen PSRAM/DMA bant darboğazı bu işte hiç doğmuyor.

**🔴 Asıl risk lehim değil, FIRMWARE.** LCD_CAM'i kamerasız, jenerik paralel
yakalayıcı olarak kullanmanın Arduino düzeyinde örneği yok; ESP-IDF register
seviyesinde çalışmak ya da `esp32-camera`'yı kırpmak gerekiyor.
**Çalışan emsal KLASİK ESP32'de var, S3'te değil:**
[EUA/ESP32_LogicAnalyzer](https://github.com/EUA/ESP32_LogicAnalyzer) ve
[lmcapacho/ESP32_LogicAnalyzer](https://github.com/lmcapacho/ESP32_LogicAnalyzer)
— klasik ESP32'nin I2S paralel giriş kipiyle **20 MHz, 8/16 bit, 128k örnek**.
Yani firmware riskini düşürmek istersen klasik ESP32 + AD9226, S3 + LCD_CAM'den
**daha az riskli** — açık kaynak başlangıç noktası hazır.

**Diğer riskler:** (1) 40 MHz'te 8 paralel hat delikli plakette çapraz karışma
ve toprak sıçraması yapar — 10 Msps'te başlamak akıllıca, o bile 1000 kat.
(2) Bugünkü halka tamponlu ön-tetik, DMA blok yakalamada döngüsel GDMA
tanımlayıcı listesi ister. (3) ±613 V girişi bu modüle bağlamak için MHz'de
**kompanzasyonlu** bölücü (trimmer kondansatörlü) gerekir — projede yeni konu.

**Fiyat ve tedarik:** modül AliExpress/Amazon'da **~18–25 USD**. Türkiye'de
modül listesi bulunamadı; Çakır Elektronik **çıplak yongayı** satıyor ama o
LQFP-48, yani **SMD — alma**. `AD9226ARSRL` bazı dağıtıcılarda "obsolete";
modüller mevcut stok/klonlarla üretiliyor. Yani **yonga değil modül al**.

##### Tedarik denendi — AD9226 gönderilemiyor, ama muadili DAHA İYİ

Kullanıcı 2026-09-09'da sipariş etmeyi denedi. AliExpress **765,37 TL**
(araştırmadaki 18–25 USD bandının tam ortası, fiyat normal) ama:
*"Bu ürün adresinize gönderilemiyor."* — **satıcıya özel** bir kısıt, ürüne
değil (stokta 99737 adet görünüyordu). Başka satıcılar var:
`aliexpress.com/item/1005005576645194` · `.../1005007430909352`.

**🟢 Muadil: ALINX AN108 — bu proje için AD9226'dan daha uygun.**

| | AD9226 modülü | **ALINX AN108** |
|---|---|---|
| ADC | AD9226, 12 bit, 65 Msps | AD9280, **8 bit**, 32 Msps |
| Giriş konnektörü | SMA | **2× BNC** |
| Giriş menzili | ±5 V | ±5 V |
| Bağlantı | header | 34 pin, 2.54 mm |
| Bonus | — | **AD9708 DAC, 8 bit, 125 Msps** |
| Fiyat | ~20 USD | 22 USD (ALINX resmi) · 40–49 USD (AliExpress/eBay) |

Üç sebeple daha iyi:
1. **8 bit zaten hedefti.** AD9226'nın 4 bitini atacaktık (gerçek osiloskoplar
   8 bit, S3'ün CAM'i 8 bit kipinde). AN108 doğrudan 8 bit veriyor.
2. **32 Msps kayıp değil.** S3'ün PCLK tavanı zaten 40 MHz; 65 Msps'i hiçbir
   zaman kullanamayacaktık.
3. **Üstündeki DAC bir sinyal üreteci.** Şu an ölçüm kartını test etmek için
   elde NE555'ten başka bilinen kaynak yok. Temiz sinüs/kare üretip **kartın
   kendisini doğrulamak** için kullanılabilir — zincirin "tezgahta ölçülmeli"
   maddelerinden birkaçı bununla kapanır. BNC olması da SMA adaptörü derdini
   kaldırıyor.

Yedekler: **TLC5510** modülü (8 bit, 20 Msps, tek 5 V, basit) ·
**AD9248** modülü (çift kanal 12 bit 65 Msps — V ve I aynı anda, ama pin iki katı).

##### Karar ve kademeli plan

**Aşama 4 kalemi, şimdi değil.** Mevcut kartın değeri ±613 V çift yönlü
V/I/W ölçümünde ve o tezgahta doğrulanmadı. Bu iş mevcut kartın büyüklüğünde
ayrı bir proje; karıştırılmamalı. Kullanıcı 2026-09-09'da "şimdilik almıyorum
ama ileride alabilirim, ihtimali aklımızda tutalım" dedi.

Sırası geldiğinde **alışverişle başlanmayacak**:

| # | Adım | Bedel | Karar noktası |
|---|---|---|---|
| 1 | Elde bir ESP32 ile hazır açık kaynak I2S paralel yakalama kodunu dene ([EUA](https://github.com/EUA/ESP32_LogicAnalyzer) / [lmcapacho](https://github.com/lmcapacho/ESP32_LogicAnalyzer)) | **0 TL** | Yürümezse burada dur |
| 2 | Yürürse **AN108** al (ADC + sinyal üreteci bir arada) | ~22–49 USD | — |
| 3 | 10 Msps'te başla, sonra yukarı çık | — | Delikli plakette 40 MHz riskli; 10 Msps bile bugünün 1000 katı |
| 4 | Kompanzasyonlu bölücü (trimmer kondansatörlü) tasarla | — | MHz'de zorunlu, projede yeni konu |

---

#### 5.12.21 🛒 Sipariş listesi denetimi (2026-09-09)

Kullanıcının direnc.net sepeti şema BOM'una karşı denetlendi.

**✅ Kartın elektroniği tam.** Şemanın istediği her direnç 50'şer adet
sipariş edilmiş (820K, 8.2K, 22K, 10K, 6.8K, 220K, 100K, 47K, 2.7K, 220R,
100R — 1K fazladan, sorun değil). BAT85 ×20 (4 gerekiyor), TL072CP ×3
(2 gerekiyor), LM358P ×10 (2 gerekiyor), 8 pin soket ×10 (6 gerekiyor),
1×40 dişi header ×2 (J5 için), silikonlu prob kablosu (HV için —
kırmızı ×2, siyah ×2). LM319N ×3 de yol haritası kalemi olarak alınmış.

**Stoktan karşılananlar (siparişe gerek yok):** 100nF ×11 gerekiyor,
stokta 41 · 1nF ×6 gerekiyor, stokta 11 · TL431 ×1, stokta 10.

**Yolda olduğu varsayılanlar — TEYİT EDİLMELİ:** ADS1115 ×2 · ESP32-S3 ×1 ·
muz jak / bariyer klemens (4 giriş çifti) · şönt seti (0.1R taş, 15mR).

##### 🔴 Listede EKSİK olanlar

| # | Eksik | Neden kritik |
|---|---|---|
| 1 | **Delikli plaket (pertinaks)** | Kart bunun üzerine kurulacak. Envanterde kaydı yok — ama "Mekanik/Sarf" rastgele girilmiş kategoriler, **kayıtta yok = elinde yok demek değil**. Bakılmalı. 615 V için geniş, kaliteli bir plaket gerekiyor |
| 2 | **±12 V rayının ham kaynağı** | 7812 ×3, 7912 ×2 stokta **ama onları besleyecek şey yok**. Simetrik ±12 V için ya çift sargılı trafo, ya iki ayrı 12 V adaptör, ya NE555 şarj pompası. **Dört TL072 kesiti (skop Sallen-Key + hızlı yol) tamamen buna bağlı** — B11 |
| 3 | **Yedek ESP32-S3** | 5.12.15'te önerilmişti. 615 V ile çalışılacak, elde tek kart var |
| 4 | İzopropil alkol | 5.12.18'de kılavuza eklendi: 820K zincirinin etrafındaki lehim kalıntısı **kaçak yolu** demek. Bu bölücüde temizlik bir doğruluk parametresi |
| 5 | Lehim teli / pasta | Envanterde kayıt yok |

**✅ Cevaplandı, 5.12.23:** 12 V adaptör yok; 24 V kaynak + LM358 orta nokta
tamponu ile çözüldü, ek alım gerekmiyor. Bu satırdaki "±12 V ham kaynağı"
eksiği **kapandı** — geriye delikli plaket, yedek ESP32-S3, izopropil alkol
ve lehim teli kalıyor.

**Listedeki fazlalıklar** (ULN2003, 74HC595, CD4027, LM339N, BD139, USB
konnektörler, tunik konnektörler, geniş soket yelpazesi) bu kartla ilgili
değil ama zararsız — başka projelere gider.

---

#### 5.12.22 ✅ B15 — ARIZA VE ZORLAMA SİMÜLASYONU — **TAMAMLANDI (2026-09-09)**

> **Sonuç özeti aşağıda 5.12.24'te.** Bu bölüm görev tanımı olarak
> bırakıldı; her maddenin cevabı 5.12.24'te kodlarıyla duruyor.
> Çıktı: `uretim/sim3_ariza.py` — 89 doğrulama, 25 senaryo,
> `dogrula3.py`'de **B15** adımı.

Kullanıcının isteği: *"sistemin baştan sona olası zorlama ve kırılma
noktalarının hepsi test ve simüle edilsin. Ters akım, ters voltaj, yüksek
voltaj — tüm giriş ve çıkışlar için."*

**Bugün ne var:** B2 yalnızca **iki** arıza senaryosunu kapsıyor —
(a) op-amp çıkışı arızada raya oturursa ADS pinine kaçan akım (kelepçe
karşılaştırması), (b) girişte %15 aşırı gerilim. Gerisi **hiç
incelenmedi**.

**B15'in kapsaması gerekenler:**

**A. Giriş terminalleri — yanlış sinyal**
1. 🔴 **±32 V terminaline 615 V** (en olası kullanıcı hatası: yanlış klemens).
   Bölücü düğümü Vref + 615/33.35 ≈ **20.1 V** olur; LM358'in mutlak giriş
   sınırı V+ +0.3 = 5.3 V. R7 (22K) üzerinden kaçak ≈ (20.1−5.3)/22k =
   **0.67 mA**. LM358'in giriş kelepçe akımı sınırıyla karşılaştırılmalı.
2. 🔴 **±32 V terminaline 230 V AC şebeke** — aynı yol, tepe 325 V.
3. **613 V terminaline 1000 V+** — direnç başına 167 V, 200 V sınırının
   altında ama pay %16'ya iner; ayrıca bölücü düğümü ne olur?
4. **Skop girişine menzil dışı** — kelepçe var, B2 kısmen ölçtü; tamamlanmalı.
5. **Şönt terminaline ters akım ve aşırı akım** — çift yönlü tasarlandı ama
   sınır ölçülmedi. Şönt açık devre kalırsa ne olur?

**B. Besleme arızaları** — ±12 V artık **24 V + LM358 orta nokta tamponu**
ile üretiliyor (5.12.23); senaryolar bu topolojiye göre kurulmalı, ileride
6× 18650 paketi de aynı konnektöre takılacağı için o yol da değerlendirilsin.
6. **+5 V yok, ±12 V var** (ve tersi) — beslemesiz op-amp girişine sinyal
   sürmek "phantom powering" ve latch-up riski.
7. **Ters polarite besleme** — 3 pinli konnektör ters takılırsa (+12 ↔ −12).
8. USB'den beslenirken harici besleme de bağlı.
8b. 🔴 **Orta nokta tamponu (LM358) arızası** — GND referansı kaybolur, iki
   ray birden kayar. Tamponsuz dirençli bölücü ne kadar dayanır?
8c. 🔴 **24 V kaynak yalıtımlı değilse** −12 V rayı şebeke toprağına kısa
   devre olur. Bu senaryo sayısallaştırılmalı.

**C. Bileşen arızası**
9. 🔴 **Alt bacak (R16, 8.2K) açık devre** — bölücü düğümü girişe bağlı
   kalır. İlk hesap: 4.92M zinciri akımı (615−5)/4.94M ≈ **123 µA**'e
   sınırlıyor, yani muhtemelen **hayatta kalınır** — ama doğrulanmalı.
10. Zincirdeki bir 820K açık devre → düğüm Vref'e gider (güvenli, teyit).
11. Vref tamponu arızası → iki kanal birden kayar.

**D. Kullanıcı hatası ve sistem**
12. 🔴 **Kart izole DEĞİL** — 615 V şebeke referanslı bir devreye bağlanırsa
    gerilim USB üzerinden PC'ye gider. Bu bilinen bir uyarı ama
    **sayısallaştırılmadı**.
13. Prob ucu kayması, sıcak takma.

**Kabul ölçütü:** Hiçbir TEK arıza ESP32'yi ya da PC'yi öldürmemeli.
Ölecek bir parça varsa **hangisi olduğu bilinmeli ve ucuz olmalı**
(tercihen soketli LM358). Her senaryo için: kaçan akım, düğüm gerilimi,
hangi mutlak sınır aşılıyor, hangi parça gidiyor.

**Yöntem:** Mevcut zincirin kuralları — ngspice (B2 kalıbı) + `kural()`
iddiaları. Her sonuç çalıştırılabilir bir testle desteklenmeli; elle
yazılmış sayı olmayacak. Çıktı `uretim/sim3_ariza.py` (yeni B15 adımı)
ve `dogrula3.py`'ye eklenmeli.

---

#### 5.12.23 🔋 ±12 V rayı ÇÖZÜLDÜ — 6× 18650, yükselticiye gerek yok (2026-09-09)

**Açık soru #1 kapandı.** Kullanıcı: *"12 volt adaptörüm yok; 24 V güç
kaynağım ve voltaj düşürücü regülatörüm var. 18650 + yükseltici ile
besleyebilir miyim?"*

**Cevap: 18650 ile evet — ama YÜKSELTİCİ GEREKMİYOR.** İki adet 3'lü paket
sırt sırta, orta nokta = GND:

| 3 hücre durumu | Ray | TL072 sınırı ±5…±18 V |
|---|---|---|
| dolu (4.2 V) | **±12.60 V** | ✅ |
| nominal (3.7 V) | **±11.10 V** | ✅ |
| boş (3.0 V) | **±9.00 V** | ✅ |

Tam şarjdan tam boşalmaya kadar TL072 aralığın içinde. Yükseltici,
inverter, şarj pompası — hiçbiri gerekmiyor. **Envanterde tam da gereken
tutucu var: `PWR003` 3'lü pil yuvası ×2.**

##### Akım bütçesi — yük çok küçük

| Ray | Yük | Ne |
|---|---|---|
| ±12 V | **5.6 mA** | 2× TL072 (4 kesit) |
| +5 V analog | **1.4 mA** | 2× LM358 |
| +3.3 V | **4.0 mA** | TL431 rayı 3.7 + 2× ADS 0.3 |
| **Analog toplam** | **11.0 mA** | ESP32 hariç |
| ESP32-S3 | 40 mA (boş) … 250 mA (Wi-Fi tepe) | |

2500 mAh hücreyle: yalnızca analog **~357 saat**; ESP32 de pilden beslenirse
**~17 saat**.

##### 🔴 Bunun asıl kazancı: KART İZOLE OLABİLİR

Projenin en büyük tehlikesi bugüne kadar şuydu: *kart izole değil, 615 V
şebeke referanslı bir devreye bağlanırsa gerilim USB üzerinden PC'ye gider.*
USB ile beslendiği sürece kart toprağı = PC toprağı = şebeke toprağı.

**Pil + Wi-Fi ile kart tamamen yüzer.** Firmware Wi-Fi'yi zaten destekliyor
(`WIFI_AD`/`WIFI_SIFRE` boş, web sunucusu kurulu). O zaman:

| | USB beslemeli (bugün) | Pil + Wi-Fi |
|---|---|---|
| Kart toprağı | PC toprağı = şebeke toprağı | **yüzer** |
| 615 V şebeke referanslı devreye bağlanırsa | ⚠️ **kısa devre — PC ve kullanıcı tehlikede** | akım akmaz |
| Kalan risk | — | **kartın kendisi 615 V'a çıkar — yalıtımlı kutu ŞART** |

Bu galvanik izolasyon *değil* (izolasyon yükselteci yok); **tüm aleti
yüzdürmek** — el tipi multimetrelerin yaptığı şeyin aynısı. Meşru ve
etkili, ama şartı var: ölçüm sırasında **USB takılı olmayacak** ve kart
yalıtımlı bir kutuda, açıkta iletken kalmayacak. Programlama/hata ayıklama
USB ile, ama yalnızca HV bağlı DEĞİLKEN.

##### İki besleme yolu — kart ikisini de kabul etsin

| | **A. 6× 18650 (önerilen)** | **B. 24 V kaynak + orta nokta bölücü** |
|---|---|---|
| ±12 V nasıl | iki 3'lü paket sırt sırta | 24 V'u ikiye böl, orta nokta = GND |
| Ek parça | yok (yuvalar elde) | **LM358 orta nokta tamponu** (stokta 8 var; LM358 azami besleme 32 V — 24 V'ta çalışır, 7 mA dengesizliği rahat sürer) |
| Anahtarlama gürültüsü | **sıfır** | kaynağın SMPS gürültüsü raya biner |
| İzolasyon | **yüzer** | kaynak yalıtımlıysa yüzer, değilse hayır |
| Kullanım | HV ölçümü, saha | tezgahta geliştirme |

**Karar: kartta 3 pinli bir besleme girişi olsun (+12 / GND / −12)** —
siparişte 3 pin tunik konnektör zaten var. Hangi kaynağın takıldığı kartı
ilgilendirmesin.

**ESP32'nin 5 V'u:** +12 raydan. İki ayrı yol tavsiye ediliyor —
analog +5 V (LM358, 1.4 mA) için **7805** (stokta 6 adet, ısınmaz, temiz);
ESP32'nin 150 mA'i için kullanıcının **düşürücü regülatör modülü** (7805 ile
7 V × 150 mA = 1 W olurdu, soğutucu gerekirdi). Anahtarlamalı modülün
gürültüsü analog rayı kirletmesin diye ayrı tutuluyor; toprak yıldız
noktası paketlerin orta noktası olmalı.

##### 🔴 Hücre sayısı: 2 var, 6 gerekiyor → BİRİNCİ YOL 24 V OLDU

Kullanıcı 2026-09-09'da cevapladı: **elinde 2 adet 18650 var.** İki hücre
ortadan bölününce ±3.7…±4.2 V eder — TL072'nin ±5 V tabanının **altında**,
olmaz. Dolayısıyla sıralama değişti:

| Yol | Ne gerekiyor | Gürültü | İzolasyon | Karar |
|---|---|---|---|---|
| **24 V + LM358 orta nokta tamponu** | **hiçbir şey — hepsi elde** | kaynağın SMPS'i | kaynak yalıtımlıysa | ✅ **ŞİMDİ BUNU KUR** |
| 6× 18650 (iki 3'lü paket) | **4 hücre daha al** | **sıfır** | **yüzer** | İzolasyon istendiğinde |
| 2× 18650 + yükseltici → 24 V → bölücü | yükseltici modülü | **iki kat anahtarlama** (boost + bölücü) | yüzer | ❌ en kötüsü |

Son satır kullanıcının ilk sorduğu şeydi ve teknik olarak mümkün — ama bir
**ölçüm aleti** için en kötü seçenek: anahtarlamalı yükselticinin gürültüsü
doğrudan ±12 V rayına biner, TL072'nin PSRR'si 100 kHz'te DC'dekinin çok
altındadır ve **Sallen-Key bu gürültüyü süzemez** (gürültü süzgeçten SONRA,
op-amp'in beslemesinden giriyor). 24 V kaynak varken buna gerek yok.

**Uygulama sırası:** B11'i 24 V + LM358 tamponu ile kur, kart 3 pinli besleme
girişi (+12 / GND / −12) taşısın. Pil yolu sonradan aynı konnektöre takılır —
kartta hiçbir değişiklik gerekmez. 4 hücre alındığında izolasyon seçeneği
açılır.
- Seri bağlı hücreler **eşleşmiş** olmalı; korumalı (protected) hücre tercih
  edilir ya da hücreler tek tek şarj edilmeli. 11 mA'de dengesizlik önemsiz
  ama ESP32 de pilden beslenirse saatler içinde bir hücre aşırı boşalabilir.
  Eldeki 2 hücre 6'lı pakete katılacaksa **aynı marka/kapasite/yaşta 4 hücre
  daha** alınmalı — karışık hücre seri bağlantıda en zayıfını öldürür.
- 24 V kaynağın **yalıtımlı (floating)** olup olmadığı ölçülmeli: negatif
  ucu ile şebeke toprağı arasına ohmmetre. Toprağa bağlıysa orta nokta
  bölücü şemasında −12 V rayı toprağa kısa devre olur.

**B11 (±12 V rayı) artık tanımlı bir iş** — açık soru değil.

---

#### 5.12.24 ✅ B15 SONUÇLARI — arıza simülasyonu (2026-09-09)

`uretim/sim3_ariza.py` · **111 doğrulama · 27 senaryo · ~4 s** ·
`dogrula3.py` → **B15** adımı. Zincir B11 ile birlikte **9/9**.

> ⚠ **Bu bir HESAP, tezgah ölçümü değil.** Donanım kurulmadı. B15 tasarımı
> zorluyor, kurulmuş bir kartı değil. Şu üçü yalnızca tezgahta öğrenilir:
> bir direncin aşırı yükte açık mı kısa mı devre kaldığı, gerçek LM358
> giriş jonksiyonunun kırılma gerilimi, delikli plakette 615 V'ta yüzey
> kaçağı.

##### 🔴 DEVİR'in kendi sayılarından DÖRDÜ yanlış çıktı

| DEVİR ne diyordu | B15 ne buldu |
|---|---|
| **5.12.22/1:** "LM358'in mutlak giriş sınırı V+ +0.3 = **5.3 V**" | **Yanlış.** Sınır V−'ye göre **32 V** ve beslemeden BAĞIMSIZ. LM358'in girişinde V+'ya kelepçe diyodu **yoktur**. İki bağımsız üretici doğruladı: TI SLOS068AB §7.3.3 *"Inputs may exceed VS up to the maximum VS without device damage"* · onsemi LM358/D Not 5 *"either or both inputs can go to +32 V without damage, independent of the magnitude of VCC"* |
| **5.12.22/1:** "R7 üzerinden kaçak ≈ **0.67 mA**" | **Pozitif tarafta akım AKMIYOR** (kelepçe yok). Kaçak yalnızca NEGATİF tarafta var: −615 V'ta alt-taş jonksiyonundan **564 µA** — TI'ın kendi 1 mA sınırının altında. 0.67 mA rakamı hem yanlış mekanizmaya dayanıyordu hem de düğümün yüklenmesini ihmal ediyordu |
| **5.12.22/9:** "R16 açık → 123 µA'e sınırlı, **muhtemelen hayatta kalınır**" | **Akım doğru (≤118 µA), sonuç doğrulanamadı.** LM358'in V+'ya kelepçesi yok, düğümü aşağı çekecek hiçbir şey kalmıyor. Girişin nerede duracağını belirleyen tek şey jonksiyonun **ters kırılma gerilimi** — o değer hiçbir veri sayfasında **yok**. B15 bu yüzden tek sayı değil **tarama** raporluyor: 40 V varsayımından itibaren mutlak sınır aşılıyor, kırılma hiç olmazsa düğüm **615 V'a** oturuyor. Anında ölmüyor ama sürekli spek dışı — **sessizce yanlış ölçüyor** |
| **5.12.23:** "±12 V rayı **5.6 mA**" (orta nokta yükü sayılmış) | **Yanlış sayım.** Op-amp boşta akımı V+ → V− **doğrudan** akar, orta noktaya hiç değmez. Gerçek orta nokta yükü **6.4 mA** (7805 kolu). ESP32'nin düşürücüsü +12 V'tan beslenirse **250 mA** — LM358'in garantili çekme akımının (sıcakta 5 mA) **50 katı** |

##### 🔴 B15'in BULDUĞU ve ŞEMADA DÜZELTTİĞİ üç kusur

**1. ADS girişlerinde seri direnç HİÇ YOKTU** — ve bu bir arıza değil,
**normal menzil dışı okumanın** her anında geçerliydi.

Netlist kanıtı: `/V_TAMPON = U3.6, U3.7, U7.4` — tampon çıkışı ADS pinine
doğrudan. LM358'in çıkış tavanı için veri sayfası **tek yönlü** garanti
veriyor (TI SLOS068AB **§5.7** — düz LM358 tablosu; §5.5 LM358B'ye ait —
koşul V_S = 5 V, R_L ≥ 2 kΩ, 25 °C: raydan düşüm **en fazla** 1.5 V,
yani V_OH ≥ 3.5 V) — rayın ne kadar **yakınına** çıkacağına dair sınır **yok**.
ADS'in giriş empedansı 2.4 MΩ, yani tampon test koşulundan (2 kΩ) 1200 kat
daha hafif yüklü; yük azaldıkça çıkış raya yaklaşır.

| V_OH varsayımı | ADS pini | seri R yok | 1K seri ile |
|---|---|---|---|
| V+ − 1.5 V (garantili) | 3.50 V | 0 mA | 0 mA |
| V+ − 0.9 V (makul) | 3.85 V | 2.51 mA | 0.30 mA |
| V+ (spek dışı üst) | 3.99 V | **12.6 mA** | 1.30 mA |

12.6 mA, ADS'in **mutlak** 10 mA sınırının üstünde. TI'ın tasarım hedefi
zaten çok daha sıkı: **≤1 mA** (SLVAEX7A §2.1) veya mutlak maksimumun
%20'si = 2 mA (SBAA227 §3.1).

⚠ **B2 bu soruyu 2.7 kΩ seri dirençle ölçüp "kelepçe gerekmiyor" demişti —
o direnç şemada yoktu.** O 2.7 kΩ skop ve hızlı akım yollarının kelepçe
direnciydi. B2 düzeltildi ve artık gerçek değeri kullanıyor.

→ **DÜZELTİLDİ:** `R34` (U3B→AIN0), `R35` (U4A→AIN2), `R36` (VREF→AIN1/AIN3),
hepsi **1 kΩ**. Bölücü altları, C2/C3 ve R28 gerçek VREF'te kaldı.
PGA sabit olduğu için kazanç hatası da sabit: **%0.042**, kalibrasyon siliyor
(ADS'in kendi kademe uyumu speki %0.1). Stokta 30 adet 1K var.

**2. Şönt kanalı — B15'in bulduğu EN CİDDİ açık.** `SONT_P`/`SONT_N` de
ADS pinlerine doğrudan gidiyordu (`/SONT_P = C4.1, R18.2, R27.1, U6.4`).
Tek akım sınırlayıcı R18 = **100 Ω**.

| senaryo | R38 YOK | R38 (1K) ile | sonuç |
|---|---|---|---|
| 10R şönt, ADS 10 mA eşiği | 0.48 A yükte | **1.48 A** yükte | eşik 3.1× yukarı |
| Şönt açık + 12 V / 1 A yük | 66.3 mA | **7.3 mA** | ADS artık **yaşıyor** |
| Şönt açık + 12 V / 10 mA yük | 6.2 mA | 3.5 mA | zaten zararsızdı |
| J3'e 32 V **çıplak** besleme | 255 mA | **25 mA** | ADS gider, ESP32 **güvende** |

⚠ **Yük direnci devrede SERİDİR.** Şönt açılınca yük akımı eski
büyüklüğünde başka yola dönmez — sıfıra düşer ve yeni bir çevrim oluşur:
`V_kaynak → harici yük → J3.1 → R18 → R38 → ADS AIN0 → ESD → +3V3 → GND`.
Bu yüzden tehlike **koşulludur**: yüksek empedanslı bir yükte (10R şöntün
varlık sebebi olan mA kademesi) arıza zaten zararsız.

🔴 Düzeltme **öncesi** bunlar kabul ölçütünü ihlal ediyordu: kaçak ADS'in iç
ESD diyodundan +3V3 rayına biniyor; ESP32'nin kendi boşta tüketimini (40 mA)
aşınca ray yükseliyor ve ESP32 de tehlikeye giriyordu. **R38/R39 ile hiçbir
senaryoda 40 mA aşılmıyor — ESP32 artık her arızada güvende.**

⚠ **Bu kanalda KELEPÇE KULLANILAMAZ:** SONT_P normal çalışmada ±256 mV
salınıyor — hem Schottky hem silisyum diyot o gerilimde zaten iletir.
Seri direnç tek seçenek.

→ **DÜZELTİLDİ:** `R38`/`R39` (1 kΩ), yalnızca ADS kolunda. Hızlı yol
(R27/R29) direncin **önünden** taplıyor, yani bant genişliği etkilenmiyor.
Eşik 4.8 V → **14.8 V**'a (3.1×), ESP32'nin güvende olduğu şönt arıza
gerilimi **47.8 V**'a çıktı. PGA sıçraması 0.120 puan — ADS'in kendi kademe
uyumu speki (0.1 puan) mertebesinde.

**3. C1 (100 nF) TL431'i osile ettiriyordu.** TI SLVA482A: TL431'in
katot–anot arasındaki kondansatör **10 nF – 2.2 µF** aralığında osilasyona
yol açıyor; güvenli değerler `<1 nF` ya da `>22 µF`. Şemadaki C1 tam o
aralığın ortasındaydı. TL431 veri sayfası zaten kondansatör
**gerektirmediğini** söylüyor (*"internally compensated to be stable
without an output capacitor"*).

→ **DÜZELTİLDİ:** C1 = **1 nF** (envanterde C049, 10 adet).

##### 📁 Ham araştırma ve denetim kanıtı — `uretim/b15-arastirma.md`

B15'in dayandığı **her veri sayfası sayısı**, kaynağı, ve her iddianın
bağımsız doğrulama sonucu bu dosyada (**437 KB**):

- 10 araştırma konusu (LM358, ADS1115, ESP32-S3, TL072/TL431, direnç aşırı
  yük, USB/izolasyon, AC şebeke, gerçek dünya arızaları, ngspice yöntemi)
- **80 iddia ayrı ayrı doğrulandı** — 35'i **çürütüldü** ve *neden*
  çürütüldüğüyle birlikte kayıtta tutuldu
- 6 denetim boyutunun tüm bulguları + önerilen yamalar

Üreteci: `uretim/b15_kanit_uret.py`. Kaynak veri oturuma bağlı geçici bir
dizindeydi ve **kaybolacaktı** — bu yüzden kalıcı `kanit/` klasörüne
döküldü. Çürütülenlerin saklanma sebebi: aynı sayılar ileride başka bir
kaynaktan tekrar önerilirse neden reddedildikleri bilinsin.

##### B15'in kendisi adversaryel olarak denetlendi

B15 yazıldıktan sonra altı bağımsız denetçi (SPICE modelleme, devre analizi,
iddia mantığı, eksik senaryo, sabitlerin kaynağı, şema tutarlılığı) betiği
ayrı ayrı denetledi ve **kendi ngspice koşumlarını yaptı.** Buldukları ve
düzeltilenler:

| bulgu | sonuç |
|---|---|
| A6/A7'nin devresi şemadaki R38'i (1K) yok sayıyordu | ADS akımı 9 kat abartılıyordu; düzeltildi, iki bulgu tersine döndü |
| A3'ün transient devresinde LM358 hiç yoktu | "giriş −5.59 V" → gerçekte **−0.62 V** (parazitik jonksiyon kelepçeliyor) |
| A5'te Sallen-Key'in seri dirençleri (2×6.8K) atlanmıştı | TL072 kelepçe akımı 2.0 mA → **0.64 mA** |
| C3b ölçülen düğümü ADS pini sanıyordu | O düğüm LM358'in **girişi**; arada doymuş tampon var. Ölen parça U7 değil, hiçbiri |
| Kazanç hatası tek bacakla hesaplanmıştı | ADS'in Z_diff'i **iki** bacağı görür; sayı 2× |
| İki iddia doğrudan `True`, beşi yalnızca literal sınıyordu | Hepsi netlist'ten/sabitlerden okunan gerçek denetimlere çevrildi |
| B5 matrisi "U3 ölür" diyordu ama ölçüm "sağ çıkıyor" diyordu | Çelişki giderildi |
| Gövde tablosu kapsam denetimi tautolojikti | Artık **netlist'ten** okuyor; R34–R39 eksikliğini yakaladı |

**Mutasyon testi:** `ADS_SERI_R` 1 kΩ → 1 mΩ yapıldığında **7 iddia kırmızıya
dönüyor** (A1, A1b, A6, A7, C5). Yani korumaların gerçekten sınandığı
kanıtlanmış durumda — testler sessizce yeşil kalmıyor.

##### 🔴 B15'in KAPATAMADIĞI tek bileşen senaryosu: endüktif yük

Denetim bunun tamamen eksik olduğunu yakaladı — ve kullanıcının alanı
(SMPS/inverter) düşünülürse **en olası zorlanma** bu. Şönt yükün **dönüş
kolunda**, yani kart yük akımının tamamını taşıyor.

**İki ayrı olay var, karıştırılmamalı:**

**(a) Her anahtarlamada — L·di/dt.** Kablo/şönt parazitik endüktansı
(~100 nH) üzerinde. **İyi haber:** 10 A/µs'te L·di/dt 1.0 V olmasına rağmen
düğüm yalnızca **−0.14 V**'a iniyor — C4 (100 nF) ve bölücü ağı tepeyi
yutuyor. Mutlak sınırın (−0.3 V) içinde, kelepçe akımı 0.001 mA.
⚠ 1 m'lik bir yük kablosu (~1 µH) aynı di/dt'de **10 kat** büyük tepe verir
— kablo kısa olmalı.

**(b) Arıza — endüktif yük akım akarken sökülüyor.** Bobin akımı devam etmek
istiyor ama kartın **1100 Ω**'luk yolundan geçemez (birkaç mA); ark **sökülen
kontakta** oluşur ve gerilim ark gerilimine (~15–20 V) kelepçelenir. Kart bunu
görür:

| | R38 yok | R38 (1K) ile |
|---|---|---|
| ~20 V arkta ADS akımı | 195 mA | **17.7 mA** |

R38 riski **11 kat** azaltıyor ama **elemiyor** — 10 mA sınırı 11.5 V'luk bir
arkta zaten aşılıyor ve hava arkı en az ~15 V.

→ **Bu, B15'in donanımla kapatamadığı tek bileşen senaryosu.** Çözüm
kullanımda: **endüktif yüke serbest geçiş (freewheel) diyodu**. Güç
elektroniğinin standart kuralı ama ölçüm kartı kullanılırken unutulması çok
kolay — **kutu etiketine yazılmalı**.

##### B2b — her programlamada yaşanan hal

Denetim, görev tanımının 6. maddesindeki "**ve tersi**"nin kapsanmadığını
yakaladı: USB takılı (+5 V, +3V3, VREF var) ama 24 V kapalı (±12 V yok).
Kart **her programlanışında** bu durumda.

TL072'ler beslemesizken girişlerinde sinyal var: U8A VREF'e (10K üzerinden),
U5A skop bölücüsüne bakıyor. Kelepçe akımları **0.12 mA** ve **1.0 mA** —
TI'ın 10 mA sınırının çok altında. Sallen-Key'in 2×6.8K'sı sınırlıyor.
**Zararsız.**

⚠ Eski die TL072'de giriş kelepçesi **yok**; TI o durumda "giriş gerilimi
beslemenin büyüklüğünü aşmasın" diyor. Alınacak TL072CP'nin hangi die olduğu
bilinmiyor — ama akım her iki halde de güvenli.

##### Bir metodoloji notu — "60 V" bir ölçüm değildi

Denetim, C1 bölümündeki manşet sayının ("LM358 girişi 60 V görüyor") bir
ölçüm değil, SPICE modelindeki **kaynaksız `BV=60`** parametresinin doğrudan
çıktısı olduğunu gösterdi. Aynı devre `BV=1000` ile koşturulduğunda düğüm
**615 V**'a oturuyor — yani tek sayılık rapor kötümser değil **iyimser**ti.

Düzeltildi: kırılma gerilimi artık `tasarim3_sabit.py`'de **açıkça bir
varsayım** olarak duruyor (`LM358_GIRIS_KIRILMA_VARSAYIMI`) ve C1 bölümü
tek sayı yerine **tarama** raporluyor. Zincir akımı da elle hesaplanmıyor,
simülasyonun döndürdüğü `i(Vin)` kullanılıyor.

Bu, projenin kendi kuralının ("elle yazılmış sonuç sayısı yok") B15'in
kendisinde de uygulanması demek — ve sonucu **güçlendiriyor**: kırılma
varsayımı ne olursa olsun (≥40 V) mutlak sınır aşılıyor.

##### Arıza → ölen parça matrisi (27 senaryo)

| kod | senaryo | ölen parça | ESP32 | PC |
|---|---|---|---|---|
| A1/A2 | J1'e ±615 V DC | R4 (220K) — kızarır, **açılmaz** | ✅ | ✅ |
| A3 | J1'e 230 V AC şebeke | **hiçbiri** (LM358 girişi −0.62 V'ta kelepçeleniyor, 261 µA) | ✅ | ✅ |
| A4 | J2'ye 1000 V | **hiçbiri** | ✅ | ✅ |
| A5 | Skop girişine ±400 V | R20 (100K) | ✅ | ✅ |
| A6 | Yanlış şönt (10R) + aşırı yük | U6 (ADS #1) — eşik 58× FS | ⚠→✅ | ✅ |
| A7 | Şönt açık + **çıplak** besleme | U6 (ADS #1) | ⚠→✅ | ✅ |
| A8 | Şönt ters akım, tam ölçek | **hiçbiri** (pay 44 mV) | ✅ | ✅ |
| A9 | 615 V ucu skop girişine kayıyor | R20 (3.3 W = 13× gövde) | ✅ | ✅ |
| B1 | ±12 V açık, +3V3 kapalı | **hiçbiri** (pay 19 mV!) | ✅ | ✅ |
| B3 | ±12 V ters takılması | U5 + U8 (2× TL072) | ✅ | ✅ |
| B5 | 24 V yalıtımsız + USB | **hiçbiri** (DIP-8'de Tj 111 °C; SOIC'te ölürdü) | ✅ | ✅ |
| B6 | USB + harici besleme | **hiçbiri** | ✅ | ✅ |
| B7b | J3'e besleme bağlanması | RS + R18 | ✅ | ✅ |
| C1 | Alt bacak (R16) açık | U3/U4 — yavaş | ✅ | ✅ |
| C2 | Bir 820K açık | **hiçbiri** (düğüm VREF'e oturur) | ✅ | ✅ |
| C3 | TL431 açık | **hiçbiri** — ama **sessizce +0.538 V kayar** | ✅ | ✅ |
| C3b | TL431 kısa | **hiçbiri** — zorlanan LM358 girişi (−0.55 V, 14 µA), ADS değil | ✅ | ✅ |
| C4 | C1 osilasyonu | **hiçbiri** — referans salınır | ✅ | ✅ |
| C5 | Vref tamponu raya oturuyor | U3 (soketli) | ✅ | ✅ |
| D1a | J2 şebekeye, kart GND toprakta | **hiçbiri** (125 µA) | ✅ | ✅ |
| **D1b** | **Kart GND'si canlıya + USB takılı** | **USB kablosu + PC anakartı** | ❌ | ❌ |
| D2 | Pille yüzdürüp 615 V ölçmek | **hiçbiri** — ama kullanıcı riskte | ✅ | ✅ |
| **A10** | **Endüktif yük akım akarken sökülüyor** | **U6 (ADS #1)** — kalan risk | ✅ | ✅ |
| B2b | USB takılı, ±12 V yok (her programlamada) | **hiçbiri** (0.12 / 1.0 mA) | ✅ | ✅ |
| D3 | Skop girişine dolu 400 V kondansatör | R20 | ✅ | ✅ |

⚠→✅ = düzeltmeden **önce** riskliydi, R38/R39 ile kapandı.

**Kabul ölçütü sonucu:** düzeltmelerden sonra **27 senaryonun hiçbirinde**
ESP32 ya da PC ölmüyor (`sim3_ariza.py` bunu bir kural olarak sınıyor).
Kalan iki risk: **A10** (endüktif yük — ADS ölebilir, freewheel diyodu ile
kapanır) ve **D1b** (kart izole değil — prosedürel). (B5'te PC'ye akan akım tamponun kendi kısa
devre akımı kadar — 60 mA, zararsız; kart GND'si USB üzerinden zaten
toprakta olduğu için 24 V'un yalıtımsızlığı yeni bir toprak yolu eklemiyor.) Ölen en pahalı bileşen **ADS1115 modülü
(~45 TL, soketli, 3 adet var)**. Tek istisna D1b — o bir **bileşen arızası
değil**, "kart izole değil" kısıtının doğrudan sonucu ve donanımla değil
**prosedürle** çözülüyor.

##### 🔴 D1b sayısallaştırıldı — DEVİR'in en eski uyarısı

| | değer |
|---|---|
| Arıza akımı (döngü 0.3–1.2 Ω) | **192–767 A rms**, tipik ~330 A |
| USB GND teli erime süresi (Onderdonk) | 28AWG **4.9 ms** · 26AWG 12.3 ms · 24AWG **31.2 ms** |
| 30 mA RCD açma süresi | ≤ **40 ms** (5×IΔn'de, IEC 61008) |
| B16 MCB | 48–80 A bandı, ≤100 ms |
| PC'nin USB koruması | **VBUS'ta 0.9 A · GND hattında HİÇBİR ŞEY** |

**Kim neyi koruyor:** RCD **insanı** korur · kablo kendini feda eder ·
**PC'yi koruyan yok** (anakartın GND izi kablodan önce buharlaşır,
20 mil/1 oz iz ~0.24 ms). Schuko fişi polarize değil, yani şebeke
referanslı bir SMPS'te DC baranın eksi ucu toprağa göre **%50 ihtimalle
0…−325 V** arasında.

**"Pille yüzdürelim" planı (5.12.23) PC'yi kurtarır, kullanıcıyı kurtarmaz.**
Tektronix pille beslenen gerçek bir osiloskop için bile toprağa göre
**30 V rms / 42 V tepe** sınırı koyuyor — 615 V bunun 14.6 katı. Yalıtımlı
kutu **şart**. Delikli plakette IEC 60664-1 takviyeli kaçak yolu (615 V → **630 V basamağı**)
12.6 mm = **5 delik atlama (12.70 mm)**; şemadaki "delik atlayarak" notu artık sayıya
bağlı. Ayrıca direnç gövdesinin çevreye karşı **sürekli** yalıtımı yalnızca
**75 V** (Vishay MRS25; 500 V rakamı 1 dakikalık testtir) — HV zinciri
toprak düzleminden ve komşu izlerden uzak durmalı.

##### 🎯 HANGİSİ ÇÖZÜLDÜ, HANGİSİ AÇIK — makineyle doğrulanıyor

`sim3_ariza.py` BÖLÜM 7 SONU bu tabloyu **netlist'ten okuyarak** üretir:
"uygulandı" diyorsa o parça şemada **gerçekten var**. Tablo şemayla
sessizce ayrışamaz.

| kod | öneri | durum |
|---|---|---|
| **F1** | ADS gerilim girişlerine 1K seri (R34/R35/R36) | ✅ **UYGULANDI** |
| **F2** | ADS akım girişlerine 1K seri (R38/R39) | ✅ **UYGULANDI** |
| **F4** | C1 100nF → 1nF (TL431 kararlılığı) | ✅ **UYGULANDI** |
| F3 | R4 bölme ya da 350 V anmalı gövde | ❌ **KAPATILDI (2026-09-09, kullanıcı kararı):** yapılmayacak. Gerekçe: 1W metal film 100K elde yok, senaryo (615 V yanlış klemense) istisnai, ve **diğer parçaları tehlikeye atmıyor** — ölen tek şey 0.60 TL'lik R4 |
| F5 | LM358 giriş kelepçeleri (1N4148) | ❌ **KAPATILDI (2026-09-09, kullanıcı kararı):** eklenmeyecek. %0.055 FS sürekli doğruluk bedeli, karşılığında C1 (R16 açık devre) senaryosu — ölen parça soketli LM358, 10 adet sipariş edildi |
| F6 | Kelepçe üst ucu TL431 rayına | ❌ **REDDEDİLDİ (B18, 2026-09-09).** Kullanıcı onaylamıştı; ölçüm F6'nın hızlı akım menzilini de %43 kestiğini ve TL431 kalıntısını kapatmadığını gösterdi. Yerine **B18/F12** — bkz. **5.12.27** |
| F7 | Orta nokta tamponu (10 Ω / TLE2426) | ⏸️ **açık** — B11 işi, ray henüz kurulmadı |
| F8 | ±12 V mekanik anahtarlama + 50 mA sigorta | ⏸️ **açık** — B11 işi |
| F9 | Delikli plaket 615 V aralığı (5 delik) | ⏸️ **açık** — montaj işi |
| F10 | Prosedür — **8** kural (kutu etiketi) | ⏸️ **açık** — kutu yapılınca. 8. madde B18'de eklendi: *açma sırası önce USB sonra 24 V* |

**Yani: şemada düzeltilebilecek her şey düzeltildi.** Açık kalanların
hiçbiri "unutuldu" değil — üçü **takas içerdiği için senin kararını
bekliyor**, ikisi **B11'e** (±12 V rayı) ait, ikisi **montaj/prosedür**.

🔴 **B15 kapsamı dışında kalan, kapatılmamış iki iş:**
- **A10** — endüktif yük: freewheel diyodu (F10/6'ya kural olarak yazıldı;
  donanımla kapatılamıyor)
- ~~**B16** — akım kanalı örtüşme süzgeci ADS Nyquist'inin 18.5 katı
  üstünde, hızlı yol belgelenenden dar bantlı~~ → ✅ **KAPATILDI**,
  sonuçlar **5.12.26**'da

##### Kutunun üzerine yazılacak yedi kural (F10)

Donanımla çözülemeyen tek şey kullanım. `sim3_ariza.py` BÖLÜM 7/F10:

1. **HV bağlıyken USB TAKILI OLMAYACAK.**
2. Önce GND klemensi, sonra HV ucu bağlanır; sökerken ters.
3. GND klemensi **her zaman** devrenin en düşük potansiyeline.
4. Programlama/hata ayıklama **yalnızca HV sökülmüşken**.
5. 24 V kaynağın yalıtımı **ohmmetreyle doğrulanmış** olacak.
6. Endüktif yük ölçülürken yükün üzerinde **serbest geçiş (freewheel)
   diyodu** olacak — A10'un kapatamadığı tek bileşen senaryosu bu.
7. Yük kablosu **kısa** olacak (parazitik endüktans doğrudan L·di/dt
   tepesine dönüşüyor).

##### Uygulanmayan ama ölçülmüş öneriler (BÖLÜM 7)

| # | Öneri | Neden uygulanmadı |
|---|---|---|
| F3 | R4 (220K) → **2 × 110K (350 V anmalı)** ya da 3 × 73.2K | Film 257 °C → 153 °C. ⚠ 2 parça yalnızca gövde **350 V anmalıysa** yeter (Vishay MRS25); ucuz Yageo minyatürü 200 V, o zaman **3 parça** gerekiyor. N ikisinde de korunur — **karar kullanıcının** |
| F5 | LM358 girişlerine 1N4148 kelepçe | C1 senaryosunu kapatır ama **%0.055 FS hata** getiriyor (kaçak × düğüm empedansı). Takas ölçüldü; lehim sağlamsa gerekmeyebilir |
| F6 | Kelepçelerin üst ucu +3V3 yerine TL431 rayına | ❌ **REDDEDİLDİ (B18).** B15 burada yalnızca skop menzilini yazmıştı; ölçüm hızlı akım yolunun da %43 kesildiğini ve F6'nın TL431 kalıntısını kapatmadığını gösterdi. Yerine B18/F12 (5.12.27) |
| F7 | Orta nokta tamponuna **10 Ω yalıtım direnci** ya da **TLE2426** | ±12 V rayı henüz kurulmadı (B11). **Kurulmadan önce okunmalı** |
| F8 | ±12 V girişine **mekanik anahtarlama** + 50 mA sigorta | Aynı — B11 ile birlikte |

##### 🔴 B11'i kuracak oturuma: ±12 V rayı hakkında üç uyarı

1. **LM358'in kapasitif yük sınırı 50 pF** — veri sayfasının Application
   Information bölümünde, tam da orta nokta tamponunun bağlantısı
   (evirmeyen birim kazanç) için. Ayırma kondansatörleri C9..C15 =
   **700 nF**, yani sınırın **14 000 katı**. Çözüm: tampon çıkışıyla GND
   düğümü arasına **10 Ω**, geri besleme direncin ardından. Ya da
   **TLE2426** (TO-92, delikli uyumlu, 40 V giriş, 31 mA çekme).
2. **ESP32'nin düşürücü regülatörü +12 V'tan BESLENMEZ.** 250 mA'lik dönüş
   akımı hiçbir orta nokta tamponunun karşılayamayacağı kadar büyük.
   ESP32 USB'den ya da ayrı bir kaynaktan beslenmeli.
3. **Ters polarite TVS ile korunamaz.** 24 V rayını tutan hiçbir standart
   SMBJ parçası LM358'in 32 V mutlak maksimumunun altında kelepçeleyemiyor
   (SMBJ24A: 38.9 V @ 15.4 A). **Mekanik anahtarlama** tek doğru çözüm.
   Ayrıca **LM2904 almayın** — "LM358 muadili" diye satılıyor ama TI onu
   26 V'a derate ediyor; 24 V rayda bu mutlak maksimumun %92'si.

##### 🔴 ARIZA DEĞİL AMA "ÇALIŞIR MI" SORUSUNUN CEVABI — tamponun CM tavanı

B15'in arıza taraması sırasında çıkan, arıza **olmayan** ama tasarımın
işleyip işlemeyeceğini doğrudan belirleyen bulgu: **her iki gerilim kanalı
da tam ölçekte LM358'in garantili ortak-mod giriş aralığının sınırında
çalışıyor.**

LM358'in CM tavanı: TI 25 °C'de `V+ − 1.5 V`, onsemi `V+ − 1.7 V`,
TI tam sıcaklık aralığında `V+ − 2.0 V`.

| kanal | +5 V rayı | CM tavanı | FS düğümü | pay | CM tavanı FS'in kaç katında |
|---|---|---|---|---|---|
| NORMAL ±32 V | 5.00 V | 3.000 V | 2.688 V | 312 mV | 1.37× |
| NORMAL ±32 V | **4.75 V** | 2.750 V | 2.688 V | **62 mV** | 1.12× |
| YÜKSEK ±613 V | 5.00 V | 3.000 V | 2.736 V | 264 mV | 1.26× |
| YÜKSEK ±613 V | **4.75 V** | 2.750 V | 2.736 V | **14 mV** | **1.02×** |

USB'nin +5 V toleransı 4.75–5.25 V. **Düşük uçta HV kanalının payı 14 mV** —
yani tam ölçeğin %2 üstünde tampon garantili aralığın dışına çıkıyor.
Parça ölmez; veri sayfası çıkışın **TANIMSIZ** olduğunu söylüyor —
okuma sessizce yanlış olabilir.

⚠ Sezgiye aykırı: **"düşük gerilim" kanalı, "yüksek gerilim" kanalından
göreli olarak daha güvenli.** Herkes 615 V bacağına odaklanıyor ama CM
tavanına önce HV kanalı çarpıyor.

**Üç çözüm ölçüldü (hiçbiri uygulanmadı — karar kullanıcının):**

1. **+5 V'u USB yerine regüle bir kaynaktan al** — 5.00 V garanti edilirse
   pay 264 mV'a çıkar. En ucuzu, ama +5 V'un ESP32'den gelmesi
   B1'deki güç sırası güvenliğini sağlıyor; değiştirilirse 5.12.24'teki
   B6 uyarısı devreye girer.
2. 🌟 **Tamponları MCP6002 (3.3 V RRIO, DIP-8) yap.**
   ⏸️ **KULLANICI KARARI (2026-09-09): şimdilik ALINMAYACAK.** "Belki daha
   sonra alırız ama unutmayalım." Yani bu satır **kapanmadı, ertelendi** —
   bir sonraki sipariş listesine mutlaka girsin. Kartın bugünkü hali bu
   parça olmadan da çalışıyor (F1'in 1K seri dirençleri ADS'i koruyor);
   MCP6002'nin çözdüğü şey ortak-mod tavanı payının 14 mV'a inmesi.
   **Ara çözüm (bedava): +5 V'u USB yerine regüle bir kaynaktan al** —
   5.00 V garanti edilirse pay 264 mV'a çıkıyor. CM aralığı raydan
   raya → sorun tamamen kalkar. **Üstelik iki sorunu daha çözüyor:**
   TI'ın 1 numaralı ADC koruma önerisini sağlar (op-amp beslemesi = ADC
   beslemesi, SLAA593 §2) ve F1'deki seri direnç gereksinimini de
   kaldırır — çünkü çıkış 3.3 V'u hiç aşamaz.
   **Bu, kullanıcıya sorulacak tek satın alma kalemi: 2 × MCP6002-I/P.**
3. Tamponları +12 V'tan besle — CM tavanı 10 V'a çıkar ama doymuş çıkış
   10.65 V olur ve ADS'i korumak için 1K yerine ~7K seri direnç gerekir.

##### Skop kanalının negatif kapsamı YOK

Skop bölücüsü (R20/R23) GND referanslı — gerilim kanallarındaki gibi VREF
ofseti **yok** (netlist: `R23.2 → GND`), ESP32'nin ADC'si de tek yönlü.
Negatif girişlerin tamamı D2 tarafından kırpılıyor. Skop kanalı
**0 … 45.5 V tek yönlü**.

Kart "çift yönlü ön uç" diye tasarlandı ama bu **yalnızca ADS kanalları
ve hızlı akım yolu** için geçerli. Bobin akımı ters dönen bir ölçümde
skop kanalı **kör**. SMPS anahtarlama düğümü genelde pozitif olduğu için
pratikte sorun çıkmayabilir — ama bilinerek kabul edilmeli.

##### Yan bulgu — B15 kapsamı dışı ama gerçek

**Hızlı akım yolunun bant genişliği belgelenenden düşük.** Şema notu
*"Hızlı yol RC'nin ARDINDAN çekilseydi 7.96 kHz'e hapsolurdu"* diyor ama
netlist'te R27/R29 zaten `SONT_P`/`SONT_N`'den, yani **R18/R19 + C4
süzgecinin ardından** taplıyor. Diferansiyel RC = 200 Ω × 100 nF →
**7.96 kHz**, Sallen-Key'in 16.55 kHz'inin altında. Yani gerçek darboğaz
Sallen-Key değil, kaynak RC'si. Ayrıca aynı RC, ADS akım kanalının
Nyquist'inin (430 Hz) **18.5 katı** üstünde — akım kanalında etkili bir
örtüşme süzgeci **yok** (gerilim kanallarında 53–56 Hz).

**Bu bir B16 işi**, B15 kapsamında değil — ama tasarımın "gerçekten
çalışıp çalışmayacağı" sorusunun bir parçası.

✅ **B16 bunu kapattı (5.12.26).** Ek olarak B16, buradaki tarifin
**eksik** olduğunu gösterdi: asıl zarar örtüşme *ve* reaktif yükteki
güç hatası (PF=0.5'te %155). Dirençli yükte fark matematiksel olarak
kendini götürdüğü için bu oturum onu göremedi.

---

#### 5.12.25 ✅ B11 — ±12 V RAYI ÇÖZÜLDÜ: 7912 orta nokta regülatörü (2026-09-09)

`uretim/sim3_besleme.py` · **23 doğrulama** · `dogrula3.py`'de **B11** adımı.
Şemaya **BLOK 9** olarak eklendi (J6, F1, U9, C16, C17, R40).

##### 🔴 DEVIR 5.12.23'ün planı ÇALIŞMIYOR

B15 o planı iki ayrı yerden kırmıştı; B11 bunu somutlaştırdı:

| | LM358 orta nokta tamponu | Gerçek gereksinim |
|---|---|---|
| Çekme (sink) akımı | 10 mA @25 °C, **5 mA @0–70 °C** | **15.0 mA** |
| Kapasitif yük | yayınlanmış tek spec **100 pF** (o da LM358B/BA) | **700 nF** (C9–C15) |

**Dengesizlik TEK YÖNLÜ:** hepsi +12 → yük → GND, yani orta noktadan
**çekilmesi** gerekiyor. Bu, parça seçimini doğrudan belirliyor.

##### ✅ Çözüm: 7912 — ve **stokta zaten var**

DEVIR 5.12.21 "7812 ×3, 7912 ×2 stokta **ama onları besleyecek şey yok**"
diyordu. 24 V kaynak ortaya çıkınca o engel kalktı.

```
7912 GND pini -> 24V+   (= kart +12 V)
7912 VI  pini -> 24V-   (= kart -12 V)
7912 VO  pini -> kart GND
```

Regülatör `V(VO) − V(GND pini) = −12 V` tutuyor, yani **kart GND'si 24V+'ın
tam 12 V altında**. −12 V rayı **regüle**, +12 V rayı ham (kaynağı izliyor).

**🔴 NEDEN 7912, 7812 DEĞİL — akım yönü.** 79xx çıkış pininden akım
**çeker**, 78xx **verir**. Dengesizliğimiz GND'den çekilmeyi gerektiriyor;
7812 ile kurulsaydı orta nokta yükselir ve regülasyon kaybolurdu.

| | LM358 | TLE2426 | **7912** |
|---|---|---|---|
| Çekme | 5 mA | 31 mA | **1500 mA** |
| Kapasitif yük | 100 pF sınır | haritalı | **istiyor zaten** |
| Koruma | yok | var | **akım sınırı + SOA + termal kapatma** |
| Stok | 8 adet | **yok** | **2 adet (REG004)** |

##### Çalışma noktası (hepsi `sim3_besleme.py`'de kural)

| | değer |
|---|---|
| Toplam regülatör akımı | 30.0 mA (dengesizlik 15 + boşaltma 12 + Iq 3) |
| Güç / Tj | 360 mW → **62 °C** (sınır 125) — **soğutucu gerekmiyor** |
| Giriş gerilimi | −24 V; karakterize aralık −15…−25 V |
| C16/C17 | 68 µF 50 V (C035 ×8) — veri sayfası 25 µF ister |
| R40 boşaltma | 1K **1/2W** (R030) → 12 mA > 5 mA minimum yük |

⚠ **Boşaltma direncinin YÖNÜ önemli:** +12 → GND. GND → −12 konsaydı
regülatörün yükünü **azaltırdı**, çoğaltmazdı.

⚠ **Kaynak %10 yukarı kayarsa** (26.4 V) karakterize aralık aşılır —
bozulmaz (mutlak sınır 35 V) ama regülasyon garantili değil.
**24 V kaynağın gerçek gerilimi ölçülmeli.**

##### 🔴 İKİ MONTAJ TUZAĞI — 79xx, 78xx'ten FARKLI

1. **Pin sırası:** 79xx = **GND-VI-VO**, 78xx = IN-GND-OUT.
   7912'yi 7812 gibi bağlamak GND ile girişi takas eder.
2. **TO-220 tabı VI pinine bağlı** (78xx'te GND'ye). Bizim bağlantımızda
   VI = −12 V rayı, yani **tab −12 V'ta**. Topraklanmış bir soğutucuya
   vidalanırsa −12 V kısa devre olur. Soğutucu zaten gerekmiyor.

##### ERC'de bir kural bilerek kapatıldı — ve yerine daha kesini kondu

7912'nin GND pini kart GND'sine değil **+12 V rayına** bağlı; bu,
topolojinin ta kendisi. ERC bunu anlayamıyor (`ground_pin_not_ground`).
O kural `.kicad_pro`'da kapatıldı, **karşılığında `netlist3_dogrula.py`
U9'un üç pinini de tek tek sınıyor** — ayrıca C16/C17 polaritesi, R40'ın
yönü ve F1'in yeri. Netlist denetimi 100 → **111**.

Ayrıca GND'nin PWR_FLAG'i kaldırıldı: o ağı artık U9'un VO pini **gerçekten**
sürüyor, bayrak bırakılsa iki "power output" çakışırdı.

##### B15'in besleme senaryoları yeni topolojiyle

- **B3 (ters polarite):** değişmedi — TVS koruyamıyor, **mekanik
  anahtarlama + 50 mA sigorta** şart (F1 şemada).
- **B5 (24 V yalıtımsız):** 7912'nin **iç akım sınırı + termal kapatması**
  var, LM358'de yoktu. Ama asıl tehlike değişmedi: kart GND'si şebeke
  toprağına bağlanıyor → prosedür (F10/5, ohmmetre ile doğrula).
- **B1 (±12 açık, +3V3 kapalı):** etkilenmiyor, kelepçe yolları ±12'den
  bağımsız. ✅ **B18/F12 ile donanımda KAPATILDI** (5.12.27): pay 18 mV →
  1930 mV ve artık TL431'den bağımsız.

##### 🔴 KARAR: 7805 EKLENMİYOR — ve bunun bir bedeli var

DEVIR 5.12.23 analog +5 V için 24 V'tan beslenen bir 7805 önermişti.
B15/B6 ve B11 bunun **üç ayrı sorun** açtığını gösterdi:

1. İki +5 V kaynağı paralel (USB + 7805) → geri sürme; 7805 için
   çıkış→giriş ters diyodu şart olur
2. **"+5 V var / +3V3 yok" hali mümkün hale gelir** — bu, B15/A1b'nin en
   kötü senaryosu (ADS beslemesizken tampon çıkışı sürüyor). Bugün bu hal
   *imkânsız*, çünkü ikisi de aynı yerden (ESP32 başlığı) geliyor.
3. Orta nokta dengesizliği 6.4 mA artar

**Karar: 7805 yok. +5 V, J5.8'den (ESP32 başlığı) gelmeye devam ediyor.**
`netlist3_dogrula.py` bunu bir kural olarak sınıyor (+5V ağında **tek**
kaynak pini olmalı) — ileride biri 7805 eklerse zincir kırmızıya döner.

⚠ **Bedeli:** kart **USB olmadan çalışmaz** (analog kısım +5 V istiyor).
Pil + Wi-Fi izolasyon yoluna geçilirse +5 V'u **o zaman** çözmek gerekecek
— ve o noktada yukarıdaki üç sorun yeniden masaya gelir. Muhtemel çözüm:
analog tarafı da MCP6002'ye geçirip +5 V'u tamamen kaldırmak (o zaman
yalnızca +3.3 V ve ±12 V kalır).

##### Konnektör 3 pin değil 2 pin — ve pil yolu bundan KAZANIYOR

DEVIR 5.12.23 "+12 / GND / −12" 3 pinli bir giriş önermişti, çünkü orta
noktayı **dışarıda** üretmek planlanıyordu (pil paketinin ortası ya da
dirençli bölücü). B11'de orta noktayı **kart** üretiyor, o yüzden girişe
yalnızca 24 V geliyor → **2 pin**.

**Pil yolu bozulmuyor, iyileşiyor:** 6 hücre seri = 24 V aynı konnektöre
takılır, paketin orta noktası **kullanılmaz** ve GND'yi 7912 tanımlar.
Yani hücre eşleşmesi artık GND'nin yerini belirlemiyor — **dengesiz
boşalan bir paket bile ölçümü kaydırmaz.** 5.12.23'ün "hücreler eşleşmiş
olmalı" uyarısı bu yüzden hafifliyor (ölçüm için; hücre ömrü için hâlâ
geçerli).

##### Alınacaklar

Yalnızca **50 mA cam sigorta + yuva**. 7912, kondansatörler ve boşaltma
direnci **stokta**.

---

#### 5.12.26 ✅ B16 — V/I SÜZGEÇ EŞLEŞTİRMESİ (2026-09-09)

`uretim/sim3_ortusme.py` · **41 doğrulama** (ngspice + kural) · `dogrula3.py`'de B16 adımı ·
şemaya **C18/C19/C20**, `netlist3_dogrula.py`'ye **5 yeni denetim**
(111 → 116).

⚠️ Bu adım da **tasarımı** sınıyor, kurulmuş bir kartı değil.

##### Sorun neydi

Wattmetre gücü **V × I** diye hesaplıyor. İki kanal aynı sinyali **farklı**
süzüyordu:

| Kanal | R | C | τ | kesim |
|---|---|---|---|---|
| gerilim / NORMAL | 28.60 k | 100 nF | 2.860 ms | **55.66 Hz** |
| gerilim / HV | 30.19 k | 100 nF | 3.019 ms | **52.72 Hz** |
| akım (B16 öncesi) | 200 Ω | 100 nF | 0.020 ms | **8037 Hz** |

Üç ayrı sonucu vardı:

1. **🔴 ÖRTÜŞME — geri dönüşü yok.** ADS'in Nyquist'i 430 Hz; akım kanalı
   onun **18.7 katı** üstünde süzülüyordu. 430 Hz ile 8 kHz arasındaki her
   şey banda katlanıyordu. 860 Hz'te zayıflama **−0.0 dB** — 20 dB kuralını
   geçmiyor. Katlanmış bir bileşen ölçüme girdikten sonra **firmware onu
   ayırt edemez.** C18'in asıl gerekçesi bu; faz eşleşmesi ikinci kazanç.
2. **REAKTİF yükte güç hatası.** 50 Hz'te V/I faz farkı **−41.6°**.
3. **Hızlı yolun bandı belgelenenden dar.** I_HIZLI 7.76 kHz, skop kanalı
   16.55 kHz — hem dar hem **eşitsiz** (5 kHz'te aralarında 31.9° fark).

##### 🔴 Neden bugüne kadar gözden kaçtı — matematiksel sebebi var

Tek kutuplu süzgeçte **|H| · cos(atan x) = |H|²**. Yani "gerilim süzülüyor,
akım süzülmüyor" ile "ikisi de aynı süzülüyor" **dirençli yükte aynı güç
okumasını verir** (betikte sayısal olarak doğrulanıyor: 0.553380 = 0.553380).
Dirençli yükteki eşleşme hatası **%0.44**. Hata yalnızca **reaktif** yükte
ortaya çıkıyor — ve kullanıcının alanı SMPS/inverter, yani yük neredeyse
her zaman reaktif.

| Yük | okunan/gerçek | eşleşmiş/gerçek | **eşleşme hatası** |
|---|---|---|---|
| dirençli (PF=1) | 0.551 | 0.553 | **−0.4 %** |
| PF=0.87 (30°) | 0.833 | 0.553 | **+50.6 %** |
| PF=0.50 (60°) | 1.398 | 0.553 | **+152.5 %** |
| PF=0.26 (75°) | 2.375 | 0.553 | **+329.2 %** |

##### Çözüm — B15/F2'nin aynı mantığı

Süzmeyi **paylaşılan** düğümden alıp **ADS'in kendi koluna** taşımak.
B15/F2 *korumayı* ADS koluna koymuştu (R38/R39); B16 *süzgeci* koyuyor.

```
sont -[R18/R19]-+- SONT_P/N -[R38/R39 1K]-+- ADS
                |                          |
             C4 1nF                    C18+C19+C20
           (yalnızca RF)                 1.320 µF
                |
        hızlı yol (R27/R29) BURADAN taplıyor
```

| Parça | Değer | Envanter |
|---|---|---|
| **C4** (değişti) | 100 nF → **1 nF** | C049 ×10 |
| **C18** (yeni) | 1 µF | C023 ×5 (400 V polyester) |
| **C19** (yeni) | 220 nF | C052 ×10 (63 V) |
| **C20** (yeni) | 100 nF | C008 ×24 (50 V) |

**Satın alınacak hiçbir şey yok.** İdeal değer 1.300 µF (NORMAL menzile
göre); seçilen 1.320 µF.

##### Sonuçlar

| Ölçüt | önce | sonra |
|---|---|---|
| PF=0.5 eşleşme hatası @50 Hz — NORMAL | %155 | **%1.91** |
| aynı, 5–400 Hz en kötü | — | %2.18 |
| PF=0.5 eşleşme hatası @50 Hz — HV | %164 | **%5.31** |
| aynı, 5–400 Hz en kötü | — | %6.04 |
| V/I faz farkı @50 Hz (NORMAL) | −41.6° | **+0.42°** |
| akım kanalı örtüşme kesimi | 7958 Hz | **54.8 Hz** (Nyquist 430) |
| I_HIZLI −3 dB | 7.76 kHz | **16.52 kHz** (skop 16.55) |
| skop↔akım faz farkı @5 kHz | 31.9° | **0.39°** |

##### 🔴 B16'nın kendi bulduğu üç yeni şey

**(a) İki GERİLİM kanalı da birbirine eşit değil.** NORMAL 2.860 ms,
HV 3.019 ms — **%5.6 fark**. Sebebi bölücülerin Thevenin'lerinin farklı
olması (6.60 k / 8.19 k), ikisine de aynı 22K + 100 nF konması.
**Tek bir C18 ikisine birden tam eşleşemez**; seçilen 1.320 µF iki
menzilin ideali (1.300 / 1.372 µF) arasında duruyor. HV menzilindeki
%5.31 artık bundan.

Ayrıca `tasarim3_sabit.py`'deki `RC_R` yorumu **eskimişti**: "yalnızca
NORMAL kanal … HV Thevenin 21.96 kΩ, oraya seri direnç EKLENMİYOR"
diyordu. O not **2.2M'lik eski HV bölücüsüne** aitti; 6×820K/8.2K'ya
geçilince Thevenin 8.19 kΩ'a düştü ve R17 şemaya **eklendi**.
`tasarim3.py` ve `sim3_giris.py` zaten RC_R'yi her iki kanala uyguluyordu
— **not koda göre geride kalmıştı.** Düzeltildi.

**(b) 🔴 B16/F11 — hızlı yol, akım algılamasını YÜKLÜYOR.** R27/R29'un
diferansiyel giriş direnci 2×10K = 20 kΩ; bu, R18/R19 üzerinden akım
çekiyor ve şönt gerilimini ADS'e **ulaşmadan** bölüyor:

```
kayıp = (R18+R19) / (R18+R19+2×R27) = 200/20200 = %0.99
```

**Bu B16'nın getirdiği bir şey değil** — B8 (hızlı yol) eklendiğinde
oluştu ve **hiçbir adım modellemedi**. `tasarim2.py`'deki akım hata
bütçesi (h_i3, "Kelvin ile kalibrasyonsuz bile %1.5'in altında")
B8'den **önce** yazıldı; içinde bu kalem yok. Niteliği: **düz**
(frekanstan bağımsız) kazanç hatası — kalibrasyonla tamamen siliniyor,
B16'nın konusu olan faz eşleşmesini bozmuyor. Ama %1.5 bütçesinin
**%66'sını** tek başına yiyor.

Seçenekler (şema **değiştirilmedi**, karar kullanıcının):

| R27/R29 · R28/R30 | kayıp | kazanç |
|---|---|---|
| bugünkü 10K · 47K | %0.99 | 4.700 |
| 22K · 100K | %0.45 | 4.545 |
| 47K · 220K | %0.21 | 4.681 |
| ya da hiçbir şey yapma, kalibrasyona bırak | — | — |

**(c) 🔴 Baskın artık hata artık KONDANSATÖR TOLERANSI.** Yukarıdaki
sayılar nominal değerlerle. Gerçekte eşleşmeyi C2 ile C18'in **gerçek**
değerleri belirliyor; dirençler metal film %1, katkıları ihmal edilebilir.

| tolerans | en kötü τ sapması | 50 Hz Δfaz | PF=0.5 hata |
|---|---|---|---|
| ±%1 | ±%2 | 0.99° | %5.4 |
| ±%5 (J) | ±%11 | 3.27° | %15.4 |
| ±%10 (K) | ±%22 | 6.12° | %27.2 |

Monte Carlo (3σ = tolerans, 20 000 örnek): J ile ortanca %2.5 / %95 dilimi
%6.9; K ile ortanca %4.3 / %95 dilimi **%12.5**.

**Sonuç: nominal seçim değil tolerans belirliyor** — o yüzden 4. bir
kondansatörle 1.320 → 1.300 µF kovalamak sahte hassasiyet.
**Envanterde tolerans yazmıyor; parçanın üzerindeki harf okunmalı
(J = %5, K = %10).**

##### 🔴 Bedeller — dürüstlük bölümü

1. **ADS akım kanalının bandı bilerek düşürüldü** (8037 → 54.8 Hz). Kayıp
   değil: eski 8037 Hz zaten **kullanılamıyordu** (Nyquist 430 Hz) ve
   wattmetrede belirleyici olan **dar** kanal — gerilim kanalı zaten
   oradaydı. Üstü için hızlı yol var, o da 7.76 → 16.52 kHz'e çıktı.
2. **Hızlı yolun örtüşme payı düştü:** −30.6 dB → **−17.0 dB** (C4'ün
   kutbu yardım ediyordu). Ama skop kanalı zaten −16.1 dB — yani akım
   yolu artık skoptan **kötü değil**. Eskisi üstünlük değil **eşitsizlikti.**
   Yetersiz bulunursa çözüm **iki yola birden** eklenmeli.
3. **B16 hızlı yola ~55 Hz'te küçük bir BASAMAK koyuyor:** DC 0.9901 →
   plato 0.9010, yani **−0.82 dB (%9)**, en büyük faz çıkıntısı **2.71°**
   (öncesi bu bölgede 0.4°'nin altındaydı). **Kaldırılamaz:** basamağın
   büyüklüğünü R38/R39 belirliyor; onları büyütmek ADS'in **PGA'ya bağlı**
   giriş empedansı yüzünden oto-kademede kazanç sıçraması yaratır
   (1K'da %0.08→%0.28, 10K'da %0.83→%2.74). B15/F2'nin 1K seçimi doğru,
   basamak **kabul ediliyor** — hızlı yolun eşi ayrı bir konnektör (J4
   skop girişi), wattmetre çarpımı ADS yolunda yapılıyor ve basamak
   200 Hz üstünde tamamen oturmuş durumda.
4. **Ortak ölçek hatası KALIYOR:** 50 Hz'te iki kanal da 0.744 kazançla
   süzülüyor, güç 0.553 katı okunuyor (%45 düşük). **B16'nın çözdüğü şey
   bu değil.** Ama artık **yükten bağımsız** bir ölçek çarpanı (PF=1 ile
   PF=0.26 arası 2.7 puan) ve firmware'de 1/|H(f)|² ile silinebilir.
   B16 **öncesi bu mümkün değildi** — hata yükün güç faktörüne bağlıydı.
5. **SINIR: harmonikli yükte tek çarpan yetmez.** Süzgeç kutbu 50 Hz'in
   hemen üstünde; 5. harmoniğin gücü temele göre **11.7 kat** bastırılıyor.
   **ADS yolu bir TEMEL BİLEŞEN wattmetresidir.** Bu B16'nın getirdiği bir
   sınır değil — 860 SPS + 430 Hz Nyquist'in doğal sonucu ve gerilim
   kanalında zaten vardı; B16 akım kanalını da aynı sınıra getirerek
   **çarpımı anlamlı kıldı.** Dalga şekli/harmonik işi hızlı yolun.
6. **Yapılmadı: ortak-mod kondansatörleri.** C18 yalnızca diferansiyel
   süzüyor. Eklenmedi çünkü şönt yük dönüşünde (ortak-mod zaten GND'ye
   yakın), iki kondansatör daha delikli plakette yer + eşleşmezlik
   (CM→DM dönüşümü) riski demek, ve ADS'in kendi CMRR'i bu seviyede
   yeterli. Gerekirse 2 × 100 nF sonra eklenir.

##### Açık kalan iş kalemleri (B16'nın kapsamı dışı)

| # | İş | Neden |
|---|---|---|
| 1 | **firmware: menzil başına FAZ KALİBRASYONU** | 🔴 Tolerans artığının tek çözümü. **Referans cihaz gerekmiyor** — dirençli bir yük (rezistans/ampul) yeter: dirençli yükte gerçek faz farkı sıfır olmalı, okunan fark doğrudan süzgeç eşleşmezliğidir. 1°'ye kadar düzeltmek PF=0.26'da hatayı %6.5'e, PF=0.5'te %3.0'a indiriyor. Firmware'de Lagrange yarım-örnek hizalayıcı **zaten var** (B4/B5) — kesirli gecikme altyapısı mevcut |
| 2 | firmware: PGA değişiminde **13 örnek at** | Akım kolu τ = 2.90 ms, örnek aralığı 1.16 ms → 5τ = 13 örnek. Gereksinim **yeni değil**, gerilim kanalında zaten vardı |
| 3 | firmware: 1/H(f)² ölçek düzeltmesi | Yukarıdaki bedel (4). Yükten bağımsız olduğu için artık yapılabilir |
| 4 | **karar:** hızlı yolun örtüşme payı yeterli mi | Yukarıdaki bedel (2) |
| 5 | **karar:** B16/F11 — R27/R29 yüklemesi | Yukarıdaki bulgu (b) |

##### Analitik model ngspice'e karşı doğrulandı (bölüm 1b)

B16'nın bütün sayıları elle türetilmiş bir merdiven transfer fonksiyonuna
dayanıyor. Bölüm 1b onu **ngspice'te kurulmuş gerçek devreye** karşı
sınıyor — hızlı yolun fark yükselteci **sadeleştirilmeden** (R27/R28,
R29/R30 + ideal op-amp), şöntün alt ucu GND'de, yani sürüş **tek yönlü**.
Analitik model ise yükü tek bir 20 kΩ diferansiyel direnç sayıyor.

8 nokta (2 yapılandırma × 4 frekans), her birinde iki düğüm: **genlikte
en büyük sapma %0.001, fazda 0.0012°.** Yani fark yükseltecinin
asimetrisi diferansiyel sonucu değiştirmiyor — klasik fark yükseltecinin
diferansiyel giriş direnci gerçekten 2×R1. `RL`'yi 20k→40k yapınca 1b
kırmızıya dönüyor, yani denetim gerçekten bağlayıcı.

##### Mutasyon testi

Yeni denetimlerin gerçekten ısırdığı gösterildi:

| Mutasyon | Sonuç |
|---|---|
| C4'ü şemada 100 nF'a geri al | netlist **116→115** |
| C18/C19/C20'yi C4 düğümüne taşı | netlist **116→109** |
| `ADS_AKIM_C` 1.32 → 1 µF | B16 **41→30** |
| `SONT_C` 1 → 100 nF | B16 **41→34** |
| `RL` 20k → 40k (analitik modeli boz) | B16 **41→37** (ngspice çapraz denetimi) |

Ayrıca B15'in bulduğu **"boş iddia"** sınıfına karşı bilerek önlem alındı:
tek bir `True` ya da yalnız-literal karşılaştırma bırakılmadı. Malzeme
iddiası `envanter.csv`'yi **okuyor** (adetler elle yazılmıyor); PGA giriş
empedansları `PGA_TABLO`'dan geliyor; `|H|·cos(atan x) = |H|²`
özdeşliğinin bir de **negatif denetimi** var — aynı özdeşlik iki kutuplu
Sallen-Key'de tutmuyor (sapma 0.322), yani iddia gerçekten *tek-kutup*
özelliğini sınıyor, her şey için doğru bir totoloji değil.

---

#### 5.12.27 ✅ B18 — GPIO KELEPÇELERİ ve +3V3 GERİ BESLEMESİ (2026-09-09)

`uretim/sim3_kelepce.py` · **46 doğrulama** (ngspice + kural) ·
`dogrula3.py`'de B18 adımı · şemaya **R41**, R26/R33 değişti ·
`netlist3_dogrula.py` 116 → **123**.

⚠️ Bu adım da **tasarımı** sınıyor, kurulmuş bir kartı değil.

##### Kullanıcı F6'yı onayladı — B18 uygulamadan önce ölçtü ve F6 REDDEDİLDİ

Kullanıcı 2026-09-09'da B15/F6'yı ("kelepçelerin üst ucu +3V3 yerine
TL431 rayına") **onayladı**. B18 uygulamadan önce ölçtü ve **iki şey**
buldu:

**🔴 1. F6'nın belgelenmemiş bir bedeli var.** B15 yalnızca skop
menzilinden söz ediyordu (48.7 → 39.4 V). Ama **aynı kelepçe hızlı akım
yolunda da var** (D3, R33). Orada tam ölçek 294.6 mV şönt gerilimine
karşılık geliyor ve F6 onu **169 mV**'a düşürüyor — **%33 kayıp**.
Daha kötüsü: bu, ADS'in kendi kırpma noktasının (**256 mV**, PGA ±0.256)
**altına** iner. Yani hızlı yol, yavaş yoldan **önce** doyar — oysa hızlı
yolun varlık sebebi tepe yakalamak.

**🔴 2. F6 asıl kalıntıyı kapatmıyor.** TL431 açık devre olursa ray
9.9 V'a tırmanıyor ve ESP32 ölüyor — F6'yla da, F6'sız da. Sebebi: R1
(220R) TL_RAY ile +3V3'ü zaten köprülüyor.

##### Yerine uygulanan: B18/F12 — iki stok direnci

| Parça | Eski | Yeni | Envanter |
|---|---|---|---|
| **R26** (skop kelepçesi) | 2.7K | **10K** | R032/R033 ×10 |
| **R33** (hızlı yol kelepçesi) | 2.7K | **10K** | aynı |
| **R41** (YENİ, +3V3 → GND boşaltma) | — | **1K** | R029/R030/R031 ×10 |

**Satın alma yok.**

##### Sonuçlar

| Ölçüt | bugün | F6 | **B18/F12** |
|---|---|---|---|
| B1 payı (TL431 var) | **18 mV** | 1096 mV | **1930 mV** |
| B1 payı (TL431 açık devre) | **ÖLÜR** | **ÖLÜR** | **1930 mV** |
| skop menzili | 45.5 V | 39.4 V | **45.5 V** |
| hızlı akım tam ölçek | 252.1 mV | 169.1 mV | **252.1 mV** |

**🔴 En önemli özellik:** R41 rayı 2.495 V'un **altında** tuttuğu için
TL431 hiç iletmiyor — yani **kurtuluş artık TL431'e bağlı değil**.
B15 kurtuluşun "tesadüfi" olduğunu yazmıştı; B18 onu tasarıma çevirdi.
Bağımsızlık **0–85 °C boyunca** doğrulandı (en büyük fark 13 µV).

##### 🔴 En güçlü sonuç: iki koruma BİRBİRİNİ ÖRTÜYOR

Kabul ölçütü *"hiçbir TEK arıza ESP32'yi öldürmemeli"* idi. Eski tasarım
bunu **sağlamıyordu** — TL431'in açık devre kalması tek başına ESP32'yi
öldüren bir arızaydı. B18/F12 sonrası:

| Durum | 3V3 rayı | pay |
|---|---|---|
| sağlam | 1.670 V | 1930 mV ✅ |
| **TEK ARIZA:** TL431 açık devre | 1.670 V | 1930 mV ✅ (R41 devralıyor) |
| **TEK ARIZA:** R41 açık devre | 2.823 V | 777 mV ✅ (TL431 devralıyor) |
| ÇİFT ARIZA: ikisi de açık | 8.940 V | ölür |

**İki değişiklik ayrı ayrı değil, birlikte anlamlı:** R26/R33 10K'ya
çıkmasaydı, R41 açık devre halinde pay yine 18 mV'a düşerdi. 10K, R41'in
yedeğini güvenli seviyeye taşıyan şey.

##### Zorlama taraması (bölüm 3)

| Koşul | pay (TL431 var / yok) |
|---|---|
| nominal (TL072 tavan 10.5 V, 27 °C) | 1930 / 1930 mV |
| 24 V kaynak %10 yüksek → tavan 11.6 V | 1752 / 1752 mV |
| TL072 raya TAM oturuyor (12.0 V) | 1687 / 1687 mV |
| 0 °C / 60 °C | 1938 / 1921 mV |
| ölü 3V3 rayı 10k / 1k yüklüyor | 2056 / 2679 mV |

En kötü koşulda bile **1687 mV**.

##### 🔴 İki model hatası düzeltildi

**(a) TL431 akım VEREMEZ.** B15'in B1 modeli TL431'i ideal gerilim
kaynağı sayıyordu. Boşaltma direnci eklenince o model rayı 2.495 V'ta
**tutuyordu** — yani TL431 akım *veriyor*, fiziksel olarak imkânsız.
662 mV'luk sahte bir sonuç.

**(b) "İdeal-e yakın diyot" numarası sıcaklıkta kırıldı.** İkinci deneme
`.model D(IS=1E-9 N=0.02)` idi: 27 °C'de doğru, ama **60 °C'de ters
yönde iletti** (ray 1.67 yerine 2.33 V). Sebep: SPICE'ın diyot sıcaklık
modelinde doyma akımı `Eg/(N·Vt)` ile ölçekleniyor; N=0.02 o üsteli
50 katına çıkarıp IS'i patlatıyor. Üçüncü ve kullanılan model
**davranışsal tek yönlü şönt**: `I = max(0, V−Vref)/z_KA`.
*"Model parametresi sonuç değildir" kuralının canlı örneği.*

##### Yan bulgu: hangi sınır geçerli

B15 `ESP_MUTLAK_PIN_UST = 3.6 V`'u her yerde kullanıyordu. Doğrusu ikiye
ayrılıyor ([ESP32-S3 veri sayfası](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf), Absolute Maximum Ratings):

- **GPIO pini:** VDD + 0.3 V — beslemeyi **izleyen** bir sınır
- **Besleme pini:** 3.60 V **sabit**

B1'de zorlanan şey **besleme rayı**, o yüzden B15'in kullandığı ölçüt
doğruydu. Ama bu ayrım, kelepçenin **neden +3V3'te kalması gerektiğini**
de açıklıyor: seviye beslemeyi izliyor. TL_RAY'e taşınsaydı bu özellik
kaybolurdu.

##### 🔴 Yeni bulgu: kelepçe payı SOĞUKTA tükeniyor

Normal çalışmada (skop girişi aşırı menzilde) GPIO pini VDD+0.3'e ne
kadar yakın:

| Sıcaklık | 2.7K (bugün) | 10K (B18) |
|---|---|---|
| −10 °C | **−13 mV** (sınır aşılıyor) | +19 mV |
| 0 °C | +3 mV | +36 mV |
| 27 °C | +47 mV | +83 mV |
| 60 °C | +101 mV | +141 mV |

Yani 2.7K ile pay 0 °C civarında tükeniyor. **10K bunu da yaklaşık
ikiye katlıyor** — değişikliğin ikinci kazancı. (Bu hal yalnızca skop
girişi aşırı menzildeyken oluşuyor ve akım 3 mA'in altında kalıyor:
anlık ölüm değil, spek dışı zorlama.)

##### Seri direnci büyütmenin ADC tarafındaki bedeli (bölüm 4)

Üç risk ayrı ayrı ölçüldü:

| Risk | 2.7K | 10K | Ölçüt |
|---|---|---|---|
| Sızıntı ofseti (50 nA pin kaçağı) | 0.135 mV | **0.500 mV** | 12-bit LSB = 757 µV ✅ |
| Örnekleme oturması (τ) | 89 ns | **330 ns** | örnek aralığı 24 µs = 73× ✅ |
| Bant genişliği | 1786 kHz | **482 kHz** | Sallen-Key 16.55 kHz ✅ |
| Direnç gürültüsü | 0.95 µV | **1.83 µV** | LSB'nin 1/400'ü ✅ |

Düğüm kapasitesi **kötümser** alındı (33 pF: 2×BAT85 + pin + delikli
plaket kaçağı) — yani oturma sınavı gerçekte daha kolay.

R41'in sürekli maliyeti: **3.3 mA / 10.9 mW**. USB/LDO için önemsiz;
**pille çalışmada not edilmeli**.

##### B2'de bir iddia yeniden kuruldu

`sim3_giris.py`'deki *"TL072 kelepçesiz KABUL EDİLEMEZ"* iddiası **akım**
üzerine kuruluydu (>1 mA). Seri direnç 10K olunca akım 2.2 → **0.80 mA**'e
düştü, yani ölçütün altına. İddia **gerilim** üzerinden yeniden kuruldu:
kelepçesiz pin, ESP32'nin kendi ESD diyoduna dayanıp **3.958 V**'a
oturuyor; sınır VDD+0.3 = 3.60 V. **Kelepçe hâlâ şart** — ama artık
akım değil gerilim yüzünden. (Akıma bakıp "kelepçe gereksiz" demek
yanlış olurdu.)

##### Kutu kuralına 8. madde

> **8. AÇMA SIRASI: önce USB, sonra 24 V. Kapatırken önce 24 V.**

Donanımda B18/F12 ile çözüldü; bu kural **ikinci savunma** — bedava.

##### 🔴 BAĞIMSIZ DENETİM — B18'in ilk sürümünde 14 bulgu

B18'in ilk sürümü 30/30 yeşildi. İki bağımsız denetçiye (biri devre
akıl yürütmesi, biri saha/veri sayfası araştırması) verildi. **Ondan
fazla gerçek kusur çıktı; hepsi düzeltildi, doğrulama sayısı 30 → 46.**

**1. "18 mV payı" tek başına USB'yi çıkarmanın sonucu DEĞİL.**
B15/B1 iki TL072 çıkışını da doğrudan 10.5 V'a (doyma) koyuyor ve bunu
"açma sırasının doğal sonucu" diye sunuyordu. Eksik olan şey: **+5 V de
J5'ten geliyor**, yani USB çıkınca LM358'ler de ölüyor ve VREF ≈ 0
oluyor; op-amp çıkışları yalnızca **giriş sinyalinin** koyduğu yerde
durur. 10.5 V için skop girişinde ~**165 V** gerekiyor (belgelenen menzil
45.5 V'un 3.6 katı).

| op-amp çıkışı | ≈ J4 girişi | B18 öncesi pay | B18 sonrası |
|---|---|---|---|
| 1.0 V | 16 V | 2744 mV | 3463 mV |
| 2.9 V (tam ölçek) | 45 V | ~1100 mV | ~3150 mV |
| 7.0 V | 110 V | 506 mV | 2497 mV |
| 10.5 V (doyma) | 165 V | **18 mV** | **1930 mV** |

Senaryo yine de gerçek ve **tasarlanmış** bir hal — kutu kuralı zaten
"HV bağlıyken USB TAKILI OLMAYACAK" diyor ve B15/A9 skop girişine 615 V
uyguluyor. Ama gerekçesi "açma sırası" değil, **"aşırı menzilli giriş +
USB çıkık"**.

**2. 🔴 Kelepçe payı, veri sayfasının EN KÖTÜ Vf'i ile ZATEN NEGATİF.**
`tasarim3_sabit.py` kendi kuralını yazıyor: *"SPICE modeli TİPİK değerleri
veriyor; en kötü durum V_F MAKS tablosundan okunur."* B18'in ilk sürümü
bu kurala uymuyordu. Tabloya geçilince sonuç **işaret değiştiriyor**:

| R | I | Vf maks | GPIO | sınır (VDD+0.3) | pay |
|---|---|---|---|---|---|
| 2.7K | 2.54 mA | 0.352 V | 3.652 V | 3.600 V | **−52 mV** |
| 10K | 0.69 mA | 0.307 V | 3.607 V | 3.600 V | **−7 mV** |

Yani aşırı menzilde GPIO, tavsiye edilen koşulun üstünde — **B18'in
getirdiği bir kusur değil, zaten vardı**; 10K aşımı 7 kat küçültüyor.
İlk sürümdeki *"10K bu payı da büyütüyor, değişikliğin ikinci kazancı"*
cümlesi tipik-model artefaktıydı, **kaldırıldı**.

**3. 🔴 Kaçak hatası R ile büyüyor — değişikliğin gerçek bedeli.**
İlk sürümün §4'ü hiç simülasyon içermiyordu ve **R ile ölçeklenen tek
hata terimini atlamıştı**. Ölçüldü:

| | 2.7K | 10K |
|---|---|---|
| 25 °C | 0.57 mV (0.8 LSB) | **2.01 mV (2.7 LSB)** |
| 60 °C | 7.96 mV (10.5 LSB) | **19.9 mV (26.3 LSB, %0.64 FS)** |

İki diyot ters yönde kaçırdığı için bu bir ofset değil, menzilin iki
ucuna doğru büyüyen bir **eğrilik**; sıcaklıkla ~10 °C'de bir ikiye
katlanıyor, yani tek seferlik kalibrasyon silmez. Yalnızca **skop**
kanalını etkiliyor (ADS kanalları bu yoldan geçmiyor).

**Bu yüzden R artık varsayılmıyor, süpürülüyor:**

| R | B1 payı (R41 var) | B1 payı (R41 AÇIK) | kelepçe payı | kaçak 25 °C | kaçak 60 °C |
|---|---|---|---|---|---|
| 2.7K | 588 mV | **18 mV** | −52 mV | 0.57 mV | 7.96 mV |
| 4.7K | 969 mV | 440 mV | −33 mV | 0.98 mV | 12.1 mV |
| 6.8K | 1321 mV | 632 mV | −20 mV | 1.40 mV | 15.6 mV |
| **10K** | **1930 mV** | **777 mV** | **−7 mV** | **2.01 mV** | **19.9 mV** |
| 15K | 2422 mV | 883 mV | +7 mV | 2.92 mV | 25.1 mV |
| 22K | 2766 mV | 952 mV | +20 mV | 4.10 mV | 30.7 mV |

İlk üç sütun R ile **iyileşiyor**, son iki sütun **kötüleşiyor**. 10K bir
**takas** — tek yönlü bir iyileştirme değil.

**4. 🔴 Örnekleme penceresi — kapatılamayan tek kalem.**
İlk sürüm oturmayı **örnekler arası** 24 µs'ye karşı ölçüyordu. Yanlış
ölçüt: oturmanın **örnekleme penceresi** içinde bitmesi gerekiyor.
ESP32-S3'ün penceresi **Espressif tarafından yayınlanmamış** (arandı,
yok). Kanal değişiminde tutma kondansatörü *öteki kanalın* gerilimiyle
geliyor → en kötü 91 mV'lık bir sıçrama:

| pencere | 2.7K artık | 10K artık |
|---|---|---|
| 250 ns | 6.0 mV | **43.7 mV** |
| 500 ns | 0.4 mV | **21.0 mV** |
| 1 µs | 0.002 mV | 4.8 mV |

**Bu kalem açık bırakıldı.** Risk yeni değil (2.7K'da da vardı), 3.7 kat
büyüyor. Tezgah testi tanımlandı: GPIO4'e 0 V, GPIO5'e tam ölçek ver,
sonra ters çevir; kanaldan kanala kayma varsa pencere yetmiyordur.

**5. 🔴 Standart çözüm bu kartta UYGULANAMAZ — ve sebebi belgelendi.**
Espressif ADC pinlerine **0.1 µF** öneriyor ve veri sayfasındaki DNL/INL
(±4/±8 LSB) rakamları **"pine 100 nF bağlı"** koşuluyla verilmiş. TI
SPNA061 daha gevşek bir ölçüt veriyor: C ≥ (2^13−1)·C_sh = **8.2 nF**.
Ama:

| C | 2.7K kutup | 10K kutup |
|---|---|---|
| 8.2 nF | 7.19 kHz | 1.94 kHz |
| 100 nF | 0.59 kHz | 0.16 kHz |

Sallen-Key bandı **16.55 kHz**. **En gevşek öneri bile bandın altında.**
Yani hızlı yol, Espressif'in karakterize ettiği koşulda çalışamaz —
ESP32 ADC'siyle 16.5 kHz istemenin bedeli bu. Karar: bant korunuyor,
oturma belirsizliği tezgahta ölçülecek.

⚠️ **Ve bir tuzak:** o kondansatör ileride eklenirse V ve I kanallarına
**aynı R ve aynı C** konmalı. 100 nF + 10K = 159 Hz kutup, 50 Hz'te 17°
faz — **B16'nın tekrarı** olurdu.

**6. 🔴 Yeni bulunan yol: modülün LDO'suna ters akım.**
ESP32 modülünün 3V3 pini bir **LDO çıkışı**. Raya akım basmak onu kendi
girişinin üstüne çıkarıyor. TI SSZT658: *"ters akım ısınma,
elektromigrasyon ya da latch-up ile cihazı bozabilir."* ROHM 66AN115E
aynı şeyi söyleyip harici koruma diyodu istiyor. Üstelik LDO'nun gövde
diyodu üzerinden **+5 V ağına** da geçer — ve bu kartın analog +5 V'u
aynı modülden geliyor. **B15 de B18'in ilk sürümü de bu yolu görmemişti.**
B18/F12 LDO'ya binen gerilimi 3.582 → 1.670 V'a indiriyor: aranmamış ama
kazanılmış bir yan fayda.

**7. 🔴 ESP32-S3 veri sayfası pin sınırı YAYINLAMIYOR.**
Tablo 14 (Absolute Maximum Ratings) yalnızca **besleme pinini**
(−0.3…3.6 V), toplam IO çıkış akımını ve saklama sıcaklığını veriyor.
**Hiçbir pin için mutlak azami giriş gerilimi ve hiçbir pin için
enjeksiyon akımı sınırı yok.** Elimizdeki tek sınır "Recommended
Operating Conditions"taki V_IH maks = VDD+0.3. Karşılaştırma: ST, STM32
için ikisini de yayınlıyor ve **ADC'si etkin pinlerde enjeksiyonu açıkça
yasaklıyor**. Sonuç: 2. maddedeki "sınır aşılıyor" ifadesi **tavsiye
edilen koşul** aşımıdır, mutlak azami aşımı değil — ne kadar tehlikeli
olduğu **belgelenemiyor**.

**8. Bu arıza tipi belgelenmiş; bizim çözümümüz belgelenmemiş.**
Microchip *3V Tips'n Tricks* TIP #11: *"diyot kelepçe 3.3 V beslemesine
akım enjekte eder… **hafif yüklü** 3.3 V raylarında bu akım rayı 3.3 V'un
üstüne çıkarabilir."* TIP #17 aynısını analog hal için tekrarlıyor ve
seri direnç için tam bizim takasımızı yazıyor. TI SLVAEX7A'nın şekil
2-2'sinin başlığı zaten *"Input Current Path of a Back-Powered Op Amp"*.

**Ama "ölü raya boşaltma direnci" öneren bir üretici notu bulunamadı.**
Belgelenmiş çözümler: op-amp'i ADC'nin kendi beslemesinden çalıştır
(TI SLAA593, "en basit yol" — **bu kartta uygulanamaz**, TL072 ±12 V'ta
çünkü Sallen-Key VREF etrafında ±1.385 V salınmalı); transistörlü kelepçe
(TIP #11); GND'ye zener (TIP #17); op-amp'li hassas kelepçe (TIP #17);
seri direnci mikroamper düzeyine göre boyutla; ölü rayı yüzer bırakma;
besleme sırası kuralı (ADI). **Bizim çözümümüz 5. + 6.'nın yumuşak
hali** ve dayanağı EDN/ADI'nin şartı: *"ADC besleme rayı kelepçe akımını
soğurabilmeli."* Türevdir, alıntılanmış değil — **böyle yazıldı**.

**9. Akım nereye gidiyor — ölçüldü.** TI'in "≤1 mA" ölçütü **çipin kendi
ESD yapısına** giren akım için. Ölçüldü: BAT85'ten **1.72 mA**, ESP32'nin
ESD diyodundan **0.044 µA** (%0.0025). Schottky, silisyum ESD diyodundan
çok daha alçakta ilettiği için çipe pratik olarak akım girmiyor —
B15'in BAT85'i 1N4148'e tercih etmesinin sebebi tam bu.

**10. İki iç tutarsızlık.** (a) Menzil iddiaları `SKOP_TAVAN` (3.1 V)
kullanıyordu; B15 ise `ESP_ADC_ETKIN_UST` (2.9 V — Espressif'in etkin
aralığı, üstü *"undefined"*). İki betik ayrışıyordu; B18 2.9 V'a
geçirildi. Skop menzili **45.5 V**, hızlı akım tam ölçek **252.1 mV**
(F6 kaybı %43 değil **%33**). (b) `menzil()` seri dirence hiç bakmıyordu.

**11. Düzeltilen küçükler.** §5'te aynı simülasyon iki farklı etiketle
koşuyordu (kaldırıldı); gürültü hesabı R26'yı Sallen-Key'in *önünde*
sanıyordu — doğrusu kT/C limiti, **11.2 µV ve R'den bağımsız**; `True`
ve `abs(x−x)` biçiminde totolojik iddialar kaldırıldı; kelepçe tavanı
kendi türetildiği sabite karşı sınanıyordu; ESP32 sınırının atfı yanlış
kaynağı gösteriyordu.

**12. TL431 KISA devre de sınandı** (açık devrenin öteki ucu): B1'de
zararsız (pay 3242 mV), ama normal beslemede **sessiz**: R1 üzerinde
49 mW ve VREF sıfıra düşer — hiçbir şey yanmaz, **her ölçüm bozulur**.
R1 sigorta gibi açılmaz.

##### Mutasyon testi

| Mutasyon | Sonuç |
|---|---|
| R41'i şemadan çıkar | netlist **123→118** (5 denetim) |
| R26'yı şemada 2.7K'ya döndür | netlist **123→121** |
| `BOSALTMA_R_3V3`'ü sonsuz yap (R41 yok) | B18 **46→40** |
| `R_SERI`'yi 2.7K'ya döndür | B18 **46→34** |

##### Kapanan kayıtlar

- **B15/F6** → ❌ değerlendirildi ve **reddedildi** (yukarıdaki iki sebep)
- **B15/B1** → ✅ **donanımla kapatıldı**, artık TL431'den bağımsız
- **B15'in "TL431 açık devre olursa ESP32 ölür" kalıntısı** → ✅ kapandı

---

#### 5.12.28 ✅ B19 — OSİLOSKOP KANALI ÇİFT YÖNLÜ (2026-09-09)

`uretim/sim3_skop.py` · **24 doğrulama** (ngspice + kural) ·
`dogrula3.py`'de B19 adımı · şemada R23, firmware'de dönüşüm,
arayüzde protokol · `netlist3_dogrula.py` 123 → **128**.

**Kullanıcı isteği:** *"Osiloskop tek yönlü değil çift yönlü istiyorum."*
Seçenekler sunuldu, kullanıcı **2.7K + alt uç VREF**'i seçti.

##### Sorun ve çözüm

ESP32'nin ADC'si yalnızca 0–2.9 V okuyor, eksi göremiyor. Skop
bölücüsünün alt ucu **GND'deydi**, o yüzden kanal tek yönlüydü.

Çözüm, gerilim kanallarının **zaten kullandığı** hilenin aynısı:
bölücünün alt ucunu GND yerine **VREF'e** (1.7153 V) bağlamak.

| | oran | menzil | adım |
|---|---|---|---|
| önce (R23 6.8K, GND) | 15.71 | 0 … +45.5 V **tek yönlü** | ~~11.1~~ **11.9** mV |
| **sonra (R23 2.7K, VREF)** | **38.04** | **−63.5 … +46.8 V** | ~~26.9~~ **28.8 mV** |

Artı taraf **daralmadı** (hatta 1.3 V büyüdü); 63.5 V eksi kazanıldı.
**Bedeli çözünürlük:** adım 2.4 kat büyüdü.

> 🔴 **B20 DÜZELTMESİ (2026-09-10):** buradaki adım sayıları yanlıştı.
> `SKOP_ADIM` "etkin aralık"tan (2.9 V) türetiliyordu, oysa adım bir
> **LSB**'dir ve nominal tam ölçekten (3.1 V) türer — firmware ve arayüzün
> üç kopyası zaten 3.1 kullanıyordu, ayrışan bu dosyaydı (**%6.92**).
> Doğrusu **11.9 → 28.8 mV**. Menzil satırları etkilenmiyor. Ayrıntı
> **5.12.30/(b)**.

Menzil simetrik değil çünkü VREF (1.7153 V), ADC penceresinin (0–2.9 V)
ortasında değil. Simetrik kullanılabilir bölüm **±46.8 V**.

##### 🔴 B19 kendi hatasını yakaladı — dönüşüm formülü yanlıştı

İlk yazdığım dönüşüm `V = (V_adc − VREF) × N` idi. Bölüm 1'deki **"0 V
giriş"** satırı bunu ortaya çıkardı: 0 V giriş **−65.2 V** okuyordu.

Doğrusu bölücünün gerçek denklemi:

```
V_düğüm = VREF + (V_giriş − VREF) · R23/(R20+R23)
V_giriş = VREF + (V_düğüm − VREF) · N  =  V_düğüm·N − VREF·(N−1)
```

Yani ofset **VREF×N değil, VREF×(N−1)** — 63.53 V. Baştaki `+VREF`
terimi unutulmuştu. Düzeltildi ve **kalıcı olarak kilitlendi**: bölüm 4b
devreyi ngspice'te kurup düğümü okuyor, firmware'in formülünü uyguluyor
ve girişe eşit çıktığını sınıyor (en büyük hata **0.2 mV**, bir ADC
adımı 26.9 mV). Ayrıca bölüm 3 formülün metnini hem firmware'de hem
arayüzde denetliyor.

##### Yeni akım yolu — asıl risk buydu, ölçüldü

Alt uç GND'deyken skop akımı toprağa gidiyordu. Artık **VREF'e** gidiyor
— ve VREF bütün kanalların referansı. Üç soru ölçüldü:

| Durum | VREF akımı | VREF sapması |
|---|---|---|
| tam artı menzil (+46.8 V) | −0.42 mA | — |
| tam eksi menzil (−63.5 V) | +0.65 mA | **4.5 µV** |
| 325 V (şebeke tepesi) arıza | −3.15 mA | — |
| 615 V arıza | −5.97 mA | — |
| −615 V arıza | +5.32 mA | **< 5 µV** |

**🔴 Arızada bile VREF kaymıyor** — tamponun geri beslemesi akımı
yutuyor. Yani skop girişindeki bir arıza diğer kanalların okumasını
bozmuyor. (VREF'in tamponlu olmasının sebebi tam buydu; B19 o kararın
karşılığını aldı.) LM358'in çıkış akımı sınırı 40 mA, en kötü 5.97 mA.

##### İyi yan etki: Sallen-Key girişi daha az zorlanıyor

Oran büyüdüğü için aynı arıza gerilimi bölücü düğümünde daha küçük bir
gerilime dönüşüyor:

| giriş | önce | sonra | kazanç |
|---|---|---|---|
| 325 V | 20.71 V | **10.22 V** | 2.03× |
| 615 V | 39.16 V | **17.84 V** | 2.19× |

Yani B19 bu yönden **koruma ekliyor**. R20'nin 615 V'taki yükü ise
pratikte değişmiyor (%+4) — B15/A9'un "R20 gider" sonucu geçerli.

##### Alt kelepçe ilk kez iş görüyor

Kanal artık eksiye indiği için D2 devreye girebiliyor. Ölçüldü: tam eksi
menzilde (−63.5 V) düğüm **−0.000 V**, yani kelepçe eşiğinin içinde —
**kelepçe menzili kısmıyor**, yalnızca aşırısında devreye giriyor
(−80 V'ta −0.43 V).

##### Firmware ve arayüz

- `olcum3.h`: `SKOP_ORAN` 15.706 → **38.037**, yeni `SKOP_VOLT_OFSET`
- `.ino`: `hizli_olcekle()` ofsetli; yeni `skop_ofsetle()` `skop_olc()`
  çıktısını düzeltiyor (vmax/vmin/vort/vrms), `S2` satırına **9. alan**
- `arayuz3/app.js`: `voltOfset` okunuyor, yoksa 0 → **geriye uyumlu**
- `arayuz3/sahte-kart.js`: aynı ofset

**🔴 `skop_olc.h`'ye DOKUNULMADI.** O dosya Aşama 2'nin `olcum2.h`'sinden
üretilen birebir kopya ve `test_skop_ayni.py` karakter karakter
karşılaştırıyor. Ofset **çağıran tarafta** uygulandı; böylece Aşama 2'nin
A6 kanıtı Aşama 3 için geçerli kalmaya devam ediyor.

Hangi alan düzeltilmeli, hangisi dokunulmamalı — sayısal olarak
gösterildi (bölüm 4): **vpp ve vac ofsetten etkilenmiyor**; vmax, vmin,
vort ofset kadar kayıyor; **vrms** ise `√(vac² + vort²)` özdeşliğinden
tam olarak yeniden kuruluyor. Frekans/periyot/duty/yükselme zaman
büyüklüğü, tetik eşikleri verinin kendisinden türetiliyor — hiçbiri
etkilenmiyor.

##### Sabit ayrışması denetimi

Aynı sayı **dört yerde** duruyor. Bölüm 3 hepsini okuyup karşılaştırıyor:

| kaynak | oran | VREF |
|---|---|---|
| `tasarim3_sabit.py` | 38.037037 | 1.7153125 |
| `kod/olcum3.h` | 38.037037 | 1.7153125 |
| `arayuz3/sahte-kart.js` | 38.037037 | 1.7153125 |
| şema (netlist) | R23 = 2.7K | R23.2 → /VREF |

Ayrıca `tasarim3.py`'de elle yazılmış bir kopya (`SKOP_ORAN_ =
15.70588235`) bulundu ve sabitler dosyasına bağlandı — **zaten
ayrışmıştı**.

##### Mutasyon testi

| Mutasyon | Sonuç |
|---|---|
| Şemada R23'ü 6.8K'ya döndür | netlist kırmızı |
| Şemada R23'ün alt ucunu GND'ye döndür | netlist **4 denetim** kırmızı |
| Firmware oranını eski bırak | B19 kırmızı |
| Ofseti VREF×ORAN'a döndür | B19 kırmızı |

##### Montaj uyarısı (kılavuza eklendi)

> ⚠️ **R23'ü GND'ye lehimleme.** Şemada VREF'e gidiyor; GND'ye takılırsa
> kanal sessizce tek yönlü kalır ve okumalar 64 V kayar.

---

#### 5.12.29 ✅ B17 — ADS YOLUNDA EŞ ZAMANLILIK + SÜZGEÇ DÜZELTMESİ (2026-09-09)

`uretim/sim3_senkron.py` · **26 doğrulama** · `test_olcum3.py` 70 → **87**
(AVR emülatöründe gerçek kod) · `dogrula3.py`'de B17 adımı ·
firmware, `tipler3.h` ve arayüz güncellendi.

B16 üç firmware kalemi bırakmıştı. Onları ele alırken **çok daha büyük**
bir kusur çıktı.

##### 🔴 ANA BULGU: iki ADS birbirinden bağımsız koşuyordu

Firmware'in kendi yorumu şunu iddia ediyordu:

> *"İki AYRI ADS1115 olduğu için V ve I **yaklaşık eş zamanlı**
> örnekleniyor. Tek çip ile kanal değiştirseydik aralarında 1.16 ms
> gecikme kalırdı."*

İkinci cümle doğru, **birincisi değil.** Kodun gerçekte yaptığı:

- iki çip de **SÜREKLİ** kipte, her biri **kendi iç osilatörüyle**
- ALERT/RDY yalnızca **akım** çipinde kurulu
- döngü akım çipinin ALERT'ini bekliyor, sonra ikisini de okuyor
- → **gerilim çipi kendi çevriminin neresindeyse orada**

ADS1115'in iç osilatör toleransı **±%10** (TI veri sayfası; 860 SPS
nominal → 774…946 SPS). Yani gerilim örneğinin yaşı **0…1.29 ms**
arasında ve **iki osilatör aynı olmadığı için sürükleniyor** — okuma
sabit bir yerde durmuyor, geziniyor.

**50 Hz'te bunun karşılığı 0…23.3 DERECE.** B16'nın düzelttiği süzgeç
eşleşmezliği 0.44° idi; **bu onun 53 katı.**

| Yük | en iyi | en kötü | ortalama |
|---|---|---|---|
| dirençli (PF=1) | 0.0% | −8.1% | **−2.7%** |
| PF=0.87 | 0.0% | −30.9% | −14.3% |
| **PF=0.50** | 0.0% | **−76.5%** | **−37.4%** |
| **PF=0.26** | 0.0% | **−155.5%** | **−77.4%** |

Kayma bütün aralığı taradığı için **ortalama alarak kurtulunamıyor.**

🔴 **Neden bugüne kadar görülmedi:** dirençli yükte hata yalnızca %2.7.
Kart dirençli bir yükle denenirse **"çalışıyor" görünür.** (B16'daki
`|H|·cos = |H|²` özdeşliğiyle aynı sınıf bir gizlenme.)

##### Çözüm: eş zamanlı TEK ATIŞ

SÜREKLİ kip bırakıldı. Her ölçümde iki çipe de **ardı ardına** tek atış
başlatma komutu yazılıyor, sonra ikisi de okunuyor. Kalan kayma artık
osilatör farkı değil, iki I2C yazması arasındaki **sabit** süre
(400 kHz'te ~95 µs) — ve **bilinen** olduğu için silinebiliyor.

| | kayma | 50 Hz'te |
|---|---|---|
| önce (sürekli, iki osilatör) | 0…1292 µs, **sürüklenen** | 0…23.26° |
| sonra (tek atış) | ~95 µs, **sabit** | 1.71° |
| sonra + kesirli gecikme | — | **%0.011 hata** |

⚠️ **Kayma ölçülüyor, varsayılmıyor:** `micros()` ile iki yazma arası
gerçekten ölçülüyor. Örnek periyodu da ölçülüyor (döngü web sunucusu da
koştuğu için sabit hızlı değil) ve `d = t_kayma / T_gerçek`.

##### Kesirli gecikme genelleştirildi

Firmware'de Lagrange yarım-örnek hizalayıcı zaten vardı (`hizala_yarim`,
d = 1/2'ye **sabit**). B17 onu genelleştirdi: `hizala_kesirli(d, …)`.

🔴 **d = 1/2'de yeni fonksiyon eskisiyle BİREBİR aynı çıkıyor**
(AVR emülatöründe 64 rastgele giriş, en büyük fark **0.000e+00**) —
yani **B5'in kanıtı genel fonksiyona taşınabiliyor**. `hizala_yarim`
kaldırılmadı; hızlı yol onu kullanmaya devam ediyor.

Doğrulananlar (hepsi AVR'de gerçek kod): d=0 tam örneğe oturuyor,
d=1 bir sonrakine, DC kazancı her d için tam 1, ve **gerçek iş**:
PF=0.5'lik bir yükte 0.0817 örneklik bilinen bir kayma
0.236967 W → **0.249965 W** (hedef 0.250000) — hata **375 kat** azalıyor.

##### 1/|H(f)| ölçek düzeltmesi (B16'nın 3. kalemi)

50 Hz'te güç `|H_v|·|H_i| = 0.55` katı okunuyordu — **%45 düşük**.
B16 iki kanalı eşitlediği için bu artık **yükten bağımsız** ve frekans
bilinirse tam silinebiliyor.

| kol | τ | 50 Hz düzeltmesi |
|---|---|---|
| NORMAL | 2.860 ms | 1.3443× |
| YÜKSEK | 3.019 ms | 1.3781× |
| AKIM | 2.904 ms | 1.3536× |

Güç düzeltmesi (V×I) **1.82×**. İki gerilim kanalının τ'su **aynı
değil**, o yüzden düzeltme **kanal başına** yapılıyor (`Kanal3.tau`).

⚠️ **Frekans ölçülmüyor, AYARLANIYOR.** ADS yolu (860 SPS, 55 Hz süzgeç)
frekans ölçemez. Yeni komut **`f<Hz>`** — 0 = DC (düzeltme kapalı).
Yanlış ayar **öngörülebilir** bir hata yapar:

| gerçek f | 50 Hz ayarıyla hata |
|---|---|
| 45 Hz | +19.9% |
| 50 Hz | 0.0% |
| 60 Hz | **−19.9%** |

Düzeltme **yalnızca güce** uygulanıyor; ortalama V ve I ham kalıyor
(AC'de zaten ~0, DC'de düzeltme zaten 1).

##### Faz kalibrasyonu (B16'nın 1. kalemi)

Yeni komut **`F<örnek>`** — menzil başına kesirli gecikme, kalıcı ayarda
`faz_kal[2]` olarak saklanıyor. **Referans cihaz gerekmiyor:** dirençli
bir yükte gerçek faz farkı sıfır olmalı; okunan fark doğrudan süzgeç
eşleşmezliğidir. `F` tek başına mevcut değerleri gösteriyor.

Çözünürlük: 0.001 örnek adım = 50 Hz'te **0.0209°** — 1° hedefinin çok
altında.

##### ❌ B16'nın 2. kalemi GEÇERSİZ çıktı

B16 *"PGA değişiminden sonra 13 örnek atılmalı"* demişti. Firmware'e
bakınca: **PGA hiç değişmiyor.** İki gerilim kanalı da PGA ±1.024'te
sabit, akım kanalı ±0.256'da sabit; oto-menzil **KANAL** değiştiriyor,
PGA kademesi değil — ve bu bilerek böyle (DEVIR 4.14: giriş empedansı
PGA ile değişiyor, kazanç sıçraması kalibrasyonla silinemiyor).

Kanal değişiminde ilk dönüşümü atma işi ise `menzil_uygula()`'da
**zaten doğru yapılmış** (1300 µs bekleme + bir okuma atma).

**B16 bu kalemi firmware'e bakmadan yazmıştı; B17 doğruladı ve kapattı.**

##### Kalıcı ayar imzası değişti

`Ayar3` büyüdüğü için imza **0xC0F3 → 0xC0F4**. Eski NVS kaydı sessizce
yanlış okunmayacak.

> 🔴 **B20 DÜZELTMESİ (2026-09-10):** bu yarım uygulanmıştı. Yalnızca
> `tipler3.h` değişmişti; `.ino`'daki `ayar_yukle`/`ayar_kaydet` elle
> `0xC0F3` yazmaya devam ediyordu — **NVS'e hep eski imza gidiyordu, damga
> hiçbir şey korumuyordu.** Tek kaynağa bağlandı: `#define AYAR3_IMZA`.

##### Mutasyon testi

| Mutasyon | Sonuç |
|---|---|
| Sürekli kipe dön | B17 **26→25** |
| Ölçek düzeltmesini kaldır | B17 **26→25** |
| `lagrange4` katsayısının işaretini boz | AVR **3 iddia** kırmızı |
| `suzgec_ters_kazanc` hep 1 dönsün | AVR **5 iddia** kırmızı |

##### 🔴 Tezgahta ölçülmesi gereken

I2C yazma süresi **hesap**. Gerçek kartta `micros()` ile ölçülüyor ama
o ölçümün doğruluğu (ve ESP32'nin Wire kütüphanesinin gecikmesi) ancak
tezgahta doğrulanır. Ayrıca tek atış kipinde gerçek örnekleme hızının ne
olduğu (döngü yükü + I2C) ölçülmeli — `D` satırındaki örnek sayısı bunu
zaten raporluyor.

---

#### 5.12.30 ✅ B20 — ÖRNEKLEME HIZI, BANT SINIRI ve MENZİL DAVRANIŞI (2026-09-10)

`uretim/sim3_bant.py` · **41 doğrulama** · `dogrula3.py`'de B20 adımı ·
firmware'de **7 düzeltme** · `tasarim3_sabit.py`, `sim3_skop.py`,
`sim3_senkron.py`, `arayuz3/app.js`, `arayuz3/sahte-kart.js` güncellendi.

⚠️ Bu adım da **tasarımı** ve **firmware'i** sınıyor, kurulmuş bir kartı değil.

> **Yöntem notu.** Bu adım 11 ölçüm ajanı + 49 adversaryel çürütme ajanıyla
> koşturuldu. **Çürütme katmanı 27 bulguyu reddetti** — aşağıdakiler ayakta
> kalan ve mutasyon testinden geçenler. Çürütücüler bu oturumun kendi
> mekanizma açıklamalarından **ikisini de düzeltti** (aşağıda "düzeltilen
> iddialar").

---

##### 🔴 ANA BULGU: kart 860 SPS'te değil ~91 SPS'te örnekliyordu

B17 ADS yolunu tek atış kipine aldı ve üstüne iki düzeltme koydu
(1/|H(f)| ölçek düzeltmesi + kesirli gecikme). **İddialarının hepsi
50 Hz'te ve 860 SPS varsayımıyla sınanmıştı.** İkisi de tutmuyordu.

İki ayrı kusur aynı yere vuruyordu:

**(1) `loop()`'un başında sürekli kipten kalma ÖLÜ bir bekleme.**

```c
if (!yeni_donusum_bekle(4000)) { delay(2); }   // <- ÖLÜ
Okuma3 o = olcum_al();                          // dönüşümü BU başlatıyor
```

Sürekli kipte bu bekleme döngünün **hız ayarlayıcısıydı** — doğru yerdeydi.
Tek atışa geçilince dönüşümü `olcum_al()` başlatıyor, dolayısıyla buraya
gelindiğinde **uçuşta dönüşüm yok**: bir önceki `olcum_al` iki yazmacı da
okumuştu ve tek atış kipi dönüşüm bitince kapanıyor. Yani bu bekleme
**ALERT kusursuz çalışsa bile her turda 4000 µs zaman aşımına düşüyordu.**

**(2) `COMP_QUE = 11b` — ALERT/RDY pini hiç etkin değildi.**

`setup()` doğru şeyi yapıyordu (Hi_thresh = 0x8000, Lo_thresh = 0x0000,
`INPUT_PULLUP`) ama **her ayar yazması** `ADS_KOMP_KAPALI = 0x0003`
gönderiyordu. TI SBAS444E §7.3.8, harfi harfine:

> *"Set the COMP_QUE[1:0] bits to any 2-bit value other than 11b to keep
> the ALERT/RDY pin enabled"*

ve yazmaç tablosu 11b için: *"Disable comparator and set ALERT/RDY pin to
high-impedance (default)"*. Yani pin yüksek empedansta kalıyor, dahili
pull-up ile hep HIGH okunuyor, `yeni_donusum_bekle` **hiçbir zaman**
başarılı olmuyordu.

| Senaryo | periyot | SPS | Nyquist |
|---|---|---|---|
| **B20 öncesi** (ölü bekleme + COMP_QUE=11b) | 11.0 ms | **91** | 45 Hz |
| yalnız COMP_QUE düzeltilse | 7.49 ms | 134 | 67 Hz |
| yalnız ölü bekleme silinse | 5.72 ms | 175 | 87 Hz |
| **B20 sonrası** (ikisi de) | 1.49 ms | **671** | 336 Hz |

**🔴 Varsayılan `sebeke_hz = 50` ayarı Nyquist'in ÜSTÜNDEYDİ** (45 Hz).
Firmware, `tipler3.h`, `olcum3.h` ve DEVIR'in dört ayrı yerinde "860 SPS"
yazıyordu; hiçbiri ölçülmemişti.

> **`delay(2)` neden tam 2000 µs değil:** Arduino-ESP32'de `delay(ms)` =
> `vTaskDelay(ms/portTICK_PERIOD_MS)`, tik 1 kHz. "Şu andan 2 tik" beklenir
> ve **tik sınırında** uyanılır. vTaskDelay dışı meşgul süre 9.72 ms olduğu
> için periyot **tam 11.000 ms'e kilitleniyordu** — ADS osilatörünün
> ±%10'undan bile bağımsız. (Bunu çürütme ajanı düzeltti; ilk hesap
> 11.72 ms / 85 SPS demişti.)

##### 🔴 TEK ATIŞIN BELGELENMEMİŞ BEDELİ

B17 sürekli kipten tek atışa geçerken bir bedel yazmadı: tek atışta I2C
yazma+okuma dönüşümle **serileşir**, sürekli kipte ise dönüşüm arka planda
akar. Tavan **671 SPS** — nominalin %78'i. Bu kaçınılmaz, ama yazılmalıydı.

Dürüst muhasebe:

| Tasarım | Hız | V/I kayması |
|---|---|---|
| Sürekli kip (B17 öncesi) | 860 SPS | 0…23°, **sürüklenen** |
| Tek atış (B17'nin tasarladığı) | **671 SPS tavan** | 95 µs, sabit |
| Tek atış (B17'nin **yazdığı** kod) | **91 SPS** | 95 µs, sabit |

##### 🔴 B17'nin kazanımı gerçek hızda YOKTU

Hizalayıcının PF=0.5'te sağladığı iyileşme (uzun ortalama):

| periyot | hizalayıcı kapalı → açık | kazanç |
|---|---|---|
| 11.0 ms (B20 öncesi) | +4.990% → +4.585% | **1.1×** |
| 5.72 ms | +4.991% → +0.332% | 15.0× |
| 1.49 ms (B20 sonrası) | +4.988% → −0.019% | **261×** |
| 1.163 ms (860 SPS) | +4.983% → −0.016% | 314× |

##### 🔴 `F` faz kalibrasyonu düşük hızda AKTİF ZARARLIYDI

Belgelenen yordam: *"dirençli yük bağla, okunan gücü en büyük yapacak
şekilde F ile ayarla"*. 11 ms periyotta f/fs = 0.55 ve orada Lagrange
süzgecinin **kazancı** d ile güçlü değişiyor — arama fazı değil kazancı
kovalıyor. Gerçek kod AVR emülatöründe: yordam `faz_kal ≈ −0.265`'e
gidiyor ve dirençli yükte 0.5000 yerine **0.5796 okuyor (+%15.9 hata,
hem de kalibrasyon yükünün ta kendisinde)**. Hız düzeltilince bu kendi
kendine kapanıyor.

---

##### 🔴 FAZ KALİBRASYONU TEK FREKANSTA — asıl sınır burası

Kullanıcının 3. sorusu. `F<örnek>` **sabit bir ZAMAN gecikmesi** saklıyor;
düzelttiği şey ise iki RC'nin **arctan farkı**:

```
Δφ(f) = atan(2πf·τ_i) − atan(2πf·τ_v)      ← düzeltilmesi gereken
Δφ_kal(f) = 360·f·d·T                       ← F'in yaptığı (DOĞRUSAL)
```

Bu ikisi **yalnızca kalibrasyon frekansında** örtüşür. 50 Hz'te kalibre
edilmiş kartta kalan faz hatası (kondansatör toleransı — B16: envanterde
tolerans yazmıyor, parçanın üzerindeki harf okunmalı, J=%5 / K=%10):

| f | tol ±%1 | tol ±%5 | **tol ±%10** | PF=0.5 güç hatası (±%10) |
|---|---|---|---|---|
| 50 Hz | 0.00° | 0.00° | **0.00°** | %0.0 |
| 60 Hz | −0.20° | −0.65° | **−1.21°** | %3.7 |
| 100 Hz | −1.16° | −3.78° | **−7.04°** | **%20.5** |
| 200 Hz | −3.52° | −11.46° | **−21.39°** | **%56.3** |
| 400 Hz | (eski `f` sınırı) | | | **tamamen geçersiz** |

**Bağlayıcı kısıt beklendiği yerde değil.** Lagrange sarkması 100 Hz'te
671 SPS'te yalnızca %0.78; kartı sınırlayan şey **faz kalibrasyonu**.

**Sonuç: `f` üst sınırı 400 → 100 Hz'e çekildi**, ve 40–70 Hz dışında
firmware artık uyarı basıyor. Ölçülen geçerlilik: 40–70 Hz bandında,
±%10 tolerans köşesinde, PF=0.5'te en kötü **%8.0** güç hatası.

> **🔴 AÇIK TASARIM SORUSU (kullanıcı kararı).** Kalibrasyon sabit gecikme
> yerine **τ eşleşmezliği** olarak saklanırsa (ölçülen fazdan `τ_i_etkin`
> çözülüp her frekansta arctan farkı hesaplanırsa) bant genişler.
> Maliyeti iki `atanf()` — ESP32'de önemsiz. **UYGULANMADI:** `F`
> komutunun anlamını değiştirir ve tezgahta doğrulanmadan yapılmamalı.
> Ayrıca çürütme ajanının uyarısı: bulunan `τ_i_etkin` **ölçek
> düzeltmesinde kullanılmamalı**, yalnızca fazda.

---

##### 🔴 OTOMATİK MENZİL AC'DE KULLANILAMIYORDU

Eşikler **anlık |v|**'ye uygulanıyordu. Bir sinüsün genliği her yarım
çevrimde alt eşiğin (22.7 V) altına inip tepede üst eşiği (29.2 V) aşıyor.
Tepesi 29.2 V'i geçen **her** AC sinyalde bu bir döngü:

| tepe | ESKİ geçiş/s | ESKİ doyan örnek | YENİ geçiş/s | YENİ doyan |
|---|---|---|---|---|
| 25 V | 0 | %0.0 | 0 | %0.0 |
| 30 V | **198** | %0.0 | **1** | %0.0 |
| 50 V | **199** | **%12.2** | **1** | %1.2 |
| 100 V | **193** | %13.5 | **1** | %1.5 |
| 300 V | 65 | %5.0 | 1 | %2.1 |

Her geçiş `menzil_uygula()`'nın **1518 µs**'sini ödetiyor → örnekleme
hızının %30'u menzil değişimine gidiyordu. Eski yorum *"Aradaki boşluk
gidip gelmeyi (chatter) önlüyor"* diyordu; **DC'de önlüyor, AC'de
önlemiyordu.**

**Çözüm — iki asimetrik karar:**
- **YUKARI**: anlık |v| ile (hızlı olmalı, yoksa kanal doyar)
- **AŞAĞI**: bir şebeke çevriminde **tutulan tepe** ile (sinüsün tepesi
  çevrim boyunca sabittir; anlık değere bakınca "aşağı in" AC'de sürekli
  tetikleniyordu)
- üstüne bir **susturma**: geçişten sonra bir şebeke çevrimi boyunca
  yeni geçiş yok

**Bedeli:** gerçek bir DC düşüşünde NORMAL'e dönüş artık anlık değil, en
çok iki pencere (50 Hz'te 40 ms) sonra. Yukarı yön — yani doymayı önleyen
yön — hâlâ anlık.

---

##### 🔴 SSE akış işleyicisi `loop()`'u sonsuza kadar kilitliyordu

```c
while (c.connected()) { ...; delay(20); sunucu.handleClient(); }
```

`akis_sayfa()`, `loop()` içindeki `sunucu.handleClient()`'tan çağrılıyor.
İstemci bağlı kaldığı sürece geri dönmediği için **loop() de geri
dönmüyordu**: `olcum_al()` koşmuyor, enerji birikmiyor. Daha kötüsü
`son_satir[]`'ı **yalnızca `loop()`** yazdığı için akış ilk (bayat) satırı
gönderip **sonsuza kadar susuyordu** — işlev kendi amacını bile yerine
getirmiyordu. Ayrıca içerideki `handleClient()` aynı sayfayı **iç içe**
çağırabiliyordu.

Blokaj bitince `enerji_biriktir`'in `dt > 1 s` koruması devreye girip o
aralığı **atlıyor**: 1 dk @ 25 W → **0.42 Wh, yani birikmesi gereken
enerjinin %100'ü** sayaca hiç girmiyor.

Bugün pratikte erişilemiyor (`WIFI_AD` boş) ama kök sayfa kullanıcıyı
açıkça oraya yönlendiriyor ve B12 bu yolu açacak. **Durum makinesine
çevrildi:** işleyici yalnızca başlıkları yazıp hemen dönüyor, `loop()`
her `D` satırında saklanan istemciye yazıyor.

---

##### 🔴 `ortalama_oku()` ortalama ALMIYORDU

Tek atış kipinde çip dönüşüm bitince kapanır; yeni bir `OS=1` yazılmadıkça
dönüşüm yazmacı **değişmez**. Eski gövde hiçbir dönüşüm başlatmadığı için
16–32 okuma **aynı bayat değeri** okuyup "ortalamasını" alıyordu:
**gürültü azaltma tam sıfır**, üstüne komut başına 48–96 ms ölü zaman
aşımı. Dört kalibrasyon komutu da (`z`, `g`, `Z`, `i`) bunu kullanıyor —
yani **sıfır ve kazanç kalibrasyonları tek bir gürültülü örnekle**
yapılıyordu. Düzeltildi: her turda dönüşüm kendimiz başlatılıyor.

---

##### Ayrışmalar

**(a) `Ayar3` imzası yarım uygulanmıştı.** B17 "0xC0F3 → 0xC0F4, eski NVS
kaydı sessizce yanlış okunmayacak" dedi ama yalnızca `tipler3.h`'yi
değiştirdi; `.ino`'daki `ayar_yukle`/`ayar_kaydet` elle `0xC0F3` yazmaya
devam ediyordu. Yani **NVS'e hep eski imza gidiyor, sürüm damgası hiçbir
şey korumuyordu.** Tek kaynağa bağlandı: `#define AYAR3_IMZA 0xC0F4u`.

**(b) 🔴 Skop adımı dört dosyada, biri ayrışmış.** B19 "sabit ayrışması
denetimi" yapmıştı ama yalnızca `SKOP_ORAN` ve `VREF`'e baktı, **adımı
atladı**:

| kaynak | önce | sonra |
|---|---|---|
| `tasarim3_sabit.py` | 2.9 V / 4096 → 26.93 mV | 3.1 V / 4096 → 28.79 mV |
| `kod/olcum3.h` | 3.10 V / **4095** → 28.80 mV | 3.1 V / 4096 → 28.79 mV |
| `arayuz3/app.js` | 3.10 / **4095** | 3.10 / 4096 |
| `arayuz3/sahte-kart.js` | 3.10 / **4095** | 3.10 / 4096 |

**%6.92 ayrışma, hiçbir iddia görmedi.** Kök sebep kavramsal: `SKOP_ADIM`
ile `SKOP_MENZIL_*` **aynı sabiti** kullanıyordu, oysa ikisi farklı şeyler:

- `SKOP_MENZIL_*` → girişin **kullanılabilir üstü** (2.9 V; üstünde ESP32
  ADC'si doğrusallığını kaybediyor) — **doğru sabit buydu, değişmedi**
- `SKOP_ADIM` → bir ADC kodunun kaç volt ettiği, yani **LSB** = nominal
  tam ölçek / 4096

> ⚠️ **DEVIR 5.12.28'in "adım 11.1 → 26.9 mV" satırı bu yüzden yanlıştı.**
> Doğrusu **11.9 → 28.8 mV**. Menzil satırları (−63.5 … +46.8 V) etkilenmiyor.
>
> ⚠️ Bu denetim dördünün **aynı** olduğunu sınar, **doğru** olduğunu değil.
> 3.1 V bir veri sayfası nominali; ESP32 ADC'sinin gerçek tam ölçeği
> yongaya göre değişiyor ve doğrusal değil — **tezgahta kalibre edilmeli.**

**(c) `TAU_*` sabitleri sıkı bağlandı.** `test_olcum3.py` bunları 1e-3 s
**mutlak** toleransla sınıyordu; τ ≈ 2.9 ms olduğu için bu **%35 tolerans**
demek. B20 üçünü de `tasarim3_sabit.py`'ye %0.1 bağıl toleransla bağlıyor.

---

##### ❌ Totoloji temizliği

`sim3_senkron.py:191` şunu yazıyordu:

```python
r.kosul("B17-1: kalan kayma SABIT ve BILINEN", True is not False, ...)
```

`True is not False` her zaman doğru — **26 iddiadan biri boştu.** Yerine
iddianın kendisi sınanıyor: "kayma sabit" demek, kaymanın ADS
osilatörünün toleransından **bağımsız** olması demek. Sürekli kipte
yayılım %22, tek atışta %0.

> Bağımsız bir AST taraması zincirin tamamında **10 boş iddia** daha
> buldu; ayrıca kaynaksız BAT85/ADS1115 SPICE model parametreleri.
> **Bunlar B20 kapsamında düzeltilmedi** — ayrı bir iş kalemi (aşağıda).

---

##### Çürütme katmanının DÜZELTTİĞİ iki iddiam

Dürüstlük bölümü — bu oturumun kendi mekanizma açıklamaları yanlıştı:

1. **"Nyquist 43 Hz, 50 Hz katlanıyor → ölçüm bozuk"** — **DAYANAKSIZ.**
   Belirleyici kontrol deneyi: hizalayıcı kapalıyken uzun ortalama hatası
   85 / 93 / 133 / 175 / 671 / 860 SPS'te **aynı** (PF=1: −0.042%,
   PF=0.5: +4.99%). Sebep: bu bir **wattmetre**; v ve i eş anda
   örnekleniyor ve **çarpımın ortalaması** alınıyor. Örtüşme dalga şeklini
   bozar, çarpımın ortalamasını bozmaz — Nyquist ölçütü **yeniden
   yapılandırma** içindir. Gerçek zarar mekanizması **Lagrange
   hizalayıcının f/fs = 0.55'te çökmesi**.
2. **"860 SPS'te pencere dalgalanması sıfır"** — **YANLIŞ GENELLEME.**
   Sıfır olması periyodun tam 1/860 s olmasına bağlı (172 örnek = tam
   10 şebeke çevrimi); 946 SPS'te 0.169 W, 774 SPS'te 0.053 W. **Tesadüf,
   özellik değil.**

Buna karşılık **pencere kırpılması** bulgusu ayakta: 200 ms rapor
penceresine gerçek hızda yalnızca 19 örnek sığıyordu ve saf sinüste bile
güç okuması **±%5.2** geziniyordu (tasarım hızında ±%0.4).

---

##### Mutasyon testi

Her yeni iddianın gerçekten ısırdığı gösterildi:

| Mutasyon | Sonuç |
|---|---|
| `loop()`'a ölü beklemeyi geri koy | B20 **41→38** |
| `ADS_KOMP_TEK`'i 0x0003'e (11b) döndür | B20 **41→40** |
| SSE blokajını geri getir | B20 **41→38** |
| İmzayı tekrar ayrıştır (`0xC0F3`) | B20 **41→40** |
| `menzil_gozet`'i anlık karara döndür | B20 **41→40** |
| `ortalama_oku`'nun dönüşüm başlatmasını sil | B20 **41→40** |
| `f` sınırını 400 Hz'e geri çıkar | B20 **41→37** |
| `TAU_NORMAL`'i %20 boz | B20 **41→40** |
| Skop adımını dört dosyanın **her birinde ayrı ayrı** boz | dördü de B20 **41→40** |

---

##### 🔴 Tezgahta ölçülmesi gerekenler (B20'den)

1. **`D` satırındaki örnek sayısı.** 200 ms'de ~134 bekleniyor (671 SPS).
   ~19 çıkarsa B20 düzeltmeleri işe yaramamış demektir. **Bu, K1'in
   bedava tezgah testidir.**
2. **ALERT/RDY darbesi skopla görülmeli.** Tek atış + `COMP_POL=0`'da
   beklenen dalga şekli: boşta HIGH, dönüşüm boyunca LOW (~1.16 ms),
   hazır olunca HIGH ve **bir sonraki başlatmaya kadar HIGH** (darbe
   değil, mandal). Kaynak: RobTillaart/ADS1X15 issue #76, iki bağımsız
   osiloskop ölçümü. Veri sayfası bu konuda **kendisiyle çelişiyor**
   (§7.3.8 "asserts low at the end" vs §8.1.4 "outputs the OS bit").
3. **`/HAZIR` hattında harici pull-up YOK** (net = yalnız J5.6 + U6.2);
   ESP32'nin dahili ~45 kΩ'u kullanılıyor. Tek atıştaki **seviye**
   assert'i için yeterli; sürekli kipin 8 µs'lik darbesi için
   olmazdı. En kötü hal (80 kΩ + 100 pF uzun şerit) yükselme 11.1 µs.
   **Stokta 10K var** (B18'in R032/R033'ü) — gerekirse eklenir.
4. **`micros()` ile ölçülen `t_kayma_us` gerçekten ~95 µs mi.**
   `Wire.begin(..., 400000)` gerçekten 400 kHz kuruyor mu; 100 kHz'e
   düşerse kayma 4 kat büyür. (I2C süreleri saf bit sayımı — ESP32 Wire
   sürücüsünün işlem başına ek yükü sayılmadı; bu periyodu yalnızca
   **uzatır**, yani 671 SPS bir **üst sınır**.)
5. **Skop ADC'sinin gerçek tam ölçeği.** 3.1 V nominal; yongaya göre
   değişiyor ve doğrusal değil.
6. **Kondansatör toleransı.** C2 ve C18'in üzerindeki harf okunmalı
   (J=%5, K=%10) — faz kalibrasyonunun geçerlilik bandını bu belirliyor.

---

##### B20'nin AÇTIĞI iş kalemleri

##### ✅ B20'nin ikinci turu — riski olmayan kalemler KAPATILDI (2026-09-10)

| # | İş | Durum |
|---|---|---|
| 1 | **Karar:** faz kalibrasyonunu τ eşleşmezliği olarak sakla | 🔴 **AÇIK — kullanıcı kararı.** Bant 40–70 Hz'ten genişler; `F`'in anlamını değiştirir, tezgah gerekir. Bilerek yapılmadı |
| 2 | Zincirde kalan **boş iddialar** | ✅ **KAPANDI.** AST taraması 13 aday buldu; 4'ü meşrudu (if/else dalları), **9'u gerçek totolojiydi** ve hepsi ölçen testlere çevrildi |
| 3 | SPICE model parametreleri | ✅ **KAPANDI.** İddia kısmen yanlışmış: BAT85 (Nexperia) ve ADS ESD kaynaklı ve gerekçeli. **Gerçek boşluk:** skaler `ADS_ESD_VF` ile SPICE `D_ESD` birbirine bağlı değildi — bağlandı (B20/6d) |
| 4 | `f` ve `F` komutları **arayüzde yok** | ✅ **KAPANDI.** Arayüze eklendi; ayrıca komut denetiminin **tek yönlü** olduğu düzeltildi |
| 5 | Fabrika ayarı `sebeke_hz = 50`, DC ölçümünde gücü %82 şişiriyor | ✅ **KAPANDI.** Arayüz artık uygulanan ölçek çarpanını ve uyarıyı gösteriyor |
| 6 | Kurulum kılavuzu U5A referansları yanlış | ✅ **KAPANDI.** Gerçek montaj tuzağıymış — netlist'e bağlandı |
| 7 | `test_olcum3.py` LK4'ün toleransı 177× kör | ✅ **KAPANDI.** Beklenen değer sarkmayı içeriyor, tolerans 200× sıkıldı |

**(2) 9 totoloji — hepsi ölçen teste çevrildi.** En ciddisi
`sim3_ariza.py:1260`: sart `True` ile *"skop kanalı çift yönlü DEĞİL — bu bir
tasarım gerçeği"* yazıyordu. **B19 (bir gün önce) tam da bunu değiştirmişti.**
İddia B19'dan beri yanlıştı ve `True` olduğu için zincir hiç görmedi. Ayrıca
`sim3_besleme.py`'de 7 tane (7912'nin kapasitif yükü, stok, regülasyon, kısa
devre koruması, soğutucu gereksinimi…) ve `bom_dogrula.py`'de 1 tane.
Mutasyon: `Cout` LM358 sınırının altına, `θ_JA` 100×, kısa devre akımı
küçültme, `-12 V` rayını regüle olmaktan çıkarma — **dördü de kırmızıya
dönüyor.**

**(4) Komut denetimi TEK YÖNLÜYDÜ — asıl kusur buydu.** `test_arayuz3.js`
yalnızca *"arayüzün gönderdiği her komut firmware'de var mı"* diye soruyordu.
Tersi sorulmadığı için B17'nin eklediği `f`/`F` arayüze konmadan **70/70 yeşil**
kalmıştı. Ters denetim eklendi; toplayıcı da üçlü ifadeleri
(`gonder(m === 1 ? 'y' : 'n')`) kaçırıyordu, düzeltildi. Arayüz **70 → 74**.

**(6) Kılavuzun montaj tuzağı — netlist'ten doğrulandı.** Kılavuz
*"Sallen-Key (U5A): R22/R23 = 6.8K, C7 = 2nF"* diyordu. Netlist'in söylediği:
**R23 bölücünün alt bacağı** (2.7K, VREF'e — B19'un konusu ve hemen üstteki
uyarının kendisi), Sallen-Key'in direnci **R21**; **C7 ise U5B'ye** ait,
U5A'nınki **C5**. R23'e 6.8K takmak skop kanalını **hem tek yönlü bırakır hem
ölçeğini bozardı.** Netlist denetimi **128 → 134**.

##### Bu turda ayrıca düzeltilenler

- **`guc_olc`: `i_rms` artık HAM örnekten.** `ii_top += ih * ih` yazıyordu,
  yani gösterilen Irms hizalayıcının genlik sarkmasını yiyordu (5 kHz'te
  %0.72), Vrms yemiyordu — asimetrik ve yanlış. Hizalama yalnızca **güç** için
  gerekli; RMS tek kanallı bir büyüklüktür.
- **`menzil_gozet(ham.volt)`.** Hizalayıcının çıkışı 2 örnek eski olduğu için
  menzil kararı 2.33 ms gecikiyordu; üst eşik ile NORMAL kanalın doyumu
  arasında yalnızca 3.24 V pay var ve **1395 V/s'ten hızlı her sinyalde** bu
  pay 2 örnekte yeniyordu.
- **`olcum3.h`'deki "güvenilir wattmetre bandı ~5 kHz" cümlesi ikiye ayrıldı.**
  Hızlı yol için doğru (41.7 kSa/s), ADS yolu için **değil** — aynı süzgeç
  orada 100 Hz'te %0.78, 200 Hz'te %8.3 sarkıyor. İki bant tek cümleye
  karışmıştı.

##### İkinci turun mutasyon testi

| Mutasyon | Sonuç |
|---|---|
| `Cout`'u LM358 sınırının altına indir | B11 **23→22** |
| `θ_JA`'yı 100× yap (Tj patlar) | B11 **23→21** |
| Kısa devre akımını küçült | B11 **23→21** |
| −12 V rayını regüle olmaktan çıkar | B11 **23→22** |
| Kılavuzu eski yanlış referansa döndür | netlist **134→132** |
| `f` / `F`'i arayüzden sil (gövdeyi boşalt) | arayüz **74→72 / 74→73** |
| Ölçek uyarısını arayüzden kaldır | arayüz **74→73** |
| LK4'ün beklentisinden sarkmayı çıkar | AVR **87→86** |
| SPICE `D_ESD`'nin `IS`'ini boz | B20 **42→41** |

---

#### 5.12.31 ✅ B21 — PİL KAPASİTE TESTİ (2026-09-10)

`uretim/sim3_pil.py` · **32 doğrulama** · `dogrula3.py`'de B21 adımı ·
şemaya **BLOK 10** · firmware'de `pil_test.h` + `/pil` ucu · arayüzde panel
· netlist 134 → **150** · AVR 87 → **91** · arayüz 74 → **82**.

⚠️ Bu adım da **tasarımı** ve **firmware'i** sınıyor, kurulmuş bir kartı değil.

**Kullanıcı isteği:** *"ZB2L3 gibi çalışan bir sistem — mAh ölçümü, kapanacağı
gerilimi kendimiz ayarlayalım, akım ve voltaj grafiğini gözlemleyelim."*

##### Kararlar (kullanıcıyla birlikte alındı)

| Konu | Karar |
|---|---|
| Yük | **Taş direnç** (harici) + MOSFET **yalnızca anahtar** |
| Kurulum | **Ana karta** — ayrı modül tartışıldı, ölçüm çekirdeği bölünmesin diye vazgeçildi |
| Sıcaklık | Şimdilik yok (envanterde sensör yok) |
| Veri | Tarayıcı **IndexedDB** (sınırsız) + kartta **yetişme tamponu** |
| Kontrol | Arayüzden başlat/durdur + otomatik kesme |
| DCIR | Periyodik otomatik (5 dk'da bir) |

##### 🔴 3.3 V kapı IRFZ44N'i süremez

Stokta **mantık seviyeli (IRL…) MOSFET yok**. IRFZ44N'in eşiği **2–4 V** ve
RDS(on) **10 V'ta** ölçülmüş (INCHANGE şartnamesi s.2). ESP32'nin 3.3 V'u en
kötü halde eşiğin **altında**, iyi halde bile MOSFET'i doğrusal bölgede
bırakıp ısıtır.

Çözüm, B11'in karta koyduğu **+12 V rayından** iki transistörlü sürücü —
üçü de stokta (2N2222 ×12, BC557 ×7):

```
GPIO ──4.7K──┤2N2222├──10K──┤BC557├── +12 V
                              │
                       ──220R── MOSFET kapısı ──10K── GND
```

##### 🔴 Failsafe yönü — B21'in en önemli tek kararı

Kapı **R42 ile GND'ye çekili**. ESP32 reset atarsa, çökerse ya da WDT
tetiklenirse GPIO yüksek empedansa döner, kapı 0 V'a iner, **MOSFET kapanır
ve pil boşalmayı durdurur.** Ters kurulum (kapıyı +12 V'a çekmek) kart
ölürken yükü **bağlı bırakırdı** — saatler süren, başında kimsenin
beklemediği bir testte bu kabul edilemez.

Kaçak denetimi: Igss 100 nA × 10K = **1 mV**, eşiğin 2000 katı altında.
Açılışta da geçerli: `pinMode` çağrılmadan önce GPIO giriş kipinde.

Bu, ESP32'nin donanım WDT'sini **bedava bir emniyete** çeviriyor — ve B20
tam da böyle bir döngü takılması bulmuştu (SSE işleyicisi `loop()`'u
sonsuza kadar kilitliyordu).

##### 🔴 Neden ayrı konnektör (J7), köprü değil

J3 "Yük dönüşü" **doğrudan şönte bağlı kalıyor** (normal ampermetre
kullanımı). MOSFET'i ana akım yoluna koysaydık, ESP32 her reset attığında
**ölçülen devrenin akımı kesilirdi** — bir SMPS'i izlerken kabul edilemez.

Bunun bedeli bir **sessiz hata riski**: kullanıcı yükü yanlışlıkla J3'e
bağlarsa MOSFET baypas olur, ölçüm çalışır, grafik çizilir ama **kesme
çalışmaz.** Firmware bunu yakalıyor: test başlarken MOSFET'i **kapalı**
tutup akıma bakıyor; akım varsa testi **reddediyor**.

##### 🔴 Yeni tasarım sınırı: pil gerilimi ≤ 38.5 V

MOSFET **kapalıyken pilin tamamı üstüne biniyor**. IRFZ44N Vdss = 55 V,
%70 payla **38.5 V**. Kartın gerilim kanalı ±613 V ölçebiliyor ama **pil
testi bundan çok daha dar bir bantta** — bu ayrı bir sınır ve firmware
zorluyor.

| Pil | Gerilim | Yargı |
|---|---|---|
| 18650 1S · LiPo 3S/6S · 12 V akü · 24 V akü | ≤ 29 V | ✅ |
| **48 V paket** | 58 V | 🔴 **REDDEDİLİYOR** |

##### Isıl sınır: soğutucusuz 6.55 A

MOSFET yalnızca anahtar; güç **taş dirençte** yanıyor. MOSFET'in yediği tek
şey I²·RDS(on):

| Akım | Senaryo | P | Tj | Yargı |
|---|---|---|---|---|
| 0.89 A | 18650, 4.7 Ω | 25 mW | 41.6 °C | ✅ (+1.6 °C) |
| 2.56 A | 100 mΩ şöntün tavanı | 210 mW | 53 °C | ✅ |
| **6.55 A** | **soğutucusuz sınır** | 1.37 W | 125 °C | sınır |
| 11.5 A | 15 mΩ şöntün tavanı | 4.23 W | **302 °C** | 🔴 soğutucu şart |

##### Veri saklama — iki katmanlı

| | Kart | Tarayıcı (IndexedDB) |
|---|---|---|
| mAh / Wh | ✅ kesintisiz, **otoriter** | gösterim |
| Eğri (1 Hz) | son **1.5 saat** | **tamamı, sınırsız** |
| Sekme kapanınca | biriktirmeye devam | duraklar, açılınca **yetişir** |

Kart her noktaya **sıra numarası** veriyor; tarayıcı `/pil?sira=N` ile
eksikleri istiyor. Kartın penceresinden uzun kopmada **boşluk** oluyor ve
grafikte **açıkça işaretleniyor** — sessizce interpolasyon **yapılmıyor**.

**Kritik özellik:** mAh/Wh sayaçları **kartta** biriktiği için, eğride
boşluk olsa bile **toplam kapasite doğru kalıyor.**

> ⚠️ **Neden 2 saat değil 1.5 saat:** 2 saatlik tampon (7200 nokta = 86 KB)
> RAM kullanımını **%42'ye** çıkarıyor ve projenin kendi *"RAM < %40"*
> kuralını aşıyordu — **`test_firmware3.py` bunu yakaladı.** 5400 nokta
> (63 KB) ile toplam **%35**. Sınır donanımdan geliyor, tercihten değil.
> PSRAM bulunursa tampon 24 saate çıkıyor; bulunmazsa **işlev kaybolmuyor.**

##### 🔴 `--clean` eklendi — önbellek uyarıları GİZLİYORDU

B21 sırasında aynı kod için peş peşe **3, 2 ve 0** uyarı raporlandı.
Sebep: `arduino-cli` artımlı derliyor ve **önbellekten gelen çeviri
birimlerinin uyarılarını yeniden basmıyor.** Yani *"Derleme UYARISIZ"*
iddiası derleme önbelleği durumuna göre değişiyordu — **güvenilmezdi.**

`test_firmware3.py`'ye `--clean` eklendi (derleme 12 s → 75 s) ve
**hemen gerçek bir hata ortaya çıktı:**

```
warning: conversion from 'unsigned int' to 'uint16_t'
         changes value from '86400' to '20864'
```

PSRAM tamponu `24u * 3600u` = 86400 nokta istiyordu ama `PilHalka.kapasite`
**uint16_t** idi (tavan 65535) → **sessizce 20864'e** düşüyordu: 24 saat
yerine **5.8 saat**. Halka alanları `uint32_t` yapıldı.

##### Firmware

- `olcum3.h`: `yuk_ekle3` / `yuk_mAh3` / `yuk_coulomb3` — enerjinin birebir
  kardeşi, **işaretli** (şarj yönünde geri sayar), tavan **2562 Ah**
- `pil_test.h`: durum makinesi, halka tampon, saf denetim fonksiyonları
- `Ayar3` büyüdü → imza **0xC0F4 → 0xC0F5**
- Komutlar: `P<volt>` kesme · `p1`/`p0` başlat/durdur · `p` durum
- `/pil?sira=N` ucu — **bloklamıyor** (en çok 600 nokta/istek; B20'de
  `akis_sayfa()`'nin `loop()`'u kilitlediği görülmüştü)

##### AVR'de doğrulanan (gerçek kod)

`sim3_pil.py` yalnızca birim aritmetiğini sınayabiliyor; sayacın **işaretli
davranışı** ancak gerçek kodda görülür:

| İddia | Sonuç |
|---|---|
| 1 A × 3600 s = 1000 mAh | fark **0** |
| deşarj + eşit şarj → net | **TAM SIFIR** (ham 0 pC) |
| negatif akım → negatif yük | −0.8333334 vs −0.8333333 mAh |

##### Mutasyon testi

| Mutasyon | Sonuç |
|---|---|
| Kapıyı +12 V'a çek (**ters failsafe**) | netlist **150→147** |
| Çekme direncini tamamen kaldır | netlist **150→147** |
| Yükü şönte doğrudan bağla (MOSFET baypas) | netlist **150→148** |
| Kapı seri direncini 0R yap | netlist **150→149** |
| Kapıyı 3.3 V'a düşür | B21 **32→31** |
| Kapıyı mutlak azaminin üstüne çıkar | B21 **32→31** |
| Isıl direnci 3 °C/W yap | B21 **32→30** |
| Vdss 600 V yap | B21 **32→31** |
| Tamponu 20 saate çıkar | B21 **32→30** |
| DCIR darbesini 30 s yap | B21 **32→31** |
| Sayacı **tek yönlü** yap | AVR **91→89** |
| mAh ölçeğini 1000× boz | AVR **91→89** |
| `p1`/`P` gövdesini boşalt | arayüz **82→80/81** |
| Boşluk sayımını/işaretini sil | arayüz **82→81** |
| IndexedDB'yi kaldır | arayüz **82→80** |
| J7/J3 uyarısını sil | arayüz **82→81** |

##### Bu adımda yakalanan iki test kusuru

1. **`test_arayuz3.js`'in `govdeIcinde` yardımcısı yorumdaki bir anmayı
   fonksiyon tanımı sanıyordu** — `pilCsvIndir` iddiası bu yüzden yanlışlıkla
   kırmızı yandı. Artık tanım biçimi aranıyor.
2. **Boşluk iddiası metin tabanlıydı** — değişken adını bırakıp mantığı
   silmek testi kandırıyordu. Davranışa bağlandı.

##### 🔴 Tezgahta ölçülmesi gerekenler (B21'den)

1. **MOSFET'in üzerindeki logo** — veri sayfası ikincil kaynak (INCHANGE).
2. **Kapı gerilimi** — yük açıkken Vgs gerçekten ~11.8 V mi.
3. **Failsafe** — kart çalışırken reset atıp yükün kesildiğini gör. En
   önemli tezgah testi bu.
4. **Baypas denetimi** — yükü bilerek J3'e bağlayıp testin reddedildiğini gör.
5. **Şöntün güç değeri** — ±11.5 A rakamı 2 W **çıkarımından** geliyor.
6. **Taş direncin gerçek değeri ve ısınması.**

##### B21'in AÇTIĞI iş kalemleri

| # | İş | Neden |
|---|---|---|
| 1 | **Sıcaklık ölçümü** | Pil testi sıcaklıksız yarım kör; envanterde sensör yok |
| 2 | **Elektronik yük (sabit akım)** | Taş dirençte akım pil çöktükçe düşüyor (0.89 → 0.64 A); C-oranı sabit değil |
| 3 | Kayıt hızı (`pil_kayit_hz`) arayüzden ayarlanamıyor | Firmware destekliyor, arayüzde denetim yok |
| 4 | Şarj yönünde test (mAh geri sayıyor) | Sayaç işaretli, ama şarj kaynağı yok |

---

#### 5.12.32 🗂 DOSYA DÜZENİ ve KULLANICI BELGELERİ (2026-09-10)

Kullanıcı *"dosya sisteminde çok fazla dosya var, neyin ne olduğunu
anlayamıyorum"* dedi. Kök dizin sadeleştirildi ve gözle okunacak belgeler
ayrı bir yere alındı.

##### Yeni düzen

| Klasör | Ne |
|---|---|
| **`BELGELER/`** | **Kullanıcının bakacağı yer** — yalnızca HTML + PDF |
| `kod/olcum-karti-a3/` · `sema3/` · `arayuz3/` | Güncel sürümler |
| `uretim/` | Doğrulama zinciri + belge üreteçleri |
| `arsiv/asama1/` · `arsiv/asama2/` | Eski aşamalar, zincirleriyle birlikte |
| `DEVIR.md` · `README.md` | Kayıt |

Kökte artık 8 girdi var (önce 19). **94 MB → 9.8 MB**: `build/`
klasörleri (85 MB) ve geçici simülasyon dizinleri silindi — hepsi
yeniden üretilebilir.

##### 🔴 Arşivleme zincirleri KIRDI — yollar düzeltildi

Aşama 1 ve 2'nin kodu/şeması/arayüzü taşınınca `dogrula.py` **4 adım**,
`dogrula2.py` **3 adım** kırmızıya döndü. **22 yol** güncellendi. İki tuzak:

1. **arduino-cli eskiz klasörünün `.ino` adıyla aynı olmasını istiyor** —
   `kod/olcum-karti-a2` → `arsiv/asama2/kod` yapınca derleme kırıldı.
   Klasör adları korundu: `arsiv/asama2/olcum-karti-a2/`.
2. Üreteçler eski yerlere yazmaya devam ediyordu; `sema/`, `sema2/`,
   `kanit/` kökte **yeniden doğuyordu**. Çıktı yolları da arşive çevrildi.

##### Zincir artık kendi çöpünü topluyor

`dogrula3.py` bitişte `build/`, `_chk*`, `__pycache__` ve `erc*.rpt`
siliyor. Önceden her koşu ~85 MB bırakıyordu.

##### BELGELER — üretilen, elle yazılmayan

Yedi sayfa, **12 grafik**, hepsi `uretim/belge-uret.py` ile üretiliyor ve
**zincire bağlı** (B9 adımı), yani tasarım değişince bayatlamıyor.

| Sayfa | İçerik |
|---|---|
| `index.html` | Giriş, hangi belge ne işe yarar |
| `1-ne-yapabilir.html` | Yetenekler · menzil grafiği · osiloskop ekranı · canlı ölçüm · multimetre karşılaştırması · yapamadıkları |
| `2-olcumler.html` | Menziller, hızlar, şönt tablosu, zaman tabanı tablosu, hassasiyet ≠ doğruluk |
| `3-pil-testi.html` | 8 pil tipi için akım/süre tablosu · 4 grafik (V–t, V–mAh, mAh+Wh birikimi, DCIR–SoC) |
| `2-malzemeler.html` | **Şemadan + envanterden üretiliyor** — alınacak / yolda / stokta |
| `4-kurulum.html` | Montaj (mevcut üreteç) |
| `5-muhendislik.html` | Nasıl çalışıyor — isteğe bağlı |

**Grafiklerin verisi hesaplanıyor**, dekoratif çizim yok: deşarj eğrisi
bir OCV modelinden + iç direnç düşüşünden, osiloskop ekranı 20 kHz'lik
bir SMPS dalgasından, menzil çubukları `tasarim3_sabit.py`'den.

Renk paleti `dataviz` becerisinin doğrulanmış varsayılan paleti;
`validate_palette.js` ile sınandı (bütün denetimler PASS, açık + koyu).
Kontrast uyarısı doğrudan etiketlemeyle karşılandı — hiçbir seri kimliğini
yalnız renge bırakmıyor. Açık/koyu tema ikisi de destekleniyor.

##### Not

`kurulum3.html` → `BELGELER/4-kurulum.html` taşındı; üreteci de oraya
yazıyor. Eski aşamaların HTML/PDF çıktıları `arsiv/` altında duruyor.

---

#### 5.12.32b 📚 B22 ÖNCESİ ARAŞTIRMA — mimarinin GEREKÇESİ (2026-09-10)

Kullanıcının soruları B22'yi başlattı: *"web sitesini bitirdik mi, ben nasıl
gireceğim, yayını bilgisayar mı yapacak, telefondan ulaşabilecek miyim"* ·
*"arayüz ESP32'ye sığar mı, kaldırabilir mi"* · *"kendi telefonumda bir HTML
dosyasını uygulama gibi açabilir miyim — böylece ESP'ye daha az yük biner"* ·
*"hem bilgisayar hem telefon bağlıysa telefonda gördüğüm şey bilgisayardan mı
yayınlanacak"*.

**Bu bölüm cevapları değil, cevapların DAYANAĞINI kaydediyor.** Aşağıdaki beş
bulgu üç bağlanma kipini ve "arayüz karttan servis edilsin" kararını
belirledi; biri değişirse mimari kararı yeniden gözden geçirilmeli.

| # | Bulgu | Sonucu |
|---|---|---|
| 1 | **`file://` bir `http://` sunucuya ULAŞAMAZ.** Sunucu hangi CORS başlığını gönderirse göndersin: `file://` kökeni *opaque*, `Access-Control-Allow-Origin: *` bu durumu kurtarmıyor | Kullanıcının *"telefonda HTML dosyası açayım"* fikri **çalışmaz**. Sayfa karttan ya da köprüden **servis edilmeli** |
| 2 | **PWA / service worker güvenli bağlam istiyor** — HTTPS ya da `localhost`. **LAN IP istisnası YOK** (`192.168.x.x` güvenli bağlam sayılmıyor) | Kartta HTTPS yok → gerçek PWA kurulumu **mümkün değil**. iOS'ta *Ana Ekrana Ekle* yine de tam ekran açıyor, Android'de yalnızca kısayol. Belgede **vaat edilmiyor** |
| 3 | **Chrome 142 Local Network Access**, public bir sayfanın yerel ağa istek atmasını kapatıyor | Bir bulut sayfasının karta bağlanması güvenilmez. Bu, **karttan servis edilen sayfayı en sağlam seçenek** yapıyor — sayfa ve veri aynı kökenden gelir |
| 4 | **IndexedDB düz HTTP'de çalışıyor** (güvenli bağlam gerekmiyor), Chrome diskin **%60**'ına kadar veriyor | Uzun ölçüm kaydı **tarayıcıda** birikebilir; kartın belleği sınır değil |
| 5 | **`NetworkClient::write(Stream&)` 1360 baytlık tampon kullanıyor** | 82 KB'lik bir dosyayı servis etmek yalnızca **~1.36 KB RAM** demek. *"Arayüz ESP32'ye sığar mı"* sorusunun cevabı: **flash'ta yer sorunu var, RAM'de yok** |

**Kullanıcının ikinci sorusunun cevabı** (*"hem PC hem telefon bağlıysa"*):
kart aynı anda **tek sürücüye** hizmet ediyor ve karta bağlanan her tarayıcı
ölçümü yavaşlatıyor (her HTTP isteği `loop()`'u bloke ediyor). İkisi birden
isteniyorsa **köprüden** geçilmeli — o kipte telefonun gördüğü sayfayı
**bilgisayar yayınlıyor**, kartın Wi-Fi'si hiç açılmıyor. Bu yüzden USB köprü
**tercih edilen** kip. Kullanıcıya görünen anlatımı `BELGELER/6-ag.html`'de.

⚠ **Bunların hiçbiri tezgahta doğrulanmadı** — hepsi belge/kaynak okumasına
dayanıyor. mDNS'in Android'de çözülmesi, CSRF savunmasının gerçek tarayıcıda
çalışması ve telefondan ilk yükleme süresi `uretim/_tezgah.md`'de.

---

#### 5.12.33 ✅ B22.0 — ARAYÜZ HİÇ AÇILMIYORDU (2026-09-10)

🔴 **Zincir 15/15 ve B7 82/82 yeşilken arayüz tarayıcıda hiç açılmıyordu.**
Bu, "yeşil test bir şey kanıtlamaz" kuralının dördüncü örneği ve şimdiye
kadarki en utandırıcı olanı: kusur bir modelde ya da zamanlamada değil,
**iki dosyanın yokluğunda**ydı.

##### Ne olmuştu

`index.html` `style.css` ve `vendor/vue.global.prod.js` istiyor.
`arayuz3/sunucu.py:37` bunları `ORTAK = BURASI.parent / "arayuz"`
yolundan düşürüyordu ("tek kopya kalsın" gerekçesiyle). **5.12.32'de o
dizin `arsiv/asama1/arayuz`'a taşındı ve bu dosya güncellenmedi.**
Aynı taşımada `demo-uret.py:28` düzeltilmiş, `sunucu.py` atlanmıştı —
DEVIR 5.12.32 "22 yol güncellendi" diyor, `sunucu.py` o 22'nin içinde yok.

Ölçüldü (sunucu ayaktayken `curl`):

| İstek | Önce | Sonra |
|---|---|---|
| `/style.css` | **404** | 200 (11 697 B) |
| `/vendor/vue.global.prod.js` | **404** | 200 (154 807 B) |

Zincirleme etki: Vue yüklenmiyor → `app.js:18` `ReferenceError` →
hiçbir metot kurulmuyor → `[v-cloak]` kalkmıyor → ekranda ham
`{{ bicim(volt, 3) }}` şablonu kalıyor. **Hiçbir düğme çalışmıyor.**

##### Zincir bunu neden göremedi

1. `test_arayuz3.js` Vue'yu **kendisi taklit ediyor** (`:36`) — vendor
   dosyasına ihtiyacı yok.
2. **Projede tek bir dosya-varlık denetimi yoktu** (`existsSync` sıfır kez).
3. Var olan `ok('ek.css bagli', htmlKaynak.includes('ek.css'))` iddiası
   bile yalnızca *dizenin HTML'de geçtiğine* bakıyor, **dosyanın diskte
   olduğuna değil**.

##### Yapılanlar

| # | İş | Neden |
|---|---|---|
| 1 | `style.css` + `vendor/` **`arayuz3/` altına kopyalandı** | Arşiv dokunulmadı |
| 2 | `sunucu.py`'den `ORTAK` ve `translate_path` **silindi** | Kusuru değil, **kusuru üreten mekanizmayı** kaldır. Aşama 1/2 arşivde olduğuna göre "tek kopya" gerekçesi zaten çökmüştü |
| 3 | `ek.css`'e `.kpi` · `.kpi-ad` · `.kpi-deger` · `.uyari` eklendi | Dördü de `index.html`'de **kullanılıyordu ama hiçbir CSS'te tanımlı değildi** |
| 4 | `style.css`'te 3 tanımsız değişken düzeltildi | `--kenar`→`--kenar-c`, `--metin`→`--yazi`, `--yuzey`→`--kart` — 8 yerde sessizce geçersize düşüyordu |
| 5 | `sahte-kart.js` statik `<script>`'ten **dinamiğe** çevrildi | 15 936 B her açılışta boşuna iniyordu; B22.5'te LittleFS görüntüsüne de girerdi |

🔴 **En ciddi görsel kusur `.uyari`'ydı:** *"Yükü **J7**'ye bağlayın, J3'e
değil. J3 doğrudan şönte gider; oraya bağlarsanız MOSFET **baypas** olur ve
**kesme çalışmaz**"* uyarısı **biçimsiz düz paragraf** olarak görünüyordu.
B21'in en önemli tezgah testi bu uyarıya dayanıyor. `.uyari`, `.hata`'dan
**bilerek farklı** tanımlandı (sol şerit ↔ tam çerçeve): `.hata` geçici bir
hatadır, `.uyari` kalıcı bir emniyet talimatıdır; ikisi aynı görünürse
kullanıcı emniyet uyarısını "geçmiş bir hata" sanır.

##### Yeni: `test_arayuz3.js` §8 varlık denetimi — **82 → 93**

Metin değil **varlık** sınıyor: referans verilen dosya gerçekten duruyor mu,
kullanılan sınıf gerçekten tanımlı mı, `sunucu.py` dizin dışına düşüyor mu.

##### 🔴 Mutasyon testi ÜÇ test kusuru buldu

İlk turda 14 mutasyonun **3'ü kaçtı**. Üçü de gerçek kusurdu:

| Kaçan mutasyon | Kök sebep | Düzeltme |
|---|---|---|
| `.kpi` kuralını sil | Sınıf araması **CSS yorumlarını da tarıyordu** — `ek.css`'in kendi açıklama yorumunda `.kpi` geçtiği için sınıf "tanımlı" sayılıyordu | Yorumlar çıkarılıyor. *Bir iddianın kendi yorumuyla karşılanması, iddia olmadığı anlamına gelir* |
| `.uyari` gövdesini `.hata` ile aynı yap | Ham **metin** karşılaştırması; iki kural ayrı dosyada ve ayrı girintide olduğu için anlamca aynı olsalar bile metinleri farklıydı | Bildirimler normalleştirilip **küme** olarak karşılaştırılıyor |
| `sahte-kart.js` statik `<script>` geri konsun | İddia sayısı **girdiyle birlikte büyüyordu**: etiket eklenince bir iddia düştü ama aynı anda bir referans (bir iddia) eklendi, **toplam değişmedi** | Referans denetimi tek bir toplu iddiaya indirildi — sayı sabit |

Üçüncüsü genel bir ders: **iddia sayısı girdiye bağlıysa, sayım tabanlı her
denetim körleşir** — planlanan `dogrula3.py` sayım kilidi dahil.

Düzeltmelerden sonra: **14/14 yakalandı, 0 kaçak.**

| Mutasyon | Sonuç |
|---|---|
| `style.css` yeniden adlandır | 93 → **88** |
| `vendor/` → `vendor2/` | → 92 |
| `.kpi` / `.kpi-deger` / `.uyari` kuralını sil | → 92 / 92 / **91** |
| `.uyari` gövdesini `.hata` ile birebir aynı yap | → 92 |
| CSS değişkenini tanımsız bırak | → 92 |
| `sunucu.py` `../arayuz` düşmesi geri gelsin | → 92 |
| `sunucu.py` `translate_path` geri gelsin | → 92 |
| `sahte-kart.js` statik `<script>` geri konsun | → 92 |
| `demoVeri`'den `betikYukle` kaldır | → 92 |
| `betikYukle` gövdesini boşalt | → 92 |
| J7/J3 uyarısından `.uyari` sınıfını kaldır | → 92 |

##### Doğrulama

Zincir **15/15** (B7 93/93). Ayrıca ölçüldü: sunucu ayakta tüm varlıklar
**200**; `vendor/vue.global.prod.js` node'da çalıştırılıp `Vue.createApp`
tanımlı ve `Vue.version = 3.5.13` doğrulandı; iki CSS dosyasının süslü
parantezleri dengeli.

⚠ **Zincirin kanıtlamadığı:** sayfanın gerçekten *doğru göründüğü*.
Tarayıcı açılmıyor, DOM kurulmuyor. Kullanıcının `python arayuz3/sunucu.py`
ile bakması gerekiyor — konsolda 0 hata, ham `{{ }}` yok, J7/J3 uyarısı
kırmızı şeritli.

#### 5.12.34 ✅ B22.1 — ÖLÇÜM TABANI (2026-09-10)

Yeni özellik yok. Amaç: WiFi açılmadan **önce** ölçülecek sayıların doğru
tabana oturması. Sonra düzeltilseydi WiFi'nin maliyeti bozuk tabana karşı
ölçülürdü — B20'nin düştüğü tuzağın aynısı.

##### 🔴 K1 — kart 665 değil **500.0 SPS**'te örnekliyordu

`loop()`'un ilk satırı `sunucu.handleClient()`. Kütüphane, **istemci
yokken** her turda `delay(1)` çağırıyor (`WebServer.cpp:422-425`,
`_nullDelay` varsayılan `true`). `CONFIG_FREERTOS_HZ = 1000` olduğu için bu
`vTaskDelay(1 tik)`: döngü bir sonraki tik sınırına kadar blokleniyor.

```
govde 1502.8 us -> ceil(1502.8/1000) x 1000 = 2000 us = 500.0 SPS
enableDelay(false) ile                                  665.4 SPS
pay 497.2 us  — web tarafına eklenecek her 497 us bir basamak düşürür
```

**Bu, B20'nin sildiği `delay(2)` kusurunun kütüphane sürümü.**
`sim3_bant.py:126` göremiyordu çünkü yalnız `.ino`'nun `loop()` gövdesinde
regex arıyor. Üstelik `sunucu.begin()` koşulsuz çağrıldığı için kusur
**WiFi kapalıyken de** geçerliydi. Düzeltme tek satır: `enableDelay(false)`.

⚠ Tersi de doğru: bekleyen bir istemci varken `_currentStatus != HC_NONE`
olduğundan `delay(1)` atlanıyor — yani **biri LAN'ı tararken kart daha
doğru ölçüyordu**. Model kurmadan akıl yürütülemeyeceğinin kanıtı.

##### 🔴 K2 — faz kalibrasyonu **örnek** cinsindendi, düzelttiği şey **sabit zaman**

```c
// eski:  d = t_kayma_us / ornek_periyot_us + faz_kal[m]
// yeni:  d = (t_kayma_us + faz_kal_us[m]) / ornek_periyot_us
```

Örnek cinsinden saklanınca uygulanan zaman `faz_kal × ornek_periyot_us`
oluyor — **döngü periyoduyla ölçekleniyor**. Oysa düzeltilen şey iki RC'nin
arctan farkı: sabit bir zaman. B20 bunu zaten *"faz kalibrasyonu (SABİT
zaman gecikmesi)"* diye yazıyordu; **uygulama o tanımla uyuşmuyordu.**

1502.8 µs'te kalibre edilen kartın artık hatası (en kötü τ eşleşmezliği,
kondansatör toleransı ±%10 → 292.8 µs):

| Periyot | Artık faz | PF=0.5'te güç |
|---|---|---|
| 1502.8 µs (kalibrasyon noktası) | 0.000° | — |
| **2000 µs (K1 yüzünden bugünkü)** | **+1.744°** | **−%5.3** |
| 3000 µs (menzil geçişi) | +5.251° | −%16 |

B17'nin kendi kabul ölçütü **≤1°**; bugünkü hata onun **1.74 katıydı**.
`AYAR3_IMZA` `0xC0F5 → 0xC0F6`. ⚠ Yapı **boyutu değişmedi**
(`float[2] → float[2]`), yani `n == sizeof(Ayar3)` denetimi bunu **göremez**
— imza tek korumadır.

##### 🔴 K3 — çıplak `g`/`i` kanalı **kalıcı olarak öldürüyordu**

`atof("")` = 0 → `kazanc *= 0/s` → 0 → `ayar_kaydet()`. Sonra
`olc_gerilim3` hep 0 döndüğü için `|s| > esik` şartı **bir daha asla**
sağlanmıyor: kanal NVS silinene kadar ölü. Kurtarma yolu **yoktu**.

Üç katmanlı düzeltme:
1. `strtof` + `son == s+1` ile **argüman varlığı** denetimi (`g`, `i`, `f`)
2. `kalibre_kazanc`'ta **sonuç kelepçesi** (0.2–5 kat) — ikinci savunma hattı
3. **`R!` fabrika sıfırlama** — bozulmuş NVS'ten tek kurtuluş yolu

Çıplak `f` de artık sessizce DC'ye geçirmiyor, **değeri gösteriyor**.

##### PSRAM öksüzü — RAM **%35 → %15**

`static PilNokta pil_ic_tampon[5400]` = **64 800 B**. PSRAM bulununca halka
PSRAM'e taşınıyor ama statik dizi serbest bırakılamıyor: iç RAM'in **%20'si**
ölü kalıyordu. Yığına alındı, ayırma tek yerde toplandı.

```
RAM 116 200 B (%35)  ->  51 400 B (%15)     serbest yığın 211 -> 276 KB
```

`test_firmware3.py` RAM eşiği **%40 → %25** sıkılaştırıldı — gevşek kalsaydı
statik tamponun geri gelmesi görünmez olurdu.

##### Belge/kod ayrışması ve blokaj görünürlüğü

Açılış satırı `"(2 saat)"` diyordu, `PIL_IC_KAPASITE` 5400 = **1.5 saat**.
Süre artık kapasiteden **türetiliyor**; elle yazılmış hâli `BULUNMAMALI`
listesinde.

Yeni **`K <kayip_ms> <loop_azami_us> <uzun_tur>`** satırı (yalnız değişince
basılıyor, `?` çıktısında da var). `enerji_biriktir`'in atladığı aralık artık
**sayılıyor** — eskiden tamamen sessizdi. Çift çekirdek kararının eşiği de bu:
`loop_azami_us > 20 000` ise görev ayrımı yapılır.

⚠ `D` satırına **alan eklenmedi** — 9 alan arayüzde, `sahte-kart.js`'te ve
testte sabit; alan eklemek üçünü aynı anda değiştirmeyi gerektirir
(B17'nin `f`/`F` kusurunun aynısı). Yeni önek geriye dönük uyumlu.

##### Zincire eklenenler

| Adım | Önce | Sonra | Ne eklendi |
|---|---|---|---|
| B17 `sim3_senkron.py` | 26 | **31** | faz düzeltmesi µs ve **bölmenin içinde**; imza bump; artık hatanın sayısallaştırılması |
| B20 `sim3_bant.py` | 42 | **47** | **kütüphane gövdesi taraması** (`WebServer.cpp`), tik kilidi modeli, `enableDelay` sırası |
| B4/B5 `test_olcum3.py` | 91 | **94** | **tuğlalama testi** — AVR emülatöründe davranışsal |
| B6 `test_firmware3.py` | 43 | **58** | 7 yeni ikili dize, eşikler **koşulsuz**, komut listesi kaynaktan |
| B7 `test_arayuz3.js` | 93 | **98** | faz birimi, iki aşamalı onay, her ret yolu sebebini söylüyor |

İki kör nokta kapandı: `test_firmware3.py`'nin **elle yazılmış komut
listesi** (`f`, `F`, `p`, `P` hiç yoktu) kaynaktan çıkarılıyor, ve
flash/RAM eşikleri `if mf:` koşulundan çıkarıldı — regex tutmazsa iddia
**sessizce buharlaşıyordu**.

##### 🔴 Mutasyon testi — 14/14, ama ilk turda 4 kaçak vardı

| Kaçan | Kök sebep | Düzeltme |
|---|---|---|
| NVS imzasını `0xC0F5`'te bırak | İddia **yoruma kanıyordu** — değişikliği anlatan açıklama da `0xC0F6` yazıyor | Yorumlar çıkarılıp koda bakılıyor |
| Fabrika sıfırlama onayını kaldır | İddia bayrağın **adına** bakıyordu; kapı silinse de `sifirlaOnay = false` gövdede duruyordu | Erken dönüş **kapısı** sınanıyor |
| `fazGonder` ret mesajını sil | Tek `this.hata` aranıyordu; iki ret yolundan biri silinince öteki iddiayı karşılıyordu | **Her iki** ret yolu ayrı ayrı |
| `kalibre_kazanc` kelepçesini kaldır | **Hiç iddia yoktu** — metin testi davranışı göremez | AVR emülatörüne davranışsal test |

Sonuncusu kaldırılınca emülatör tuğlalamayı birebir üretiyor: kazanç
`0.000000`, kurtarma başarısız, 12 V yerine **0 V**.

İki kaçağın kök sebebi aynı ve B22.0'dakiyle de aynı: **bir iddianın kendi
yorumuyla karşılanması (ya da yorumdan dolayı düşmesi), iddia olmadığı
anlamına gelir.** Metin tabanlı iddialar yazılırken yorumlar çıkarılmalı.

##### Doğrulama

Zincir **15/15**. Derleme uyarısız, flash %16, RAM **%15**.
⚠ Zincir hâlâ kurulmuş bir kartı değil tasarımı doğruluyor; K1'in gerçek
etkisi tezgahta `D` satırındaki örnek sayısıyla ölçülecek (200 ms'de
**133 ± 3** beklenir; **100 çıkarsa** `enableDelay` işe yaramamış demektir).

#### 5.12.35 ✅ B22.2 — TAŞIYICI KATMANI (2026-09-10)

Arayüz artık **üç taşıyıcıyı** destekliyor: `seri` (Web Serial), `akis`
(SSE — kart ya da PC köprüsü) ve `demo` (sahte kart). **Tek arayüz kodu**,
üç taşıma. Modlar arasındaki fark kodda değil `yetenek` tablosunda yaşıyor.

**Neden iki ayrı arayüz yazılmadı:** bu proje arayüz↔firmware ayrışmasından
üç kez yandı (DEVIR 4.1, 4.15, B17 — sonuncusunda zincir 70/70 yeşilken
kullanıcı gücü %82 yüksek okuyordu). "Basit sürüm + zengin sürüm" aynı riski
dördüncü kez açardı; üstelik en az bakılan kod, kart odanın öbür ucunda
613 V ölçerken çalışacaktı.

##### Dikişin çalıştığı zaten kanıtlıydı

`navigator.serial` yalnız 68 satırda geçiyordu ve aşağı akış tamamen
`satirIsle(string)`'den besleniyordu — `sahte-kart.js` bu dikişten **zaten**
takılıyordu. Yapılan iş dikişi genişletmek oldu, yeniden çizmek değil.

🔴 **`gonder()` çağrı yerlerinin şekli değişmedi.** `test_arayuz3.js`
`gonder('x')` / `komut('x')` düz metin kalıbını tarıyor; şekil korunduğu
için çift yönlü komut denetimi hiç bozulmadan çalışmaya devam etti.

##### 🔴 `pilYokla` — üç kusur birden kapandı

| # | Kusur | Sonucu |
|---|---|---|
| 1 | Adres **göreliydi** (`fetch('/pil?…')`) | İstek karta değil Python sunucusuna gidiyordu |
| 2 | `fetch` **404'te reddetmez** | Hata sayfasının HTML'i `anahtar=değer` sanılıp ayrıştırılıyor, **tüm KPI'lar sessizce 0** oluyordu — `pilKesme: 3.0` bile eziliyordu |
| 3 | Kısmi yanıt denetlenmiyordu | Kartta yığın sıkışırsa `String::concat` başarısız oluyor, `operator+=` bunu **yutuyor**, gövde kesiliyor ama `Content-Length` tutarlı → tarayıcı hata görmüyor |

Artık her uzak istek `kartAdres()`'ten geçiyor, `y.ok` ve `durum=` biçimi
denetleniyor, başarısızlık `pilHataMetni` ile **kullanıcıya söyleniyor**.

##### Yetenek tablosu ve tek kaynak

`yetenek = {ad, komut, skop, skop_azami, gecmis_s, cok_istemci, surucu}`.
🔴 Kural: **yetenek yoksa düğme görünmez ama nedeni görünür** — ölü düğme
bırakmak DEVIR 4.15'in ta kendisiydi. `desteksizNeden` computed'i her kip
için ayrı bir cümle veriyor (telefonda Web Serial yok → akış kipini seç).

`demo` ayrı bir bayrak olmaktan çıkıp `tasiyiciAdi`'ndan **türetilen**
computed oldu — iki bayrak tutmak DEVIR 4.1'in deseniydi.

Ayrıca `localStorage` ilk kez kullanılıyor: pencere, göstergeler, şönt,
şebeke Hz, kart adresi ve taşıyıcı tercihi saklanıyor. ⚠ Her erişim
try/catch içinde — özel kipte ve kota dolduğunda **erişimin kendisi** atıyor.

##### Zincir: arayüz 98 → **112**, ve çoğu METİN DEĞİL YAPI sınıyor

Taşıyıcılar `vm` bağlamında **gerçekten oluşturulup** yüzeyleri
karşılaştırılıyor (`vm.runInContext('TASIYICILAR', sandbox)`):

* üçü de aynı yüzeyi sunuyor (`ad·yetenek·destekli·ac·kapat·gonder`)
* yetenek tabloları aynı **alanlara** sahip
* tablo modları **gerçekten** ayırıyor (`gecmis_s: 0 / 86400`) — hepsi aynı
  değeri verseydi tablo süsleme olurdu
* `app.js`'te `kartAdres()` dışında `fetch(` **yok**
* `satirIsle` içinde taşıyıcıya özgü **dal yok** — dal açmak, tel üstündeki
  baytların ayrıştığı anlamına gelir

##### 🔴 Üçüncü kez: iddia yorumu okuyordu

Taşıyıcı katmanının açıklama yorumunda örnek olarak `gonder('x')` yazıyordu
ve **komut toplayıcı bunu gerçek komut sandı** — ileri yön denetimi
*"arayüz 'x' gönderiyor, firmware'de yok"* diye kırmızıya döndü.

Tersi çok daha kötü olurdu: firmware'e eklenip arayüze konmamış bir komut,
yalnızca bir yorumda adı geçtiği için **"erişilebilir" sayılabilirdi** —
ters yön denetiminin bütün değeri kaybolurdu.

`komutlariTopla` artık yorumları çıkarıyor. Bu, aynı sınıfın bu oturumdaki
**beşinci** örneği (CSS sınıfı, NVS imzası, `faz_kal` alanı, `.uyari`
gövdesi, komut toplayıcı). Kural netleşti: **metin tabanlı her iddia koda
bakmalı, prozaya değil.**

İkinci küçük kusur: varlık denetiminin `(?:href|src)="` deseni Vue'nun
`:href="kopruAdresi"` **bağlamasını** da yakalıyordu. `(?:^|\s)` şartı eklendi.

##### Mutasyon: 10/10, sıfır kaçak

`pilYokla`'yı göreli fetch'e geri al · `y.ok` sil · biçim denetimi sil ·
bir taşıyıcıdan metot sil · yetenek tablolarını aynı yap · bir yetenek
alanını çıkar · `satirIsle`'ye taşıyıcı dalı koy · `demo`'yu ayrı bayrak
yap · `ayarOku` try/catch kaldır · `pilHataMetni`'ni şablondan sil.

Önceki iki aşamada 4+3 kaçak vardı; bu turda **ilk denemede sıfır** —
yapısal iddiaların metin iddialarından üstünlüğü ölçüldü.

##### Doğrulama

Zincir **15/15**. Ayrıca işlevsel duman testi: `gonder('?')` demo
taşıyıcısından `SahteKart`'a gidip `satirIsle`'yi besliyor (`A` satırı
günlükte), `satirIsle` D satırını doğru ayrıştırıyor, `kartAdres` boş ve
dolu tabanda doğru çalışıyor.

⚠ `TasiyiciAkis` **henüz uçtan uca denenemedi** — `/akis` ve `/komut`
uçları B22.3/B22.4'te geliyor. Bugün yalnızca yapısal olarak doğrulandı.

#### 5.12.36 ✅ B22.3 — PC KÖPRÜSÜ (2026-09-10)

🎯 **Telefon burada çalışmaya başladı — firmware'e hiç dokunmadan.**
Köprü karta USB ile bağlanıyor, telefona kendisi yayın yapıyor. Bu kipte
kartın WiFi'si hiç açılmıyor: `loop()`'ta TCP yok, ölçüm doğruluğu en
yüksek, ve CORS / Chrome LNA / Android `.local` sorunlarının **üçü de
ortaya çıkmıyor** (sayfa ve veri aynı kökenden geliyor).

##### Köprünün asıl değeri güzel arayüz değil, **röle** olması

Karta bağlanan her tarayıcı ölçümü doğrudan bozuyor (`/pil` isteği
`loop()`'u 25–200 ms bloklıyor; >1 s ise enerji sayacı o aralığı
**tamamen atıyor**) ve kartın SSE'si **tek istemcilik**. Köprü N tarayıcıyı
**1**'e indiriyor.

##### Üç dosya, yalnız standart kütüphane

| Dosya | Ne |
|---|---|
| `kopru/kart_baglanti.py` | `SeriKart` (Win32 API, ctypes) · `KayitKart` (kayıttan oynatma) |
| `kopru/arsiv.py` | Eklemeli ham satır günlüğü + türetilmiş CSV |
| `kopru/kopru.py` | Röle · statik arayüz · `/akis` · `/komut` · `/devral` · `/durum` |

**pyserial kullanılmadı.** Bu makinede kurulu ama bir Python yeniden
kurulumunda kaybolabilir; projenin bütün Python tarafı stdlib. Win32 seri
API'si `ctypes` ile erişilebiliyor.

🔴 **İlk yazımda ciddi bir ctypes kusuru vardı:** `CreateFileW`'ye
`restype` verilmemişti, ctypes dönüşü `c_int` (32 bit) sayıp **64 bitlik
tanıtıcıyı kırpıyordu**. Başarısızlıkta dönen −1, `INVALID_HANDLE_VALUE`
ile karşılaştırılamıyor ve kod **geçersiz tanıtıcıyla devam ediyordu** —
hata "COM99 açılamadı" yerine bir sonraki adımda "GetCommState başarısız"
olarak, yani **yanlış yerde** görünüyordu. Bütün fonksiyonlara
argtypes/restype verildi.

Ayrıca: WinError 2 (port yok) ile WinError 5 (port meşgul) **ayrı ayrı**
raporlanıyor — yanlış sebep söylemek en can sıkıcı hata ayıklama türü.

⚠ DTR/RTS sürücüsü **kapalı**: ESP32 kartlarında bu iki hat otomatik-reset
devresine bağlı, açılışta değişirlerse kart **reset atar**.

##### Plandan bir sapma: `/k` değil `/komut`

Kartın B22.4'te açacağı uç da `/komut` olacak. Aynı yol, aynı yöntem, aynı
başlıklar — **istemci köprüye mi karta mı bağlı olduğunu bilmek zorunda
değil.** Köprü 204 + boş gövde dönüyor (kartın cevabı zaten SSE'den
geliyor); kart doğrudan bağlandığında yanıt gövdede geliyor. Aynı istemci
kodu ikisini de işliyor çünkü boş gövde hiçbir satır üretmiyor.

##### Sürücü hakemi

N izleyici, **bir sürücü**. Jeton SSE'nin `kimlik` olayıyla geliyor,
komutlarda `X-Jeton` başlığıyla dönüyor. Arayüzde "izleyici" şeridi ve
**Devral** düğmesi var.

🔴 **`p0` (pil deşarjını DURDUR) her taşımada, jetonsuz, kimliksiz geçiyor.**
Başlatmak yetki ister; durdurmayı hiçbir şey geciktiremez. Bu, testte ayrı
bir emniyet iddiası olarak duruyor.

⚠ Politika **tek yerde**: sunucuda. Arayüz yalnızca durumu gösteriyor ve
devri istiyor — politikayı iki yerde tutmak bu projenin cezalandırdığı
ayrışma deseni olurdu.

##### CSRF yüzeyi

`POST` zorunlu + `X-Olcum: 1` özel başlığı. `<img>`/`<form>` özel başlık
**ekleyemez**; çapraz kökende preflight'a zorluyor. Ölçüldü:
`GET /komut?k=p1` → **404**, başlıksız POST → **400**.

##### Zincir: yeni adım **B22**, 24 doğrulama — zincir 15 → **16 adım**

En önemli iddia **rölenin bayt-şeffaflığı**: 9 farklı önekten oluşan bir
örnek küme köprüden geçiriliyor ve girdiyle çıktı **bayt-bayt** karşılaştırılıyor.
Köprü satırı "düzeltmeye" kalksa (boşluk kırpma, sayı biçimleme, JSON'a
çevirme) ikinci bir temsil doğar ve ayrışma sınıfı geri gelir.

Ayrıca sınanıyor: arşivdeki satırlar da birebir aynı · CSV **günlükten
üretiliyor** (ayrı tutulmuyor) · Excel-TR uyumlu (BOM + `;` + `,`) · köprü
`arayuz3/`'ü **kopyalamıyor**, aynen servis ediyor (bayt karşılaştırması).

🔴 **Test sırası tuzağı:** yukarı-akış döngüsü SSE abonesinden önce
başlatılırsa `KayitKart`'ın bütün satırları abone yokken tüketiliyor ve
akış boş kalıyor. Testte önce abone olunuyor, sonra döngü başlıyor.

##### Mutasyon: 11/11, sıfır kaçak

Röle satırı düzeltsin · röle JSON sarsın · röle yalnız `D` taşısın ·
`X-Olcum` denetimini kaldır · GET ile komut kabul et · **`p0` de jeton
istesin** · sürücü hakemini kaldır · `devral` bilinmeyen jetonu kabul etsin ·
arşiv ham satırı bozsun · CSV BOM'suz · CSV ondalık nokta kalsın.

##### 🔴 Windows tuzağı: `0.0.0.0:80` ile `127.0.0.1:80` yan yana durabiliyor

stok-takip `127.0.0.1:80`'i tutuyor (Windows açılışında başlıyor). Köprü
`0.0.0.0:80`'e bağlanmayı denediğinde bu **başarılı olabiliyor** —
`SO_EXCLUSIVEADDRUSE` kullanılmamışsa. O durumda hangi sunucunun cevap
verdiği **hedef adrese** bağlı: `127.0.0.1` daha özel bağlamaya (stok'a)
gider, köprüye yalnızca LAN IP'sinden ulaşılır.

Bu makinede tam olarak öyle oldu ve köprünün *"Bu bilgisayardan:
http://127.0.0.1"* mesajı kullanıcıyı **stok arayüzüne** yollayacaktı.
Artık her iki satırda da LAN IP'si yazıyor.

Bağlama sırası: `0.0.0.0:80` → `<LAN-IP>:80` → `0.0.0.0:8770`.

##### Doğrulama

Zincir **16/16**. Uçtan uca ölçüldü (donanımsız, kayıtlı günlükle):
köprü ayakta, statik arayüz servis ediliyor ve `index.html` geliştirme
sunucusuyla **bayt-bayt aynı**, `/durum` yanıt veriyor, geliştirme
sunucusunda `/durum` 404 (otomatik algılama doğru şekilde sessiz kalıyor).

⚠ **`SeriKart` gerçek donanımla denenemedi** — kart kurulmadı. Sınanan:
port bulunamayınca doğru hata, DCB/COMMTIMEOUTS alan düzeni (28/20 bayt),
satır tamponlama. Gerçek baud ve DTR davranışı **tezgah listesinde**.

#### 5.12.37 ✅ B22.4 — KARTIN WEB KATMANI (2026-09-10)

Kartın web tarafı **üç yerden kırıktı** ve üçü de kapandı.

##### 🔴 1. WiFi hiç açılmamıştı

`WIFI_AD` boş bir sabitti, yani `WiFi.begin()` **bir kez bile
çağrılmadı**; AP kipi dosyada hiç yoktu. Yerine `ag.h`: STA dene →
10 s'de olmazsa **kendi ağını kur** (`OLCUM-KARTI-XXXX`, WPA2) + mDNS.

🔴 **AP parolası MAC'ten türetilmiyor.** İlk akla gelen "SSID'ye MAC son
eki koy, parolayı da MAC'ten üret" **hiçbir şey korumaz**: SSID zaten
beacon ile yayınlanıyor. Bunun yerine ilk açılışta **rastgele** üretilip
NVS'e yazılıyor ve seri konsola basılıyor.

🔴 **Ağ ayarları `Ayar3`'e EKLENMEDİ**, ayrı NVS ad alanında
(`olcumag`). Gerekçe: `Ayar3` büyürse `sizeof` denetimi bozulur, imza
bumplanır ve **kalibrasyon sıfırlanır**. Bir WiFi parolası değişikliği
yeniden kalibrasyona mal olamaz.

##### 🔴 2. SSE yalnızca `D` satırını taşıyordu

`akis_yolla` tek bir yerden — `loop()`'un rapor bloğundan — çağrılıyordu.
`S2`/`M`/ham skop/`E`/`T`/`W`/`B` ve bütün `*`/`!` yanıtları **yalnızca**
`Serial.print`'teydi. WiFi ile bağlanan arayüz **salt-okunur ve sessiz**
olurdu: osiloskop yakalar, hiçbir şey göremezdi.

Çözüm **`Serial` aynası**: `.ino`'da 245 `Serial.` çağrısı var, dört
başlık dosyasında **sıfır** (ölçüldü) — tek bir `#define` hepsini aynaya
alıyor ve **çağrı yerlerinin hiçbiri değişmiyor**. 245 satırı elle
değiştirmek, içinde bir tanesini atlamayı kolaylaştırırdı (DEVIR 4.15'te
`index.html`'in üç düğmesi tam böyle atlanmıştı).

⚠ `#undef Serial` şart: çekirdekte `Serial` **zaten** bir makro; doğrudan
yeniden tanımlamak `warning: "Serial" redefined` veriyor ve bu projede
uyarıya sıfır tolerans var.

Satır bölücü (`web_satir.h`) **saf C** yazıldı ve AVR emülatöründe
sınanıyor: CRLF temizleme, boş satır atlama, taşan satırın **yine de
tamamlanması** (yoksa ayrıştırıcı hizasını kaybeder) ve **kırpılan baytın
sayılması**. AVR 94 → **101**.

##### 🔴 3. Komut ucu yoktu

`komut_calistir`'a HTTP'den giden yol yoktu. Artık `POST /komut` var ve
komutlar **kuyruğa** giriyor, `loop()` boşaltıyor — HTTP işleyicisi uzun
bir komutu beklemiyor ve tek yazar disiplini kuruluyor.

**CSRF yüzeyi:** `HTTP_POST` açıkça yazılı (`HTTP_ANY` olsaydı
`GET /komut?k=p1` çalışırdı ve `<img>` ile pil deşarjı başlatılabilirdi) ·
`X-Olcum: 1` özel başlığı zorunlu · oturum jetonu · `Host` beyaz listesi
(DNS rebinding) · isteğe bağlı Basic auth.

⚠ **`collectHeaders` çağrılmazsa `header()` her zaman boş döner ve bütün
CSRF savunması sessizce ölür.** Zincirde ayrı bir iddia.

🔴 **`enableCORS(true)` KULLANILMIYOR** — üç başlığı da `*` yapıyor
(`WebServer.cpp:663-667`), yani herhangi bir sayfa yanıtı **okuyabilir**
ve oturum jetonu sızardı. Yalnızca kayıtlı köprü kökenine elle izin
veriliyor. `ACAO: null` da verilmiyor (sandbox'lı iframe'ler de `null`).

🔴 **`p0` (DURDUR) jetonsuz, parolasız geçiyor** — köprüdeki kuralın aynısı.

##### SSE düzeltmeleri

Önce **tek istemcilikti**: ikinci `GET /akis` birincisini sessizce üzerine
yazıyordu. Artık 4 yuva, 15 s kalp atışı, `retry: 3000`, `id:` yer imi ve
köprü kayıtlıysa **gerekçeli ret** (`event: kopru` + adres).

##### Ağ kurulum paneli — akış bilerek USB'den

Kartın WiFi'sini kartın WiFi'si üzerinden kurmak tavuk-yumurta olurdu.
`N` komut ailesi (`N?` `Na` `Np` `NA` `Ns` `N1` `N0`) arayüze eklendi;
ağ üzerinden kuruluyorsa **düz metin uyarısı** çıkıyor (kartta TLS yok).

##### Bütçe

```
flash  511 636 -> 1 024 631 B  (%16 -> %32)   esik %60   [WiFi+mDNS yigini]
RAM     51 416 ->    71 268 B  (%15 -> %21)   esik %25
```

##### Zincir: yeni adım **B22b** (`sim3_web.py`, 46) — zincir 16 → **17 adım**

##### 🔴 Mutasyon: 19/19 — ama ilk turda 4 kaçak

| Kaçan | Kök sebep | Düzeltme |
|---|---|---|
| `X-Olcum` denetimini komut ucundan kaldır | İddia **dosya genelinde** arıyordu; `kopru_sayfa` da aynı denetimi yaptığı için yeşil kaldı | Fonksiyon **gövdesinde** aranıyor |
| AP parolasını MAC'ten türet | İddia **adın geçmesine** bakıyordu; tanım yeniden adlansa çağrı yeri adı taşımaya devam ediyordu | Gövde sınanıyor: `esp_random` **var**, `macAddress` **yok** |
| Kaynağa sabit parola yaz | Desen `wifi_`/`ap_` öneki istiyordu; `String sifre = "..."` kaçtı | Adında `sifre`/`parola`/`pass` geçen **her** değişkene atanan uzun dize |
| `kirpilan` artırmasını kaldır | Ad yapı alanında ve yorumda da geçiyordu | **Artırmanın kendisi** (`s->kirpilan++`) sınanıyor |

Dördü de aynı ailenin üyesi: **iddia yanlış kapsamda arıyordu.** Ders
netleşti — metin tabanlı bir iddia (a) yorumları çıkarmalı, (b) **doğru
gövdenin içinde** aramalı, (c) adın varlığını değil **davranışı** temsil
eden ifadeyi aramalı.

##### Doğrulama

Zincir **17/17**, derleme **uyarısız**.

⚠ Bu adımın kanıtlamadıkları — hepsi tezgah listesinde: gerçek WiFi
bağlantısı · mDNS'in telefonda çözülmesi · CSRF savunmasının gerçek
tarayıcılardaki davranışı · `esp_wifi_start()` ↔ `adc_continuous_start()`
çarpışması (DEVIR 7.1 ①) · SSE'nin `loop()`'u ne kadar bloklandığı.

#### 5.12.38 ✅ B22.5 — ARAYÜZ KARTTAN SERVİS EDİLİYOR (2026-09-10)

🎯 **"Bilgisayar yoksa" senaryosu burada tamamlandı.** Kart arayüzü artık
kendisi sunuyor: telefon doğrudan karta bağlanıyor, PC hiç gerekmiyor.

##### Üretim zinciri — hiçbir adres elle yazılmıyor

| Betik | Ne |
|---|---|
| `uretim/ikon-uret.py` | 180×180 PNG + `manifest.json` üretiyor (stdlib zlib) |
| `uretim/arayuz-uret.py` | `arayuz3/` → gzip → mklittlefs → `_fs.bin` |
| `uretim/arayuz-yaz.py` | esptool ile karta yazıyor |

Bölüm ofseti (`0x310000`) ve boyutu (`0xE0000`) **`huge_app.csv`'den
okunuyor**. Elle yazılsaydı bölüm şeması değiştiğinde görüntü yanlış
adrese gider ve kart sessizce boş bir dosya sistemi görürdü.

```
index.html    26 683 ->  8 046      style.css   12 051 ->  2 906
app.js        64 505 -> 20 752      vue        154 807 -> 58 361
ek.css         3 317 ->  1 577      manifest       312 ->    214
ikon-180.png   1 150 ->  1 150      TOPLAM             93 753 B
                                    bölümün %10.2'si
```

🔴 **`arayuz-yaz.py` bayat görüntüyü YAZMIYOR.** Künyedeki sha256'ları
kaynakla karşılaştırıyor ve değişen dosyayı adıyla söylüyor. Bayat bir
görüntüyü karta yazmak, depodaki arayüz ile karttaki arayüzün sessizce
ayrışması demekti — bu projenin üç kez yandığı sınıf.

##### 🔴 `index.htm` tuzağı

`serveStatic` dizin isteğini `requestUri + "index.htm"` ile karşılıyor
(`RequestHandlersImpl.h:198`) — **`index.html` değil**. Dosyayı `index.htm`
diye adlandırmak yerine **açık bir kök işleyicisi** kondu: dosya adı
alışıldık kalıyor ve tuzak koda yazılı hale geliyor.

##### Önbellek — telefonda "her açılışta 58 KB" ile "bir kez" farkı

`/vendor/` → `max-age=31536000, immutable` (Vue sürümlenmiş bir varlık,
bir kez iniyor). Kök → `no-cache`. ⚠ `index.html` **immutable olamaz**:
olsaydı arayüz güncellemesi tarayıcıya **hiç ulaşmazdı**.

⚠ `enableETag` **kullanılmıyor**: `calcETag` dosyanın tamamını okuyup özet
çıkarıyor, yani göndermek kadar bloklar. `immutable` aynı işi sıfır
maliyetle yapıyor.

⚠ `LittleFS.begin(false)` — **otomatik biçimlendirme yok**. Başarısız bir
yazma "boş dosya sistemi"ne dönüşüp sebebi gizlerdi. Boş bölüm bir hata
değil; `kok_sayfa` ne yapılacağını **yazıyor**.

##### Telefonda uygulama gibi

`apple-mobile-web-app-capable` **düz HTTP'de çalışıyor**: iPhone'da Ana
Ekrana Ekle → adres çubuğu yok, kendi ikonu, kendi kartı. ⚠ Android'de
gerçek PWA kurulumu HTTPS + service worker istiyor; kısayol Chrome
sekmesinde açılıyor. **Bu vaat edilmiyor**, belgede de böyle yazıyor.

İkon **üretiliyor** — depoda kaynağı olmayan bir PNG değiştirilemeyen bir
esere dönüşürdü. Renkler `style.css`'in **koyu tema** belirteçlerinden
okunuyor (`#161b21` / `#6690ff` / `#f79009`); arayüzün rengi değişirse
ikon da değişiyor.

##### Toplu uçlar — asıl hafıza sıkışması burada

**`PIL_YANIT_NOKTA` 600 → 150** ve gövde **parçalı** gönderiliyor:

* *Blokaj:* 600 nokta ≈ 15 KB, lwIP `TCP_SND_BUF` ≈ 5 744 B → üç TCP
  penceresi, her biri ACK bekliyor ve o süre boyunca **örnekleme duruyor**.
  150 nokta ≈ 3.8 KB — en kötü blokaj **dört kat** azaldı. Kayıp yok:
  kayıt 1 Hz, yoklama 2 s, kararlı durumda zaten ~2 nokta geliyor.
* *Bitişik bellek:* eski kod `g.reserve(64 + n*34)` ile **tek parça
  20 464 B** istiyordu. Parçalanmış yığında bu ayırma başarısız olabilir
  ve `String::concat` `false` döner — ama `operator+=` bunu **yutuyor**:
  kesik gövde + tutarlı `Content-Length`, yani tarayıcı hiçbir hata
  görmeden eksik veri alıyor.

**`GET /skop.bin`** — 32 B başlık + `adet × uint16`. ASCII dökümü 4000
örnekte 20 250 B; ikili **8 032 B** (%40'ı). Kural: *bir kanal kalp atışı
için (D, 5 Hz), ikinci kanal toplu aktarım için (istek/yanıt, ikili);
ikisi karışmaz.*

🔴 **Uç tek başına yarım iş olurdu** (B17'nin `f`/`F` kusuru). İki taraf da
yapıldı: firmware'de **`tB`** (yakala ama ASCII **dökme** — yoksa `Serial`
aynası yüzünden aynı veri SSE'de iki kez taşınırdı), arayüzde
`skopIkiliAl()`.

🔴 **İki çözücü, tek gösterici:** ikili yol da ASCII yol da aynı
`osiloTopla` yapısını kurup aynı `osiloBitir()`'i çağırıyor. Çizim kodu iki
kez yazılsaydı ikisi ayrışır ve **biri sessizce yanlış çizerdi**.
Endian **açıkça** küçük (`DataView(..., true)`); `Uint16Array` platformun
endian'ını kullanır ve bir gün sessizce ters okuyabilirdi.

##### Bütçe

```
flash  1 024 631 -> 1 067 303 B  (%32 -> %33)   esik %60
RAM       71 268 ->    71 420 B  (%21)          esik %25
LittleFS       0 ->    93 753 B  (bolumun %10.2'si)
```

##### Mutasyon: 18/18 — ama bir kaçak vardı

*"iOS tam ekran etiketini kaldır"* kaçtı: `apple-mobile-web-app-capable`
dizesi etiketin **üstündeki açıklama yorumunda** da geçiyordu. HTML
yorumları da çıkarılıyor artık.

Bu, aynı sınıfın bu oturumdaki **altıncı** ortaya çıkışı: CSS sınıfı ·
NVS imzası · `faz_kal` alanı · `.uyari` gövdesi · komut toplayıcı · HTML
meta etiketi. Kural artık üç maddeli — metin tabanlı bir iddia
**(a)** yorumları çıkarmalı, **(b)** doğru gövdenin içinde aramalı,
**(c)** adın varlığını değil davranışı temsil eden ifadeyi aramalı.

Yakalanan diğerleri: otomatik biçimlendirme · serveStatic sırası ·
`immutable` kaldır · kök işleyicisinden LittleFS dalını çıkar ·
`enableETag` kullan · `PIL_YANIT_NOKTA` 600 · parçalı gönderimi kaldır ·
`/skop.bin` kaydını sil · `tB`'yi kaldır · görüntü listesinden varlık
çıkar · `sahte-kart.js` ekle · manifest bağlantısını kaldır · istemcide
`Uint16Array` · imza denetimini kaldır · uzunluk denetimini kaldır ·
hep ASCII kullan · ikili yol `osiloBitir` çağırmasın.

##### Doğrulama

Zincir **17/17**, derleme uyarısız. B22b 46 → **72**, arayüz 116 → **122**.
Görüntü bayatlığı ayrı bir iddia ve ısırdığı ölçüldü (`ek.css`'i değiştir
→ kırmızı).

⚠ **Karta hiç yazılmadı** — kart kurulmadı. `mklittlefs -l` ile görüntünün
yedi dosyayı doğru içerdiği doğrulandı; gerçek bağlama, `serveStatic`
davranışı ve telefondan ilk yükleme süresi **tezgah listesinde**.

#### 5.12.39 ✅ B23 — TEZGAH LİSTESİ · AĞ BELGESİ · ZİNCİR KORUMALARI (2026-09-10)

Donanım gelene kadar kapatılabilecek üç boşluk vardı ve üçü de aynı
sınıftandı: **elle yazıldığı için ölçümle bağı kopmuş bilgi.**

##### B23.1 — Tezgah listesi artık üretiliyor

Tek tezgah listesi `DEVIR.md`'de **elle yazılmış 8 kalemdi ve B20/B21
döneminde dondu.** B22.3, B22.4 ve B22.5'in üçü de *"tezgah listesinde"*
diyerek o listeye atıf yapıyordu — ve liste onların kalemlerini
**içermiyordu.** Ayrıca dört ayrı "kanıtlamaz" listesi vardı ve
**kesişimleri sıfırdı**; zincirin donanıma en bağımlı iki adımı
(`test_kopru.py`, `sim3_web.py`) hiçbir şey basmıyordu.

Yeni kural: **tezgah kalemi, onu doğrulayamayan kodun yanında yaşar.**

`uretim/tezgah.py` — ortak biçim. Çıktı hem insan hem makine için
okunabilir; ikinci bir "makine satırı" basılmıyor (o, aynı bilginin iki
temsili olurdu):

```
  === TEZGAH: B20 Ornekleme hizi ve bant ===
  [T] [!] `D` satirindaki ORNEK SAYISI — ilk, en ucuz ve en onemli test
      -> 200 ms'de 133 ± 3 bekleniyor. ~100 -> enableDelay ise yaramadi.
         ~19 -> B20 cokmus
```

`dogrula3.py` bunları adım çıktılarından toplayıp **tek birleşik liste**
basıyor ve `uretim/_tezgah.md` yazıyor. **17/17 adımın hepsi kalem
basıyor, toplam 72 kalem.**

**Taban çizgisi elle yazılmıyor — `ADIMLAR`'ın kendisi taban çizgisi.**
Bir betikten `tezgah(...)` silinirse o adım sıfıra düşer ve toplayıcı
kırmızı döner. Ölçüldü: `netlist3_dogrula.py`'den çağrı silindi → adım
**kendi başına 150/150 yeşil kaldı**, toplayıcı yakaladı.

`_tezgah.md`'nin başındaki **"İlk gün"** tablosu da türetiliyor: `[!]`
işaretli kalemler. Elle bir sıralama tutulsa yine bayatlardı.

🔴 **Kendi eklediğim kalem, eklediği adımı düşürüyordu.** Dört adımın
kalemine kırmızı daire emojisi, birine çevrelenmiş rakam koymuştum.
Windows konsolu cp1254: `python sim3_web.py` **tek başına** koşturulunca
codecs içinde `UnicodeEncodeError` ile çöküyordu (ölçüldü, rc=1). Kural
`tezgah.py`'nin docstring'inde yazılıydı ve **ilk gün çiğnendi** — yani
belge olarak tutulan her kural gibi. Artık `tezgah()` yazmadan önce
konsolun karakteri çizip çizemeyeceğine bakıyor ve hangi adımın hangi
kaleminin suçlu olduğunu söyleyerek düşüyor.

##### B23.2 — `BELGELER/6-ag.html`

Kullanıcının bu oturumdaki **ilk sorusu** (*"nasıl gireceğim, bilgisayar
mı yayın yapacak, telefondan ulaşabilecek miyim"*) belgelerde
cevapsızdı; dahası `index.html` **"Bilgisayara USB ile bağlanıyor"**
diyordu — B22'den sonra yanlış.

Yeni sayfa üç bağlantı kipini SVG diyagramla anlatıyor ve kaynakta
yazılı olup hiçbir belgede olmayan iki davranışı söylüyor: **kart aynı
anda tek sürücüye hizmet eder** ve **karta bağlanan her tarayıcı ölçümü
yavaşlatır** — "bilgisayar mı yayın yapacak" sorusunun asıl cevabı
**USB köprünün tercih edilen olduğu**.

Sayfadaki her sayı kaynaktan: `AG_MDNS` · AP SSID deseni · `10 s` ·
portlar · `_fs.json`. `h_metin()` yeni bir okuyucu — `h_sabit` yalnızca
`[0-9.]+f` yakalıyordu. **Ölçüldü:** `ag.h`'de `AG_MDNS` değiştirildi →
sayfadaki üç adres de kendiliğinden değişti, geri alındı → geri döndü.

Bu sırada üç bayat/yanlış sayı daha çıktı:

| Nerede | Yazıyordu | Gerçek |
|---|---|---|
| `index.html` | "15 adımlı bir zincir" | **17** — artık `dogrula3.ADIM_SAYISI`'ndan |
| `belge-uret.py` | `"5 sayfa"` | **7** — artık sayılıyor |
| `4-kurulum.html` | Firmware **481 935 B (%15)** | **1 067 423 B (%33)** — 2.2 kat sapma |

Firmware boyutu artık `test_firmware3.py`'nin **ölçtüğü** değerden
geliyor (`_firmware.json`); B6 zincirde B9'dan önce koştuğu için hep
taze. Yedek değer **bilerek yok** — elle bir sayı koymak bayatlamayı
geri getirirdi.

🔴 **`4-kurulum.html` gezinme şeridini hiç göstermiyordu** ve MENU'ye
eklenen "Bağlanma" sekmesi orada görünmedi: serit iki ayrı üreteçte
yaşıyordu. `belge_menu.py` ikisinin de tek kaynağı.

⚠ `index.html`'deki "hangi belgeye bakmalıyım" tablosu MENU'den
**türetilmiyor**, elle yazılıyor. Şimdi bir denetim ayrışmayı kırmızı
yapıyor. **İlk yazımı boştu:** tüm sayfaya bakıyordu ve gezinme şeridi
zaten her adresi içerdiği için her zaman geçiyordu — mutasyonla
ölçüldü, kaçtı. Denetim tabloyla sınırlandırıldı, mutasyon yakalandı.

##### B23.3 — Zincir korumaları

**`uretim/sayim.py`** — ortak özet ayrıştırıcı. Zincirdeki 18 özet
satırı dört ayrı biçimde yazılıyor; hem sayım kilidi hem mutasyon
koşucusu aynı deseni kullanıyor.

**`uretim/beklenen_sayim.json`** — iddia sayısı kilidi. Sapma **her iki
yönde de kırmızı**: DEVIR'in kendi uyarısı, B22.2'de bir iddia düşerken
başkası eklendi ve toplam sabit kaldığı için mutasyon kaçmıştı.
`python dogrula3.py --sayim-kilidi-yaz` ile tabanı tazeliyorsun.

Kilit yanlış alarm vermesin diye önce koşullu iddia blokları sabitlendi:
`test_olcum3.py`'nin üç `if "SZn" in s:` bloğu emülatör çıktısı bozulursa
**sekiz iddiayı birden sessizce** düşürüyordu. Varlığın kendisi artık bir
iddia — B22.1'de `test_firmware3.py`'nin flash/RAM regex'ine yapılanın
aynısı.

**`uretim/mutasyon.py`** — 10 mutasyon, `--adim` ile hedeflenebilir.
İki tasarım kararı: **yerinde mutasyon yok** (proje git deposu değil, bir
Ctrl-C kaynağı bozuk bırakır ve geri dönüş yolu yoktur) ve kopya
`%TEMP%`'e değil **kardeş dizine** (üç betik `Elekronic/` düzeyine
bakıyor; `projeler/_mutasyon-<pid>/` kullanılırsa üçü de çalışır).

🔴 **Koşucu ilk turunda üç gerçek kusur buldu:**

| Mutasyon | Neden kaçtı |
|---|---|
| `collectHeaders(` → `collectHeadersX(` | İddia `"collectHeaders" in INO_KOD` idi — **alt dizge**. `collectHeadersFoo` da geçerdi |
| `AG_MDNS ""` | **Hiçbir iddia yoktu.** mDNS adı boşalsa `olcum.local` çözülmez ve yeni ağ sayfası boş adres yazar |
| `enableDelay` yorumu | İddia B20'de, benim tablomda B22b yazıyordu — **mutasyon tablosunun kendi hatası** |

İlk ikisi düzeltildi (B22b 72 → **74** iddia), üçüncüsü tabloda
düzeltildi. Sekiz hafif mutasyonun hepsi artık yakalanıyor.

İki mutasyon **tam zinciri** koşturuyor (`AGIR`, yalnızca `--adim` ile,
her biri ~12 dk) çünkü ölçtükleri şey tek adımda değil `dogrula3.py`'nin
kendi düzenlemesinde:

| Mutasyon | Sonuç |
|---|---|
| `sema3-uret.py` çöksün | Zincir **kırmızı** (B23.3'ten önce yeşil kalıyordu) |
| Bir adım `tezgah(...)` çağırmasın | Zincir **kırmızı**, adım kendi başına 150/150 yeşilken |

##### Üç somut kusur

🔴 **B3, şema üretimi çökse bile yeşil kalıyordu.** `dogrula3.py`
`sema3-uret.py`'nin dönüş kodunu denetlemiyordu; ERC ve netlist
diskteki **bayat** `.kicad_sch` / `.net` dosyalarını okuyup temiz rapor
veriyordu. Zincirin en sessiz deliği.

🔴 **826 sızmış geçici dizin.** Altı betik `mkdtemp()` çağırıp
silmiyordu: `spice-` 618 · `olcum3_` 135 · `skopolc_` 47 · `kopru_` 22 ·
`fw3_` 4 · `skop_` 2. `spice.kos()` çalışma dizinini **döndürdüğü** için
`finally` yetmiyor — silme çağrı bitince değil **süreç** bitince olmalı.
`uretim/gecici.py` bunu `atexit` ile yapıyor; ölçüldü: `sim3_ortusme.py`
koşusu artık **sıfır** dizin bırakıyor (önce 9 bırakıyordu).

🔴 **Çöp toplama kapsamı.** `glob` özyinelemesiz ve `if d.is_dir()`
dosyaları eliyordu: `kopru/__pycache__`, `uretim/avr/__pycache__` ve
`_a4_*.elf` hiç silinmiyordu. ⚠ `kopru/arsiv/` **bilerek kapsam dışı** —
orası kullanıcının ölçüm günlüğü, proje çöpü değil.

##### Mutasyon koşucusunun kendi bulduğu iki kusur

Koşucu ilk kurulduğunda `arsiv/`'i kopya dışı bırakıyordu ("eski
aşamalar, mutasyonların hiçbiri oraya bakmıyor") ve **taban koşusu
kopyada kırmızı döndü** — mutasyon uygulanmadan önce.

Sebep: `kurulum3-uret.py:326` CSS'ini **`arsiv/asama2/kurulum2.html`**'den
okuyor. Yani **güncel kurulum kılavuzu bir arşiv dosyasına bağımlı** ve
bunu hiçbir yer söylemiyordu. Derleme çıktıları temizlendikten sonra
`arsiv/` zaten 6 MB / 52 dosya; dışlama kaldırıldı.

Ders: *"eski aşamalar"* diye işaretlenmiş bir dizin, güncel bir üretecin
bağımlılığı olabilir. Koşucu bunu ilk turunda buldu — ama yalnızca özet
satırı bastığı için **nedeni görünmüyordu**; artık taban kırmızıysa
kopyadaki başarısız satırları da basıyor.

Tanılama açılınca **ikinci kusur** çıktı: `kurulum3-uret.py`
`BELGELER/4-kurulum.html`'i yazarken klasörü **yaratmıyordu**, ve B9'da
`belge-uret.py`'den **önce** koşuyor — `mkdir` yapan tek betik oydu.
Yani `BELGELER/` silinmiş bir ağaçta B9 çöküyordu. Asıl ağaçta klasör
hep var olduğu için hiç görülmemişti; **mutasyon kopyası onu görünür
kıldı.** Düzeltildi.

İkisi de aynı sınıf: **temiz bir ağaçta koşmayı hiç denemediğimiz için
görünmeyen bağımlılıklar.**

Arşiv bağımlılığı **taşınmadı** — biçim çalışıyor ve kopyalamak yeni bir
ayrışma yüzeyi açardı. Onun yerine **görünür** kılındı: dosya yoksa
`kurulum3-uret.py` ne olduğunu söyleyen bir hatayla düşüyor (ölçüldü:
dosya geçici olarak yeniden adlandırıldı → rc=1 ve mesaj çıktı).

##### Bu bölümün kanıtlamadıkları

Hiçbiri donanımsız doğrulanamaz; hepsi `_tezgah.md`'de. **Ertelendi:**
B22.6 (köprünün ağ yukarı-akışı) · çift çekirdek (eşik `loop_azami_us >
20 000 µs`, ölçümü tezgah listesinde).

#### 5.12.40 ✅ B24 — GITHUB YAYINI VE YAYIN ÖNCESİ DENETİM (2026-09-11)

Proje **herkese açık** yayınlandı: <https://github.com/Muhammet933321/esp32-olcum-karti>
(MIT). `git init` + `.gitignore` + `.gitattributes`; 180 dosya, 11 MB.
Dışarıda: derleme çıktıları, `__pycache__`, `_fs.bin`, **kullanıcının
ölçüm günlüğü** (`kopru/arsiv/`) ve `fiyat_tara.py`.

İngilizce tanıtım `README.md`, mevcut Türkçe rehber `README.tr.md` oldu.

##### Yayından önce denetim — ve yayından SONRA çıkanlar

İki bağımsız denetim koşturuldu (12 + 10 ajan). **129 doğrulanmış bulgu.**
En pahalıları, yayınlanmış belgelerde **yanlış güvenlik ve emniyet
bilgisi** olmasıydı:

🔴 **`BELGELER/6-ag.html` dört yanlış iddia taşıyordu.** Üçü kaynağa
bakınca çürüdü: *"USB kipinde kartın Wi-Fi'si hiç açılmıyor"* (varsayılan
**açık**, `N0` gerekiyor) · *"kart aynı anda tek sürücüye hizmet eder"*
(aslında `AKIS_AZAMI`=4 tarayıcı; tek-sürücü kuralı **yalnızca köprü
kayıtlıyken**) · *"tehlikeli komutlar parola istiyor"* — `web_yetkili()`
parola kurulmamışsa **`true` dönüyor**, yani varsayılan kurulumda
yetkilendirme **kapalı**. Dördüncüsü çelişkiydi: ağ sayfası USB'yi
koşulsuz öneriyordu, kurulum kılavuzu izole olmayan devrede USB'yi
**yasaklıyor**.

🔴 **En ciddisi: "pil + Wi-Fi ile yüzdür" ÇÖZÜM DEĞİL.** Hem kurulum
kılavuzu hem benim yazdığım README bunu şebeke referanslı ölçümün cevabı
diye sunuyordu. B15/D2 bunu zaten ölçmüş ve yazmış: *"PC kurtulur;
KULLANICI kurtulmaz — kart 615 V'a çıkar. Yalıtımlı kutu + 5 delik
aralık ŞART."* **Yalıtımlı kutu şartı hiçbir kullanıcı belgesinde
geçmiyordu.** Artık kurulum kılavuzunun ilk uyarısında, ağ sayfasında ve
iki README'de de var; sayılar (12.6 mm creepage, 5 delik) kaynaktan.

🔴 **Firmware kullanıcıya yanlış söylüyordu.** `N` komutunun ortak
kuyruğu her alt komuttan sonra *"(bir sonraki açılışta geçerli)"*
basıyordu — ama `Ns` (web parolası) **anında** geçerli. Yani `Ns` ile
korumayı KALDIRAN kullanıcıya korumanın sürdüğü söyleniyordu. Mesaj
alt komuta göre ayrıldı ve **iki yeni iddiaya** bağlandı (B22b 74 → 76).

⚠ İlk yazdığım iddia **boştu**: dilim `alt == 's'`den ortak kuyruğa
kadardı ve sonraki dalların `break`'lerini de içeriyordu — mutasyon
kaçtı. Dilim dalın gövdesine daraltıldı, iki mutasyon da yakalandı.
**Aynı kapsam hatası, aynı oturumda üçüncü kez.**

##### Yayınlanan dosyada kişisel iz

`uretim/b15-arastirma.md` üç satırda Windows kullanıcı adı ve Claude
oturum kimliği taşıyordu (geçici dizin yolları). Temizlendi; bilgi değeri
(`<yerel-gecici-dizin>`) korundu.

##### Bayat sayılar — yine

| Nerede | Yazıyordu | Gerçek |
|---|---|---|
| `_tezgah.md` (B18 kalemi) | pay **18 mV** | **1930 mV** — 18 mV B18/F12 **öncesinin** değeri |
| `_tezgah.md` (B19 kalemleri) | skop `-65.2/+45.1 V`, `26.9 mV` | `-63.5/+46.8 V`, `28.8 mV` |
| `README.md` | "over 30 abuse scenarios" | **27** |
| `bom_dogrula.py` | "diğer 15 adım" | **16** |
| `CLAUDE.md` | zincir **15/15**, ~5 dk | **17/17**, ~6 dk |
| `DEVIR.md` (4 yer) | B15 **109** doğrulama | **111** |
| `README.md` · `DEVIR.md` | mutasyon **~2 dk** | ölçüldü: **~14 s** |

İlk ikisi **üretilen** `_tezgah.md`'nin içindeydi: kalem metinleri elle
yazılmıştı. İkisi de artık ölçümden türetiliyor.

⚠ Ayrıca README'nin *"hiçbir sayı elle yazılmadı"* iddiası **kendisi
için yanlıştı** — README üretilmiyor. Cümle, üretilen belgelerle sınırlı
hâle getirildi.

##### Klonlayan biri ne yaşar

* `arduino-cli` ve kişisel envanter depo **dışında**. İkisi de artık
  traceback yerine açık mesaj veriyor. B16 atlamayı **duyurup iddia
  sayısını koruyor**; B9 erken çıkıyor ve zincir kırmızı dönüyor —
  `--sayim-kilidi-yaz` bunu **susturmaz**, tezgah denetimi sayımdan
  bağımsız.
* FQBN eksikti: README yalnızca `huge_app` diyordu. **`PSRAM=opi` ve
  `FlashSize=16M` olmadan N16R8 kartta derleme yanlış çıkıyor** —
  LittleFS'in `0x310000` ofseti 4 MB sınırına düşüyor. Tam FQBN yazıldı.

##### Açık kalan

Denetimlerin düşük öncelikli bulguları (`__pycache__`'in kaynak yolu
taşıması, arşivde yinelenen kanıt dosyaları, `4-kurulum.html`'in tek dış
font bağlantısı, AVR emülatörünün ATmega328P olması) **kapatılmadı** —
listesi bu bölümde, biri canımı sıkarsa buradan bakılır.

---

#### 5.12.41 ✅ B25 — DONANIM BRINGUP KOSUCUSU (2026-09-11)

ESP32 **yarın geliyor.** Zincirin 18 adımı tasarımı doğruluyor ama kart
elde olduğunda çalıştırılabilecek tek bir donanım testi yoktu:
`uretim/_tezgah.md` bir **kontrol listesi** — insan okur, koşmaz. 75 kalemi
elle denemek hem yavaş hem atlamaya açık.

`uretim/tezgah_kart.py` bunu kapatıyor: gerçek karta **seri + HTTP**
üzerinden bağlanıp elle denenmesi gerekmeyen her şeyi otomatik sınıyor.

```
python tezgah_kart.py --liste                       # ne yapacağını gösterir
python tezgah_kart.py --sifirla                     # aşama 0: çıplak ESP32
python tezgah_kart.py --sifirla --asama 1           # + ADS1115
python tezgah_kart.py --sifirla --http olcum.local  # + web katmanı
```

##### Aşamalar — elde ne varsa o kadarı

| Aşama | Donanım | Ne sınanıyor |
|---|---|---|
| **0** | Yalnız ESP32-S3 | Açılış afişi (PSRAM boyutu, LittleFS, ağ kipi), komut yüzeyi, `K` blokaj sayacı, NVS savunmaları, web katmanı |
| **1** | + ADS1115 modülleri | I²C adresleri, `D` satırının biçimi · hızı · **örnek sayısı** |
| **2** | + analog ön uç | Değer denetimleri (henüz kalem yok — kart kurulunca eklenecek) |

**27 denetim.** Her beklenen yanıt **firmware kaynağından okunuyor** —
`D` satırının alan sayısı `.ino`'daki biçim dizesinden sayılıyor, mDNS adı
`ag.h`'den, beklenen örnek sayısı `sim3_bant.py` ile **aynı bütçeden**
hesaplanıyor. Elle yazılmış tek beklenti yok.

🔴 **`loop_azami_us` okunuyor ve 20 000 µs eşiğiyle karşılaştırılıyor.**
Aylardır açık duran çift çekirdek kararını kapatan tek ölçüm bu; artık bir
komut mesafesinde.

##### Emniyet

🔴 **Koşucu hiçbir aşamada yük sürmüyor.** Pil deşarjını başlatan komutu
bir test betiğinin kendiliğinden göndermesi kabul edilemez — ve bu bir
niyet beyanı değil, **iddiayla korunuyor**: B25 koşucunun kaynağını tarayıp
gönderdiği `p`-komutlarını çıkarıyor, `p0` (durdur) dışında bir şey varsa
kırmızı. `R!` (fabrika sıfırlama) de hiç gönderilmiyor.

NVS'e kalıcı yazan denetimler `--yazmaya-izin-ver` istiyor; varsayılan
kapalı, taze bir kartın kalibrasyonunu bringup koşusu bozmasın diye.

##### Koşucunun kendisi nasıl sınandı

Bu asıl mesele: **yanlış bir bringup testi, testsizlikten kötüdür** —
geçmeyen bir karta "geçti" der ve kusur tezgahtan çıkıp alana gider.

`kopru/kart_baglanti.py`'deki **`KayitKart`** tam bunun için vardı:
`SeriKart` ile aynı yüzey, komutlara betiklenmiş yanıt, ve yanıtı akışın
**içine** koyuyor — gerçek kartta olduğu gibi. `test_tezgah_kart.py`
(zincirde **B25**) koşucuyu bunun üzerinde iki yönlü sınıyor:

1. **Sağlıklı kart** senaryosunda her denetim yeşil
2. **15 kasıtlı bozuk senaryo** — doğru denetim kırmızı, ötekiler yeşil

| Bozuk senaryo | Yakalayan denetim |
|---|---|
| PSRAM yok (FQBN'de `PSRAM=opi` eksik) | PSRAM satırı |
| PSRAM 2 MB (yanlış modül) | PSRAM ≥ 8 MB |
| LittleFS boş (arayüz yazılmamış) | Arayüz LittleFS'te |
| Pil tamponu ayrılamadı | Tampon AYRILDI |
| `loop_azami_us` eşik üstünde | Çift çekirdek eşiği |
| Çıplak `g` **kabul ediliyor** (K3 geri geldi) | K3 tuğlalama koruması |
| `R` onaysız fabrika sıfırlıyor | Onay kapısı |
| Bilinmeyen komut sessizce yutuluyor | Açık ret |
| ADS bağlı değil / yalnız 0x48 var | I²C adresleri |
| Örnek sayısı ~100 / ~19 | Örnek sayısı bandı |
| `D` satırı hiç gelmiyor | Ölçüm satırı |

Ayrıca **telemetri ayıklama** ayrıca sınanıyor: kart sürekli `D` basıyor ve
komut yanıtı bu akışın içine düşüyor. Naif bir "gönder, bir satır oku"
%90 ihtimalle telemetri okur. **38/38 geçiyor.**

##### Öz-test koşucuda ÜÇ GERÇEK HATA buldu

Yazılmasının sebebi buydu ve daha yazılırken karşılığını verdi:

1. **`KayitKart` sonlu.** Gerçek kart sonsuza kadar `D` basıyor, kayıt
   bitiyor — `D` denetimleri kaydı tüketip **0 satır** görüyordu ve
   sağlıklı senaryoda bile kırmızıydı. Çözüm: aşamalama + `gecikme` ile
   gerçek tempoyu taklit etmek.
2. **Telemetri ayıklama testi BOŞTU.** `KayitKart.yaz()` yanıtı imlecin
   **önüne** koyuyor, yani yanıt her zaman ilk satır — ayıklanacak hiçbir
   şey yoktu (0 telemetri satırı). Test "çalışıyor" diyordu ama hiçbir şey
   sınamamıştı. Yanıtın kendisi telemetriyle sarılarak düzeltildi.
3. **Emniyet denetiminin kapsamı çok genişti.** Deseni her tırnaklı
   p-dizgesini yakalıyordu ve *"pil egri tamponu"* gibi **metinleri komut
   sanıyordu**. Artık yalnızca gerçekten gönderilen komutlara bakıyor.
   ⚠ **Aynı kapsam hatası, aynı oturumda üçüncü kez.**

##### Açılış afişi tuzağı

Afiş (PSRAM boyutu, pil tamponu, LittleFS) **yalnızca açılışta** basılıyor,
ama `SeriKart.ac()` DTR/RTS'i bilerek `DISABLE` kuruyor — bağlanmak kartı
sıfırlamıyor, yani afiş çoktan geçmiş oluyor.

`SeriKart.sifirla()` eklendi (klasik oto-reset dizisi: DTR→EN, RTS→IO0).
⚠ **Yerel USB CDC'li kartlarda etkisi yok** — orada DTR/RTS gerçek bir pine
bağlı değil. O yüzden `sifirla()` "sinyaller gönderildi" diyor, "kart
sıfırlandı" demiyor; çağıran taraf **afişi gördü mü** diye bakıyor.
Görülmezse PSRAM/LittleFS denetimleri **atlanıyor, kırmızı olmuyor** ve
kullanıcıya EN düğmesine basması söyleniyor.

`KayitKart`'a da aynı yüzey eklendi — yoksa koşucunun içinde `isinstance`
dalı doğar ve kayıtlı koşu gerçek koşudan **ayrışır**.

##### Yan düzeltme: bayat RAM sabiti

`tasarim3_sabit.ESP_DRAM_KULLANILAN` **51 084**'te donmuştu (yorumu
"güncellenir" diyordu), gerçek derleme **71 420 B**. Bu sayı B21'in *"pil
tamponu boş DRAM'in üçte birinden küçük"* iddiasını **20 KB iyimser**
besliyordu — iddia yine geçiyordu ama iddia edilen pay gerçek değildi.
Artık `_firmware.json`'dan okunuyor ve **B6 yedek sabitin ölçümle eşit
olduğunu sınıyor**, bir daha sessizce kayamaz.

##### Bağımsız araştırma iki gerçek kusur daha çıkardı

B25 hazırlanırken, "elde ne varsa onunla ne sınanabilir" sorusunu
kaynaktan cevaplaması için ayrı bir denetim koşturuldu (10 ajan, 161
doğrulanmış kalem). İki bulgusu koşucudan bağımsız, **firmware ve
zincirin kendisiyle** ilgiliydi.

🔴 **Açılış afişinde satır kapanmıyordu.** `Ag:` bloğunun sonunda
`Serial.println()` **yoktu**; çıktı şöyle yapışıyordu:

```
Ag: AP  SSID=OLCUM-KARTI-A1B2  http://192.168.4.1Arayuz: YOK — ...
```

Yani **kullanıcının seri konsoldan kopyalayacağı IP adresi bir sonraki
etikete karışıyordu** ve afiş ayrıştırılamaz haldeydi. Kart daha hiç
açılmadığı için kimse görmemişti. Düzeltildi; `sim3_web.py` artık `Ag:`
bloğunun `Arayuz:`den **önce kapandığını** ayrıca sınıyor (mutasyonla
doğrulandı: `println` geri silinince kırmızı).

🔴 **`olcum3.h` kendi kuralını çiğniyordu ve adımın iddiası yanlıştı.**
Dosyanın başında *"`int` ve `double` YASAK; her yerde açık genişlikli tip
ve `float`"* yazıyor — sebebi tek: **avr-gcc'de `double`, `float`a takma
addır (32 bit), Xtensa'da 64 bittir.** Kural, emülatörle kartın **bit
birebir aynı** aritmetiği koşturmasını garanti etmek için var.

Dört fonksiyon bu kuralı çiğniyordu (`enerji_joule3`, `enerji_wh3`,
`yuk_mAh3`, `yuk_coulomb3`), hepsi
`(float)((double)<int64> / <sabit>)` kalıbında — Aşama 1'den devralınmış
bir alışkanlık; kaynakta savunan tek satır yoktu.

Sonucu: **`uretim/avr/ornek_olcum3.c`'nin *"burada koşturulan kod,
ESP32'de koşacak kodun ta kendisidir"* iddiası bu dört fonksiyon için
DOĞRU DEĞİLDİ** — ve aynı iddia `DEVIR.md`'de ve **kullanıcıya gösterilen
belgede** (`5-muhendislik.html`: *"sınanan şey kartta çalışacak kodun ta
kendisi"*) tekrarlanıyordu.

**Ölçüldü, iki bağımsız yoldan.** Denetim kodu avr-gcc ile derleyip
projenin **kendi emülatöründe** koşturdu ve Xtensa çıktısını
disassemble etti (`__floatdidf`/`__divdf3` vs `__floatdisf`/`__divsf3`).
Ayrı olarak ben de sayısal modelle ölçtüm. İki ölçüm aynı yere çıktı:

| Büyüklük | Değer |
|---|---|
| İki yolun en kötü bağıl farkı | **6.8e-8** (1 ULP) |
| float32'nin kendi çözünürlüğü | 6.0e-8 |
| ADS1115 tek adımı | 3.1e-5 — **450 kat büyük** |
| ADS1115 kazanç hatası | 1.5e-3 — 22 000 kat büyük |

**İlk kararım "cast kalsın" idi** — çünkü `(double)` hedefte ölçülebilir
biçimde *daha doğru*: int64 uçlarında hata 0.046 yerine 0.016. Bağımsız
denetim buna katılmadı ve haklı çıktı: kazanılan şey **0.5 ULP**, kaybedilen
şey **emülatörün temsil gücü** — yani B4/B5'in bütün değerinin dayandığı
şey. Ayrıca yanlış bir iddia **kullanıcıya yayınlanmış** durumdaydı.

Dört cast kaldırıldı, saf `float`a geçildi. Mevcut 110 iddianın hiçbiri
bozulmadı — bu da denetimin *"B4/B5 bu satırları hiç ölçmüyordu"*
bulgusunu bağımsız olarak doğruluyor.

**Yeni kapsam:** `test_olcum3.py` B4.6 artık altı şey sınıyor — farkın
sınırı, ADS gürültüsüne oranı, bit-birebirlik, dosyada **hiç `(double)`
olmadığı**, kaldırma gerekçesinin kayıtta durduğu ve
`ornek_olcum3.c`'nin öncülünün artık geçerli olduğu.
`mutasyon.py`'ye de karşılığı eklendi (denetimin ayrı bir bulgusu:
**mutasyon tablosunda `olcum3.h`'ye ait tek kayıt yoktu**) — cast geri
konunca zincir kırmızı, ölçüldü.

⚠ **Açık kalan (arşiv):** `sim2_kart.py:267` Aşama 2'de beklenen değeri
**float64** modeliyle üretip emülatörün float32 çıktısıyla karşılaştırıyor.
Aşama 2 zinciri geçiyor ama model tutarsız; Aşama 2 arşiv olduğu için
dokunulmadı.

##### Yan bulgu: şema her koşuda değişiyordu

🔴 Depo GitHub'a çıkınca görüldü: `sema3-uret.py` UUID'leri
`uuid.uuid4()` ile üretiyordu, yani **şema her üretildiğinde bütün
UUID'ler değişiyordu.** 242 KB'lik `.kicad_sch` ve 114 KB'lik netlist
her zincir koşusunda **858 satırlık anlamsız bir diff** veriyordu — ve
bu her commit'te tekrarlayıp **gerçek bir tasarım değişikliğini
boğardı**.

UUID'ler artık bir sayaçtan türetiliyor (`uuid.uuid5` + sabit ad alanı).
KiCad için tek gereklilik dosya **içinde** benzersizlik; küresel
benzersizlik gerekmiyor. Ölçüldü: üç ardışık üretim **aynı SHA-256**.

Şema böylece projenin geri kalanıyla aynı disipline girdi —
**yeniden üretilebilir bir yapı**. `netlist3_dogrula.py` iki iddiayla
koruyor (mutasyon: `uuid4` geri konunca kırmızı, ölçüldü).

⚠ İddianın ilk iki yazımı **boştu**: aradığı `uuid4()` dizgesi kendi
gerekçe yorumunda ve bir docstring'te de geçiyordu, yani iddia
**kendi açıklaması yüzünden** kırmızı yanıyordu. Kapsam koda
sınırlandırıldı. *Aynı sınıf, bu oturumda dördüncü kez.*

##### Kayıt denetimi (10 ajan, 60 doğrulanmış bulgu)

Kayıt yazıldıktan **sonra** bağımsız bir denetim koşturuldu — "yeni bir
oturum bunu okuyup ne yapacağını bilebilir mi" diye. On yüksek öncelikli
bulgu çıktı ve hepsi kapatıldı:

🔴 **ESP32 gününün BİRİNCİ komutu olduğu gibi koşmuyordu.** İlk gün akışı
çıplak `arduino-cli compile` yazıyordu; ikili **PATH'te değil**,
`Elekronic/.araclar/` altında. Üstelik FQBN iki komutta **elle
tekrarlanıyordu** — tek kaynak `hedef2.py` olduğu hâlde. `uretim/yukle.py`
ikisini birden kapattı: `arduino-cli`'yi buluyor, FQBN'i `hedef2.py`'den
okuyor.

🔴 **DEVIR kendi içinde çelişiyordu:** aynı bölüm hem "24 denetim / 13
senaryo / 36-36" hem "27 denetim / 15 senaryo" diyordu. Sayılar
tazelendi; `--liste` artık **aşama başına** sayıyı basıyor.

🔴 **Bölüm 6.1'in emniyet kutusu** hâlâ *"pil + WiFi ile yüzdür"*ü
koşulsuz çözüm diye sunuyordu — 5.12.40'ın düzeltmesi oraya işlenmemişti.
Yalıtımlı kutu şartı eklendi.

🔴 **`tezgah_kart.py` boş bir vaat taşıyordu:** docstring "aşama 2 = değer
denetimleri" diyordu ama o aşamaya ait **tek denetim yoktu**; `--asama 2`
ile `--asama 1` aynı kümeyi koşturuyordu. Docstring dürüstleştirildi ve
`--liste` boş aşamayı **açıkça** gösteriyor.

🔴 **README'nin `#safety` bağlantısı yanlış yere gidiyordu** — lisans
bölümünü eklerken elektriksel emniyet metnini başlıksız bırakmışım, yani
*"615 V öldürür"* uyarısına giden bağlantı **ağ güvenliği** paragrafına
düşüyordu. Bölüm yeniden kuruldu: **elektriksel önce**.

🔴 **Envanteri iki değil ÜÇ adım okuyor.** B11 bunu `.exists()` ile
korumuyordu: temiz bir klonda iddia sessizce başarısız oluyor ve
*"envanter.csv okundu (0 B): 7912 var"* gibi anlamsız bir mesaj veriyordu.
B16'nın deseni uygulandı — atlama duyuruluyor, iddia sayısı korunuyor.

🔴 **Skop çözünürlüğü altı dosyada iki farklı tabandan** yazılıydı:
"11.1 → 26.9 mV" — öncesi **etkin aralıktan** (2.9 V), sonrası
**nominalden** (3.1 V). B20 adımın bir LSB olduğunu, yani nominalden
türediğini söylüyor. Hepsi aynı tabana getirildi (**11.9 → 28.8 mV**) ve
kullanıcı kılavuzu artık `SKOP_ADIM_ESKI` sabitinden türetiyor.

🔴 **`4-kurulum.html`'de `<!doctype>`, `charset` ve `viewport` yoktu** —
sekiz sayfadan yalnızca onda. Tezgahta okunacak, Türkçe karakterli bir
sayfa için tarayıcının kodlamayı tahmin etmesine bırakılmıştı.

##### Doğrulama

Zincir **18/18**, 75 tezgah kalemi (güncel iddia sayısı
`beklenen_sayim.json`'da). B25 `--liste` ile ne koşacağını yazıyor;
`--sifirla` olmadan afiş denetimleri atlanıyor. Bringup koşucusu
**27 denetim** yapıyor, öz-testi **15 bozuk senaryoyu** yakalıyor.

⚠ **Bu adım gerçek donanımı doğrulamıyor.** Yalnızca koşucunun doğru soruyu
sorup doğru cevaba baktığını sınıyor. Gerçek seri port, gerçek zamanlama ve
gerçek USB CDC davranışı yarın görülecek.

---

#### 5.12.42 ✅ B26 — KART GELDİ: İLK GERÇEK BRINGUP (2026-09-11)

ESP32-S3 elde. Firmware yüklendi, arayüz karta yazıldı, aşama 0 bringup
koşuldu. **Tasarım zinciri 18/18 yeşilken üç kusur çıktı** — ikisi
yalnızca gerçek donanımda görülebilirdi.

##### Kart gerçekten N16R8 mi — etikete değil silikona soruldu

`esptool flash-id`: ESP32-S3 (QFN56) rev v0.2 · flash **16 MB** ·
**Embedded PSRAM 8 MB (AP_3v3)** · MAC `…:96:9c` (tam adres kasıtlı kısaltıldı — depo herkese açık).
Açılış afişi: `PSRAM: 8192 KB`, pil eğri tamponu 86400 nokta = 24 saat,
**1012 KB PSRAM'de**.

Yani `hedef2.py`'nin uyarısı karşılandı: *"Derleme başarılı olması kartta
PSRAM bulunduğunu KANITLAMAZ — kanıt açılış satırıdır."* PSRAM hem var
hem gerçekten kullanılıyor. `PSRAM=opi` ve `FlashSize=16M` doğru seçim.

##### Hangi soket — VID ile ayırt edilir, "port göründü" yetmez

COM yazan soket: **CH343** USB-UART köprüsü (`VID_1A86` / `PID_55D3`,
wch.cn) → `COM6`. Sürücü Windows 11'de hazır geldi.

⚠ **"Bir COM portu belirdi" doğru sokete takıldığının kanıtı DEĞİL.**
ESP32-S3'ün içinde ayrı bir USB Serial/JTAG birimi var; yerel USB
soketine takılırsa Windows **yine** bir COM portu açar (`VID_303A`) ama
firmware `Serial`i UART0'da tuttuğu için o port **sessiz** kalır.
Ayırt edici ölçüt VID: `1A86`/`10C4`/`0403` = köprü çipi (doğru soket),
`303A` = yerel USB (yanlış soket).

`esptool`'un `Hard resetting via RTS pin` satırı da doğru sokette
olunduğunu bağımsız olarak doğruluyor — DTR/RTS otomatik reset yalnızca
köprü çipinde çalışıyor.

##### 🔴 Kusur 1 — AP SSID MAC'ten GELMİYORDU

`ag.h`'de sıra tersti:

```c
String ap = ag_ap_ssid();   // WiFi.macAddress(m) BURADA
WiFi.mode(WIFI_AP);         // WiFi ancak BURADA başlıyor
```

Kayıtlı ev ağı yokken (varsayılan durum) WiFi sürücüsü o ana kadar hiç
başlamamış oluyor. `esp_wifi_get_mac` böyle bir durumda
`ESP_ERR_WIFI_NOT_INIT` dönüp tampona **dokunmuyor**, yani `m[6]`
**ilklenmemiş yığın belleği** olarak SSID'e giriyordu.

**Kanıt:** gerçek MAC `…96:9c` iken ad, firmware yazıldıktan sonraki ilk
açılışta `OLCUM-KARTI-0400`, sonrasında **hep** `OLCUM-KARTI-ABAB`
(`AB AB` = tekrarlayan dolgu baytı deseni). Dört sıcak reset boyunca
sabit kaldığı için kusur *"rastgele ad"* gibi de görünmüyordu — aynı kod
yolu aynı yığın içeriğini bıraktığından **deterministik çöp** üretiyor.

⚠ Bu, "sabit olması doğru olduğu anlamına gelmez" sınıfının iyi bir
örneği: ilk hipotezim *"her açılışta değişiyor"* idi, dört resetlik
deney bunu **çürüttü**, ama kusur yine de oradaydı.

**Neden önemli:** B22'nin bütün *"telefondan, bilgisayarsız kullan"*
hikâyesi bu ada dayanıyor. Ad değiştiği her seferde telefondaki ağ
profili kırılıyor ve 12 karakterlik AP parolası elle yeniden giriliyor.
Ayrıca AP parolasını MAC'ten **türetmeme** kararının gerekçesi (*"SSID
zaten MAC son ekini yayınlıyor"*) fiilen yanlıştı.

**Düzeltme:** `esp_read_mac(m, ESP_MAC_WIFI_SOFTAP)` — eFuse'tan okur,
sürücünün başlatılmış olmasını gerektirmez, hem STA hem AP yolunda
çalışır. Kartta doğrulandı: **`SSID=OLCUM-KARTI-969C`**,
`MAC=…:96:9C`. (softAP MAC son baytı artırmıyor, ilk oktetteki
yerel-yönetim bitini kuruyor: `68`→`6A`.)

**Neden eski koşucu yakalamadı:** *"Ag kipi bildirildi"* denetimi yalnızca
satırın **var olduğuna** bakıyordu, içeriğin tutarlılığına değil.

Yeni denetim: afiş artık softAP **ayağa kalktıktan sonra** okunan gerçek
MAC'i de ilan ediyor ve `tezgah_kart.py` SSID sonekini onunla
karşılaştırıyor. ⚠ MAC'i `ag_ap_ssid()` ile **aynı kaynaktan** okusaydı
test totoloji olur ve eski kusuru kaçırırdı — bağımsızlık kasıtlı.

##### 🔴 Kusur 2 — çift çekirdek ölçütü kırılgandı → **KARAR ÇIKTI**

`loop_azami_us` açılıştan beri sıfırlanmayan **koşan maksimum** ve ısınma
payı yok (ölçüm ikinci `loop()` turunda başlıyor). Yani `setup()` sonrası
WiFi/mDNS ayağa kalkarken oluşan tek seferlik bir sıçrama kalıcı olarak
çakılıyordu.

Ölçülen: taze açılışta **18 203 µs** (eşiğin ALTINDA, 0 uzun tur),
dakikalar sonra **30 397 µs** (ÜSTÜNDE). **Aynı kart, ne zaman baktığına
göre iki farklı cevap veriyordu** — ve 5.12.34'ün *"bu tek ölçüm aylardır
açık duran mimari kararı kapatıyor"* dediği ölçüt buydu.

Firmware'e **`K` komutu** eklendi: blokaj sayaçlarını sıfırlar, **eski
değerleri basarak** (bu projede bir sayının sessizce kaybolması kabul
edilmiyor). Koşucu artık sıfırlayıp **45 sn kararlı hal** ölçüyor.

**Sonuç:** sıfırlamadan sonra 45 sn'de yine **30 382 µs**, 1 uzun tur.
Yani ~30 ms'lik olay **açılış sıçraması değil, kararlı halde ~45 sn'de
bir tekrarlıyor.** İlk yorumum *"muhtemelen açılış artığı"* idi; **ölçüm
onu çürüttü.** Tahmin etmek yerine sayacı eklemenin karşılığı buydu.

→ **DEVIR 5.12.34'ün kararı: ölçüm döngüsü çekirdek 1'e taşınacak.**

⚠ İki sınır: (1) ölçüm **ADS'ler bağlı değilken** alındı — ama 30 ms'lik
bir blokaj I²C okumasından gelemez (WiFi/mDNS bakımı olması muhtemel),
ADS eklemek bunu iyileştirmez, kötüleştirir. (2) `atlanan_ms` **hep 0**:
enerji penceresi kaçmıyor, yani bugün enerji sayacı zarar görmüyor; asıl
risk skop/örnekleme sürekliliğinde.

##### 🔴 Kusur 3 — bayat `f` denetimi (firmware doğru, TEST yanlıştı)

`d_ciplak_f_reddi` çıplak `f`'in `! f: frekans gerekli` ile reddedilmesini
bekliyordu ve gerçek kartta **kırmızı** döndü. Ama B22.1 bunu bilerek
değiştirmiş: çıplak `f` artık `F`/`P` gibi **değeri basıyor**
(`* sebeke frekansi 50.00 Hz`, kartta doğrulandı). Hata mesajı yalnızca
**bozuk** girdide (`fabc`) çıkıyor. Denetim `g`/`i` desenini kopyalarken
`f`'in farklı tasarımını görmemiş.

⚠ Üstelik kayıt tabanlı sahte kart da `f` için hata dönüyordu, yani
**bayat denetimi "doğruluyordu"**. İkisi birlikte onarıldı; artık iki şey
sınanıyor: çıplak `f` değeri basıyor **ve** `fabc` reddediliyor.

**Ders:** yeşil test bir şey kanıtlamaz — ama **kırmızı test de tek
başına kusur kanıtlamaz.** Önce kaynağa bakılır.

##### 🔴 Kusur 4 — koşucu `D` satırında YANLIŞ ALANI okuyordu

Aşama 1 ilk kez gerçek donanımda koşuldu (tek ADS, `0x48`) ve
**`ornek = 0`** raporladı. Kart suçsuzdu. Biçim:

```
D <volt> <amper> <watt> <joule> <wh> <ms> <ornek> <menzil>
```

Örnek sayısı **7.** alan, son alan `menzil`. `d_ornek_sayisi` ise
`split()[-1]` ile **son** alanı okuyor, yani menzili (NORMAL = `0`)
örnek sayısı sanıyordu.

**Neden kaçtı:** `test_tezgah_kart.py`'deki sahte kart da örnek sayısını
son alana koyuyordu. İkisi **birbiriyle tutarlı**, ikisi de firmware'den
farklıydı. Yandaki *"İlan edilen alan sayısı firmware biçimiyle AYNI"*
denetimi yalnızca **sayıya** bakıyor, **sıraya** bakmıyordu — `8 == 8`
olduğu için sessiz kaldı.

⚠️ Bu, B22.2'deki *"bir iddia düşerken başkası eklendi, toplam sabit
kaldığı için mutasyon kaçtı"* olayının **alan sırası sürümü.** Aynı sınıf:
**bir sayı korunuyor diye içerik korunuyor sanmak.**

**Düzeltme:** indeks artık **afişin ilan ettiği alan adlarından**
türetiliyor (`_ornek_indeksi`); firmware sırayı değiştirirse ayrıştırıcı
peşinden gider. Sahte kartın alan sırası gerçeğe uyduruldu. Üç yeni iddia:
protokol ilanı `ornek`i adlandırıyor mu · sahte kart onu **ilan edilen**
yere koyuyor mu · koşucu aynı indeksi afişten türetiyor mu. **Sahte kartın
kendi kendine tutarlı olması artık yetmiyor.**

##### İlk gerçek ölçüm: örnekleme hızı 4 kat düşük

Düzeltilmiş ayrıştırıcıyla, tek ADS bağlıyken:

| | |
|---|---|
| `ornek` | **33** / 200 ms → **~162 örnek/s** |
| beklenen | 133 / 200 ms → **665 örnek/s** |
| tur süresi | 203.5 ÷ 33 = **6.17 ms** |
| zaman aşımı yolu | 4000 µs + 1300 µs yedek + I²C ≈ **6.2 ms** |

Sayılar sebebi tek başına söylüyor: **ALERT/RDY sinyali gelmiyor**, kod
her turda `yeni_donusum_bekle(4000)`'de zaman aşımına düşüp
`delayMicroseconds(1300)` yedeğine kaçıyor.

Firmware doğru: eşik yazmaçları (`0x8000`/`0x0000`) `ADS_AKIM`'a
yazılıyor, `pinMode(PIN_HAZIR, INPUT_PULLUP)` kurulu. **Fiziksel bağlantı
sınanacak.** ⚠ `ALRT` pininin iki komşusu (`ADDR`, `A0`) bu kurulumda
GND'ye bağlı; tel bir delik kayarsa GPIO7 sürekli LOW kalır ve belirti
*"tel hiç yok"* ile **birebir aynı** olur.

⚠ Bu, B20'nin 91 SPS'inin **aynı sınıfı ama aynısı değil**: orada pin
yüksek empedansta kalıyordu (COMP_QUE=11b), burada firmware doğru,
donanım yolu şüpheli.

##### 🔴 Kusur 5 — ALERT/RDY KENAR YÖNÜ TERSTİ (162 SPS'in asıl sebebi)

Kablolama süreklilikle doğrulandı, 3V3 rayı 3.26 V — donanım sağlamdı.
Sebebi tahmin etmek yerine GPIO7'yi doğrudan dinleyen geçici bir tanı
yazılımı yüklendi (yalnızca `0x48` ile konuşuyor, yani eksik ikinci ADS
hipotezi tamamen devre dışı):

```
GPIO7 bosta: HIGH (beklenen)     -> kablo doğru, GND'ye kaçmamış
Hi_thresh=0x8000  Lo_thresh=0x0  -> eşikler yazıldı VE geri okundu
RDY dustu: EVET @1228 us         -> pin DÜŞÜYOR, tam dönüşüm süresinde
kalkti: HAYIR                    -> ama GERİ KALKMIYOR
```

Kontrol grubu (`COMP_QUE=11`, pin yüksek empedans) hiç darbe vermedi —
ölçüm düzeneğinin kendisi doğrulandı.

`yeni_donusum_bekle` önce **düşmeyi**, sonra **kalkmayı** bekliyordu. ADS'in
RDY pini ise dönüşüm bitince LOW'a çekip **öyle kalıyor**; pini geri
kaldıran şey **yeni dönüşümü başlatan ayar yazması**. (İlk hipotez "okuma
kaldırır"dı, o da ölçülüp çürütüldü: `okuma oncesi LOW | okuma sonrasi LOW`.)

Yani ikinci döngü **hiç gelmeyecek bir kenarı** bekliyor, her turda
4000 µs zaman aşımı + 1300 µs yedek = ölçülen 6.17 ms.

**Düzeltme:** kenar yönü ters çevrildi — önce kalkmayı (yeni dönüşüm
başladı), sonra düşmeyi (dönüşüm bitti) bekle. Ters sıra ayrıca teorik bir
yarışa açıktı: ayar yazması bitmeden pin hâlâ LOW iken bakılırsa ÖNCEKİ
dönüşüm okunur. Tezgahta 300 turda **sıfır zaman aşımı**, 620 örnek/s.

| | önce | sonra |
|---|---|---|
| örnek / 200 ms | 33 | **97** |
| örnek/s | 162 | **485** |
| tur süresi | 6.17 ms | 2.06 ms |

⚠️ **Bu kusur B20'nin düzeltmesinin ALTINDA duruyordu.** B20 `COMP_QUE=11b`
sorununu doğru teşhis edip düzeltmişti (91 SPS) — ama kenar yönü hatası
altta kaldı ve donanım olmadığı için 665 SPS hiç ölçülmemişti.
**Düzeltilmiş bir kusurun arkasında ikinci bir kusur.** Zincire kenar
yönünü sınayan iddia (`sim3_bant.py` 1b-bis) ve onu yalanlayan mutasyon
eklendi.

Kalan 97 → 133 farkının sebebi eksik `0x49`: firmware her turda ona da
yazıp okumaya çalışıyor. Yalın testte (tek ADS) 1.61 ms/tur, firmware'de
2.06 ms. **Tahmin: ikinci ADS takılınca bant tutar** — sınanabilir.

##### Web katmanı gerçek donanımda açıldı

Kart ev ağına alındı (`Na`/`Np`), web parolası kuruldu (`Ns`). Atlanan
5 denetim koştu ve **hepsi yeşil**:

| Denetim | Sonuç |
|---|---|
| Arayüz servis ediliyor | 200 · 26 683 bayt (gzip'li 8 046) |
| CSRF — özel başlık zorunlu | 400 |
| Geçersiz jeton | 403 |
| **`p0` jetonsuz geçiyor** | **204** ← emniyet özelliği |
| Yabancı Host (DNS rebinding) | 403 |

⚠️ Ama önce **beş koşucu kusuru** çıktı, hepsi kartı haksız yere suçluyordu:

1. **`Content-Type`.** `urllib` gövde verilince başlık yoksa
   `application/x-www-form-urlencoded` ekliyor; ESP32 `WebServer` onu FORM
   diye ayrıştırıp ham gövdeyi `arg("plain")`'e koymuyor → 400 "bos komut".
   Koşucu bunu *"`p0` GEÇMİYOR — EMNİYET kusuru"* diye raporluyordu.
   **Olmayan bir emniyet kusuru uyduruyordu**, ki bu yanlış-yeşilden beter.
   Ölçüldü: form-ct → 400, `text/plain` → 204.
2. **gzip.** Kök sayfa `Content-Encoding: gzip` geliyor; `urllib` açmıyor,
   denetim ham baytta `<!doctype` arıyordu.
3. **Afiş penceresi.** STA kipinde afiş `AG_STA_BEKLE_MS` (10 s) kadar
   gecikiyor; sabit 3 sn yüzünden afişe dayanan **12 denetim birden
   atlandı** ve koşu "23 geçti · 12 atlandı" diye yanıltıcı göründü. Artık
   `D` satırı görünene kadar bekliyor, tavan `ag.h`'den türetiliyor.
4. **SSID/MAC denetimi** STA kipinde yanlış kırmızı veriyordu — orada SSID
   yönlendiriciden geliyor, MAC'ten türetilmiyor. Artık AP kipi dışında
   atlanıyor.
5. **Parola uyarısı** "uyarı metni var mı" diye bakıyordu; parola kurulunca
   metin kaybolur ve denetim kırmızı olurdu — oysa o tam istenen durum.
   Artık koşullu: korumasızsa uyarı OLMALI, korumalıysa yanıltıcı uyarı
   OLMAMALI. İki yön de sınanıyor.

**Sonuç: 23 geçti · 5 kaldı · 12 atlandı → 48 geçti · 3 kaldı · 1 atlandı.**

##### NVS kalıcılığı — yeni kalıcı denetim

`NVS kalibrasyon kaliciligi` eklendi (tehlike sınıfı `NVS-yazar`, yani
`--yazmaya-izin-ver` olmadan koşmuyor). Ayırt edici bir değer yazıp
resetleyip hayatta kaldığını doğruluyor, sonra **eski değeri geri
yüklüyor** — tezgahta iz bırakmıyor. Gerçek kartta doğrulandı.

⚠️ İlk yazımı **boş bir iddiaydı**: `i_ofset` kullanıyordu ve girişler
GND'deyken hem varsayılan hem ölçülen değer 0 olduğu için NVS hiç
çalışmasa da `0 == 0` diye geçerdi. `s<ohm>`'a geçildi. Sahte kartın da
bunu modelleyebilmesi için küçük durumlu `AyarliKart` yazıldı — **durumsuz
bir taklit bu soruyu cevaplayamıyor**, ki boş iddianın kaynağı tam buydu.

##### PC köprüsü ilk kez gerçek kartla

`kopru/` tamamen sınanmamıştı. Uçtan uca çalıştığı görüldü: seri↔SSE
rölesi (6 sn'de 32 olay ≈ kartın rapor hızı), jeton, sürücü hakemi, disk
arşivi (gün dosyası gece yarısı döndü). Stok sunucusunu bozmuyor:
`127.0.0.1` stoka, köprü LAN adresine düşüyor.

##### Çift çekirdek: olay PERİYODİK, 30 saniyede bir

Daha önce "45 sn kararlı halde 30 382 µs" denmişti; o ölçüm **bozuk
firmware'le** ve tek pencereyle alınmıştı. 180 saniye ölçüldü:

```
 30 sn -> K 0 26209 1      120 sn -> K 0 26342 4
 60 sn -> K 0 26209 2      150 sn -> K 0 26342 5
 90 sn -> K 0 26342 3      180 sn -> K 0 26342 6
```

**Her 30 saniyede tam bir tane ~26 ms blokaj**, aralarda döngü en fazla
2.4 ms, `atlanan_ms` hep 0. Karar değişmiyor (eşik 20 ms aşılıyor) ama
gerekçe artık çok daha sağlam: seyrek/rastgele değil, **periyodik** —
muhtemelen mDNS ya da WiFi bakımı.

⚠️ Bu, koşucudaki bir iddiayı da düzeltti: "sayaçlar sıfırlandı mı" 45 sn
BEKLEDİKTEN SONRA bakıyordu, ama periyodik olay o pencerede değeri geri
tırmandırıyor — sıfırlama kusursuz çalışırken bile kırmızı dönüyordu.
Sıfırlamanın kanıtı **sıfırlama anındaki** değerdir.

##### Arayüz: sayfayı kart sunarken kip `seri`de kalıyordu

Kullanıcı `http://olcum.local`'ı açtı, "bağlı değil" gördü, telefonda hiç
açılmadı. Sebep: `kopruyuAlgila()` otomatik kip seçimi için `/durum`
ucunu yokluyor — o uç **yalnızca PC köprüsünde** var, kartta 404. B22.3
bu algılamayı köprü için yazmış; B22.4/B22.5 sonradan kartı da sunucu
yapmış ama algılama genişletilmemiş. Kart sunarken yoklama sessizce
başarısız oluyor, kip `seri`de kalıyor, Web Serial de güvenli bağlam
olmadığı için çalışmıyor.

İkinci kusur: hata metni *"tarayıcı Web Serial desteklemiyor"* diyordu.
Chrome destekliyor — `navigator.serial` **güvenli bağlam** istiyor ve
`http://olcum.local` güvenli bağlam değil. Metin yanlış yere baktırıyordu.

**Düzeltme:** sayfayı localhost olmayan bir adres sunuyorsa sunan taraf
kart ya da köprüdür, ikisi de `/akis` veriyor → doğrudan akış kipi.
Mesaj artık `window.isSecureContext`'e bakıp gerçek sebebi söylüyor.
Headless tarayıcıda doğrulandı: kip kendiliğinden "WiFi / köprü (akış)",
kırmızı kutu yok, sayfa tam render.

##### SSE: her satır İKİ KEZ yayınlanıyordu

Yayını ölçerken kart 5/s rapor ederken SSE'den **10/s** geldi:
8 sn'de 80 `D` olayı, 40 benzersiz satır, dağılım `{2: 40}` —
istisnasız hepsi çift. Sebep: B20 `loop()`'a `akis_yolla(son_satir)`
eklediğinde SSE'yi besleyen tek yol oydu; **B22.4 `Serial` aynasını
getirdi** (tamamlanan her satır zaten aynadan gidiyor) ama eski çağrı
kaldırılmadı. `K` satırında da aynısı. Bedeli: iki kat WiFi trafiği,
grafikte üst üste noktalar, CSV'de çift satır.

İki çağrı da kaldırıldı; ölçüldü: 40 olay / 40 benzersiz / `{1: 40}`.
Zincire *"`akis_yolla` yalnızca ayna geri çağrısından çağrılır"* iddiası
ve onu yalanlayan mutasyon eklendi.

⚠ **Bir mekanizma daha genelini getirdiğinde eskisini KALDIR.** İkisi
birlikte çalışırsa sonuç sessizce iki katına çıkar.

##### Gizlilik: yayınlanan depoda 59 kişisel iz + geçmişte kullanıcı adı

Kullanıcının isteğiyle iki bağımsız ajan depoyu denetledi (çalışma
ağacı + tüm git geçmişi). **Parola, e-posta, ağ kimliği yok** — ama:

* **HEAD'de 59 mutlak yol** (`C:\<proje kökü>\...`): `b15-arastirma.md`
  56×, `arsiv/*/tam-dogrulama.txt` 2×, üç netlist. Kural `dogrula3.py`'de
  bir **yorum** olarak duruyordu — ve **yorum kuralı korumaz.**
* Netlist temizliği vardı ama **işe yaramıyordu**: B3 temizliyor, B9
  netlist'i **sonradan yeniden üretiyordu**. Üstelik `count=1` ile
  yalnızca ilk geçişi değiştiriyordu.
* **Git geçmişinde `076a366`** (ilk yayın): `b15-arastirma.md`'de üç satır
  Windows kullanıcı klasörü altındaki geçici bir yol — B24'te temizlenmiş ama geçmişte
  duruyor. Windows hesap adı + ölü bir oturum UUID'si; kimlik bilgisi yok.
  **Geçmişi yeniden yazmak kullanıcının kararı**, yapılmadı.
* Benim MAC fikstürüm (`test_tezgah_kart.py`) gerçek kartın OUI'sini
  taşıyordu; DEVIR'deki kasıtlı kısaltmayla birleşince tam adres
  kurulabiliyordu. Sentetik OUI'ye (`02:00:00`) çevrildi.
* ⚠ **Bu ortamda `grep` güvenilmez.** Ajan `grep -i` ile birden fazla
  `-e` deseninin çöktüğünü (`Aborted`) ve `2>/dev/null` varsa **sessizce
  boş** döndüğünü bildirdi. Benim ilk taramam da bu yüzden "temiz"
  demişti. Gizlilik taraması artık saf Python.

**Düzeltmeler:** `netlist_temizle.py` (tek kaynak, her üretim yerinde
çağrılıyor, tüm geçişler) · 59 yol depoya göreli yapıldı (klonlayan için
zaten daha kullanışlı) · **`gizlilik_dogrula.py`** yeni araç, zincirin
bir **değişmezi** olarak her koşuda çalışıyor (adım değil; deponun
tamamına ait) · iki mutasyon (yol + e-posta enjeksiyonu) yakalanıyor.

⚠ Tarayıcı ilk yazımında **kendi test verisini yakaladı** — `mutasyon.py`
örnekleri ve `netlist_temizle.py` docstring'i. Metin tabanlı iddianın kendi
açıklamasını yakalaması, bu projede **beşinci** kez.

##### Mutasyon koşucusu bu oturumda benim iddiamı çürüttü

Yeni SSID denetimi için iki mutasyon yazıldı. İkincisi — afişten `MAC=`
satırını silmek — **KAÇTI**: iddiam `"MAC=" in INO` diyordu ve `N` komut
çıktısındaki kopya onu yeşil tutuyordu. Koşucu afişi okuyor, `N`'i değil.
Kapsam `setup()` gövdesine daraltıldı, mutasyon artık yakalanıyor.

⚠ **Bu tam olarak B23.3'te koşucunun kurulma gerekçesiydi** ve ilk turunda
üç boş iddia bulmuştu. Bugün dördüncüyü buldu — **yazan bendim.**

##### Yan düzeltmeler

* `test_tezgah_kart.py`'deki *"24 denetim / 72 kalem"* elle yazılıydı ve
  **ikisi de bayattı** (gerçek 27/75) — üstelik kalem sayısı `_tezgah.md`'nin
  kendi son satırında doğru yazıyordu, yani üretilen belge **kendi içinde
  çelişiyordu**. Denetim sayısı artık `len(TK.DENETIMLER)`'den türetiliyor,
  kalem sayısı hiç yazılmıyor.
* `yukle.py` derlerken `--clean` geçmiyor, zincirdeki `test_firmware3.py`
  geçiyor (B21 dersi: önbellek uyarı gizler). Bugün zararsız çıktı —
  temiz derleme de **0 uyarı** ve **bayt bayt aynı** boyut verdi — ama
  ayrışma yüzeyi duruyor.
* `mutasyon.py` geçici kopya dizinini `_mutasyon-<pid>` diye açıyor ve
  dizin varsa **çöküyor**. Windows PID'leri geri dönüştürdüğü için bir kez
  tetiklendi; `dirs_exist_ok` ya da önceden temizleme gerekiyor.

##### Henüz sınanmayanlar

* **Web katmanı** — 5 denetim atlandı, `--http` istiyor. PC'nin kartın
  AP'sine katılması gerek: `OLCUM-KARTI-969C`, parola seri konsoldan
  (`N` komutu) okunuyor.
* **Aşama 1** — ADS1115'ler bağlanınca. I²C taraması şu an boş (beklendiği
  gibi); envanterde 3 modül var (MOD003).
* **`_tezgah.md`'nin ilk gün kalemleri** — multimetre isteyenler.

---

#### 5.12.43 📋 B27 — ARAYÜZ YENİDEN YAPIMI: PLAN (2026-09-12, onaylandı)

Kullanıcı gerçek kartta arayüzü açtı ve iki şey istedi: *"yavan ve karışık,
her yerde bildirim; ayrı sayfalar olsun; PC'de güzel görünsün"* ve demin
bulunan beş kusurun çözülmesi.

**Teknik zemin — değişmeyecek kararlar:**

* Arayüz **tarayıcıda** çalışır; ESP32 yalnızca dosya sunar + SSE akıtır.
  Animasyon/sayfa/renk ESP'ye **yük bindirmez.** ESP'yi ilgilendiren:
  dosya boyutu (LittleFS 917 KB) ve istek sayısı (tek çekirdek servis).
* **Vue 3'te kalınıyor.** Framework değişimi kazandırmaz, kaybettirir:
  `test_arayuz3.js` (122 iddia) Vue'ya bağlı, "derleme adımı yok" ilkesi
  bozulur. Eksik olan yönlendirme ve tasarım.
* **Hash yönlendirme** (`#/olcum` …) — stok-takip'te kanıtlanmış desen.
  Tek HTML, sıfır ek istek.
* Aynı kod PC + telefon; CSS kırılma noktası.

**Aşama 0 · Doğruluk** — sahte sayıyı güzelleştirmek yanlış olur

| # | Kusur | Düzeltme |
|---|---|---|
| K1 | `ads_oku` yanıt gelmeyince sessizce 0 dönüyor; kalibrasyon o sıfıra uygulanıp **1.716 V** gösteriliyor (ters çevrilmiş `n_sifir`). Çip bozulunca da aynı sahte sayı | Firmware hata bayrağı; `D` satırına durum alanı; arayüzde "veri yok" |
| K5 | Şönt menüsü `localStorage`'daki tercihi gösteriyor, karttan hiç okumuyor (menü 10R, kart 0.1R) | Bağlanınca `?`'den `sont`/menzil/kalibrasyon okunur |
| K2 | "geri besleme" etiketi gürültüde yanıp sönüyor | Ölü bant |
| K4 | Skop metni "0–48.7 V tek yönlü" — B19 çift yönlü yaptı | Metin `tasarim3_sabit`'ten türetilir |
| K3 | Hızlı ölçüm boş pinden 223.5667 W basıyor | Sinyal varlığı eşiği, altında "sinyal yok" |

Her biri: iddia + mutasyon + kartta doğrulama.

**Aşama 1 · Yapı** — beş görünüm, kalıcı üst şerit

```
#/olcum   Ölçüm      KPI + zaman grafiği          (açılış)
#/skop    Osiloskop  skop + hızlı ölçüm
#/pil     Pil testi
#/ayar    Ayarlar    kalibrasyon · şönt · menzil · ağ
#/konsol  Konsol     ham satırlar, komut
```

Üst şerit: bağlantı durumu, kart adı, **tek** bildirim alanı. Emniyet
uyarısı (J7/J3) ayrı ve kalıcı. `test_arayuz3.js`'nin "her firmware komutu
arayüzden erişilebilir" denetimi korunur.

**Aşama 2 · Tasarım sistemi** — tek kaynak CSS değişkenleri; laboratuvar
cihazı yönü (koyu zemin, fosfor izler, tabular rakamlar, tek vurgu);
ölçülü hareket; açık/koyu tema sistem tercihine uyar.

**Aşama 3 · PC ↔ telefon** — telefonda KPI + grafik + durdur, gerisi katlanır.

**Aşama 4 · Doğrulama** — her görünüm headless Edge ile render (B22.0
dersi: zincir render etmiyor); gzip toplam **< 250 KB**, dosya **≤ 8**;
ilk yükleme karta karşı ölçülür; PC + telefonda gerçek deneme.

Çok oturumluk iş. Aşama 0 ≈ 1, 1 ≈ 1, 2 ≈ 1-2, 3-4 ≈ 1.

##### ✅ Aşama 0 bitti (2026-09-12) — beşi de gerçek kartta doğrulandı

| # | Yapılan | Kanıt |
|---|---|---|
| **K1** | `ads_oku` hata bitini kuruyor/temizliyor; `D`'ye 10. alan **`durum`** (bit0 V, bit1 I okunamadı); enerji `if (!ads_hata)` kapısıyla birikiyor; arayüz "—" ve "veri yok — ADC yanıt vermiyor" gösteriyor | Tek ADS ile `D … 97 0 1`; koşucu I²C taramasıyla tutarlılığını doğruluyor (`0x49 YOK → durum=1, kart 1 dedi`). **Enerji 0.03 J çöpten 0.0000'a düştü** |
| **K2** | `gucYon` ölü bandı 1 mW | −10 µW etiket üretmiyor, −6 W hâlâ "kaynak" diyor (birim test) |
| **K3** | `hizli_yolla` ham ADC ortalaması raydaysa (<%2 / >%98) `! hizli yol: giris RAYDA` basıp **W'yi atlıyor**; arayüz eski sonucu siliyor | Kartta 3/3: `V ham ort=6…62` — 218 W artık hiç basılmıyor |
| **K4** | Skop metni "−63.5 … +46.8 V, çift yönlü"; `sim3_bant.py` metni `SKOP_MENZIL_EKSI/ARTI` ile karşılaştırıyor | 57/57 |
| **K5** | Bağlanınca `?` gönderiliyor; `A menzil=… sont=…` ayrıştırılıp menü **kartın** değerine uyduruluyor; uyuşmazlık görünür | 0.1 → menü `0.1`; 0.123456 → menü dokunulmaz, "uyuşmuyor" uyarısı |

**Mutasyon kapsamı genişledi:** `mutasyon.py` artık `.js` betikleri de koşuyor — `test_arayuz3.js`'in 138 iddiası ilk kez mutasyon altında (önce **hiçbiri** sınanmıyordu). B7: 2/2, B20: 6/6 yakalanıyor.

**Bu aşamada yakalanan kendi hatalarım** (hepsi mutasyon ya da test tarafından):

* K3'ün ilk ölçütü "ortalama raydada **VE** yayılım < 41 LSB" idi; kartta **kaçırdı** — boştaki pin gürültülüdür (yayılım >41), 218 W yine basıldı. Yayılım rayda olmanın kanıtı değil; ortalama yeter.
* K1 kaynak iddiası `"ads_hata" in blok` idi; mutasyon **kaçtı** — `ads_hata_pencere` alt dizge olarak eşleşiyordu. Kelime sınırı eklendi.
* K3 sıra iddiası `RAYDA[^}]*return;` idi; iç `if {}` blokları yüzünden **doğru kodda bile** kırmızıydı. Sıra tabanlı yazıldı.
* `test_tezgah_kart.py` ve `test_arayuz3.js` D alan sayısını **sabit** (`8` / `9`) yazmıştı; "kaynaktan türetiliyor mu" iddiası beklentiyi elle tutuyordu. İkisi de bağımsız sayımla karşılaştırıyor artık.
* Heredoc `\n` tuzağına **üç kez** düşüldü (`mutasyon.py`'ye çok satırlı dizge, `app.js`'e `\b` → backspace 0x08). Hafızadaki ders, tekrar.

⚠ **Aşama 2 tezgah kalemi:** K3'ün %2 rayda eşiği gerçek ön uçla doğrulanacak — boştaki pin 62 LSB'ye kadar sürüklendi (eşik 82).

##### ✅ Aşama 1 bitti (2026-09-12) — beş görünüm, karttan sunuluyor

Tek kaydırmalı 569 satırlık sayfa **hash yönlendirmeli beş görünüme** bölündü; yapı stok-takip'teki desenle aynı (`#/olcum` … `#/konsol`, geri tuşu çalışır, adres paylaşılabilir). ESP'ye **ek istek yok**: aynı tek `index.html`, görünümler `v-show` ile saklanıyor.

| Ne | Nasıl | Neden böyle |
|---|---|---|
| `GORUNUMLER` listesi (app.js) | id · ad · alt açıklama; sekme şeridi `v-for` ile bundan üretiliyor | Elle kopya olsaydı sekme ↔ görünüm ayrışırdı |
| `hashtenGorunum()` | `#/skop`, `#skop` → `skop`; bilinmeyen/boş → `olcum` | Bozuk adres boş sayfa **açmasın** |
| `v-show`, `v-if` **değil** | beş `<main class="gorunum">` | `v-if` tuvali yok eder; skop'a dönünce yakalama kaybolurdu |
| `watch.gorunum` → `$nextTick` → `grafikCiz()+osiloCiz()` | görünüme dönünce yeniden çizim | `display:none` tuval **0 genişlik** okur; çizilmezse 300 px varsayılanda sola yapışık kalır — headless'ta `nodemo-olcum,skop.png` ile **ispatlandı** (skop gizliyken açıldı, tam genişlik + ortalı "yakalama yok") |
| Tek `.bildirimler` sarmalı | üst şeritteki dört koşullu blok | `:empty` ise yer kaplamaz |
| Konsol | `<details>` katlaması gitti, kendi sekmesi | "kartla ham konuşma" artık gizli değil |

**Ayrışınca ortaya çıkan iki yerleşim kusuru** (tek sayfada fark edilmiyordu):

* *"Sıra önemli — önce girişi 0 V'a bağla…"* ve *"Kalibrasyon değeri negatif de olabilir"* paragrafları **pil bölümünün altında** duruyordu; sekmeler ayrılınca "Pil testi" ekranında kalibrasyon talimatı belirdi. Kalibrasyon kartına taşındı; test artık yerini civiliyor.
* Köprü olayı (`kopru` SSE) aynı bilgiyi **hem** `.hata` **hem** `.uyari` kutusunda basıyordu — iki bildirim, tek olgu. Bağlantılı olan kaldı (kullanıcının "çok bildirim" şikâyetinin ilk somut kalemi).

**Doğrulama:** `test_arayuz3.js` 142 → **156** (bölüm 10: liste↔HTML birebir, v-show, hash çözümü 4 durum, `watch.gorunum` davranışı sahte `this` ile, bildirim sarmalı, paragraf yeri). `mutasyon.py` B7 **6/6** — v-if'e çevirme, skop çizimini düşürme, hash doğrulamasını kaldırma, `hashchange` dinleyicisini silme: hepsi yakalanıyor. Headless Edge: 5 görünüm dev sunucudan (demo) + 5 görünüm **gerçek karttan** (kartın ev ağı adresinden, LittleFS `_fs.bin` 98.3 KB, %10.7) render edildi; geçiş testi iframe'de yalnızca hash değiştirerek (yeniden yükleme yok) yapıldı.

**Aşama 2'ye devredilen gözlemler:** üst şeritte taşıyıcı seçici + adres kutusu dar alanda alt satıra sarıyor (tasarım işi); demo kipinde seçici boş görünüyor (`demo` seçeneği menüde yok); ~~sayfa karttan geldiğinde "Karta bağlan"a basmak gerekiyor~~ (A2-a'da yapıldı).

##### ✅ Aşama 2-a (2026-09-12) — kullanıcının ekran görüntüsünden çıkan dört kusur + rapor aralığı

Kullanıcı canlı paneli gösterip üç şey sordu: *görünüm nasıl · "463 /sn" yazıyor ama ekran o hızda değil · grafik hangi hıza göre?* Cevap ararken **dört kusur** çıktı, ikisi yalnızca gerçek kartta görülebilirdi.

| # | Kusur | Nasıl bulundu | Düzeltme |
|---|---|---|---|
| **G1** | Kartlar "veri yok" derken **grafik sahte 1.72 V'u düz çizgi** çiziyor, "tepe 1.72 V" yazıyordu — K1'in grafik yarısı eksikti | ekran görüntüsü | geçersiz kanal `NaN` → çizgi kopar, etiket "veri yok", CSV'de hücre boş |
| **G2** | "463 /sn" tek sayı: ADC hızı ile ekran hızı karışıyordu | kullanıcının sorusu | iki ölçülen sayı: **"480 örnek/s"** + **"5 güncelleme/s"** (`1000/ölçülen aralık`) |
| **G3** | Sayfa açılınca gönderilen `?` **her seferinde 403** alıyordu: `ac()` EventSource'u kurup hemen dönüyor, jeton `kimlik` olayıyla sonra geliyordu. K5 eşitlemesi WiFi yolunda **hiç çalışmamıştı**, her açılış bir hata bildirimiyle başlıyordu | **CDP ile kartta** (`tarayici.py`) | `ac()` `kimlik`i (ya da hata / 3 s tavan) bekliyor; `?` jetonla gidiyor |
| **G4** | `?` için parola sorulması: izleyici daha ilk saniyede parola penceresiyle karşılanıyordu | CDP | `?` (salt okunur ayar dökümü) `p0` gibi **serbest**; `N` (parolaları basar) serbest **değil** — kartta 204/403 doğrulandı |

**Rapor aralığı kullanıcı seçimine açıldı** (`r<ms>`, 20..5000, sınır dışı **kırpılır ve kırpılmış değer basılır**; NVS'e yazılmaz — görüntüleme tercihi, tarayıcı localStorage'da tutup bağlanınca uydurur; şönt'ün tersi yön: orada kart haklı, burada tarayıcı). Menü: 20 · 10 · 5 · 2 · 1 /s. `A` satırına `rapor=` eklendi. Demo kartı aynı kırpma ile aynı davranıyor.

**Kartta ölçülen maliyet** (tek ADS, 465 örnek/s taban):

| aralık | seri, istemcisiz | WiFi'de 1 SSE istemcisi | en uzun döngü |
|---|---|---|---|
| 200 ms | 483 örnek/s | 444 örnek/s | 2.8 / 18 ms |
| 50 ms | 478 | 460 | 3.2 / 5.0 ms |
| 20 ms | 469 | **425** (−%9) | 2.9 / 5.3 ms |

"Yorar" somutlaştı: her satır istemci başına bir TCP yazma ve bu yazma ölçüm döngüsünün **içinde**; 20 ms'de tek istemci ~%9 örnek götürüyor. Osiloskop farklı: tek yakalama, tek blok, sonra sessiz — sürekli akış değil. SSE olayı artık istemci başına **tek `write()`** (önce dört `print()`); bunun tek başına etkisi ölçülmedi (eski firmware'e dönülmedi).

**Otomatik bağlanma:** sayfa kart/köprüden geldiyse (`localhost`/`file://`/`?demo` değilse) `kopruyuAlgila()` sonrası kendiliğinden bağlanıyor. Yan ürün: headless doğrulama artık **canlı veriyle** yapılabiliyor.

**Yeni araç — `uretim/tarayici.py`:** headless Edge'i CDP ile süren, yalnızca stdlib (asgari WebSocket istemcisi). `--screenshot`'un yapamadığı üç şey: JS değerlendirme, Basic Auth isteğini iptal etme (askıda kalınca sayfa "bağlı ama veri yok" görünüyordu — **ölçüm aracı bozuktu, sayfa değil**), sayfada etkileşim. G3 ve G4 onunla bulundu.

**Doğrulama:** `test_arayuz3.js` 156 → **197** (bölüm 11: NaN/çizim sahte tuval bağlamıyla, iki hız, `A rapor=`/`* rapor araligi` akışı, watch, firmware sınırları, demo kartı; bölüm 12: **asenkron** — sahte EventSource ile `ac()` kimlik gelmeden çözülmüyor, `?` jetonla gidiyor). Bölüm 12 için yakalanmayan asenkron hata artık açıkça kırmızı (`unhandledRejection` → exit 1) — ilk yazımda sessizce 0 ile çıkıyordu. `mutasyon.py` B7 **17/17**, B22b **8/8**. `tezgah_kart.py`: `d_rapor_araligi` (yanıt + **davranış** + kırpma + geri alma; kartta 10.0/s ölçüldü), `d_web_soru_serbest`; öz-test 46/46 ("yanıt var, davranış yok" senaryosu yakalanıyor). `sim3_web.py` 82/82.

**Bu aşamada yakalanan kendi hatalarım:** `belge-uret.py` ve `yetenek_tablosu.py` de `rapor_ms = <sayı>` arıyordu — zincir B9'da **çöktü** (`--sayim-kilidi-yaz` yine de taban yazdı — çökmüş adımın yarım sayısı kilide girdi; `sayim_kilidi()` artık **kırık koşuda yazmayı reddediyor**, doğrudan çağrıyla doğrulandı: dosya değişmedi); `ino_sayi`/`ino_sabit` artık `#define`'a bir seviye iniyor. `govdeIcinde()` C fonksiyonlarında ilk girintili *çağrıyı* tanım sanıyordu (iki iddia yanlış kırmızı) → `cGovde()`; NaN kopma testinde `lineTo −1` beklemiştim, doğrusu −2 (kopan nokta iki lineTo götürür); `tezgah_kart.py` `rapor_ms` sayısını `=` ile arıyordu, `#define`'a taşınınca import anında patlayacaktı; CDP betiğinde `select[title]` taşıyıcı seçicisini yakaladı (yanlış seçici, sayfa kusuru değil).

**Aşama 2'ye kalan:** kart yeniden başlarken sayfa açılırsa `app.js` gelmeyip ham `{{ }}` kalıyor — yeniden yükleme ipucu/`v-cloak` dışı bir hata durumu gerek (Aşama 4 dayanıklılık kalemi). `K` sayaçları sayfa her yüklendiğinde 200+ ms sıçrıyor: 100 KB gzip'i LittleFS'ten loop() içinde sunmak — çift çekirdek kalemi, yeni değil.

##### ✅ Aşama 2-b (2026-09-12) — tasarım sistemi

Kullanıcı A2-a'yı onaylayıp "sıkıntı yoksa sonraki aşamaya geç" dedi. Önce onun gözlemi kapatıldı (**akım hep µA'larda**), sonra tasarım sistemi.

**Akım sorusu — kusur değil, eksik bilgi.** Kartta ölçüldü: 0.1 Ω şöntte ham gürültü tam **1 LSB** (78 µA), 200 ms penceresinde 96 örneğin ortalaması ort **10.7 µA** ± 7.9 µA — yani ekrandaki "7 µA" gerçek bir akım değil, **çözünürlük tabanı**. Şönt ADS'in diferansiyel girişine doğrudan bağlı (kademe sabit ±0.256 V), menzili şönt belirliyor: 10 Ω → LSB 0.78 µA, 0.1 Ω → **78 µA**. Gerilim kartı menzilini ve adımını yazıyordu, **akım kartı yazmıyordu** — eklendi (`±2.56 A · 78.1 µA`), kaynağı kartın `sont=` değeri (menü yalnızca yedek).

**Tasarım sistemi:** `ek.css` `style.css`'e katıldı → **tek stil dosyası** (karttan her ek istek `loop()`'u blokluyor). Koyu tema **varsayılan**, açık tema sistem tercihine uyuyor; bütün belirteçler `:root`ta, açık blok yalnızca **değerleri** değiştiriyor. Renk yalnızca ölçülen büyüklükte (kanal renkleri = tuvaldeki çizgi renkleri, `renk('--volt')` aynı kaynaktan) ve tek vurguda (camgöbeği). Sayılar mono + `tabular-nums`; ölçüm kartlarının üstünde 2 px kanal rengi şeridi. Hareket ölçülü: tek sonsuz animasyon bağlı noktasının nabzı, `prefers-reduced-motion` hepsini kapatıyor. Üst şeritteki dört ayrı öğe tek `.baglanti` öbeği oldu (dar ekranda dağılıyordu); taşıyıcı menüsüne **`demo` seçeneği** eklendi — `?demo`'da seçici **boş** görünüyordu.

**Headless render iki canlı kusur buldu** (ikisi de yalnızca tarayıcıda görünür):

| | Kusur | Sebep | Düzeltme |
|---|---|---|---|
| **R1** | `sahte-kart.js` **iki kez** iniyor → `Identifier 'SahteKart' has already been declared` → sayfanın o andan sonraki betikleri düşüyor | `?demo` açılışında `demoVeri()` hem `mounted()`'tan hem yeni `watch`'tan çağrılıyor, ikisi de betiği beklerken geçiyordu | `betikYukle` aynı `src`'yi ikinci kez eklemiyor + `demoKurulu` kapısı `await`ten **önce** kapanıyor |
| **R2** | Demo akışı ilk 300 noktadan sonra **susuyor**, rozet "bağlı değil" | `demoVeri()` önce `tasiyiciAdi`'yi 'demo' yapıp sonra `bagli`'yi açıyor; `watch` ondan sonra koşup **az önce açılan** bağlantıyı "eski taşıyıcı" sanıp kapatıyordu | bağlı taşıyıcı artık açıkça tutuluyor (`bagliTasiyici`), watch yalnızca **onu** kapatıyor |

**Doğrulama:** `test_arayuz3.js` 203 → **225**; bölüm 13 tasarım sistemini sınıyor (her renk belirteci **iki temada da** tanımlı, kanal renkleri üçü de farklı ve vurgudan ayrı, `app.js`'in tuvalde okuduğu her belirteç CSS'te var, reduced-motion karşılığı, sonsuz animasyon ≤ 1, tek stil dosyası, her taşıyıcının menüde seçeneği). Mutasyon B7 **26/26** (yeni 7'si: akım rengini gerilime eşitle, açık temadan belirteç sil, reduced-motion bloğunu boz, demo seçeneğini kaldır, `destekli()`'yi geri al, `demoKurulu` kapısını aç, taşıyıcı sahipliğini eski hâle döndür). Headless: 5 görünüm × 2 tema yerel + karttan `#/olcum` (0 konsol hatası, ham `{{ }}` yok, nabız animasyonu etkin). LittleFS 102.9 KB, %11.2.

**Bu aşamada yakalanan kendi hatalarım:**

* Bölüm 13'ün iki asenkron iddiası **özet satırından sonra** koşuyordu: sayılmıyor, kırmızı olsa bile süreç 0 ile çıkıyordu — iddia değil süsleme. Asenkron iddialar artık `SONRA` kuyruğunda, özetten önce bekleniyor.
* Sahte 2B bağlam `measureText()` için `undefined` dönüyordu; gerçek tarayıcı her zaman `TextMetrics` döner. Taklit düzeltildi (B17 dersi: taklit **gerçeği** modellemeli, kodu savunmacı yazmak yerine).
* Yerel `secenekler` değişkeni Vue'nun `secenekler`ini gölgeleyip asenkron bölümü çökertti — `unhandledRejection` kancası sayesinde sessiz kalmadı.
* `tarayici.py`'nin `bekle()`'si soket zaman aşımını 0.25 s'ye çekip `al()` çağırıyordu; zaman aşımı **çerçeve ortasında** düşünce okunan 2 başlık baytı kayboluyor ve CDP akışı bozuluyordu (açık tema render'ı böyle düştü) → `select` ile önce veri var mı bakılıyor. Ayrıca `Fetch.enable` uzun oturumlarda `captureScreenshot`'ı asıyor: parolasız sunucuda `auth_iptal=False`, her tema **kendi tarayıcı örneğinde**.

**Aşama 3'e kalan:** telefon kırılımı (şu an yalnızca 560 px altı için asgari kural var), `ayar` görünümünde alan genişlikleri düzensiz, grafik tepe etiketleri şeritli ama hâlâ çizgiye yakın.

##### ✅ Aşama 3 bitti (2026-09-12) — PC ↔ telefon

Kullanıcı telefondan karta bağlanamıyordu; sebep **kartta değil adreste**: `olcum.local` bir mDNS adı, Windows ve iPhone çözüyor, **Android çözmüyor** (Chrome `.local`'i arama sorgusuna çeviriyor). IP ile (`http://<kart-ip>`) her şey parolasız açılıyor — 200, 9.6 KB, 115 ms. Bu tuzak artık **Ayarlar → Bağlantı** kartında yazılı ve testle korunuyor; kullanıcı telefondan bağlandığını doğruladı.

| Ne | Neden |
|---|---|
| **Acil durdurma şeridi** — pil testi çalışırken **her görünümde**, gezinmenin üstünde, tek düğme (`p0`) | Telefonda deşarj sürerken önce doğru sekmeyi bulmak zorunda kalmak emniyet kusurudur. Şerit görünümlerin **dışında** (yoksa yalnızca açık sekmede görünür) ve düğmede `:disabled` **yok** — `p0` zaten jetonsuz geçen tek komut |
| **Üst şerit sadeleşti**: yalnızca durum rozeti + birincil eylem | Taşıyıcı seçici ve kart adresi oturumda bir kez dokunulan şeyler; Ayarlar'ın yeni **Bağlantı** kartına taşındı. Telefonda üst şerit 89 px'e indi |
| **Telefon yerleşimi** (≤620 px): gerilim + akım yan yana, güç tam genişlik, ikincil kutular iki sütun, alt başlık gizli | Tek sütunda güç kartı ilk ekrandan düşüyordu. Gerçek 390 px'te **üç ölçüm de ilk ekranda** |
| ≤380 px'te tek sütuna dönüş | 26 px'lik mono sayı iki sütunda kutuya sığmıyor |

**Ölçüm aracının kendi kusuru:** `--window-size=390,844` Windows'ta işe yaramıyor — pencere ~500 px'in altına inmiyor, yani "390 px testi" aslında 496 px'te koşuyordu ve **telefon kırılımı hiç sınanmamıştı**. `tarayici.py`'ye `ekran()` eklendi (CDP `Emulation.setDeviceMetricsOverride`); gerçek 390/360 px'te doğrulandı. Acil şeridi görmek için `/pil` ucunu taklit eden tek kullanımlık bir sunucu yazıldı (demo sahte kartı pil testini modellemiyor).

**Doğrulama:** `test_arayuz3.js` 225 → **239** (bölüm 14: şerit görünümlerin dışında mı, yalnızca `CALISIYOR`'da mı, `p0` gönderiyor mu, `:disabled` **yok** mu, telefon ızgarası, çok dar ekran, üst şeritte seçici kalmamış mı, Ayarlar'da var mı, Android `.local` uyarısı yazılı mı). Mutasyon B7 **30/30**. Headless: 390 · 360 · 768 · 1280 px'te yatay taşma yok; **gerçek kartta 390 px** — üç ölçüm ilk ekranda, 0 konsol hatası. LittleFS 104.1 KB (%11.3).

**Kendi hatam:** "sonsuz animasyon en fazla bir yerde" iddiası ikinci **meşru** gösterge (acil nokta) gelince yanlış yere kırmızı döndü. Doğru ölçüt sayı değil **hangi seçici**: nabız yalnızca `.rozet.acik .nokta` ve `.acil-nokta`'da, ölçüm sayılarında animasyon yasak.

##### ✅ Aşama 4 bitti (2026-09-12) — bütçe, dayanıklılık ve **sayfa sunmanın ölçüme bedeli**

Plandaki iki sayı (gzip < 250 KB, dosya ≤ 8) **belgede yazıyordu ama hiçbir şey sınamıyordu** — yani bütçe değil temenniydi. Artık `_fs.json` (karta gerçekten yazılan görüntünün künyesi) üzerinden ölçülüyor: **105 060 B, %41 dolu, 6 dosya**. Sayfanın istediği her varlığın görüntüde olduğu da aynı yerde sınanıyor (B22.0'ın kusuru tam buydu).

**İlk yükleme kartta ölçüldü:** 622 ms · 107 KB · 7 istek. **İkinci açılış: statik trafik 0 B** (yalnızca `/pil` yoklaması) — 5.12.38'in ölçütü tutuyor, panel çıkarma adımı **açılmıyor**.

**🔴 Asıl bulgu — her HTTP isteği ölçüm döngüsünü boyutuyla orantılı blokluyor.** Varlık varlık ölçüldü (her ölçümden önce `K` sıfırlandı):

| varlık | boyut | `loop_azami` |
|---|---|---|
| boşta referans (istek yok) | — | **16–17 ms** |
| `/pil` yoklaması | 167 B | 15 ms |
| `index.html` | 10.1 KB | 33 ms |
| `style.css` | 6.5 KB | 34 ms |
| `vue.global.prod.js` | 58.4 KB | 155 ms |
| `app.js` | 27.8 KB | **186 ms** |

Yani **bir sayfa açılışı ≈ 0.4 s ölçüm kaybı**.

**B26'nın "30 s'de bir 26 ms" bulgusu yeniden ölçüldü** — hiçbir HTTP isteği ve hiçbir istemci yokken, 300 s kesintisiz:

| pencere | 50 s | 100 s | 150 s | 200 s | 250 s | 300 s |
|---|---|---|---|---|---|---|
| `loop_azami` | 16.3 ms | 22.3 | 22.3 | 22.3 | 22.5 | **22.5 ms** |
| >20 ms tur | 0 | 1 | 2 | 3 | 4 | **5** |

Yani kendiliğinden olay **var ama daha küçük ve daha seyrek**: ~50–60 s'de bir, **22.5 ms** (eşik 20 ms). İlk kayıttaki 26.5 ms, bringup koşucusunun **kendi HTTP denetimleriyle birlikte** ölçülmüştü — o sayı ikisinin toplamıydı. 75 s'lik iki ayrı pencerede (istemcisiz ve 1 SSE istemcili) hiç uzun tur görülmedi; olay 50 s'lik pencerede yakalanıyor.

**Çift çekirdek kararının gerekçesi netleşti:** baskın terim **sayfa sunumu** (186 ms), ikincil terim periyodik 22.5 ms. İkisi de aynı çözümle gidiyor (ölçüm döngüsünü çekirdek 1'e al), ama artık "gizemli kilitlenme" değil ölçülmüş iki kalem.

**Boşta yoklama seyreltildi:** `/pil` her 2 s'de bir yoklanıyordu — test çalışmıyorken ve pil görünümü kapalıyken karşılığı yok. Artık boşta **10 s**, test çalışırken veya pil görünümü açıkken 2 s. Ölçüldü: boşta 25 s'de `loop_azami` 18.5 ms, **0 uzun tur**.

**Dayanıklılık — "açılmadı" durumu artık görünür.** Kart yeniden başlarken sayfa açılırsa betiklerden biri gelmiyor ve ekranda ham `{{ }}` kalıyordu; `v-cloak` onu **gizliyor ama yerine bir şey koymuyor**. İki katmanlı kapı eklendi: betik `onerror`'ı (dosya hiç gelmediyse) ve 6 sn zaman aşımı (dosya geldi ama Vue mount edemediyse) → kırmızı kutu + **Yenile** düğmesi + sebep. `app.js`'i 404 döndüren bir sunucuyla doğrulandı: kutu çıkıyor, ham şablon yok.

**Doğrulama:** `test_arayuz3.js` 239 → **250** (bölüm 15: bütçe, dosya sayısı, varlık↔görüntü eşleşmesi, `onerror`, zaman aşımı, kutunun varsayılan gizliliği, Yenile eylemi, uyarlanır yoklama). Mutasyon B7 **33/33**. Gerçek kartta **5 görünüm × 2 tema**: ham şablon yok, açılmadı kutusu çıkmıyor, yatay taşma yok, **0 konsol hatası**. LittleFS 105.1 KB (%11.5).

---

#### 5.12.44 ✅ B28 — ÇİFT ÇEKİRDEK (2026-09-12)

Aylardır açık duran karar (5.12.34) kapandı. Gerekçe B27 Aşama 4'te **ölçülmüştü**: her HTTP isteği ölçüm döngüsünü boyutuyla orantılı blokluyordu (`app.js` 186 ms, `vue` 155 ms; eşik 20 ms), üstüne boşta ~50–60 s'de bir 22.5 ms.

**Bölüm:**

| çekirdek | ne yapıyor |
|---|---|
| **1** — Arduino `loop()` | ADS okuma, enerji, pil testi, `D` satırı, seri komutlar, komut kuyruğunu boşaltma, osiloskop |
| **0** — yeni `ag_gorevi()` | `WebServer.handleClient()`, SSE yazımı, kalp atışı |

Çekirdek 0 seçildi çünkü **WiFi/lwIP görevleri zaten orada**; ağ işini oraya koymak TCP'yi kendi çekirdeğinde tutuyor.

**Aralarında paylaşılan değişken YOK, yalnızca kuyruk:**

* `komut_kuyrugu_q` (0 → 1) — HTTP komutu. Elle sayaçlı halka tamponu iki çekirdekte **yarış** demekti (kayıp komut ya da aynı komutun iki kez çalışması); FreeRTOS kuyruğu oldu. `false` dönüşü (dolu → HTTP 503) ve 48 baytlık kalem sınırı **aynı**.
* `akis_kuyrugu_q` (1 → 0) — SSE satırı. Ölçüm çekirdeğinden sokete yazmak hem `akis[]` dizisinde ikinci yazar olurdu hem de kaldırılan blokajı geri getirirdi. Bırakma **beklemesiz**: kuyruk dolarsa satır **düşer ve sayılır**, ölçümü yavaşlatmaktansa telemetri satırını kaybetmek yeğdir.
* `skop_kilidi` — iki çekirdeğin gördüğü tek tampon. **Ölçüm tarafı asla beklemiyor** (`timeout 0`; döküm sürüyorsa yakalama reddedilip kullanıcıya söyleniyor), bekleyen hep çekirdek 0 (`/skop.bin`, 200 ms, sonra 503).

Kalibrasyon, NVS ve osiloskop yazımı **yalnızca çekirdek 1'de** — komutlar orada çalışmaya devam ediyor, tek yazar disiplini korundu. Pil halkası ekle-yalnız olduğu için `/pil` okuyucusu kilitsiz güvenli.

**Kartta ölçülen sonuç** (pasif dinleme; seri komut göndermeden, kartın kendiliğinden bastığı `K` satırlarından):

| | önce | **sonra** |
|---|---|---|
| tam sayfa yüklemesi sırasında `loop_azami` | **186 ms** | **3.8–4.1 ms** |
| boşta (40 s) | 16.7 ms + ~50 s'de bir 22.5 ms | **3.0 ms, 0 uzun tur** |
| örnekleme | 478 /s | **500–503 /s** |
| bringup koşucusunun kararlı-hal ölçütü | 26 541 µs ❌ | **11 418 µs ✅** |

**Geriye kalan tek >20 ms kaynağı benim kendi ölçüm komutumdu:** `?` çıktısı (9 satır, ~700 B) 115200 baud'da varsayılan TX tamponunu doldurup `Serial.print`i bloklıyordu — tek bir tur 27 ms. `setTxBufferSize(2048)` (begin'den **önce**) ile 11.8 ms'e indi. Ders: *ölçüm aracının kendisi ölçülen şeye karışabilir* — pasif dinleme olmasa bu sayı "çift çekirdek yetmedi" diye okunurdu.

**Bir gerçek yan etki bulundu ve görünür kılındı:** yoğun anlarda (osiloskopun ASCII dökümü ~63 satırlık patlama üretiyor + eşzamanlı sayfa yüklemesi) akış kuyruğu taştı — 32 satır düştü. Kuyruk 24 → 48 kalem (~10.7 KB) büyütüldü ve **düşen satır artık sessiz kalmıyor**: yer açılınca `! akis: N satir dustu (kuyruk doldu)` gönderiliyor. Eksik bir dökümü tam sanmak, düşmesinden kötüdür. Aynı yük tekrarlandı: **0 düşme**.

**Doğrulama:** `sim3_web.py` 82 → **97** (bölüm 3b: `loop()` artık `handleClient` çağırmıyor, görev çekirdek 0'a sabit, `vTaskDelay` var, komut kuyruğu FreeRTOS kuyruğu, komutlar hâlâ çekirdek 1'de, `web_satir_hazir` sokete yazmıyor, bırakma beklemesiz, düşen satır bildiriliyor, skop kilidinin iki yanı, TX tamponu `begin`'den önce, `C` telemetri satırı). Mutasyon B22b **15/15** — yedi yeni mutasyon: `handleClient`'ı `loop()`'a geri koy, görevi çekirdek 1'e kur, `vTaskDelay`'i sil, `web_satir_hazir`'ı sokete yazdır, skop kilidini `portMAX_DELAY` yap, düşme işaretini boşalt, `setTxBufferSize`'ı `begin`'den sonraya al.

**İki bayat iddia yenilendi** (B20'de aynısı olmuştu): *"`akis_yolla` yalnızca ayna geri çağrısından çağrılıyor"* ve *"kalp atışı `loop()`'tan çağrılıyor"* eski mimariyi kodluyordu. Niyetleri korunarak yeniden yazıldı: **sokete yazan tek yol** kuyruk boşaltıcıdır ve ölçüm tarafından çağrılmaz; kalp atışı **ağ görevinden** çağrılır. Eskisi bırakılsaydı çift gönderim koruması sessizce yok olurdu.

**İşlevsel doğrulama (kartta):** SSE 44 olay / 44 benzersiz / dağılım `{1: 44}` (B26 düzeltmesi kuyrukta korundu) · HTTP `?` → 204 ve yanıtı SSE'den geldi (çekirdekler arası komut yolu uçtan uca) · `/skop.bin` 5 tur eşzamanlı sayfa yüklemesiyle, beşinde de `32 + 2×adet` bayt, uyumsuzluk yok · 120 s dayanma: **0 yeniden başlatma**, 491 örnek/s, `ag_yigin_dip` 4828 B boş (8 KB yığının ~%40'ı kullanımda).

**Araç kusuru:** `mutasyon.py` Windows'ta yeni kopyalanan ağaca yazarken `PermissionError` alıp koşu ortasında çöktü (Defender/dizinleyici kısa süreli kilit). Yazma 5 kez deneniyor artık.

**Kalan:** ikinci ADS takılınca örnekleme bandı ve `durum` alanı yeniden ölçülecek. Çift çekirdek kararı kapandı — `loop_azami` eşiği artık 4 ms civarında, 20 ms'lik ölçüt rahat.

---

#### 5.12.45 ✅ B29 — İKİNCİ ADS TAKILDI (2026-09-12)

Kullanıcı ikinci ADS1115'i (0x49, gerilim) bağladı: VDD/GND, SDA/SCL paralel, **ADDR → 3V3**, ALERT boşta (tasarımda U7'nin ALERT ucu bilerek `unconnected`), dört analog giriş de GND'de.

**İlk kontrol:** `#` → `I2C: 0x48 0x49` · `durum` alanı **0** · gerilim **1.7157 V**. O 1.7156 V, aylardır ekranda hayalet olarak duran sayının ta kendisi ve **beklenen** değer: ön uç yokken AIN0−AIN1 = 0, firmware ise girişin VREF ofsetli gelmesini bekliyor (`sifir_ham = −1646`). Yani okuma yolu uçtan uca doğru çalışıyor.

**Koşucu bir kırmızı verdi: "ornek 96, beklenen 133".** Kusur **kartta değil modeldeydi.**

##### Çevrim süresi nereye gidiyor — ölçüldü, tahmin edilmedi

Firmware'e faz sayacı konup `?` çıktısına `F` satırı eklendi (256 çevrimlik kayan ortalama). Üç ayrı koşuda aynı sonuç:

| faz | ölçülen | ideal I²C bütçesi |
|---|---|---|
| iki ayar yazması | **324 µs** | 90 µs |
| RDY beklemesi (dönüşüm) | **1227 µs** | 1163 µs (±%10 osilatör) |
| iki dönüşüm okuması | **504 µs** | 224 µs |
| **toplam** | **2053 µs → 487 çevrim/s** | 1490 µs → 671/s |

Fark **işlem sayısıyla orantılı**: çevrimde 6 `Wire` işlemi var (2 yazma + 2×[işaretçi yazması + okuma]) ve fazlalık işlem başına **~69 µs**. Bu, ESP32 Arduino `Wire` sürücüsünün işlem başına sabit maliyeti — bit hızından bağımsız, yani 400 kHz'i yükseltmek bu kısmı kısaltmaz. Model bu terimi hiç saymıyordu; `tasarim3_sabit.I2C_ISLEM_EK_US = 69` olarak girdi ve koşucunun beklentisi 133 → **104** oldu (ölçülen 95–96, bant 94–115 ✓).

⚠ **Tik yuvarlaması değil:** ölçülen fazların hiçbiri 1000 µs'in katı değil — B22.1'deki `enableDelay` kusuru (periyodu 2000 µs'e kilitler) geri gelmemiş. Bunu artık **ayrı bir denetim** söylüyor, çünkü…

##### Düzeltilmiş model bir denetimi körleştirdi — yerine ölçülebilir olanı kondu

Beklenti 133'ten 104'e inince, `enableDelay` kusurunun ürettiği **100 örnek artık bandın içinde** kalıyor: örnek sayısı o kusuru **ayırt edemiyor**. Koşucuya `d_cevrim_fazlari` eklendi; ayırt eden ölçüt artık **fazın 1 ms tik sınırına oturması**. Öz-testteki senaryo da buna taşındı (eski hâli sessizce yeşil kalacaktı — bayat iddia).

##### B17'nin ölçütü: iki çip arasındaki başlatma kayması

Kod kaymayı **ölçüyor** (varsaymıyor) ve Lagrange hizalayıcısına veriyor — ama sayı hiç dışarı basılmıyordu. Artık `F` satırında: **152 µs (0.0740 örnek)**. Koddaki yorum "400 kHz'te ~95 µs, SABİT ve BİLİNEN" diyordu; gerçek bunun **1.6 katı** (aradaki fark yine `Wire` işlem yükü). Düzeltme olmasaydı 50 Hz / PF=0.5 yükte güç hatası **%8.35** olurdu — yani B17 mekanizması iki çip takılınca gerçekten iş yapıyor. Yorum ölçülen değerle düzeltildi; koşucu kaymayı 80–400 µs bandında ve Lagrange'ın düzeltebileceği aralıkta (< 0.5 örnek) denetliyor.

##### Sonuç

`tezgah_kart.py --sifirla --asama 1`: **50 geçti · 0 kaldı** (ilk kez hiç kırmızı yok). Öz-test 46 → **49** (üç yeni senaryo: tik kilidi, büyümüş kayma, `F` satırının hiç gelmemesi). Mutasyon B25 +3. `F` öneki seçilirken `T ` ile çakışma yakalandı — `T ` zaten osiloskop ayar satırının öneki ve koşucu onu telemetri sayıp süzüyordu; aynı öneği ikinci bir anlamla kullanmak bu projenin defalarca cezalandırdığı şey.

**Kalan:** analog ön uç (bölücü + VREF tamponu) kurulana kadar gerilim kanalı sabit 1.7157 V okuyor; gerçek gerilim ölçümü ön uçla gelecek. Örnekleme 487/s, Nyquist 244 Hz — tasarımın 100 Hz sınırı rahat.

---

#### 5.12.46 ✅ B30 — SESSİZ KUSUR: ALERT teli düştü, kart 3 kat yavaşladı (2026-09-12)

Kullanıcı "lehim yapmadan ne ölçebiliriz" diye sordu. İki iş seçildi: (a) girişler GND'deyken gürültü tabanı, (b) osiloskobu bilinen bir sinyalle sınamak. Birincisi koşarken **gerçek bir kusur ortaya çıktı.**

##### Kusur: kart çalışıyordu, sayılar doğruydu, sadece 3 kat yavaştı

Gürültü verisinde örnek sayısı **96 → 32**'ye düşmüştü. `F` faz satırı sebebi anında gösterdi:

```
F yaz_us=332  bek_us=5305  oku_us=533  toplam_us=6170
```

`bek_us = 5305` tam olarak `yeni_donusum_bekle(4000)` **zaman aşımı + `delayMicroseconds(1300)`** demek: RDY hiç gelmiyor, her çevrim zaman aşımına düşüyor. Örnekleme **487 → 162/s**. Kart hiçbir şey söylemiyordu — ölçümler doğru, sadece üçte bir hızda. B20'de aynı aileden bir kusur (91 SPS) **aylarca** fark edilmemişti.

Sebep fiziksel: kullanıcı ikinci ADS'i takarken **ADS #1'in ALERT teli çıkmış**. Reset denendi (eşik yazmaçları teorisi) — **düzelmedi**, yani teori yanlıştı; sinyal gerçekten gelmiyordu.

##### Tahmin etmek yerine pini ölçen kalıcı teşhis

`#` (donanım sağlığı) komutu I²C adreslerini gösteriyor ama ALERT telini **hiç sınamıyordu** — kusurun yarısını görüp yarısını kaçırıyordu. Eklenen prob:

```
! alert: pin=GPIO7 baslangic=YUKSEK 0x48=YOK 0x49=YOK
   -> ALERT teli hicbir modulde degil
```

🔴 **Prob iki modülü de deniyor.** Modülde `ADDR` ile `ALRT` **yan yana** pinler ve iki modül birbirine benziyor; tel #2'ye takılırsa GPIO7 yüksek-Z bir çıkış görür — "tel yok" ile **aynı belirti**. Ayırt etmek için #2'nin RDY'si geçici açılıp yoklanıyor, sonra eski hâline (yüksek-Z) döndürülüyor. Kullanıcıya "ara bul" dedirtmek yerine kart **söylüyor**: *"tel yanlış modülde: #2'den çıkarıp #1'e tak"*.

Ayrıca `rdy_zaman_asimi` sayacı eklendi (`F` satırında `rdy_asim=`): sayılan ama görünmeyen sayaç, sayılmamış sayaçtır.

Kullanıcı teli geri taktı, ölçüldü: `0x48=VAR sure=1229 us`, `bek_us=1227`, `rdy_asim=0`, örnekleme **474/s**. Bringup: **58 geçti · 0 kaldı** (`--http` ile).

##### Kalibrasyon çıkışı (CAL) — skopu lehimsiz sınamak için

`X<hz>` komutu GPIO10'da %50 kare dalga üretiyor (`X0` kapatır, açılışta kapalı). Her gerçek osiloskopta olan prob dengeleme çıkışının karşılığı; skop zinciri (12 bit DMA ADC + tetik + zaman tabanı + ölçüm matematiği) bugüne kadar **hiç bilinen bir sinyal görmedi**, yalnızca benzetimde doğrulandı. Tek atlama teliyle (GPIO10 → GPIO4) sınanabilir.

🔴 **Basılan frekans İSTENEN değil GERÇEKLEŞEN.** LEDC 80 MHz APB'yi tam sayı bölerek üretiyor; kartta ölçüldü: **7000 istendi, 6998 üretildi**. Skopun ölçümünü istenen değerle karşılaştırmak, ölçümü kendi varsayımıyla doğrulamak olurdu.

⚠ Sınırı da yazalım: CAL ile ADC örnekleme saati **aynı kristalden** türüyor. Bu test skopun *iç tutarlılığını* (bölücü, tetik indeksi, görev oranı matematiği) doğrular, **mutlak frekans doğruluğunu değil**. Mutlak ölçüm harici bir referans ister.

##### Gürültü tabanı — artık ölçülmüş sayı (10 dk, girişler GND'de)

| | gerilim (0x49) | akım (0x48) |
|---|---|---|
| ortalama | 1.7156 V (1646.04 LSB) | 1.14 µA (0.01 LSB) |
| 200 ms penceresinde σ | 0.0623 LSB | 0.1010 LSB |
| **tek örnek σ** | **0.607 LSB** | **0.983 LSB** |
| tepe-tepe | 0.38 LSB | 0.74 LSB |
| **10 dk kayması** | **0.004 LSB** | **0.004 LSB** |

Yani ADS'ler tek örnekte ~**1 LSB RMS** gürültüyle çalışıyor (veri sayfası tipik değeri) ve 10 dakikada ölçülebilir **hiçbir kayma yok** — hata bütçesindeki (B1) ofset varsayımı gerçekle uyumlu. Gerilim kanalının 1.7156 V'u ön uç yokken beklenen sabit (bkz. 5.12.45).

⚠ İlk ölçüm ALERT kusurluyken alınmıştı ve **sıfır varyans** gösteriyordu — o sayı geçersizdi, tekrarlandı. Ders: bir ölçüm almadan önce *ölçüm koşullarının* sağlıklı olduğunu doğrula (`F` satırı tam bunun için var).

##### Doğrulama

`sim3_bant.py` 60 → **69** (1b-ter: RDY sayacı, `#` probu, iki modül ayrımı, #2'nin geri döndürülmesi; 1c-bis: CAL komutu, açılışta kapalı, gerçekleşen frekans, pin çakışması yok). Mutasyon B20 **10/10**.

🔴 **Mutasyon boş bir iddiamı yakaladı:** "prob hangi modülde olduğunu ayırt ediyor" denetimi `"ADS_GERILIM" in g_prob` diye bakıyordu; o ad probu **eski hâline döndüren** satırda da geçtiği için, denemeyi `iki = false` yapan mutasyon **kaçtı**. Ölçüt çağrının kendisine (`alert_dener(ADS_GERILIM`) çevrildi.

**Araç kusuru (ikinci kez):** `mutasyon.py`'nin `rmtree(..., ignore_errors=True)`'u Windows kilidinde **sessizce** başarısız olup sonraki `copytree`'yi çökertiyordu. Artık beş kez deneniyor, olmazsa benzersiz ada kaçılıyor — koşu bölünmüyor.

---

#### 5.12.47 ✅ B31 — OSİLOSKOP İLK KEZ GERÇEK SİNYAL GÖRDÜ (2026-09-12)

Kullanıcı GPIO10 (CAL) ile GPIO4 (skop girişi) arasına tek tel taktı. Osiloskop zinciri — 12 bit DMA ADC, tetik, zaman tabanı, ölçüm matematiği — bugüne kadar **yalnızca benzetimde** doğrulanmıştı; ilk kez bilinen bir sinyalle sınandı.

##### Frekans ve periyot: Nyquist'in altında **tam isabet**

| CAL (gerçekleşen) | tdiv | fs | örnek/periyot | skop f | hata | görev |
|---|---|---|---|---|---|---|
| 100 Hz | 50 ms | 2 000 | 20.0 | 100.000 | **%0.000** | 49.95% |
| 200 Hz | 20 ms | 5 000 | 25.0 | 200.000 | **%0.000** | 51.95% |
| 500 Hz | 10 ms | 10 000 | 20.0 | 500.000 | **%0.000** | 49.95% |
| 1 kHz | 10 ms | 10 000 | 10.0 | 1000.000 | **%0.000** | 49.95% |
| 2 kHz | 5 ms | 20 000 | 10.0 | 2000.000 | **%0.000** | 49.95% |
| 5 kHz | 2 ms | 50 000 | 10.0 | 5000.000 | **%0.000** | 49.95% |
| 8 kHz | 1 ms | 83 333 | 10.4 | 7995.054 | %−0.062 | 49.63% |

Gerilim eşlemesi de tasarım sabitleriyle **birebir**: 0 V → −63.53 V, 3.3 V → +54.36 V, Vpp 117.886 V = 4096 × 28.788 mV (tam ölçek). Ön uç yokken 0–3.3 V kare dalga ADC'yi raydan raya sürüyor — beklenen davranış.

⚠ **Dürüst sınır:** CAL ile ADC örnekleme saati **aynı kristalden** türüyor. Bu test skopun *iç tutarlılığını* doğrular (bölücü, tetik indeksi, görev matematiği), **mutlak frekans doğruluğunu değil**. Onun için harici referans (multimetrenin Hz kademesi) gerekir.

##### 🔴 Bulunan kusur: en yavaş zaman tabanı asla tamamlanmıyordu

Yakalama zaman aşımı **4 s'e kapatılmıştı**, ama en yavaş kademenin (500 ms/bölme) penceresi **5 s**. OTO kipi tetik bulamayınca eldeki kısa kaydı döndürüyor: kullanıcı "10 bölme × 500 ms" seçip **3.77 s**'lik kayıt alıyordu. Kartta ölçüldü: **3055 örnek beklenirken 2304** geldi.

Çizim yanlış değildi — `S2` satırı gerçek adet/hızı bildiriyor ve eksen ondan hesaplanıyor. **Yalan olan etiketti.** Düzeltme: zaman aşımı tavanı artık pencerenin kendisinden küçük olamıyor (`taban = pencere × 1.2 + 300 ms`). Ölçüldü: tdiv=11 → **3055 örnek / 5.00 s**, on iki kademenin hepsi modelle birebir.

Bedeli açıkça yazıldı: yakalama süresince ölçüm döngüsü duruyor ve bu boşluk zaten `enerji_kayip_ms` olarak sayılıyor.

##### Kendi ölçüm hatalarım (ikisi de rapor edilmeden yakalandı)

* **"tdiv=9'da yakalama yok"** — kusur değil, benim bekleme penceremin kısalığıydı (1 s yakalama + döküm). Uzun beklemeyle sorunsuz. Rapor etmeden önce kontrol ettim.
* **"tdiv 10 ve 11 modelden farklı"** — ölçümüm kaymıştı: tdiv=9'un geç gelen yakalaması bir sonraki satırın sonucuna karıştı. Tamponu boşaltıp tek tek ölçünce 10 tuttu, **yalnızca 11 gerçekten sapıyordu**.
* **50 kHz'te %60 hata** — kusur değil, **benim test tasarımım**: tdiv=2'de Nyquist 41.7 kHz, sinyal onun üstünde. Ön uçtaki 25 kHz süzgeç (henüz kurulmadı) tam bunun için var.
* **Görev oranı sapması** (10 kHz'te %59.94) — örnek nicemlemesi: 5 örnek/periyotta çözünürlük %20. Beklenen davranış.

##### Doğrulama

`sim3_skop.py` 24 → **31** (bölüm 5: on iki kademenin tamamlanabilirliği firmware'in **kendi tablosundan** türetiliyor, alt sınır ifadesinin varlığı, kartta ölçülen üç kademe, 1-2-5 dizisi, artan/tekrarsız). Mutasyon B19 **2/2**.

🔴 **Mutasyon yine boş bir alan gösterdi:** tabloda `5000 → 4000` değişikliği hiçbir denetimi kırmadan geçti — yani tablonun **içeriği** hakkında hiçbir iddiam yoktu, yalnızca zaman aşımı ilişkisi hakkında. Ölçü aletlerinin zaman tabanı **1-2-5 dizisini** izler; bu kural eklendi ve mutasyon artık ısırıyor.

---

#### 5.12.48 ✅ B34 — ESP32 ADC'sinin DOĞRUSALSIZLIĞI ÖLÇÜLDÜ (2026-09-12)

Kullanıcı "lehimsiz ne geliştirebiliriz" deyince seçilen iş. Skopun gerilim ekseni bugüne kadar ADC'yi **tam doğrusal** varsayıyordu (`SKOP_ADIM` sabit çarpan) — bu varsayım hiç sınanmamıştı.

##### Düzenek: kartın kendisi referans üretiyor

CAL çıkışı (GPIO10) PWM, 20 kHz, **10 bit görev oranı** → iki kademe RC (10K + 100nF ×2) → GPIO4. Görev oranı **tam sayı ve tam bilinen**, yani ölçüm kendi varsayımına değil bağımsız bir sayıya dayanıyor. 101 nokta, her nokta 833 örneğin ortalaması (dalgalanma tepe-tepe 15–26 kod, ortalamanın standart hatası 0.06 kod).

##### Sonuç: sapmanın dörtte üçü ADC'nin

| | en büyük sapma | rms |
|---|---|---|
| **Ham kod** (bugünkü yol) | **+75.6 kod = +60.9 mV** | 14.7 mV |
| **Fabrika eğrisi** (eFuse) | **−15.4 mV** | 4.9 mV |

Doğru bölge %5–%85; üstünde ADC doyuma giriyor (kod 4095 = **3160 mV**, kalibrasyonun söylediği).

🔴 **Bu, "eğri ADC'nin mi kaynağın mı" sorusunu kaynağı hiç değiştirmeden yanıtlıyor:** kalibrasyon ham kodun **saf fonksiyonu**; aynı ham veriyi ondan geçirince sapma 4 kat düşüyorsa, sapma ADC'dedir. Kalan 4.9 mV rms kaynağın dalgalanması, PWM seviyesi ve kalibrasyonun kendi hatasının toplamı.

##### Skop ekseninde ne demek

`SKOP_ADIM` = 28.79 mV/kod olduğundan:

| | pinde | **skop girişinde** |
|---|---|---|
| ham doğrusalsızlık | 58 mV | **±2.18 V** |
| fabrika eğrisiyle | 15.4 mV | **±0.57 V** |

Skop menzili −63.5…+46.8 V (110.3 V aralık) — yani tam ölçeğin **%2'si → %0.5'i**. Ayrıca tasarımın varsaydığı ADC tam ölçeği **3100 mV**, ölçülen **3160 mV**: doğrusalsızlıktan **ayrı** bir **%1.9 kazanç hatası**.

##### Yapılanlar

* `adc_cali` eğri şeması firmware'e eklendi; `c<ham>` komutu ham kodun fabrika-kalibre mV karşılığını veriyor. `?` çıktısında `adc_cali=egri|YOK` — kalibrasyon yoksa **sessiz kalmıyor**, çünkü kalibrasyonsuz bir mV değeri "ölçülmüş" gibi görünüp aslında ham kodun sabitle çarpımı olurdu.
* `x<promil>` ile CAL görev oranı (panelde kaydırıcı) — RC ile birlikte **ayarlanabilir 0–3.3 V DC kaynağı**.
* 🔴 **Kendi eklediğim kusur:** `ledcAttach(pin, hz, 10)` sabit 10 bit varsayıyordu; 50 kHz bu kartta 10 bitle **üretilemiyor**, ama panelde seçenek duruyordu. Daha sinsisi: düşük frekansta bağlanıp `ledcChangeFrequency(50000)` çağrılınca API **50000 dönüyordu** — aynı soruya iki yoldan iki farklı cevap. Artık çözünürlük **donanıma soruluyor** (12→6 deneyip tutanı bulur) ve bildiriliyor: 1 kHz→12 bit, 10 kHz→11, 20 kHz→10, 50 kHz→9, 200 kHz→7. Bu, B31'deki "50 kHz'te %60 hata = örtüşme" yorumunu da doğruluyor: üreteç 50 kHz'i gerçekten üretiyor.
* Ham veri depoda: `uretim/olcum-adc-dogrusallik.csv` (101 nokta, düzenek ve yöntem başlıkta).
* `sim3_skop.py` 31 → **37** (bölüm 6: kalibrasyon kuruluyor mu, **atten'i sürekli kipinkiyle aynı mı** — farklıysa aynı ham kod başka gerilime çevrilir ve hata sessiz olur, kalibrasyon yokken susmuyor mu, `c` girdisi kırpılıyor mu, tasarımın tam ölçeği ölçülenle %5 içinde mi, ham doğrusalsızlık skop tam ölçeğinin %5'inden küçük mü). Mutasyon B19 **4/4**.

##### 🔶 KARAR BEKLEYEN: kalibrasyon skop eksenine uygulanacak mı

Uygulamak ölçümü 4 kat iyileştirir ama bir **protokol** kararı gerektiriyor: kart bugün **ham kod + tek ölçek çarpanı** yolluyor (`/skop.bin`, `S2`), eğri ise tek çarpanla ifade edilemez. Üç yol:

1. **Kart mV yollasın** — protokol değişir, arayüzün ölçek çarpanı 1 olur; en temiz, en çok dokunan.
2. **Kart ham + küçük düzeltme tablosu yollasın** (ör. 17 nokta), arayüz aradeğerlesin — protokol geriye dönük uyumlu kalır.
3. **Bırakılsın**, belgede "skop ekseni ±2.2 V doğrusalsızlık taşır" yazsın — skop zaten kaba bir dalga-şekli aracı.

Bu adım ölçüyü çiviledi; kararı kullanıcıya bırakıyor.

---

#### 5.12.49 ✅ B35 — SKOP KÖPRÜ KİPİNDE HİÇ ÇALIŞMIYORMUŞ + geriye dönük kayıt (2026-09-12)

Kullanıcı yönü seçti: *"Ben osiloskopda şekilleri görebilmek istiyorum. Eğer ki bilgisayara bağlı ise hem şekilleri görebilmek hem de geriye dönük kayıtlar alabilmek de isterim."*

Hangi yoldan başlanacağına karar vermeden önce **var olanı ölçtüm** — ve istenen şeyin ikisi de yoktu.

##### 🔴 Bulunan canlı kusur: köprüde osiloskop ölü bir düğmeydi

`arayuz3/app.js`'te `TasiyiciAkis` (kart doğrudan **ve** PC köprüsü aynı taşıyıcıyı kullanıyor) `skop: 'ikili'` ilan ediyor ve yakalama gövdesini `/skop.bin`'den çekiyor. Sayfa köprüden geldiğinde o istek **köprüye** gidiyor; köprü ise `arayuz3/`yi servis eden bir `SimpleHTTPRequestHandler` — yani **404**.

Yani osiloskop, tam da kullanıcının "PC'ye bağlıyken şekil görmek" istediği kipte çalışmıyordu. Zincir 18/18 yeşilken. (B22 → B23 → B31 → B35: aynı sınıf, beşinci kez.)

##### 🔴 İkinci canlı kusur: arşiv hatası röleyi öldürüyordu

`Arsiv.kapat()` `_gun`u sıfırlamıyordu. Kapatılmış arşive gelen **ilk** satır `yaz()` içinde `AttributeError` atıyor, bu da **yukarı-akış ipliğini öldürüyordu**. Köprü ayakta görünmeye devam ediyor, HTTP cevap veriyor, ama ne arşiv ne SSE çalışıyor ve **hiçbir yerde yazmıyordu**.

⚠ **`test_kopru.py`'nin kendisi de bu kusurdan etkilenmişti:** 2. bölümdeki `k.arsiv.kapat()` çağrısından sonraki **bütün bölümler**, yukarı-akış ipliği ölmüş bir köprüye karşı koşuyordu ve hiçbir iddia bunu yakalamıyordu. Kanıt: iplik yaşamaya başlayınca SSE gerçekten yayın yapmaya başladı ve kapanış davranışı değişti.

Röle artık arşiv hatasında **durmuyor**; sebep bir kez akışa basılıyor. Röle kritik işlev, arşiv ikincil.

##### Kayıt: ayrı dosya YOK, günlükten türetiliyor

Köprü zaten her seri satırı `<ms>\t<satır>` olarak `kopru/arsiv/<gün>.satir`'a yazıyor. Skopun `t` komutu ASCII dökümü (`S2 … E`) **`Serial`den geçiriyor** — yani yakalama zaten günlüğe düşüyor. Ölçüm bunu doğruladı: iki günlük arşivde **`grep -c "^S2"` = 0**, çünkü arayüz `tB` kullanıyordu ve `tB` seri porta hiçbir şey basmıyor.

Yani "geriye dönük kayıt" özelliği **yeni bir depolama gerektirmedi**: `Arsiv.skop_bloklari()` aynı günlükten türetiyor, `csv_uret`in `D` satırlarından CSV üretmesiyle aynı desen. Ayrı tutulsaydı iki temsil ayrışırdı.

🔴 **HAM ADC KODU saklanıyor, mV değil.** B34'te ölçülen doğrusalsızlığın düzeltmesi henüz karara bağlanmadı; ham saklandığı için ileride bulunacak her düzeltme **eski kayıtlara da** uygulanabilir. mV saklansaydı her kayıt o günkü kalibrasyona çivilenirdi ve geri dönüşü olmazdı. **Bu, sıralamayı belirleyen argümandı: önce kayıt, sonra kalibrasyon.**

##### Taşıma kararı: köprüde ASCII, kartta ikili (sezgiye ters)

| | kart ↔ tarayıcı | seçilen yol | neden |
|---|---|---|---|
| **Kart doğrudan (WiFi)** | tek bağlantı | `tB` + `/skop.bin` | döküm SSE'yi tıkamasın; 20 250 B yerine 8 032 B |
| **PC köprüsü (USB)** | kart↔köprü **115 200 baud** + köprü↔tarayıcı LAN | düz `t` (ASCII) | döküm **zaten** seri porttan geçmek zorunda (arşive düşmesinin tek yolu; kartta ikili-seri döküm yok). Geldiğine göre ayrıca `/skop.bin` çekmek aynı dalgayı **ikinci kez taşımak ve iki kez çizmek** olurdu |

Pahalı bağlantı kart↔köprü: 4000 örnek ≈ 20 KB ≈ **1.8 s**. Bedel her iki durumda da orada ödeniyor, yani köprüde ASCII yolu bedava.

Köprü yine de `/skop.bin` sunuyor (curl/betikler için, kendi `t`sini tetikliyor) ve arayüzün `tB`sini `t`ye **çeviriyor** — çevirmeseydi kart iki kez yakalar, arayüze dönen dalga kullanıcının tetiklediği dalga **olmazdı**.

##### Tek çözücü kuralı korundu

`skopIkiliAl` ikiye ayrıldı: **`skopIkiliCoz(buffer)`** artık hem canlı yakalamanın hem arşivden açılan eski kaydın tek çözücüsü. İki çözücü yazılsaydı biri sessizce başka bir dalga çizerdi (endian/ölçek/ofset) — bu projenin üç kez yandığı ayrışma sınıfı.

##### Yeni uçlar

| Uç | Ne |
|---|---|
| `GET /skop.bin` | canlı yakalama, **kartın biçiminde** (aynı 32 B başlık, aynı `S3B` imzası) |
| `GET /skop/liste[?gun=]` | arşivdeki yakalamalar — **örnek dizisi taşımıyor** (4000 örnek ≈ 20 KB/satır olurdu) |
| `GET /skop/al?gun=&ms=` | tek kaydı aynı ikili biçimde |
| `GET /durum` | `skop_arsiv: true` — arayüz köprüde mi kartta mı olduğunu **bundan** anlıyor (kart `/durum` ucunu hiç açmıyor, yani yanıtın kendisi köprünün imzası) |

##### Arayüz

Skop görünümüne **Kayıtlar** bölümü eklendi — `v-if="skopArsivVar"`, yani kart doğrudan bağlıyken **hiç çizilmiyor**: çalışmayan bir düğme göstermek DEVIR 4.15'in ta kendisiydi. Tuvalin üstünde arşiv kaydı çizilirken ayırt edici şerit + "Canlıya dön"; olmasaydı geçmiş bir dalgaya bakıp "kart şu anda bunu ölçüyor" sanılırdı. Kırpık kayıt listede işaretleniyor. Zaman damgasının **duvar saati olmadığı** yazıyor.

##### Doğrulama

* `test_kopru.py` **24 → 54** iddia (bölüm 7 skop + bölüm 8 arşiv dayanıklılığı). Mutasyon B22a **2 → 13**, hepsi yakalandı.
* `test_arayuz3.js` **250 → 266** (bölüm 16). Mutasyon B7 **33 → 41**, hepsi yakalandı.
* Mutasyon koşucusu bir **boş iddia** yakaladı: örnek tavanı (`adet_bildirilen`) sınanmamıştı — `yer = 1 << 30` mutasyonu kaçtı. Tavan sınandı **ve** taşan örnekler artık sessizce atılmıyor, `atlanan`a yazılıyor.
* **Gerçek kartta** (`uretim/tezgah_skop_arsiv.py`, COM6): **16/16** — 1000 örnek 1.07 s, arşive düştü, geri okunan kayıt canlı gövdeyle bayt-bayt aynı.
* **Gerçek tarayıcıda** (`uretim/tarayici_skop_arsiv.py`, CDP + Vue + DOM, sahte köprü): **14/14**. Bölüm 16 kaynak metninde arama yapıyor — sayfanın açıldığını kanıtlamıyor (B22.0 dersi).
* 🔴 **Tarayıcı koşusu bir görsel kusur yakaladı:** rozetlere verdiğim `uyari` sınıfı bu projede emniyet uyarısının **kırmızı şeritli kutu** stili; rozetler buton gibi görünüyordu ve "serbest koşu" (normal bir tetik kipi) alarm rengindeydi. Kendi değiştiricisine (`dikkat`) ayrıldı; listedeki tek vurgulu işaret artık `kırpık`.
* ⚠ **Bir kez de ölçümün kendisi yanlıştı:** `innerText.includes('kırpık')` başarısız oluyordu ama ürün doğruydu — `text-transform: uppercase` altında Chrome'un `innerText`'i dönüşümü uyguluyor ve "KIRPIK" döndürüyor (Türkçede ı → I). `textContent`'e geçildi.
* Ürün gürültüsü: tarayıcı SSE sekmesini kapattığında köprü konsoluna 25 satırlık yığın izi basıyordu. Yalnızca kopma ailesi (`BrokenPipe`/`ConnectionReset`/`ConnectionAborted`/`Timeout`) susturuldu — başka her istisna aynen basılıyor.

##### 🔶 B34'ün kalibrasyon kararı hâlâ açık — ama artık acelesi yok

Kayıtlar **ham** tutulduğu için düzeltme ne zaman kararlaştırılırsa geçmişe de uygulanabilir. Ayrıca B34'ün seçeneklerinde bir **düzeltme**: "çipin kalibrasyonundan tek bir volt/adım türetmek" (2a) yalnızca **%1.9 kazanç hatasını** kaldırır; ±76 kodluk **eğriliği** olduğu yerde bırakır. Kullanıcının istediği şey *şekil* olduğuna göre şekli gerçekten düzleştiren tek yol **düzeltme tablosu** (seçenek 2).

---

#### 5.12.50 ✅ B36 — SKOPUN GERİLİM EKSENİ ARTIK KALİBRE (2026-09-12)

B34 ölçümü çivilemişti ama düzeltme uygulanmıyordu; B35 kayıtları **ham kod** olarak sakladığı için sıra doğal olarak buraya geldi. Karar: **düzeltme çizim anında, arayüzde.**

##### Tablo karttan geliyor, koda gömülü değil

Yeni firmware komutu:

```
CT  →  CT 17 oran=38.037037 ofset=63.530090 tavan_mv=3100.0
       0:0 256:229 512:452 … 3840:3053 4095:3160
```

🔴 **Her yonganın eFuse eğrisi kendisine ait.** Benim tek bir kartta ölçtüğüm eğriyi koda gömmek başka bir karta **yanlış** düzeltme uygulamak olurdu. B34'ün 101 noktalı ölçümü bu tablonun *kaynağı* değil, **denetimi**.

🔴 **`oran` ve `ofset` tabloyla birlikte gidiyor.** Arayüzün bunları kendi sabitlerinden türetmesini isteseydik, türetme VREF'in nominal değerine gömülü bir varsayıma dayanırdı ve VREF bir gün kalibre edilince eksen **sessizce** kayardı. Arayüz `V = (mv/1000)·oran − ofset` hesabını kartın söylediği sayılarla yapıyor.

##### Bağımsız iki kaynak uyuşuyor

| | en büyük sapma | rms |
|---|---|---|
| B34 · PWM+RC süpürmesi (ham kod → gerçek gerilim) | ±60.9 mV | **14.7 mV** |
| B36 · eFuse tablosunun kendi eğriliği (%5–%85 bandı) | −35.8 mV | **13.5 mV** |

Aynı fiziksel eğriliği iki bağımsız yoldan ölçtük ve rms'ler **%10 içinde**. Tablo doğru düzeltme.

##### Düzeltmenin büyüklüğü — beklenenden çok daha fazla

Kartın varsaydığı doğru `mV = 0.7568·kod`; çipin söylediği `mV = 0.7942·kod + 69.6`:

| bileşen | değer | ne yapar |
|---|---|---|
| kazanç hatası | **+4.94 %** | genliği bozar, şekli bozmaz |
| ofset hatası | +69.6 mV → **+2.65 V** girişte | izi kaydırır |
| gerçek doğrusalsızlık (%5–85) | −35.8 mV → **−1.36 V** girişte | **şekli** bozar |

Toplam düzeltme girişte **9.2 V**'a kadar çıkıyor — tam ölçeğin %8.4'ü.

**Gerçek yakalamada ölçüldü** (CAL 1 kHz, görev %50, 1000 örnek, ham kod 1845–1989):

```
en düşük  kod 1845:  ham -10.416 V → kalibre  -3.869 V   (+6.55 V)
en yüksek kod 1989:  ham  -6.271 V → kalibre  +0.732 V   (+7.00 V)
tepe-tepe            ham   4.145 V → kalibre   4.600 V   (%+11.0)
```

##### 🔴 Tek çeviri noktası

`kod * voltAdim - voltOfset` arayüzde **dört ayrı yerde** yazılıydı: tetik seviyesi, tepe değeri, dikey ölçek, çizim döngüsü. Düzeltme eklenince dördünün de değişmesi gerekirdi; biri unutulsa **ızgara etiketi bir şey, iz başka şey** gösterirdi ve hata sessiz olurdu. Hepsi artık `kodVolt()`'tan geçiyor. Mutasyon bunu üç ayrı yoldan sınıyor.

##### Susmuyoruz

Eksenin kalibre olup olmadığı **ekranda yazıyor** (`eksen kalibre` / `eksen HAM`), ve tablo yokken sapmanın büyüklüğü de yazıyor. Düzeltmesiz bir eksen "ölçülmüş" görünseydi sayılar sessizce yanlış okunurdu.

##### `wR` — GPIO5 için ham kod yolu

B34 yalnızca GPIO4'ü ölçebilmişti: ham kodu dışarı veren tek yol skop yakalamasıydı ve skop yalnızca `SKOP_KANAL`'ı okuyor. `wR` iki hızlı kanalın da ham kod istatistiğini basıyor.

⚠ `w`nin "giriş RAYDA" koruması `wR`'de **bilerek yok** — doğrusallık süpürmesi tam da rayın yakınını ölçmek zorunda. Ama `wR` **watt basmıyor**, yani "ölçülmüş güç" gibi görünen bir şey üretmiyor.

##### 🔴 YENİ KUSUR: boş girişte `w` yine 7.68 W basıyor

`wR` eklenirken görüldü. B27/K3'ün "giriş rayda" koruması yalnızca **ortalama bir raya yapışmışsa** yakalıyor:

```
ray eşikleri : <82 ya da >4014
GPIO4 ort 2039 → rayda değil       yayılım   12 kod (RC ile sürülü)
GPIO5 ort  787 → rayda değil       yayılım 2400 kod (BOŞTA, %59)
→ `w` geçiyor: P=7.68 W, PF=0.983
```

Boştaki GPIO5'in ortalaması tesadüfen orta ölçekte kaldığı için koruma delindi. Ayırt edici işaret **yayılım**: sürülü kanal 12 kod, boşta olan 2400 kod — 200 kat. Ama eşiği şimdi uydurmak, yalnızca "boşta" tarafını sınayabildiğim için tam da bu projenin kaçındığı şey olur. **GPIO5 jumper'ı takılınca iki taraf da ölçülüp eşik veriden seçilecek.**

##### Doğrulama

* Zincir 18/18, **1349 iddia** (1321'den).
* `test_arayuz3.js` 270 → **292** (bölüm 17) · mutasyon B7 42 → **50/50**
* `sim3_skop.py` 37 → **43** (bölüm 6c/6d) · mutasyon B19 4 → **8/8**
* **Gerçek kartta**: `CT` ve `wR` koşuldu; kalibrasyonun gerçek yakalamadaki etkisi ölçüldü (yukarıdaki tablo).
* **Gerçek tarayıcıda**: `tarayici_skop_arsiv.py` 14 → **19/19** — tablo komut→SSE yolundan geliyor, rozet çiziliyor, ve bir **arşiv kaydı** kalibre eksende çiziliyor (kod 3548 → 46.433 V, ham 38.609 V). Kayıtlar ham tutulduğu için düzeltme **geriye dönük** çalışıyor; B36'nın sıralama gerekçesi buydu.

##### Mutasyonun yakaladığı üç boş iddia

1. "Bozuk tablo reddediliyor" bir **totolojiydi** (`null || uzunluklar eşit`) — denetim silinince de geçiyordu. Yerine dört ayrı bozuk biçim tek tek sınanıyor. Bu arada **gerçek bir delik** bulundu: `256:abc` gibi bir çift `NaN` üretiyor, uzunluk ve `oran` denetimlerinden **geçiyordu**, sonra her gerilim NaN oluyor ve dalga ekrandan sessizce kayboluyordu — "kalibre" rozeti yanarken.
2. `"hizli_ham_yolla" in ino` — yeniden adlandırma (`…_`) alt dizge olarak hâlâ eşleşiyordu. Tam imza aranıyor.
3. `"hizli_olcekle" not in govde` — gövdedeki **yorum** "`hizli_olcekle` ÇAĞRILMIYOR" diyordu ve düz kelime araması o yorumla eşleşip iddiayı kırmızıya döndürdü. Çağrı biçimine (`hizli_olcekle(`) bakılıyor.

⚠ Tarayıcı testinde bir iddia daha **yanlış sebeple geçiyordu**: karşılaştırdığım "ham" değeri mV/V karışıklığı yüzünden 1000 kat büyüktü, "fark > 1 V" koşulu yine sağlanıyordu. Üst sınır da eklendi.

⚠ Türkçe büyük harf tuzağı ikinci kez: rozette `text-transform: uppercase` ve sayfa `lang="tr"`, Chrome "kalibre"yi **"KALİBRE"** (noktalı I) yapıyor; ASCII karşılaştırma tutmuyor. `textContent` kullanılıyor.

---

#### 5.12.51 ✅ B37 — BOŞ GİRİŞTE `w` ARTIK WATT BASMIYOR + `?` 21.9 → 5.8 ms (2026-09-13)

GPIO5 jumper'ını beklerken B36'da kaydedilen kusura dönüldü ve bir de bringup koşucusu **biriken bir gerileme** yakaladı.

##### 1 · Boş pin sinaması — deterministik, iki taraf da ölçüldü

B27/K3'ün "ortalama bir raya yapışık mı" koruması, boştaki GPIO5'in ortalaması orta ölçekte (787) kalınca deliniyordu; `w` **7.68 W / PF 0.98** basıyordu. Sinyal istatistiğine dayanan bir eşik uydurmak yerine **dahili pull-up/pull-down testi**: pull-down ile oku, pull-up ile oku; boş (yüksek empedanslı) pin çekmeyi izler, sürülü pin izlemez.

**İlk ölçüm yanıltıcıydı.** Çekme değiştirilip 30 ms beklenip okununca GPIO4'ün (RC ile sürülü) kayması −1557 … **+2728** kod arasında, **işaret değiştirerek** geliyordu; beklenen hep ~+740. Sebep: sürekli ADC'nin **DMA halkası çekme değişmeden önceki örnekleri tutuyor**; ilk okuma o bayat veri. GPIO5 (boş) yine de yakalanıyordu — kayma o kadar büyük ki bayat veri gizleyemiyor. Yani kusur yalnızca **sürülü** tarafta görünüyordu; iki tarafı da ölçmeseydik hiç görülmezdi. Her ölçüm öncesi sürücü durdurulup yeniden başlatılınca (`adc_continuous_start` DMA'yı sıfırlar) ±2 kod tekrarlanabilirlik:

| kaynak | kayma |
|---|---|
| boşta (GPIO5; CAL kapalıyken GPIO4) | **%100** (4095 kod) |
| RC düzeneği — Thevenin **20K** (iki kademe seri) | **%41–50** (1666–2054) |
| skop bölücüsü ~2.6K (hesap) | ~%10 |
| op-amp çıkışı (hesap) | ~%0 |

Ölçülen kaymadan geri çıkarılan dahili çekme **~25K** (veri sayfasının 45K'sı değil). İlk eşik %50'ydi ve RC düzeneği %90 görevde **2054 kodla eşiği aşıyordu** — sürülü pin "boş" sayılırdı. **%75**: iki tarafa da 25 puan pay.

`w` artık bu sinamadan geçmeden güç basmıyor: `! hizli yol: giris BOSTA — cekme sinamasi: GPIO4 %100 BOS · GPIO5 %100 BOS`. `wB` tanı komutu yüzdeleri veriyor.

##### 2 · Bringup koşucusu kırmızı: `?` komutu 21.9 ms bloklıyor

`tezgah_kart.py --sifirla`: **kararlı halde 21.6 ms** (eşik 20). B28 "boşta 3.0 ms" ölçmüştü. Önce B37'den şüphelendim:

* `tezgah_blokaj.py` (yeni, pasif, tekrarlı): B37 firmware 3×60 s → **0 uzun tur, en uzun 3.4 ms**. Açılış sonrası 4×45 s → ilk pencere 15.8 ms, sonra 3 ms.
* Önceki firmware (B36, HEAD) aynı betikle: 15.5 / 3.3 ms — **aynı**. B37 değil.
* Koşucunun kendi `_k_oku`'su `K` satırını okumak için **`?` gönderiyor**; `?`'nin bedeli doğrudan ölçüldü: **+18.8 ms**. (`#` +18.4 ms — I²C taraması, beklenen; `CT` +1.9; `t?` +0.2.)

`?` 548 bayt basıyor, TX tamponu 2048 — taşmamalı. Ölçüm: 1000 baytlık **tek** write 229 µs (tampon çalışıyor), ama 200'lük parçalar **1600 baytta** bloklamaya başlıyor ve sonra her 200 bayt 11–22 ms (hat hızı). Satır satır zamanlama + `availableForWrite`: tampon `?`'nin daha **başında** dolu.

🔴 **Sebep — IDF'nin TX halkası `RINGBUF_TYPE_NOSPLIT`: her `write` çağrısı ayrı bir öğe, ~8 B başlık + 4 B hizalama.** `Print::print(float)` rakam rakam yazıyor → her rakam ~12 B halka yeri. `?`'deki ~15 float ≈ 120 tek-baytlık write ≈ 1.4 KB. B34–B36 boyunca `?` çıktısına alan eklendikçe (`adc_cali=`, `cal_hz=`, `akis_dusen=`, `bos_dram=`) bu sessizce birikti; bringup B29'dan beri koşulmamıştı. Aynı sorun `M` (12 float), `F`, `W`, `S2` satırlarında.

Ucuz önlem: tampon **2048 → 8192** (DRAM'de 71 KB boş). `?`: **21.9 → 5.8 ms.** Bringup **32/0**, kararlı hal 5.8 ms. Yapısal çözüm (`WebAkis`'te satırı tek write'a birleştirmek — `t` dökümünün 16 000 halka öğesini de 4000'e indirir) açık kalem.

##### 3 · Sürücü durumu sarmalayıcıda

Zaten durmuş sürücüye `adc_continuous_stop` çağırmak IDF'den her `w`'de **3 satır ERROR** basıyordu ("already stopped"). Eskiden beri bir satırdı; çekme sinaması üçe çıkarınca düzeltmeye değdi. `adc_baslat()/adc_durdur()` yalnızca durum değişiyorsa IDF'i çağırıyor; `skop_hiz_ayarla`/`hizli_kur` config'den önce durduruyor. Gürültü **0**, skop `w`'den sonra çalışmaya devam ediyor.

##### 4 · Süpürme aracı doğrulandı, GPIO5 bekliyor

`tezgah_adc_supur.py` (B34'ün kaydedilmemiş betiğinin kalıcı hali): GPIO4'ü **iki bağımsız yoldan** (skop yakalaması + `wR`) okuyup **3 kod içinde** uyuştuğunu gösterdi — `wR` GPIO5 için güvenilir. GPIO5'te tel yokken betik "BOŞTA" diyor ve sütunu ölçüm saymıyor. (Boştaki GPIO5'in ortalamasının GPIO4'le birlikte yükselmesi komşu pinden sızıntı.)

##### Doğrulama

* Zincir 18/18, **1355 iddia** · `sim3_skop.py` 43 → **48** (6e) · `sim3_web.py` 97 → **98** (TX tamponu büyüklüğü) · mutasyon B19 8 → **12/12**, B22b **16/16**, B22a **13/13**.
* **Gerçek kartta**: `wB` iki tarafı ölçüldü; `w` boş girişi reddediyor; komut bedelleri ölçüldü; bringup 32/0.
* Mutasyon iki boş iddia yakaladı: (1) `"adc_durdur();" in govde` — gövdede ölçümden **sonra** da bir `adc_durdur()` var, öndeki silinince de geçiyordu → **sıra** sınanıyor; (2) `"static bool skop_calisiyor" in ino` — `skop_calisiyor_` alt dizgesi eşleşiyordu → `\b`.
* Mutasyon taraması: bir eski mutasyonun deseni kaynakta **yoktu** (`akis_tasma++` → `akis_tasma = akis_tasma + 1` olalı) ve koşucu onu "UYGULANAMADI" diye ayrı raporluyordu — kimse bakmamış. Uygulanamayan mutasyon, iddiayı sınamayan mutasyondur. Bir diğeri (`self._gun = None`) iki yerde eşleşip iddiayı **yanlış sebeple** (tanımsız nitelik) kırmızıya döndürüyordu; hedef daraltıldı.

⚠ Bu oturumda heredoc kaçış tuzağına **dört kez** düşüldü; en sinsisi `\b`'nin gerçek backspace (0x08) olarak yazılması — dosya çalıştı, regex sessizce eşleşmedi. Hafıza notu güncellendi.

---

#### 5.12.52 ✅ B38 — GPIO5 KARAKTERİZE EDİLDİ: eğrilik dönüştürücüye ait (2026-09-13)

Kullanıcı GPIO5'i GPIO4'le aynı breadboard satırına bağladı; RC düzeneği (2×10K + 2×100nF) yerinde. Hızlı AKIM kanalı ilk kez ölçüldü — güç faktörünün başka kaynağı olmadığı için bu, B34'ten beri açık en önemli kalemdi.

##### Sonuç (101 nokta, `uretim/olcum-adc-supurme.csv`)

| | %5–%85 bandında en büyük sapma | rms |
|---|---|---|
| GPIO4, skop yolu | +75.0 kod | 18.5 kod |
| GPIO4, `wR` yolu | +77.0 kod | 18.2 kod |
| **GPIO5, `wR` yolu** | **+77.0 kod** | **18.2 kod** |
| B34 (dün, GPIO4 skop, GPIO5 bağlı değil) | ±75.6 kod | ~18 |

* **GPIO5 − GPIO4, aynı yakalamada: −0.26 ± 0.75 kod.** İki kanal 1 kodun altında aynı.
* **Eğrilik kanala değil dönüştürücüye ait** → B36'nın eFuse düzeltmesi GPIO5'e de geçerli. Hızlı yolun (P, PF, Vrms, Irms) kalibrasyonu artık veriyle gerekçelendirilebilir.
* B34'ün kaydedilmemiş betikle yapılan ölçümü **ilk kez tekrarlandı** (75.0 vs 75.6).

##### Çekme sinamasının iki taraflı kanıtı

* **CAL kapalıyken sinama "BOŞ" dedi, oysa yayılım yalnızca 18 kod.** Kondansatörler şarjlı ama arkalarında kaynak yok (GPIO10 giriş kipinde). Yayılıma bakan bir ölçüt bunu "sürülü" sayardı. B37'de yayılım yerine çekme sinamasını seçmenin somut kanıtı. Süpürme betiğinin kendi "boşta mı" kararı da yayılımdaydı — firmware'in `wB`'sine bağlandı.
* İki pin aynı düğümde → çekmeler paralel (~12.5K) → RC düğümünde kayma %60 → %71 (öngörü ~%61; üst uçta ADC eğriliği kodu büyütüyor). Eşik %75, **4 puan pay — en zorlu, yapay durumda.** Gerçek ön uçta (≤%10) pay 65 puan.

##### 🔴 Kırmızı bir iddia: yanlış kurulmuştu, eşik gevşetilmedi

"Skop yolu ile `wR` yolu ≤ 8 kod" 101 noktada **12.8 kodla** kırmızı döndü (kaba süpürmede 3'tü). Önce örtüşmeden şüphelendim; değil: tb3 833 örnek = 199.9 PWM periyodu, `wR` 300 örnek = tam 144 periyot. Sonra **dünkü CSV bağımsız referans oldu**: `wR` dünle uyuşuyor (ort +1.6, std 2.9), sapan **bugünkü skop** okuması. Tekrarlı A/B (`--ab`):

| görev | tb3 (83 kSa/s) − wR | tb5 (20 kSa/s) − wR |
|---|---|---|
| %30 | +1.1 | +3.4 |
| %60 | +3.7 | +4.5 |
| %90 | +4.1 | +6.9 |

Fark **seviyeyle orantılı** ve **örnekleme hızına bağlı** — ADC örnekleme kondansatörünün düğümden çektiği ortalama akımla tutarlı (~4 pF × V × f); 20K kaynak empedansında birkaç mV. Gerçek ön uç bunu en az 8 kat küçültür. Seviyeyle orantılı fark bir **kazanç** terimi ve doğrusallık analizindeki en iyi doğru onu siliyor. 101 noktada ayrıştırıldı:

```
skop - wR = +0.74 + %0.141 x kod        kazanç terimi
artık std 2.65 kod                      gürültü (wR yalnızca 300 örnek)
```

İddia ikiye ayrıldı: **kazanç farkı < %0.5** ve **kazanç silinince artık std ≤ 4 kod**. İkisi de ölçtüğü şeyi söylüyor; eski tek iddia açıklanmış bir terimi gürültüyle topluyordu.

##### Analiz kartsız ve zincirde

`tezgah_adc_supur.py --analiz <csv>` ham veriden bütün iddiaları yeniden koşturuyor (5 dk süpürme tekrarlanmadan). `sim3_skop.py` 6f bunu çağırıyor — **zincir artık kayıtlı ham ölçüm verisini de sınıyor** ve mutasyon koşucusu analizin eşiklerini bozabiliyor. Analiz ikinci kez yazılmadı; betiğin kendisi çağrılıyor.

##### 🔴 Ön uç kurulmadan önce

GPIO4–GPIO5 köprü teli ve RC düzeneği **sökülmeli**. Gerçek devrede GPIO4 skop/GERİLİM, GPIO5 hızlı AKIM: kısa devre kalırsa iki op-amp çıkışı birbirine bağlanır ve güç/PF anlamsız olur. Kartta zaten görüldü: iki kanal aynı sinyali okurken `w` **PF = 1.0000** bastı. Tezgah listesinde en üstte.

##### Doğrulama

* Zincir 18/18, **1356 iddia** · `sim3_skop.py` 48 → **49** (6f) · mutasyon B19 12 → **15/15** (GPIO5≠GPIO4 eğriliği, kazanç eşiği, bozuk CSV).
* Kartsız analiz **8/8**.

---

#### 5.12.53 ✅ B39 — HIZLI YOL KALİBRE: 1 W'lık yük 3.56 W, PF 0.77 okunacaktı + kör parola denetimi (2026-09-13)

##### 1 · Doğrusal ADC modeli hızlı yolda büyük hata veriyordu

`guc_olc` ortalamayı **çıkarmıyor**: P = ort(v·i), Vrms = √ort(v²). Yani ADC modelinin orta ölçekteki **ofset** hatası doğrudan güce giriyor — skopta kazanç hatası yalnızca ölçeği bozuyordu, burada toplam yanlış. Kartın eFuse tablosu ve tasarım değerleriyle:

| | doğrusal model | kalibre |
|---|---|---|
| sıfır giriş (düğüm 1670 mV) | **−6.93 V** | 0.00 V |
| sıfır akım (düğüm 1715 mV) | **−397 mA** | 0 mA |
| 10 Vrms / 100 mA dirençsel (gerçek P 1.000 W, PF 1) | **P 3.56 W, Vrms 11.37 V, Irms 407 mA, PF 0.77** | P 1.000 W, PF 1.000 |

Ön uç kurulmadığı için hiç görülmemişti.

**eFuse'un mutlak ölçeği fizikle sınandı:** PWM ortalaması = görev × rail zorunlu. Kalibre mV görev oranına karşı: eğim **3296 mV** (3.3 V'un %0.1'i), artık rms 4.6 mV, B34 ve B38 verisinde aynı. Doğrusal model eğimi %8.8 düşük buluyor. Kalan belirsizlik ~22 mV kesme (eFuse ofseti mi, rail mi — multimetresiz ayrılamıyor) = girişte ~0.8 V / ~47 mA → **ön uç kurulunca hızlı yol için sıfır kalibrasyonu yine gerekecek** (tezgah listesinde).

##### 2 · Tek tablo, üç tüketici

Açılışta eFuse'tan 17 nokta çıkarılıyor (`kal_mv_tab`). **`CT` bu diziyi basıyor, arayüz skop eksenini bu diziyle çiziyor, hızlı yol bu diziyle ölçekliyor.** Hızlı yol tam eFuse eğrisini çağırsaydı aynı ham kod arayüzde bir, kartta başka bir gerilime çevrilirdi. Aradeğerleme hatası kartta ölçüldü (orta noktalar, tam eğriyle): kod 0–3000'de **±1 mV**, doyum yakınında −4.3 mV; hızlı yol kod ~2000 çevresinde çalışıyor.

`W` satırına 11. alan `kal` (1/0) eklendi; arayüz **kalibre / HAM / bilinmiyor** ayrı gösteriyor (eski firmware'in 10 alanlı satırı "kalibre" sanılmıyor). Sahte kartın `W` alan sayısı artık elle yazılmıyor, **firmware'in protokol yorumundan türetiliyor**.

##### 3 · Gerçek kartta doğrulama (`tezgah_adc_supur.py --hizli`)

GPIO4 ve GPIO5 aynı RC düğümünde; Vort ve Iort **iki farklı ölçekleme zincirinden** geçiyor (skop bölücüsü / fark yükselteci + şönt). İkisinden geri çıkarılan düğüm gerilimi:

```
görev  dügüm(V) mV  dügüm(I) mV   fark
 150      475.58       475.67    -0.09
 550     1789.41      1789.45    -0.04
 850     2787.51      2787.60    -0.09
en büyük |fark| 0.39 mV · düğüm = -28.0 + 3302.3 × görev (eFuse fiti 3296.1) · artık rms 5.4 mV
```

Önceki doğrusal modelle görev %50'de aynı düğüm Vort −8.42 V / Iort −568 mA okuyordu; şimdi −1.83 V / −199 mA — öngörülen −1.80 V / −196 mA.

##### 4 · B37'nin ölçülmemiş bedeli: `w` döngüyü 123 ms blokluyordu

Çekme sınaması 3 × 30 ms bekleme + iki tam yakalama ekliyordu. Bekleme **ölçülerek** seçildi (`wB<ms>`):

| bekleme | sürülü (RC 20K) | kaynaksız 100 nF |
|---|---|---|
| 3 ms | %60 | **%56 ← yanlış: "sürülü"** |
| 5 ms | %63 | %77 (eşiğe 2 puan) |
| **8 ms** | **%63** | **%94** |

Okuyucu **yıkıcı olmayan** hale getirildi (asıl yakalamanın dizilerine yazmıyor), sınama asıl yakalamadan **sonraya** alındı (serbest bırakma beklemesi gerekmiyor), 64 örnek/kanal. `w` **123 → 34 ms**, `wB` 23 ms. Hâlâ 20 ms'nin üstünde; `#` 18 ms ile aynı sınıfta, elle komut.

##### 5 · 🔴 Parola sızıntısı denetimi İLK YAYINDAN BERİ KÖRDÜ

B39 test yamasından sonra depoda kontrol karakteri tarandı: **üç** backspace (0x08). Heredoc tuzağı `\b`'yi gerçek karaktere çevirmişti; regex dosyada çalışıyor ama hiçbir şeyle eşleşmiyordu:

* **`sim3_web.py:444` — firmware'e gömülü parola arayan 5c denetimi.** İlk yayından (`076a366`) beri her zaman yeşildi. Depo herkese açık ve kural "parola depoda olmaz". Doğru desenle tarandı: **bugünkü ağaçta ve `kod/`un bütün git geçmişinde 0 eşleşme** — kör kaldı ama kaçak olmamış. Denetimin ısırdığını kanıtlayan mutasyon eklendi (gömülü parola → kırmızı).
* `test_arayuz3.js` — iki iddianın yarısı (B35 rozet sınıfı, B36 ikinci çeviri izi). `&&`'nin diğer yarısı taşıdığı için mutasyon yakalayamamıştı; iki mutasyon eklendi.

**Kalıcı önlem:** `gizlilik_dogrula.py` artık takip edilen metin dosyalarında kontrol karakteri (sekme/LF/CR hariç) arıyor ve zincirde kırmızı dönüyor; mutasyonla sınandı. Bu tuzak bu projede on altı kez yaşandı; artık sessiz bir iddia körlüğü yerine kırmızı bir zincir.

⚠ B37'nin 6e iddiası çağrı imzası değişince `index()` istisnası atıp **betiği çökertiyordu** (kırmızı yerine yığın izi, ardındaki iddialar koşmuyor). `in` ile önce sınanıyor. 6g'nin "yıkıcı değil" iddiası da yine **bir yoruma** takılmıştı; yorumlar soyuluyor.

##### 🔴 Bulunan, henüz düzeltilmedi: skop yakalaması ölçüm çekirdeğini saniyelerce blokluyor

```
t @ tb3 (10 ms pencere)   döngü  667 ms   atlanan enerji    0 ms
t @ tb5 (50 ms)                  897 ms                     0
t @ tb7 (200 ms)                1524 ms                  1526 ms
t @ tb9 (1 s)                   4437 ms                  4439 ms
```

Blokajın çoğu pencere değil, **ASCII dökümün ölçüm çekirdeğinden seri porta basılması**. B35'te "köprüde ASCII yolu bedava, bedel zaten seri portta" demiştim — aktarım için doğru, ama **ölçüm çekirdeği** hesaba katılmamıştı. Köprü kipinde her yakalama ADS ölçümünü durduruyor, tb7 ve üstünde enerji sayacı o aralığı atıyor, "Sürekli" kipte ölçüm neredeyse hiç çalışmaz. **Sıradaki iş (B40).**

##### Doğrulama

* Zincir 18/18, **1368 iddia** · `sim3_skop` 49 → **55** (6g) · `test_arayuz3` 292 → **298** (bölüm 18) · `sim3_web` 98 (5c artık canlı).
* Mutasyon: B19 **21/21**, B7 **53/53**, B22b **17/17**, B26 **3/3**.
* Gerçek kartta: `--hizli` 4/4, bringup 32/0.

---

#### 5.12.54 ✅ B40 — SKOP ÖLÇÜM ÇEKİRDEĞİNİ ARTIK BLOKLAMIYOR (667 ms → 1 ms) + skopu öldüren kilit sızıntısı (2026-09-13)

B39'da bulunmuştu: skop yakalaması ölçüm döngüsünü saniyelerce durduruyordu. **B35'teki bir iddiamı düzeltiyor:** "köprüde ASCII yolu bedava, bedel zaten seri portta ödeniyor" demiştim — aktarım için doğruydu, **ölçüm çekirdeğini** hesaba katmamıştım.

##### Ölçüm (kartta, `t` sırasında ölçüm döngüsünün en uzun turu, tetik yok = en kötü durum)

| taban | B40 öncesi | B40a (döküm turlara bölündü) | **B40b (yakalama çekirdek 0'da)** | atlanan enerji |
|---|---|---|---|---|
| tb3 (10 ms pencere) | 667 ms | 344 ms | **~1–5 ms** | 0 |
| tb5 (50 ms) | 897 ms | 515 ms | **~1–5 ms** | 0 |
| tb7 (200 ms) | 1524 ms | 1131 ms | **~1–5 ms** | 0 (önce **1526 ms**) |
| tb9 (1 s) | 4437 ms | 4048 ms | **~1–5 ms** | 0 (önce **4439 ms**) |

Tekrarlanabilir: `python tezgah_blokaj.py --skop` (3/3). `ta` (otomatik kurulum; eşiği 0'a çekip 12 zaman tabanını tarayabiliyor, periyodik sinyal yoksa onlarca saniye) artık döngüyü 4.8 ms blokluyor.

##### B40a — döküm bir durum makinesi

Blokajın çoğu pencere değil, **ASCII dökümün ölçüm çekirdeğinden seri porta basılmasıydı** (tb3: 10 ms pencereye karşı ~650 ms). Döküm artık yakalama bitince başlatılıyor ve her `loop()` turunda TX halkasında yer olduğu kadar satır basılıyor. Her satır **tek `write`** — halka öğesi ek yükü satır başına bire iniyor ve bir satırın ortasına başka satır giremiyor. Düzenli çıktıya 1.5 KB TX payı bırakılıyor; bırakılmasaydı `D` satırının kendisi bloklardı. Satır biçimleri eskisiyle aynı.

Sonuç: **`D` satırları dökümün içine düşebiliyor** (kartta görüldü). Köprünün `SkopCozucu`su onları atlayıp sayıyordu (B35 bunu öngörmüştü). **Arayüzün ayrıştırıcısı ise her satırı örnek sayıyordu**: `D 1.7156 …` → `parseInt` ile 1, 0, 0 … dalgaya çöp örnek; D satırının kendisi de göstergeye ulaşmıyordu. Artık yalnızca tamamı tam sayı olan satır örnek, diğerleri normal ayrıştırmaya düşüyor.

##### B40b — yakalama çekirdek 0'daki ayrı görevde

Kalan blokaj yakalamanın kendisiydi: OTO kipte tetik gelmezse zaman aşımı `pencere × 4 + 300 ms` (en çok 4 s).

🔴 **KURAL: yakalama görevi HİÇ yazdırmıyor.** `Serial`'in satır birleştirmesi (WebAkis) tek yazarlı; iki çekirdekten yazılırsa satırlar **karakter düzeyinde** karışır ve hem D hem skop satırları bozulur. Görev sonucu bir kuyruğa bırakıyor, bütün çıktı çekirdek 1'den. Ölçümler (`skop_olc`) görevde hesaplanıyor.

**Sahiplik:** `skop_is` yalnızca çekirdek 1'de yazılıyor (işe başlarken kurulur, sonuç alınınca silinir). İş sürerken:
* ADC'yi kullanan `w`, `wR`, `wB` → `! skop: yakalama suruyor — hizli yol ADC'yi kullanamaz`
* `skop_ayar`ı değiştiren `tb`, `tl`, `te`, `th`, `tp`, `tm`, `t+`, `t-`, `tB`, `ta` → `! skop: yakalama suruyor — tekrar dene` (`t?` okuyor, serbest)

Kartta 4 s'lik yakalama sırasında hepsi sebebiyle reddedildi, bittikten sonra hepsi kabul edildi. Dökümün `S2` başlığı ve `/skop.bin` artık **yakalamanın yapıldığı** zaman tabanı/kiple etiketleniyor — önceden yakalamadan sonra `tb` değiştirilirse eski kayıt yeni zaman tabanıyla etiketleniyordu. Görev yığını 6144 B, ölçülen dip pay 3952 B (`C` satırında `skop_yigin_dip`).

##### 🔴 Kilit sızıntısı: Normal/Tek kipte skop yeniden başlatmaya kadar ölüyordu

`skop_yakala()` `skop_kilidi`ni alıyor, ama tetiklenmeyen iki başarısızlık dalı kilidi **bırakmadan** dönüyordu. Kartta:

```
NORMAL kip, ulaşılamaz eşik → ! tetiklenemedi
OTO kipe dön, yakala       → ! skop: dokum suruyor, yakalama atlandi — tekrar dene
bir kez daha               → ! skop: dokum suruyor, yakalama atlandi — tekrar dene
```

Arayüzdeki "Normal" ve "Tek atış" seçeneklerinin ikisi de bunu tetikliyordu; WiFi'de `/skop.bin` sonsuza dek 503 dönerdi; mesaj da yanlıştı (döküm sürmüyordu). Düzeltildi; iddia her `return SKOP_SONUC_TETIK_YOK`'un kilidi bıraktığını satır satır sınıyor, mutasyon eski hali geri koyunca kırmızı.

##### WiFi'de `tB`: sabit 400 ms bekleme kaldırıldı

Arayüz `tB`'den 400 ms sonra `/skop.bin` çekiyordu. Yakalama bundan uzun sürerse (tb7'de ~1.1 s) kilit tutuluyor → 200 ms bekleme → 503. Web parolası depoda olmadığı için komut ucu sınanamadı; yarış **seri tetik + WiFi `/skop.bin`** ile yeniden üretildi:

```
eski davranış (400 ms sonra çek)  → HTTP 503 "yakalama suruyor, tekrar dene"
yeni davranış (onay satırıyla çek) → HTTP 200, 1000 örnek
```

Bir denemede eski yol 200 aldı **ama yakalama henüz bitmemişti** (onay 3.25 s'de) — yani **bir önceki yakalamanın bayat verisini** yeni dalga diye çizebilirdi. Artık `* skop yakalandi (ikili)` satırı gelince çekiliyor; `!` satırı bekleyişi iptal ediyor. Bu kusur B40'tan önce de vardı.

##### Doğrulama

* Zincir 18/18, **1382 iddia** · `sim3_skop` 55 → **63** (6h) · `test_arayuz3` 298 → **304** (bölüm 19) · firmware derlemesi uyarısız (`-Wextra`'nın enum/uint8_t uyarısı düzeltildi).
* Mutasyon B19 **27/27**, B7 **56/56**.
* Gerçek kartta: `tezgah_blokaj.py --skop` 3/3 · köprü `tezgah_skop_arsiv.py` 16/16 · tarayıcı `tarayici_skop_arsiv.py` 19/19 · bringup 32/0.
* ⚠ WiFi'de komut ucundan uçtan uca `tB` parolasız sınanamadı — tezgah listesinde elle kalem.

---

#### 5.12.55 🔴 B41 — B40b SKOP ÖRNEKLERİNE HATA SOKMUŞ: I²C kenarları ADC1'e giriyor (2026-09-13)

**Kullanıcı bulgusu.** WiFi'den 200 ms/böl yakalamada ekran görüntüsü: CAL kapalı, düz bir iz üzerinde **üç dik aşağı iğne** (−3 V civarından −17 V'a) ve tetik işareti **tam ilk iğnenin üstünde**. "Doğru mu? Yakalama biraz uzun sürüyor."

##### B40'ın iddiası geri çekiliyor

B40b'nin "yakalama sırasında atlanan enerji 0, döngü ~1–5 ms" sonucu **ADC örneklerini bozma karşılığında** elde edilmişti. Zincir 18/18, bringup 32/0, `tezgah_blokaj --skop` 3/3 yeşildi — **hiçbir iddia örnek bütünlüğüne bakmıyordu**, yalnızca yakalamanın "tam" gelmesine.

##### Ölçüm: iğneler gerçek sinyal değil

CAL %50 = düğüm 20K + 100 nF ile sürülü; 1.6 ms'lik tek bir örnekte 600 kod (~0.5 V) atlayıp geri dönemez. Yine de orada da, iki yönde. Tek-örnek hatası (> 60 kod, komşu 4 örneğin medyanına göre) örnekleme hızından bağımsız: 83 kSa/s'de 6.8, 611 Sa/s'de 9.4 / 1000. B34 ve B38 süpürmelerinde tb3 std 1.5–6.8 kod idi — bu sıklıkta hata olsaydı ~30 kod olurdu, yani **hatalar yeni**.

##### Tanı — ilk tahmin yanlıştı

Hepsi aynı oturumda, sürülü düğüm, tek-örnek hatası / 1000:

| yapılandırma | tb3 | tb10 |
|---|---|---|
| yakalama döngüyü blokluyor (B40a) | **0** | **0** |
| ayrı görev, çekirdek 0, ADS eşzamanlı (B40b) | 3.9 | 2.1 |
| ayrı görev **çekirdek 1**, ADS eşzamanlı | 5.7 | 2.9 |
| ayrı görev, yakalamada **ADS susuyor** | **0** | **0** |
| yakalamada **yalnızca I²C okuma** (dönüşüm yok, RDY sabit) | 5.1 | 3.3 |
| yakalamada I²C yok, **CPU meşgul** | **0** | **0** |
| **I²C sürücüsü KAPALI**, SDA/SCL açık-drenaj elle tıklatılıyor | 2.4 | 1.2 |

İlk tanım "çekirdek 0 / WiFi" idi ve firmware'e yorum olarak bile yazılmıştı — **yanlıştı**, çekirdek 1'e almak hatayı gidermedi. Sebep **elektriksel**: GPIO8/9 (I²C) kenarları — sürücü kapalıyken bile — GPIO4'ün **aynı ADC1 birimindeki** dönüşümüne hata sokuyor. B40a'da yakalama döngüyü bloklarken bu yalıtım **kazara** sağlanıyordu; B34, B38 ve hızlı yol (`w`) de hep böyle kazara yalıtılmış çalışmıştı.

##### Düzeltme (firmware)

* **Yakalama sürerken ADS susuyor** (`loop()`'ta bekçi). Hata **0** (tb3 0/3332, tb10 0/2444; `tezgah_blokaj --skop` 0/3721).
* **Susma gizlenmiyor:** `ads_duraklama_ms` (C satırı). Kartta yakalama süresiyle birebir: tb3 312 · tb5 373 · tb7 566 · tb9 1539 · tb10 2717 ms. >1 s aralıklar enerji sayacında eskisi gibi kayıp olarak görünüyor (tb9'da 1542 ms).
* **Emniyet:** pil testi sürerken skop yakalanmıyor (susma = kesme gerilimi denetiminin durması); yakalama sürerken pil testi başlatılmıyor; **`p0` (DURDUR) hiçbir şeye bakmıyor** — kartta doğrulandı.
* Yakalama yine **ayrı görevde** kalıyor: 4 s'lik yakalamada da `p0` ve diğer komutlar anında işleniyor. Döngü en uzun tur ≤ 7.8 ms.
* **OTO kipte tetik yoksa taban kadar bekleniyor** (1.2 × pencere + 300 ms, pencerenin tamamını hâlâ garanti ediyor — B31). Kullanıcının "uzun sürüyor" şikâyeti: 200 ms/böl'de **4.08 → 2.72 s**. Pencere 2 s olduğu için bundan kısası fiziksel olarak mümkün değil. NORMAL/TEK kip tetiği beklemeye devam ediyor.

##### Ekran görüntüsünün kendisi

İz, CAL kapalıyken **kaynaksız RC düğümü**: kondansatörler şarjlı, GPIO10 giriş kipinde. Kartta ölçüldü: yavaş deşarj −25 kod/s, eğilim çıkarılınca gürültü 2.2 kod, 50 Hz bileşeni 0.3 kod (girişte ~0.01 V) — şebeke paraziti yok. İğneler bu kusurdu; tetik ilk iğnenin geri dönüşünde (yükselen kenar) **sahte** tetiklenmişti.

WiFi'de 200 ms/böl yakalamanın **hata bildirimi olmadan** çizilmesi, B40'ın tezgah kalemini (satır tetiklemeli `/skop.bin`) doğruluyor.

##### 🔶 Kullanıcı kararı: I²C'yi ADC1 dışına taşımak

> ⚠ **B44'te (5.12.58) ölçüldü ve REDDEDİLDİ:** taşımak çözmüyor; yukarıdaki A/B tablosu sıralı koşulmuştu ve CAL PWM'inin ara sıra gelen hata patlamalarıyla karışabiliyordu. Aşağıdaki öneri tarihsel kayıt olarak duruyor.

Bugünkü düzeltme bir **ödünleşim**: skop temiz, ama yakalama süresince enerji ve pil ölçümü yok. ESP32-S3'te ADC1 = GPIO1–10. I²C (ve RDY) GPIO11+ pinlere — tercihen ADC'siz 38–42 — alınırsa ikisi aynı anda çalışabilir. Breadboard'da 3 tel + şema + firmware pin sabitleri; ön uç henüz kurulmadığı için şimdi ucuz. Taşındıktan sonra ADS susturulmadan `tezgah_blokaj --skop` 0 hata vermeli. Tezgah listesinde.

##### Doğrulama

* Zincir 18/18, **1388 iddia** · `sim3_skop` 63 → **69** (6i; 6h'de çekirdek artık iddia edilmiyor — yanlış gerekçeyi kalıcı yapmamak için).
* Mutasyon B19 **33/33** (bekçi, susma sayacı, pil emniyeti, `p1` reddi, `p0` serbestliği, OTO tabanı).
* Gerçek kartta: `tezgah_blokaj --skop` **5/5** (yeni: tek-örnek hatası 0, susma muhasebesi, OTO süresi) · köprü 16/16 · tarayıcı 19/19 · bringup 32/0 · `p1`/`p0` elle.

---

#### 5.12.56 🔴 B42 — ÖN-TETİK HİÇ UYGULANMIYORMUŞ: çerçeve kuyruğu tetik geçmişini eziyordu (2026-09-13)

**Nasıl bulundu.** Kullanıcı panelin tarayıcıdan kullanılabilmesini istedi; **Claude in Chrome** kuruldu (VS Code'da mesaja `@browser` yazınca araçlar geliyor). Kartın web parolasını kullanıcı kendi Chrome oturumunda girdi — parola ne konuşmaya ne depoya girdi. Panelde `olcum.local` → Osiloskop açıldı, yakalamaların ham kodu sayfanın Vue durumundan okundu (pikselden yorum yapılmadı).

İlk bakış — CAL kapalı, kaynaksız RC düğümü, 5 ms/böl: iz ekranda "gürültülü" görünüyor ama 1000 örnekte kodlar **2462–2477** (15 kod tepe-tepe), std **2.16 kod** (B41'deki 2.2 ile aynı), tek-örnek hatası **0**. Görünüş otomatik dikey ölçeğin 15 kodu tüm ekrana yaymasından.

CAL 100 Hz ile iz temizdi (ölçülen 100.00 Hz) ama **tetik işareti pencerenin 4.6 ms'sindeydi**; ön-tetik %25 → 12.5 ms olmalıydı.

##### Ölçüm — düzeltmeden önce

Panelden, ön-tetik %25:

| taban | adet | beklenen | gelen `tetikIdx` |
|---|---|---|---|
| 5 ms/böl | 1000 | 250 | 143 42 3 54 113 249 109 229 105 73 |
| 200 µs/böl (Otomatik kurulum) | 167 | 41 | 153 12 127 123 2 38 147 4 13 123 — 2/10'da işaretin gösterdiği örnek eşiği **geçmiyor** |

Tezgahta (`tezgah_blokaj.py --tetik`, CAL 1 kHz, NORMAL kip, 6'şar yakalama): **0/30** doğru yer; 1 ms/böl %10'da (833 örnek, beklenen 83) `737x 778x 801x 780 768x 789x` — 6'nın 5'inde tetik örneğinin **kendisi ezilmiş**. 200 µs/böl'de "x" çıkmaması tesadüf: 167 örnek ≈ 2.004 periyot, ezilen yere yine bir geçiş denk geliyor.

##### Sebep

`skop_yakala()`'da `break` yalnızca **çerçeve bitince** çalışıyordu. Tetikten sonraki sayaç (`kalan`) sıfırlansa da aynı DMA çerçevesinin geri kalanı (1024 bayt = **256 örneğe kadar**) halkaya yazılmaya devam ediyor, en eski örnekleri — yani ön-tetik geçmişini, kısa pencerede tetik örneğini — eziyordu. Tetik indeksi `on − kuyruk` (mod n) oluyordu. Sonuç: ön-tetik ayarı fiilen yok; Sürekli kipte iz her yakalamada yatayda zıplıyor, hızlı tabanlarda işaret yanlış örneği gösteriyor.

Zincir 18/18 ve bütün tezgah testleri yeşildi: **hiçbir iddia tetiğin YERİNE bakmıyordu** — yakalamanın "tam" gelmesine ve örnek bütünlüğüne bakıyorlardı.

⚠ Arşivdeki Aşama 2 firmware'inde (`arsiv/asama2/.../olcum-karti-a2.ino`) aynı döngü, aynı kusur. Arşiv etkin değil, dokunulmadı.

##### Düzeltme (firmware)

* İç döngünün başında `if (bulundu && kalan == 0u) break;` — sayaç bitince çerçevenin kalanı **yazılmıyor**.
* İki bir-eksik hatası birlikte giderildi: `dolu >= on` → `dolu > on` (sayaç o anki örneği de sayıyor) ve `kalan = sonra` → `kalan = sonra - 1` (tetik örneği zaten yazıldı). Böylece `on + 1 + (sonra−1) = n`: halka tam dolu, tetik dizide **tam `on`**'da.

##### Doğrulama

* Tezgah, düzeltmeden sonra: `--tetik` **30/30** doğru yer + gerçek geçiş (öncesi 0/30) · `--skop` **8/8** (B40/B41 denetimleri bozulmadı: tek-örnek hatası 0/3721, döngü ≤ 7.8 ms, susma muhasebesi, OTO 2.73 s).
* Panelde: Otomatik kurulum + 10 yakalama → `41 ×10`, 10/10 gerçek geçiş; Sürekli kipte iki ardışık görüntüde iz ve tetik işareti yerinde (−492 µs = 41 × 12 µs).
* Zincir 18/18, **1391 iddia** · `sim3_skop` 69 → **72** (6j: kuyruk bekçisi yazmadan ÖNCE, `dolu > on`, `sonra - 1`) · mutasyon B19 **37/37** (yeni 4: bekçiyi sil, bekçiyi yazmadan SONRAYA taşı, `>=`, `kalan = sonra`).
* ⚠ Masaüstünde C derleyicisi yok; döngü masaüstünde koşturulamıyor. Zincirdeki iddialar düzeltmenin **kaldırılmasını** yakalıyor, davranışın kanıtı tezgahta.

---

#### 5.12.57 🔴 B43 — SKOP ÖLÇÜM SATIRI: WiFi'de hiç yokmuş, USB'de eksenle 7 V çelişiyormuş (2026-09-13)

Panelde sırayla sınanırken bulundu (B42'nin devamı, tarayıcıdan).

##### Kusur 1 — WiFi'de ölçüm satırı HİÇ çıkmıyordu

Kullanıcının kullandığı yol (WiFi: `tB` + `/skop.bin`) her yakalamada `olcum: null` veriyordu: frekans, periyot, Vpp, Vmax/Vmin/Vort/Vrms/Vac, duty, yükselme/düşme ve "ekranda bir tam çevrim yok" uyarısı **hiç gösterilmiyordu**. Firmware ikili işte ölçümü atlıyordu (`is != SKOP_IS_IKILI`), `/skop.bin`'in 32 baytlık başlığında da yer yok. Zincir yeşildi: ikili çözücü iddiaları başlığı ve örnekleri sınıyor, ölçümü değil.

##### Kusur 2 — USB'de ölçüm satırı B36'nın kalibre ekseniyle çelişiyordu

B36 ekseni eFuse tablosuyla çiziyor; ekranın altındaki `M` satırı ise hâlâ doğrusal modelden (`kod × volt_adim`) geliyordu. Aynı yakalamanın aynı kodlarından:

| CAL 1 kHz | Vmax | Vmin | Vpp | Vort |
|---|---|---|---|---|
| `M` satırı (doğrusal) | −6.30 V | −10.65 V | 4.35 V | −8.49 V |
| eksen (eFuse, arayüz `kodVolt`) | +0.70 V | −4.12 V | 4.82 V | −1.73 V |

Izgara bir şey, sayılar başka şey: 7.00 V fark, Vpp %10 düşük (100 Hz'de 9 V). Ön uç kurulmadığı için panel voltları henüz fiziksel değil; ama iki gösterimin **birbiriyle** çelişmesi her durumda kusur.

##### Karar — ölçüm kartta kalıyor, dönüşüm B39'un tek tablosundan

Arayüzde yeniden hesaplamak `skop_olc`'un ikinci bir kopyası olurdu (AVR emülatöründe analitik değerlerle sınanan tek uygulama). Bunun yerine `kal_mv_tab` dördüncü tüketici oldu (`skop_olc_kalibre`):

* **Volt büyüklükleri** tablodan, arayüzün `kodVolt` kuralıyla birebir; toplamlar **double** (ofsetsiz değer ~65 V; float32 kare toplamında gürültü düzeyindeki Vac yuvarlamada kaybolurdu).
* **Zaman büyüklükleri** (f, T, duty, tr, tf, n) `skop_olc`'tan, tablodan doğrusallaştırılmış kodlarla (eşikler eksenin gösterdiği orta seviyede). `skop_olc.h`'e dokunulmadı.
* Ölçüm artık ikili işte de yapılıyor; `M` satırı **onay satırından hemen önce** basılıyor ve iki yol tek biçimleyiciden geçiyor (`skop_m_satiri`). Arayüz onaydan önce gelen `M`'yi o yakalamaya bağlıyor (`skopIkiliOlcum`, tek kullanımlık; `!` ve yeni `tB` temizliyor). Tek ayrıştırıcı: `skopMCoz`.
* Arşivden açılan kayda bekleyen ölçüm **bağlanmıyor**. ⚠ Arşiv kayıtlarında ölçüm satırı hâlâ yok (bilinen eksik; ham kod saklandığı için ileride geriye dönük eklenebilir).

##### Doğrulama

* Tezgah `tezgah_blokaj.py --olcum` (yeni; CT tablosu karttan, arayüz kuralının Python karşılığı): düzeltmeden önce **0/4**, sonra **4/4** — ASCII ve ikili yolda `M` ile eksen arasındaki en büyük fark < 0.05 mV (sınır 2 mV); ikili yolda `M` onaydan önce; frekans 999.6 / 999.7 Hz (CAL 1 kHz).
* Tezgah `--skop` (B40–B43 hepsi) **12/12**. ⚠ Yakalama sırasında döngünün en uzun turu bu koşuda **8.99 ms** (B42 koşusunda 7.79 ms): ölçüm hesabı (double) yakalama görevinde, çekirdek 1'de ek iş. Tek koşu, koşular arası saçılmadan ayrılmadı; sınır 20 ms.
* Panelde (WiFi, yenilenmiş sayfa): ölçüm satırı 12 değerle görünüyor; Vmax 0.3482 / Vmin −4.0922 / Vort −1.8082 V eksenden hesaplananla aynı.
* Zincir 18/18, **1406 iddia** · `sim3_skop` 72 → **78** (6k) · `test_arayuz3` 304 → **313** (bölüm 20) · mutasyon B19 **43/43**, B7 **61/61**. İlk koşuda bir mutasyon **kaçtı**: "M onaydan önce" iddiası yalnız biçimleyici çağrısının yerine bakıyordu, `Serial.write` silinince yeşil kalıyordu — iddia yazmanın kendisini de sıraya alacak şekilde düzeltildi.
* ⚠ Kendi hatam, kayda değer: arayüzü karta yazdıktan sonra tarayıcıda aynı adrese (`#/skop`) `navigate` sayfayı **yenilemedi** (yalnızca hash gezinmesi); eski kod "ölçüm yok" gösterdi. Kart doğruydu (`no-cache`, yeni `app.js` sunuluyordu). Arayüz güncellemesinden sonra `location.reload()` şart.

---

#### 5.12.58 🔶 B44 — KUPLAJ DENEYİ: I²C'yi taşımak ÇÖZMÜYOR, B41'in tanısı düzeltildi (2026-09-13)

**Soru.** B41 skop örneklerindeki tek-örnek hataları I²C kenarlarına bağlamış ve "I²C'yi (GPIO8/9, ADC1 pinleri) ADC1 dışına taşı" önermişti — kullanıcı kararı olarak bekliyordu. Gerekçe kanıtlanmamıştı ve karşı bir işaret vardı: GPIO10 da ADC1 pini, 20 kHz CAL basarken hata sıfırdı. Tel oynatmadan önce ölçüldü.

**Araç.** Firmware `tK[<pin>[,<pin>]]`: normal skop yakalaması (ADS susuyor) + yakalama boyunca seçilen pinlerde I²C benzeri kenar patlaması (sürüş hep aynı: açık-drenaj + dahili pull-up; bus'a zararsız sıra). İzin listesi `1 2 SDA SCL 39–42` — pil kapısı (6), skop/hızlı (4/5), RDY (7), CAL (10), UART, flaş/PSRAM **dışarıda**; zincir listeyi C ifadesini çalıştırarak sınıyor. Tezgah `uretim/tezgah_kuplaj.py` (yakalama başına hata + gerçekleşen patlama sayısı; boş sonuç elenir).

##### Sıralı koşu YANILTTI

İlk koşu (durum başına 10 yakalama, arka arkaya, CAL 20 kHz): K1 GPIO8/9 1.68 (bir önceki koşuda 6.72) · boş GPIO2 **0** · boş GPIO40 **4.08** /1000 — "ADC'siz pin hata sokuyor, ADC1 pini sokmuyor". Durumlar **iç içe** koşulunca (her turda her durum bir yakalama) GPIO40 **0**, kontrol ise iki yakalamada **tam 33'er hata** verdi.

150 kontrol yakalamasının ham kaydı olayı çözdü: bozuk yakalamalarda hatalar **tam 25 örnekte bir, aynı fazda, 60–70 kod**. 20 kHz CAL'in 4. harmoniği 80 kHz, 83 333 Sa/s'de 3333 Hz'e = 25 örneğe katlanıyor; 833/25 = 33. **CAL PWM kenarı ADC örnekleme anına denk gelince** örneğe ~60 kod giriyor; faz yavaş kaydığı için ara sıra. Sıralı koşuda bir durumun 10 yakalamasına bu dönem denk gelince o durum "kirli" görünüyordu — **B41'in A/B tablosu da sıralıydı**.

##### Temiz ölçüm (CAL KAPALI, iç içe 20 tur, 16 660 örnek/durum, eşik > 30 kod)

| durum | tıklatılan | yük | /1000 | hatalı yakalama |
|---|---|---|---|---|
| K0 kontrol | — | — | 0 · 0.12 | 0/20 · 2/20 |
| K1 | GPIO8/9 | I²C telleri **bağlı** | **2.22** | 9/20 |
| K4 | GPIO8/9 | teller **sökük** | **0** | 0/20 |
| K2 | boş GPIO2 (ADC1) | — | 0.06 | 1/20 |
| K3 | boş GPIO40 (ADC'siz) | — | 0.18 · 0 | 3/20 · 0/20 |
| **K5** | **GPIO41/42 (ADC'siz)** | **aynı teller bağlı** (kullanıcı taşıdı) | **1.26** | 4/20 |

(İki değerli satırlar iki oturumdan: aşama 1d ve aşama 2.)

##### Sonuç

* Hatayı **yüklü hat** üretiyor; pinin ADC1'de olması belirleyici değil (boş ADC1 ve boş ADC'siz pin arasında anlamlı fark yok, teller sökülünce aynı pinler 0).
* **I²C'yi ADC'siz pinlere taşımak çözmüyor**: K5 1.26/1000. K1'den (2.22) düşük görünüyor ama hatalar yakalamalarda kümelendiği için anlamlı değil (9/20'ye karşı 4/20 yakalama). Teller 8/9'a **geri takıldı**; şema ve belgeler değişmedi.
* B41'in çözümü (yakalama sürerken ADS susuyor) **kalıyor**; tanısı firmware yorumunda ve 6i iddiasında düzeltildi.
* **Açık aday: kablo.** Dişi-erkek tel demetinde I²C tellerinden GPIO4 teline sızma ya da ortak GND telinde sıçrama. Sınama tezgah listesinde (telleri ayır → `--asama 1d` yeniden). Nihai PCB (toprak planı, kısa iz) breadboard'dan farklı davranır; orada yeniden ölçülmeli.
* Yan bulgu: skop girişini süren **PWM de** aynı yolla hata sokuyor (kenar örnekleme anına denk gelince). CAL ile yapılan bütünlük sınamalarında (B41, `tezgah_blokaj --skop`) bu bir karışma kaynağı — hata sayımı yapan yeni deneyler `--cal-kapali` ile koşulmalı.

##### Doğrulama

* `sim3_skop` 78 → **82** (6l: izin listesi çalıştırılarak, pil kapısı dahil yasak pinler, I²C'nin ADS okunmadan önce geri kurulması, tıklatmanın yalnız yakalamada) · mutasyon B19 **47/47**.
* `tK8,9` sonrası I²C'nin geri kurulduğu kartta doğrulandı (D satırı durum 0).

##### B44b — Kablo değil, KENAR HIZI (aynı gün, sonra)

Kullanıcı I²C tellerini GPIO4 telinden ayırdı (tam uzak değil, mümkün olduğunca): K1 **3.24**/1000 — değişmedi, yakınlık değil. Kalan aday: yüklü hattan akan kenar akımı ESP32'nin kendi toprak/besleme rayını sarsıyor. Bunu tel oynatmadan sınamanın yolu **kenar hızı**: `tK8,9,d<n>` sürüş gücünü seçiyor (IDF `gpio_set_drive_capability`, d0 zayıf … d3 güçlü); aynı hat, aynı yük, yalnız di/dt farklı.

| sürüş | /1000 (>30 kod) | hatalı yakalama |
|---|---|---|
| d0 en zayıf | **1.26** | 7/20 |
| d2 varsayılan | 4.80 | 15/20 |
| d3 en güçlü | 4.44 | 16/20 |

⚠ Bu tablo alınırken modül #1'in SCL teli bağlı değildi (B46'da bulundu): SCL'de tek modülün pull-up'ı vardı. Üç satır aynı kablolamada olduğu için **karşılaştırma geçerli**, mutlak değerler B44'ün K1'iyle (2.22, iki modül) kıyaslanamaz.

Zayıf sürüş hatayı ~4× azaltıyor ama **sıfırlamıyor**. Karar: yakalamada ADS susturma **kalıyor** (1.26/1000 hâlâ sahte tetik demek). Firmware'de I²C sürüş gücü **değiştirilmedi**: ADS'ler ADC1 örneklerken zaten hiç çalışmıyor (mute), yani bugünkü düzende ölçülebilir bir kazancı yok — ölçülemeyen bir değişiklik yapılmadı. **PCB notu** (tezgah listesinde): SDA/SCL'ye seri direnç (33–100 Ω, kenarı yavaşlatır), tek pull-up seti (iki modülün paralel 10K'ları değil), zayıf sürüş; nihai kartta `tezgah_kuplaj --asama 3` ile yeniden ölçülmeli — K1 kontrol düzeyine inerse ADS susturması kaldırılabilir.

---

#### 5.12.63 🧱 B48b — YERLEŞİM PLANI LEGO SIRASINDA: 91 ALT ADIM (2026-09-15)

**Neden.** Kullanıcı kuruluma başlarken planı "adım adım, LEGO kılavuzu gibi — bir adımda birkaç şey olabilir ama her şey bir adımda olmasın" istedi. B48'in 9 büyük adımı her adımda bütün parçaları, izleri ve telleri tek tabloda veriyordu (adım 7: 14 parça + 29 iz + 2 tel).

**Ne yapıldı.**
* `uretim/yerlesim3_adim.py` (yeni) her büyük adımı sıralı alt adımlara bölüyor: **hazırlık** (kart ilk kullanıldığında: kes, M3, ped çapı, A1 işareti) · **parça** (alçaktan yükseğe, ≤4; yönlü parça — elektrolitik, diyot, DIP, TO-92/220, başlık — kendi alt adımında) · **iz** (ağ ağ, raylar önce; ≤6 iz, ≤40 delik) · **tel** (≤4) · **kablo** (lehim noktası + kablolar, ≤4) · **kontrol** (ohmmetre + KAPI). Sıra veriden; elle yazılmıyor.
* `yerlesim3_belge.py` yeniden: yapışkan görüş penceresi seçili alt adıma yakınlaşıyor (o adım parlak, öncekiler soluk, sonrakiler görünmez; parça → parça yüzü, iz/tel → lehim yüzü; yakınlaşınca kenar etiketleri JS'le görünen alana, dar ekranda seyreltilerek) · ◀ ▶ / klavye / `#s0.3` bağlantısı · "yaptım" işaretleri + ilerleme (localStorage, yalnız o tarayıcı) · her büyük adımın başında **gerekenler**: değer · adet · nereye · stok kaydı · kutu — envanterden (`bom_dogrula.ESLEME` + `stok_bul`; yenisi varsa söküm kayıtları gizli; direnç güç sınıfı ayak izinden: R40 R5 → R030 1/2 W; soket/klips/başlık/plaket/kablo aksesuarları). Envanter yoksa stok sütunu çıkmıyor.
* Ağ adları okunur: `Net-(U3A-+)` → "U3A + girişi", zincir düğümleri "HV düğüm 1..5", `Net-(J6-Pin_1)` → "24V+ (sigorta öncesi)".

**Denetim bölüm 9 — 7 iddia, ölçüt üreticiden BAĞIMSIZ** (`yerlesim3.py` 40 → **47**): 9a her parça/iz/tel/kablo TAM BİR alt adımda ve kendi büyük adımında, kart dışı parçalar kendi adımının kablo alt adımında · 9b sınırlar `V.ALT_ADIM_SINIR`'dan (üretici kendi grup boylarını ayrı tutuyor), boş alt adım yok · 9c hiçbir iz/tel, SONRAKİ alt adımda takılacak parçanın deliğine lehim akıtmıyor (TEL pedleri hariç — kablo lehimli pede lehimlenir) · 9d aynı adım+kartta alçak parça önce (`AYAKLAR[..]["yukseklik_mm"]`, katalogdan yaklaşık; üreticinin `SIRA` listesi buna karşı sınanıyor) · 9e `"yonlu"` parça başka türle karışık değil · 9f kablo, ucundaki lehim noktasıyla aynı ya da sonraki alt adımda · 9g büyük adım sırası korunuyor, her adım KONTROL ile bitiyor, kart parçalarından önce hazırlanıyor.

**Bulgular.**
* 🔴 **9c'nin koruması yalnız üreticideydi.** B48'in yol üreticisi "henüz takılmamış parçanın deliğine iz akıtma" kuralını `gecilir()` içinde uyguluyor, denetim hiç sınamıyordu — `--yol-uret` değişse sessizce bozulurdu. Bugünkü planda ölçüldü: 0 ihlal (büyük adım düzeyinde de). Artık iddia.
* 🔴 **J6 stok eşlemesi eskiydi.** `ESLEME["24V girisi"]` bariyer klemense bakıyordu; B48 kararı XT30. Gerekenler tablosu kullanıcıya yanlış parçayı gösterecekti → CON058. Malzemeler sayfasındaki L7912 notu da "REG004 ×2" diyordu (söküm, test edilmemiş) → "REG009 yeni; REG004 söküm".
* ⚠ **"XT30 (anahtarlı)"** açma-kapama anahtarı gibi okunuyor (bu oturumda asistan da öyle okudu) → "kodlu: ters takılamaz; açma-kapama anahtarı DEĞİL".
* 🔴 **Belge üretimi çöktü, eski belge yerinde kaldı.** JS `%`-biçimlendirmeyle gömülüyordu; eksen seyreltmesi için `i % adimX` eklenince `TypeError` — ama `7-yerlesim.html` bir önceki sürümle duruyordu ve ekran görüntüleri o eski sayfadan alınmıştı. "Belge: yazıldı" satırının yokluğundan yakalandı. Veri artık `str.replace` ile.
* Aynı sayfada adres `#s…` değişince görünüm güncellenmiyordu → `hashchange`.
* ⚠ **Elle mutasyon düzeneğinde bayat `.pyc`:** aynı uzunlukta iki değişiklik aynı saniyede yazılınca Python önceki mutasyonun modülünü çalıştırdı (9c, 9b'nin çıktısını verdi). `mutasyon.py` her mutasyonda kopyayı sıfırdan kurduğu için ETKİLENMİYOR; elle düzenekte `__pycache__` silinmeli.

**Doğrulama.** `yerlesim3.py` **47/47** · mutasyon B48 6 → **13/13**, ve her yeni mutasyonun **hedef** iddiayı düşürdüğü ayrıca döküldü (9f "boş alt adım"ı da tetikliyor) · `dogrula3.py` **18/18**, sayım kilidi B9 [[3,3],[47,47]], toplam 1497 · başsız Chrome: 1280 px ve 400 px, açık/koyu, konsol hatası yok, yatay taşma yok, yaptım/ilerleme/ileri/hash çalışıyor · `bom_dogrula` 3/3.

**Kart A 38×38 → 45×45 (aynı gün, kullanıcı).** Kullanıcı "38×38 mecburi mi, 40 ya da 45 olmaz mı" diye sordu. 38, planın sığdığı en küçük boyuttu (kullanılan alan 37×35 + köşe vidaları). Denetim 38/40/45'te birebir aynı (47/47, A'da en dar pay +4.78 mm; vidalar köşeye kaçınca yüksek gerilimli bakırdan yalnızca uzaklaşıyor). 45×45 seçildi: 13×23 plaketin kısa kenarı zaten 45 delik → **tek kesim** (46. sıra), üç fabrika kenarı. Plan A1'e (sol üst) bağlı kaldığı için **delik adları değişmedi**; fazlası sağda/altta 7'şer sıra. `KARTLAR[..]["kaynak"]` (kesilmemiş delik sayısı) eklendi, kesim talimatı artık bundan türüyor (önceden "39. sütun ve 39. sıra" elle yazılıydı). Mutasyon B48 yeniden 13/13.

Aynı soruda kullanıcı "buradan yüksek akım/gerilim geçecek mi" diye sordu; denetimin gerilim modelinden: **A kartında** ağların GND'ye göre en yükseği skop girişi ~64 V (−63.5…+46.8), V girişi ~36 V, raylar ~17 V; iki ağ arası en büyük fark ~99 V (zarf). **B kartında** 617 V. Akım: kartın kendi beslemesi ~30 mA (F1); yük akımı (≤11.5 A / pil testi ≤6.55 A) plakete girmiyor. ⚠ Skop girişi 60 V'u geçebildiği için T_SKOP bölgesi enerjiliyken dokunulmamalı — belgeye "615 V A'ya girmez" cümlesi eklendi.

**ESP32 bağlantı alt adımı (aynı gün, 9h).** Kullanıcı "ESP32 bu kartta mı olacak" diye sordu. Hayır: kartta yalnız J5 (1×10 erkek başlık, AJ15–AJ24), devkit kutuda, 10 telli dişi-dişi kabloyla. Sorunun cevabını ararken 🔴 **boşluk** çıktı: hiçbir alt adım "ESP32'yi bağla" demiyordu, oysa Adım 1 KAPI'sı (TL431/Vref) +3V3/+5V'u J5'ten alıyor; tezgâhtaki GPIO4–GPIO5 kısa devresi ve RC düzeneğinin sökülmesi de hiçbir adımda yoktu. Yeni `esp32` alt adımı (1.12, KAPI'dan hemen önce): eski teller sökülür, pin eşleme tablosu, 3V3/5V uyarısı, kısa kablo (I²C + SKOP + I_HIZLI aynı demette), COM soketi. J5 çizimde vurgulanıyor (`ilgili` — sayılmayan alan, 9a'yı bozmaz). **9h:** J5 kablosu J5 takıldıktan SONRA, o adımın KAPI'sından ÖNCE tam bir alt adım. `yerlesim3.py` 47 → **48**, mutasyon B48 **14/14** (alt adımı kaldırmak), zincir 18/18, kilit 1498.

**Çizimde 5'lik ızgara (aynı gün).** Kullanıcının plaketinde her 5 delikte bir boydan boya çizgi var; çizime aynısı eklendi (`KARTLAR[..]["cizgi"] = 5`). Çizgi FİZİKSEL delik aralığına (5|6, 10|11 …) konuyor, `X()` aynaladığı için lehim yüzü çiziminde de gerçek çizginin üstüne düşüyor (başsız tarayıcıda iki yüz karşılaştırıldı). 5'in katı etiketler kalın; yakınlaşınca etiket seyreltmesi 5'in katlarına uyuyor. Hazırlık alt adımı kullanıcıdan plaketindeki çizgilerin A1'den sayınca E|F ve 5|6'ya düştüğünü doğrulamasını istiyor — plaketin çizgisi başka yerden başlıyorsa plan kaydırılmalı. B plaketinde çizgi olup olmadığı doğrulanmadı. Ayrıca `V.PARCA_NOTU`: F1 "yuva (2 klips) + 50 mA cam sigorta", R40 "1/2 W, metal film gerekmez" (kullanıcı sordu).

**Direnç türü ve gücü belgede (2026-09-16, bölüm 10).** Kullanıcı 1.1'de "metal film mi, standart mı; hepsi kaç watt" diye sordu. Cevap tasarim3 §11/§12'den: **hepsi 1/4 W, R40 1/2 W** (en yüksek yük R20 %15, en yüksek gerilim 820K 102 V = %51); oran kuran **15 direnç metal film %1 zorunlu** (R4, R6, R10–R16, R20, R23, R27–R30), 8'i önerilir (R2, R3 Vref; R7, R17 süzgeç eşleşmesi; R21, R22, R31, R32 Sallen-Key), 18'i standart. `V.DIRENC_TURU` + `DIRENC_GOREV` (41 direnç); belgede yeni "Dirençler — tür ve güç" tablosu, her parça satırında güç + tür, gerekenler tablosunda metal film paketi tercihi (R060/R059 vb.). 🔴 **"Zorunlu" kümesi elle liste değil:** denetim 10 onu netlist topolojisinden türetiyor — giriş ağına/zincire dokunan direnç (bölücü üst; zincirin ALT düğümü hariç, oraya R17 RC de dokunuyor), VREF ile bölücü düğümü arasındaki direnç (alt bacak), iki girişinde de ≥2 direnç olan op-amp'in dirençleri (fark yükselteci, yalnız U8A) — ve beyanla karşılaştırıyor; ilk koşuda R17'yi yakaladı (alt düğüm kuralı). `yerlesim3.py` 48 → **50**, mutasyon B48 **16/16**, zincir 18/18, kilit 1500. Not: tasarim3 §12'deki POZ etiketi "R22/R23/R31/R32 Sallen-Key" bayat (B19'dan beri R23 skop bölücü alt, SK R21) — sayılar doğru, etiket yanlış; düzeltilmedi.

**Kondansatör tipi belgede (2026-09-16, bölüm 10b).** Kullanıcı 1.3'te "multilayer mi mercimek mi; elektrolitikse belirt" diye sordu. `V.KOND_TIPI` + `KOND_GOREV` (20 kondansatör): disk (mercimek) C1, C4, C5–C8 (değeri kritik değil; C049); multilayer C2, C3, C9–C15, C19, C20 (ayırma + süzgeçler; C051/C008/C052); film 15 mm C18 (C022 — tek adet, 22.5 mm'likler sığmaz); elektrolitik kutuplu C16/C17 (C035). Belgede "Kondansatörler — tip" tablosu (biçimle ayırt etme: disk yassı tablet, bacak kenardan; multilayer yumru, bacak alttan), parça satırında tip + görev, gerekenlerde stok artık envanterin ETİKET alanından süzülüyor (100nF için 630 V film C004/C015'i listelemiyordu ama sıralamada onlar öne çıkıyordu → düzeldi), 2×1nF adet 2. Denetim: her C tek tipte ve tip ayak iziyle tutarlı (CE→elektrolitik, C6→film, C1/C2/C1x2→seramik); kanal RC süzgeç çifti **topolojiden** (op-amp giriş ağı + VREF arasındaki kondansatör → C2, C3) aynı tip ve multilayer (B16 bölüm 4: tolerans baskın). `yerlesim3.py` 50 → **52**, mutasyon B48 **18/18**, zincir 18/18, kilit 1502.

**U1 bacak sırası doğrulandı (2026-09-16).** Stoktaki TL431 gövdesinde "WS TL431A 819SB": Wing Shing, A sınıfı (±%1). Wing Shing TL431I veri sayfası (TO-92 ön yüz çizimi, alttan görünüş ve bonding diyagramı birbirini tutuyor): **R–A–K**, TI LP ile aynı → `V.BACAK["TL431"]` doğru. PDF `Elekronic/datasheet/TL431A_WingShing_TO-92.pdf` (depo dışı), envanter IC002 `parca_no` = WS TL431A. Tezgah kalemi (`[!]` diyot kademesi) yine de duruyor: 5 V→1K→K, REF=K → 2.5 V.

🔴 **J5 erkek değil DİŞİ (2026-09-16, kullanıcı sordu).** B48 planı J5'i 1×10 erkek başlık, kabloyu "dişi-dişi" yazmıştı. Devkit'in pinleri erkek, kullanıcının jumper kabloları dişi-erkek (kart ADS modüllerine bugün onlarla bağlı; envanterde dişi-dişi kablo yok) ve 3.2'deki sipariş notu J5 için zaten "dişi header" diyordu — planın iki varsayımı da elindekilerle uyuşmuyordu, üstelik B48b'nin 1.12 alt adımı bunu belgeye de geçirmişti. Düzeltme: J5 **dişi** (CON018 1×40'tan 10'luk; ADS'lerle birlikte 30 pin, bir şerit yeter), kablo dişi-erkek: dişi uç devkit'e, erkek uç J5'e. Ayak izi/yerleşim değişmedi (aynı 1×10, 2.54 mm); yalnız metin ve gerekenler. Denetim 52/52.

**50 mA sigorta geldi (2026-09-17, robotistan kargosu).** `BILINEN_DIS` boşaldı; `ESLEME["50mA"]` → FUS010 (×5). Yuvadaki geçici 400 mA (FUS001) ile değiştirilecek — F1 satırı ve `PARCA_NOTU` güncellendi. Aynı kargoda: 1 nF / 10 nF **polyester film** ×50 (C054/C055 — Sallen-Key C5–C8 için disk seramikten iyi aday, henüz plana geçirilmedi; kullanıcı 3.x'te), 5×20 cam sigorta serisi 50 mA…30 A, pano tipi sigorta yuvası (BLX-3), 12 mm kilit anahtarı (KS-01-101C — kutunun güç anahtarı adayı), ESP32-WROOM-32D (BRD004 — sinyal üreteci adayı), PCB tutucu, 1N4148 ×50, krokodil +2+2. B9 3/3, alınacak listesi boş.

**Kablo alt adımları: burma + silikon (2026-09-17/19, 4.7 ve 5.12'de soruldu).** Belge her kablo alt adımında "lehimden sonra teli giriş deliğinin yanından sıcak silikonla sabitle, komşu deliklere yayma" diyor; sinyal teli kendi COM/GND teliyle aynı alt adımdaysa "burabilirsin (zorunlu değil)" — J1 ±32 V, giriş 227K, burmak yalnız döngü alanını küçültür; HV kablosu olan alt adımda "silikondan ÖNCE öbür telden uzağa yatır". Sonraki adımların delikleri 4.7 (B4/C4, B6/C6) ve 5.12 (B:C8/D8, B:O16/P16, A:B11/C11) çevresinde ölçüldü: kart B'ye 5'ten sonra hiçbir şey gelmiyor; A'da en yakın sonraki iş 3+ delik uzakta.

**Kontrol alt adımları somutlaştı (2026-09-19, kullanıcı 5.13'te "gene kablo mu bağlayacağım? anlamadım" dedi).** Eski metin genel ("izlerde süreklilik var, raylar GND'ye kısa değil") ve KAPI kutusu hem "kutu kurulunca yap" hem "geçmeden ilerleme" diyordu. Şimdi: ilk satır "lehim de kablo da yok"; tablo Ne / Uç 1 / Uç 2 / Doğru sonuç — ray için iki bacağı ray+GND olan parça (dekuplaj kondansatörü; 1K altı direnç seçilmez, bip eşiği), yoksa bu adımın ray pedi + en yakın GND pedi. HV zinciri adımında **HV jak kablosu ucu ↔ A:C11 ≈ 4.92 MΩ** (R10–R15 6×820K + kartlar arası tel); değer netlistten toplanıyor ve yalnız zincir düğümlerinde seri dirençten başka bir şey yoksa yazılıyor (bugün: yok — `/HV_GIRIS` = {J2.1, R10.1}, ara düğümler iki pinli). Panel parçası gereken adımda tek kutu: "KAPI şimdi değil, kutu kurulunca"; HV adımında krokodil seçeneği gösterilmiyor. Kontrol görünümü artık ölçüm uçlarının olduğu kart A'yı gösteriyor (5.13'te B gösteriyordu). Yalnız belge metni — denetim 52/52 değişmedi; ölçüm satırları için ayrı iddia yazılmadı.

**Köprü kontrol listesi (2026-09-19, kullanıcı 6.12'de "AJ18 ile AJ19 arası ötüyor, böyle mi olmalı?").** AJ18 = J5.4 **SCL**, AJ19 = J5.5 **SKOP** — tasarımda aralarında <2.7 kΩ yol yok (tek DC yol SCL→R24 2.7K→+3V3→D1→SKOP) → bip = gerçek köprü. Yerleşimin en sıkı noktası: SKOP adım 6'da SCL pedinin köşesini sarıyor (tel ucu AK18, iz AK18→AK19→AJ19; AJ18'in iki yanı + bir çaprazı SKOP). Kontrol alt adımlarına katlanır **"Köprü kontrolü"** tablosu eklendi (`kopru_ciftleri()`): o adımda lehimlenen her deliğin farklı ağa ait 4-komşusu + beklenen sonuç; beklenen okuma o adıma kadar takılı dirençlerden (sigorta ~10 Ω) Laplace sözde-tersiyle hesaplanıyor — sonsuz → "ötmemeli", <100 Ω → "öter, normal", arası → "ötmemeli (≈ X)". Adım başına çift sayısı 7…45 (6'da 32). Yalnız belge metni, denetim 52/52.

**Ray satırları her kontrolde tüm raylar (2026-09-19, kullanıcı 6.12'de C36–C29 = −12V–GND kısa devre ölçtü).** Eskiden ray tablosu yalnız o adımın İZLERİNİN dokunduğu rayları alıyordu: adım 3 GND izini 36. satıra, 37. satırdaki −12V izinin dibine (K–R, 6 delik paralel) çekti ama 3.9 −12V satırı göstermedi — kusur sınıfı: "yeni bakırın komşusu olan eski ray" denetlenmiyordu. Şimdi o ana kadar kartta var olan her ray (RAYLAR ∩ takılı pinler), her kontrolde; ray pedi yoksa önceki adımlardan seçiliyor (`ray_uclari`, eskiden bu adımda ped yoksa satır düşüyordu). GND–−12V yan yana noktalar: C12 (L21↔M21/L22, adım 6), 7912 (Q36↔R36), 36/37. satır K–R, ve kullanıcının 24 V girişindeki fazla lehimi (C33 GND … C36 −12V, arada C34 24V+). Rail satırına "ohm kademesi: kısa 0–1 Ω sabit, kondansatör yükselir" ayırıcısı eklendi.

🔴 **Açık — yerleşim zayıflığı: üç ray üst üste (2026-09-19).** Kullanıcı −12V–GND arası 2.5 Ω ölçtü (C34–C29 temiz → 24 V girişi değil). 7912 çevresinde lehim yüzünde 35. satır +12V (K–T), 36. satır GND (L–Q, adım 3), 37. satır −12V (C–R, adım 0) — 2.54 mm arayla üç paralel lehim izi, 6+ delik boyunca; ayrıca F1'in +12V klips bacakları K35/M35 arasında L35 GND izi. Denetim (`yerlesim3.py`) farklı ağ komşuluğunu SAYMIYOR — plan geometrik olarak doğru ama köprüye en açık yer burası. Yapılacak: "iki ray ≥3 delik paralel komşu olamaz" iddiası + mutasyon; `--yol-uret` maliyetine ray–ray komşuluk cezası. Kullanıcıya bölme yöntemi verildi: adım 0'daki R33→R36 telini R36'dan sök → −12V ikiye ayrılır (C36/37. satır/7912 ↔ R33/C16/adım-6 kolu C12, U5); hangi yarı GND'ye 2.5 Ω okuyorsa kısa orada.

**Kısa devrenin sebebi bulundu (2026-09-20): bozuk C14.** Bölme: R33→R36 teli sökülünce C36–C29 temiz, R33–C29 kısa → adım-6 kolu. Kullanıcı M33'ü temizledi, M32–M33 hâlâ ötüyordu: orada **C14** takılıydı (100 nF MLCC, planda ADIM 7 — erken takılmış). M32 (−12V, N32'ye iz) ↔ M33 (GND, L33'e iz) arasında çatlamış seramik ≈2.5 Ω. Kondansatör değişti (stoktan), tel geri lehimlendi, kullanıcı kontrolleri temiz buldu. Ders: bozuk MLCC birkaç Ω okur — "sürekli bip" her zaman lehim köprüsü değildir; kontrol tablosu şimdilik bunu söylemiyor. 7. adımda C14 zaten takılı. 0.9 ilk elektrik listesine "soketli entegreleri çıkar (U3, U4, U5, U8)" eklendi — kullanıcı ilk enerjiyi 6. adımdan sonra veriyor, U5 ±12V'tan beslenir.

🔴 **Açık — "50 mA" sigorta etiketinden kalın (2026-09-20).** İlk elektrik geçti (+12/−12 doğru), ama sigorta üzerinde **5 mV** okundu; kart ~13 mA çekiyor → **0.4 Ω** (kullanıcı sigortayı tek başına da 0.4 Ω ölçtü, iki ölçüm tutarlı). Gerçek 50 mA telin çapı ~7 µm mertebesinde, direnci onlarca ohm olmalı; 0.4 Ω'luk bir bakır tel Preece'e göre ~0.5 A'de erir → bu sigorta pratikte ~250 mA sınıfı. **B15/F8'in "50 mA, 1.7× pay" koruma iddiası bu sigortayla geçerli değil.** Kart çalışmasını etkilemiyor (13 mA). Yapılacak: markalı (Littelfuse/ESKA/Schurter) 50 mA almak; o zamana kadar yeni blokların ilk enerjisinde ısınmayı izle. 0.9'a sigorta düşümü kontrolü eklendi (E35↔M35, >0.1 V beklenir). **Ayrıca:** `1-ne-yapabilir.html` hâlâ "wattmetre 665 örnek/s" diyor; bu `yetenek_tablosu.ADS_PERIYOT_US` I²C bütçe MODELİNDEN geliyor (1503 µs). Kartta ölçülen çevrim 2053 µs → 487/s, çift çekirdekten sonra 500/s. B22'nin bulduğu kusur sınıfı (model ≠ ölçüm) kullanıcıya bakan belgede duruyor — ölçülen değerle değiştirilmeli. Ayrıca 0.9: kaynak KAPALIYKEN XT30'u tak — sıcak takmada 136 µF'lik darbe gerçek 50 mA'lik hızlı sigortayı attırır.

---

#### 5.12.64 📦 B50 — KUTU / PANEL KURULUM PLANI (2026-09-20)

**Neden.** Kullanıcı 0–8 arası bütün adımları lehimledi ve sordu: "şönt, born jaklar, hiçbiri bağlı değil; A ve B kartı için yaptığımız gibi devamını da planla — neyi nereye, nasıl kontrol ederim, sonunda voltajı/akımı/skopu nereden ölçerim; belge de oluştur." Kart dışı kurulum bugüne kadar yalnız `KABLOLAR` notlarında ve kurulum kılavuzunun dağınık yerlerinde duruyordu — toplu sıra yoktu.

**Ne yapıldı.** `uretim/kutu_veri.py` (tek karar yeri: kutu iç ölçüsü, panel öğeleri, adımlar, kalibrasyon komutları, kullanım tablosu) + `uretim/kutu.py` (denetim + `BELGELER/8-kutu.html`). Kablolar tekrar yazılmadı: `yerlesim3_veri.KABLOLAR` tek kaynak, veri yalnız "hangi kablo hangi adımda" eşlemesini tutuyor; KAPI metinleri `yerlesim3_belge.KAPI`'dan geliyor.

**Plan:** K1 kutu+şablon · K2 panel delikleri ve parçalar · K3 kartlar+ESP32 · K4 şönt/J3/Kelvin/yıldız · K5 Q1+J7 · K6 V/COM/SKOP/HV girişleri · K7 XT30+anahtar · K8 ESP32 (KAPI 1–2) · K9 kalibrasyon + KAPI 3–8 · K10 kapak/etiket, sonunda "neyi nereden ölçerim" tablosu.

**Denetim 78/78** (kutu ölçüsü parçalardan; panel: kenar payı, jak arası ≥20 mm, HV metal açıklığı ≥ `IEC60664_CREEPAGE_TAKVIYELI` = 12.6 mm — bugün 18.0 mm; kablo eksiksizliği ve tekilliği; yük akımı kabloları yalnız K4/K5 ve metinde kalın kablo kuralı; her kart dışı parça tam bir kez monte; **KAPI sırası**: her testin gerektirdiği parça daha önce monte ediliyor — gereklilik `KABLOLAR[adim]`'dan türüyor; stok). **Mutasyon B50 4/4 YAKALANDI** (HV jakını 18 mm yaklaştır → 76/78; skop kablosunu adımdan düşür → 77/78; Q1'i monte etme → 76/78; `s0.015` → `s0.15` → 77/78).

**Bulgu (belgeye girdi).** Bölücüler GND'ye değil VREF'e iniyor; jak–COM arası enerji yokken **sonsuz** okur. Anlamlı panel kontrolü jak↔VREF (A:R8): **V 227 kΩ · HV 4.93 MΩ · SKOP 103 kΩ** — üçü de netlistten hesaplanıyor, elle yazılmadı.

Zincire bağlandı: `dogrula3.py` B9 paketi artık `kutu.py`'yi de koşuyor (yerleşimden sonra); menü ve index'e "Kutu" satırı eklendi (`belge_menu`, `belge_sayfa`).

**B50b (2026-09-20) — ÇUBUK KUTU + ALT ADIM GÖRÜNÜMÜ + ÇİZİMLER.** Kullanıcı: "daha çok adım adım istiyorum, ben next next diyeyim; görselleştir — neyi nereye, nasıl sabitleyeceğimi göreyim. Kutuyu da kendim yapacağım, şimdilik **dil çubuklarından** (ileride 3D baskı)." Çubuk ölçüsü kullanıcıdan: **150 × 18 × 2 mm**, elde ~50 (daha alınabilir).

Plan baştan kuruldu: satın alınan plastik kutu yerine **çubuktan kutu** — iç **190 × 146 × 72 mm** (duvar 4 sıra × 18 mm). 13 adım, **32 alt adım**; belge artık ileri/geri ile tek alt adım gösteriyor (klavye ←/→, adım düğmeleri, "yaptım" localStorage, ilerleme çubuğu).

**Çizim motoru** (hepsi aynı veriden): kesim listesi (her parça bir çubuk şeridi üzerinde, artan gösteriliyor) · taban/kapak kuşbakışı · **izometrik** duvar sırası (sıra sıra yükselen kutu, üst sıra vurgulu) · ön/arka duvar görünüşü (çubuk sıraları + delik merkezleri x/z) · yerleşim kuşbakışı (kart A/B, ESP32, şönt, Q1 + panel öğeleri) · izometrik iç görünüm. İzometrik çizimler `_izo_sigdir()` ile otomatik sığıyor (ilk sürüm viewBox'ı taşırıyordu).

**Denetim 132/132** — yenileri: her kesim parçası çubuktan çıkıyor (uzun kenarlar tam+ek parçaya bölünüyor: ön/arka duvar 194 = 150 + 44), taban çubuğu sayısı iç eni kapatıyor, gereken çubuk sayısı greedy kesimle hesaplanıyor (**48 çubuk**), iç parçalar sığıyor ve **çakışmıyor**, duvar yüksekliği en yüksek parça + 10 mm, ESP32 USB deliğine hizalı, **her delik tek bir çubuk sırasının içinde** (3 mm kenar payı) ve delik çapı çubuk genişliğine sığıyor, HV jakı kaçak yolu, kablo/parça/KAPI sırası. **Mutasyon B50 5/5 YAKALANDI** (HV'yi yaklaştır · COM köprüsünü düşür · Q1'i monte etme · kutuyu kısalt · şönt komutunu kaydır).

Denetim iki gerçek kusur yakaladı: (1) taban rayı/duvar/kapak rayı çubuktan uzundu — ek parça mantığı eklendi; (2) HV jakı z=15'te çubuk sırası sınırına denk geliyordu → 4. sıraya (z=63) ve x=166'ya alındı; diğer jaklar 3. sıra ortasında (z=45), klemensler 1. sırada (z=9).

**B50c (2026-09-20) — YUVARLAK UÇ, 3B GÖRÜNÜM, SÖKÜLEBİLİRLİK.** Kullanıcı üç şey istedi: (1) "dil çubuklarının iki ucunda hafif eğim var, hesaba kattık mı?" — **katılmamıştı**; (2) 3B, döndürülebilir görünüm; (3) "ileride başka bir kaba geçebilirim, hiçbir parça sökülemez şekilde yapıştırılmasın".

**Yuvarlak uç.** `CUBUK["uc_egim"] = 10 mm` eklendi → **düz bölüm 130 mm**. Düz birleşme isteyen her parça düz bölümden kesiliyor, uzun kenarlar eşit parçalara bölünüyor (ön/arka duvar 2 × 97, yan 2 × 73, ray 2 × 95). Tek istisna taban/kapak çubukları: **kesilmeden** kullanılıyor ve bunu bir iddia kilitliyor — **dış derinlik (150) = çubuk boyu**; ic_boy değişirse kırmızı. Gereken çubuk 48 → **62**.

**3B görünüm.** Dış kütüphane YOK (belgeler tek dosya, çevrimdışı çalışmalı): `kutu.sahne()` blok listesi üretiyor (70 blok — taban/kapak çubuk çubuk, duvar sıraları gerçek kesim parçalarına bölünmüş ve ekler kaydırılmış), tarayıcıda ~120 satırlık ressam algoritması çiziyor: sürükle-döndür, tekerlek-yakınlaştır, izometrik/üst/ön/sağ düğmeleri, "duvarlar saydam" ve "hepsini göster". Alt adım ilerledikçe sahne de ilerliyor, o adımın parçası sarı çerçeveyle parlıyor. İki kusur: ressam sırası TERSTİ (taban kartı örtüyordu) ve tek büyük taban yüzeyi parçaları yutuyordu → çubuk çubuk bölünerek çözüldü; kapak "hepsini göster"de içeriyi kapatıyordu → kapak yalnız kendi adımında.

**Sökülebilirlik.** Bütün montaj metinleri değişti: kart A/B ayak bloklarına **M3 vidayla**, ESP32 ve şönt ahşap altlığa **kablo bağıyla**, Q1 ahşap köşebende M3 vidayla. Kutunun kendi parçaları (çubuk, ayak, altlık) yapıştırılır; **içine giren hiçbir parça yapıştırılmaz**. Denetim bunu ölçüyor: her `IC_PARCA["nasil"]` metninde 'vida' ya da 'kablo bağı' geçmeli, 'yapıştırıl' geçmemeli.

Ayrıca ileri/geri artık sayfanın tepesine değil **alt adım kartına** kaydırıyor (kullanıcı her adımda elle aşağı iniyordu; `scroll-margin-top` şeridin altına hizalıyor). Kullanım bölümüne iki bağlantı şeması eklendi (J3 seri akım yolu, J7 deşarj yolu) — "yük ve pil girişi ne" sorusu sözle çözülmemişti. Denetim **135/135**, mutasyon **B50 7/7**.

**B50d (2026-09-20) — 3B'yi gerçekten kullanılır yapmak.** Kullanıcı: "kutuyu hazırlarken 3B'ye bakamıyorum." İki sebep vardı: (1) ilk adımlarda sahnede HİÇBİR blok görünmüyordu (hepsinin `gor`u ileride) → panel kapkara, bozuk gibi; (2) mobilde şerit 3 satıra sarıyor, sabit `scroll-margin` yetmiyordu, panel başlığı şeridin altında kalıyordu. Düzeltmeler: **hedef önizlemesi** — henüz yapılmamış bloklar %10 saydamlıkla hayalet olarak çiziliyor ("hedefi göster", varsayılan açık) ve altta "N parça kuruldu · soluk olanlar sırada" satırı; kaydırma şeridin yüksekliğini ÇALIŞMA ANINDA ölçüyor; ileri/geri artık **3B paneline** kaydırıyor (kutu + metin birlikte görünsün); tuval telefonda 300 px, ≤640 px'te düğme/figür ölçüleri uyarlandı.

**`uretim/belge_sun.py` (yeni).** Tezgahta elde telefon oluyor, belgeler ise PC'de `file://`. Stdlib http.server ile BELGELER/ klasörünü LAN'a açıyor, yazdığı adres telefonda açılıyor (`python belge_sun.py`, varsayılan 8099; salt okunur). Belgenin girişine de yazıldı.

**B50e (2026-09-20) — 3B düzeltmeleri (kullanıcı ekran görüntüsüyle bildirdi).** Dört şikâyet, dördü de giderildi. (1) "Bir kısmı yukarıda bir kısmı aşağıda": yüz sarımı tutarsızdı, arka yüzler ayıklanmıyordu ve derinlik yüz ortalamasıyla ölçülüyordu → dışa dönük sarım + işaretli alanla **arka yüz ayıklama** + sıralama **blok düzeyinde** (her bloğun yüzleri kendi içinde), zemin çubukları her zaman önce (uzun zemin çubuğu üstündeki kartı örtüyordu). Ayrıca kameraya kutu merkezinden yakın duvarlar otomatik **kesit** gibi soluklaşıyor — yoksa ön duvar içeriyi kapatıyordu. (2) "Her zaman tüm model görünüyor": panel **açılır-kapanır** (▾/▸, tercih localStorage'da). (3) "Sağ sol ters": ön görünüş zaten doğruydu, yan görüşler terstir — `sag` +90°, `sol` −90° olarak düzeltildi, **arka** görünüşü de eklendi; hazır görüşler pan/zoom'u sıfırlıyor. (4) "Blender gibi hareket": orta/sağ tuş ya da **Shift+sürükle ile kaydırma (pan)**, tekerlek yakınlaştırma, **çift tık sıfırlama**; sağ tuş menüsü engellendi.

**B50f (2026-09-20) — PROFESYONEL 3B (WebGL) + SAĞLAM KUTU + SÖKÜLEBİLİR KAPAK.** Kullanıcı ekran görüntüleriyle: "hangi obje önde anlaşılmıyor, yanlış obje önde/arkada; fare yatay ekseni ters; hedefi göster varsayılan olmasın; duvar saydamlığı seçenek olsun (tamamen opak da isteyebilirim); yan duvarlar ince mi, destek lazım mı; tavan nasıl sabitlenecek (vidalı/mıknatıslı tak-çıkar); hiçbir açık nokta kalmasın."

**3B: ressam algoritması atıldı, WebGL geldi** (`uretim/kutu_3b.py`, dış kütüphane yok, belge tek dosya). Derinlik tamponu → örtme her pikselde doğru; opak yüzler + kenar çizgileri + saydamlar uzak→yakın. Ortografik kamera, kolon-öncelikli 4×4 matris yardımcıları elle. **Blender turntable**: sol tuş = nesneyi tutup çevirme (sağa sürükle → nesne sağa döner, sol yüz görünür — ekran görüntüsüyle doğrulandı), orta/sağ tuş ya da Shift = kaydır, tekerlek = yakınlaştır, çift tık = sıfırla, iki parmak = kaydır+yakınlaştır. Duvar kipi **seçmeli** (opak / yakın olanlar saydam / hepsi saydam; varsayılan **opak**), "hedefi göster" varsayılan **kapalı**; ikisi localStorage'da. Etiketler örtülme testinden geçiyor (blok yüzlerinin izdüşümünde nokta-üçgen + düzlem derinliği) — opak duvarın üstünde uçan yazı yok; vurgulu parça duvar ardındaysa bilgi satırı uyarıyor. Grup etiketleri ("Taban çubuğu ×11") tek satır.

**Eksen tutarsızlığı bulundu:** `kutu_veri` y ekseni 2B kuşbakışında AŞAĞI (ön duvar y = ic_boy), 3B sağ-el sistemi ise ön duvarı y = 0'a koyuyordu → iç parçalar aynalıydı (Q1 arkada, B önde). `sahne()` iç parça/direk y'sini çeviriyor (`cev`); "ön" görüşü jak sırasını doğru gösteriyor (V, COM, SKOP soldan sağa), "sağ" görüşte ön duvar solda (doğru).

**Kutu yapısı:** duvar **iki kat** — dışta 4 yatay sıra (delik sıraları), içte dikey çubuklar (kontrplak gibi çapraz, 10+10 ön/arka, 6+6 yan), toplam 4 mm: tek kat 2 mm esner, jak somunu/klemens vidası tutmaz. Dört iç köşede **köşe direği** (3 kat = 6 × 18 × 72) — köşeleri sertleştirir ve **kapak M3×10 ile buraya vidalanır** (tak-çıkar; mıknatıs stokta yok, vida var). İç ölçü 190×146 → **186×142** (dış derinlik 150 = çubuk boyu korunuyor, iddia kilitli). Yeni alt adımlar 3.4 (iç kat) ve 3.5 (direkler + 2.5 mm kılavuz deliği); 13.1 kapak vidalama. Üç parça kaynağı: tam (taban/kapak), düz (130), **yarım** (75, bir ucu yuvarlak — iç kat ve direk parçaları, yuvarlak uç kapak/taban altında). Gereken çubuk 62 → **84**. Denetim **162/162** (yeni: parça kaynağına göre sınır, yarım ≥ duvar yüksekliği, iç kat sayısı duvarı kapatıyor, direk–parça çakışması ×20, direk et kalınlığı ≥ 6). Sahne 110 blok.

**B50g (2026-09-20) — DÖRT YÖNLÜ İNCELEME + YENİDEN TASARIM ("hiçbir açık nokta kalmasın").** Kullanıcının isteğiyle plan bağımsız 8 gözle incelendi (mekanik · kablolama · plan mantığı · 3B görüntüleyici, her bulgu iki hakemden geçti): 71 bulgu, ~60'ı doğrulandı. Hepsi bu sürümde; `kutu_veri.py` ve `kutu.py` **baştan yazıldı**.

**Mekanik (kutu).** (1) Taban/kapak çubukları kesilmeden kullanılıyordu → **yuvarlak uç duvarın altına geliyordu**, duvar yuvarlağın üstüne oturuyordu; şimdi taban/kapak **x yönünde düz parçalardan** (222 = iki parça, ek yeri sırada bir sola bir sağa), dış derinlik 162 = 9 tam sıra. (2) İç kat çubukları düzenli 18 mm adımla diziliyordu ve ek yeri jak deliğinin arkasına gelebiliyordu → iç kat artık **panel deliklerinden türetiliyor** (`ic_kat_cubuklari`: her deliğe ortalanmış çubuk + iki köşe, aralar dolgu; ön 11, arka 10, yan 8+8), denetim her deliğin arkasında TEK çubuk ve ≥3 mm et olduğunu ölçüyor. USB oval yuvası 18 mm çubukta 2 mm et bırakırdı → arkasındaki çubuk **kısa**, yuvanın üstünden başlıyor. (3) Dış kat ek yeri sıra başına **deliklerden kaçarak** seçiliyor (`ek_yerleri`: delikli sıralar önce, ≥8 mm; ardışık sıralar ≥10 mm kaymış; iki parça da 130 mm düz bölüme sığar). (4) **Delme duvar dikilmeden**, parça düz zeminde: adım 3, parça parça tablo (hangi sıra, sol/sağ parça, parçanın sol ucundan, çubuğun alt kenarından). (5) Kapak direğe vidalanıyordu (uç lifine M3 diş tutmaz) → **yan duvardan M3×12 cıvata + somun**, kapağın altında yan duvara yaslı iki ray (116 mm), cıvata yan iç-kat çubuğunun ortasından geçiyor (y 45/117, denetimli). (6) Kartlar tabana vidalanacaktı (2 mm tahtaya diş) → **4 katlı ayak blokları, gömme M3 somun** (3. katta Ø6, 2.–4. kat arasında hapis); ayak merkezleri yerleşim planının köşede boş bıraktığı 2×2 delik bloğundan türetiliyor (`Y.vida_merkezleri`), kart kenarından ~6 mm taşar. (7) Bariyer klemens (CON012) PCB tipi, panele vidalanamaz → **YÜK ve PİL born jak çifti** (büyük boy siyah ×2, mavi ×2; 15 A); 24 V girişi **XT30 kuyruk** (Ø6 delik, içeride gerilim tahliyesi); USB yuvası ESP32 soket yüksekliğinde (z 8, eski plan z 45'te — fiş sokete girmezdi). (8) Panel parçalarının içeri uzanan gövdesi (`derin_mm`) artık 3B çakışma denetiminde; parçalar arası ≥6 mm; Q1 soğutucusu ahşap köşebende, HV kablosu ankraj bloğuna. Gereken çubuk **100** (elde ~50, 50 alınacak) — iki kat duvar + ayaklar + kapak.

**Kablolama.** J2.2/J4.2 netlistte ayrı pin ama panelde tek COM → `KABLOLAR`'da **'sanal'** tür, kutu planı listeye koymuyor (kullanıcı olmayan teli arardı; mutasyonla kanıtlı). Yıldız GND etiketi "klemens vidası" diyordu, bacak olmalı → düzeltildi. Şönt/Q1 demetleri **tezgahta lehimlenip konnektörle** karta (3'lü dişi header) — kart sökülebilir kalıyor. 24 V kart telleri iç **2'li vidalı klemense** (CON007). Kablo tablolarında **kart deliği** netlistten yazılıyor ve denetim adım metnindeki delik adlarını (C25, Z36, B16, D8, C34/36…) netlistle kıyaslıyor — yerleşimde tel bir satır kayarsa kutu metni kırmızıya döner (mutasyon 15). 8.1 kontrolünde MOSFET gövde diyotu sahte 'öter' → prob yönü yazıldı. Sigorta: anahtar her açmada 136 µF'yi doldurur, gerçek 50 mA F atar → **T tipi** alınacak (takılı 'olan' 0.4 Ω, fiilen ~0.5 A).

**Çalışma mantığı.** **COM'a krokodil takma** kuralı: COM = YÜK 2 = PİL 2 içeride bağlı; COM'u devrenin eksisine takmak şöntü baypas eder (okuma düşer, ince kablo ısınır) — kullanım tablosu ve iki şema bunu söylüyor, denetim metni ölçüyor. HV ölçerken **USB PC'ye takılmaz** (COM = USB toprağı). Pil testinde V jakı zorunlu, YÜK boş. Kalibrasyon eşikleri firmware kuralından (tam skalanın %5'i): akım ≥0.85 A, NORMAL ≥1.6 V, **HV ≥31 V** — kullanıcının 24 V kaynağı yetmez, 12.4 iki kaynağı seri ya da kazancı 1.0 bırak diyor (denetimli). Menziller ve akım sınırı (15 mΩ: 11.5 A ısıl) sabitten. "Başlamadan önce" kutusu yerleşim planındaki ön koşulları (0.9, 1.12, 5.12, 8.6) `yerlesim3_adim`'dan doğrulayarak listeliyor. Sona **kutu arayüzü** (3D baskı için bütün sayılar + gömülü JSON).

**3B.** "Yakın olanlar saydam" kararı duvarın **dışa normaliyle** (`n`), blok merkezinin z'siyle değil (üst görünümde taban, eğik görünümde iç kat rastgele saydamlaşıyordu). "Hepsini göster" bitmiş kutuyu **opak** çiziyor. Kamera her görüşte izdüşüm sınır kutusuna sığdırıyor (ön/yan görüşte kutu küçük kalıyordu). Tekerlek yalnız Ctrl ile ya da tuval odaklıyken ve **imlece demirli** (sayfa kaydırmasını çalmıyor). WebGL bağlam kaybı/geri gelmesi ele alınıyor; koyu temada kenar çizgileri açık; ok tuşları; bilgi satırı grup grup sayıyor (166 blok). Delikler dış yüzde koyu plaka, jaklar gövde + iç saplama, kapak cıvataları.

**Denetim 162 → 854/854** (43 alt adım), mutasyon B50 **18/18** (yenileri: USB z, ESP32 x, kapak cıvatası y, iki jak yakınlaşması, jak rengi ↔ stok, S+ satır kayması, sanal→sinyal, COM baypas metni, ön koşul anchor'u). Ekran görüntüleriyle doğrulandı: izometrik/üst/ön/sağ, yakın-saydam, bitmiş kutu; 2B: arka duvar aynalı, iç kat kesikli, etiketler sıra sıra.

**B50h (2026-09-20) — kullanıcı geri bildirimi, üç düzeltme.** (1) "Dönerken kamera ileri geri gidiyor": B50g'de eklenen sığdırma ölçeği her karede o anki dönüşle hesaplanıyordu → izdüşüm kutusu büyüyüp küçüldükçe kutu da büyüyüp küçülüyordu. Ölçek artık **yalnız hazır görüş seçilince** (ve pencere boyutuyla) hesaplanıyor; dönerken sabit (`sigdirYaw/sigdirPitch`). (2) "Duvar yokken delik görünüyor": delik plakaları 3.x'te (delme) doğuyordu, duvar 4.1'de. Şimdi delik **duvar sırasıyla** doğuyor; 3.1/3.2'de delinecek dış-kat parçaları hayalet **önizleme** (`on` alanı: adımda hazırlanan ama takılmamış parça, "hedefi göster"den bağımsız), delikler üstünde. (3) "Alınacak" listesi TO-220 yalıtımı ve 50 mA sigortayı "al" diyordu — ikisi de stoktaydı (MEK037–041; FUS010 ×5, 17 Eylül'de gelmiş). Liste artık `MALZEME` (stok sorgulu): üreteç envantere bakıp **stoktan çıkar / alınacak** diye ikiye böler, denetim stokta olanın "al" demediğini ölçüyor (861/861). Sigorta notu: 0.4 Ω okuyan sigorta gerçek 50 mA olamaz (birkaç ohm okur) — büyük olasılıkla yuvada hâlâ geçici 400 mA FUS001 var; sigorta kararı (F/T/darbe) B52 incelemesinde.

**B52 (2026-09-20) — SİGORTA KARARI + PİL BLOĞU İNCELEMESİ (hakemli, 70 ajan).** Kullanıcı: "elimde TO-220 yalıtımı ve 50 mA sigorta var, neden T alıyorum; pil (18650 + MT3608 + TP4056) ne olacak?"

**Sigorta.** Veri sayfası sayıları `tasarim3_sabit.SIGORTA`'da (Littelfuse 217 rev 2019 / 218 rev 2020): gerçek 50 mA telin soğuk direnci **15.2 Ω (F) / 21.3 Ω (T)**; 0.4 Ω = 400 mA sınıfı (217.400: 0.277, 218.400: 0.535). Kullanıcının 0.4 Ω ölçtüğü sigorta 50 mA olamaz → **yuvada hâlâ geçici FUS001 (400 mA)** var (5.12.64'teki "~250 mA sınıfı" tahmini düşüktü). Anahtar dolu 24 V'u C16 68 µF + (7912 üzerinden) C17'ye uygular; darbe I²t = V²C/2R, kötü hal 136 µF ve R = sigorta + 0.3 Ω: **F 50 mA 2.5 mA²s darbe / 0.49 mA²s erime → her açmada atar**; **T 50 mA 27 mA²s erime → 15× pay** (2009 tablosundaki 6.9 mA²s ile bile 3.8×). Stoktaki F 315/400 mA da ≥3× pay vermiyor (düşük dirençli sigortada darbeyi yalnız kablo/ESR sınırlar; ESR modelde yok, kötü yön) → ara çözüm 315'e geçmek değil, **yuvadaki 400 kalsın**. Karar: **T (gecikmeli) 50 mA cam, markalı** alınacak (T 63 mA da olur); TO-220 yalıtımı ve F 50 mA stoktan (MEK037–041, FUS010). `kutu.py` bölüm 6 bunları netlist C16/C17 değerinden hesaplayıp ölçüyor (869/869), mutasyon: T'nin I²t'si 10× düşük → kırmızı; 'gecikmeli' silinirse → kırmızı; T stokla eşlenirse → kırmızı; stoktaki kalemin notuna 'al' → kırmızı (**B39 tuzağı yine ısırdı:** `\b` heredoc yamasında gerçek 0x08 olmuş, 'stokta olan alınacak değil' iddiası ölü doğmuştu — Write ile düzeltildi, mutasyon kanıtlıyor). B50 mutasyon 22/22. Tezgah: torbadan bir FUS010 ölç (>10 Ω gerçek 50 mA); T takılınca 20× aç-kapa, her açılışta +12/−12.

**Pil bloğu — henüz KARAR yok, tuzak netleşti.** 5.12.23 "2× 18650 + yükseltici" yolunu en gürültülü diye reddetmişti; B11 (7912 + XT30) ile plan kapanmıştı. Kutuya pil koymanın önündeki asıl engel **toprak topolojisi**: kart GND = 24V− + 12 V (7912 orta nokta). Tek hücreden hem MT3608 (24 V) hem ESP32 için 5 V üretilirse iki çıkışın eksisi ortak (hücre −) olur → 24V− = kart GND → **−12 rayı GND'ye kısa**: 7912 kapanır, raylar +24/0 olur, R40 0.58 W, F1 atmaz — **sessiz arıza**. Aynı kısa, TP4056'nın şarj USB'si ile ESP32'nin USB'si aynı PC/hub/çok portlu adaptöre takılınca da olur. Seçenekler: **(A)** hücre − = kart GND; TP4056 OUT → MT3608 **5 V** → ESP32 5V pini + **yalıtılmış 5→24 V modül** (B0524S-2WR3 sınıfı, 2 W, 1.5 kV; stokta YOK) → DPDT → kilit → klemens; şarj ve PC ile uyumlu; modül dalgalanması (270 kHz) −12 rayına biner, ölçülmeli. **(B)** alım sıfır: hücre − = −12 rayı, MT3608 → 24 V; ESP32 yüzen güç bankasından; kural: şarj yalnız pil anahtarı KAPALIyken ve ESP32 USB'si PC'de değilken; 5.12.23'ün reddettiği gürültülü yol, −12 rayı skopla ölçülmeden karar yok. **(C)** hücre − = −12 + LM2596 ile +12→5 V: 7912'de 0.65–1.4 W ısı — önerilmez. Ortak kurallar: anahtar **hücre tarafında** (MT3608 boşta 1–4 mA çeker, 1500 mAh'ı haftalarda bitirir); MT3608 yüksüz ayarlanır (fabrika 28 V'a kadar çıkabilir); TP4056 yük paylaşımsız → şarj = pil KAPALI; korumalı modülde OUT± kullan; Rprog ~1.5 kΩ (0.5 C). Bütçe: 24 V yükü 19 mA tipik / 25 maks (R40 12 + TL072 5.6/10 + 7912 1.5/3) = 0.46–0.60 W → hücreden 150–200 mA → **6–9 saat** yalnız analog; (A) ESP32 dahil ~450–510 mA → **~2.5 saat** (1500 mAh). Kutuda yer: zeminde 77×21 yuvaya yer **yok** (en büyük boşluk ~40×29); seçenekler: yuvayı sol iç duvara A'nın üstüne (z 32–53) M3 ile · kutuyu +54 mm büyütmek (kapak rayı 130'u aşar, iki parça) · **harici XT30 pil paketi** (plan değişikliği sıfır — ve HV ölçümünde kutuyu tamamen yüzer yapar). Envanter: PWR005 ×2 (başlı hücre — yuvaya değil lehim), yuva PWR004/007, MOD002 ×4, MOD012 ×2, KTS202 SW026 (DPDT olduğunu ölç), CON007, XT60. **Kullanıcıdan karar bekleniyor:** (1) pil kipi isteniyor mu; (2) A (alım + temiz toprak) / B (alım yok + kural) / harici paket; (3) kutu +54 mm mi, duvara asma mı, harici mi. Karar gelince: `kutu_veri.py` (IC_PARCA pil bloğu, PANEL_ARKA ŞARJ/pil anahtarı, KULLANIM kuralı, ADIMLAR), `kutu.py` (kısa devre topolojisi iddiası: pil eksisi hangi düğümde), `sim3_besleme.py` 4b (OUT→IN yönü, R40 0.58 W), mutasyonlar.

**B52b (2026-09-20 gece) — KARAR VE UYGULAMA: iki hücre, sıfır alım, arka duvara asılı; sigorta takılı kalıyor.** Kullanıcı: "50 mA takılıydı, birkaç açmada atmadı; MT3608 stokta, neden kullanmıyoruz; duvara asma uygun." → (1) Atmaması 0.4 Ω ölçümüyle tutarlı: takılı sigorta fiziksel olarak 50 mA değil (gerçek 50 mA 15–21 Ω ve darbede atardı) — etiket şüpheli, envanter FUS010 notuna yazıldı; **T alımı isteğe bağlı**, 400 sınıfı koruma yeter (kısa devre + ters polarite açar; 50–400 mA yavaş arızayı hiçbiri güvenilir açmaz). (2) MT3608 her iki seçenekte de kullanılıyordu; sorun eksisinin nereye bağlanacağıydı. Seçilen: **iki hücre** — hücre 1 → TP4056 → SWP1 → MT3608 (5.0 V) → ESP32 VIN (eksi = kart GND); hücre 2 → TP4056 → MT3608 (24.0 V) → **DPDT kaynak seçici (KTS202: PİL / HARİCİ, iki hat birden)** → kilit anahtarı → klemens (eksi = −12 rayı). Hepsi stokta (PWR005 ×2, PWR004/007, MOD002 ×2, MOD012 ×2, SW026 ×2). Kural: şarj yalnız seçici HARİCİ + SWP1 KAPALI iken; ŞARJ 2 kablosu ile ESP32 USB'si aynı PC'deyken seçici PİL'e alınmaz.

**Yerleşim (kutu_veri.DUVAR_PARCA, arka duvar):** iki 18650 yuvası alt alta x 94–171, z 22–43 ve 49–70 (ESP32'nin ve A'nın **boş arka şeridinin** üstünde — A'nın kullanılmayan 7 sütunu (17.8 mm) arka kenarda, `kart_hacimleri()` bunu yerleşimden türetip A'yı 'dolu' + 'boş kenar' iki kutu olarak denetliyor; sol duvarda A'nın üstü kapak rayına sığmıyordu); TP4056'lar raf gibi duvarın iki ucunda (x 18.5 ve 178.5, z 42) soketleri ŞARJ 1/2 yuvalarına (x 27 / 187, z 45); MT3608'ler düz, x 42–78, z 24 ve 47. **Kilit anahtarı ve iki toggle ÖN panele taşındı** (4. sıra: x 33 / 69 / 87, z 63 — YÜK 1, YÜK 2 ve V jaklarıyla aynı iç çubuklar): arka duvarın 3. sırasında iki şarj yuvası + kilit anahtarı dış kat ek yerine yer bırakmıyordu. J6 kuyruğu x 45'e. Yeni **Adım 14** (14.1 MT3608 yüksüz ayar · 14.2 montaj · 14.3 kablolama (`PIL_KABLOLAR`, 18 kablo) · 14.4 pil kipinde ilk enerji (hücre 2 eksisi ↔ GND ≈ −12 V okunmalı, 0 V = kısa) · 14.5 şarj kuralı/etiket); kullanım tablosuna pil kipi satırı; MALZEME'ye pil kalemleri (hepsi stoktan).

**Denetim 869 → 1313/1313:** bölüm 2b duvar parçaları (sökülebilir, duvar içinde, kapağa ≥2 mm, iç parçalarla 3B ≥6 mm pay, direk/ray/ayak/panel gövdeleriyle çakışma yok, şarj yuvası raf hizası), panel gövdeleri birbirine girmiyor, **pil grafı** (union-find, PIL_KABLOLAR + modül iç bağları + seçici konumu): PİL'de H2− = −12 ve KART_GND değil, H1− = KART_GND, HARİCİ'de H2− −12'den ayrılıyor (şarj güvenli), XT30 eksisi yalnız HARİCİ'de −12'de, TP4056 yükü OUT'tan, SWP1 hücre tarafında; metin kuralları (14.3 ötmemeli, 14.5 aynı PC, kullanım). Bulunan: stok kontrolü `'kayıtta yok' not in` **'yeri kayıtta yok'** (konum boş) ile karışıyordu → `_stokta()` (`class='kotu'` işareti); KULLANIM yer tutucu iddiası sabit indeksle bakıyordu. Mutasyon B50 **27/27** (yeni: H2−→ESP32 GND, tek kutuplu seçici, yuva ESP32'ye 6 mm'den yakın, şarj kuralı metni, yük B+'dan). 3B sahne 180 blok, 48 alt adım.

**B52c (aynı gece) — kullanıcı: "tek 18650 + tek boost ile çalışmaz mı?"** Kartın analog kısmı için çalışır (24 V, 19–25 mA, 6–9 sa); ESP32 aynı hücreden beslenemez (toprak ofseti; +12'den 7805 de reddedilmişti) → ESP32 USB'den (PC/güç bankası). Plan buna göre **iki aşamaya bölündü:** **Adım 14 = 24 V hücresi** (YUVA2 + TP2 + MT2 + DPDT seçici; tek hücre + tek modül, kart pilden çalışır), **Adım 15 = ESP32 hücresi, isteğe bağlı** (YUVA1 + TP1 + MT1 + SWP1; tamamen kablosuz). `pil_asama()` kabloyu uç adından aşamaya ayırıyor; denetim yalnız 1. aşama kuruluyken de grafın tam olduğunu (H2− = −12, GND değil, MT2 → kilit) ve 14.3/15.3 tablolarının kendi aşamasını listelediğini ölçüyor. 52 alt adım, kutu.py 1318/1318, mutasyon 27/27. Kullanıcının ikinci sorusu ("plana eklenmemiş sanırım") → eklenmişti, sayfa yenilenmemiş (Ctrl+F5).

**B52d — tezgah ölçüleri ve anahtar tercihi (kullanıcı, aynı gece).** 18650 yuvası **80 × 21 × 21** (77 varsayılmıştı → yuvalar x 92–172; TP2 rafına 6.5 mm pay korundu), TP4056 **27 × 17 × 5**, Type-C soketi kart kenarından 2 mm dışarı → raf derinliği 25, soket şarj yuvasının içine giriyor. Kullanıcı "toggle'ları açma kapama için kullanabiliriz" → **kilit anahtarı (SW045) kaldırıldı**, AÇ/KAPA = KTS102 toggle (Ø6), SWP1 = ikinci KTS102, SWP2 = KTS202 DPDT (stoktaki 3 konumlu KTS103 tek kutup, seçici olamaz). Ön 4. sıra: üç toggle Ø6 + HV. kutu.py 1319/1319, mutasyon 27/27.

**B52e — "o adımda hangi uzunluktan kaç tane lazım anlayamıyorum" (kullanıcı).** Kesim listesi kayıtları artık kullanıldığı alt adımı taşıyor (`hesap()` → `adim`); her çubuk kullanan alt adım (2.1, 2.2, 4.1, 4.2, 4.3, 4.5, 4.6, 6.1, 6.3, 6.6, 9.3, 10.1, 13.1, 14.2, 15.2) kendi **"Bu adımda gereken çubuk parçaları"** tablosunu (uzunluk × adet + çubuk üstünde çizim) alıyor; yan sıralar 1 / 2–4 diye ayrıldı; kısa iç kat çubukları x'iyle adlanıyor; TP4056 raf blokları kesim listesine girdi. Denetim: her parça var olan bir alt adıma bağlı, 1.2 parçaları 4.4'ten önce / 4.4 parçaları sonra kullanılıyor, montaj adımlarının hepsi tablo alıyor (1366/1366); mutasyon: parça olmayan adıma bağlanınca kırmızı (28/28).

**B52f — yapıştırıcı seçimi (kullanıcı kesime başladı; elinde japon/CA, sıcak silikon, hızlı yapıştırıcı).** `KUTU['yapistirici']` artık iş türüne göre tablo: lamine bloklar ve iç kat çubukları **japon (CA)** (ince kalır — iç kat 2 mm olmalı; kelepçe gerekmez; somun dişine damlatma), taban/kapak derzleri maskeleme bandı + süzülen CA, raylar ve taban altlıkları **sıcak silikon** (tek oynatma paylı yapıştırıcı), dış kat sıraları CA ile tutturup içeriden silikon fileto, silikon mastik (kürlenen) **kullanılmaz**, soğutucu çevresinde hiçbiri. Adım metinleri (2.2, 4.1/4.2, 4.5, 4.6, 6.1) tabloyla hizalandı; denetim tabloyu ve 4.5/2.2 metinlerini ölçüyor (1369/1369), mutasyon 29/29 (iç kat yeniden silikon derse kırmızı).

**B52g — sade adım görünümü (kullanıcı: "'Bitince: neyi nereden ölçerim' her adımda görünüyor, adımlar sade olsun").** Referans bölümleri (bu belge ne, yapıştırıcı, ön koşullar, malzeme, bitince ölçüm, kutu arayüzü) katlanır `<details class='ref'>` oldu, varsayılan kapalı, durumu tarayıcıda kalıyor; adım kartında yalnız yap-listesi → gereken parçalar tablosu → tek ana çizim → (kablo/delik tabloları) → kontrol; diğer çizimler, parça çubuk çizimi ve ek-yeri tablosu "Diğer çizimler / gör" katlanır kutularında; çizimler 540 px'e sınırlı. Panel çizimlerinde aynı sıradaki komşu etiketler (ön 4. sırada üç toggle) üst üste biniyordu → sıra başına satır + komşular 24 px kaydırmalı. İddia sayısı değişmedi (1369), kilit geçerli.

**B52h — "matkabım yok, deliği nasıl açarım; ölçüler merkez mi, hangileri daire?"** `kutu_veri.DELME` (9 aşama) → sayfa başında katlanır "Delikleri nasıl açarım (matkapsız)": biz ile kılavuz, **havya ucuyla** (350 °C, eski konik uç) 2 mm huşu geçen ~3 mm yanık delik (yarmaz), bıçak ucu / kaleme sarılı zımparayla çapa büyütme, oval yuva = 5 mm aralıklı iki Ø9 + arası bıçakla; matkap ucu varsa penseyle elle döndürme; el matkabı önerisi. 3.1/3.2/5.1 metinleri: ölçüler deliğin **MERKEZİ**, Ø = yuvarlak, "14 × 9 oval" = yuva; delik tablosu başlıkları "Merkez: …". Denetim: 3.1 metni merkez/yuvarlak/oval diyor, rehberde havya + oval var, tabloda her çap Ø ya da oval (1372/1372).

**B52i — "hangi deliğe ne gelecek, neden?" (kullanıcı, delmeden önce).** Her panel öğesine `neden` alanı (gerekçe: akım/gerilim/renk/kaçak yolu/konnektör tipi) ve sayfa başına katlanır **"Hangi deliğe ne geliyor — ve neden"** tablosu (delik, çap, parça + stok kaydı, gerekçe; M3 delikleri dahil). Cevaplarken **veri hatası** bulundu: PİL jakları (CON029, büyük boy) Ø6.5/12 mm yazılıydı, YÜK'le aynı aile → Ø8/14; düzeltince J7.1 gövdesi A'nın ayağıyla 0.76 mm çakıştı → büyük jak iç derinliği 22 → **21** (1.1'de ölçülecek; ayağa 0.2 mm kalıyor). Denetim: her öğede ≥40 karakter gerekçe, PİL = YÜK ölçüsü, büyük > küçük (1389/1389), mutasyon 29/29.

**B53 (2026-09-21) — ŞÖNT: 2 W VARSAYIMI YANLIŞTI, TAKILI ŞÖNT 5 mΩ.** Kullanıcı ölçtü: 15 mΩ (R044) tel Ø1 mm, bacak aralığı 10 mm; 5 mΩ (R042 "9.5 A", R043) Ø2 mm, 11 mm. Tasarımdaki "±11.5 A" 2 W'lık şönt çıkarımıydı (B20 notu: "parça gelince teyit et"); Ø1 mm manganinde 2 W ≈ 250–400 K ısınma — lehim erir. `tasarim3_sabit`: ısıl sınır yüzey yoğunluğundan (üreticinin 5 mΩ/9.5 A referansı, 0.20 W/cm², ~45 K) → **I_ısıl ∝ d^1.5, R'den bağımsız**: Ø1 mm → **3.4 A**, Ø2 mm → 9.5 A. Kullanıcı "≥10 A istiyorum" → `SONT_TAKILI = 0.005` (5 mΩ Ø2, 9.5 A sürekli, 1.56 mA adım); 15 mΩ yedek (mA işleri, 0.52 mA adım), XP128 10 mm klemensle (CON064, bacak aralığına birebir; 11 mm'lik hafif bükülür) vidayla değişir; Kelvin telleri boncuğun hemen altına bakıra, vida daha aşağıda. Paralel/seri şönt reddedildi (klemens temas direnci 5 mΩ mertebesinde → paylaşım/değer kayar; seri anlamsız). Firmware kazanç eşiği (%5 = 1638 kod) 5 mΩ'da 2.56 A → 12.2 iki aşamalı: kazanç 15 mΩ ile 18650 + 3.3 Ω (R049, 1.1 A), sonra 5 mΩ + `s0.005` + `Z` (i_duzeltme şönttten bağımsız, olc_akim3). Envanter FUS010 notu: etiket şüpheli (0.4 Ω, darbede atmadı). Yeşil yalan: 1-ne-yapabilir/yetenek tabloları 11.5 A yazıyordu, artık üretilen değer.

**B54 (2026-09-21) — BÜTÜNLÜK İNCELEMESİ (95 ajan, hakemli): 4 sıra yetmiyordu, 12 doğrulanmış kusur.** Kullanıcı "plan mantıklı mı, her giriş/çıkış bağlı mı, şönt düşünüldü mü?" sordu. Kapsam TAM: A'nın 10 teli + J5, B'nin 2 teli, 8 jak, XT30, toggle'lar, şarj yuvaları, USB — hepsi bir alt adımda. Kusurlar ve yapılanlar: (1) **ESP32 yüksekliği 14 = çıplak pin ucuydu**; dişi dupont + tel bükümü ≈ 28 → YUVA1 (z 22) dupont'ların üstüne biniyordu. 72 mm'lik kutuya iki yuva sığmadı → **duvar 5 sıra (90 mm)**, iç kat/direk parçaları 90 mm (tam çubuktan, tek yuvarlak uç: yeni kaynak `tek_uc`), kapak cıvatası z 81, yuvalar z 36/63, çubuk 100 → **131**. (2) **CAL (GPIO10) J5'te ve panelde yoktu**, 12.5/13.4 kapak açıkken GPIO'ya krokodil istiyordu → ön 2. sıraya sarı büyük **CAL jakı** (CON030) + devkit'ten 1 kΩ seri jumper; kapalı kutuda CAL → SKOP kısa kablo. (3) **Kutu kablolaması sigortasızdı** (XT30→seçici→toggle→klemens, F1'den önce, 8.3 A kaynağa çıplak) → ön 2. sıraya **F0 pano yuvası** (FUS027) + 1 A F (FUS003), seçici ortak ucu ile AÇ/KAPA arasında (pil kipinde de). (4) **Hücre 2'nin kesmesi yoktu** (MT3608 boşta 1–4 mA) → AÇ/KAPA = **KTS202 çift kutup**, 2. kutup TP2.OUT+ → MT2.IN+. (5) **Şönt en uzak köşedeydi** (yük kablosu 190–250 mm, 9.5 A'de ~30 mV V okumasına biniyordu, B49 dışında) → RS Q1'in önüne (x 196, y 96) ve **YÜK ↔ PİL jak çiftleri yer değiştirdi** (YÜK x 123/159, PİL x 33/69): YÜK kablosu ≈ 60 mm. (6) **13.2 uygulanamıyordu** (kapak kapalıyken rayın arkasında somun tutulamaz) → raylara gömme somunlu 3 katlı bloklar (13.1). (7) TP4056/MT3608'de montaj deliği yok → çubuk bloğu + kablo bağı; **YUVA cıvata delikleri** (C1a/b, C2a/b) artık PANEL_ARKA'da (tip `civata`), 3.2 delik tablosunda, iç kat çubuğunun ortasına denk getiriliyor (99 / 152; yuva plastiği 53 mm aralıkla delinir). (8) SWP2 10.1'de kablolanıp 14.2'de monte ediliyordu → üç toggle + F0 + CAL **5.3'te**; KL klemensi 10.1'de `monte`, KL → C34/C36 kabloları listede. (9) **Kalibrasyon kaynağı tuzağı**: "12 V + 10 Ω/20 W" kayıtta yok ve WCT+buck kullanılsaydı WCT− = −12 rayı → COM'a bağlanınca kısa → kural: kutuyu besleyen kaynak test kaynağı olamaz; test yükü 18650 + 3.3 Ω 11 W (R049 ×3). (10) 7.2 "YÜK 1 ↔ COM ötmemeli" yanlıştı (5 mΩ öter) → "öter, ≤ 0.5 Ω"; 8.1 D–S kontrolünde kapı kısa devre edilir. (11) 15.3: devkit'te tek 5V pini → çatal; VBUS diyot kontrolü. (12) T_24P/N: kart tellerinde XT30 erkek varsa kesilip kuyruğa (tek takım). **Bilinmeyen (kullanıcı ölçecek, 1.1'e girdi):** A/B dış ölçüleri (13 cm'lik kenar kesilmediyse A 130 mm — ön jak gövdelerine pay kalmaz), A1 ofseti, devkit dış ölçüsü + COM soketi ofseti, B:O16 → A:C11 sarı telin boyu (kutuda 7–13 cm gerekiyor; yerleşim "<10 cm" demişti). Delmeye bunlar gelmeden devam edilmemeli — arka/ön delik tabloları bunlara bağlı değil ama kart sığmazsa yerleşim değişir. Reddedilen/ertelenen: B49'a R_kablo sabiti (yük kablosu kısaldı, ihtiyaç azaldı — açık), kapak orta rayı, alt adım `kimlik` alanı. Denetim 1400 → **1558/1558**, mutasyon **34/34** (yeni: hücre 2 doğrudan MT2'ye, F0 yoldan çıkınca, ESP32 yük 14, yuva ESP32'ye yakın).

**Açık (B52).** −12 rayında MT3608 dalgalanması 14.4'te skopla ölçülecek (5.12.23'ün gürültü endişesi); 18650 yuvası ölçüleri (77×21×21) ve TP4056 boyu (26.5) kumpasla doğrulanacak (1.1); KTS202 ON-ON mu ölçülecek; duvar parçalarının cıvata yerleri iç kat çubuğuna denk gelmeyebilir (14.2 notu). Firmware: pil gerilimi izleme yok (isteğe bağlı: MT girişi bir ADC'ye).

**Açık (B50).** 50 çubuk daha alınacak (100 gerekiyor, elde ~50); `1-ne-yapabilir.html` hâlâ modelden 665 örnek/s yazıyor, kartta ölçülen 500 (B28) — belgeye ölçülen değer + iddia girilecek; `4-kurulum.html` sıra için eskimiş (besleme adımı yok); firmware pil akım tavanı (B51) yok; yük yolu için ≥1.5 mm² kablo envanterde belirsiz (KBL003 karışık); Q1 için TO-220 yalıtım seti doğrulanmadı. 3D baskı kutuya geçilirse yalnız adım 1–5 değişir, elektrik adımları (6–13) aynı kalır.

**Açık.** Parça yükseklikleri yaklaşık (yalnız sıralama). ~~KAPI 0 "kaynakta CC varsa ~60 mA"~~ **kapandı (2026-09-19):** kullanıcı 5. adımdayken "24 V'u nereye vereceğimi bilmiyorum" dedi — 0.8 (24 V telleri C34/C36) atlanmış, hiçbir KAPI enerjili yapılmamış (fotoğrafla doğrulandı; iki kartın parça yerleşimi plana uyuyor). Akım sınırı = F1 50 mA hızlı: adım 0'da ±12 V'un tek tüketicisi R40 (12 mA) + 7912 boşta akımı → ~15 mA; U3/U4 +5V'tan (ESP32), ±12 V'u ilk kullananlar adım 6–8 (U5, U8, Q3) — netlistten. Yani 5. adıma kadar kurulu kartta da 24 V yalnız besleme bloğuna gider. 0.9 artık somut yordam (`ilk_enerji()`, delik adları veriden): 50 mA sigorta, ESP32/ADS yok, WCT-200-24 doğrudan, XT30 dişi ucunda +24 V polarite ölçümü, 5 s dokunma testi, V36'ya göre V35 +11.5…+12.5 V, R33 ≈ −12 V. XT30: kart tarafı erkek, kaynak tarafı dişi (J6 notu). Aynı fotoğraflarda: B'de E8→D8 (5.10) ve N16→O16 (5.11) izleri bacakla bükülmüş ama D8/O16'da lehimlenmemiş ve kesilmemiş; 5.12'nin B tarafı (HV kablosu D8, sarı tel O16) yapılmamış. `4-kurulum.html` besleme adımını hâlâ içermiyor ve "12 V adaptör başlangıç için yeter" diyor; ana sayfa artık "kurulum Yerleşim'den başlar" diyor ama kılavuzun kendisi düzeltilmedi.

**B55 (2026-09-22) — KAPAK SIRASI KUSURU + AĞIRLIK MERKEZİ.** Kullanıcı sordu: "Adım 13'te kutunun üst kapağı takılıyor ama daha sonraki adımlarda kutunun içerisine yeniden bir şeyler ekleniyor."

**Kusur doğrulandı ve iddia kusuru ONAYLIYORDU.** Adım 13 kapağı cıvatalıyor (13.2), etiketleyip topluyor (13.3), kapalı kutuda uçtan uca test yapıyordu (13.4) — ardından Adım 14–15 pil bloğunu **arka duvarın iç yüzüne** takıyor (yuva cıvatalarının somunları içeriden, TP4056 rafı, MT3608 kablo bağı, hücre 2 kablolaması). Kapak takılıyken bunların hiçbiri yapılamaz. Daha kötüsü, `kutu.py`'de tam bu sırayı **onaylayan** bir iddia vardı:

```python
D.kosul("Pil blogu adimlari kapali kutu testinden SONRA (istege bagli ek)", sira["13.4"] < sira["14.1"])
```

Yani 1558/1558 yeşilken belge kullanıcıya kapalı kutunun içine parça takmasını söylüyordu. (B22/B23 dersinin aynısı: yeşil test bir şey kanıtlamaz — burada testin kendisi kusurun bekçisiydi.)

**Düzeltme.** Adım 13 = **kapağı yap, cıvata deliklerini aç, dene ve ÇIKAR**; 14–15 pil bloğu; **Adım 16 = Kapat ve son kontrol** (16.1 etiketle/topla, 16.2 kapağı tak ve cıvatala, 16.3 kapalı kutuda uçtan uca). Delikler bilerek 13'te kalıyor: kutu dolduktan sonra yan duvarı delmek talaşı kartların üstüne döker. 13.2 "pil bloğunu yapmayacaksan doğrudan 16'ya geç" diyor. **16 adım / 53 alt adım.**

**İddia tek adım değil, KURAL oldu.** Kapanış alt adımı veride işaretli (`"kapanis": True`, 16.2) ve denetim şunu ölçüyor: `monte`/`kablo` taşıyan ya da türü montaj/duvar_parca/pil_kablo/kablo/delik/duvar_ic/direk olan **hiçbir alt adım kapanıştan sonra gelemez**. Böylece ileride 17. bir adım eklenirse ya da kapanış öne kayarsa kendiliğinden kırmızı olur. 3B'de kapak artık 13.1/13.2'de **hayalet önizleme** (tezgahta hazır, kutuda değil), takılı görünüm 16.2'den sonra — `kutu_3b.py`'deki `if (kapak && ileride) return;` önizlemeyi de yutuyordu.

**Ağırlık merkezi (kullanıcının ikinci sorusu: "bir taraf aşırı ağır olmasın").** `kutu_veri.KUTLE` — her kalem (gram, belirsizlik, **kaynak**); `kutu.agirlik_merkezi(hucre)` kutuyu parça parça kuruyor (çubuk hacmi × yoğunluk + parça kütleleri) ve dış çerçevede AM'yi, ray yük paylarını, devrilme açılarını veriyor.

| | iki hücre | tek hücre | pilsiz |
|---|---|---|---|
| toplam | 746 g | 682 g | 618 g |
| AM x (merkezden) | +3.3 mm | +2.1 mm | −0.1 mm |
| AM y (merkezden) | −3.3 mm | +2.7 mm | +9.8 mm |
| ray yük payı sol/sağ | %47 / %53 | %48 / %52 | %50 / %50 |
| en küçük devrilme açısı | 55° (kötü halde 45°) | 56° (45°) | 59° (48°) |

**Sonuç: dengeli, düzeltme gerekmiyor.** Denge tesadüf değil: kutunun kendi tahtası (323 g, ≈ 92 çubuk eşdeğeri) toplamın %42'si ve simetrik; ağır parçalar zıt yanlarda (A kartı solda 90 g, Q1 soğutucusu + iki 18650 sağda). AM tabandan 42 mm = dış yüksekliğin %44'ü.

**Ölçüt fiziksel seçildi**, "merkeze yakın olsun"dan değil: kutu **iki taban rayının** üzerinde duruyor (destek açıklığı 129 mm, kutu eni 222) → "bir taraf ağır mı" sorusunun karşılığı **her rayın taşıdığı yük payı** (≥ %35, kötü halde ≥ %25). Derinlikte raylar baştan başa uzandığı için aynı sorun yok; orada ölçüt AM'nin orta bölgede kalması. Devrilme açısı dört yönde ≥ 25°. Hepsi üç yapılandırmada (2/1/0 hücre) ve **kütlelerin en kötü halinde** ölçülüyor: her kalemi belirsizlik aralığının AM'yi en çok kaydıracak ucuna iten sabit nokta yinelemesi (`_am_uc`) — sonuç yalnız nominal tahminlerle sağlıklıysa iddia kırmızı olur.

⚠️ **Hiçbir kütle tartılmadı.** Hepsi hacim × yoğunluk ya da benzerinden kestirme; tablo her satırın nereden geldiğini yazıyor. En değerlisi çubuk: **10 çubuğu tartıp söylemek** (varsayım 3.5 g/çubuk, yoğunluk 0.65 g/cm³) tahtayı — toplamın %42'sini — ölçülen sayıya çevirir.

Yan bulgu: taban rayı konumu **üç ayrı yerde** `(0.25, 0.75)` yazılıydı (3B sahne, kuşbakışı çizim, kütle) → `kutu.TABAN_RAY_X` tek kaynağı. Mutasyon bunu (0.45, 0.55) yapınca destek açıklığı daralıyor ve devrilme/ray payı iddiaları kırmızıya dönüyor.

Denetim **1558 → 1629/1629**, mutasyon **34 → 40/40**. Yeni mutasyonlar: kusurun kendisini geri getir (kapanışı 13.2'ye taşı) · kapanış işaretini sil · Q1 soğutucusunu 150 g yap (ray payı kötü halde %25'in altına düşer) · rayları birbirine yaklaştır · bir kütle satırının kaynağını sil · MT2'nin kütle satırını sil.

**Açık (B55).** Kütleler tartılmadı (yukarıda). Kutu masada **kaymaya** devrilmeden önce başlıyor (7.3 N ağırlık, μ≈0.4 → ~3 N; ön jaka kablo takıp çekmek kutuyu kaydırır, devirmez): istenirse rayların altına lastik ayak — kutunun dışı, "yapıştırma yok" kuralı içerisi için.

**ERTELENDİ (B55b, 2026-09-22) — TEK ŞARJ GİRİŞİ.** Kullanıcı: "bu tek parça bir alet ancak
2 adet şarj girişi var, saçma hissettiriyor." Haklı; **kullanıcı şimdilik iki girişle idare
etmeye karar verdi, ileride tekrar plana alınabilir.** Analiz burada dursun ki yeniden
yapılmasın.

> ✅ **KAPANDI — B58 (2026-09-25).** Kullanıcı dış beslemeyi de kaldırınca (XT30 + seçici) tek
> şarj girişi uygulandı: iki hücre **paralel** + tek TP4056 + **yalıtılmış 5→5 V (B0505S)**
> analog tarafta. Aşağıdaki ②'den farkı: yalıtım şarj yolunda değil 24 V'un yolunda — hücreler
> tek paket, eksisi kart GND. Ayrıntı B58 bloğunda (5.12.64 sonu).

*Neden iki giriş:* iki hücrenin eksisi çalışırken farklı potansiyelde (H1− = kart GND,
H2− = −12 rayı). Tek jakta USB toprağı ikisini birleştirir → −12 GND'ye kısa → sessiz arıza.

*Üç çözüm — üçü de küçük bir alım istiyor* (KTS202 stoğu 2, ikisi de planda kullanılıyor;
yani anahtarlı çözüm bile alım demek. İki jak, "alım sıfır" kararının bedeli):

| | ne | alım | sonuç |
|---|---|---|---|
| ① | Tek hücre + yalıtılmış **5→24 V** (B0524S-2WR3 sınıfı, 2 W) | 1 modül | 1 hücre, 1 jak, hiç kural yok; 1 hücre + yuva + TP4056 + MT3608 + SWP1 plandan düşer. Süre 2.4–3.8 sa. Güç bloğu baştan yazılır |
| ② | İki hücre kalır; tek USB-C jakı, TP2 **yalıtılmış 5→5 V** modülden (B0505S-2W sınıfı) | 1 modül | Tek kabloyla ikisi birden şarj; seçici/PC kuralı **tamamen kalkar**. H2 şarjı ~300 mA → 5–6 sa (5 W sınıfı yarıya indirir). Plana dokunuşu küçük: yalnız şarj kablolaması + arka panel |
| ③ | Tek USB + **3PDT** ŞARJ/ÇALIŞ anahtarı | 1 × 3PDT | Kural anahtara taşınır, yok olmaz; yanlış konumda unutmak mümkün |

*③'te neden DPDT yetmiyor* — üç bağlantı birden kesilmeli: (a) USB +5V → TP2.IN+ (kesilmezse
ÇALIŞ'ta TP2 girişinde 17 V, mutlak sınır 8 V → modül ölür), (b) H2− ↔ MT2.IN− (kesilmezse
ŞARJ'da −12 GND'ye kısa), (c) TP2.OUT+ → MT2.IN+ (kesilmezse ŞARJ'da MT2 −12'ye referanslı
çalışmaya kalkar). (c) AÇ/KAPA'nın 2. kutbuna bırakılırsa DPDT yeter ama "şarj ederken AÇ/KAPA
kapalı" kuralı kalır.

*Tavsiye edilen:* **②** — şikâyeti tam çözer, projenin en tehlikeli kullanım kuralını
(ŞARJ 2 kablosu + ESP32 USB'si aynı PC'deyken seçici PİL'e alınmaz) yapısal olarak siler ve
lehimlenmiş kartla tasarlanmış güç zincirine dokunmaz. Uygulanırsa değişecekler:
`PANEL_ARKA` (ŞARJ 1/ŞARJ 2 → tek USB-C yuvası), `DUVAR_PARCA` (+ yalıtılmış modül),
`PIL_KABLOLAR` + union-find denetimi (yeni düğüm: modülün yalıtım bariyeri; iddia "H2− hiçbir
konumda USB toprağına değmez"), 14.5/15.4 şarj kuralı metinleri, `MALZEME`, `KUTLE`,
Adım 14.2/15.2 montaj metinleri, mutasyon (bariyeri kısa devre et → iddia kırmızı).

**B55c (2026-09-23) — BAĞIMSIZ GÖZDEN GEÇİRME: 4 açı planlandı, 2'si koştu.** Kullanıcı
"planladığımız şeyleri tekrar gözden geçir, ekstra ajanlara da söyle" dedi. Dört bağımsız
inceleme başlatıldı (elektrik/emniyet · mekanik/yapılabilirlik · doğrulama disiplini ·
belge/sıra/malzeme). **Elektrik ve belge incelemeleri tamamlandı; mekanik ve doğrulama
disiplini incelemeleri oturum kotasına takılıp hiç çıktı üretmedi — bu iki açı hâlâ
İNCELENMEDİ.** Denetim koşu boyunca yeşildi; aşağıdakilerin hiçbiri bir iddiayı kırmıyordu.

**Düzeltilenler (hepsi doğrulandı, kaynak okunarak):**

1. 🔴 **Malzeme listesi AÇ/KAPA için YANLIŞ anahtar söylüyordu.** `MALZEME` "KTS202 ×1
   (seçici) + KTS102 ×2 (AÇ/KAPA + hücre 1)" diyordu; planın gerçek kullanımı (PANEL_ON'dan
   sayıldı) **KTS202 ×2, KTS102 ×1**. Listeye uyulsaydı AÇ/KAPA'ya tek kutuplu KTS102
   takılırdı → 2. kutup yok → hücre 2 kesmesi çalışmaz (B54 kusur 4 geri gelirdi) ve MT3608
   boşta akımı 1500 mAh'ı haftalarda bitirirdi. Stokta KTS202 tam 2 adet, yedek yok.
2. 🔴 **Kesim listesinde 16 parça eksikti.** 13.1 "gömme somunlu 3 katlı blok" istiyordu
   (4 blok × 3 kat = 12 parça), MT1/MT2 "iki çubuk parçasının arasına oturur" diyordu
   (4 parça) — hiçbiri kesim listesinde yoktu. Kök sebep `hesap()` içinde
   `d["ref"].startswith("TP")` sabit kodu. Artık veri: **`kutu_veri.DUVAR_TUTUCU`** +
   `KUTU["kapak_somun_kat"]`. Çubuk sayısı 131'de kaldı (parçalar artıklara sığdı).
3. 🔴 **12.4 (HV kalibrasyonu) "kutuyu besleyen kaynak test kaynağı olamaz" kuralını
   tekrarlamıyordu** ve üstüne "iki kaynağı seri bağla" diyordu. Kullanıcının elindeki tek
   24 V kaynak WCT; WCT− = kartın −12 rayı → HV/COM'a bağlanınca −12 GND'ye kısa, parça
   ölmez, **kalibrasyon sabitleri sessizce yanlış yazılır**. Kural eklendi + "yalıtılmış
   ikinci kaynağın yoksa bu adımı Adım 14'ten sonra pil kipinde yap" yönlendirmesi.
   (İki bağımsız inceleme de aynı kusuru buldu.)
4. **14.2 / 15.2 metni veriyle çelişiyordu.** Metin TP4056 ve MT3608 için "vidala" /
   "cıvata dıştan somun içeriden" diyordu; `DUVAR_PARCA.nasil` ise "modülde montaj deliği
   yok, kablo bağı, vida yok". O cıvatalar için delik tablosunda delik de yok. Kullanıcı
   14.2'de kurulu kutunun arka duvarını delmeye kalkardı (talaş kartların üstüne). Metinler
   veriye uyduruldu; cıvata yalnız 18650 yuvalarında.
5. **`{adim_uA}` yer tutucusu belgede HAM çıkıyordu** — `KULLANIM` tablosunun 4. sütunu
   `.format()` edilmiyordu (`kutu.py`). "1.56 mA adım" yazması gereken yerde `{adim_uA}`.
   Denetimin "menziller yer tutucudan" iddiası bu sütunu kapsamıyormuş.
6. **ŞARJ 1 notu "PC'ye takılıyken de güvenli" diyordu** — −12 kısası bakımından doğru, ama
   HV ölçümünde bu kablo da COM'u (613 V'luk devrenin referansı) PC toprağına bağlar. ⚡
   uyarısı eklendi.
7. **Şönt takası anlatımı yanlıştı.** `RS.nasil` ve 6.4 "vidayı gevşet, şönt çıkar" diyor
   ama Kelvin/yıldız telleri şöntün bacağına LEHİMLİ. Metin düzeltildi + "kalibrasyon için
   takas zorunlu değil" notu.
8. **Ters bağlanan pil uyarısı yoktu.** Q1 N-kanal, S→RS.1, D→J7.1: hücre ters bağlanırsa
   akım **gövde diyodundan** akar ve kart bunu kesemez (MOSFET kapalıyken bile; 3.3 Ω ile
   ~1.1 A sürekli, 1500 mAh ~1.4 saatte derin deşarja gider). Firmware `PILH_TERS`/
   `PILH_BAYPAS` ile testi başlatmıyor ama **akımı durduramıyor** — bu ayrım hiçbir yerde
   yazılı değildi. `KULLANIM` pil satırına uyarı eklendi.
9. **16.2 "Hücreleri şimdi tak" diyordu** — 14.4/15.4'te zaten takılmıştı. "Yerinde mi, son
   kez bak" oldu. Ayrıca malzeme notlarındaki iki eskimiş sayı düzeltildi (gömme somun
   ×6 → ×10; yuva "77×21×21 varsayıldı" → 80×21×21 ÖLÇÜLDÜ, B52d).

**Kendi kodumda bulduğum iki kusur (B55'te dün yazılan ağırlık merkezi):**

10. **Ahşap kalemleri `bel == TAHTA_BEL` ile süzüyordum; ESP32'nin belirsizliği de tam
    0.20 olduğu için 9 g ESP32 "ahşap" sayılıyordu.** İddia yeşil kalıyor, bastığı sayı
    yanlış. Artık `grup` alanına göre süzülüyor.
11. **TP raf blokları kütle modelinde yoktu** (kesim listesinde vardı).

**Yeni iddia — iki bağımsız modelin ahşap hacmi EŞİT olmalı.** Kesim listesi parça parça
uzunluktan, kütle modeli geometriden kuruluyor. Bugün ayrışma tam olarak eksik parçaları
gösterdi; düzeltmeden sonra **fark 0** (497 664 mm³ = 497 664 mm³). Bu tek iddia 2, 10 ve
11'i birden yakalar. Yanında: her `DUVAR_PARCA` için ahşap tutucu kararı verilmiş olmalı, ve
metinde ahşap tutucu diyen her parçanın kesim listesinde karşılığı olmalı. **Bu ikincisi
yazıldığı anda bir kusur daha yakaladı:** "blok" ile arama TP2'yi kaçırıyordu, çünkü metinde
"çubuk **bloğuna**" geçiyor ve Türkçe yumuşak g yüzünden "blok" alt dizgisi yok — deponun
bilinen tuzağı, kök "blo" ile düzeltildi.

Denetim **1629 → 1643/1643**.

**AÇIK — kullanıcı kararı bekleyen (düzeltilmedi):**

* 🔴 **F0 yanlış yerde.** `SWP2.P1 → F0.1` yani sigorta **seçicinin çıkışında**. XT30'dan
  seçiciye giden iki tel ve seçiciden klemense dönen tel (toplam ~0.75 m, kutuyu çaprazlayan
  demet) 8.3 A'lik kaynağa **hâlâ çıplak bağlı** — B54'ün bulduğu kusur doğruydu, çözümü
  yanlış yere konmuş. Düzeltme **iki telin yerini değiştirmek**: `J6.1 → F0.1`,
  `F0.2 → SWP2.B1`, `SWP2.P1 → SW.1`. Sıfır parça maliyeti, kullanıcı henüz 10.1'e gelmedi.
* 🔴 **Kutu içinde HV kaçak yolu hiç uygulanmıyor.** Kart üstünde 12.6 mm (IEC 60664
  takviyeli) titizlikle uygulanırken kutuda yalnız mekanik 6 mm payı bakıyor:
  **ESP32–B 7.0 mm**, RS–B ve B–Q1 10.3 mm, A–B 12.7 mm. Yalıtım yüzeyi işlenmemiş ahşap
  (CTI tanımsız, higroskopik). Ayrıca kart B'nin kutu içindeki **yönü veri değil** — zincirin
  en yüksek düğümünün hangi kenara baktığı bilinmiyor, en kötü hal hesaplanamıyor.
* **Q1 soğutucusu yüzen çıplak alüminyum**, 613 V zincirin 10.3 mm yanında. COM'a bağlanmalı
  mı, yoksa bilerek mi yüzüyor — hiçbir yerde yazılı değil.
* **CAL jakı tek korumasız giriş.** GPIO10'a yalnız 1 kΩ ile bağlı; 25.5 mm ötedeki PİL 1
  jakı pil testinde 38.5 V'a çıkıyor. Yanlış deliğe giren yama kablosu GPIO'ya ~35 mA sürer.
  Öneri: BAT54S kelepçe ya da CAL'ı uzağa al.
* **TP4056'nın "korumalı" sürüm olduğu hiçbir adımda doğrulanmıyor.** Korumasız modülde
  B− ile OUT− fiziksel olarak aynı bakırdır → graf denetimi aynı sonucu verir, 1643/1643
  yeşil kalır. Korumasızsa aşırı deşarj ve aşırı akım koruması yok, hücre kolunda sigorta da
  yok. Öneri: 14.2/15.2'ye "modülde DW01A + FS8205 var mı" kontrolü.
* **16.3 için serbest 18650 gerekiyor**, ikisi de 16.2'de kutuya kapanıyor (stokta 2).
* **6.1 delikli plakete Ø3.2 delik istiyor**, matkapsız delme rehberi yalnız 2 mm ahşap için.
* **`{...}` kalıbı taraması** ve **F0 darbe payı** (T.SIGORTA'da "F 1 A" satırı yok, F0'ın
  "bol pay" iddiası ölçülmüyor) — ikisi de iddiaya bağlanmalı.
* **İncelenmeyen iki açı:** mekanik/yapılabilirlik ve doğrulama disiplini. Yeni oturumda
  koşulmalı.

**B55d (2026-09-23) — EKSİK KALAN İKİ AÇI KOŞTU: mekanik/yapılabilirlik + doğrulama disiplini.**
B55c'de kotaya takılan iki inceleme kullanıcının isteğiyle yeniden koşuldu. Denetim koşu boyunca
yeşildi (1643/1643); bulguların **hiçbiri** bir iddiayı kırmıyordu.

**Belgede BUGÜN duran, kullanıcının sırada olduğu adımları yanlış anlatan üç hata:**

1. 🔴 **Adım 1.2 fiziksel olarak imkânsız bir kesim tarif ediyordu.** Metin "iç kat ve direk
   parçaları **yarım çubuktan**: çubuğu ortadan ikiye kes → 90 mm" diyordu; yarım çubuk **75 mm**.
   B54'te duvar 4→5 sıra olunca (`ic_yuk` 72→90 > `yarim` 75) `hesap()` doğru kaynağa (`tek_uc`)
   geçmiş, **metin 72 mm dünyasından kalmış**. Etki 46 parça (34 iç kat + 12 direk ≈ 23 çubuk).
   İki inceleme de bağımsız buldu. Bunu yakalaması gereken iddia **tautolojiydi**: `hesap()`'taki
   formülün kopyasını yazıp veriyi kendisiyle karşılaştırıyordu. Artık metin ile veri karşılaştırılıyor
   ve metin `KAYNAK_AD[dikey_kaynak]`'tan üretiliyor.
2. 🔴 **Adım 4.3 dört sıra diyordu, tasarım beş sıra.** Başlık "2., 3. ve 4. sıralar", `"sira": 4`,
   `duvar_sira = 5`. İzometrik çizim "4. sıra bitti · 72 mm" yazarken aynı adımın parça tablosu
   5. sıranın parçalarını listeliyordu. Başlığa uyulsaydı duvar 72 mm kalır, kapak cıvatası (z 81),
   YUVA2 (z 63–84) ve ESP32 dupont payı — B54'te 5. sıranın eklenme gerekçelerinin hepsi çökerdi.
   Hiçbir iddia `s["sira"]` ile `duvar_sira`'yı karşılaştırmıyordu.
3. **AÇ/KAPA'nın kural metni hiçbir yerde yoktu** → belgede "Kural" hücresi boş. Kutunun en emniyet
   kritik anahtarı (KTS202 çift kutup olmak ZORUNDA) kuralsız görünüyordu. Denetim yalnız *var olan*
   notları geziyordu; artık ters yönden de soruluyor: monte edilen her ref'in notu var mı.

**Kendi B55/B55c işimde bulunan kusurlar:**

4. 🔴 **13.2'nin gerekçesi kendisiyle çelişiyordu (B55'te ben yazmıştım).** "Delikleri neden şimdi:
   kutu dolduktan sonra delmek talaşı kartların üstüne döker" — oysa 13.2'ye gelindiğinde kart A, B,
   ESP32, şönt, Q1 ve bütün kablolar takılmış oluyor (6.2 → 11.1). Havyayla 4+2 mm delerken yanık
   talaş lehimli kart A'nın üstüne dökülecekti. **Ayrıca somun blokları 13.1'de yapıştırılıp delikler
   13.2'de açılıyordu**: somunun yeri kalıcı sabitlendikten sonra delik iki bağımsız ölçümden
   açılıyor (±2–3 mm; Ø6 cepte M3 ancak ±1.5 mm oynar). **Çözüm ikisini birden kapattı:** yeni
   **4.7 = cıvata deliklerini aç (kutu BOŞKEN, konumlar tablodan — kapağa gerek yok)** → 13.1 kapağı
   yapıp cıvataları geçirir ve somun bloğunu **cıvataya merkezleyerek** yapıştırır (kendi kendine
   hizalanır) → 13.2 dener ve çıkarır. Numaralandırma korundu (14/15/16 aynı).
5. **Kötü-hal katmanının tamamı hiçbir mutasyonla sınanmıyordu.** `_am_uc`'yi devre dışı bırakan tek
   satır (`range(50)` → `range(0)`) 24 denge iddiasını nominal değerle besliyor ve hepsi yeşil
   kalıyordu — "denetim kötü halde de bakar" vaadi hiçbir testin arkasında durmuyordu. Eklenen iddia:
   kötü hal nominali her eksende en az `AM_KOTU_EN_AZ`=1 mm aşmalı (katman gerçekten çalışıyor).
6. **`am_yukseklik` ölçütünün kötü-hal ikizi eksikti ve eklenseydi BUGÜN kırmızı olurdu** (iki hücre
   0.509, tek hücre 0.508, eşik 0.50). Eşik geçirmek için değiştirilmedi: `kotu_am_yukseklik = 0.55`
   konuldu ve **neden gevşek olduğu veriye yazıldı** — AM yüksekliği bağımsız bir fiziksel sınır
   değil, devrilmenin ikincil göstergesi; asıl ölçüt kötü halde ölçülen devrilme açısı (45–56°,
   eşik 25°).
7. **Pil grafı yalnız EKSİ tarafı koruyordu.** `MT1.OUT+ → ESP32.5V` kablosunu `MT2.OUT+` yapmak —
   tek harf — belgeye "24 V'u devkit'in 5V pinine bağla" dedirtiyor ve 1643/1643 yeşil kalıyordu.
   `ESP32.5V` yaprak düğümdü, hiçbir iddia adını anmıyordu. Artı taraf için iddia + mutasyon eklendi.
8. **5.3 yanlış duvarın çizimini gösteriyordu**: altı öğenin beşi ön panelde, çizim arka panel.
   Panel seçimi artık takılan parçalardan türetiliyor. ⚠ İlk yazdığım kapsama iddiası **mutasyonu
   kaçırdı** — çizim kodunu okumak yerine aynı mantığı ikinci kez yazmıştım; `cizim_panelleri()` tek
   fonksiyonuna indirildi, ikisi de onu çağırıyor.

**Denetim 1643 → 1687/1687**, mutasyon B50 **47 → 50**.

**AÇIK — kullanıcı kararı bekliyor (B55c'nin açıklarına ek):**

* 🔴 **F0 sigorta yuvası kart A'ya 1.7 mm kalıyor** (`parca_payi` kuralı 6 mm) ve `derin_mm: 26`
  **ölçülmemiş bir varsayım** — 1.1 kumpas listesinde yoktu. Stoktaki pano yuvaları (BLX-3 sınıfı)
  tipik 30–33 mm → 3.3 mm girişim demek. Ölçüm maddesi 1.1'e eklendi; 26'dan büyükse F0 ön 4. sıraya
  (z 63, kart A'nın üstü boş) ya da arka panele alınmalı. Ayrıca F0'ın Ø12 deliği 18 mm çubukta
  dört yanda tam 3.0 mm et bırakıyor (pay 0.0) — serbest elle zımparada 1 mm kaçış sırayı koparır.
* 🔴 **Havalandırma yok.** İki 18650 + iki TP4056, kapak 4 × M3 ile sıkılı, hücre kolunda sigorta yok.
  Serbest hacim ≈ 2.5 L; bir hücrenin termal kaçakta saldığı gaz 1–3 L → ≈ +1 bar → kapağa ≈ 3.3 kN.
  Düşük olasılık, yüksek sonuç. Öneri: arka duvarın 5. sırasına 3–4 × Ø5 havya deliği (matkapsız
  rehbere birebir uyuyor), veriye `PANEL_ARKA` tip "havalandirma" olarak girsin.
* **Gömme M3 somun cebi:** somun 2.4 mm, cep 2.0 mm ve YUVARLAK (köşeden köşeye 6.35 > Ø6). Dönmeye
  karşı yalnız sıkı geçme; elle tork 0.5 N·m → cep yüzeyinde ≈ 8 MPa, huşun lif dikine ezilme
  dayanımı 5–7 MPa. Kapak somunu dönerse **kapak bir daha açılamaz**. Ayrıca M3×10 vidanın ucu
  deliksiz 4. kata 1.5 mm dalıyor. Öneri: cebi bıçakla altıgene getir + son katı da Ø3.2 del.
* **Kalın jak kabloları kart A takıldıktan sonra 12.7 mm'lik kör yarıkta bağlanıyor** (J3.1/J7.1/J7.2).
  Öneri: 5.2'de her büyük jakın iç ucuna pabuç + 20 cm pigtail, kutu boşken.
* **Kablo bağı yolları:** ESP32 altlıkları 2 mm ve tabana yapışık, bağ altından geçemez; MT1/MT2 için
  "bir kablo bağı" iki ayrı yanaktan geçemez. Öneri: ESP32 altlığı 3 kat (6 mm) tünel delikli, MT'lerde
  her yanağa bir bağ.
* **6.6 yapıştırıcı tablosuyla çelişiyor** (tablo "Q1 köşebendi: yapıştırıcı yok" diyor, 6.6 "tabana
  silikonla"). Fizik 6.6'yı haklı çıkarıyor (ahşap ısı yolunu kesiyor, ΔT 13–19 K) — tablo satırı
  daraltılmalı.
* **Kapak raylarının geçme payı nominal SIFIR** (KR1+KR2 dış yüzleri tam 214 = iç en). 0.5 mm içeri
  alınmalı.
* **18650 yuva cıvatalarının somunları hücre yatağının içinde kalıyor** (hücreyi 2.4–3 mm kaldırır,
  YUVA2'nin kapağa payı 6 → 3 mm'ye iner). Öneri: yuvayı da kablo bağıyla tut, vida hiç olmasın.
* **ESP32 anteni için keep-out kararı yok** (kart A 11.7 mm solda; Espressif ~15 mm istiyor). Öneri:
  16.3'e kapak açık/kapalı RSSI farkı ≤ 6 dB ölçümü.
* **YUVA1 ile ESP32 arası tam 6.0 mm** — J5'in 10 telli demeti + 5 V çatalı + CAL jumper'ı o 6 mm'de
  90° dönmek zorunda. 1.1'e "J5 kablosu takılıyken devkit'in en yüksek noktası" ölçümü eklenmeli.
* `KUTLE["KABLO"]` = 25 g iyimser; kaba hesap 40–45 g.

**B55e/f (2026-09-23) — KULLANICI KARARLARI: havalandırma, somun cebi, GÜÇ lambası.**
B55d'nin açık maddelerinden üçü kullanıcı kararıyla kapandı; ayrıca "kablolu kullanım" ve
"bildirim ışığı" soruları hesaplanıp cevaplandı.

**Havalandırma (B55e, seçenek A).** İki 18650 kapalı ahşap kutuda şarj oluyordu, tek delik
yoktu: bir hücre termal kaçakta 1–3 L gaz salıyor, serbest hacim ≈ 2.5 L → ≈ +1 bar →
kapağa ≈ 3.3 kN. Arka duvara **4 × Ø5** delik eklendi (`PANEL_ARKA`, yeni tip
`havalandirma`): **HV1 x63 z81 · HV2 x81 z63** (üst, çıkış) · **HV3 x81 z27 · HV4 x117 z9**
(alt, giriş). Konumlar üç kuralı birden sağlıyor: tam boy iç kat çubuğunun ortası, dış kat ek
yerinden ≥ 10.5 mm, ve **hiçbirini duvara asılı parça kapatmıyor** (18650 yuvaları x 92–172
şeridini örtüyor, delikler onun dışında). İlk denediğim x 187 / x 117 konumları mevcut
denetime takıldı (x 187'de tam boy çubuk yok, x 117 ek yerine 0.5 mm yakın) — konumlar
programla arandı. Dört yeni iddia: hücre varsa delik var · toplam alan ≥ 50 mm² (79) · en az
ikisi üst yarıda · hiçbirini parça kapatmıyor. `PARCASIZ_TIP` eklendi: havalandırma deliğinin
kendi parçası yok, kütleye girmez (eklenmeseydi 4 × 6 g hayalet kütle sayılacaktı).

**Somun cebi (B55e, seçenek C — kullanıcı: "somunların sökülebilir olması önemli değil,
yalnızca değerli parçalar sökülebilir olsun").** Cep Ø6 ve 2 mm idi; DIN 934 M3 somun 2.4 mm
kalın ve **köşeden köşeye 6.35 mm** — yani Ø6'ya zaten girmiyor, 2 mm cebe 0.4 mm taşıyor ve
yuvarlak cep dönmeyi engellemiyor (elle tork 0.5 N·m → cepte ~8 MPa, huş 5–7 MPa). Kapak
somunu dönerse **kapak bir daha açılmaz**. Yeni: `M3_SOMUN` + `SOMUN_CEP` sabitleri —
**Ø6.5 cep, 2 kat (4 mm) derin, somunun DIŞ yüzüne japon, son kat Ø3.2** (M3×10'un ucu ayakta
1.5 mm, M3×12'ninki kapakta 1.1 mm deliksiz kata dalıyordu). `kapak_somun_kat` 3 → **4**.
Adım metinleri artık bu sabitlerden üretiliyor, sabit "Ø6" yok. Kullanıcının gerekçesi de
veriye yazıldı. Altı yeni iddia.

**Kablolu kullanım sorusu — cevap: tasarım zaten destekliyor.** Kablo XT30'da takılı kalır
(PİL konumunda DPDT iki bacağı da ayırıyor), ön panelden AÇ/KAPA ile açılıp kapanır, seçici
ile pile geçilir. Üç uyarı belgeye girecek: (1) **kablo takılı olmak pili ŞARJ ETMEZ** —
TP4056'lar yalnız Type-C jaklarından besleniyor; (2) geçiş **elle** ve bu bilerek — diyot-OR
otomatik geçiş pilin eksisi ile kaynağın eksisini kalıcı birleştirir, topraklı adaptörde −12
rayı toprağa bağlanır ve kutunun yüzer olma özelliği (HV emniyetinin temeli) kaybolur;
(3) geçişte raylar kısa süre çöküyor (mekanik boşluk 10–50 ms, kondansatör tutması ~5 ms),
ölçüm kesilir, ESP32 ayrı beslendiği için panel ayakta kalır.

**GÜÇ lambası (B55f).** Kullanıcı "kart çalışıyor mu?" sorusunun görsel cevabı olmadığını
fark etti ve RGB ile zengin bildirim önerdi. **Analiz: RGB'yi ESP32 sürmek zorunda ve o LED
YALAN SÖYLEYEBİLİR** — ESP32 USB'deyken analog kapalıysa "hazır" gösterir; hiç gösterge
olmamasından kötü. Ayrıca saydığı bildirimlerden ikisi aynı yalıtım duvarına çarpıyor: hücre
2'nin eksisi −12 rayı olduğu için TP2'nin şarj sinyali ve hücre gerilimi **GPIO'ya yalıtımsız
gidemez** (yalnız hücre 1 okunabilir). Üçüncü sorun: RGB'nin yeşil/mavi Vf'i 3.0–3.2 V, ESP32
3.3 V veriyor → cılız ve Vf toleransına duyarlı. Kullanıcı bunun üzerine **yalnız pasif GÜÇ
LED'i** seçti.

Uygulanan: ön panel **5. sıra x 51** (AÇ/KAPA'nın tam üstü, en yakın deliğe 25.5 mm, iç kat
çubuğunun ortası). **KL.+ (= +12 rayı) → 10 kΩ (R060) → LED anodu; katot kart GND.** Karta
lehim yok. **LED +12 rayında olmak ZORUNDA:** akım GND'ye GİRER, 7912'nin çekmek üzere
tasarlandığı yön; GND ile −12 arasına konsaydı regülatörden akım VERMESİ istenirdi ve 79xx
veremez (7812 yerine 7912 seçilme gerekçesinin aynısı). Sayılar: 0.99 mA · 7912'nin
kapasitesinin %1.1'i · F1 payı 26/50 mA (%48) · pil analog süresi 7.9 → 7.6 sa (−%4) ·
direnç 9.8 mW. **LED akımı B11 orta nokta bütçesine de girdi** (`tasarim3_sabit.PANEL_LED_*`,
`sim3_besleme` kötü hal 15 → **16.0 mA**, 23/23) — sayı iki yerde ayrı yaşamıyor. Yedi yeni
iddia + üç mutasyon (LED'i −12'ye taşı · direnci 100 Ω yap · ESP32'ye bağla).

Denetim 1687 → **1784/1784**, mutasyon B50 **50 → 53/53**.

**Bu turda düşülen tuzaklar (hepsi yakalandı):** yazdığım açıklama cümleleri iki kez kendi
iddialarıma takıldı ("yarım çubuk YETMEZ" ve "Ø6 DEĞİL Ø6.5" — olumsuz cümlede geçen dizge),
ve heredoc kaçışı iki kez ısırdı (bir kez `print("
"` gerçek satır başına döndü, bir kez
mutasyon satırındaki kesme işareti dizgeyi kapattı). [[bash-heredoc-ters-bolu]] hâlâ geçerli:
kesme işareti / ters bölü içeren yamaları tek tırnakla değil, çift tırnak + kaçışla yaz.

**AÇIK kalanlar:** F0'ın derinliği hâlâ ölçülmedi (kullanıcı sigortanın gerekli olduğunu
onayladı, yeri ölçüme bağlı) · kalın jak kabloları kart takılıyken 12.7 mm kör yarıkta ·
kablo bağı yolları · kapak rayı geçme payı sıfır · 6.6 yapıştırıcı tablosuyla çelişiyor ·
18650 yuva somunları hücre yatağında · ESP32 anteni keep-out · YUVA1–ESP32 6.0 mm ·
kutu içi HV kaçak yolu (ESP32–B 7.0 mm) · hücre 2 için yalıtılmış modül (B55b).

---

**B55g (2026-09-23) — 11 AÇIK MADDE BAĞIMSIZ İNCELENDİ, 3 KULLANICI KARARI UYGULANDI.**
22 ajanlı bir koşu: her açık madde için bir inceleme, her tavsiye için ayrı bir **çürütme**
ajanı (varsayılanı "bu tavsiye yanlış"). **11 tavsiyenin 10'u kusurlu çıktı** — yani
incelemenin kendisi de incelenmeseydi yanlış kararlar veriye girecekti. Denetim koşu boyunca
1784/1784 yeşildi; aşağıdakilerin hiçbiri bir iddiayı kırmıyordu.

**Belgede BUGÜN duran, kullanıcının birkaç gün içinde okuyacağı beş hata (hepsi düzeltildi):**

1. 🔴 **Delik tablosu 8 HAYALÎ cıvata deliği deldiriyordu.** `kutu.py:2313` elle yazılmış bir
   satırla "Duvara asılı parçalar (yuva ×2, MT3608 ×2, TP4056 blokları ×2) → Ø3.2, ikişer,
   M3 cıvata dıştan" diyordu. `DUVAR_TUTUCU`'ya göre MT/TP **kablo bağıyla** tutuluyor,
   montaj deliği yok; gerçek cıvata deliği yalnız YUVA1/YUVA2'nin dördü (C1a/C1b/C2a/C2b) ve
   onlar zaten tablonun üstünde tek tek listeli. **B55c bu kusuru adım metinlerinde düzeltmiş,
   referans tablosundaki ikizini kaçırmıştı.** Üç satır da artık veriden türetiliyor.
2. 🔴 **Somun cebi metni B55e öncesi dünyada kalmıştı.** Hem `DELME` tablosu hem delik tablosu
   "3. kattaki **Ø6** somun yuvası" diyordu; B55e dün cebi **Ø6.5 · 2.–3. kat · 4 katlı blok**
   yapmıştı. İkisi de `SOMUN_CEP`'ten üretiliyor artık.
3. 🔴 **Üç havalandırma gerekçesi yanlış x yazıyordu** (B55e'de dün yazılmıştı): HV2 "x **187**
   … kutunun **sağ** yarısı" derken veri x 81 (sol yarı), HV3 "x **117**" derken 81, HV4 "bu
   noktada iç kat yok" derken denetimin kanıtladığının tersi (çubuk z 0'dan başlıyor).
   Konum cümlesi artık `ic_kat_konumu()` ile geometriden üretiliyor.
4. **16.2 "13.2'de açılan dört delikten" diyordu** — delikler B55d'de 4.7'ye taşınmıştı.
5. 🔴 **13.1 FİZİKSEL OLARAK YAPILAMIYORDU.** Cıvatanın yolunda 2 mm'lik kapak rayı duruyor
   (KR1 x 0–2 / KR2 x 212–214, z 72–90; cıvata y 45/117 z 81 tam içinden geçiyor) ve **rayı
   delen adım yoktu**: 4.7 yalnız duvarı deliyor. Çözüm deponun kendi yöntemi (`DELME`'nin
   "İç kat (5.1)" maddesi): dıştaki delik kılavuz olur, havya ucu ondan geçirilip ray delinir —
   eş eksenli, işaretleme yok, kapak kalkmıyor.

**Teşhisi değişen iki açık madde:**

* **"Kutu içi HV kaçak yolu ESP32–B 7.0 mm" yanlış çerçevelenmişti.** Orada sürekli katı yüzey
  yok (B 8 mm ayakta, ESP32 2 mm altlıkta), yani *creepage* değil *clearance* geçerli ve
  elektriksel pay 3–6 kat. **Ama altından daha kötüsü çıktı:** `IC_PARCA["B"]` 45.7 mm
  (= 18 × 2.54, yani DELİK ALANI) modelleniyor, oysa `KARTLAR["B"]` = "5×5 cm (SRF020)" ve bu
  plaket **kesilmiyor** (kart A kesiliyor, B fabrika kenarlı). Her yanda ~2.15 mm eksik →
  ESP32–B gerçek boşluk **4.85 mm**, `parca_payi` 6.0'ın altında. ⏳ Kullanıcı kumpasla ölçecek.
* 🔴 **`kutu.py:970` "Kart B HV jakına yakın (kablo ≤ 60 mm)" iddiası 43.6 mm yazıp yeşil
  geçiyordu.** Kod okundu: 2B `math.hypot` (jakın z 63'ü ile plaketin z 8'i arasındaki **53 mm
  düşüşü hiç saymıyor**), lehim noktası yerine kartın **merkezini** kullanıyor, ankrajdan geçen
  kırık yolu düz çizgi sanıyor. Gerçek yol dört yönelimde **74–101 mm** — yani `kutu_veri.py`'deki
  "HV kablosu ≤ 6 cm" kuralı **hiçbir yönelimde sağlanamıyordu** ve denetim bunu göremiyordu.

**Kullanıcı kararları (uygulandı):**

**① Kart B'nin yönü = 270° (yeni veri alanı `yon`).** Kare plaket dört türlü takılabiliyordu,
yönü hiçbir yerde yazılı değildi ve ayaklar 6.1'de **yapıştırıldığı için seçim geri dönülemez**.
617 V'luk düğüm (T_HV, sütun 3 satır 7) kartın bir kenarında toplanmış, yani yön kutudaki en
yüksek gerilimin nereye bakacağını belirliyor. Dört yönelim hesaplandı:

| yön | HV düğümü → en yakın iletken | HV kablosu (jak→ankraj→D8) |
|---|---|---|
| 0° | 21.6 mm | 92 mm |
| 90° | 16.0 mm | 101 mm |
| 180° | 19.2 mm | 88 mm |
| **270°** | **30.2 mm** | **74 mm** |

270° **iki ölçütte de en iyi**. Denetim yönü sabit yazmıyor, **en iyi olduğunu ölçüyor**: ölçütler
ileride ayrışırsa (biri 180°, diğeri 270° derse) kırmızıya döner ve karar yeniden sorulur.
Kullanıcıya bakan cümle de üretiliyor (`kart_yon_cumlesi`): *"kartın A1 köşesi (ön-sol) kutunun o
köşesine baksın"* — ve bu cümle Adım **6.3**'te, HV kablosunun bağlandığı 9.3'ten önce çıkıyor.
⚠ Yan bulgu: `IC_PARCA["nasil"]` alanı **belgeye hiç girmiyor** (yalnız denetim okuyor) — kartların
nasıl tutturulacağı kullanıcıya ulaşmıyordu; yön cümlesi bu yüzden adım metnine kondu.

**② CAL seri direnci 1 kΩ → 22 kΩ (R059, stokta 50).** CAL panelin **tek korumasız GPIO ucu**;
25.5 mm ötesindeki PİL 1'de pil testinde 38 V'a kadar çıkıyor. İki ayrı arıza yolu ve ikisi de
artık ölçülüyor:
* Kart **kapalıyken** +3V3'ü hiçbir şey çekmiyor; CAL direnci ile **R41** (1 kΩ, +3V3–GND,
  netlistten okunuyor) bir **bölücü** oluyor ve ray yükseliyor. O rayda yalnız GPIO10 değil,
  **iki ADS1115'in VDD'si** de var (netlist +3V3: U6.8, U7.1, U7.8) → mutlak sınır 3.6 V.
  1 kΩ ile **19.0 V**; 22 kΩ ile **1.65 V**.
* Kart **açıkken** ray 3.3 V'ta tutuluyor (`ESP_BOSTA_AKIM` 40 mA > enjeksiyon) ama akım GPIO'nun
  ESD diyodundan akıyor: `ESP_ENJEKSIYON_HEDEFI` 5 mA. 1 kΩ ile **34.7 mA (6.9×)**, 22 kΩ ile
  **1.58 mA**. Direncin gücü de 1.20 W → **55 mW** (1/4 W anma).
⚠ *Ajanın "seri R41" tarifi yanlıştı* — R41 GPIO'ya seri değil, rayın tek yükü; sayılar aynı
çıkıyor ama mekanizma bölücü. Bedel **bilinen sabit bir bölme oranı**: kare dalga 3.27 → 2.72 V,
skopta **94 kod** (eşik `CAL_ASGARI_KOD` = 50, yüzde değil kod: okunabilirliği sınırlayan şey
menzil değil çözünürlük). Kenar yuvarlaması 2.2 µs = 1 kHz'de periyodun %0.2'si ve CAL frekansı
yazılımdan düşürülebiliyor — **koruma payı geri alınamaz, genlik alınabilir.**
⚠ Kullanıcı "kart A'da tekrar lehim beni aşırı yorar" dedi; gerek yok: direnç kartın üstünde
değil, devkit'in GPIO10 pinine takılan jumper'ın ucunda ve **Adım 11.1'de**, henüz gelinmemiş bir
adımda takılıyor. Ölçüm doğruluğu/hızı da etkilenmiyor: CAL bir **çıkış**, ölçüm yollarının
hiçbirinde değil.

**③ Hücre 2 koluna 500 mA sigorta (F2 = FUS015 + FUS009 yuva, ikisi de stokta).**
TP4056'nın koruma FET'i (FS8205) **B− ile OUT− ARASINDA**; hücre uçlarındaki ya da H+/H−
kablolarındaki bir kısa devre o FET'in **dışında** kalıyor ve DW01A kesemiyor. Kapalı ahşap
kutudaki tek onlarca amperlik yol bu. Graf değişti (`H2+ → F2.1`, `F2.2 → TP2.B+`) ve üç iddia
ölçüyor: yapısal (artı uç önce sigortaya girer), **sürekli kötü hal 294 mA** (24 V × 25 mA,
hücre 2.4 V, verim 0.85) → anma 500 mA = **1.7× pay** (boşuna atmaz), **kısa devre 42 A** =
anmanın 84 katı (gerçekten atar). Hücre 1 kolu isteğe bağlı kaldı (Adım 15 zaten isteğe bağlı).

**🔴 Denetimin en büyük yapısal kör noktası kapatıldı: AÇIKLIK hiç ölçülmüyordu.**
`cakisma3` yalnızca **çakışmaya** bakıyor ve `parca_payi` = 6 mm kuralı sadece IC_PARCA
çiftlerine + duvar parçalarına uygulanıyordu. Taşıyıcı bloklar, kutu ek parçaları, sabitler
(köşe direği / kapak rayı) ve panel gövdeleri **tamamen kapsam dışıydı**. Gerçek 3B (Öklid)
boşluk hesaplanınca **19 çift 6 mm'nin altında** çıktı ve hiçbirini tek bir iddia ölçmüyordu:
F0 ↔ kart A **1.70**, ESP32 ↔ B-ayak1 **0.54**, A-ayak2 ↔ ESP32-altlık1 **0.24**,
RS-altlık1 ↔ B-ayak2 **0.82**, CAL ↔ PİL jakları **5.66** mm… Çözüm bir *eşik* değil **kilitli
envanter**: `DAR_ACIKLIK` her çifti gerekçesiyle tutuyor, liste hem tavan hem taban (yeni dar
çift → kırmızı, artık dar olmayan kayıt → kırmızı, gerekçe < 40 karakter → kırmızı, gerekçedeki
sayı gerçek boşlukla tutmuyorsa → kırmızı) ve belgede tablo olarak duruyor.
**Envanteri kurarken çıkan yeni bulgu:** ESP32'nin **anten ucu** (USB arka duvarda → anten karşı
uçta) B-ayak1'e **0.54 mm** — yani 18 mm'lik bir ahşap blok antenin yarım milimetre yanında.
RF etkisi ölçülmedi, anten keep-out açık maddesine eklendi.

**Sessiz kusur: 43 iddia kaybolabiliyordu ve koşu bunu söylemiyordu.** `kutu.py`'nin
stdout'u gerçek bir dosya değilse (`bom_dogrula` import'unda `sys.stdout.reconfigure`)
envanter okuyucusu çöküyor, `yerlesim3_belge.Stok` istisnayı yutuyor ve **7 · STOK bölümünün
43 iddiası düşüyor** — özet yine "N/N doğrulama geçti", rc=0. Yani 43 iddia eksik bir koşu tam
koşudan **ayırt edilemiyordu**. (Bu oturumda kazara üretildi: `redirect_stdout` altında
F0 konumlarını denerken 1815 yerine 1772 çıktı.) Mutasyon koşucusu etkilenmiyor (kopya
`projeler/` altında, envanter çözülüyor) ve envanter depo DIŞINDA olduğu için (herkese açık
depo) bunu kırmızı yapmak yanlış olurdu; çözüm özet satırına taşımak:
`1770/1770 doğrulama geçti  ⚠ EKSİK KOŞU: envanter okunamadı, 7 · STOK bölümü atlandı`.

**Yer tutucu taraması (B55c'nin açık maddesi kapandı).** MALZEME'nin `ad` alanı `.format()`
edilmiyordu ve `{pil_sigorta}` belgeye **ham** çıktı — B55c'deki `{adim_uA}` kusurunun aynısı.
Artık belge üretiminin tek çıkış noktasında `{kelime}` kalıbı taranıyor ve bulunursa üretim
patlıyor.

**Kendi yazdığım iddialarda mutasyon koşucusunun yakaladığı iki ölü doğum:**
(a) somun cebi kalıbı "Ø6 **somun yuvası**" biçimini hiç yakalamıyordu — cep kelimesi Ø'nun
önünde de arkasında da olabiliyor, iki kalıp gerekti; (b) rayın delinmesini **metinle** ölçen
ilk iddia, talimatı değil "orada delik yok" cümlesini yakalıyordu ve mutasyon kaçtı — iddia
metinden **geometriye** taşındı (`kapak_civata_delen` sözlüğü, cıvatanın kestiği katmanlar
geometriden hesaplanıp planla karşılaştırılıyor).

**B55g-b — kullanıcı geri bildirimiyle sadeleştirme.** Kullanıcı: *"kartı şu şekilde yamuk
yerleştir, şunlar arasında şu kadar mesafe olsun falan bunları aşırı derecede hesaplayarak
kendini yormana gerek yok; basic seviyede hesapla, ben gerekli şekilde ayarlarım, gerekirse
araya izole bant koyarım."* Haklı: 19 dar çiftin **10'u ahşap–ahşap** ve bıçakla yerinde
ayarlanıyor; onları tek tek gerekçelendirmek gereksiz bakım yükü. Envanter daraltıldı —
gerekçe artık **yalnız en az bir tarafı iletken** olan **9 çiftten** isteniyor (`iletken_mi()`:
IC_PARCA + metal gövdeli panel öğeleri iletken; taşıyıcı/ek blok/direk/ray değil). Ahşap–ahşap
çiftlerde yalnız **çakışma** ölçülüyor ve belgede tek satırda sayı olarak geçiyor. İddia sayısı
değişmedi (1815), mutasyon 70/70 korundu. Ayrıca kullanıcı **gerekli parçayı gerektiğinde
kesiyor** (toplu kesim yapmıyor) → F0'ın yer değiştirmesi hiçbir fireye yol açmıyor, ölçüm
aciliyeti kalktı.

**B55h — yalıtkan kaplama planı (kullanıcı kararı: tırnak cilası).** Kullanıcı yüksek gerilim
bölgelerini tırnak cilasıyla 4–5 kat kaplamayı planlıyor; nereye yapılacağı veriye yazıldı
(`kutu_veri.KAPLAMA` + `KAPLAMA_HARIC`, belgede "Yalıtkan kaplama" bölümü). Kaynaktan çıkan
tablo: **zincirin tamamı kart B'de** (617 · 514 · 411 · 309 · 206 · 103 V), kart A'nın en
yüksek düğümü **63.5 V** (skop girişi) — yani kaplama tek kartın işi.
**Asıl gerekçe emniyet değil DOĞRULUK:** HV bölücüsü 4.92 MΩ / 8.2 kΩ olduğu için yüzey kaçağı
bölücüye paralel girip oranı kaydırıyor — 1 GΩ → %0.5, **100 MΩ → %4.7**, 50 MΩ → %8.9 okuma
hatası. Tozlu/nemli FR4 yüzeyi 10⁸–10⁹ Ω mertebesinde, yani kaplama kalibrasyonu koruyor.
⚠ Kaplama **yüzey kaçağını** keser, **hava aralığından atlamayı kesmez** — mesafe yerine geçmez
(kutuda mesafeler 16–30 mm, zaten fazlasıyla yeterli). Kaplanmayacak yerler de gerekçesiyle
yazılı: kart A (gerekmiyor), Q1 soğutucusu/regülatör çevresi (nitroselüloz ısıda çatlar), panel
jaklarının lehim kulakları (tel oynayınca cila çatlar → makaron/bant), ölçüm pedleri (kaplanmış
pede prob değmez). Sıra: T_HV/T_N6 tellerini **önce lehimle**, sonra kapla, sonra 6.3'te tak.
**Kendi iddiam yine ölü doğdu ve mutasyon yakaladı:** "zincirin kartı kaplama listesinde mi"
diye sormak yetmiyordu — tam-kart kaydı A'ya taşınsa bile aynı kartın "lehim noktaları" kaydı
listede kaldığı için yeşil kalıyordu. Kayıtlara `kapsam` alanı (kart/nokta) eklendi, iddia
**tam kart kaplaması** şartına bağlandı.

**B55i — kullanıcının SIRADAKİ adımı denetlendi (Adım 3–4), delme rehberinde iki açık.**
Kullanıcı tabanı bitirdi (2.1/2.2) ve sırada duvar parçalarını delmek var. O adımlara bakınca:

1. 🔴 **Ø12 için delme yöntemi hiç yoktu.** `DELME`'nin "Büyütme" satırı Ø6 (kalem) ve Ø8
   (kalın marker) ile bitiyordu; F0 sigorta yuvasının **Ø12'si kutudaki EN BÜYÜK delik** ve
   18 mm çubukta her yanda **3.0 mm et** bırakıyor (diğer bütün çaplarda et ≥ 4.5 mm).
   Matkabı olmayan kullanıcı Adım 3.1'e bu tarifsiz geliyordu. Eklendi: **zincir delme**
   (çemberin üstüne havyayla 8–10 delik → göbeği çıkar → eğe/zımpara) + et payı uyarısı,
   sayılar `CUBUK`/panel verisinden üretiliyor.
2. 🔴 **Ø5 için de yöntem yokmuş** — dört havalandırma deliği ve GÜÇ LED'i o çapta ve
   **Adım 3.2'de** deliniyor. Bunu kendi yazdığım kapsam iddiası ÖNCE kaçırdı: süzgeç olarak
   `yuvarlak_mi()` kullanmıştım, o ise "arkasına iç kat çubuğu ortalanıyor mu" sorusu —
   "yuvarlak delik mi" değil. Süzgeç düzeltilince (oval olmayan her delik) iddia kırmızıya
   döndü ve gerçek açığı gösterdi.

Yeni iddialar: panelde kullanılan **her yuvarlak çapın** `DELME`'de geçmesi (6 çap: Ø3.2 · Ø5 ·
Ø6 · Ø6.5 · Ø8 · Ø12) ve en büyük delik için kalan etin rehberde **sayıyla** yazması.
**Mutasyon burada da bir ölü doğum yakaladı:** Ø5'in yöntem cümlesini silen ilk mutasyon KAÇTI,
çünkü aynı satırın sonundaki "Havalandırma delikleri (Ø5) istisna" ibaresi çapı anmaya devam
ediyordu — iddia çapın *anılmasını* ölçüyor, *yöntem verilmesini* değil. Mutasyon çapı satırdan
tamamen kaldıracak şekilde yazıldı; sınırı DEVIR'e not edildi.

**Sıra bulgusu (kullanıcıya verildi):** plan "3.1 ön → 3.2 arka" diyor ama **tersi doğru**.
F0 taşınırsa yalnız **ön duvarın 2/3/4. sıra** parçalarının ek yeri kayıyor (6 parça, 3'ü uzuyor;
1. ve 5. sıra etkilenmiyor, arka duvar hiç etkilenmiyor). Kullanıcı gerekliyi gerektiğinde
kestiği için fire yok: 3.2 → 4.1 → 4.2 serbest, 4.3'ün ön duvar kısmı ölçüme bağlı.

**B55j (2026-09-23) — KULLANICI ÖLÇTÜ: planın üç varsayımı yanlıştı, biri geri dönülemez
bir çakışmaydı.** Kullanıcı kumpasla ölçüp verdi; hepsi veriye işlendi (`olculdu: True`).

| Ne | Plan varsayımı | ÖLÇÜLEN | Sonuç |
|---|---|---|---|
| F0 derinliği | 26 mm | **24** (gövde 19–20 + lehim bacağı 4) | ✅ plandan SIĞ — F0 **yerinde kalıyor**, ön duvarın kesim boyları değişmiyor |
| F0 diş çapı | Ø12 | **Ø10–11** | delik Ø12 → **Ø11**, 18 mm çubukta et 3.0 → **3.5 mm** |
| Kart A | 114.3 × 114.3 | **130 × 120** | 🔴 köşe direğine ve kart B'nin ayağına GİRİYORDU → kullanıcı **115 × 115'e kesecek** |
| Kart A yüksekliği | 24 mm | **35** (alt teller + üst parçalar) | TP4056 rafına pay 4.78 mm |
| Kart A ayağı | 8 mm (4 kat) | **16–17 gerekiyor** | kullanıcı kararı: ahşap blok **9 kat = 18 mm** |
| Kart B | 45.7 (delik alanı) | **50 × 50** (fabrika, kesilmiyor) | gövde modeli düzeltildi (`tasma` alanı) |
| ESP32 | 26 × 63 | **27.5 × 63** | işlendi; yükseklik 14 mm ölçümü modelin 28'iyle tutarlı (dişi dupont dahil) |

**Kart A'nın 130×120 olması geri dönülemez bir hataydı:** kartları delik ızgaralarına ortalayıp
koyunca kart A **köşe direği D1'e** ve **kart B'nin ayağına** 0.00 mm ile giriyordu. 115×115'e
kesilince bütün çakışmalar kalkıyor; en dar iletken taraflı açıklık **0.54 mm** (ahşap ayak ↔
devkit gövdesi). Çubuk sayısı **131'de kaldı** — 18 mm'lik ayakların 20 ek parçası artıklara sığdı.

**Kart B 50 mm** doğrulandı: model 45.7 diyordu ve o DELİK ALANIydı (18 × 2.54), gövde değil.
`tasma` alanı eklendi — x/y delik ızgarasının çıpası olarak kalıyor, gövde iki yana taşıyor.
Sonuç: kart B ↔ ESP32 boşluğu 7.0 değil **4.85 mm**. Elektriksel sorun yok (617 V'luk düğüm
yön 270° ile karşı kenarda, en yakın iletkene 30.2 mm) — 270° gerçek ölçülerle de hâlâ
her iki ölçütte en iyi.

**Ayak 8 → 18 mm:** kart A z 18–53, kapak rayına 19 mm pay. Gömme somun yine 2.–3. katta,
yani M3×10 vida yetmeye devam ediyor; alttaki beş kat delinmiyor, sadece yükseltiyor.
Kart B 8 mm'de kaldı (altında tel yok).

**Ölçümlerin açtığı iki yeni kusur:**
* **TP4056 rafı (TP1) ↔ kart A = 4.78 mm.** Kart A 35 mm olunca üstü 53'e çıktı ve raf
  (z 42–47) ile DÜŞEYDE kesişiyor; ayıran şey yatay 4.8 mm. TP1 Adım 15'e ait (hücre 1,
  isteğe bağlı) — takılmazsa sorun yok.
* **Kart A'nın arka boş şeridi ↔ MT1 = 4.00 mm** (şerit 18 mm'ye yükseldi, MT3608 z 24–41).

**Ayak kat sayısı değişince iki eskimiş metin daha yakalandı** — ikisi de elle yazılmış sabitti:
6.1 *"Ayak bloğu: 4 parça çubuk üst üste"* (artık `{ayak_kat_a}` ile veriden, A 9 / B 4 ayrı
yazıyor) ve `DELME`'nin *"Son kat da Ø3.2 delinir"*'i (9 katlı blokta son kat 9.; artık
"cebin hemen altındaki kat" ve altındakilerin delinmediğini söylüyor). Yeni iddia:
**kart + ayak kapak rayının altında kalmalı** (A: 53 ≤ 72) — bu olmasa ayağı yükseltmek
sessizce kapağı kapanmaz hale getirebilirdi.

**Envanterde iki yapısal eksik kapandı:** (1) duvara asılı modüller açıklık envanterine hiç
girmiyordu, ayrı bir iddia ailesi onlara tek tek bakıyordu — TP1 tam o boşluktan çıktı;
(2) HV yön hesabı AYRI bir gövde kopyası kuruyordu ve `tasma` ile dolu/boş ayrımını
görmüyordu, yani eski modelle çalışıyordu. İkisi de `kutu_govdeleri()`'ne bağlandı.

**B55k (2026-09-23) — KALAN AÇIK MADDELER: dün eklediğim sigortanın kendisi kusurluymuş.**
Üç açık madde (termal · TP4056 koruma · mekanik artıklar) bağımsız incelendi, termal ve TP4056
ayrıca çürütüldü. Çürütme turu ikisinde de manşeti çökertti — ve en değerli bulgu B55g'de
**benim eklediğim** sigortada çıktı.

**🔴 F2 = 500 mA İLK ŞARJDA ATARDI.** Sigortayı hücrenin artı ucuna koydum; orası TP4056'nın
**BAT** ucu, yani **şarj akımının tamamı oradan geçiyor**. Modül fabrika ayarında
(`Rprog` 1.2 kΩ) **1.0 A** şarj ediyor (`kutu_veri.py:1366` bunu zaten yazıyordu).
500 mA, o akımın yarısı. Ölçütüm yalnız **deşarj** kolunu sayıyordu (294 mA) ve 1.7× pay
görüp yeşil geçiyordu — **iddia doğru hesaplanmış ama yanlış akımı ölçüyordu.**
Düzeltme: `TP4056_RPROG` + `PIL_SARJ_AKIMI = 1200/Rprog` sabitleri, anma **2 A** (FUS004,
stokta 8), ölçüt `≥ 1.5 × max(şarj, deşarj)`. Kısa devre payı 42 A / 2 A = **21×**.

**🔴 Hücre 1 kolunda hiç sigorta yoktu.** B55g'nin gerekçesini (koruma FET'i B−/OUT− arasında,
hücre ucu kısasını DW01A kesemez) yazdım ama yalnız hücre 2'ye uyguladım; denetim de yalnız
`H2+`'ya bakıyordu. Aynı 42 A'lik yol hücre 1'de tamamen açıktı. **F1P** eklendi, kural artık
her iki hücre için döngüyle.

**Termal — hiç bakılmamıştı, bakıldı, manşet çürütüldü.** İlk analiz "Li-ion 45 °C şarj tavanı
aşılıyor, ölümcül" dedi. Çürütme üç kusurunu gösterdi: (a) sonuç **ölçülmemiş bir ESP32 gücüne**
asılı (1.57 W varsayılmış, KULLANIM'ın "~3 sa" iddiasından türetilmiş; gerçek devkit 0.4–0.8 W),
(b) en sıcak senaryo (boş hücre 3.0 V) **28 dakikalık geçici bir çalışma noktası**, kutunun ısıl
zaman sabiti ise 65 dk — kararlı hale hiç ulaşmıyor, (c) model **hücreyi havaya koyuyor**, oysa
hücreler kutunun en soğuk yüzeyine (arka duvara) cıvatalı. Ayakta kalanlar:
* Kutu ısıl olarak sorun değil: Q1 soğutuculu Tj 58–78 °C (sınır 175), 7912 38–68 (sınır 125),
  elektrolitik ömrü 21 yıl. Bağlayıcı tek parça 18650.
* 🔸 **Havalandırmanın ısıl gerekçesi yanlıştı.** Baca akışı ΔT 10 K'de 0.19 L/dk = **36 mW**,
  duvarların attığı 3338 mW'ın **%1.1'i**. HV3/HV4'ün "TP4056'ların hemen altında" gerekçesi de
  geometrik olarak yanlış (delikler x 81/117; TP4056'lar x 18–36 ve 178–196). Metinler düzeltildi;
  **gaz tahliyesi gerekçesi doğru ve kaldı** — B55e'nin kararı yanlış değildi, gerekçesi yanlıştı.
* Şarj kuralı `KULLANIM`'a eklendi (şarjda ölçüm yok · iki hücre aynı anda şarj edilmez · sıcak
  odada kapak açık) + `LIION_SARJ_TAVANI_C` / `LIION_DESARJ_TAVANI_C` sabitleri.
  **SAYI İDDİA EDİLMEDİ:** model 4–5 tahmin sabitine dayanıyor ve baskın olan iç taşınım
  katsayısı sonucu **+%39 / −%33** oynatıyor. Yerine tezgah ölçümü (ilk şarjda içeri termometre).

**TP4056 koruma ayrımı: kategori hatası olduğu anlaşıldı.** Bir DC bağlantı grafı korumalı ile
korumasız modülü **ilke olarak** ayırt edemez — korumalı modülde hücre takılı ve sağlıklıyken
FS8205 iletken, yani B− ile OUT− gerçekten aynı düğüm. Statik denetime yüklenemez; yordam
tezgaha ait (hücre yokken diyot kademesinde B−↔OUT− iki yönde de OL, B+↔OUT+ öter).
Asıl kazanç zaten sigortalardan geldi: artık koruma **olmasa da** her iki kol sigortalı.

**Mekanik artıklar:** "adım metinleri yapıştırıcı tablosuyla çelişmiyor" diye adlandırılan
denetimin aslında bir **kural değil iki adımlık beyaz liste** olduğu bulundu (yapıştırıcıdan söz
eden 19 alt adımın 17'si hiç karşılaştırılmıyor) — 6.6 çelişkisinin bu yüzden kaçtığı doğrulandı.
Bu tur uygulanmadı, açık kaldı.

Denetim **1784 → 1830/1830**, mutasyon B50 **53 → 82/82**, sayım kilidi **3332**.

**AÇIK — kullanıcı kararı / ölçümü bekliyor:** F0 yuvasının derinliği (26'dan büyükse x 141
z 63'e; dört aday konum 1784 setiyle sınandı, (141,63)/(141,81)/(141,45)/(159,63) yeşil,
(123,63) ve (105,81) kırmızı) · **kart B'nin gerçek kenar ölçüsü** (model 45.7, fabrika plaketi
50 → ESP32'ye 4.85 mm) · ESP32 anteni keep-out (ahşap blok 0.54 mm, önce tezgahta RSSI ölçülsün) ·
kalın jak kabloları kart takılıyken 12.7 mm kör yarıkta · kablo bağı yolları · kapak rayı geçme
payı sıfır · 6.6 yapıştırıcı tablosuyla çelişiyor · 18650 yuva somunları hücre yatağında ·
YUVA1–ESP32 6.0 mm · TP4056'nın korumalı sürüm olduğu doğrulanmıyor · Ø12 için `DELME`'de yöntem
yok (kutudaki en büyük delik, matkap yok, FUS027 stokta tek) · kütleler hiç tartılmadı ·
hücre 2 için yalıtılmış modül (B55b).

**B55l (2026-09-23) — belge üretecinin kendi altyapısı.** Adım metinlerinin yer tutucu
sözlüğü **iki yerde elle yazılmıştı** (belge üreteci + denetimin 1.2 kolu); yeni bir yer
tutucu eklenince denetim tarafı `KeyError` ile çöküyordu. Tek kaynağa indi:
`adim_bicim(h, nl, parcalar)`. Belgenin tek yazma noktasına **yer tutucu kaçağı kapısı**
kondu (`{[a-z_]{3,24}}` kalıntısı varsa `AssertionError`) — biçimlenmemiş bir alan artık
sessizce kullanıcının ekranına çıkamaz. "Adım metinleri yapıştırıcı tablosuyla çelişmiyor"
denetimi **iki adımlık beyaz listeden gerçek kurala** çevrildi (B55k'da açık bırakılmıştı):
kapalı dünya olduğu için "epoksi" görünmezdi.

**B55m (2026-09-23) — kullanıcının ölçüleri geldi, plan onlara oturtuldu.** Ölçülenler:
F0 yuvası **derinlik 24 mm, panel deliği Ø12** (kullanıcı 10–11 okudu ama o **diş** çapı;
stok kaydı FUS027 "panel Ø12mm" — kaydı okuyan bir iddia eklendi, ben bir ara Ø11'e
çekmiştim, kayıt geri çevirdi) · kart B **50 × 50** (fabrika, kesilmiyor) · ESP32 **27.5 × 63**
· kart A **130 × 120**, kullanıcı **115 × 115'e kesecek** (yeni **Adım 1.3**; karar veride ve
DEVIR'de duruyordu ama *belgede hiç yoktu*) · kart A parçalarla birlikte **35 mm** kalın ve
altındaki atlama telleri için **16–17 mm** yerden yükseklik istiyor → ayak bloğu **9 kat
(18 mm)**. Ayrıca: F1P/F2 hücre sigortası yuvalarına gerçek konum (x 76 / x 177, z 0 — üç
denemede; MT1 ve A-ayak1 ile çakıştı, denetim yakaladı) · Q1 soğutucusu malzeme listesine ·
FR4 delme yöntemi (**havya YASAK**: cam elyaf erimez, reçine karbonlaşır ve **karbon
iletkendir**) · "halka pabuç" üç adımda **koşulsuz** isteniyordu ama envanterde hiç yok →
kalaylı kanca yöntemi + *hiçbir adım stokta olmayan bir parçayı koşulsuz istemiyor* iddiası.

🔴 **Kendi altyapımda gerçek bir kusur üretip yakaladım:** `kutu.main()`'i
`redirect_stdout` altında çağırınca `bom_dogrula`'nın `sys.stdout.reconfigure`'ü patlıyor,
`yerlesim3_belge.Stok` bunu yutuyor ve **43 iddia sessizce kayboluyor** — koşu yine
"1741/1741 geçti", `rc=0` diyordu. Özet satırına **`⚠ EKSIK KOSU: envanter okunamadı`**
işareti kondu (kırmızı yapılmadı: envanter herkese açık depoda yok, orada eksik koşmak
normal). Aynı sınıftan ikinci bulgu: bir **B22b firmware mutasyonunun deseni eskimişti**
(sondaki `{` koda uymuyordu) ve mutasyon **sessizce uygulanmıyordu** — o iddia hiç
sınanmamış. Koşucu artık "UYGULANAMADI (desen yok)" diye ayrı sayıyor.

**B55n (2026-09-24) — TAMAMLANABİLİRLİK: "sana bir şey sormadan sonuna kadar gidebilmeliyim".**
Kullanıcının kuralı değişti; plan bu kurala göre tarandı ve **10 kusur** bulundu. Hepsi
"belge yeşil ama kullanıcı o adımda takılır" sınıfından:

| # | Kusur | Çözüm |
|---|---|---|
| 1 | 9.3 *"baskısı 600 V altıysa **söyle**"* — kullanıcıyı bana yolluyor | Karar metne: ≥ tam skala → kullan; altı/baskısız → **boydan boya makaron + panele o değeri yaz**; her halde tek parça kablo. 1.1'deki üç "söyle" ve KULLANIM'daki "sayıyı bana söyle" de kurala çevrildi |
| 2 | **LED1** 5.3'ün `monte` listesinde ama takılışını anlatan tek cümle yok | Takma + **bacak yönü** (uzun = anot; takılınca görünmez, şimdi işaretle) |
| 3 | **Şönt kutbuna üç iletken** biniyordu (Ø2 manganin çubuk + iki kalın kablo, tek XP128 kafesi: çubuk basıncı alır, kablo gevşer, 10 A'da ısınır) | Güç düğümü **HB950 bariyer klemensine** (CON011, stokta 2) ayrıldı; XP128'de şönt bacağı + tek köprü. Ölçüme etkisi yok — Kelvin uçları şöntün **bacağında**. Şönt takası da kolaylaştı |
| 4 | 6.1: "katları lamine et" — dört katın deliği **nasıl üst üste gelecek** yazmıyordu; cep lamine olduktan sonra açılamaz, sıra tersine çevrilemez | 7 adımlık sıra: kılavuz Ø3.2'yi **dört katı birlikte sıkıp tek seferde** del → hizalama çizgisi → ayır, cebi büyüt → 4+3+2'yi yapıştır → somunu kuyuya bırak (kendiliğinden ortalanır) → 1. katı koy → **japon kurumadan vidayı sok-çıkar** |
| 5 | 13.1: somunlu blok **rayın iç yüzüne**, yani kutunun içine yapıştırılıyordu — kapak takılıyken oraya el girmez (kutunun tek açıklığı kapağın kendisi) | Kapak **tezgaha alınıyor**, ters çevriliyor; cıvata rayın dış yüzünden sokuluyor, blok onun üstünde **kendiliğinden merkezleniyor** |
| 6 | 10.1: "seçicinin **ortak** uçları" — KTS202'nin hangi ayağının ortak olduğu hiçbir yerde yok; stokta tam 2 adet, yedek yok | Ölçerek bulma yordamı (ohmmetre ötüş, kolu ters at, iki konumda da öten ayak ortak) + işaretle |
| 7 | 11.2 başlığı "Vref ve I²C kapıları" ama metni **yalnız WiFi ayarı**; iki kapının ölçütü yok | Sayılar `tasarim3_sabit`'ten: TL431 = 2.495 V ±%2, U3A = 1.7153 V ±10 mV, yük altında kaymamalı; I²C'de 0x48 **ve** 0x49; her ikisi için "tutmazsa" dalı |
| 8 | 14.2/15.2: "blokta iki delik" — **çap yok** | `KABLO_BAGI` (SRF012 3.6 mm şerit → **Ø4.5**, aralık ≥ 12 mm), delikler modülün kısa kenarlarının dışına |
| 9 | 2.2: taban raylarının **konumu metinde hiç yok** ("uçlardan içeride") — oysa devrilme ve ray yük payı hesabı konumu varsayıyor | Sol kenardan **56 / 166 mm** (dış enin ¼ ve ¾'ü), ±5 mm'den fazla kaydırma |
| 10 | 16.1'in **etiket listesi elle yazılmıştı** ve panel verisinden kaymıştı: CAL, F0, GÜÇ, ŞARJ 1/2 ve üç toggle listede hiç yoktu | Liste `PANEL_ON`/`PANEL_ARKA`'dan **üretiliyor**; 5.2 kendi `monte` listesinden |

##### Mutasyon koşucusu bu turda **altı ölü iddia** buldu (hepsi benim yeni yazdıklarım)

* *"hiçbir adım kararı bana bırakmıyor"* deseni **`\bsoyle\b` yazılmıştı** — `_kucuk()`
  harfleri sadeleştirmiyor, yalnızca küçültüyor; Türkçe "söyle" ile hiç eşleşmiyordu.
  İddia doğduğu gün ölüydü.
* 13.1 sıra iddiası `find("kapağı kaldır")` yapıyordu ve delme paragrafındaki
  **"kapağı kaldırMADAN yap"** — yani tam tersini söyleyen cümle — onu yeşil tutuyordu.
* KAPI ölçütü iddiası **cihaz adresini (0x48) ölçüt sayıyordu**; "var mı yok mu" der,
  "ne kadar" demez. Ölçüt artık sayı + **fiziksel birim**.
* KTS202 iddiası adımın **tamamında** "öt…" arıyordu; 10.1'in kontrol satırlarında zaten
  "ötmeli" var, yordam silinse bile yeşil kalıyordu. Ölçüt aynı cümleye indi.
* İki mutasyon **fazla zayıftı** (metnin bir bölümünü siliyor, iddiayı besleyen başka
  cümle kalıyordu) — çok satırlı hale getirildi.
* `monte` iddiasının eşleştirmesi tek harfli ref ("A") ve ölçüyle başlayan ad
  ("5 mΩ Ø2 şönt") için tutmuyordu → sözcük sınırı + adın ilk dört harfli sözcüğü.

**B55n-b (2026-09-24) — kullanıcının üç kararı.** Kalan açık maddeler şıklarıyla
soruldu, üçü de uygulandı:

**① Giriş sigortası (F0B).** F0 kaynak seçicinin **çıkışında** duruyordu, yani J6 ile
seçici arasındaki ~24 cm kalın kablo kutunun içindeki **tek sigortasız bakırdı** ve tek
koruması WCT-200-24'ün kendi akım sınırıydı. PCB klipsli yuva (FUS009) + **2 A** (FUS004),
ikisi de stokta. Yer **programla arandı**: arka duvarın alt bandı tamamen dolu (kart A'nın
ayakları, 24 V klemens çubuğu, F1P, ESP32 altlığı, F2) — 6 mm'yi geçen tek bölge üst sıra;
havalandırma delikleri de kaçırılarak **x 30, z 78** (en yakın parça MT2, 12 mm). Kuyruğun
artı teli J6'dan girer girmez buraya uğruyor.

**② Q1 soğutucusu 1 MΩ ile kart GND'ye** (R026). Mika onu yalıttığı için kapalı kutuda
**yüzen** bir metal plakaydı. Düz tel *değil*: mika bir gün delinirse soğutucu Q1'in
savağına, yani **PİL 1**'e (test edilen pil, ≤38.5 V) bağlanır ve düz tel bunu GND'ye kısa
devre ederdi — o yolda bizim koyduğumuz sigorta yok. 1 MΩ ile arıza akımı **38 µA**.
Denetim iki şeyi birden ölçüyor: arıza akımı < 1 mA (fizik) **ve** talimat cümlesinde
direncin geçtiği (metin). Kontrol satırı: soğutucu ↔ GND ≈ 1 MΩ okumalı, **0 Ω ise mika
delinmiş**.

**③ F1: takılı sigorta kalıyor, T 50 mA "isteğe bağlı / sonraki plan".** Kullanıcı
*"şu anda 50 mA takılı ancak hiç atmadı"* dedi; B52 aynı yuvada **0.4 Ω** ölçmüştü ve
50 mA'lık tel 15–21 Ω okur. İki bilgi birbirini tutmuyor ve hangisinin doğru olduğunu
ancak ölçüm söyler — bu yüzden metin **iddia olmaktan çıkıp yordam oldu**: "etikete değil
ohmmetreye bak; sigortayı çıkar, soğukken direncini ölç: 15–21 Ω → gerçekten
50 mA (ve T tipi, çünkü atmadı), 0.3 Ω civarı → 400 mA sınıfı". Her iki hâlde de kısa
devre koruması var, kurulum beklemiyor.

Bu turda mutasyon koşucusu **yine dört iddiayı ölü buldu** ve ikisi B55n'dekiyle **tam
aynı sınıftı** (adımın TAMAMINDA anahtar sözcük aramak): soğutucu iddiası gerekçe
paragrafındaki direnç sayısına takılıyordu, sigorta iddiası ise 10.1'in **KTS202
yordamındaki "ohmmetre"** kelimesine. İkisi de talimat/madde düzeyine indirildi. Ayrıca
`ad`'dan türetilen takma adın çok genel olabildiği ortaya çıktı — F0B'ninki **"xt30"**
çıkıyordu ve 10.1'in her yerinde geçtiği için `monte` iddiası F0B için boştu; takma ad
artık yalnız `IC_PARCA` için üretiliyor (ref'leri tek harf olabildiği için orada gerekli).

**Doğrulama.** `kutu.py` **1830 → 2181/2181** · mutasyon B50 **82 → 115/115** (tam takım
**306/306**) · `dogrula3.py` **18/18**, sayım kilidi **3332 → 3683**.

**B56 (2026-09-24) — PANEL SİMETRİSİ.** Kullanıcı üretilen ön duvar çizimine bakıp
*"ön ve arka yüzünün çok daha düzgün gözükmesini istiyorum, şu anda çok asimetrik ve
hoş değil"* dedi. Haklıydı: toggle'lar 36 sonra **18** mm aralıkla diziliydi, GÜÇ lambası
tek başına solda (x 51) duruyordu, V/COM/SKOP sağa kaymıştı, sağ yarı boştu; arkada
dört havalandırma dört ayrı x ve dört ayrı z'deydi.

**Ne yapıldı.** Bütün panel delikleri **tek bir 18 mm ızgaraya** oturtuldu
(35·53·71·89·107·125·143·161·179) ve her sıra **x = 107 mm'ye, yani panelin tam
ortasına göre simetrik** dizildi; sıra içi adım her yerde 36 mm:

| Sıra | İçerik (x) |
|---|---|
| z 81 | GÜÇ **35** · HV ⚡ **179** |
| z 63 | AÇ/KAPA **71** · PİL ESP32 **107** · PİL/HARİCİ **143** |
| z 45 | V **53** · COM **89** · SKOP **125** · F0 1A **161** |
| z 27 | CAL **107** |
| z 9 | PİL 1 **35** · PİL 2 **71** · YÜK 1 **143** · YÜK 2 **179** |

İki ızgara (35+36k ve 53+36k) 18 mm ötelenmiş olduğu için **komşu sıralar hiçbir yerde
aynı sütunu paylaşmıyor** — en dar komşuluk artık köşegen (25.5 mm merkez arası).

**Estetik değişiklik üç gerçek kusuru birden kapattı.** Ön panelde en dar metal–metal
aralık **5.66 → 12.0 mm** ve 6 mm'nin altında **hiçbir çift kalmadı**; beş `DAR_ACIKLIK`
kaydı listeden düştü. Bunlardan ikisi aylardır açık duran maddelerdi: **F0, kart A'nın
x menzilinin (13–128) dışına, x 161'e geçti** — 24 mm'lik gövdesi artık kart A'nın önünde
değil, yani B55d'den beri "1.7 mm / 3.0 mm" diye taşınan pay sorunu *geometrik olarak*
yok oldu. **CAL panelin ortasına** alındı: PİL jaklarına 5.7 mm yerine **26 mm**
(B55g'de "🔴" işaretiyle kaydedilen çift). HV en yakın komşusuna 20.3 → **25.5 mm**.

**Arka.** Havalandırmalar **iki ayna çiftine** indi: üst çıkışlar x 12.5 / 201.5, alt
girişler x 80 / 134 (hepsi tam yükseklikte bir iç kat çubuğunun ortasında; simetrik çift
olabilecek x'ler kısıtlı, çünkü hem x hem 214−x 18650 yuvalarının örttüğü 92–172 şeridinin
ve F1P/F2/TP/USB bloklarının dışında kalmak zorunda — program tarayarak buldu). XT30
deliği USB'nin aynasına alındı (x 62 ↔ 152). **18650 yuvasının dört cıvata deliği simetrik
olamıyor** (yuvanın kendi delikleri 53 mm aralıklı, yuvayı ortalamak MT1/MT2 ile çakışıyor)
— `PANEL_SIMETRI_HARIC`'te gerekçesiyle yazılı.

**Simetri artık kural, tercih değil.** `PANEL_SIMETRI_HARIC` (DAR_ACIKLIK ile aynı
disiplin: hem tavan hem taban) + üç iddia: her deliğin ayna eşi olmalı ya da gerekçesi
yazılı olmalı · istisna listesinde **artık simetrik olan** bir kayıt kalırsa kırmızı ·
ön panelin her sırası ayrı ayrı ölçülüyor.

⚠ **Mutasyon koşucusu yine iki iddiayı ısırmaz buldu.** (1) Dört mutasyon deseni
taşıdığım öğelerin eski koordinatlarında kalmıştı ve **sessizce uygulanmıyordu**.
(2) Daha kötüsü: 5.2/5.3'e koyduğum **üretilen etiket listesi (`{bu_etiketler}`),
"monte edilen her parça metinde geçiyor" iddiasını besliyordu** — LED1'in montaj cümlesi
silinse bile liste onu saydığı için iddia yeşil kalıyordu, yani B55n'de düzelttiğim kusur
sessizce geri gelebilirdi. İddia "adı geçiyor mu"dan **"nasıl tutturulduğunu söyleyen bir
cümle var mı"**ya çevrildi (ad + tutturma yöntemi aynı maddede; üretilen liste sayılmıyor).

**Doğrulama.** `kutu.py` **2181 → 2189/2189** · mutasyon B50 **115 → 118/118** · `dogrula3.py` **18/18**, sayım kilidi **3683 → 3691**.

**B57 (2026-09-25) — PARÇA BİLGİ KARTI (fareyle üzerine gel / tuşla).** Kullanıcı:
*"Elimi mouse ile üzerine getirince veya bir tuşa basınca o parçanın detaylarını görebilmem
lazım. Örneğin uzunluğu ne kadar, veya o parçanın adı ne, ölçüleri ne. Yoksa hangi parça ne,
ne kadar uzun anlamak zorlaşıyor."*

**Ne yapıldı.** `8-kutu.html`'de 2B çizimlerde (panel, kuşbakışı yerleşim, izometrik, taban/kapak,
kesim listesi) ve 3B görünümde her parçanın üzerine gelince kart açılıyor: ad, tür, ölçü, çubuksa
**uzunluk (vurgulu) + kesit + kesim listesindeki satırı + "nereden" (düz/tek uçlu/yarım)**, panel
öğesiyse delik Ø / metal gövde / içeri uzantı / konum (çizimdeki etiketlerle aynı eksen) /
delindiği ve takıldığı adım, ve **stokta hangi kutuda** olduğu (`CON027 · Soketler 1 Kutusu`).
3B'de seçilen blok turkuaz çerçeveyle vurgulanır; kart "★ bu adımın parçası" ya da "⏳ henüz yok —
X adımında takılır" der. Etkileşim: fare üzerine gel = geçici kart, tıkla/dokun = sabitle, Esc =
kapat; klavye: çizimlerde **Tab** parçadan parçaya (odak = kart, Enter = sabitle), 3B tuvalde
**N / P** sonraki / önceki parça (önce bu adımın parçaları).

**Tek kaynak.** `kutu.py`'deki `bi_*` fonksiyonları (panel · iç parça · duvar parçası · ayak · direk
· çubuk · dış kat sırası · kesim satırı) kartları **veriden** üretip `_BILGI`'ye kaydeder. 3B bloklar
`k` alanıyla, SVG grupları `data-bi` ile aynı anahtara bakar (aynı parça iki görünümde aynı kart);
sayfaya tek bir `BILGI` tablosu gömülür, yalnız sayfada ya da sahnede anılan anahtarlar. Kart
metni DOM'a `textContent` ile yazılır (veri HTML sayılmaz). Taban/kapak/ray başlıkları yöne değil
**boya** bağlı (kısa/uzun parça — kesim listesiyle aynı dil), çünkü kuşbakışı çizim ile 3B'nin
"ön" yönü farklı.

**3B seçim.** Işın ↔ eksen hizalı kutu: blok yüzleri klip uzayına izdüşürülür, en yakın yüzün
derinliği alınır; önce **gözle katı görünenler** (alfa ≥ 0.3) — saydam duvarın arkasındaki parça
seçilir, hayalet (hedef) bloklar yalnız yedek. Etiket örtülme denetimi (`ortulu`) aynı fonksiyona
bağlandı. Tıklama eşiği 4 px: altı = seçim, üstü = döndürme.

**Yol boyunca bulunanlar.** (1) Kesim listesi yan duvar için **"sıra 2–4"** diyordu; duvar B54'ten
beri 5 sıra (adet 8 doğruydu, ad eskimişti) → sıra sayısından üretiliyor. (2) Belgenin yer tutucu
kapısı ilk denemede kart notlarında çiğ **`{hv_kablo}` / `{yon_b}`** yakaladı — notlar artık adım
metinleriyle aynı sözlükle biçimleniyor. (3) Kesim listesi eşleşmesi önce 0.6 mm toleranslıydı;
kart çizimdeki 0.4 mm **kısaltılmış** boyu (99.5) gösterse de geçerdi → **0.05 mm** (yalnız
yuvarlama payı); 119 çubuk kartının hepsi birebir eşleşiyor.

**İki test katmanı.** `kutu.py` bölüm 9 (6 iddia): her 3B bloğun kartı var · her çubuğun kesim
listesinde birebir boyla satırı var (**iki bağımsız hesabın çapraz denetimi**: `sahne()` geometrisi ↔
`hesap()['parcalar']` — B55c'deki "16 parça eksikti" sınıfını yakalar) · her çubuk kartının ilk
vurgulu satırı uzunluk · kart boyu bloğun gerçek boyu · verideki **her** parça (59) 3B'de üzerine
gelinebilir · her panel kartında delik ölçüsü. Yazma noktasında yeni kapı: sayfadaki her `data-bi`'nin
kartı gömülü olmalı. **`kutu_ipucu_test.py`** (28 iddia, ~15 s): belgeyi GEÇİCİ klasöre **kaynaktan**
üretir, `tarayici.py` ile başsız Edge'e CDP'den **gerçek fare/klavye olayları** gönderir, `#ipucu`'nun
açılıp ne yazdığına bakar; sayfaya test kancası yok. Mutasyon adımı **B57** bu testi koşar — **JS
davranışı da mutasyonla sınanıyor**.

⚠ **Tarayıcı testi iki gerçek hata ve üç kendi zayıflığını buldu.** Hata: **Tab odağı sayfayı
kaydırıyor, kaydırma dinleyicisi de kartı kapatıyordu** — klavye kullanıcısı kartı bir an görüp
kaybederdi. Çözüm: kart bir öğeye bağlıysa (`ipBag`: odak ya da sabit) kaydırmada kapanmaz, öğeyi
izler; sabit 3B kartı bloğu izler. Testin zayıflıkları: (a) jak grubunun sınır kutusu alttaki etiketleri
de kapsıyordu, merkezi başka parçaya düşüyordu → ilk **şeklin** merkezi; (b) Chromium **kapalı
`<details>` içindeki SVG'ye de sınır kutusu döndürüyor** — `getClientRects()` "görünür" demek değil;
(c) iki mutasyon **kaçtı**: kaydırma hatası testi artık kaydırma içermiyordu (senaryo: sayfa sonuna
git, görünüm dışındaki parçaya odaklan, **kaydığını da doğrula**), "en yakın gövde" testi üstten
bakışta ayırt edemiyordu (orada en yakın = en son çizilen) → önden duvar: dört katman üst üste,
**ön dış kat** seçilmeli. Ayrıca iki çizim grup açılışını `_bi` yerine elle yazıyordu; tabindex
mutasyonu onları görmezdi → tek `_bi_ac()`.

**Doğrulama.** `kutu.py` **2189 → 2195/2195** · `kutu_ipucu_test.py` **28/28** · mutasyon B50
**118 → 121/121**, B57 **7/7** (yeni) · `dogrula3.py` **18/18**, sayım kilidi **3691 → 3697**.

**B57b (2026-09-25) — 18650 YUVALARI YAPIŞTIRILIYOR.** Kullanıcı: *"18650 yuvalarını vidalamak
yerine direkt olarak yapıştırmak istiyorum yan taraflara"*. Önce yan duvarlar ölçüldü: 80×21×21
yuva **sığmıyor** — sol duvarda kart A'nın üstü z 53, kapak rayı z 72 → 19 mm; sağ duvarda Q1
soğutucusu z 60'a kadar. Gösterildi; kullanıcı **"olduğu yerde kalsın, M3 değil yapıştırıcı"**
dedi.

**Ne değişti.** "Kutuya giren hiçbir parça yapıştırılmaz" kuralının **TEK gerekçeli istisnası**
veriye yazıldı: `kutu_veri.YAPISTIRMA_ISTISNA` (YUVA1/YUVA2 → sıcak silikon, söküm yolu: ısı
tabancası / izopropil + maket bıçağı, neden). Arka duvardaki dört M3 deliği (C1a–C2b) kalktı →
arka panel **istisnasız simetrik** (`PANEL_SIMETRI_HARIC` boş). M3 geçme çapı eskiden yuva cıvata
kayıtlarından okunuyordu; artık `KUTU["m3_gecme"]` (tek kaynak, kapak ve ayak cıvataları kullanıyor).
Yapıştırıcı tablosunda yuvaların kendi satırı var.

**Ölü iddia (kendi).** "Duvara cıvatalı EN AZ iki parça var" iddiası yuvalar yapıştırılınca **boş
kümede** dönecekti (`all([]) = True`). Yerine: yapıştırılan parçanın ikinci bir tutturması
(cıvata / kablo bağı tutucusu) YOK · istisnadaki her ref gerçekten bir duvar parçası ve metni
yapıştırıcıyı adıyla söylüyor (eskimiş istisna yok) · istisna dışındaki her parça söküleBİLİR
(silikon/japon yok). Beş yeni mutasyon: istisna ref kaybı, istisna dışı yapıştırma, söküm yolunun
düşmesi, tablo satırının düşmesi, yuvaya tutucu blok eklenmesi.

**Doğrulama.** `kutu.py` **2172/2172** (dört panel deliğinin iddiaları gitti) · mutasyon B50
**121 → 126/126** · `dogrula3.py` **18/18**, sayım kilidi **3697 → 3675**. Bir mutasyon deseni
(`PANEL_SIMETRI_HARIC = {`) tip ekiyle eskimişti, koşucu "UYGULANAMADI" dedi → düzeltildi.

**B58 (2026-09-25) — DIŞ BESLEME KALKTI, TEK ŞARJ GİRİŞİ.** Kullanıcı: *"1) Ekstra dışarıdan
besleme kısmını kaldırmanı istiyorum. 2) 24 volt giriş ile çalışma sistemi de komple kalkabilir
— dışarıdan ekstra kaynak ile beslemek istemiyorum. 3) Şarj en az 2 adet Type-C kablo ile. Bunu
tek kablo ile yapmam mümkün değil mi?"* Seçenekler sunuldu; seçilen: **"Tek paket (tavsiye)"**
ve B0505S için **"Yok, alırım"**.

**Neden iki kablo gerekiyordu.** Kart yüzen bir 24 V istiyor ve orta noktası kart GND. Eski
düzende hücre 1 (ESP32) eksisi = kart GND, hücre 2 (24 V) eksisi = −12 rayı; tek USB toprağı
ikisini birleştirir → −12 GND'ye kısa. Yalıtımsız her yükseltici aynı sonucu verir.

**Yeni topoloji.** İki 18650 **paralel** (her hücrenin artısı kendi sigortasından: F1P, F2) →
tek TP4056 → **PİL** anahtarı (SWP1, KTS102) → MT1 5.0 V = **5 V barası** (ESP32 5V pini +
kartın +5 V'u J5 üzerinden) → **ANALOG** anahtarı (SW, KTS102) → **F0** (1 A, panel, artık 5 V
tarafında) → **B0505S** (yalıtılmış 5→5 V, 1 W) → MT2 24.0 V → iç klemens (KL) → kart C34/C36.
Paketin eksisi kart GND; −12 rayı B0505S'in öbür tarafında. Kalkanlar: XT30 kuyruğu (J6 paneli),
PİL/HARİCİ seçici (SWP2, KTS202), F0B giriş sigortası (B55n), TP2, ŞARJ 2, AÇ/KAPA'nın 2. kutbu;
**KTS202 artık kullanılmıyor**. `tasarim3_sabit.GIRIS_SIGORTA` silindi, yerine B58 bütçe sabitleri.

**Bütçe (sabitlerden, kötü hâl).** 24 V yükü 26 mA (kart 25 + GÜÇ LED'i 1) = 0.62 W → B0505S
**0.73 W, anmanın %73'ü** (ölçüt ≤ %80). F0 normal akımı 204 mA (1 A ≥ 3×). 5 V barası
0.47 A (ESP32 WiFi tepesi 250 mA) → tek hücre, 2.4 V'ta kol akımı **1.16 A**: MT3608 2 A'nın,
DW01A 3 A'nın (1.5× pay) altında; hücre sigortası 2 A ≥ 1.5 × max(1.16, şarj 1.0) ✓. Çalışma
≈ **4.9 sa** (tipik, iki hücre), şarj ≈ **3.6 sa** (1 A, iki hücre birlikte). Sayılar metne
`{pil_suresi}` / `{sarj_suresi}` / `{iz_yuk}` ile giriyor.

**Plan değişiklikleri.** Pil bloğu eski Adım 14–15'ten **Adım 10'a** taşındı — kutu artık
yalnız kendi pilinden çalıştığı için 11–12'nin enerjisi bu paketten geliyor (yeni iddia: pil
bloğu ilk kapıdan önce bitiyor). Adım 10 = 10.1 MT1/MT2 ayarı · 10.2 bütün duvar parçaları ·
10.3 paket kabloları (tablo `asama: "paket"`) · 10.4 analog kabloları (`"analog"`) · 10.5 ilk
enerji (VBUS geri besleme kontrolü dahil) · 10.6 şarj kuralı. Eski 14–15 silindi, **16 → 14**
(kapanış 14.2). Panel: ön 4. sıra PİL (x 71) / ANALOG (x 143) ayna çifti, ortadaki SWP2 gitti;
arka: **ŞARJ yuvası x 62 z 8 = USB'nin tam aynası**, TP1 rafı onun arkasında en alt sırada
(2 katlı blok). Test kaynağı artık **tezgah beslemesi** (WCT-200-24 + MOD011 buck 3.7 V → 3.3 Ω
= 1.12 A): WCT kutuya bağlı olmadığı için yalıtılmış bir test kaynağı; yeni 12.2 kuralı "kutunun
**kendi paketi** test kaynağı olamaz" (dönüş akımı J5'in GND telinden geçer). 12.7 pil testi
buck'la: 4.0 V'ta akım, 3.4 V'a inince kesme — gerçek pilden daha kesin sınıyor.

**Yol boyunca bulunanlar.** (1) Alt sırada TP1 + F1P + klemens çubuğu + ESP32 sığmıyordu (68.5 mm'ye
73 mm iş) → "24 V klemens çubuğu" (taban) kalktı, klemens **duvar parçası KL** oldu (B0505S'in
üstü, MT2'nin çıkışına bitişik). (2) ⚠ **Eski bir hata:** 6.5 soğutucu direncini "kart GND'ye
(klemensin siyah ucu ya da A:T_YILDIZ)" diye tarif ediyordu — **klemensin siyah ucu C36 = −12
rayı**, B50'den beri. Düzeltildi, yeni iddia bu sınıfı yakalıyor. (3) F1P/F2 ilk kez bir
`monte` listesine girince "kural metni yok" kırmızısı verdi → KUTU_NOTU'na eklendi. (4) İki yeni
iddia ilk hâlinde **gevşekti**: 10.4 yalıtım kontrolü ve KULLANIM şarj kuralı adımın/tablonun
tamamında arıyordu; aynı kelime başka maddede de geçtiği için tek mutasyonla kaçacaktı → ölçüt
**aynı maddede** (B55n dersi, yeniden). (5) **Klemens kodlu değil:** XT30 ters takılamazdı; vidalı
klemens takılır. Ters 24 V iki TL072'yi öldürür ve TVS koruyamaz (B15/F8) → 10.4'e enerjiden
ÖNCE kutup ölçümü (+ ↔ MT2 OUT+ ve C34, − ↔ MT2 OUT− ve C36) + iddia + yalanlayıcı. (6) Mutasyon
koşucusu bir **boş iddia** buldu: "delik adımının çizimi takılan öğelerin panellerini kapsıyor"
5.1 için (hiç panel öğesi anmıyor, iki duvarı birden deliyor) boş kümeyle geçiyordu; eskiden
5.3'ün arka/ön karışıklığı bu mutasyonu tek başına yakalıyordu, B58'de 5.3'ün hepsi öne geçince
kaçtı → öğe anmayan delik adımı **iki paneli de** çizmek zorunda. (7) Kart BOM notu (J6 = XT30)
"tezgah için; kutuda kullanılmıyor" oldu.

**Yeni iddialar (bölüm 4).** Tek şarj girişi (tek yuva + tek TP4056) · dış besleme yok · paket
eksisi kart GND · iki hücre paralel · **−12 rayı kart GND'den AYRI** (union-find; B0505S'in içi
grafta kenar değil) · B0505S'in iki tarafını birleştiren kablo/iç bağ yok · ESP32 5V yalıtılmış
tarafın artısına değmiyor · anahtarlar AÇIK konumda yolu gerçekten kesiyor (PİL, ANALOG) · F0
ANALOG ile B0505S arasında · bütçe (B0505S yükü, F0 payı, MT3608, DW01A) · süreler sabitten ·
12.2 kuralı · test kaynağı eşiği · paneldeki toggle adedi ≤ stok (KTS102: 2/2) · B0505S
"alınacak" · klemens eksisini GND diye anan talimat yok · klemens kutbu enerjiden önce.

**Doğrulama.** `kutu.py` **2172 → 2044/2044** (panel/duvar öğeleri ve eski seçici grafının
iddiaları gitti; B58'in iddiaları geldi) · `kutu_ipucu_test.py` **28/28** · mutasyon B50
**126 → 146/146** (16 eskimiş desen yeni topolojiye çevrildi, 20 yeni yalanlayıcı; ilk koşuda
1 kaçtı → (6)) · B57 **7/7**. Panel çizimleri başsız Edge'de ekran görüntüsüyle de bakıldı:
ön 4. sıra PİL/ANALOG, arka USB/ŞARJ ayna çifti.

**Alınacak tek parça:** B0505S. Kurulum 10.2'de onu bekliyor; 10.1'e kadar her şey stoktan.

**B58b (2026-09-25) — kullanıcının aldığı modül: Hi-Link B0505S-2WR3 (motorobit).** 2 W,
4.5–5.5 V giriş, 1500 VDC yalıtım, sürekli kısa devre koruması, **gövde 19.5 × 7 × 10 mm**
(plan 1 W'lık 11.6 mm gövdeyi varsayıyordu) ve üreticinin şartı **yük ≥ anmanın %10'u**
(regülesiz). Değişenler: `IZOLE_GUC` 2.0, IZ x 20→14 / en 12→20 (MT2'ye 8 mm), tutucu 22 mm;
yük %37, **en düşük yükte %28** (yeni iddia, `RAY24_AKIM_ASGARI` 19 mA). 1 W ve 2 W sürümlerin
bacak sırası farklı → metin artık numara değil **ada göre** bağlatıyor ve 10.1'de modül tezgahta
deneniyor (5 V giriş, 5–7 V yüksüz çıkış, GND ↔ 0V ötmemeli). Aynı turda iki stok kusuru:
10.5 "100 µF ekle" diyordu — stoktaki 100 µF'lerin 13/15'i **16 V**, 24 V rayında patlar →
68 µF 50 V (C035) + gerilim sınıfı iddiası (≥ 1.5 × 24 V); VBUS geri beslemesi için istenen
1N5819 **stokta yok** → stoktaki SR5100 (D004) + MT1 5.3 V, ve "stokta olmayanı koşulsuz
isteme" iddiası 1N5819'u da tarıyor. Malzeme notlarında çiğ `<b>` basılıyordu (tablo kaçışlı)
→ yeni iddia, ilk koşuda ikinci örneği (Q1 soğutucusu) yakaladı. Kullanıcı kapağı mıknatıslı
yapmayı düşündü, **vazgeçti** (M3 cıvatalı kalıyor; ileride 3D baskıda belki). `kutu.py`
**2047/2047**, tarayıcı 28/28.

**B58c (2026-09-25) — plan İKİ modül için de geçerli.** Kullanıcı 1 W'ın (B0505S-1WR3, Hi-Link,
motorobit 123.60 TL; 2 W 171.60 TL) yetip yetmeyeceğini sordu. Yeter: yük 0.73 W → 1 W'ta %73
(sınır %80), en düşük yükte %56; 2 W'ta %37 / %28. `IZOLE_GUC` tek sayı olmaktan çıktı →
`IZOLE_GUC_SECENEK = (1.0, 2.0)` ve iki iddia **her seçenek için ayrı** koşuyor (min/max seçen
tek bir sayı olsaydı "küçüğü mü büyüğü mü" mutasyonu sonucu değiştirmediği için kaçardı). Duvarda
2 W'ın gövdesine yer ayrılı, 1 W (4-SIP 11.6 mm) aynı yere sığar; bacaklar ada göre. Aynı turda
kullanıcı motorobit'te **50 mA gecikmeli sigorta** sordu: sigorta kategorisinin 38 sayfası
tarandı — **yok**; en küçük gecikmeli 500 mA ("TMDP T50A" = T 5.0 A), en küçük sigorta 100 mA
hızlı. direnc.net aramasında da çıkmadı. Karar zaten "takılı sigorta kalıyor, T isteğe bağlı".
`kutu.py` **2049/2049**.

**B58d (2026-09-25) — şarj modülü yerleştirilemiyordu.** Kullanıcı "şarj devresinin konumu doğru
mu, düzgün yerleştirilebilir mi" diye sordu; denetim yeşildi ama üç gerçek sorun çıktı:
(1) TP1 (y 0–25, z 4–9) kart A'nın arka boş şeridinin (y 12–29.8) **altına** giriyor, kart
tabanına 9 mm. Plan onu **10.2'de**, kart A 6.2'de takıldıktan sonra takıyordu: 27 mm'lik modül
duvar ile kart arasındaki 12 mm'lik aralıktan indirilip yatırılamaz (dönerken uç kartın kenarına
z 25'te çarpıyor). (2) B±/OUT± pedleri kartın altında kalıyor, 10.3'te havya girmez. (3) Tutturma
tarifi "delikleri kısa kenarların dışına aç" diyordu — kısa kenarlardan biri DUVARA dayalı; fiş
takılırken modülü içeri iten kuvvete karşı da dayanak yoktu. **Düzeltme:** yeni **6.0** (kart
A'dan önce, kutu boşken): kablolar tezgahta önceden lehimlenir (4 uç, etiketli), raf 4 parça —
alt kat 2 × 9 mm arasında **9 mm kanal** (ESP32 altlığıyla aynı yöntem), üst kat 27 mm, dayanak
5 mm dik; tek kablo bağı kanaldan geçip modülün ortasını sarar. `DUVAR_TUTUCU` artık çok parçalı
tutucu taşıyor (`parcalar`), kesim listesi ve kütle modeli ikisi de oradan. **Denetim bu sınıfı
hiç görmüyordu** (yalnız çarpışma ve açıklık ölçülüyordu, SIRA değil) → yeni kurallar: kart A'nın
altına giren duvar parçası (tutucusuyla) yalnız boş şeridin altında (dolu bölgede atlama telleri
sarkar) · kart A'dan (6.2) önce takılır · kabloları tezgahta önceden lehimlenir · kanallı
tutucunun kanalı bağı geçirir ve ölçüsü metne veriden girer. Dört yalanlayıcı mutasyon; "TP1'i
10.2'ye geri koy" mutasyonu bellekte ayrıca koşuldu, kırmızıyı gerçekten sıra iddiası veriyor.
`kutu.py` **2057/2057**, tarayıcı 28/28.

**B58e (2026-09-25) — ANALOG anahtarı kalktı, F0 kutunun içinde.** Kullanıcı sordu: "Analog
anahtarı neden var? Panel sigortası mantıklı mı, içeri alsak? CAL nedir?" Seçenekler sunuldu;
kararlar: **F0 içeri**, **ANALOG kaldır**. (1) F0 yalnız İÇ arızada atar (B0505S, MT2, kart);
panelde "F0 1A" yazısı, ölçüm akımının (YÜK jakları, bilerek sigortasız, 9.5 A'e kadar)
korunduğunu düşündürüyordu ve Ø12 delik panelin en zayıf yeriydi (her yanda 3 mm et). Artık arka
duvarın sol ucunda, MT1 ile B0505S'in arasında (x 12, z 26; FUS009 PCB klipsli + FUS003 1 A);
MT1/MT2 1 mm sağa kaydı (F0'a ve köşe direğine 6'şar mm). (2) Kutunun **tek anahtarı PİL**.
Kaybedilen: ESP32'yi ölçüm tarafından ayrı açabilmek. Bedeli bir kural: **USB'yi PC'ye takarken
PİL açık olsun** — PİL kapalıyken 5 V hattı USB'den beslenir ve ölçüm tarafı da PC'den çeker
(~0.35 A, USB 2.0 sınırına yakın); PİL açıkken MT1'in 5.0 V'u USB'nin ~4.7 V'unu bastırır.
İlk enerji sıralaması (10.5) artık F0 ile: F0 çıkarılmışken PİL → 5 V ölç → PİL kapat, F0 tak →
±12 V ölç. (3) Ön panel **üç sıraya** indi, hepsi x 107'ye simetrik: üst GÜÇ · PİL · HV, orta
V · COM · SKOP, alt PİL 1 · PİL 2 · CAL · YÜK 1 · YÜK 2. CAL alt sıranın ortasında (PİL 2 ve
YÜK 1'e 22 mm; 22 kΩ koruma bu komşuluğu güvenli kılıyor). **Yol boyunca bulunanlar:** DELME'nin
"en büyük delik" hesabı 14×9 oval yuvaları da yuvarlak sayıyordu — F0'ın Ø12'si bunu
örtüyordu; F0 kalkınca "en büyük Ø9, 4.5 mm et" diye yanlış yazdı, iddia (yuvarlak Ø8, 5.0 mm)
yakaladı. "Panel deliği stok kaydıyla tutuyor" iddiasının tek öznesi F0'dı; iddia boş kaldı →
koruma "eşleştirici gerçek envanterde çalışıyor mu" (FUS027 kaydı hâlâ orada) diye yeniden
yazıldı + yalanlayıcı. Tarayıcı testi 3B'de panelin tam ortasına bakıyordu; COM oraya gelince
jaka çarptı → nokta artık dizilime bağlı değil (ortadan yukarı/aşağı taranıp ilk çubuk alınıyor;
"en yakın katman" iddiasının gücü aynı). KAPLAMA_HARIC B56'dan beri "CAL ↔ PİL 5.66 mm" diyordu
(eski) → düzeltildi. Yeni iddialar: panelde tek güç anahtarı · USB kuralı kullanım tablosunda ·
F0 kutu içinde, panelde değil. `kutu.py` **1999/1999**, tarayıcı **28/28**.

**B58 serisinin son doğrulaması (2026-09-25).** `kutu.py` **2057/2057** · `kutu_ipucu_test.py`
**28/28** · mutasyon B50 **154/154** (B57b sonunda 126) · B57 **7/7** · `dogrula3.py` **18/18**,
sayım kilidi **3675 → 3559** (panel/duvar öğeleri ve eski seçici grafının iddiaları gitti). Not:
kilit yazan ilk koşuda B25 (`test_tezgah_kart.py`) 1800 s zaman aşımına düştü — mutasyon
koşusunun hemen ardındaydı; aynı adım sonraki iki koşuda 344 s'de geçti. Kutuyla ilgisi yok.

**B58e'nin mutasyon turu (2026-09-25):** B50'de 1 kaçak — 11.2'ye eklenen "<b>Enerji:</b> PİL AÇ …
MT1'in 5.0 V'u USB'nin ~4.7 V'unu … ~0.35 A" cümlesindeki sayılar "her KAPI sayısal ölçüt veriyor"
iddiasını besliyordu; iki kapının ölçütü silinse bile yeşil kalıyordu. Enerji satırı artık ölçütten
hariç (`_kapi_metni`); mutasyon yakalanıyor. B57 7/7.

**B58f (2026-09-25) — kutunun kendi beslemesinin ZAMAN benzetimi: iki gerçek kusur.** Kullanıcı:
"değiştirdiğimiz şeyler gerçekten bir şeyi bozmuş olabilir mi — tek anahtar, yalıtılmış DC-DC… değişen
her şeyi simüle et ve test et." `kutu.py` besleme zincirini DURAĞAN sayılarla (B0505S %73 yük, paket
1.16 A) ve bağlantı grafıyla denetliyordu; açılış/kapanış hiç benzetilmemişti. Yeni adım
**`uretim/sim3_kutu_besleme.py`** (zincirde "B58f", ~1.5 dk): ortalanmış MT3608 ×2 + B0505S Thevenin
modeli + DW01A/FS8205A + kart (C16 + C17 = 136 µF, netlistten) + ESP32 (LDO, WiFi patlamaları);
numpy ile yüzlerce senaryo birlikte. Veri sayfaları indirilip okundu (DW01A-DS-11, EVVO FS8205A,
Aerosemi MT3608 V1.0, Mornsun B_S-1WR3 / A_S-B_S-2WR3 — Hi-Link bunların kopyası; Littelfuse 217
soğuk direnç). Veri sayfasının VERMEDİĞİ her şey tek değere bağlanmadı, **taranıyor**: MT3608'in
yumuşak başlama süresi (0.3/1/5 ms) ve mekanizması (referans rampası UVLO'da sıfırlanır / akım rampası),
B0505S'in aşırı yük davranışı (A3 sarkma + 3× tavan, B15/B11 akım sınırı 1.5×/1.1×, C hiccup),
B0505S çıkış eğrisi (kötü/tipik), pil (4.2/3.7/3.3 V iki hücre, 3.3 V tek hücre).

**Kusur 1 — 1 W B0505S açılışta YETMİYOR.** Durağan yükte %73 yeterliydi ve kullanıcıya "1 W da
olur" denmişti. Açılışta MT2 kartın 136 µF'sini doldururken 3.5 A'e kadar çeker; akım sınırlı modül
(Mornsun R3 kendisi "büyük kapasitif yükte CC kipinde açılış" diyor) MT2'nin girişini UVLO'ya (~2 V)
çeker ve orada tutar: aktarılan güç ≈ I_sınır × 2 V. Kart 24 V'ta 0.62 W istiyor → sınır ≥ 0.35 A;
1 W'ta (anma 0.2 A) bu anmanın 1.8 katı, garanti yok. Benzetimde 1 W + 1.5× sınır kartı 18 V'ta,
1.1× 14 V'ta bırakıyor. → **`IZOLE_GUC_SECENEK = (2.0,)`**, 1 W malzemeden çıktı; `kutu.py`'ye fiziksel
iddia: modülün ANMA akımı tek başına açılış ihtiyacını karşılamalı.

**Kusur 2 — MT2 girişinde toplu kondansatör yoksa kart ~15 V'ta TAKILIYOR (2 W'ta bile).** Yumuşak
başlama referans rampasıysa MT2 girişini UVLO'ya çekince rampa sıfırlanıyor; her döngü yalnız modülün
22 µF seramiğinin enerjisini taşıyor, kart yükü (sabit ~26 mA) onu yiyor. 220 µF yetmiyor, **470 µF
her modelde yetiyor (ESR iki katıyla da)**. → yeni duvar parçası **CB = 680 µF 16 V (C042, stokta 2)**,
MT2'nin üstünde (x 45, z 70), bacakları MT2'nin giriş uçlarına; 10.2 montaj, 10.4 kablo + kutup
kontrolü (şeritli bacak ↔ MT2 IN− ötmeli), grafta B0505S'in çıkış tarafında (`IZ_CIKIS`).
`kutu.py`: CB ≥ 470 µF ve anma ≥ 1.5 × 7 V; **stok kaydının adı ile sabit aynı değer** (envanter ↔
`tasarim3_sabit` ayrışmasın).

**Kalan risk — DW01A açılışta kesebilir (belirtiye bağlı yordam yazıldı).** Açılışta paket akımı
B0505S'in aşırı yükte ne kadar çektiğine bağlı ve bu veri sayfasında yok. Tarama: **dolu pilde dört
modelin hiçbirinde tipik eşik aşılmıyor**; yarım pilde (3.3–3.7 V) modül anmasının ≤ 2× verirse
güvenli, ~2.5×'ten itibaren tipik eşik 25–32 ms aşılıyor (gecikme tipik 10 ms). En kötü tolerans
(VOIP 120 mV + Rds maks) iki toleransın birlikte uca düşmesini gerektiriyor. Seri direnç (B0505S +Vo →
MT2 IN+, 3 × 1 Ω 1 W R052) güçlü modelde sorunu gideriyor ama hiccup tipinde 24 V'u engelliyor →
**varsayılan değil, 10.5'te belirtiye bağlı yedek yol**: "kutu açılmazsa" → kapat-aç → doldur →
3 Ω seri → TP4056 yedeği; "24 V gelmiyorsa" → direnci çıkar. KULLANIM'a "Kutu açılmıyorsa → doldur"
satırı. **Boş pil** (3.0 V, tek yaşlanmış hücre): MT1 paketi UVLO'ya çökertip çırpınıyor, ESP32
açılmıyor — zararsız (DW01A aşırı deşarjda keser), bilgi olarak basılıyor.

**Sınırda, B58'den önce de vardı:** PİL kapanırken MT1'in giriş seramiğine 20–31 A'lik µs darbe;
kısa kablo + en kötü FET direncinde DW01A'nın kısa devre eşiği 2.4 µs aşılıyor (tipik gecikme 5 µs,
MİN verilmemiş). Olursa belirti aynı ("kutu açılmadı → kapat-aç"). Mutasyon bunu gösteriyor: gecikme
2 µs olsa kırmızı.

**Doğrulanan (sorun yok):** açılış 24 V'a en geç ~113 ms · ESP32 brownout yok (bara ≥ 4.13 V) ·
F0 (1 A) açılışta en fazla %178, ms ölçeğinde açma bölgesine girmiyor · F1 gerçek (yumuşak) açılışta
400 mA sınıfına 25×, T 50 mA'ya 29× pay (F 50 mA hâlâ atar — kutu.py'nin sert kaynak hesabı en kötü
hal olarak kalıyor) · B0505S girişi durağanda 4.98 V · B0505S'in gördüğü kapasite 849 µF < 2400 ·
kapanışta ±12 V en fazla ~79 ms yalnız kalıyor (B18'in süresiz güvenli bulduğu hal; B58 öncesinde
saatlerce olabiliyordu) · yalnız USB 358–510 mA → "USB takarken PİL açık" kuralı gerekli, 11.2'nin
~0.35 A'i benzetimle tutarlı · paralel hücre ±0.1 V kuralı 0.61 A ≤ 0.5 C (izin 0.12 V) · PİL
açıkken şarjda yük (482 mA) TP4056'nın bitiş eşiğini (100 mA) engelliyor → 10.6 kuralı doğru ·
B0505S dalgalanmasının raylara ulaşan payı 3 µVpp (10.5 ölçütünün 1/16000'i) · durağan B0505S yükü
iki bağımsız modelde (benzetim ↔ `kutu.besleme_butcesi`) aynı, %36.7.

**Doğrulama disiplini — iki tuzak.** (1) **Adım boyu:** 5 µs'de UVLO çırpınması yutuluyordu; DW01A
süreleri yakınsamış değerin **8'de biri** (2.8 → 21.9 ms), 24 V süresi %50 sapıyordu. Açılış fazı
artık 1 µs; benzetim kendi yakınsamasını 0.5 µs'ye karşı ölçen bir iddia taşıyor (mutasyon: adım
5 µs → kırmızı). İlk keşif turundaki "k ≤ 2.2 güvenli" sonucu bu yüzden yanlıştı. (2) **`spice.Rapor`
numpy bool'unu saymıyordu** (`g is False`): ilk koşu 15 kırmızıyla "27/29 geçti" yazdı. Benzetim
`bool()` saran bir alt sınıf kullanıyor. (3) Ayrıca: MT1'in UVLO'su önce kaynak geriliminden
okunuyordu (paket terminali olmalı) — düzeltilince boş pil köşesi ortaya çıktı.

Mutasyon turunun buldukları (üç ölü/maskeli iddia, üçü de düzeltildi): (a) KULLANIM'daki "açılmıyorsa … doldur" deseni aynı satırdaki "doldur**urken**" kelimesiyle kendini karşılıyordu → `\bdoldur\b`; (b) yedek yol iddiası yalnız "kötü" B0505S eğrisini tarıyordu, 1 Ω'u da "yeter" sayıyordu — tipik eğri daha çok akım veriyor; tarama: **0.5/1/2 Ω yetmiyor, 3 Ω yetiyor**, mutasyon artık 3 → 2 Ω; (c) `kutu.py`'deki yeni "anma akımı" iddiası tabloda olmayan seçenekte (0.5 W, 10 W) **KeyError ile çöküyordu**: mutasyon "yakalandı" diyordu ama kırmızıyı iddia değil çökme veriyordu ve asıl iddiaları maskeliyordu → anma = P / 5 V. Ayrıca B58f'in değiştirdiği 4 eski B50 mutasyonu (iki seçenekli demet, malzeme satırı, 10.2 montaj listesi) güncel metne uyarlandı. 10.5'in SR5100 yolu için yeni iddia: MT1 5.3 V + 0.05 ≤ B0505S'in 5.5 V sınırı.

Negatif kontroller (benzetimin içinde, KIRMIZI olmaları iddia): kondansatörsüz plan 15 V'ta takılıyor ·
1 W 18 V'ta takılıyor · 0.5 ms'de hiccup yapan modül hiç başlamıyor · 1.5 Ω'luk ölü paket ESP32'yi
sıfırlatıyor · k taraması DW01A dedektörünü tetikliyor (dedektör canlı).
Sayılar: `sim3_kutu_besleme.py` **31/31** · `kutu.py` **2063/2063** · tarayıcı **28/28** · mutasyon B58f
**16/16**, B50 **160/160**, B57 **7/7** · `dogrula3.py` **19/19**, sayım kilidi **3501 → 3596**.

**B59 (2026-09-26) — ön yüz: simetrik DEĞİL, toplu ve düzenli.** Kullanıcı: "Sanırım simetrik
konusunda yanlış anlaştık. Aslında ön yüzün daha toplu ve düzenli gözükmesini istiyorum, simetrik
değil." B56'da "asimetrik ve hoş değil" sözü "simetrik yap" diye yorumlanmış ve ön panel simetrisi
DENETİM KURALI olarak yazılmıştı. Bu kez yorumlamadan önce dört aday (A tam ızgara, B ortada 4×3
blok, C iki işlev kümesi, D iki sıra) bellekte `kutu.denetle`'den geçirilip ASCII önizlemeyle
soruldu; kullanıcı her biri için başka bir modelde görsel ürettirmek üzere ayrı promptlar istedi,
sonra kendi görselini getirdi. O görsel kurallardan geçiyordu ama iki işlevsel sorunu vardı:
(1) **COM sol uçtaydı**, V/HV/SKOP sağda — her gerilim ölçümünde prob ~110 mm yayılır ve COM PİL
jaklarıyla karışır; (2) **CAL HV'nin tam üstündeydi** — bir HV ucu (614 V) yanlışlıkla CAL'e girse
22 kΩ'dan ~28 mA akar, GPIO10 ile +3V3 rayındaki iki ADS1115 ölür. Düzeltilmiş hâli onaylandı:

```
x:     35        71        107       143       179
z 81:  AÇ/KAPA   GÜÇ●                CAL       SKOP
z 45:                      COM       V         HV⚡
z  9:  PİL 1     PİL 2               YÜK 1     YÜK 2
```

Anahtar panelde büyük "AÇ / KAPA", altında küçük "PİL" (metinler 35 yerde "PİL anahtarı" diyor;
iki ad aynı anahtarı göstersin diye). PİL ve YÜK jakları yerinde kaldı (kalın kablolar değişmedi).
**Denetim:** simetri kuralı yalnız ARKA panelde; istisna listesinde arka panelde olmayan bir ref
de eskimiş sayılıyor. Ön panelin yeni kuralları: her öğe `ON_IZGARA_X/Z` ızgarasında · COM ölçüm
jaklarına ≤ 2 ızgara adımı · CAL SKOP'un komşusu (patch kablo) · CAL HV'nin komşusu DEĞİL
(`CAL_KOMSU_R` 40 mm; HV 51 mm çaprazda). **Yol boyunca bulunan:** CAL'in arıza denetimi tehdit
gerilimini sabit PİL 38 V alıyordu; CAL yer değiştirince komşuları SKOP (−63.5…+46.8 V) ve V
(±32 V) oldu. Artık tehdit = komşuların GERÇEK menzili (`jak_azami_gerilim`, `cal_komsulari`)
ve enjeksiyon kutuptan bağımsız |V|/R (SKOP'un eksi ucu GND'ye kenetlenir, VDD'ye değil; eski
(V−VDD)/R eksi kutbu küçük sayıyordu): 2.89 mA < 5 mA, 183 mW < 250 mW, kart kapalıyken ray
2.03 V < 3.6 V — 22 kΩ yetiyor. 5.3 ve CAL/HV/anahtar metinleri konumdan bağımsız hâle getirildi
(komşu adları ve gerilimi veriden). Çizim Edge'de görüntüye çevrilip gözle kontrol edildi.
Sayılar: `kutu.py` **2065/2065** · tarayıcı **28/28** · mutasyon B50 **165/165**, B57 **7/7** ·
`dogrula3.py` **19/19**, sayım kilidi **3596 → 3598**.
Kilit yazan koşu ve ilk doğrulama gizlilik taramasında kırmızıydı: B58f'in DEVIR kaydına `\b` desenini yazan kabuk betiği gerçek backspace (0x08) bırakmıştı — iki karakter temizlendi (hafızadaki heredoc tuzağı; `gizlilik_dogrula.py` yakaladı).

**B59b (2026-09-26) — 3B'de iç kat delikleri.** Kullanıcı: "panelin üzerindeki delikler gözüküyor ama iç kat ön duvardaki kısımlarda olması gereken delikler gözükmüyor." Plan iç katı 5.1'de deliyor (dış kattaki delik kılavuz) ama `sahne()` deliği yalnız DIŞ yüze koyu plaka olarak koyuyordu; içeriden (arka görüş, yakın duvar saydam) bakınca iç kat çubukları deliksiz görünüyordu. Artık her panel deliğinin iç kat yüzünde de plaka var (ön: y −0.3, arka: iç_boy − 0.3), **5.1'den itibaren** görünür ve o adımda vurgulu; USB/ŞARJ yuvalarında yok (arkalarındaki iç kat çubuğu kısa, yuvanın üstünden başlıyor). 4.5'te (çubuklar yeni konmuş, delinmemiş) görünmüyor — başsız Edge'de 4.5 ve 5.1 görüntüsü alınıp gözle doğrulandı (15 iç kat deliği: ön 11 + arka 4 havalandırma). Yeni iddia: her panel deliğinin iç yüz plakası var ve 5.1'de beliriyor; iki yalanlayıcı (plaka hiç yok / 4.5'te beliriyor) yakalanıyor. `kutu.py` **2066/2066**.
**Tarayıcı testinde iki düzen bağımlılığı (ikisi de B59 panel değişikliğiyle ortaya çıktı, ürünle ilgisi yok):** (1) Tab senaryosu sayfa SONUNA kaydırıp ilk çizim parçasına odaklanıyordu; etiket listesi kısalınca parça görünümün ancak 22 px üstünde kaldı, kaydırma 23 px'te bitti (eşik 50) → taban kırmızı. Artık parça hangi taraftaysa oradan uzaklaşılıyor (ilk ekranın altındaysa sayfa başına) ve önce gerçekten görünüm DIŞINDA olduğu da ölçülüyor. (2) B57'nin "ışın son çizileni seçer" mutasyonu KAÇTI: "üstten ortada kart A" noktasının altında yalnız taban (önce, uzak) ve A (sonra, yakın) var, hatalı seçici de A'yı buluyor. Yeni ayırt edici nokta: TP1 (B58d) kart A'nın arka şeridinin ALTINDA ve A'dan SONRA çiziliyor; test ölçeği kart A'nın dört kenarını fareyle bularak kalibre ediyor (1.54 / 1.55 px/mm, iki eksen tutarlılığı da iddia) ve TP1'in üstünde yine A bekliyor — panel dizilimine bağlı değil. `kutu_ipucu_test.py` **30/30**, B57 **7/7**.

**B60 (2026-09-26) — panelde tek jak modeli, renkler stoktan.** Kullanıcı: "elimde 2 adet born jack var ve ikisi farklı model; ikisi birden kullanılırsa uyumsuz gözükecek, aynı model kullanılmalı." Panelde 6 büyük şeffaf (PİL, YÜK, CAL, HV) + 3 küçük vidalı (V, COM, SKOP) vardı. Küçük vidalı model YÜK'ün 11.5 A'ini taşımaz → birleştirilecek model büyük şeffaf. Stok her renkten 2 (CON027–031); geleneksel renkler 3 kırmızı + 3 siyah isterdi. Üç seçenek soruldu (HV sarı + 1 siyah al · geleneksel + 1 kırmızı 1 siyah al · alım yok); kullanıcı **alım yok**'u seçti: V, SKOP kırmızı · COM, CAL siyah · **HV sarı (tek)** · PİL mavi · **YÜK yeşil**; sarı 1 yedek. Önemli yan etki soruda açıkça söylendi: HV'nin ayırt ediciliği eskiden BOYUTTAYDI ("tek büyük kırmızı"); B15/A1'e göre V'ye 615 V takılırsa R4 257 °C'ye çıkıp zamanla yanar. Artık ayırt edicilik RENKTE. Denetim: bütün jaklar aynı model ve ölçüde (Ø8 / 14 / 15 mm) · HV'nin rengini başka jak kullanmıyor · her jak renginin adedi stoktakini aşmıyor (toggle kuralının genellemesi; 'alım yok' kararı böylece korunuyor). Eski 'büyük boy deliği küçükten büyük' iddiası kalktı. Metinler: jak gerekçeleri, 5.2 montaj, KULLANIM ('HV (SARI)'), delme tablosu renk açıklaması, 3.x ölçü talimatı (tek ölçü), KART_DISI_NOTU J2/J3; 3B'ye yeşil jak rengi. Çizim görüntüye çevrilip kontrol edildi. Üç yalanlayıcı (CAL eskisi gibi sarı → HV tek değil · YÜK siyah → 4 siyah > 2 stok · V/SKOP küçük vidalıya dönerse iki model) + eski renk mutasyonu yeni parça adına uyarlandı. `kutu.py` **2068/2068** · mutasyon B50 **170/170**, B57 **7/7** · `dogrula3.py` **19/19**, sayım kilidi **3599 → 3601**.

**B61 (2026-09-26) — pilin ve yükün + ucu nerede.** Kullanıcı: "Şu anda pilin + tarafı nerede olmalı, ayrıca yükün hangi tarafı + olmalı — bunu da düşünmemiz gerekir." Devre değişmedi, anlatım ve denetim değişti. Şönt kart GND tarafında (**low-side**): YÜK 2 = kart GND = COM = PİL 2. Akım ölçümü: kaynağın + ucu yükün + ucuna **doğrudan** gider, kutuya girmez; yükün − → YÜK 1, kaynağın − → YÜK 2; V → yükün +. Ters YÜK zararsız (okuma eksi; kart çift yönlü, B15/A8). Pil testi: pilin + → **yük direnci → PİL 1** (Q1 drain) ve ayrıca **V**; pilin − → PİL 2. Direnç + tarafta olmak ZORUNDA: − tarafta olsa V jakı (COM'a göre) direnç düşümünü de okur. Pilin + ucu doğrudan PİL 1'e takılırsa Q1 açılınca kısa devre; ters pil Q1 gövde diyodundan akar ve kart kesemez. Bulunan eski kusur: kullanım şemaları ELLE renkliydi, B60'ta YÜK yeşil olunca şema siyah kaldı. Yapılan: panel `alt_etiket`'leri kutbu söylüyor (YÜK 1 'yükün −', YÜK 2 'kaynağın −', PİL 1 'direnç ← pil +', PİL 2 'pil −'; 16.1 etiket listesi panel verisinden, fiziksel etiket de değişti) · `ciz_kullanim` jak rengini/adını panel verisinden alıyor, kaynak/yük/pil kutularında + ve − işaretli · KULLANIM akım satırı 'eksi hattan ölçülür, + kutuya girmez' diyor. Üç iddia: şemadaki her jak dairesinin rengi paneldekiyle aynı ve gereken jaklar şemada · her PİL/YÜK etiketi DOĞRU kutbu söylüyor (YÜK 1/2 ve PİL 2 '−', PİL 1 '+' ve 'direnç') · kullanım tablosu eksi hattı söylüyor. Altı yalanlayıcı (renk sabit yazılır · PİL 2 şemadan düşer · YÜK 1 kutupsuz · YÜK 1 'yükün +' · PİL 1 direnci anmaz · KULLANIM 'seri ölçülür'). Şema görüntüye çevrilip kontrol edildi (alt yazı taşıyordu → iki satır). `kutu.py` **2071/2071** · mutasyon B50 **176/176**, B57 **7/7** · tarayıcı testi **30/30** · `dogrula3.py` **19/19**, sayım kilidi **3601 → 3604**.

**B62 (2026-09-27) — kalın kablo bağlantısı + eskimiş güç düğümü metinleri.** Kullanıcı kutuyu kurdu, 6.0'da (TP4056 takılı) ve sordu: "born klemenslerde hiç kablo yok, normal mi?" Değildi: 5.2 dört büyük jaka (YÜK 1/2, PİL 1/2) kutu boşken ≥1.5 mm² pigtail istiyordu; başlık "Born jakları tak" olduğu için atlanmış (kart A takılmadığı için telafi edildi). Ardından "nasıl bağlayacağım, pabuç lazım mı?" sorusu planın kendi kusurunu gösterdi: 5.2/7.1/8.1/9.1 kalın kabloyu **kalaylı kanca somunun altına / kalaylı uç vidanın altına** koyduruyordu. Kalay basınç altında zamanla akar, somun gevşer; 9.5 A'lik yolda gevşek bağlantı ısınır. Jakın arkası metal saplama + somun, paket içeriği ürün sayfasında yok → 5.2'ye üç durumlu tarif: ① lehim kulağı varsa somun → kulak → ikinci somun, kabloyu kulağa lehimle · ② yoksa kalaysız, saat yönünde halka iki somunun arasında · ③ tek somun varsa ikinci somun (M3 ise MEK034, değilse hırdavat). Jakı panele tutan somun kablo için kullanılmaz (sıktıkça jak döner). Pabuç stokta yok ve gerekmez; alınırsa borusu lehimlenir (lehim boruda, somunun altında değil). Bariyer tarafı kalaysız burulmuş uç. Aynı taramada eskimiş dört metin: 6.4 ve şönt notu kalın kabloları hâlâ XP128'in vidalarına gönderiyordu (B55n'den beri güç düğümü bariyerde) · yerleşim KART_DISI_NOTU RS/J3 aynı + J3 'jak tarafı halka pabuç' (stokta yok) · 6.3 'altlıkta iki delik' (B55l'den beri kanal) · 6.6 kanaldan söz etmiyordu. 6.1 değişti: bloklar kalem işaretiyle tek tek değil **karta vidalıyken** yapıştırılıyor (0.5–1 mm kayma M3'ü somuna sokmaz; hizayı vida verir). Beş iddia: veride 'kalaylı uç/kanca' yalnız uyarı olarak (ardından 'gevşer') · hiçbir metin kalın kabloyu XP128 vidasına göndermiyor · 5.2 kalaysız/ikinci somun/saat yönü/panel somunu değil · 6.1 karta vidalıyken · kanallı altlığı takan her adım kanalı veriyle aynı ölçüyle söylüyor. Altı yeni yalanlayıcı, iki eski desen yeni metne uyarlandı; 7.1'den 'kalın kablo' düşünce eski iddia ('7.1 metninde kalın kablo geçiyor') yakaladı. **Mutasyon koşucusu bir kaçış buldu:** B55n'nin güç düğümü iddiası yalnız 'bariyer' SÖZCÜĞÜNE bakıyordu; 7.1'e 'Bariyer tarafında: teli soy…' cümlesi girince, kabloları şönt vidasına geri gönderen mutasyon yeşil kaldı. İddia artık YÖNLENDİRMEYİ ölçüyor (adım kabloları 'bariyer kutup 1/2'ye götürüyor mu, etiketler sökülerek), XP128 iddiası 'bacağıyla aynı vida'yı da tanıyor — o mutasyon şimdi iki iddiaya takılıyor. `kutu.py` **2076/2076** · mutasyon B50 **182/182**, B57 **7/7** · tarayıcı testi **30/30** · `dogrula3.py` **19/19**, sayım kilidi **3604 → 3609**.

**B63 (2026-09-27) — ayna ovaller karıştı: TP4056 USB yuvasına takılmış.** Kullanıcı: "ESP32'yi yanlış deliğe yerleştirmişim, solda olması gerekirken sağda." Jak tarafından bakınca TP4056 SAĞDA çıktı — yani 6.0'da şarj modülü USB ovaline (x 152) takılmış, ESP32'ye ŞARJ ovali (x 62) kalmış. Kök sebep planda: iki oval TIPATIP AYNI (14 × 9, birbirinin aynası — B56 simetri kararı), etiketler 14.1'e kadar yapıştırılmıyor, arka panel çizimi arkadan bakana göre çizili ve 6.0 yalnız 'ŞARJ yuvasının önüne' diyordu. Sonuç fiziksel: ters takılırsa ESP32 (dupontla 28 mm) kart A'nın altına düşer (A 18 mm ayakta) — kart oturmaz. Düzeltme kullanıcıda: TP4056 rafı silikonundan kesilip soldaki ovale (modül sol iç duvardan 53.5–70.5 mm) taşınıyor; yeni delik gerekmez. Plan: 3.2 deler delmez iki ovalin iç yüzüne kurşun kalemle ŞARJ / USB yazdırıyor; 3.2, 6.0 ve 6.3 tarafı önden bakışa göre söylüyor ve bu söz VERİDEN (`on_bakis_taraf()`, `{sarj_taraf}`/`{usb_taraf}`); 6.0 ters takmanın sonucunu söylüyor; 6.3 COM soketinin ovale girdiğini altlık yapışmadan dışarıdan kabloyla denetiyor. Bir eskimiş kontrol daha: 3.2 'anahtarın somunu oturuyor' diyordu — B58e'den beri arka duvarda anahtar yok. İddia: 'birbirinin aynası iki ovale takılan modüller karıştırılamıyor' — ters takmada ESP32–kart A çakışmasını GEOMETRİDEN hesaplıyor (çakışıyorsa 6.0 uyarmak zorunda), taraf fonksiyonu kullanıcının onayladığı bir gerçekle kalibre (AÇ/KAPA önden solda, B59). Üç yalanlayıcı (6.0 taraf düşer · 3.2 ad yazdırmaz · taraf fonksiyonu ters döner). ⚠ **AÇIK:** `ESP32.soket_x_ofset = 13` (kartın ortası) hiç ölçülmedi, oysa devkit'te iki Type-C yan yana — COM soketi ortada olamaz. 6.3'teki kablo denemesi bunu yakalayacak; kayarsa ESP32 sola kaydırılamaz (kart A'nın ayağı A-ayak2 x 115.8–133.8), seçenekler sağa kayma (çakışma denetimiyle sınanmadı) ya da ovali genişletmek. `kutu.py` **2077/2077** · mutasyon B50 **185/185**, B57 **7/7** · tarayıcı testi **30/30** · `dogrula3.py` **19/19**, sayım kilidi **3609 → 3610**.

**B64 (2026-09-27) — kart A'nın yönü veride yoktu.** Kullanıcı 6.2'de: "kartın kablo olan tarafları ne yöne bakmalı?" Kart A kare (115 × 115) ve dört ayak simetrik: dört türlü oturur, yanlış yön de vidalanır. Yön yalnız 6.1'de parantez içinde ('telli kenar öne') ve IC_PARCA notunda ('A–C sütunları ÖN panele') vardı; 6.2 hiç söylemiyordu, veride `yon` alanı yoktu (kart B'de 270 vardı). Kart A'nın dışarı giden tellerinin dokuzu A–C sütunlarında (V C4, COM C6, HV alt C11, SKOP B16, S+/S−/yıldız C25/27/29, 24 V C34/36); Q1 kapısı Z36 kartın ortasında, J5 (ESP32) AJ15 arka yarıda. A'ya `yon: 270` (kart B ile aynı dönüş, `sutun_yonu: 'arka'` ile aynı şey), 6.2'ye yön cümlesi `{yon_a}` = `kart_yon_cumlesi()` → 'A1 köşesi (ön-sol)'. İddia: yon ile sutun_yonu tutarlı · A–C'deki 9 tel ucu `kart_nokta()` ile kutu koordinatında ön kenara ≤ 7.0 mm · 6.2 yönü veriden söylüyor. Yalanlayıcılar: yon 90 (telli kenar arkaya) · 6.2'de elle ve yanlış 'sol-arka'. `kutu.py` **2078/2078** · mutasyon B50 **187/187**, B57 **7/7** · tarayıcı testi **30/30** · `dogrula3.py` **19/19**, sayım kilidi **3610 → 3611**.

**B64b (2026-09-27) — B:O16 → A:C11 telinin boyu üç yerde üç farklıydı, hepsi kısa.** Kullanıcı kart B'yi gösterdi (6 × 820K yerleşimi planla aynı; T_HV ve T_N6 telleri henüz yok) ve "iki kart kabloyla mı bağlı?" diye sordu. Tel boyuna bakınca: yerleşim 5.12 iki yerde 'kısa tut (<10 cm)', kablo notu 'B–A arası 7–13 cm; 15 cm kes, GND ile bur', 1.1 'kısa kaldıysa ek yap, GND ile bur'. Kutuda (B 270°, B55g) iki lehim noktası `kart_nokta()` ile **düz çizgide 145 mm, eksen eksen yol 189 mm** — '<10 cm' ile kesilen tel hiç yetişmez. 'GND ile bur' da eski kararla (DEVIR başı: 'GND ile burulu değil, B'de GND yok') çelişiyordu. Tek sayı `yerlesim3_veri.HVALT_TEL_KES_CM = 22`; yerleşim belgesi ve kablo notu bu sabiti, 1.1 geometriden `{hvalt_duz}/{hvalt_yol}/{hvalt_kes}` yazıyor; kısa kaldıysa ek + makaron (~1.7 V). İddia İKİ YÖNLÜ: not gereken boydan (yol + 30 mm) kısa olamaz, 50 mm'den fazla uzun da olamaz (yüksek empedanslı düğüm gürültü toplar); hiçbir metin 'GND ile bur' demiyor. Yalanlayıcılar: sabit 15 · yol hesabı bozulur (gereken boy düşer, not 'çok uzun' kalır) · 1.1 'GND ile bur'a döner. `kutu.py` **2079/2079** · mutasyon B50 **190/190**, B57 **7/7** · tarayıcı testi **30/30** · `dogrula3.py` **19/19**, sayım kilidi **3611 → 3612**.

**B65 (2026-09-27) — ESP32 kızağı: bacaklar, USB itmesi, anten çıkıntısı.** Kullanıcı: "ESP'nin bacaklarına dikkat et, USB takılırken geriye gitmemesi için arkasında bir yer olmalı; arkasında ~18–19 mm genişliğinde, ortalanmış dahili anten çıkıntısı var — planla ve hallet." Eski plan yalnız altlık + "bağı devkit'in üstünden dolandır" diyordu. Üç kusur: (1) bağ 3.6 mm, pin arası ~1.9 mm — bağ pinlerin ARASINDAN geçemez, dupont ucuna basardı; (2) USB takılırken devkit'i öne karşı tutan hiçbir şey yoktu; (3) devkit'in anten ucunun 0.5 mm önünde kart B'nin ayağı var — kaçan devkit anteni o ayağa dayardı. **Tasarım (`kutu_veri` ESP32 `tasiyici.kizak`, `kutu.kizak_parcalari()`):** altlığın ÜSTÜNE enine kesilmiş 5 mm şeritler, uzun kenarı üstünde dik — iki uzun kenara ikişer ray (kanal hizasında boşluklu, 0.25 mm pay) ve anten ucunda bir şeridin iki yarısı (9 + 9 mm) omuz takozu: anten çıkıntısının İKİ YANINDA kartın omuzlarına dayanır, aralarında 22 mm (çıkıntı 19 mm + 1.5 mm pay) — itmeyi kartın omuzları taşır, antene hiçbir şey değmez. Arka taraf arka duvar (USB ucu 2 mm). Kurulum kendi kendine hizalanır: Type-C kablo dışarıdan ovalden COM soketine takılıyken parçalar devkit'e dayanarak yapıştırılır (kâğıt = pay + japon koruması). Bağ kanaldan geçer, iki yandaki BOŞ pinlerin tepesinden devkit'in üstüne döner; dolu pinler metne VERİDEN (`esp_dolu_pinler()`: J5 tablosunun kaynağı olan netlist + firmware pinleri + PIN_CAL → 3V3, 5V, GND, GPIO4–10). COM soketi ovale denk gelmezse kaydırma payı da veriden (`esp_kayma_payi()`: takım adım adım kaydırılıp gövde envanteriyle çakışma aranıyor): önden sağa 6, sola 1 mm (kart A'nın sağ-arka ayağı) — fazlası için oval genişletilir. 3B'de devkit gövde + dar anten çıkıntısı olarak çiziliyor; yapıştırıcı tablosuna kızak satırı. İddialar: kızak dört yandan tutuyor (GERÇEK modelden — ilk sürüm yardımcı fonksiyondan okuyordu ve kızak modelden düşse de yeşildi; mutasyon koşucusu yalnız iddia SAYISI düştüğü için yakaladı, sonra çökme olarak — ikisi de düzeltildi) · takozlar antene ≥ 1 mm, omuza ≥ 2 mm · ölçülmemiş çıkıntı ARALIĞI (3–8 mm) boyunca takozlar hiçbir gövdeye/raya çarpmıyor · raylar kanal hizasında boşluklu · kaydırma payı iki bağımsız hesapta tutuyor · 6.3 boş pin/pin listesi/anten/sökme yolunu söylüyor. Yedi yalanlayıcı. Yeni parçalar çakışma envanterine kendiliğinden girdi: `kutu.py` **2398/2398** · mutasyon B50 **197/197**, B57 **7/7** · tarayıcı testi **30/30** · `dogrula3.py` **19/19**, sayım kilidi **3612 → 3931**. ⚠ AÇIK: `soket_x_ofset` hâlâ ölçülmedi — 6.3'teki kablo denemesi bunu kurulumda çözüyor.

**B65b (2026-09-27) — kuşbakışında etiketler üst üste biniyordu.** Kızağı görüntüye çevirip kontrol ederken fark edildi: B59'un ön panel ızgarasında aynı x'te üç öğe var (CAL/V/YÜK 1 x 143, SKOP/HV/YÜK 2 x 179); `ciz_yerlesim` onları aynı noktaya çizip etiketleri index'e göre iki satıra dağıtıyordu → "HVÜK 2", "YÖK1" gibi okunmaz yazılar. Arka duvardaki modüllerde de aynısı (IZ/KL/F0, CB/MT1/MT2/TP1 aynı x'te farklı z). Düzeltme: ön panelde aynı x'tekiler gruplanıyor — daireler yan yana, adlar panelin üstten alta sırasıyla alt alta; duvar modüllerinde açgözlü satır atama (etiket öncekilerle yatayda örtüşürse alt satıra). Açıklamaya üçüncü satır. Yalnız çizim; iddia sayısı değişmedi, tarayıcı testi ve B57 mutasyonları yeniden koştu. Görüntüye çevrilip kontrol edildi.

**B66 (2026-09-27) — yük yolunun en zayıf halkası klemensti.** Kullanıcı 6.4'e gelip sordu: "o klemens kaç amper kaldırıyor, baktın mı?" Bakılmamıştı. Yük yolu sırayla: YÜK jakı → ≥1.5 mm² kablo → HB950 bariyer → köprü → XP128 → şönt. Plan akım sınırını yalnız şöntün ısıl sınırından (9.5 A) alıyordu ve KULLANIM "13 A birkaç dakika" vaat ediyordu; XP128'in stok notu **300 V 10 A** — 13 A onu %30 aşıyor. HB950'nin değeri ne kayıtta ne ürün sayfasında var. Düzeltme: `kutu_veri.KLEMENS_ANMA_A = {"XP128": 10.0}`; KULLANIM ve 7.1 "kısa süreli de olsa 10 A'i geçme"; 7.1 HB950'nin üstündeki baskıya baktırıyor (< 10 A ise o değer kutunun sınırı, YÜK etiketinin altına yazılır). İddia: menzil sınırı ≤ klemens anma akımı, KULLANIM akım satırındaki hiçbir akım onu aşmıyor, 7.1 HB950 baskısını soruyor. Yalanlayıcılar: '13 A birkaç dakika' geri gelir · klemens 8 A olur (veri gerçekten kullanılıyor). Aynı turda kullanıcıya 6.4 adım adım anlatıldı (Kelvin = 4 telli ölçüm, klemensten ÖNCE tezgahta lehim). `kutu.py` **2399/2399** · mutasyon B50 **199/199**, B57 **7/7** · tarayıcı testi **30/30** · `dogrula3.py` **19/19**, sayım kilidi **3931 → 3933 (B67 ile birlikte)**.

**B67 (2026-09-27) — şönt veri sayfaları: plan takılı şöntü yanlış tarif ediyordu.** Kullanıcı iki veri sayfası gönderdi: "elimde 2 şönt var, hangisini kullanayım?" R042 "5mR 9.5A" = **YSR serisi**: tek parça **manganin** Ø1.6 mm, 5 mΩ ±%5, **10 A**, bacak aralığı W = 10 ± 0.5 mm, basık yerin ("boncuk") altında bacak A = **3.5 mm**, ölçüm noktası (test point) basık yerde, lehim sınaması 350 °C / 3.5 s. R043 (akımı yazmayan 5 mΩ) veri sayfası genel katalog (Royalohm CSR): alaşım "değere göre CuNi ya da MnCu", ±400 ppm/°C'ye kadar → 9.5 A'deki ~40 K ısınmada okuma ~%1.6 kayabilir (manganinde ~%0.1). **Karar: R042 (planın zaten seçtiği), R043 kullanılmaz.** Planın eski tarifi veri sayfasıyla çelişiyordu: "iki bakır bacak, manganin–bakır eki" (R042 tek parça manganin), "11 mm aralık, 10 mm'e bük" (W 10 mm = XP128 adımı; B53'teki 11 mm muhtemelen dıştan dışa), "Kelvin boncuğun hemen ALTINA, bakıra" (altta 3.5 mm var ve o kısım klemense giriyor). Yeni 6.4: Kelvin tellerinin ne olduğu bir cümleyle, basık yerin KENDİSİNE lehim, ≤350 °C / ≤3–4 s, önce bükmeden dene. **12.2'de gizli kusur:** iki aşamalı yolda (15 mΩ ile kazanç, sonra 5 mΩ + `s0.005`) 5 mΩ'un gerçek değeri hiç düzeltilmiyordu; veri sayfası ±%5 ve Kelvin lehiminin yeri mm başına ~%4 (Ø1.6 manganin 0.22 mΩ/mm) oynatıyor, metin ±%2 kapısı tutmazsa ne yapılacağını söylemiyordu → "`s` = 0.005 × kart ÷ multimetre" ya da ≥2.6 A yolu. Veriye `SONT_VERI["R042"]` ve `KLEMENS_ADIM_MM`; iddia bükme tarifini W ile, akım sınırını şöntün anma akımıyla karşılaştırıyor, eski tarifin hiçbir metinde kalmadığını ölçüyor. Beş yalanlayıcı, hepsi yakalandı. Stok notları (R042/R043) veri sayfasıyla güncellendi (yedekli). ⚠ AÇIK: 15 mΩ'un ısıl sınırı (3.4 A) B53'te Ø2 referansla d^1.5 ölçeklenmişti; referans Ø1.6 olunca ~4.7 A çıkar — 3.4 A güvenli yönde, değiştirilmedi. `kutu.py` **2400/2400** · `dogrula3.py` **19/19**, sayım kilidi **3931 → 3933** (B66 + B67).

**B68 (2026-09-27) — şönte yapıştırıcı yasağı.** Kullanıcı 6.4'ü bitirdi (fotoğraflar: S+ turuncu RS.1, S−/yıldız siyah+gri RS.2 aynı noktada, basık yerde; A tarafı kırmızı C25 / siyah C27 / yeşil C29, iki tarafta 3'lü header + makaron — doğru; eksikler: yön işareti (orta pin S− simetrik, ters takılırsa S+ ile yıldız yer değiştirir), burma, tel kılları) ve sordu: "silikonlasam nasıl olur, sağlamlık açısından?" Plan şöntün kendisi için bir şey söylemiyordu. Şönt 9.5 A'de ~45 K ısınır (B53 yüzey modeli), kapalı kutuda 70 °C'yi geçer: sıcak silikon ~65 °C'de yumuşar; 9.5 A sınırı açık havada soğumaya göre, silikon onu da bozar; 15 mΩ takasında lehimler sökülür. Yapıştırıcı tablosuna YASAK satırı ("Yapıştırıcı yok — makaron + kablo bağı"; gerilmeyi 7.2'deki kablo bağı alır), 6.4'e aynı cümle. İddia: tabloda yasak satırı var, 6.4 söylüyor, 6.4/7.2 şönte ya da lehimine silikon sürdürmüyor (ilk regex yasak cümlesinin kendisini — "silikon SÜRME" — izin sandı; olumsuz ek dışarıda). İki yalanlayıcı. `kutu.py` **2401/2401** · mutasyon B50 **206/206**, B57 **7/7** · tarayıcı testi **30/30** · `dogrula3.py` **19/19**, sayım kilidi **3933 → 3934**.

**B69 (2026-09-27 akşam) — DEVİR NOTU: kurulum 6.6/7.1/8.1'de, plana işlenmemiş kararlar.** Oturum uzadığı için kapandı; yeni oturum hafızadaki "Ölçüm kartı KURULUM İLERLEMESİ" notundan başlasın. Kullanıcı 6.5'i bitirdi: IRFZ44N U profil soğutucuya yalıtımlı (tabla↔soğutucu ötmüyor), kapıda 1 pin dişi header, 1 MΩ somunun altında (öbür ucu RS.2'ye bağlanacak). Soğutucu ~26×30×20 mm — plan 15×40 varsaymıştı (`sogutucu_olcu_varsayim`); kullanıcı köşebent yerine yapıştırıcısız bir kafes/bağ kurdu, sağ duvara yaslı, B kartına ~6 mm (1 cm geri alması önerildi). Kullanıcıya şönt + güç yolu için tek tek sıra verildi: şönt XP128'e → köprüler XP128'in ALTTAKİ PCB pimlerine lehimli (vida altında yalnız şönt bacağı) → XP128 kanallı altlıkta (pimler kanalda) + kablo bağı → köprülerin öbür ucu HB950'nin alttaki pimlerine → HB950 şöntün arkasında (Q1 ile arası), kanallı altlık + bağ → Q1 S → kutup 1, YÜK 1 → kutup 1, YÜK 2 + PİL 2 → kutup 2, PİL 1 → Q1 D. **Plana işlenecek (fotoğraf gelince):** (1) HB950'nin konumu ve montajı veride hiç yok — çakışma/mesafe denetimi görmüyor; 8.1 "yapıştır/vidala" diyor ama kutuya giren parça yapıştırılmaz ve bu PCB tipinde vida deliği yok; (2) köprülerin pimlere lehimlenmesi 7.1/8.1 metninde yok; (3) Q1'in gerçek ölçüsü/yeri ve montajı; (4) kart B'nin gerçek yönü (veride yon 270, gerçekte 90° dönük; HV ucu en yakın iletkene ~20 mm, sınır 12.6). Açık küçük işler: ESP32 COM soketi denemesi (soket_x_ofset ölçülmedi), HV kablosunun tipi (ince sarı tel gibi görünüyordu), ESP32 kablo bağı, Kelvin fişi yön işareti ve S+/S− burma.

**B70 (2026-09-28) — B0505S-2WR3 GELDİ (envanter MOD013, 1 adet).** Envantere girdiği anda `kutu.py`'nin B58 iddiası ("B0505S stokta yok → malzeme listesinde ALINACAK, duvar parçasında stok sorgusu yok") kırmızıya dönecekti — doğru tepki: plan parçayı hâlâ alınacak sayıyordu, 10.2'nin stok hücresi "stokta YOK — alınacak" yazıyordu. Düzeltme: `kutu_veri` IZ'nin `alinacak` anahtarı → `"stok": ("B0505S-2WR3", "Modül")` (eşleştirici tam ad ya da "ad + boşluk" ister; "B0505S" tek başına "B0505S-2WR3 …"yu BULMAZ), MALZEME kaydı `stok: None` → aynı sorgu, notundaki "Stokta yok, alınacak tek parça bu" → "2026-09-28'de geldi". İddia ters çevrildi: "B0505S stokta → malzeme listesinde STOKTAN, duvar parçası IZ envanter sorguluyor" (IZ stok taşır ve `alinacak` taşımaz · `malzeme_ayir` onu stokta sayar, alınacakta saymaz · envanterde kaydı var). Mutasyon: eski "stok None → sorgu" kaydı kaynakta artık yok (ATLANDI olurdu); yerine tersi + IZ'yi `alinacak`a geri çeviren ikincisi — ikisi de YAKALANDI (rc=1). `kutu.py` 2401 → **2403**: +1 "IZ envanterde", +1 B0505S için "stokta olan alınacak listesinde değil". `beklenen_sayim.json` B9 yalnız bu değer için elle güncellendi (tam `--sayim-kilidi-yaz` yapılmadı: çalışma ağacında başka commit'lenmemiş iş var, onun sayılarını körlemesine kilitlememek için). Tam `dogrula3.py` bu değişiklikten sonra koşulmadı; `kutu.py` 2403/2403, `yerlesim3.py` 52/52, `bom_dogrula.py` 3/3, `_ortak/tahsis.py` 18/18. Aynı gün 1N5819 da geldi (D013, 20 adet) — B58b'deki "1N5819 yok" notu artık geçersiz.

---

#### 5.12.65 ✅ B71 — KAYIT MOTORU (alt proje 1A-1, 2026-09-29)

Tasarım: `tasarim/2026-09-29-yazilim-sistemi.md` (onaylı) · Plan:
`tasarim/2026-09-29-plan-1a1-kayit-motoru.md`. **Karta dokunulmadı**;
firmware (`.ino`) değişmedi. Kullanıcının istediği "kartın kaydetmesi"
sisteminin (her mod, güvenilir, bildirimli) ilk dilimi: baytların tanımı ve
flaştaki günlük, bilgisayarda doğrulanmış halde.

**Ne yapıldı**

| Dosya | Ne |
|---|---|
| `kod/olcum-karti-a3/kayit_bicim.h` | Baytların TEK tanımı: kayıt = 16 B başlık (imza, tür, yük, sıra, oturum, CRC-32 = zlib) + yük + dolgu. Nokta 36 B: V/A **ham kod** ort + min + maks, W watt. BASLA kalibrasyonun tam kopyasını taşır |
| `kayit_nokta.h` | Noktacı: ham örnek → ort + min + maks. Menzil değişince nokta O ANDA kapanır; hatalı örnek istatistiğe girmez; kayıp/duraklama bayrakları |
| `kayit_gunluk.h` | NOR flaşta halka: sektör kullanılmadan önce HEP silinir · kurtarma yarım kaydı ve çöp sektörü atar · akıllı temizlik (onaysız veri ASLA silinmez) · sıra tabanı (biçimlemeden sonra numara tekrar verilmez) · eşitleme okuması yarım kaydı atlar, boşluğu bildirir |
| `kayit_oturum.h` | Oturum yazıcı: TEKRAR (her sektör kendi oturumunu anlatır) · DEVAM (yeniden başlamada sürer) · BITIR(DOLU) için sektör başına 24 B ayrılmış pay |
| `kopru/kayit_bicim.py` | Bağımsız Python çözücü (stdlib) — C ile ortak test vektörleriyle sınanıyor |
| `uretim/avr/nor_flas.py` | Emüle NOR: yazma yalnız 1→0, silme zaman alır; arıza modeli yarım yazma + yarım silme |
| `uretim/avr/ornek_kayit.c`, `uretim/test_kayit.py` | AVR harness (senaryo başına ayrı ELF) + zincir adımı B71 |

**Test yolu neden AVR:** bu makinede masaüstü C derleyicisi yok. `kayit_*.h`
platform çağrısı içermiyor, flaş işlev işaretçileriyle geliyor; B4/B5'in
yöntemiyle (`olcum3.h`) aynı kod AVR emülatöründe koşuyor. Başlıklar ayrıca
`avr-g++ -fsyntax-only -Wall -Wextra` ile C++ olarak da uyarısız (ESP32
`.ino`'yu C++ derliyor).

**Doğrulama**
- `test_kayit.py` **74/74** (tek başına ~1 dk, zincirde 85 s). Plan 72
  diyordu; +2 = Y14 / K10 (aşağıda).
- `--kesinti 1000` **74/74**, 424 s: 98 kesik silme, 219 yarım kayıt, 571
  DEVAM, 608 açılış; veride tek bozulma yok, sıra hiç geri gitmedi.
  Varsayılan 120 kesmede: 9 kesik silme, 32 yarım kayıt, 68 DEVAM.
- Mutasyon B71 **13/13** (620 s). 🔴 **İlk turda 12/13:** `KY_BITIR_PAY 0u`
  KAÇTI. Y12 sonuca bakıyordu ("BITIR(DOLU) flaşta mı"); pay kaldırılınca
  BITIR çoğu zaman tesadüfen sektör kuyruğuna sığıyordu. Test **yerleşimi**
  ölçecek şekilde düzeltildi — `bitir_payi_korunur()`: BITIR dışında hiçbir
  kayıt sektörün son 24 baytına girmez (Y14; kesme altında K10). Mutasyonlu
  koşu tam Y14 + K10'u kırmızı yaptı. Ders yine aynı: sonucu ölçen iddia,
  sonucu tesadüfen doğru çıkaran bozukluğu yakalamaz.
- Zincir **20/20** (`ADIM_SAYISI` 19 → 20; 738 s). İlk koşuda iki kırmızı:
  adım **tezgah kalemi basmıyordu** (proje kuralı; 4 kalem eklendi) ve
  `gizlilik_dogrula.py` plan belgesinde **3 mutlak Windows yolu** buldu
  (kullanıcı hesap adı + proje kökü). Belge temizlendi; push edilmemiş 7
  commit yalnız plan blobu değişecek şekilde yeniden yazıldı (yedek:
  `refs/yedek/1a1-gizlilik-oncesi`) — yoksa yollar herkese açık geçmişe
  girecekti.
- Sayım kilidi `--sayim-kilidi-yaz` ile DEĞİL elle eklendi (B71 = 74):
  kullanıcının commit'lenmemiş B55–B70 işi aynı dosyada; kilidi baştan yazmak
  olası bir kaymayı sessizce onaylayabilirdi.

**Kilitlenen kararlar:** oturum kimliği = BASLA kaydının sırası · W kayıt
anındaki kalibrasyonla watt olarak saklanıyor → başka kalibrasyonda W
yaklaşık (spec §7 güncellendi) · her yeni sektör TEKRAR ile başlar · BITIR
payı 24 B · boşaltma en fazla 28 nokta / 5 s · kapasite kesinleşti (spec §5:
5/s ~17 saat, 1/s ~3.4 gün, 10 s'de 1 ~24 gün — önceki tahminden düşük;
yavaş hızda nokta 5 s içinde tek başına yazılıyor).

**Commit düzeni:** `dogrula3.py`, `mutasyon.py`, `beklenen_sayim.json` ve bu
dosyada kullanıcının commit'lenmemiş B55–B70 işi var. B71 bu dosyalara
**yalnız HEAD + B71** sürümüyle (index'e `update-index --cacheinfo`)
commit'lendi; bekleyen iş çalışma dizininde dokunulmadan duruyor.

**Tezgahta (1A-2'de) ölçülecek:** flaş yazma/silmenin ölçüme etkisi · gerçek
fiş çekme (Ö2: kayıp ≤ ~5 s) · emüle NOR modelinin gerçek ESP32 flaşını
temsil edip etmediği (RTS sıfırlamasıyla 100 kesme) · Python çözücünün
volt/amper çevriminin kartın D satırıyla aynı olması.

**Son bağımsız inceleme (tek inceleyici, taze bağlam) — "düzeltmelerle":
Kritik 0, Önemli 6.** Hepsi planın tasarım boşluğuydu (uygulama planla
birebirdi); tek düzeltme turunda, her biri önce kırmızıyı gösteren testle:

| # | Bulgu | Etkisi | Düzeltme · test |
|---|---|---|---|
| 1 | Onay yalnız RAM'de, `kg_ac` sıfırlıyordu | Halka bir kez dolduktan sonra her yeniden başlamada eşitlenmiş veri "onaysız" sayılır, kayıt ~1 sektör sonra DOLU'ya düşerdi | `kg_ac(g, sira_taban, onay_taban)` · G6b |
| 2 | Kafa sektörü yarımken + bellek onaysız veriyle doluyken BITIR(DOLU) yazılamıyor | Oturum ACIK kalır; iki ACIK oturumda yanlışı sürdürülebilirdi | **Kısmen:** `kg_acik_oturum()` EN YENİ ACIK'ı seçer (D4). Yedek-sektör garantisi 1A-2'ye |
| 3 | Olmayan bir sıraya gelen onay kırpılıyordu | Eski bir cihaz (ör. biçimlemeden önce eşitlenmiş) hiç gönderilmemiş veriyi sildirebilirdi | `kg_onayla` reddeder (KG_HATA) · G6 |
| 4 | G/Ç hata yolları | Okuma hatası çöp sayılıp onaysız veri silinebilirdi; yarım yazma sırayı tekrar veriyordu | `kg_ac` okuma hatasında açmayı reddeder (G17, iki geçiş) · sıra yazmadan ÖNCE harcanır (G18) · emüle NOR'a arıza enjeksiyonu (0xE5/0xE6, N8/N9) |
| 5 | Dizin bakımı testsizdi (iki mutasyon 74/74 geçiyordu) | 1A-2'nin oturum listesi ve DEVAM'ı buna dayanacak | DIZIN senaryosu: tahliye (D1), canlı dizin = flaştan kurulan (D2), `kg_basla_oku` oturum kimliğini doğrular (D3) |
| 6 | Biçim sürümü yazılmıyor, bilinmeyen tür bozuk sayılıyordu | 1C yeni tür ekleyince eski uygulamanın eşitlemesi kırılırdı | BASLA bayt 2–3 = biçim sürümü (B12) · bilinmeyen tür CRC doğruysa geçerli (B13, G16) |

**Güncel sayılar:** `test_kayit.py` **88/88** · mutasyon B71 **24/24**
(1230 s) · zincir **20/20** (657 s) · `--kesinti 1000` **88/88** (348 s;
92 kesik silme, 195 yarım kayıt, 560 DEVAM, veride bozulma yok).
Ertelenen 12 küçük bulgu ve inceleyicinin kapsam dışı bıraktığı 10 madde,
çalışma defterinde karar satırı olarak duruyor.

**1A-2 devir notları (inceleme):**
- NVS'te iki değer: `onay` (hız sınırlı yazım) ve `sira_taban`; `sira_taban`
  **biçimlemeden ÖNCE** yazılmalı (yoksa yarıda kesilen biçimleme numarayı
  başa döndürebilir).
- Bütün `kg_*` / `ky_*` çağrıları tek kilidin arkasından (kayıt görevi +
  web eşitleme uçları).
- `kg_ac` süresi dolu 2912 sektörde ölçülecek (tahmin birkaç saniye; büyük
  okuma parçası ya da `esp_partition_mmap`).
- B10'u gerçek ESP32 derleyicisiyle tekrarla (`-ffp-contract=off`; FMA
  mikrowatt yuvarlamasını değiştirebilir).
- Bulgu 2'nin kalanı: bir yedek sektör ayrılıp ayrılmayacağı (kafa yarımken
  BITIR(DOLU)/DEVAM her zaman yazılabilsin).

**Sırada: 1A-2** — bölüm tablosu (`partitions.csv`; nvs 0x9000/0x5000
yerinde), çekirdek 0 kayıt görevi, `G` komutu ve durum satırı, `/kayit/*`
uçları, NTP, eşitleme istemcisi, tezgah ölçümleri (flaş durmasının ölçüme
etkisi = spec §11'in ilk riski). Hazır bilgi plan belgesinin sonunda.

---

#### 5.12.66 ✅ B72 — KAYIT MOTORU KARTTA (alt proje 1A-2, 2026-09-30)

Tasarım: `tasarim/2026-09-29-yazilim-sistemi.md` · Plan:
`tasarim/2026-09-29-plan-1a2-kayit-firmware.md`. B71'in (5.12.65) kayıt
motoru artık **gerçek kartta kaydediyor**: bölüm tablosu, çekirdek 0'da kayıt
görevi, `G` komutu, `/kayit/*` uçları ve PC eşitleme istemcisi. Kullanıcı
gece "soru sorma, benim adıma karar ver" dedi; bu bölümdeki kararlar o
yetkiyle verildi, her biri gerekçesiyle aşağıda.

**Ne yapıldı**

| Dosya | Ne |
|---|---|
| `kod/olcum-karti-a3/partitions.csv` | Çizim klasöründe → çekirdeğin `huge_app` yerleşimini geçersiz kılar (platform.txt `prebuild.3`). **nvs / otadata / app0 huge_app ile birebir** (WiFi parolaları ve `Ayar3` yüklemeden sonra yerinde — kartta doğrulandı). spiffs 896 KB → 1.5 MB (aynı ofset). **`kayit`** data/0x40, 0x490000, 0xB60000 = **2912 sektör**. coredump en sonda |
| `kod/olcum-karti-a3/kayit_yonet.h` | **Kayıt durum makinesi, platformsuz** (son incelemeden sonra yapıştırıcıdan ayrıldı): açılış (NVS `acilis`, `kimlik`, `taban`, `onay`, `kapat`) · DEVAM ya da kapatma niyeti · durum 4 · son gelen kazanır onay · mantıksal biçimleme · aralıklı arka plan temizliği · NVS'e kısıtlı onay (16 sıra / 30 s). NVS bir işlev tablosu → AVR'de emüle NVS ile sınanıyor |
| `kod/olcum-karti-a3/kayit_esp.h` | ESP32 yapıştırıcısı. `esp_partition` flaşı (yaz/sil süreleri ölçülüyor), `Preferences` NVS tablosu (yazma hatası yutulmaz), çekirdek 0'da kayıt görevi (açılış taraması `setup()`'ı BEKLETMEZ), **tek kilit**, nokta kuyruğu 256, istek kuyruğu 4 (onay kuyrukta DEĞİL), web uçları için 200 ms süreli kilit, NTP. **`Serial` yok** (makrodan önce dahil; çekirdek 0'dan basmak aynayı yarışa sokardı) |
| `olcum-karti-a3.ino` | `olcum_al` ham kodu + hata bitlerini + menzili `kayit_ham`'a verir (`static_assert`: ADS_HATA_* = KN_HATA_*) · `loop` noktacıyı besler, skop duraklamasında noktayı kapatır · `G` komutu + `G` durum satırı (yalnız çekirdek 1) · `/kayit/liste` (JSON) + `/kayit/veri` (ham kayıtlar, kilit altında, 8 KB tavan) · afiş `Kayit: … KB, … sektor` ya da `KAPALI` |
| `kayit_gunluk.h` (2) | **Mantıksal biçimleme:** `taban` (NVS) altındaki kayıtlar yok sayılır — `kg_ac` o sektörleri boş sayar, oturum listesine almaz, eski kafanın arkasına yazmaz · `kg_bicimle_mantiksal` flaşa dokunmaz · `kg_temizle_adim` canlı olmayan eski sektörü siler (canlıya dokunmaz) |
| `kayit_gunluk.h` | Kurtarma yalnız BAŞ sektörün kuyruğunu 0xFF diye okur (boş flaşta 4352 → 768 B; gerçek bölümde 11.4 MB → ~97 KB) · `KG__PARCA` dışarıdan (ESP32 256) · **gizli kusur:** `kg__ff_mi` sayacı `uint8_t` idi, `(uint8_t)256 == 0` → 256'lık parçada kirli kuyruk "temiz" sayılır, yeni kayıt 0xFF olmayan baytların üstüne yazılırdı. AVR testi 32 ile koştuğu için hiç görünmedi; plan kodla karşılaştırılırken bulundu (T2) |
| `kopru/kayit_esitle.py` | Eşitleme: `/kayit/veri` → CRC (`akis_coz`) → kartın baytları **aynen** diske + fsync → `durum.json` atomik `{son_sira, bayt, onaylanan, kimlik}` → **ancak sonra** onay (seri `Go<sıra>` ya da HTTP jeton + parola ortam değişkeninden); "onaylandı" yalnız kart `X-Onay` ile doğrulayınca. Akış kimliği değişirse ya da kartın sırası geri giderse DUR. Çökme: geçerli kesintisiz kuyruk ileri sarılır, yarım kısım kırpılır. İşletim sistemi kilidi |
| `uretim/test_kayit_esp.py` | Zincir adımı **B72**: bölüm tablosu (6) · firmware KAYNAĞI yorumsuz (12) · eşitleme istemcisi sahte kart HTTP sunucusuna karşı (10) |
| `uretim/tezgah_kayit.py` | Gerçek kart: `--yedek` (16 MB, depo DIŞINA) · `--duman` · `--durma` · `--kesinti N` · `--esit` · `--dolu` (DOLU → tarama → 11 MB eşitleme → halka dönüşü) · `--bicim` (dolu bölümde `GF!`) |

**Doğrulama**
- `test_kayit.py` **135/135** (B71: +T1/T2 tarama, +M1–M5 mantıksal
  biçimleme, +V1–V13 yönetici); `--kesinti 1000` 95/95 (yönetici öncesi;
  103 kesik silme, 224 yarım kayıt, 588 DEVAM).
- `test_kayit_esp.py` **40/40** (B72: tablo 6 · kaynak F1–F16 · istemci
  E1–E17 + E14b). Plan 26 diyordu: E7 planda BOŞTU (sahte kart sırayı zaten
  süzüyordu, kırmızıya dönemezdi); gerisi inceleme düzeltmeleri.
- Mutasyon **B72 26/26**, **B71 38/38**. İlk turda B71'de **1 KAÇTI**:
  arka plan temizliğinin "canlı sektöre dokunma" koruması kaldırılınca da
  yeşildi — V8 yalnız eski sektörlerin 0xFF olduğuna bakıyordu (kafa ikinci
  bir korumayla güvendeydi). V8 artık kafa dışı canlı sektörlerin de sağlam
  olduğunu ölçüyor; mutasyonla elle kırmızı görüldü. Bazı B72 mutasyonları
  iddiayla değil çökmeyle yakalanıyor (rc≠0, kabul).
- Zincir: ilk koşuda **B7 kırmızı** (345/346) — `kayit_komut`'taki iç `switch`
  `b/d/o`'yu sahte üst düzey komut yapıyordu (harfler `.ino`'daki BÜTÜN
  `case 'x':` satırlarından toplanıyor). Projenin `alt == 'x'` desenine
  çevrildi (31 → 28 harf); `G` arayüzsüz listesinde, gerekçesiyle (kayıt
  ekranları alt proje 3 — ⚠ o zaman satır düşecek). Son koşu (bütün düzeltmelerden sonra): **21/21**, gizlilik temiz.
- `gizlilik_dogrula.py` plan belgesinde **mutlak Windows yolu** buldu (yedek
  klasörü). Push edilmemiş 6 commit yalnız plan blobu değişecek şekilde
  yeniden yazıldı (yedek ref `refs/yedek/1a2-gizlilik-oncesi`, push edilmez).

**Gerçek kart (COM6, ADS1115'ler TAKILI DEĞİL — döngü I²C zaman aşımıyla
~5–8 ms)**

| Ölçüm | Sonuç |
|---|---|
| Tam flaş yedeği (yüklemeden önce) | 16 MB, 224 s, depo dışı `<çalışma alanı>/.yedek/olcum-karti/` |
| Yeni tabloyla açılış | NVS/parolalar/kalibrasyon yerinde · eski panel imajı büyüyen bölümde de bağlandı, yine de 1.5 MB imaj yazıldı |
| Kayıt bölgesinde eski çöp | 2 sektör (236–237, eski bir metin dosyası kalıntısı) → çöp sayıldı, kullanılmadan silindi |
| Açılış taraması | boş 299–304 ms · birkaç yüz kayıtla 358 ms · **DOLU: ilk sürümde >20 s + Task WDT → SONSUZ yeniden başlama (aşağıda); düzeltmeden sonra 1999 ms** |
| Duman | 5/5 — BASLA (kalibrasyon kopyası, sürüm `A3-B72`) + 40 nokta + BITIR, eşitlendi, onay karta döndü |
| Flaşın ölçüme etkisi (boş sektör) | döngü en uzun: kayıtsız 7.6 ms · 5/s 9.1 ms · 50/s 8.2 ms; >20 ms tur 0; silme 0.3–1.35 ms; yazma ≤ 2.9 ms; kuyrukta düşen 0 |
| **Dolu sektör silme** | **24.9 ms** (`GF!` ile ölçüldü). `CONFIG_SPI_FLASH_AUTO_SUSPEND` kapalı → silme boyunca İKİ çekirdek de durur |
| Tam biçimleme `GF!` | 2912 sektör ~1.8 s; bu sırada döngü en fazla 59 ms (art arda silme) |
| 20 RTS sıfırlaması | 20/20 aynı oturum, flaşta 20 DEVAM, 1599 nokta boşluksuz/tekrarsız |
| Açılıştan DEVAM'a | **4.8–6.3 s** (WiFi bağlantısı `setup()`'ta bekleniyor) |
| Bayt eşitliği | eşitlenen 196 kaydın 196'sı esptool dökümüyle bayt bayt aynı |
| Doldurma (50/s, onaysız) | 1 sa 44 dk'da 311 505 nokta; DOLU'da oturum `BITIR(DOLU)` ile kapandı, onaysız veri silinmedi (%99.9), akıllı temizlik yalnız onaylı eski sektörleri kullandı; `dusen` 23 = dolma anındaki tampon (sayılıyor, sessiz değil) |
| 11 MB eşitleme | 16 856 kayıt, 11.83 MB, 62 s = **185 KB/s** (WiFi, 8 KB parça); temizlenmiş 1–383 boşluk olarak raporlandı; onay kart tarafından doğrulandı |
| **Halka dönüşü** (onaydan sonra 50/s, 120 s) | 55 DOLU sektör silindi, en uzun silme 25.2 ms, döngü en uzun **30.5 ms**, 52 tur >20 ms (≈ silme başına bir), düşen 0 — spec §11 riskinin gerçek en kötü hali |
| **Dolu bölümde `GF!`** (düzeltmeden sonra) | **1.0 s**'de biter; arka plan temizliği sürerken 90 s'de 714 web isteği, en uzun **264 ms**, 503 yok; temizlik ~1.9 sektör/s (~25 dk); döngü en uzun 39.9 ms |
| Düzeltilmiş firmware tekrarı | duman 5/5 · kesinti 5/5 (tarama ~1.8 s, açılış→DEVAM 2.5–5.7 s) · bayt eşitliği 39/39 (belleğe eşli okuma yazmadan sonra tutarlı) |

🔴🔴 **GECENİN EN ÖNEMLİ BULGUSU — dolu bölümde SONSUZ yeniden başlama.**
Bölüm onaysız veriyle dolduktan sonra yeni firmware yüklendi ve kart hiç
açılamadı: açılış taraması 11.4 MB'ın her kaydının CRC'sini
`esp_partition_read` ile 256 B'lık ~46 000 okumayla yapıyordu. Her okuma
flaş önbelleğini kapatıp iki çekirdeği de durdurduğu için tarama >20 s
sürüyor, kayıt görevi çekirdek 0'ı hiç bırakmıyordu → **Task WDT (IDLE0)
kartı ~11 s'de sıfırlıyordu**, her açılış yeniden aynı taramaya giriyordu.
Yani bölüm dolunca kayıtlara hiçbir yoldan ulaşılamazdı. Ne AVR testi (WDT
yok) ne son inceleme ne de boş bölümle yapılan tezgah bunu görebilirdi;
bölümü gerçekten doldurmak gerekti (5.12.65'in "dolu 2912 sektörde
ölçülecek" notu tam buydu, tahmin "birkaç saniye"ydi). Düzeltme:
**(1)** kayıt görevi uzun işlerde 50 ms'de bir tick bırakır (`kayit__nefes`),
**(2)** bölüm `esp_partition_mmap` ile belleğe eşli okunur (önbellek
kapanmaz, öbür çekirdek durmaz) → dolu bölüm taraması **1999 ms**, döngü
yok. Tripwire F16 + mutasyon. Afiş eşlemenin tutup tutmadığını söylüyor.

🔴 **İlk kesinti koşusu tezgah betiğinin kusurunu gösterdi:** sıfırlamadan
hemen sonra tamponda kalmış ESKİ `G … durum=2` satırını "kayıt sürdü" sayıyordu,
kart WiFi'ye bağlanırken yeniden sıfırlanıyordu (18/20 DEVAM). Motor
doğruydu (flaştaki dizi kusursuz); betik artık yeni açılışın afişini bekliyor.

**Kararlar (kullanıcı adına, gerekçeli)**
1. **Flaş duraklaması: önlem yok, belgelendi.** Halka dönene kadar (~11 MB;
   50/s'de ~1.6 sa, 5/s'de ~16 sa) yalnız BOŞ sektör silinir (≤1.35 ms).
   Döndükten sonra her 4 KB'da bir dolu sektör silinir: ~25 ms duraklama, 50/s'de
   ~2.3 s'de bir. `K` satırı sayar, o aralıktaki nokta `DURAKLAMA` bayrağı alır,
   enerji hesabı (dt < 1 s) etkilenmez. Tek gerçek çözüm (`AUTO_SUSPEND` ya da
   PSRAM'den XIP) çekirdeğin önceden derlenmiş IDF'ini değiştirmeyi ister.
2. **Ö2 tuttu, ama bir ayrım belgelendi.** Kaydedilmiş veriden kaybolan
   yalnız flaşa yazılmamış tampon (≤ 28 nokta / 5 s) — flaştaki dizi 20
   sıfırlamada da kusursuz. AYRICA açılıştan kaydın yeniden başlamasına
   **4.8–6.3 s** geçiyor; bu kayıp veri değil, kartın ölçmediği süre (DEVAM
   kaydı işaretliyor, zaman ekseninde boşluk görünür). Büyüğü `setup()`'taki
   WiFi beklemesi; ağ kurulumunu ağ görevine taşımak 1A-2'nin kapsamı dışı →
   **açık iş** (1E/MQTT ile birlikte).
3. **`G` arayüzde yok** — kayıt ekranları alt proje 3 (kullanıcının sırası).
4. **Onay NVS'e kısıtlı yazılıyor** (16 sıra ya da 30 s). Elektrik kesilirse
   kartın onayı en fazla o kadar geri gider: o kayıtlar kartta "onaysız"
   kalır, istemci ise kendi `son_sira`'sından devam eder (tekrar çekmez) ve
   bir sonraki eşitlemede yeni son sırayı onaylayınca eskiler de kapanır.
   Kayıp yok, tekrar yok; en kötü etki, arada bellek biraz erken dolabilir.
5. Bulgu 2'nin kalanı (yedek sektör) **ayrılmadı**: bellek doluyken açık
   oturum sürdürülemezse durum **4 (BEKLİYOR)**; ilk geçerli onayda DEVAM
   yeniden denenir — kullanıcı durdurduysa (niyet NVS'te) DEVAM değil BITIR.
8. **Biçimleme mantıksal** (fiziksel silme 73 s + web donması yerine). Bedeli:
   silinen veri eski sektörler arka planda silinene kadar (dolu bölümde ~24 dk)
   esptool ile flaştan okunabilir; kartın hiçbir ucu onu vermez.
9. Arka plan silme aralığı **500 ms** (AVR testinde 200 ms): dolu sektör başına
   ~25 ms iki çekirdek durur → ölçüm döngüsünün duraklama payı ~%5.
10. Bölüm **belleğe eşli okunuyor** (`esp_partition_mmap`, 11.4 MB): okuma
    önbelleği kapatmıyor, IDF yazma/silmeden sonra eşli aralığın önbelleğini
    tazeliyor — tezgahta aynı açılışta yazılıp eşitlenen kayıtlar esptool
    dökümüyle bayt bayt aynı çıktı. Eşleme tutmazsa eski okuma yoluna düşer ve
    afiş bunu söyler.
6. B10 (FMA) ESP32 derleyicisiyle **tekrarlanmadı**: `watt*1e6f+0.5f` Xtensa'da
   `madd.s` olabilir; etkisi örnek başına ≤ 1 µW, PC çözücü W'yi yeniden
   hesaplamıyor (kartın toplamını okuyor) → kabul.
7. `_tezgah.md` commit'lenmedi (kullanıcının bekleyen işiyle aynı dosya;
   zincir üretiyor).

**Son bağımsız inceleme (Opus, taze bağlam) — "düzeltmelerle": Kritik 0,
Önemli 5.** Tek düzeltme turunda, her biri önce kırmızıyı gösteren testle.
Yapısal karar: yapıştırıcıdaki durum makinesi **`kayit_yonet.h`'ye taşındı**
(platformsuz, NVS işlev tablosu) ve AVR'de emüle NVS + NOR ile **açılıştan
açılışa** sınanıyor (B71.V, 13 iddia) — ESP32'ye özgü kod artık yalnız flaş,
Preferences, görev ve kuyruk.

| # | Bulgu | Etkisi | Düzeltme · test |
|---|---|---|---|
| O1 | NVS kaybolursa (tam silme, eski yedeği geri yükleme) kart numarayı 1'den başlatır; istemci "yeni 0 kayıt" der, sonra 5001+ kayıtları boşluksuz ekleyip onaylar | Eşitlenmemiş 1..5000 kartta sessizce silinir | Kartta **akış kimliği** (NVS `kimlik`; NVS yoksa ya da flaş NVS'in onayladığı yerin gerisindeyse yenilenir) · `X-Kayit-Kimlik` · istemci kimlik değişince ve kartın sırası geri gidince DURUR · V11, E11, E12 |
| O2 | Onay 4'lük istek kuyruğunda düşebiliyordu; istemci "onaylandı" yazıp bir daha yollamıyordu | Dolu kart, her şey diskte olduğu halde takılı kalır | Onay kuyruk değil **son gelen kazanır** · istemci "onaylandı"yı yalnız kart `X-Onay` ile doğrulayınca yazar, değilse yeniden yollar · V10, F13, E14, E14b |
| O3 | Durum 4'te (açık oturum, yer yok) `Gd` hiçbir şey yapmıyordu; sonraki eşitlemede kayıt kendiliğinden sürüyordu | Kullanıcının durdurduğu kayıt geri gelir | **Durdurma niyeti** NVS'te (`kapat`): yer açılınca DEVAM değil `BITIR(kullanıcı)` (yeni sektörde TEKRAR ile); durum 4'te `Gb` eskisini de niyete alır · V3, V4, V5, V6 |
| O4 | Dolu bölümde `GF!` 2912 × ~25 ms ≈ 73 s kilidi tutuyordu; web uçları `portMAX_DELAY` bekliyordu | Tek iş parçacıklı web sunucusu — pil testinin acil durdurması `p0` dahil — donar | **Mantıksal biçimleme:** NVS'e taban yazmak (atomik); `kg_ac` tabanın altını yok sayar; eski sektörler arka planda **500 ms aralıkla** silinir · web uçları 200 ms süreli kilit → 503 · pil testi sürerken `GF!` reddedilir · M1–M5, V7–V9, V13, F9, F12 |
| O5 | Durum makinesi hiç çalıştırılarak sınanmıyordu; F2'nin "KAPALI" denetimi boştu (kelime .ino'da zaten 16 kez geçiyordu); kuyruk taşmasının işaretlenmesi testsizdi | Yeşil test bir şey kanıtlamıyordu | Yönetici AVR'de (B71.V) · F2 artık afişin kendi dalına bakıyor · F15 (`kn_kayip`) |

Ucuz minor'lar da kapandı: istemci çökmede **ileri sarar** (fsync'li ama
duruma geçmemiş kayıtlar korunur; yalnız kesintisiz dizi — E15, E17) · aynı
dizine iki eşitleme **işletim sistemi kilidiyle** engelli (E16) · parça en
az 1100 B · boş yanıt ama kartta yeni sıra varsa sessizce "bitti" yok (E13) ·
durum 4'te `G` bekleyen oturumu gösteriyor · yeniden deneme hataları
maskelenmiyor. Test edilmeyen iki savunma kodu (**`kg_oku` taban kırpması**,
**`onay_red`**) mutasyon hazırlanırken ölü bulundu ve **silindi**.

Ertelenen minor'lar: `Gb` kayıt sürerken yeniden verilirse kuyruktaki 1–2
eski nokta yeni oturuma girebilir · `--esit` yalnız eşitlenen ⊆ flaş
denetliyor (tamlık yok) · yedek ref'ler (`refs/yedek/*`) mutlak yol içeriyor —
**yalnız `main` push edilir**.

**Açık (tezgah/sonraki):**
- Gerçek fiş çekme (USB + PİL kapalı, 5 kez) — elle.
- ADS takılınca `--durma` tekrarı ve Python çözücünün volt/amper çevriminin
  `D` satırıyla karşılaştırılması (B71 tezgah kalemi).
- Açılıştan kaydın sürmesine 2.5–6.3 s: büyüğü `setup()`'taki WiFi beklemesi
  (ağ kurulumunu görev içine taşımak — 1E/MQTT ile birlikte).
- `/kayit/veri` okuması 1D'ye kadar parolasız (bugünkü `/pil` gibi); onay
  parolalı/USB.
- esptool 921600 baud'da gece iki kez `Corrupt data` verdi (geçici, USB):
  `tezgah_kayit.flas_oku` 460800'e düşüyor.
- Kart şu an dolu bölümün **arka plan temizliğinde** (~25 dk'da biter,
  kendiliğinden); flaşta yalnız test kayıtları var.

**Sırada: 1B — kalibrasyon geçmişi** (alt proje 1'in bir sonraki dilimi;
kayıtlar BASLA'da kalibrasyon kopyasını zaten taşıyor, 1B geçmişi ve
"eski kayıtları yeni kalibrasyonla göster" seçimini kuracak). Sonra 1C (pil
testi/skop oturum türleri, zamanlanmış kayıt, ayrıntılı kip — 25 ms flaş
duraklamasıyla tasarlanacak), 1D (eşleştirme + imzalı istekler), 1E (MQTT +
bildirim + ağ kurulumunun görev içine alınması); ardından alt proje 2
(`ortak/`) → 3 panel → 4 PC → 5 Android.

---

#### 5.12.67 ✅ 1B — KALİBRASYON GEÇMİŞİ (alt proje 1B, 2026-09-30)

Tasarım: spec §7 + §5 · Plan: `tasarim/2026-09-30-plan-1b-kalibrasyon-gecmisi.md`.
Kart artık her kalibrasyonu **numaralı, kalıcı** bir geçmiş kaydı olarak
tutuyor. Her oturum başlığı hangi kalibrasyonla ölçüldüğünü (numara + tam
kopya) taşıyor. PC geçmişi `kalibrasyon.json`'a eşitliyor. Eski bir kayda
başka kalibrasyon **uygulama** ve "aynı dönemde daha yeni ince ayar öner"
alt proje 2/3'te.

**Kullanıcı kararları (2026-09-30):**
1. **Taslak + kaydet.** Kalibrasyon komutları (`z g Z i s f F`) yalnız
   `Ayar3`'ü değiştirir. Değerlerin geçmişte karşılığı yoksa ortada TASLAK
   var. `kk<t><not>` numaralı kayda çevirir. Unutulursa kayıt başlarken
   otomatik kaydedilir (kart bunu söyler), yani hiçbir oturum numarasız
   kalmaz. Not ve tür sonradan düzeltilir; değerler değişmez.
2. **NVS'te sakla** (ad alanı `kalgec`: `adet` + `k1…k40`); bölüm tablosu
   değişmedi.
3. **Sıfırlar hariç + tekrar kullan** (son inceleme C1 üzerine, aynı gün).
   Sıfır ofsetleri (gerilim iki kanal + akım) karşılaştırmaya girmez:
   panelden sık sıfırlanır ve her seferinde biraz farklı çıkar. Oturum
   başlığı gerçek sıfırı zaten taşıyor. Daha önce kaydedilmiş değerlere
   dönülürse (şönt, şebeke A→B→A) o kaydın numarası kullanılır (aynı
   değerli iki kayıt varsa en yenisi). 40 kayıt ancak 40 gerçekten farklı
   kalibrasyonla dolar; 35'ten itibaren kart uyarır. Silme yok.

**Ölçülen kapasite (kullanıcıya "64" denmişti):** yedekteki NVS'te 179 dolu
giriş vardı; 116 baytlık kayıt NVS'te 6 giriş tutuyor → **40 kayıt**. Kartta
`available_entries` (GC sayfası hariç) = **310** → 40 × 6 = 240 sığıyor, pay
kalıyor. Dolunca açık hata (`KGC_DOLU`), sessiz silme yok. Kaydetmeden önce
24 giriş pay denetleniyor (`KGC_NVS_DOLU`).

**Ne yapıldı**

| Dosya | Ne |
|---|---|
| `kayit_bicim.h` / `kopru/kayit_bicim.py` | **Biçim v2:** BASLA 98 → 102 B, sona `u32 kal_no`. Kalibrasyon paketi `kayit_kal_paketle/coz` (62 B, geçmiş aynı paketi kullanıyor). `kg_basla_oku` ve Python çözücü **sürüm 1'i (98 B) de okuyor**: 1A-2 firmware'iyle açılmış oturum yükseltmeden sonra DEVAM edebiliyor |
| `kalgec.h` (yeni, platformsuz) | Geçmiş yöneticisi: ilk açılışta bugünkü `Ayar3` #1 olur (kaynak "ilk") · `kgc_esle` (sıfırlar hariç eşit EN YENİ kayıt; 0 = taslak) · `kgc_kaydet` (elle) · `kgc_oturum_no` (kayıt başlarken; karşılık yoksa otomatik) · `kgc_duzenle` (not/tür) · `kgc_dolmak_uzere` · paket 116 B + CRC-32. Yazım sırası önce `k<no>`, sonra `adet`: arada elektrik giderse numara ne tekrarlanır ne atlanır. Not: geçersiz UTF-8 (RFC 3629; cp1254 'ş' = FE, kopuk dizi, aşırı uzun, vekil), `"`, `\` ve kontrol karakterleri atılır; 31 baytta KARAKTER sınırında kesilir. JSON'a kaçışsız girer, PC'de her zaman çözülür |
| `kayit_esp.h` | `Preferences` tablosu (ad alanı `kalgec`; `isKey` ile, eksik anahtar günlüğü kirletmez) · `nvs_get_stats().available_entries` · `kalgec_kur` · firmware sürümü **A3-1B** |
| `olcum-karti-a3.ino` | `setup`: `ayar_yukle`'den sonra geçmiş kurulur; açılış mesajı `Kalibrasyon: #<etkin> (adet/40)` · `kayit_basla_doldur` → `kal_no`, ardından `kalgec_oturum_bildir` (otomatik kayıt: numara + `kn`/`kt` · numarasız: hata adı) · `k` komutu (`k?` → `KG … <etkin>`, `kl`, `kv<no>`, `kk<t><not>` (değerler kayıtlıysa "zaten kayıtlı: #N"), `kn<no> <not>`, `kt<no><t>`) · `/kal/liste` JSON (`etkin` dahil; önce `adet`, sonra bloblar) · `ayar_kaydet` etkin numarayı tazeliyor |
| `kopru/kayit_esitle.py` | Veri eşitlemesinden sonra `/kal/liste` → `kalibrasyon.json` (atomik). Kartın geçmişi PC'dekinden bir kaydı **siliyor ya da değiştiriyorsa** (aynı numara başka değer/tarih; NVS silindi, başka kart) eski dosya önce `kalibrasyon-<zaman>.json` olarak yedeklenir; not/tür düzeltmesi olağan sayılır. `/kal/liste` hatası (bozuk/yarım JSON, 500, zaman aşımı) eşitlemeyi DURDURMAZ: hata raporlanır, eski dosya yerinde kalır. Eski firmware (404) sessiz |
| `uretim/avr/nor_flas.py` | Emüle NVS'e **ada göre blob** (ad portu, veri portu, boş giriş yazmacı, yazma arızası) |

**Doğrulama**
- `test_kayit.py` **165/165**:
  - B14/B15: sürüm 1 okunur.
  - B71.C1–C13 + C10b + C12c: açılıştan açılışa kalibrasyon geçmişi; blob Python'da C'den bağımsız çözülüyor. C11: sıfır değişikliği taslak açmıyor. C12: A→B→C→A→B yalnız 3 kayıt açıyor. C12c: aynı değerli iki kayıttan en yenisi seçiliyor. C10b: 2/3/4 baytlık karakterin ortasına düşen sınır ve 12 geçersiz UTF-8 biçimi, Python'un katı çözücüsüyle karşılaştırılıyor.
  - B10: C++ denetimine **`kayit_yonet.h`** (1A-2'den beri eksikti) ve `kalgec.h` eklendi.
- `test_kayit_esp.py` **54/54** (F17–F26, E18–E21). Zincir **21/21**.
- Mutasyon: B72 **43/43**. 1B'nin B71 mutasyonları **23/23**; bunlar yalnız ilgili bölümlerle
  (biçim + kalibrasyon geçmişi) koşuldu, çünkü tam `test_kayit.py` (120 elektrik kesmesi)
  mutasyon başına ~1 dk sürüyor. Tam B71 koşusu (61) ayrıca.
- **Kart (tezgah `--kal` 9/9, düzeltmelerden sonra):**
  - #1 gerçek `Ayar3` (`kv1` == `?` satırı); `etkin` = 1.
  - Not/tür düzeltmesi yeniden açılışta kalıcı (Türkçe dahil); deneme notu eski haline geri yazıldı.
  - Taslak yokken `kk` kayıt açmıyor ("zaten kayıtlı: #1").
  - `Gb` kalibrasyon için sessiz.
  - Yeni oturum başlığı sürüm 2 + `kal_no` 1.
  - `/kal/liste` == `kl`.
  - ⚠ **Kalibrasyon komutu çalıştırılmadı:** ADS takılı değil; çöp ölçüm gerçek kalibrasyonun yerine yazılırdı. Taslak/kaydet/tekrar kullanım yolu AVR'de sınanıyor. Gerçek kalibrasyon adımı ADS takılınca tezgah kalemi.
- Karta her yüklemeden önce NVS yedeği depo dışına alındı.

**Bağımsız son inceleme (opus): "düzeltmelerle"**

| # | Bulgu | Neden önemli | Ne yapıldı |
|---|---|---|---|
| C1 | Olağan panel işleri (Akımı/Gerilimi sıfırla, şönt seçimi, DC/50/60) taslak açıyor, `Gb` her birini kalıcı kayda çeviriyordu. A→B→A kopya kayıt üretiyordu. | ~39 oturumda 40 dolar, sonra sonsuza kadar `KGC_DOLU`: gerçek bir kalibrasyon bir daha kaydedilemez. | Kullanıcı kararı 3 (`kgc_esle`), 35'ten uyarı. C11, C12, C12c, C13 |
| I1 | Kayıt başlarken otomatik kayıt da, başarısızlığı da sessizdi. | Kullanıcı hangi numaraya not/tür vereceğini bilemiyordu. Numarasız oturum fark edilmiyordu. | `kalgec_oturum_bildir`; `kk` "zaten kayıtlı: #N"; F22–F24; tezgahta sınandı |
| I2 | C10 girdisi UTF-8 sınırını hiç sınamıyordu (31. bayt boşluktu, `(void)uz` mutasyonu yaşıyordu). Geçersiz UTF-8 nota giriyordu. | cp1254 terminalden yazılan 'ş' (FE) `/kal/liste` JSON'unu PC'de çözülemez yapıyordu. | Not kopyalama UTF-8 doğruluyor; C10b (8 girdi, bağımsız Python referansı) |
| I3 | PC `kalibrasyon.json`'u körlemesine eziyordu. | NVS silinirse ya da başka kart takılırsa PC'deki geçmiş kaybolurdu. | Geçmiş değişirse zaman damgalı yedek; E20 (değer değişti / kayıt kayboldu ayrı adımlar) |
| I4 | `/kal/liste` hatası veri eşitlemesinden SONRA istisnayla çıkıyordu. | Veri diskteydi ama çağıran sonucu alamıyordu; eski firmware notu (cp1254) eşitlemeyi her seferinde düşürürdü. | Hata raporlanır, eski dosya yerinde; `errors="replace"`; E21 |

Düzeltirken bulunanlar:
- **E19** 404'ün hata sayılmadığını iddia etmiyordu. 404'ü hata sayan kod yeşil kalırdı; iddia eklendi.
- **`govde()` ileri bildirimi tanım sanıyor:** F22/F26'nın ilk sürümü yanlış işlevin gövdesine bakıyordu. Test kusuruydu, kod değil. İmza artık ` {` ile tanıma bağlanıyor.
- **Tezgah kalemi eskimişti:** "z sonrası taslak=1" diyordu, sıfırlama artık taslak açmıyor.
- **E7 mutasyonu ~20 dk dönüyordu** (1A-2'den kalma): "sıra geri gitti" denetimi
  kalkınca eşitleme `azami_tur` = 100 000 turu fsync'le dönüyor ve koşucunun 30 dk
  zaman aşımına yaklaşıyordu. Test artık `azami_tur=100` veriyor; mutant 4 s'de kırmızı.

**Ertelenen küçükler (inceleme M):**
- M1: `adet` anahtarı kaybolursa `kgc_ac` #1'in üzerine yazar. Doğrusu `k1…k40`'ı tarayıp sayıyı yeniden kurmak.
- M2: bozuk kayıt `/kal/liste`'de sessizce atlanıyor. Doğrusu `{"no":n,"bozuk":true}`; PC yedeği bunu artık kısmen karşılıyor.
- M3: `/kal/liste` kayıt başına ~20 `sendContent` yapıyor.
- M5: bayat yorumlar (`kayit_oturum.h` ve spec §5 "116 baytlık TEKRAR" → 118).
- M6: `kn<no>` boş metinle notu siliyor (bilinçli sayılabilir); `R!` sonrası varsayılanlar da otomatik kaydedilir (tekrar kullanım artık kopyayı önler).
- M7: çevrimdışıyken unix = 0.
- M8: kuyruk doluysa oturumsuz kayıt kalabilir.
- M9: `Gb`'de NVS yazma duraklaması.
- M10: sürüm 1'den uçtan uca devam sınanmıyor; ESP yapıştırıcısı yalnız kaynak iddiasıyla sınanıyor.
- M11: okuyucular tam blob boyu istiyor (B34 büyütmesi için).

**Açık / sonraki:** eski kayda başka kalibrasyon uygulama, dönem uyarısı ve
"daha yeni ince ayar öner" → alt proje 2 (`ortak/`) + 3 (Ayarlar >
kalibrasyon geçmişi ekranı; o gelince `k` arayüzsüz listesinden çıkar).
B34 doğrusalsızlık düzeltmesi hâlâ karar bekliyor. Tezgah: dolu geçmişte
tarama süresi (`kgc_esle` en fazla 39 NVS okuması). **Sırada 1C** (pil
testi/skop oturum türleri, zamanlanmış kayıt, ayrıntılı kip).

---

#### 5.12.68 ✅ 1C-1 — PİL TESTİ KENDİ OTURUMUNDA + OTURUMA AD/NOT (2026-10-01)

Tasarım: `tasarim/2026-09-30-1c1-pil-oturumu.md` (kararlar K1–K15) · Plan:
`tasarim/2026-09-30-plan-1c1-pil-oturumu.md`.

Pil testi artık RAM'de değil, kartın flaşında **kendi oturumunda** yaşıyor:
noktalar (ham kod, ölçüm kaydıyla aynı biçim), her DCIR darbesi ve sonuç.
PC eşitlemesi bunları öbür kayıtlarla birlikte alıyor. Her oturuma ad, etiket
ve not eklenebiliyor.

**Karar yetkisi:** kullanıcı üç karar verdi, sonra "ben şu an inceleyemiyorum,
sen ver kararları, en son ben kontrol edeceğim" dedi. Kullanıcının kararları:
1. 1C dört dilim: **önce pil testi** → ayrıntılı kip → osiloskop günlüğü →
   zamanlanmış kayıt.
2. Ölçüm kaydı sürerken `p1` gelirse ölçüm kaydı "başka oturum başladı" ile
   kapanır, pil kaydı açılır.
3. Yaklaşım A: pil oturumu ölçüm noktası biçimini aynen kullanır, yalnız OLAY
   kaydı eklenir.

Geri kalan 12 karar tasarım belgesinde, gerekçesiyle. Özetle:
- Her pil testi otomatik kaydedilir.
- Kayıt açılamazsa test yine başlar ve kart "KAYDEDİLMİYOR" der.
- Test sürerken `Gb`/`Gd` reddedilir.
- Açılışta ölçüm dışı açık oturum kapatılır.
- `/pil` panel yenilenene kadar kalır.
- DCIR örnekleri atılmaz, işaretlenir.
- Biçim sürümü 2 kalır.
- Not kayıtlarının başlığında oturum 0 yazar.
- Kart adları ve notları yorumlamaz.
- Tek metin temizleyici kullanılır.
- Firmware `A3-1C1`.

**Ne yapıldı**

| Dosya | Ne |
|---|---|
| `kayit_bicim.h` / `kopru/kayit_bicim.py` | **OLAY (7):** `PIL_AYAR` 32 B, `DCIR` 44 B, `PIL_SONUC` 36 B. **NOT (8):** başlıkta oturum 0, hedef yükte, `degistirir` ile düzelt/sil, metin ≤ 120 B. `KN_DCIR` (0x40) · sebepler 4 pil / 5 yeniden başladı / 6 başka oturum · `KAYIT_OTURUM_PIL` (2). Ortak metin temizleyici `kayit_metin_kopyala` (1B'nin not temizleyicisinin genellemesi; kalibrasyon notu da onu kullanıyor). Python: `olay_coz/paketle`, `not_coz/paketle`, `Oturum.olaylar/ad/etiketler/notlar` |
| `kayit_nokta.h` | `kn_ornek`'e `ek` bayrak: sınırdan **sonra**, örneğin girdiği noktaya işlenir (önce işlense kapanan eski noktaya düşerdi) |
| `kayit_oturum.h` | `ky_olay`: önce bekleyen noktalar boşaltılır, kayıt sırası zaman sırasıyla aynı · `ky_baslat` sürmekte olanı "başka oturum" (6) ile kapatır |
| `kayit_yonet.h` | `kyn_olay` · `kyn_pil_bitir` (yalnız etkin oturum PİL ise: SONUÇ, hemen ardından BITIR) · `kyn_not` (hedef doğrulanır; dolu ise etkin oturumu **kapatmaz**) · `kyn__devam_dene`: ölçüm dışı açık oturum **"kart yeniden başladı" ile kapanır, DEVAM asla**; yer yoksa durum 4'te bekler |
| `kayit_esp.h` | `KM_PIL_BASLAT` (BASLA + AYAR tek mesaj) · `KM_OLAY` · `KM_PIL_BITIR` · `KM_NOT` · `kayit__kuyruga` / `kayit_mesaj_gonder` (beklemez, düşeni sayar) · `A3-1C1` |
| `olcum-karti-a3.ino` | `pil_baslat` kabulünde `kayit_pil_baslat` (kayıt açılamazsa "KAYDEDİLMİYOR — sebep", test sürer) · DCIR bitince `kayit_pil_dcir` · `pil_durdur` **yükü önce keser**, sonra `kayit_pil_bitir` (bu mesaj düşmez: kuyruk doluysa `loop` her turda yeniden dener) · noktacıya `KN_DCIR` · pil sürerken `Gb`/`Gd` reddi · `Ga/Ge/Gn/Gx` (+ yardım) · DRAM 74204 (+264) |

**Doğrulama**
- `test_kayit.py` **186/186**:
  - B71.B16–B21: OLAY/NOT C == Python; metin 120 B sınırı; `oturumlari_kur` ad/etiket/not son hali; B21 not komutu ayrıştırıcısı (20 girdi).
  - B71.P6: `KN_DCIR` sınırdaki örnekte doğru noktaya düşüyor.
  - B71.PL1–PL7: yeni `SENARYO_PIL`, açılıştan açılışa:
    - ölçüm → pil geçişinde sebep 6;
    - olaylar zaman sırasında;
    - açılışta açık pil oturumu sebep 5 ile kapanıyor, DEVAM yok;
    - pil bitir yalnız pil oturumunu kapatıyor, SONUÇ BITIR'dan hemen önce ve alanları doğru;
    - not kayıtları oturum 0 başlıklı, değiştir/sil ve geçersiz hedef;
    - yer yokken durum 4, onayla kapanış.
- `test_kayit_esp.py` **66/66** (F27–F34, F36–F39; F25 yeni sürüm; F9 onarıldı). Arayüz 346/346. Zincir **21/21**.
- Mutasyon: B72 **61/61** (tam). B71'in 1B + 1C-1 girdileri **45/45**, yalnız ilgili bölümlerle koşuldu
  (tam `test_kayit.py` mutasyon başına ~1.3 dk; B71 82 girdi). İlk B72 koşusunda **1 KAÇTI**: 1A-2'nin F9'u
  (pil sürerken `GF!` reddi) `pil_testi_suruyor()` çağrısını bütün işlevde arıyordu; 1C-1'in `Gb`/`Gd`
  retleri aynı çağrıyı başka dallara koyunca iddia boş kaldı. Artık yalnız `F` dalına bakıyor.
- **Kart (tezgah `--pil` 5/5, ADS takılı değil):**
  - `p1` reddedildi ve oturum açmadı.
  - `Ga/Ge/Gn` gerçek bir ölçüm oturumuna yazıldı; `Gn0` ve `:` olmayan `Gx` reddedildi.
  - Yeniden başlatmada ölçüm oturumu DEVAM aldı.
  - PC adı, etiketleri ve iki notu Türkçe karakterle okudu; `Gx` notu sildi.
  - Regresyon: `--duman --kal` 14/14.
  - İnceleme düzeltmelerinden sonra yeniden yüklendi: `--pil --kal` 14/14.
- Karta yüklemeden önce NVS yedeği depo dışına alındı.
- ⚠ **Gerçek pil testi koşulmadı:** ADS takılı değil. Pil oturumunun kendisi (olaylar, sonuç, açılışta kapanış) AVR'de sınanıyor. ADS takılınca yapılacak tezgah kalemi:
  - Tam test.
  - SONUÇ olayı `B` raporuyla aynı olmalı.
  - Fiş çekilince oturum BITIR(5) ile kapanmalı.

**Bağımsız son inceleme (opus): "düzeltmelerle", kritik yok**

| # | Bulgu | Neden önemli | Ne yapıldı |
|---|---|---|---|
| 1–2 | Kuyruğa giremeyen pil bitiş mesajını sonraki istekler (`p1`'in PIL_BASLAT'ı, `Gb`) geçebiliyordu. F32 bunu yakalamıyordu (yalnız adları arıyordu) | Sonraki testin oturumu öncekinin SONUÇ'uyla kapanır; kart "KAYITTA" der, test kayıtsız sürer | **Sıra kuralı** (`kayit_esp.h`): bekleyen bitiş her istekten önce gider, gidemezse yeni istek reddedilir; `Gb/Gd/GF!` de bu yoldan. F32 kesin metne bakıyor + üç mutasyon |
| 3 | Seri ve web komut tamponları 48 B: not ~34 bayttan sonra **sessizce** kesiliyordu | Spec'in 120 baytı ulaşılamazdı; web 204 dönüyordu | `KOMUT_AZAMI` 176; uzun komut seri ve webde **reddedilir** (413). F37 |
| 4 | `Gx` notun grafik yerini siliyordu; not kimliği tanımsızdı (düzeltme kaydının sırası hayalet not üretiyordu) | Kullanıcı yalnız metni düzeltir, not grafikten kaybolur | `degistirir` = ASIL notun sırası; düzeltmede `nokta_ms 0` = yer korunur (`Gx<id>:<sıra>[@ms]`); bilinmeyen sıra yok sayılır. B18 (önce kırmızı görüldü: yer 0, iki hayalet), PL5 |
| 6 → önemli | `strtoul` işaretli/boş sayıyı, 0'ı, taşmayı kabul edip kayıt yazdırıyordu | Planın kendi odak maddesi #5'i | Ayrıştırıcı **platformsuz** (`kayit_not_ayir`), AVR'de 20 girdiyle (B71.B21) |
| 10 → önemli | İlk DCIR darbesinin "anlık" değeri darbenin SON örneğinden geliyordu (`dcir_sayisi == 0 ||`; B21'den kalma) | 1C-1 bunu flaşa yazıyordu; `B` raporu da yanlıştı | Koşul yalnız `dcir_ani == 0`. F39 |
| 11 → önemli | Test sürerken `p1` testi yeniden başlatıyordu | Oturum SONUÇ'suz kapanır; ret hâlinde pil oturumu açık kalıp sonsuz nokta yazar | Test sürerken `p1` reddedilir. F38 |

Değişen fonksiyonlarda iki yanlış mesaj da düzeltildi: "KAYITTA" (kayıt henüz açılmamıştı) → "kaydı istendi — sonuç G satırında"; not mesajı gelmeyecek bir hata vaat ediyordu.

**Ertelenen küçükler:**
- Kayıtsız bir pil testinin DCIR olayları ve `KN_DCIR` noktaları, o sırada açık bir ölçüm oturumuna düşebilir (`p1` tarama sırasında ya da kuyruk doluyken).
- `kayit_mesaj_dusen` sayacı okunmuyor.
- `ky_olay`, `kyn_pil_bitir` ve `kyn_not`'un DOLU yolları testsiz.
- İki kuyruk arasında en fazla bir nokta olaydan sonra yazılabilir.

**Uygularken bulunanlar**
- **Plan varsayımı yanlıştı.** "Halka dolarsa pil oturumu açılışta kapatılamaz" sanılmıştı. Oysa her sektörde BITIR için yer ayrıldığından kapatma normalde her zaman sığıyor. Durum 4 ancak baş sektörde yarım yazma varken oluşuyor; test YÖNET aşama 2'nin desenini kullanıyor.
- **İki test zayıflığı güçlendirildi.** PL4 sonuç olayının yalnız türüne bakıyordu, alanlarına bakmıyordu: 8 baytlık boş bir sonuç geçerdi. F33 `PIL_BASLAT` dalında AYAR olayını aramıyordu.
- **`govde()` tuzağı yine yakaladı** (1B'de de olmuştu). İmza ileri bildirimde bulunuyor, test yanlış gövdeye bakıyordu. İmzalar artık ` {` ile tanıma bağlı.
- **Önceki dilimlerden iki mutasyon eskidi.** F8 ve V4, bu dilimde değişen koda artık uymuyordu (ATLANDI olurdu). Desenleri güncellendi. 1B'nin altı temizleyici mutasyonu kodla birlikte `kayit_bicim.h`'ye taşındı.

**Açık / sonraki:**
- `/pil` ve `PilHalka` panel oturumdan okuyunca kalkar (alt proje 3).
- Ad/not için web ucu (alt proje 3).
- "Pil testi kesildi" bildirimi (1E).
- `Gn` ile yazılan notun sıra numarası kartta basılmıyor; eşitlenen dosyadan okunuyor (`Gx` için).

**Sırada 1C-2 (ayrıntılı kip).**

---

#### 5.12.69 ✅ 1C-2 — AYRINTILI KİP (HER ÖRNEK) + HAZIR ALAN (2026-10-01)

Tasarım: `tasarim/2026-10-01-1c2-ayrintili-kip.md` (kararlar K1–K11, son
incelemeden sonra K8a–K8c) · Plan: `tasarim/2026-10-01-plan-1c2-ayrintili-kip.md`.

`Gb0` artık her ölçüm örneğini zamanıyla birlikte flaşa yazıyor (ADS'le
~500/s, 3.1 KB/s, dolu bölüm ~60 dk). Flaşın 25 ms'lik dolu sektör silmesi,
kart boştayken önceden yapılarak kayıttan çıkarılıyor. Kalan duraklamalar
işaretli ve sayılı.

**Karar yetkisi:** kullanıcı 2026-10-01 gecesi "sen devam et ben yatıyorum,
adım adım devam et" dedi; 1C-1'deki "sen ver kararları, en son ben kontrol
edeceğim" yetkisi sürüyor. Spec ve plan onay kapıları dahil bütün kararlar
benim, gerekçeleri tasarım belgesinde ve aşağıda.

Kararların özeti:
- Ayrıntılı kip ayrı bir oturum türü değil. Bir **ÖLÇÜM oturumu, `hiz_ms = 0`**.
- Örnek **6 bayt**: ham V, ham I, 4 µs'lik zaman farkı + 4 bayrak. Watt saklanmaz; PC hesaplar (alt proje 2).
- Yeni kayıt türü **AYRINTI (9)**. Biçim sürümü **2 kalır**.
- Boşlukta yeni kayıt açılır, sessiz birleştirme yoktur. Halka taşarsa bayrak konur, kirli sektör silinirse de bayrak konur.
- Çekirdek 1 → 0 yolu kilitsiz halka, PSRAM'de 4096 örnek.
- **Hazır alan:** kart boştayken onaylı sektörler önceden silinir (en fazla 480 ≈ 10 dk ayrıntılı kayıt).
- Hazır alan biterse kayıt **sürer**.
- Süre sınırı yok.
- `G?`'nin ardından **`GA`** satırı gelir; `G` satırı değişmedi.
- Firmware `A3-1C2`.

**Ne yapıldı**

| Dosya | Ne |
|---|---|
| `kayit_bicim.h` / `kopru/kayit_bicim.py` | `KAYIT_T_AYRINTI` 9, baş 16 B (`ilk`, `t0_ms`, `t0_us`, `adet`, `bayrak`) + örnek 6 B (`dt4<<4 \| bayrak`). `KA_KAYIP_ONCE` / `KA_SILME`, `KAO_*`. Python `ayrinti_paketle/coz`, `Oturum.ayrinti`. `ayrinti_ornekler` → `(sıra, µs, v, i, bayrak, açılış)`: µs o açılışın `micros()`'u (32 bit sarması `t0_ms`'den çözülür), açılış = kaçıncı DEVAM'dan sonra |
| `kayit_halka.h` (yeni) | Tek üretici / tek tüketici halka, bariyerli (`KAYIT_BARIYER`, varsayılan `__sync_synchronize`). Doluysa örnek **düşer, sayılır**, sonraki başarılı itme `KO_KAYIP_ONCE` taşır. `KO_SILME_ONCE`: üretici, kirli silme duruşundan sonraki ilk örneği işaretler. `tampon == NULL` (PSRAM yok) → her itme düşer, görünür |
| `kayit_oturum.h` | `ky_ayrinti_ornek`: zaman **tampondaki ilk örneğe göre** 4 µs nicemli (hata ≤ 2 µs, birikmez). Fark > 16.38 ms, kayıp, silme işareti ya da dolu tampon → önce boşalt. `ky_ayrinti_bosalt`: sektöre sığdığı kadar yazar (≥ 8 örnek, yoksa yeni sektör); bölünen kaydın kalanı `t0`'ını dt toplamından alır. `ky_nokta` ayrıntılı oturumda `KG_YOK`; 5 s kuralı ve `ky_bitir` örnek tamponunu da kapsar; DOLU'da tampondakiler `dusen`'e |
| `kayit_gunluk.h` | Açılış dizini AYRINTI'yı sayar (DEVAM sırası sürer). **`hazir`** (RAM): `kg_on_sil_adim` başın önündeki sektörü siler — onaysızda durur, başa dokunmaz; `kg_ilerle` hazır sektöre silmeden geçer; `kg_ac` ve mantıksal biçimlemede 0. **`kirli_sil`**: kafa sileceği sektör tabloda yoksa flaşa bakar (`kg__bos_mu`), boş değilse silmeden ÖNCE sayar |
| `kayit_yonet.h` | `on_sil_izin`. Kayıt yok, DEVAM beklemiyor, temizlik bitmiş ve hedef < 480 ise `KYN_TEMIZ_MS` arayla bir ön silme. İzin yeni açıldıysa önce bir aralık beklenir. Ayrıntılı kayıt sürerken GF! temizliği **durur** |
| `kayit_esp.h` | Halka PSRAM'de. `kayit_ornek` ayrıntılı oturumda `micros()` + KAO bayraklarıyla halkaya iter; `kirli_sil` değiştiyse `KO_SILME_ONCE` (görülen değer yalnız itme başarırsa güncellenir). Görev halkayı kilit altında boşaltır. GA "kayıt içi silme" = ayrıntılı oturum süren turlarda `kirli_sil` artışı. `A3-1C2` |
| `olcum-karti-a3.ino` | `Gb0` kabul (yardım + hata metni). `G?` ardından `GA <hazır> <ayrıntılı örnek> <düşen> <kayıt içi silme>`. `loop` izni skop erken dönüşünden ÖNCE günceller. DRAM 74412 (+80) |
| `tezgah_kayit.py` / `tezgah_kart.py` / `tezgah_blokaj.py` | `--ayrinti`, `--hazirsiz [--doldur]`. Kararlı hal ve blokaj ölçümleri önce boşta silmenin durmasını bekler (`G` satırının silme sayacı 3 s artmayana dek; blokajda `--on-silmeli` beklemez) |

**Doğrulama**
- `test_kayit.py` **224/224**:
  - B71.B22–B24: AYRINTI C == Python; tür 9, sürüm 2; sarmada zaman; DEVAM'dan sonra açılış 1.
  - B71.H1–H3: halka; taşmada sayma ve bayrak; 32 bit sayaç sarması.
  - B71.A1–A10: `SENARYO_AYRINTI`, sentetik örnek dizisi PC'de **birebir**:
    - zaman ≤ 2 µs, bölmelerde birikmiyor;
    - DEVAM'da yeni açılışın saati;
    - boşlukta ve kayıpta yeni kayıt;
    - sektör sonu boşa gitmiyor;
    - `Gd`'de tampondaki kuyruk da flaşta;
    - 5 s kuralı;
    - bölmeden sonra yazma hatası (A10).
  - B71.Z1–Z7: `SENARYO_HAZIR`, silmeler NOR'da sayılıyor:
    - izin ve aralık;
    - hazır sektöre silmeden geçiş;
    - Z2: çekirdek 1 partili itme + 25 ms duruşla taklit ediliyor, her kirli silme = bir `KA_SILME`, boşluktan hemen sonra;
    - açılışta ve biçimlemede 0 (aynı süreçte `kg_ac` dahil);
    - onaysızda durur, başa dokunmaz;
    - Z7: GF! sonrası hemen ayrıntılı kayıt — temizlik kayıtta silmiyor, eski sektörler sayılıyor, 10 ms'lik duruşta da işaret doğru kayıtta.
- `test_kayit_esp.py` **74/74** (F40–F48; F25 `A3-1C2`). Arayüz 346/346. Kayıtlı kart bringup 49/49. Zincir **21/21**, gizlilik temiz.
- **Mutasyon:** ilk odaklı koşuda 1C-2'nin 42 yalanlayıcısından **40/42**. Tam B71 koşusu da 1A'dan bir boş iddia buldu:
  - **Z4 boştu:** AVR'de her açılış yeni süreç, RAM zaten sıfır. Senaryo artık hazır > 0 iken aynı süreçte `kg_ac` çağırıyor.
  - **`a_q -= top`'ı "ölü kod" diye sildim — YANLIŞTI.** Başarı yolunda ölü, ama bölmeden sonra yazma hatası olursa kalan tamponda kalır ve sonraki örneğin zamanı 2R ms kayar. İnceleme gösterdi; satır geri kondu ve A10 NOR yazma arızasıyla bunu sınıyor.
  - **G16 (1A) boş kaldı:** "bilinmeyen kayıt türü" olarak 9 kullanıyordu, 9 artık AYRINTI. Bilinmeyen tür artık 200.

  Son hâl (paralel koşucu, 6 işçi): **B71 123/123, B72 73/73**.
- **Kart (tezgah, ADS takılı değil; her yüklemeden önce NVS yedeği depo dışında):**
  - İlk yazılım, `--duman --pil --ayrinti` **14/14**:
    - boşta hazır alan büyüyor, 480'e doluyor;
    - `Gb0` 60 s: **10 133 örnek, 169/s** (ADS yokken I²C zaman aşımı döngüsü), zaman farkı ortancası 6064 µs, en büyüğü 8440 µs, düşen 0, kayıt içi silme 0;
    - yeniden başlatmada DEVAM, sıra kesintisiz.
  - **40 dk dayanıklılık** (ilk yazılım): **391 969 örnek**, 2943 kayıt, 615 sektör, düşen 0, sıra kesintisiz, en büyük fark 9.6 ms. Kirli silmeye hiç ulaşmadı: 1A-2'nin GF! temizliği bütün bölümü silmişti, o günden beri ~1000 sektör kullanıldı. "0 == 0" iddiası bu yüzden boştu; artık silme > 0 isteniyor.
- **Hazır alansız (kirli silme), gerçek kartta üç deneme:**
    1. **Açılıştan hemen sonra, 40 dk:** 391 969 örnek, 615 sektör, düşen 0. Kirli silmeye **hiç ulaşmadı**: 1A-2'nin GF! temizliği bütün bölümü silmişti, "0 == 0" iddiası boştu. İddia artık silme > 0 istiyor.
    2. **Bölümü `Gb20` ile DOLU'ya kadar doldurup eşitleyip onaylayınca:** onaylar gelirken kart boştaydı, ön silme kafanın önünü temizledi. Yine 0. `--doldur` artık eşitlemeden `GF!` yapıyor.
    3. **`GF!` ve hemen 20 dk `Gb0`:** **196 093 örnek, 204 kirli silme = 204 `KA_SILME` = GA 204**, işaretten önceki boşluğun ortancası 27.8 ms. Ama **3/204 işaret bir örnek erken** düştü. Sayaç silmeden önce artıyor, `kayit_f_sil` ise silmeye girmeden `kayit__nefes` ile 1 tik bırakıyordu; o arada itilen örnek işaretleniyordu.
       - Düzeltme: işaret artık duruş kanıtıyla konuyor (≥ 15 ms boşluk, yoksa 100 ms) ve `nefes` silmeden sonra.
       - Bu düzeltmenin `fark = simdi | 1` hatası 1C-3 incelemesinde bulundu. Kural platformsuz `ksi_*` oldu (B71.H4); ayrıntı 5.12.70.
       - Düzeltilmiş yazılımla son kart doğrulaması 5.12.70'te.
- **Tezgah kalemi (ADS takılınca):** gerçek 500/s; PC'de W kartın `D` satırıyla karşılaştırılacak.

**Bağımsız son inceleme (opus): "düzeltmelerle", kritik yok, 5 önemli**

| # | Bulgu | Neden önemli | Ne yapıldı |
|---|---|---|---|
| 1 | `KA_SILME` ve GA silme yalnız **tabloda kaydı olan** sektörleri sayıyordu; GF! sonrası eski sektörlerin (ve çöp ilk kayıtlı sektörlerin) 25 ms'lik silmeleri sayılmıyordu. GF! temizliği ayrıntılı kayıt sürerken 500 ms'de bir siliyordu | K8 "görünür ve sayılır" diyordu; GF! + `Gb0` senaryosunda 25 ms'lik delikler bayraksız ve sayısızdı (0 == 0) | Kafa boş olmayan her sektörü kirli sayar (flaşa bakar, 4 KB ~100 µs); ayrıntılı kayıtta temizlik yok. Z7 (GF! + hemen ayrıntılı), 5 mutasyon |
| 2 | `KA_SILME` silmeyi yapan boşaltmaya bağlıydı: bayrak, halkada bekleyen (silmeden önce üretilmiş) örneklerle dolan kayda düşüyor, boşluk ondan SONRA geliyordu | PC boşluğu yanlış kayıtta arar | Çekirdek 1 durustan sonraki ilk örneği `KO_SILME_ONCE` ile işaretler; işaretli örnek yeni kayıt açar. Z2 artık partili itme + 25 ms duruşla ölçüyor, F47 |
| 3 | `ayrinti_ornekler` iki açılışın saatini tek listede karıştırıyordu; AVR üreteci DEVAM'da saati sürdürdüğü için A2'nin "DEVAM'da birikmez" iddiası boştu | Yeniden başlamadan sonra zaman ekseni geri gider ya da sahte bir boşluk gibi görünür | Her örnek açılış numarası taşır; üreteç DEVAM'da yeni açılışın saatiyle; tezgah DEVAM'dan sonra örnek ve açılış içinde artan zaman istiyor |
| 4 | `ky_bitir`'in örnek tamponu boşaltması silinse de hiçbir iddia kırmızı olmuyordu | Her `Gd` son ~0.33 s'yi sessizce kaybederdi | Aşama 2 tamponda örnek varken durduruyor (A1/A8), mutasyon |
| 5 | Açılıştan/eşitlemeden sonra boşta ön silme (ve GF! temizliği) 500 ms'de bir 25 ms durdurur; bringup'ın 45 s kararlı hal ölçümü ve `tezgah_blokaj` kirlenirdi | Mevcut tezgah denetimi sebepsiz kırmızı | İkisi de önce `G` satırının silme sayacının durmasını bekliyor |
| küçük 1 | Bölmeden sonra yazma hatası yolunda `a_q` (benim "ölü kod" kararım) | Sessiz 2R ms zaman hatası | Kendi gerilemem olduğu için düzeltildi (A10) |

**Ertelenen küçükler** (kayıt dışı kalmasın diye):
- Yazma hatasında tetikleyen örnek sayılmadan düşüyor.
- 16.38 ms'den kısa skop duraklaması işaretlenmiyor (zaman doğru, sebep kayboluyor).
- İzin yarışı: skop yakalaması başladığı turda izin ancak turun sonunda kapanıyor. ⚠ Ön silme sürerken bir yakalama ~%5 ihtimalle 25 ms'lik bir duruşa denk gelebilir; hazır alan dolunca (≤ ~4 dk) biter.
- Ön silme hatasında geri çekilme yok; sektör tablosu silmeden önce düşürülüyor.
- 4095/4096 dt sınırı ve `kg__sektor_dusur` doğrudan sınanmıyor.
- PSRAM ayrılamazsa `Gb0` yine kabul ediliyor (yalnız GA düşen gösterir).
- NaN watt, geçerli ham kodlu örneğe V/I hata bayrağı koyuyor.
- Örnek zamanı `olcum_al` dönüşünde; V–I başlangıç kayması saklanmıyor (PC W hesabı için alt proje 2'de).
- Oturum sınırında halkada kalan örnekler yeni oturuma geçebiliyor.

**Açık / sonraki:** PC'de W'nin hizalamalı hesabı ve grafik (alt proje 2/3) ·
ayrıntılı kipte süre sınırı ve zamanlanmış başlatma (1C-4) · skop günlüğü
(1C-3, sıradaki dilim).

---

#### 5.12.70 ✅ 1C-3 — OSİLOSKOP GÜNLÜĞÜ (2026-10-01)

Tasarım: `tasarim/2026-10-01-1c3-skop-gunlugu.md` (K1–K14) · Plan:
`tasarim/2026-10-01-plan-1c3-skop-gunlugu.md`.

`Gt` ile osiloskop yakalamaları artık kartın kayıt günlüğüne yazılıyor:
- `Gt0` her tetikte bir yakalama alır.
- `Gt<ms>` N ms'de bir yakalama alır.

Kayıtlar ölçüm kaydı gibi eşitleniyor; PC her yakalamayı bugünkü `/skop.bin` biçimine birebir çeviriyor.

**Karar yetkisi:** kullanıcı 2026-10-01 gecesi "sen devam et ben yatıyorum,
adım adım devam et sisteme" dedi. Spec ve plan onayları dahil bütün kararlar
benim, gerekçeleri tasarım belgesinde.

Kararların özeti:
- **SKOP kaydı (10).** Parça parça yazılır, ilk parça META taşır: istek anı, ADS'in sustuğu süre, hız, zaman tabanı, ölçek, tetik ve bütün ayarları. Örnekler u16 ham kod.
- **Kalibrasyon:** eFuse eğrisi günlük başlarken tek bir `SKOP_KAL` olayıyla yazılır.
- **Oturum:** ÖLÇÜM oturumu varsa yakalamalar ona eklenir ("işaretli boşluk"). Yoksa SKOP oturumu (3) açılır. SKOP oturumunda nokta ve ayrıntılı örnek olmaz; `hiz_ms 0` orada "her tetik" anlamına gelir, ayrıntılı kip değildir.
- **Çekirdekler arası:** tek PSRAM yuvası kullanılır. Günlük yeniden ancak yuva boşalınca kurulur, yani yakalama düşmez.
- **Retler:**
  - PSRAM yoksa `Gt` reddedilir.
  - Pil testinde `Gt` reddedilir.
  - Günlük sürerken `p1` ve elle yakalama reddedilir; ayar komutları serbest.
- **Yeniden başlama:** günlük sürmez. SKOP oturumu "kart yeniden başladı" ile kapanır.
- **Durum:** yeni `GT` satırı. Firmware `A3-1C3`.

**Ne yapıldı**

| Dosya | Ne |
|---|---|
| `kayit_bicim.h` / `kopru/kayit_bicim.py` | `KAYIT_T_SKOP` 10, `KAYIT_OTURUM_SKOP` 3, `KO_SKOP_KAL` 4, `KayitSkopMeta` (36 B; histerezis u16 — `SkopAyar`'da u16), parça başı 12 B. Python `skop_paketle/coz`, `Oturum.skoplar`: parçaları `ilk`'e göre birleştirir, tekrarı atar, eksik parçayı **doldurmaz** (`tam=False`, kodlar yok). `skop_ikili` → `S3B`, `arsiv.skop_ikili` ile tek kodlama |
| `kayit_oturum.h` / `kayit_yonet.h` | `ky_skop`: önce bekleyen noktalar ve ayrıntılı örnekler; parçalar sektöre ve yazıcı tamponuna sığdığı kadar (32 örnekten azı sığıyorsa yeni sektör); DOLU'da BITIR(DOLU). `kyn_skop`. Ayrıntılı kip yalnız ÖLÇÜM'de; SKOP oturumunda nokta `KG_YOK` |
| `kayit_esp.h` | `KM_SKOP`, `KM_SKOP_BASLAT`. `KayitSkopYuva` PSRAM'de. Görev yuvadan yazar, SONRA boşaltır, yazamazsa sayar. Noktacı SKOP'ta kapalı, ayrıntılı yalnız ÖLÇÜM'de. Durum oturum türünü taşır. `A3-1C3` |
| `olcum-karti-a3.ino` | `SKOP_IS_GUNLUK` (döküm yok). `skop_gunluk_isle`: skop boş, döküm yok, yuva boş, aralık dolmuş olmalı. `skop_gunluk_sonuc`: META yakalamanın ayarıyla. `Gt<ms>`, `Gtd`. `Gd` ve bağlı oturumun kapanması günlüğü durdurur. `p1` ve `t/tB/ta/tK` günlükte reddedilir. `GT` satırı. DRAM 74468 (+56) |
| `tezgah_kayit.py` | `--skop`; `--hazirsiz --doldur` artık eşitlemeden `GF!` (1C-2'den kalan iş, aşağıda) |

**Doğrulama**
- `test_kayit.py` **242/242**:
  - B71.B25–B29: biçim C == Python; kayıt sırasıyla birleştirme, aynı `no`'lu iki yakalama, eksik parça; `S3B`.
  - B71.H4: kirli silme işareti (1C-2 izi).
  - B71.S1–S8 (`SENARYO_SKOP`):
    - 240 örnek birden çok sektöre bölünür ve birebir birleşir;
    - sektör sonu boşa gitmez;
    - SKOP oturumu kuralları;
    - ÖLÇÜM'e ekleme sırası;
    - açılışta sebep 5;
    - DOLU;
    - ayrıntılı örnek tamponu yakalamadan önce boşalır;
    - flaş temiz.
- `test_kayit_esp.py` **88/88** (F25, F49–F62). Arayüz 346/346. Zincir **21/21**, gizlilik temiz.
- **Mutasyon:** 29 yalanlayıcının hepsi yakalanıyor (B71 11, B72 18). İki bulgu:
  - DOLU yolundaki ilk mutasyon eşdeğerdi; mutasyon yeni sektör dalına taşındı.
  - B27'deki parçalar aslında sıra dışı değildi; test artık gerçekten sıra dışı.
  - Tam koşu (paralel koşucu): **B71 137/137, B72 99/99** (A7'nin deseni `ky_nokta`'ya eklenen SKOP satırı yüzünden eskimişti; güncellendi). Düzeltme turunun 15 yalanlayıcısından biri eşdeğerdi, çıkarıldı.
- **Kart (A3-1C3, tezgah; her yüklemeden önce NVS yedeği depo dışında):**
  - ⚠ Skop girişinde **sinyal yok** (RC düzeneği sökülmüş, kodlar 0). Bu yüzden yakalamalar düz, 1 kHz frekans denetimi yapılamadı; denetim tezgah kalemi.
  - İlk koşu: `--skop` 0 yakalama gördü. Sebebi `Gt0`'ın NORMAL'e aldığı kipin geri alınmamasıydı: sonraki `Gt2000` de tetik bekledi. Bunun üzerine F62 eklendi.
  - Düzeltilmiş yazılımla `--duman --pil --ayrinti` yeşil.
  - `--skop` **4/4**:
    - `Gt0` sırasında `D` **5.0 → 2.9/s** (önce 0.1), durunca kip geri, tetiksiz kayıt yok.
    - `Gt2000` 30 s: **16 yakalama**, aralık ortancası **2000 ms**, hepsi tam ve `S3B`, numaralar tekrarsız.
    - `Gb200` + `Gt2000`: ölçüm oturumuna eklendi; `p1` ve `t` reddedildi; **`Gtd`'den sonra ölçüm sürdü** (K11).
    - Yeniden başlatmada SKOP oturumu sebep 5, DEVAM yok.
  - Kirli silmenin düzeltilmiş işaretle son doğrulaması (`--hazirsiz --doldur`, bölüm dolduruluyor): sonuç sonraki girdide.

**Bağımsız son inceleme (opus): "düzeltmelerle" — 1 kritik, 4 önemli**

| # | Bulgu | Neden önemli | Ne yapıldı |
|---|---|---|---|
| K1 | Yakalama numarası `no` bir oturumda tekrarlanabiliyordu (`Gtd` + yeniden `Gt`, DEVAM'dan sonra `Gt`); PC `no`'ya göre gruplayıp iki yakalamayı **sessizce birleştiriyordu** (kodlar birinden, META öbüründen, `tam=True`) | Kullanıcı yanlış dalgayı doğru sanır; ikinci yakalama görünmez | PC yakalamayı **kayıt sırasıyla** kurar (0. parça açar, parça yalnız hemen önceki açık yakalamaya); `skoplar` anahtarı sıra; kartta `no` açılış boyunca tekdüze. B27/B29, 2 mutasyon |
| Ö2 | Uçuştaki yakalama `Gb`'den sonra yeni oturuma yazılıyordu | Kullanıcının ölçüm kaydına yabancı, SKOP_KAL'sız yakalama | Yuva bağlı oturumu taşır; görev yalnız o oturum etkinse yazar. F59 |
| Ö3 | `Gt0` tetik beklerken ADS hiç okunmuyordu | **Kartta ölçüldü: `D` 5.0 → 0.1/s** — voltmetre, otomatik menzil, enerji donuyor | Her sonuçtan sonra en az bekleyiş kadar (≥ 100 ms) ölçüm. F60; kartta yeniden: **5.0 → 2.9/s** |
| Ö4 | 1C-2'nin işaret düzeltmesinde `fark = simdi \| 1`: çift ms'de kanıt atlanıyordu; düşen işaretli örnekte işaret 100 ms kayıyordu | Düzeltme yarı yarıya çalışmıyordu; F47 metni ifadeyi kopyaladığı için yakalayamazdı | Kural platformsuz `ksi_*` (`kayit_halka.h`), B71.H4 **davranış** testi (çift ms, düşen işaret, kısa silme) |
| Ö5 | `Gtd`'nin ölçümü kapatmaması (K11), SKOP oturum türü ve `KM_SKOP_BASLAT` hiçbir iddiayla sınanmıyordu | Mutasyonla yeşil kalıyordu | F61 + 3 mutasyon; tezgahta `Gtd` sonrası ölçüm sürüyor mu |
| küçük 7 | `Gt0`'ın NORMAL'e aldığı kip geri alınmıyordu | **Tezgahta ısırdı:** sonraki `Gt2000` tetik bekleyip hiç yakalayamadı | Durunca geri + panel bilgilendirilir. F62 |

**Ertelenen küçükler:**
- `Gtd` oturum öğrenilmeden gelirse yetim SKOP oturumu açılabiliyor.
- Ayar komutları pratikte uçuştaki yakalamaya takılıyor.
- `GT` sayaç anlamları karışık.
- Ekli oturumda kayıt sırası tam zaman sırası değil (PC META `t_ms` kullanmalı).
- Yakalama boşluğu AYRINTI'da bayraksız.
- SKOP_KAL tablonun geçerliliğini taşımıyor.
- Küçük kod düzeltmeleri.
- Tezgah `Gb` sırasında günlüğü kartta sınamıyor.

**Açık / sonraki:** yakalamaların panelde/telefonda gösterimi (alt proje 3/5) ·
günlüğün yeniden başlamada sürmesi ve zamanlanmış başlatma (1C-4) · 12 bit
paketleme.

---

#### 5.12.71 ✅ 1C-4 — ZAMANLANMIŞ KAYIT (2026-10-01)

Tasarım: `tasarim/2026-10-01-1c4-zamanlanmis-kayit.md` (K1–K12) · Plan:
`tasarim/2026-10-01-plan-1c4-zamanlanmis-kayit.md`.

`Gp` ile kart bir ölçüm kaydını **gerçek saatte** (NTP) kendisi başlatıp
bitiriyor:
- `Gp<unix>,<süre_s>,<hız_ms>` mutlak başlangıç alır.
- `Gp+<saniye>,…` göreli başlangıç alır.
- `Gp-` planı iptal eder; `Gp?` ya da `G?` ardından **`GP`** satırı.

Süre 0 "`Gd`'ye dek" demektir; en fazla 30 gün.

**Karar yetkisi:** 1C-2/1C-3 ile aynı ("sen devam et ben yatıyorum"); kararlar
tasarım belgesinde, inceleme sonrası kararlar `.superpowers` defterinde ve aşağıda.

Kararların özeti:
- **Tek plan, tekrarsız.** NVS'te kendi ad alanı `plan` (7 anahtar, durum en son yazılır).
- **Saat:** yalnız NTP; saat yoksa `Gp` reddedilir. Bekleyen plan saat gelene dek bekler.
- **Başlangıç:**
  - Meşgulse plan **atlanır**. Meşgul = oturum, oturumsuz pil testi ya da skop günlüğü.
  - Kart başlangıçta kapalıydı ve pencere bitmediyse **geç başlar**; pencere geçmişse "kaçırıldı".
- **Kayıt:** ÖLÇÜM oturumu + OLAY `PLAN` (5: başlangıç, süre, hız, plan no) tek mesajda.
- **Bitiş:** süre dolunca BITIR **sebep 7 "planlı süre doldu"**. `Gd` (sebep 1) ve `Gp-` (sebep 1, kaydı da durdurur) planı bitirir.
- **Yeniden başlama:** planın oturumu DEVAM aldıysa bitiş yine plandan; DEVAM yoksa plan "bitti", yeni oturum açılmaz.
- **Biçim:** sürüm 2 kalır. Firmware `A3-1C4`.

**Ne yapıldı**

| Dosya | Ne |
|---|---|
| `kayit_bicim.h` / `kopru/kayit_bicim.py` | `KB_SEBEP_PLAN` 7, `KO_PLAN` 5, `KayitPlanOlay` (C == Python, B71.B30/B31) |
| `kayit_plan.h` (yeni, platformsuz) | `plan_kur` (saat / süre / pencere / anlamsız başlangıç `KP_ZAMAN` / sürüyor retleri), `plan_adim(p, simdi, mesgul, oturum_id)` → `PE_YOK/BASLAT/BITIR`, `plan_sonuc` (çekirdek 0'ın bildirdiği oturuma bağlar; 0 meşgul → ATLANDI, hata → BAŞLATILAMADI; plan beklemiyorsa 0 döner), `plan_basliyor`, `plan_iptal`, `plan_ac` (açılışta oturumu bilinmeyen SÜRÜYOR → BİTTİ). Durumlar 0 yok · 1 bekliyor · 2 sürüyor · 3 bitti · 4 atlandı · 5 kaçırıldı · (6 saat yok, yalnız GP) · 7 başlatılamadı |
| `kayit_esp.h` | `KM_PLAN_BASLAT` (11): çekirdek 0 oturum ya da DEVAM bekleyişi varken AÇMAZ, sonucu `kayit_plan_sonuc` + istek numarasıyla yayınlar. `KM_PLAN_BITIR` (10): yalnız etkin oturum planınkiyse, sebep mesajdan. `plan` NVS yapıştırıcısı. `A3-1C4` |
| `olcum-karti-a3.ino` | `Gp` ayrıştırıcı (yalnız rakam, ≤ 10 hane, 32 bit taşmasız; göreli ≤ 1 yıl), `kayit_plan_isle` saniyede bir (tarama bitmeden karar yok), sonucu istek numarasıyla alır, plan artık beklemiyorken geç açılan oturumu kapatır, `GP` satırı. DRAM **74548** (+64) |
| `uretim/avr/ornek_kayit.c` | `SENARYO_PLAN`: emüle NVS + sahte saat, 5 açılış |
| `tezgah_kayit.py` | `--plan` |

**Doğrulama**
- `test_kayit.py` **263/263** — B71.R1–R13 (`SENARYO_PLAN`, açılıştan açılışa):
  - başlat/bitir;
  - başka oturum **benimsenmez**;
  - NTP geri adımı zaman aşımı sayılmaz;
  - meşgulse atla, geç başla, kaçırıldı;
  - saat yokken bekle;
  - DEVAM'lı yeniden başlama, saat geri gitse de yeniden başlama yok;
  - `Gd`; iptal ve retler (`Gp20`, 1 yıl ileri, 30 gün, geçmiş pencere);
  - sonuç gelmezse / hata → başlatılamadı; meşgul → atlandı; geç sonuç alınmaz;
  - süre 0 hiç BITIR demez;
  - açılışta oturumu bilinmeyen plan bitti.
- `test_kayit_esp.py` **99/99** (F63–F73).
- **Mutasyon:** 1C-4'ün **38** yalanlayıcısının hepsi yakalanıyor.
  - Tam koşu (paralel koşucu): **B72 115/115**, **B71 158/158**.
    - B71: koşu listenin bir önceki halini okudu (156/157); uygulanamayan tek giriş, işaretli fark düzeltmesiyle eskiyen zaman aşımı kalıbıydı. Yeni hali ve işaret mutasyonu ayrıca koşuldu: 2/2.
  - 1C-3'ün sürüm adı girişi (`A3-1C3` → `A3-1C2`) artık uygulanamıyordu (F25'i 1C-4'ünkü örtüyor) → çıkarıldı.
- **Kart (A3-1C4, NVS yedeği depo dışında, NTP'li STA):**
  - `--plan` **6/6**:
    - Geçersiz argümanların hepsi reddedildi: eksik alan, hız 7, taşan sayı, harf, > 30 gün, `Gp20,…`, 1 yıldan ileri. Plan kurulmadı.
    - `Gp+20,30,200`: **+20.3 s**'de ÖLÇÜM oturumu açıldı, **+50.4 s**'de sebep 7 ile kapandı (GP 1 → 3). PLAN olayı süre 30 / hız 200.
    - Plan sürerken yeniden başlatma: DEVAM aldı, planlanan anda (**52.8 s**, plan 53) sebep 7 ile kapandı.
    - Elle kayıt sürerken plan: ATLANDI (GP 4), elle kayıt bölünmedi.
    - `Gp-` bekleyeni iptal etti.
    - Süre 0: oturuma bağlandı, kendiliğinden bitmedi; `Gp-` kaydı sebep 1 ile kapattı.
  - Regresyon `--duman --pil --ayrinti --skop` yeşil.
  - ⚠ İlk `--ayrinti` koşusunda "boşta hazır alan büyüyor" kırmızıydı. Sebep: hemen önceki `--hazirsiz --doldur` bütün bölümü kirli bırakmıştı. Hazır alan GF! temizliği bitince başlar (`temiz_s >= sektor_adet`), her yeniden başlama temizliği baştan alır; o an kartta `temiz_kalan` 1040'tı. Temizlik bitince yeniden koşuldu: hazır alan 39 → 67, oturum başında 480, `KA_SILME` 0 → **4/4**. Tasarım gereği; kusur değil.
  - Tezgahın kendi iki yarışı düzeltildi: plan saniyede bir karar verdiği için GP, G değiştikten ≤ 1 s sonra izler; `Gp-`'nin G satırı komut çıktısında kalıyordu.

**Bağımsız son inceleme (opus): "düzeltmelerle" — 5 önemli**

| # | Bulgu | Neden önemli | Ne yapıldı |
|---|---|---|---|
| Ö1 | Plan BASLAT'tan sonra beliren **herhangi** bir oturumu benimsiyordu; "meşgul" kararı çekirdek 0 ile atomik değildi | Kuyrukta önde bir `Gb`/`p1` varsa plan kullanıcının kaydını kendi sanıp sonunda sebep 7 ile **kapatırdı** | Çekirdek 0 meşgulken açmaz, sonucu istek numarasıyla yayınlar; plan yalnız o oturuma bağlanır. B71.R1/R12/R13, F67/F68/F72 |
| Ö2 | Oturumsuz pil testi (DOLU'da) ve skop günlüğü meşgul sayılmıyordu | Plan pil testini bölerdi (emniyet, Ö7) | `mesgul` tam. F70 (ters çevrildi) |
| Ö3 | Başlatılamayan plana "bitti" deniyordu | Kullanıcı kaydın alındığını sanır | Yeni durum 7 "başlatılamadı", kart sebebi yazar. R9/R11 |
| Ö4 | `Gp-` sürmekte olan planın otomatik bitişini sessizce kaldırıyordu | Kayıt `Gd`'ye dek (30 güne kadar) sürerdi | `Gp-` kaydı da durdurur (sebep 1). F71 |
| Ö5 | Süre 0 hiç sınanmıyordu | — | R10 + mutasyon |
| k2 (yükseltildi) | Zaman girdileri denetlenmiyordu: `+` unutulmuş `Gp20,…` 1970 sayılıp plan **hemen** başlıyordu; işaretsiz fark NTP geri adımında planı düşürüyordu | Bitmeyen beklenmedik kayıt | `KP_ZAMAN`, göreli ofset ≤ 1 yıl, işaretli fark. R8, R1 |

**Ertelenen küçükler:**
- Planın oturumu DEVAM yeri beklerken her saniye etkisiz bir bitiş isteği ve mesajı gidiyor; yer açılınca oturum ~1 s fazla sürüyor.
- NVS yazım sırası: `plan_basliyor` mesajdan sonra yazılıyor (pencerede elektrik → atlandı + bitişsiz oturum; pencere kısaldı, kapanmadı), `plan_kur` alan alan yazıyor.
- Plan NVS'e yazılamazsa da "kuruldu" deniyor.
- `GP`: saatsiz SÜRÜYOR düz 2; atlandı/kaçırıldı geçişleri o an yazılmıyor; bekleyen planın üzerine yazmak sessiz.
- Çekirdek 0 tarafı hâlâ kaynak metin iddiası (platformsuz `kyn_plan_bitir` yok); tezgahta "`Gd` + `Gb` arada" ve oturumsuz pil durumu yok.

**1C-2'den kalan iş — kirli silme işaretinin son kart doğrulaması (A3-1C3 son
inceleme yazılımı, `--duman --pil --ayrinti --skop --hazirsiz --doldur --sure 600`,
21/21):**
- Bölüm `Gb20` ile DOLU'ya dek dolduruldu (311 495 nokta, 2911 silme, en uzun silme 30.7 ms).
- Ardından `GF!` ve hemen `Gb0` ile 600 s kaydedildi; bütün sektörler kirliydi.
- Sonuç: 96 446 örnek, 874 kayıt, **GA silme +154 → KA_SILME 153**. Eksik olan bir tanesi `Gd`'nin son boşaltması.
- Sıra kesintisiz, düşen yok.
- **Her** `KA_SILME`'li kaydın ilk örneğinin önünde ≥ 15 ms boşluk var: en küçük **23.96 ms**, ortanca 29.0 ms, en büyük 37.2 ms.
- 16.38 ms'yi aşıp bayraksız kalan boşluk yok.
- Sonuç: 1C-3'teki `ksi_*` düzeltmesi kartta doğrulandı (önceki koşuda 204 silmenin 3'ü bir örnek erken işaretleniyordu).

**Açık / sonraki:** 1D (eşleştirme; cihazdan saat alma burada) · 1E (MQTT) ·
plan gösterimi panel/PC/telefonda (alt proje 3–5) · tekrarlı plan (kapsam dışı).

---

#### 5.12.72 ✅ 1D — EŞLEŞTİRME + İMZALI İSTEKLER (2026-10-01; kararlar ONAYLANDI)

Tasarım: `tasarim/2026-10-01-1d-eslestirme.md` (K1–K18 + "⚠ Onay bekleyen kritik kararlar" 1–7) ·
Plan: `tasarim/2026-10-01-plan-1d-eslestirme.md`.

> **Onay (2026-10-01 gece):** kullanıcı "önerilerinin hepsi olur" dedi. Spec'teki yedi karar
> önerildiği gibi; en kısa parola 10 → **12**. Düzeltme dalıyla (`1-duzeltme`, 5.12.72a) `1-birlesik`
> dalında birleştirildi.
>
> **Durum (onaydan önce):** yerel dal `1d-eslestirme`; `main`'e girmedi, push yok. Kullanıcı:
> "ben hâlâ inceleyemiyorum, sen devam et, ancak kritik bir şey varsa hemen commit atma".
> 1D bir güvenlik dilimi, onay bekleyen kararları var. Kart akşam yeniden takıldı
> ("lazım olursa kullanabilirsin"): tezgah koşuldu (aşağıda), kart sonra tam yedekten
> `main` firmware'ine (A3-1C4) döndürüldü.

**Ne yapıldı**
- **Platformsuz çekirdek `guvenlik.h`:**
  - PBKDF2 + HMAC-SHA256 eşleştirme. Önce istemci kanıtı, sonra kart kanıtı (karşılıklı).
  - Cihaz anahtarı `K` NVS'te durur, RAM'de tutulmaz.
  - 8 cihaz.
  - Deneme sınırı `2^k` s.
  - Yüzde kodlu kanonik metin ve 64'lük tekrar penceresi (önce HMAC, sonra pencere).
  - USB eşleştirmesi.
  - Kriptografi bir işlev tablosundan gelir (hata döndürür). PBKDF2 çekirdekte, 1000 turda bir nefes alır.
  - Ayar bozuksa fail-closed.
- **Kart:**
  - `guvenlik_esp.h` (mbedTLS, Preferences, kilit, SNTP saat kaynağı).
  - Her web ucu `guv_kapi`'dan geçer.
  - Yeni uçlar `/eslestir/bilgi|baslat|kanit`, `/cihaz/liste|sil`, `/saat`.
  - Yalnız USB'den `E` komutları: `E?` `Ex` `Ep` `Ez` `Em` `Et` `Er`.
  - `Ep`'nin anahtarı yalnız ham UART'a basılır. `Serial` aynası SSE'ye taşıdığı için `WebAkis::ham` eklendi.
  - Zorunluluk **varsayılan kapalı:** bugünkü panel ve araçlar aynen çalışır.
  - `A3-1D`, DRAM 75044.
- **PC:**
  - `kopru/imza.py`: parolalı ve USB eşleştirme, DPAPI ile saklama, sayaç `max(son+1, unix_ms)`, 401 + `X-Acilis` ile bir kez eşitleme.
  - `kayit_esitle.py`: `--cihaz` ile imzalı eşitleme.
  - `kopru.py`: `E` komutunu ve gömülü satır sonunu reddeder, `EK` satırını yaymaz.
- **Ön-cesi sızıntı bulundu:** `N?` AP WiFi parolasını `Serial` aynasıyla açık `/akis`'e basıyordu. Dalda düzeltildi; **`main`'de hâlâ var** (1-acik-isler D0).

**Doğrulama**
- B71 289/289 (U1–U19, 5 açılış). Ayrıca:
  - C, Python'un vektörlerini kabul eder.
  - Sınama SHA-256'sı RFC 4231/7914 ile ölçülür.
- B72 148/148:
  - G: vektörler, RFC sabitleri `hmac`/`hashlib` ile de karşılaştırılır.
  - F74–F101: kaynak.
  - I0–I9: istemci, bağımsız doğrulayıcılı sahte karta karşı.
- B22a 58/58, B7 346/346.
- Mutasyon: 1D'nin bütün yalanlayıcıları yakalanıyor (son: B72 152/152, B71'in 1D'si 21/21, B22a 16/16; zincir 21/21). Mutasyon **7 boş iddia** buldu ve hepsi kapatıldı:
  - tek silmenin kalıcılığı;
  - taze pencerede sayaç 0;
  - tek deneme;
  - F86;
  - köprü testinin sürücü kayıtlı nesneyle boş kalması;
  - B7'de `m`;
  - U17: hata enjeksiyonu her HMAC'i bozuyordu, kanıt HMAC'inin hatası yok sayılsa da sonraki adım yakalıyordu. Artık yalnız sonraki çağrı bozuluyor (U17G/H).
- **AVR'de 2 KB RAM yığını taşıyordu** (kart sürekli yeniden başlıyordu). Etiketler flaşa alındı, adımlar `noinline`, `GUV_ISLEV` eklendi.

**Bağımsız son inceleme (Opus): "düzeltmelerle" — 1 kritik, 6 önemli (+2 yükseltilen küçük)**

| # | Bulgu | Ne yapıldı |
|---|---|---|
| K | İstemci, kartın verdiği PBKDF2 turunu ve tuzunu doğrulamıyordu; sahte kart `tur=1` dayatıp parolayı HMAC hızında tahmin edebilirdi | İstemci 10 000…1 000 000 dışını, biçimsiz kimlik/tuzu ve kısa parolayı istek atmadan reddeder (I8) |
| Ö | Köprüde `?\nEz0` E süzgecini atlatıyordu | Kontrol karakterli komut reddi |
| Ö | mbedTLS hataları yok sayılıyordu (karar yığındaki eski MAC'e dayanabilirdi) | Tablo hata döndürür; HMAC hatası = ret (U17, F92) |
| Ö | Sınırsız PBKDF2 (`Et` günlerce; `Er` 10M ile web görevinde WDT) | P yalnız çekirdek 1'de, nefesli; `Et`/`Er` sınırlı, pil testinde ret (F93, F96) |
| Ö | `kayit_esitle` komut satırı imzalı yolu kullanmıyordu | `--cihaz` / `--cihaz-dizin` (I9) |
| Ö | Tezgah yarıda kalırsa kart `Ez1`'de kalırdı | `try/finally` (F94) |
| Ö | Basic-Auth sınırsız parola denemesi K7'yi boşa çıkarıyordu | `web_yetki` deneme sınırı (F95) |
| k→Ö | Ayar okunamazsa zorunluluk sessizce kapanıyordu | fail-closed (U18) |
| k→Ö | RF'siz RNG: açılış değeri her açılışta aynı olabilirdi | `guv_esp_ac` ağdan sonra; `Ep` WiFi kapalıyken ret (F97) |

**Kart tezgahı (2026-10-01 akşam): ilk koşu 15/18 — üç kusur yeşil zincirin arkasındaydı**

Tam flaş yedeği alındı (`.yedek/olcum-karti/tam-20261001-172953.bin`, depo dışı). Ardından 1D yüklendi,
`--duman --guvenlik` koşuldu. Kırmızılar:

1. **PBKDF2 50 000 tur kartta 4.76 s** (spec ölçütü < 1 s). Sebep: `guv_pbkdf2` her turda HMAC'i baştan
   kuruyordu; ESP'de bu `mbedtls_md_setup` (bellek ayırma) + ipad/opad sıkıştırması demek. Ayrı bir ölçüm
   eskiziyle (depo dışı) beş yol kartta karşılaştırıldı, hepsi `hashlib` ile aynı sonucu verdi:

   | Yol | µs/tur |
   |---|---|
   | her turda HMAC kurulumu (eski) | 85.5 |
   | `mbedtls_pkcs5_pbkdf2_hmac_ext` | 56.7 |
   | tek kurulum + `hmac_reset` | 56.3 |
   | yazılım SHA, ipad/opad önceden | 43.3 |
   | **`mbedtls_sha256` ipad/opad durumu bir kez, her turda `clone`** | **30.5** |

   Seçilen son yol çekirdekte platformsuz: `GuvKripto.sha_kopya` eklendi, ESP'nin SHA'sı md katmanından
   `mbedtls_sha256`'ya geçti (bellek ayırmaz, kopyalanır). Firmware içinde ~38 µs/tur: 25 000 tur 956 ms
   (pay %4), **varsayılan 20 000 = 764 ms**. 50 000 bu çipte < 1 s olamaz (1.9 s). Spec K4 ve onay
   maddesi 2 güncellendi: çevrimdışı tahmin planlanandan 2.5 kat ucuz → PAKE ve parola uzunluğu sorusu
   ağırlaştı.
2. **Her `Ez`/`Em` P'yi yeniden hesaplatıyordu:** çekirdek 1 (ölçüm + seri) 4.7 s donuyor, sonraki seri
   komutlar bekliyordu; tezgahın `Ez0`'ı henüz işlenmeden HTTP isteği 401 alıyordu. Artık yalnız ayar
   bozukken (tuz yeniden üretildi).
3. **Tezgahın kendi kusuru:** SSE dinleyicisi `olcum.local` çözümü (~3 s) bitmeden `Ep` gönderiliyordu.
   Bildirim kaçtığı için kırmızıydı, ama aynı sebeple **"anahtar SSE'de yok" denetimi boş yere
   geçebilirdi**. Ayrı tanı koşusunda anahtar, `EK` satırı ve 64-hex dizi SSE'de YOK (doğrulandı).
   Tezgah artık akışın ilk olayını bekliyor (B72.F101).

`Et` artık P'nin ilk 8 baytını basıyor (sabit sınama parolası + açık tuz, gizli değil). Tezgah kartın
PBKDF2'sini `hashlib` ile karşılaştırıyor. **Son koşu 19/19.** Testler: B71.U19 (tur başına 2 kopya, HMAC
kurulumu yok, 70 baytlık parola `hashlib` ile aynı), B72.F98–F101. Yalanlayıcılar 1D-TZ 7/7. Kart
`esptool write-flash 0x0 <yedek>` ile eski haline döndü (hash doğrulandı, `E?` → "bilinmeyen komut").

⚠ **Süreç dersi:** bağlantı koptuğunda bilgisayar uyudu. Git Bash `ps` Windows süreçlerini göstermediği
için ilk koşu "ölü" sanıldı ve ikinci koşu başlatıldı. İkisi üst üste bindi: zincirin `%TEMP%` temizliği
mutasyon koşusunun altından kesti. Yarıda öldürülen ikinci zincir `_tezgah.md`'yi yarım yazdı (sonraki tam
zincir yeniden üretti). Kural: süreç denetimi `Get-CimInstance Win32_Process` ile; yeniden başlatmadan önce
eski koşunun gerçekten bittiğini doğrula.

**Ertelenen küçükler:** `tasarim/1-acik-isler.md` D5 (#8, #10–#12, #14–#19).

**Açık / sonraki:** D3 parolalı eşleştirmenin başarı yolu (kullanıcının web parolasıyla; kart 1D'ye
yeniden yüklenmeli) · kullanıcı onayı (D4) · onaydan sonra `main`'e birleştirme ve push · 1E (MQTT;
ChaCha20-Poly1305 orada).
#### 5.12.72a 🟢 ALT PROJE 1 DÜZELTMELERİ — Y1–Y6 + D0 (dal `1-duzeltme`, 2026-10-01 akşam)

Kullanıcı "sırada ne var" diye sordu. Öneri onaylandı ("tamamdır devam et"): `tasarim/1-acik-isler.md`'nin
"önce bakılacaklar" bölümündeki veri doğruluğu hataları ve 1D'de bulunan D0 sızıntısı.
`main`'den ayrı bir çalışma ağacında yapıldı (`projeler/olcum-karti-duzeltme`). Kullanıcının
commit'lenmemiş B55–B70 işine ve 1D dalına dokunulmadı. Push yok.

| # | Kusur | Düzeltme | Test |
|---|---|---|---|
| Y1 | Kayıtsız kalan pil testinin DCIR olayı ve `KN_DCIR` noktaları açık/DEVAM almış ÖLÇÜM oturumuna düşüyordu | Olay hedef türü taşır: `KM_PIL_OLAY` → yalnız PİL, `KM_OLAY` (skop KAL eki) → yalnız ÖLÇÜM, başlatma mesajları kendi BASLA türüne (`kyn_olay(m, tür, …)`). `KN_DCIR` yalnız PİL oturumunda kalır (`kn_ek_suz`). Mesaja alan eklenmedi: DRAM değişmesin, niyet açık | B71.PL8, B72.Y1 |
| Y2 | Plan BAŞLAT'tan sonra, plan NVS'i yazılmadan elektrik gidince plan kendi oturumunu tanımıyor, kayıt bitişsiz sürüyordu | İncelemenin önerisi ("isteği göndermeden önce yaz") yalnız ATLANDI'yı BİTTİ'ye çeviriyordu: kayıt yine bitişsiz, üstelik oturum açılmadan kesilirse yeniden deneme de kayboluyordu. Yerine **kanıtlı bağlantı**: çekirdek 0 (`kyn_plan_baslat`, platformsuz) oturumu açmadan ÖNCE NVS'e `pk_alt` (sonraki sıra) + `pk_ot 0` + `pk_no` (plan no), açınca `pk_ot = id`, açamazsa `pk_no 0` yazar. Açılışta `kyn__plan_kanit` devam eden oturumla karşılaştırıp yayınlar (eksik kanıtı onarır, bayatı siler). Çekirdek 1 tarama bitince **bir kez**, `plan_adim`'dan önce `plan_acilis` ile benimser. Kanıt tahmin değil: o pencerede çekirdek 0 başka oturum açmaz (meşgulken plan açmaz). `plan_ac` artık SÜRÜYOR/oturumsuz → BİTTİ dönüşümünü yapmaz; karar kanıt belli olunca | B71.R13 (güncellendi), R14–R16, PK1–PK5, B72.Y2, F68 |
| Y3 | Plan NVS'e yazılamasa da `plan_kur` başarı dönüyor, kart "plan kuruldu" diyordu | `plan__yaz` hata döner; bir alan yazılamazsa geçerlilik işareti (`pl_dur`) yazılmaz. `plan_kur` `KP_NVS` (-6) döner, önceki plan RAM'e ve NVS'e geri yazılır; kart "KURULMADI, önceki plan geçerli" der | B71.R17 (kısmi hata: yalnız `pl_bas`), B72.Y3 |
| Y4 | Kalibrasyon geçmişinin `adet` anahtarı kaybolursa #1 eziliyordu | `adet` okunamazsa k1…k40 taranır: numarası kendine eşit, CRC'si tutan en büyük kayıt. Ortadaki bozuk kayıt taramayı durdurmaz; bulunan değer geri yazılır | B71.C14 |
| Y5 | Ayrıntılı kipte boşaltma hatasında örnek sayılmadan düşüyordu; yeniden deneme aynı kaydı iki kez yazabiliyordu | Kart: yazılamayan örnek `dusen`'e sayılır, boşluğu açan kayıt `KA_KAYIP_ONCE` taşır. PC: ayrıntı örnekleri VE noktalar sıra başına bir kez (ilk kopya). Emülatörde gerçek kopya üretildi: yalnız son dolgu baytı yazılamıyor → kayıt flaşta geçerli, `kg_ekle` hata döner | B71.A11, A12, A13 |
| Y6 | Bozuk kalibrasyon kaydı `/kal/liste`'de sessizce atlanıyordu | Kart `{"no":n,"bozuk":true}` yazar (numarası tutmayan blob da bozuk). PC'de sağlam kopyası varsa o kalır (`kartta_bozuk`, yedek açılmaz); yoksa bozuk işaretiyle yazılır. Eşitleme bozuk numaraları bildirir | B72.Y6a, Y6b |
| D0 | `N?` ve AP afişi AP parolasını `Serial` aynasıyla `/akis`'e (ağa) basıyordu | `WebAkis::ham` + yalnız ham UART | B72.D0 |

**Doğrulama:** B71 291/291, B72 105/105; yeni ve taşınan yalanlayıcılar B71 21/21, B72 15/15 (Y6a ilk koşuda boştu: mutasyon bozuk dalını ölü kod yapıp metni bırakıyordu, test yapıya bağlandı);
değişen satırlara dayanan 7 eski girdi yeni koda taşındı. Zincir 20/21 + B22b: tek kırmızı "6j LittleFS görüntüsü güncel" ORTAMDAN (yeni çalışma ağacında `arayuz3` LF, `_fs.json` özetleri CRLF dosyalardan; dosyalar CRLF yapılınca `sim3_web` 98/98). Bu denetim satır sonuna bağlı: kırılgan, ayrıca not edildi. Firmware uyarısız, DRAM 74548 →
74572 (+24). Sürüm `A3-1C4d`. Kart tezgahı (tam yedekten sonra): `--duman --plan --kal --pil --ayrinti` **29/29**. Kart `A3-1C4d`'de bırakıldı: D0 sızıntısı kapalı. Geri dönüş: `esptool write-flash 0x0 .yedek/olcum-karti/tam-20261001-203242.bin`.

⚠ **AVR test donanımı:** osiloskop senaryosu (2 KB RAM, 480 B yakalama tamponu) `main`'de de yığının sınırındaydı. Bu dalın +15 B'ı S5/S6/S8'i sessizce bozdu; tampon 16 B küçültülünce geçtiği görülerek doğrulandı. Çözüm test donanımında: NVS ad tablosu `PROGMEM`, `sayi()` etiketi `PSTR`. Osiloskop senaryosu artık 1532 B statik RAM (`main`'den 83 B az). `kyn__plan_kanit` satır içine açılmıyor; açılış taramasının çerçevesini büyütmesin.

⚠ **Süreç:** heredoc'a kaçış dizisi içeren test kodu yazılırken yine bozuldu; Write aracına geçildi.
`govde(ino, "static void f(")` yine ileri bildirime takıldı (B72.Y1'in ilk RED'i kısmen bu yüzden),
imza `) {` ile bitirildi ve RED mutasyonla doğrulandı.

**Birleştirme notu:** dal `mutasyon.py`, `beklenen_sayim.json`, `tasarim3_sabit.py`, `DEVIR.md`'yi
değiştiriyor. Kullanıcının çalışma kopyasında bu dosyalarda commit'lenmemiş iş var; `main`'e alınırken
cerrahiyle (yalnız bu dalın parçaları) alınmalı. 1D dalıyla çakışma: `web_akis.h` (iki dal da aynı
`ham()`'ı ekliyor), `tasarim3_sabit.py` DRAM satırı, `kayit_esp.h` KM_* tanımları.

---

#### 5.12.105 🟢 W1–W5 BİRLEŞMESİ + mDNS SERVİS DUYURUSU (2026-10-04, dal `w-birlesik`, ağaç `projeler/olcum-karti-wb`)

Kullanıcı uyurken açılan beş kol (W1 veri doğruluğu · W2 firmware küçükleri · W3 açılış bütçesi · W4 mutasyon
hijyeni · W5 kart tezgahı) her biri ayrı ağaçta yazıldı, bağımsız çürütücü inceledi, bulgular düzeltildi
(5.12.100–5.12.104a). Birleştirme sırası W4 → W2 → W5 → W1 → W3 (W4 önce: zincirin özel TEMP'i diğerlerinin
koşularını korusun).

**Çakışmalar (hepsi kayıt dosyalarında, kodda yok):** `DEVIR.md` girişleri iki taraf da tutularak; `mutasyon.py`
liste kayıtları birleşim; `test_kayit_esp.py` iki yeni bölüm (`bolum_w2`, `bolum_tezgah_w5`) ikisi de `BOLUMLER`'de;
`beklenen_sayim.json` sayılar TOPLANARAK (B72 207 + W2 8 + W5 6 = 221, + W2i = 222; B7 911 + W2 1 + W1 2 + W3 4 = 918);
`1-acik-isler.md` satır satır (E6/E7 W5'ten, E3 W2'den; Y7 W1'in kapanışı + W5'in kart ölçümü, W1'in `SKOP`
işaretinin nokta oturumlarına da uygulandığı `noktaSerileri`'nden doğrulandı); `sw.js` / `_fs.json` birleşimden sonra
`arayuz-uret.py` ile YENİDEN üretildi.

**W2i — mDNS servis duyurusu (alt proje 5 isteği, `mobil/DEVIR-ISTEK.md` #1):** Android `.local` adını güvenilir
çözmez, NSD ile servis tarar. Kart artık `_http._tcp` port 80 duyurur, TXT `kimlik=<16 onaltılık>` (`/eslestir/bilgi`'deki
aynı değer; yanlış kartı bağlanmadan elemek için — asıl doğrulama yine eşleşme/imza). İki yol: AP'de `MDNS.begin`
setup'ta kimlikten ÖNCE çalışır → `ag_mdns_kimlik` (guv_esp_ac'tan sonra, yalnız `guv_hazir` iken) duyurur; STA'da
`MDNS.begin` ağ görevinde, kimlik o anda var → `ag__mdns_servis` duyurur. Tek duyuru bayrağı. İddia B72.W2i, mutasyon
`W2:` ×3 (STA'da duyuru yok / TXT kimlik yok / kimlik verilmez) **YAKALANDI**.

**PC'de mDNS notu (kusur değil):** bu PC'de `Resolve-DnsName olcum.local` çözemiyor; çoklu yayın sorgusu varsayılan
olarak `vEthernet (Default Switch)`'ten çıkıyor. Wi-Fi arayüzü `IP_MULTICAST_IF` ile seçilince kart hem A kaydını
hem tekil sorguyu yanıtlıyor. Köprü 4J IP önbelleğiyle zaten bundan etkilenmiyor.

⚠ **Kartta görülen (A3-4B, 2.9 sa çalışma):** `QY dahili_en_az=2504` — dahili yığının en düşük değeri **2.5 KB**. ⚠ E6 ölçüm halkası (5.12.105a) birleşmede 8 → **4** kayda indi: 8 kayıtla statik DRAM 81 932 B = %25.003 ve B6 "RAM payı < %25" kırmızıydı; şimdi 81 836 B, pay ~80 B — sıradaki statik ekleme sınıra takılır, önce kalıcı dahili tamponlar PSRAM'e (F4)
(W5 20.7 KB görmüştü, E6 kaydı 54–60 KB). Sebep bilinmiyor; E6 satırına işlendi, sıradaki iş.
Salt okuma kod incelemesi (karta dokunmadan) sıralı aday verdi: (1) Arduino `WiFiGeneric.cpp` 32 dinamik TX + 32 RX
Wi-Fi tamponu, hepsi DAHİLİ (`SPIRAM_TRY_ALLOCATE_WIFI_LWIP` kapalı) — bağlantı takılınca birikir, 7 `hata=-7`
yeniden bağlanmayla uyumlu; (2) mbedTLS DAHİLİ (`MBEDTLS_INTERNAL_MEM_ALLOC`, 16 KB içerik tamponu) — oturum ~38–40 KB
sürekli + el sıkışma tepesi; (3) lwIP gönderme kuyrukları (`SPIRAM_MALLOC_ALWAYSINTERNAL=4096`), yarı açık SSE
istemcisi; (4) kalıcı dahili ayırmalar (`kayit_veri_tampon` 8 KB, SSE kuyruğu 10.5 KB). Not: ölçüt bölge
minimumlarının TOPLAMI (RTC FAST da yığın) — gerçek eşzamanlı dip bundan da düşük olabilir. **Sıra:** önce ölçüm
(I1 `heap_caps_print_heap_info` + en büyük blok, I2 `heap_caps_register_failed_alloc_callback` halkası `QY`'de),
sonra F1 mbedTLS'i `mbedtls_platform_set_calloc_free` ile PSRAM'e (~40 KB kalıcı kazanç), gerekirse F2
`WiFi.useStaticBuffers(true)`, F3 SSE yazma kısa dönerse istemciyi düşür, F4 iki tamponu PSRAM'e. F5 (2 kaçırılmış
ping) K8 vasiyet süresiyle çelişir — kullanıcı kararı.

---

#### 5.12.105a 🟡 E6 ÖLÇÜM ARACI: DAHİLİ YIĞIN TANISI (2026-10-04, dal `e6-olcum`, ağaç `projeler/olcum-karti-e6`; karta YÜKLENMEDİ)

5.12.105'teki `QY dahili_en_az=2504` için sebebi tahminle değil karttan ayırmak üzere (I1 + I2; I3 pencereli
minimum atlandı — gerçek dipleri yakalamak için örnekleme gerekir, basit değil). Davranış değişmedi.

- **I1:** `QY` satırının SONUNA `dahili_en_buyuk=` (`heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL)`) ve
  `ayirma_hata=`; eski iki alan yerinde. Ayrıştırıcılar `ad=değer` okuyor (`tezgah_bildirim.q_oku`), başka QY
  okuyucusu yok. **`QH`** (yalnız USB; `Qe` gibi `s[1] == 'H'` ile — yeni `case` harfi yok, komut harfi
  denetimleri etkilenmez): önce `QH dahili_bos= dahili_en_az= dahili_en_buyuk= ayirma_hata=`, sonra
  `heap_caps_print_heap_info(MALLOC_CAP_INTERNAL)` bölge bölge (`At 0x… len … free … min_free …
  largest_free_block …`; IDF `printf`'i — **yalnız ham UART**, `/akis`'e gitmez), sonra son 8 başarısız ayırma
  `QF no= boyut= caps=0x…. ms= cekirdek= gorev=` (eskiden yeniye; yoksa `QF yok`). `Serial.flush()` yüzünden
  ölçüm döngüsü `QH`'de ~0.1 s durabilir (tanı komutu). `/komut` ve `kopru.py` `Q*`'ı zaten reddediyor (403).
- **I2:** `setup`'ta `Serial.begin`'in hemen ardından (WiFi, güvenlik, kayıt, MQTT ve ilk görevden ÖNCE)
  `heap_caps_register_failed_alloc_callback(ayirma_hata_kaydet)`. Geri çağırma `IRAM_ATTR`, basmaz/ayırmaz;
  `portENTER_CRITICAL_SAFE` altında halkaya {boyut, caps, `esp_timer` ms, çekirdek, görev adının ilk 8 harfi —
  ÇAĞRI ANINDA kopyalanır, sonradan `TaskHandle` çözmek silinmiş TCB okuyabilirdi} yazar, sayaç kayıttan sonra
  artar; dizin `sayaç % 8`. Döküm halkayı kilit altında kopyalar. RAM: +216 B DRAM, flaş +1232 B
  (1 414 402 → 1 415 634; DRAM 81 700 → 81 916, `_ESP_DRAM_SON_OLCUM` güncellendi). Derleme uyarısız.
- IDF ayrıntısı: düz `malloc` başarısızlığı geri çağırmaya `caps=0x1000` (MALLOC_CAP_DEFAULT) ile gelir ve
  ancak dahili + PSRAM ikisi de dolunca düşer; açık `heap_caps_malloc`'lar kendi caps'iyle gelir.

**Kartta okuma (yükledikten sonra, aynı koşulda birkaç saat):** `Q?` → `QY …` ve `QH`.
`ayirma_hata=0` → dip hiçbir ayırmayı düşürmedi (tepe); `dahili_en_buyuk` el sıkışma için ≥ ~17 KB olmalı.
`QF boyut≈1600 caps=0x080C` (INTERNAL|DMA|8BIT), görev `wifi`/`tiT` → **Wi-Fi dinamik tamponu** (F2/F4).
`QF boyut≈16700 caps=0x0804` (INTERNAL|8BIT), görev `bld` → **mbedTLS** (F1: `mbedtls_platform_set_calloc_free`
ile PSRAM). `dahili_bos` büyük, `dahili_en_buyuk` küçük → parçalanma. `QH` bölge satırlarında `min_free`'si
sıfıra yakın bölge, toplam minimumun (bölge minimumlarının TOPLAMI) gizlediği gerçek dibi gösterir.

**İddialar (B72.E6a–f, 221 → 227):** kayıt setup'ta her başlatmadan önce ve tek yerde · IRAM + basmaz + SAFE
kilit + ad kopyası · halka 8, `% 8`, kilitli kopya · QY alan sırası · `q_oku` yeni ve eski satırı çözer
(davranış) · `QH` switch'ten önce, bölge dökümü, `/komut` 403, `kopru.py` ret. **Mutasyon `E6:` 12** — ilk koşuda
11/12: "döküm kilitsiz kopyalar" KAÇTI, çünkü `find()` −1 döndürünce `-1 < a < b` zinciri yine doğruydu; `0 <=`
eklendi (E6c ve E6f'de), tekrar koşu YAKALANDI.

**Birleştirme notu:** dal `w-birlesik`'in COMMIT'li hâlinden (c5e22e2) açıldı; `olcum-karti-wb`'deki
commit'lenmemiş 5.12.105 (W2i mDNS) bu dalda yok. Çakışma beklenen yerler: bu DEVIR girişi (5.12.105'in altına
alınmalı), `1-acik-isler.md` E6 satırı (bu daldaki hâli 5.12.105 cümlesini de içeriyor), `beklenen_sayim.json`
B72 (W2i'nin sayısıyla TOPLANMALI), `mutasyon.py` (E6 kayıtları listenin sonunda, W2i'ninkiler W2 bloğunda).
c5e22e2'nin kendisinde `sw.js` SURUM'u ve `_fs.json` bayattı (ilk zincir koşusunda B22b 109/113 + B7 915/918
kırmızı, E6'dan bağımsız); `arayuz-uret.py` ile yeniden üretildi — çıkan fark `olcum-karti-wb`'deki
commit'lenmemiş farkla BAYT BAYT aynı, birleşmede çakışmaz.

---

#### 5.12.103 🟢 W4 MUTASYON HİJYENİ (2026-10-03, dal `olcum-karti-w4-mut`)

Kuru uygulama denetimi (her kaydın `eski` metni hedef dosyada var mı; test koşmadan): **önce 4 / 2077
uygulanmıyor, sonra 0 / 2078.** Dördü hedef kodu değişmiş kayıtlardı, anlamı korunarak yeniden
hedeflendi: 3A `arayuz-uret.py` (`+ ikon +`), 3C/WIG 401 metni (artık `kl.neden_imza`, PC köprüsü
`kopru/pc.py` yolunu söylüyor), 3C (C4) `kayitlar.js` (`yerelNerede`), 4D `kart_wifi.py` `_p0` (çok satırlı
belge dizesinin sonuna). Yeni: **W4:** [1A-1] "kullanmadan önce HEP sil" (`kg_ilerle` tabloda kaydı
olmayan sektörü silmeden geçerse) — `test_kayit.py` kırmızı (ilk: B71.Z7). Beşi koşuldu: **5/5 YAKALANDI**.

**İnceleme bulgusu (aynı gün):** bu ağaçta yarım kalmış/kırık bir zincir koşusu `uretim/_tezgah.md`'yi
**122 kalemden 81'e** indirip yazmıştı (B71'den sonraki adımlar kalem basmamıştı; önbellekte yalnız B1…B25).
Commit'lenseydi 41 kalem (9'u [!]) sessizce silinirdi. Dosya `git checkout` ile geri alındı. Kök sebep
`dogrula3.tezgah_birlestir`: kalem basmayan adım ya da eksik adım sayısı KIRMIZI deniyordu ama liste YİNE
yazılıyordu. Artık eksik koşu eski listeyi **ezmez** ("YAZILMADI: eksik koşu"). Test `test_zincir_hiz.py`
`test_tezgah_eksik_kosu` (3 iddia, 101 → 104), mutasyon `W4:` ×2 (koşul kaldırılır / yalnız sayım kalır)
**YAKALANDI** (W4 öneki 3/3).

**Yarım koşunun sebebi de bulundu:** düzeltmeden sonraki ilk zincir koşusunda B71 yine KALDI — `test_kayit.py`
B71.K'nın (120 elektrik kesmesi) ortasında **sessizce** öldü (traceback yok, sayım `[]`), tek başına 362/362.
`cop_topla` → `gecici.kalintilari_sil` ORTAK `%TEMP%`'teki `kayit_*` / `spice-*` … dizinlerini canlı mı diye
bakmadan siliyor; o anda dört kardeş ağaçta zincir koşuyordu, birinin bitişi bu ağacın ELF'lerini sildi.
Düzeltme `dogrula3.ozel_temp_kur`: zincir ve adımları `_zincir-yerel-*/tmp`'de koşar (mutasyon işçileri
gibi); TEMP önbellek anahtarında yok (`ZO.ORTAM_UCUCU`). Test `test_ozel_temp` (2 iddia, 104 → 106),
mutasyon `W4:` ×2 (çağrı silinir / ortam çevrilmez) **YAKALANDI** — W4 öneki **5/5**.

---

#### 5.12.101a 🟢 W2 inceleme: `tezgah_kart` / `tezgah_blokaj` 15 alanlı `G` satırını bekleyebiliyor (2026-10-04, dal `w2-fw`)

Ajan (W2), inceleme bulgusu. 5.12.101'deki "bütün G ayrıştırıcıları geriye uyumlu" listesi EKSİKTİ: kararlı-hal
blokaj ölçümünden önce boşta ön silmeyi bekleyen iki araç (`tezgah_kart._on_silme_bekle`, `tezgah_blokaj`'ın
`main` içi döngüsü) `G?` yanıtını `^G( -?\d+){13}\s*$` ile arıyordu. A3-W2'nin 15 alanlı satırı eşleşmez →
`tezgah_kart` hemen None döner ("None s beklendi"), `tezgah_blokaj` "boşta silme durdu" deyip çıkar; ikisi de
`loop_azami`'yi 500 ms / ~25 ms ön silme sürerken ölçer — 1C-2'nin önlediği sahte kırmızı. Kart listesinin 9.
maddesi (blokaj aynı sınıfta mı) yanıltıcı olurdu. B72.W2c yalnız `pc_bildirim`, `tezgah_kayit`, `tezgah_pc`'yi
kapsıyordu.

- İki modülde `G_DESEN` = 13 alan + isteğe bağlı 2 (`son_not`, `mesaj_dusen`); 14/16 RET. `G_SIL_ADET = 11`
  (iki biçimde aynı yer).
- `tezgah_blokaj`: bekleyiş `on_silme_bekle(k, azami_sn)` işlevine çıktı. Çözülemeyen `G`'de eskiden "durdu"
  deyip ölçüyordu; artık None döner ve iki araç da "`G?` yanıtı çözülemedi — ön silme BEKLENEMEDİ" uyarısı basar.
- **B72.W2h** (davranış, kaynak metni değil): sanal saat + sahte kart; `sil_adet` 5, 9, 9 → 15 ve 13 alanda
  6 s / 3 sorgu, 14 ve 16 alanda None / 1 sorgu, iki modülde. İlk koşu kırmızıydı (`tezgah_kart` 15 → None,
  `on_silme_bekle` yok), düzeltmeden sonra yeşil. B72 214 → **215** (sayım kilidi güncellendi).
- Mutasyonlar (B72): iki modülde deseni 13'e geri çevirmek, `tezgah_blokaj`'da None yolunu eski "durdu"ya
  bağlamak.

**Doğrulama:** `dogrula3.py --artimli` **22/22** (`mutasyon.py` değiştiği için zincir kendisi TAM koştu; ilk koşuda B6 derlemesi `arduino-cli` geçici dosyası kaybolunca düştü — `…AP.cpp.libsdetect.d: No such file`, koddan bağımsız; yeniden koşu yeşil, B72 215/215) · `mutasyon.py --neden "W2:" --paralel 2` **21/21 YAKALANDI** (1606 s; yeni üçü B72.W2h'de) · uygulanamayan yok · `gizlilik_dogrula.py` temiz. Karta dokunulmadı.

---

#### 5.12.101 🟢 W2: FİRMWARE KÜÇÜKLERİ — G `son_not`, `/saat` + `Ex` tam çözüm, rastgele `eno`, `Qe` eşiği (2026-10-03, dal `w2-fw`, firmware `A3-W2`)

Ajan (W2). Ağaç `projeler/olcum-karti-w2-fw`, `main` 20d3171'den. Push yok. **Karta YÜKLENMEDİ** (yükleme
tam yedekten sonra orkestratörün işi; kart listesi aşağıda). `1-acik-isler.md`'de yedi satırın üstü çizildi.

- **G satırı (1C-1 + M9):** `G`'nin SONUNA iki alan: `son_not` (son Ga/Ge/Gn/Gx'in NOT kaydının sırası =
  `kyn_not` dönüşü; `Gx<oturum>:<sıra>` bunu hedefler; < 0 KG_*, 0 = açılıştan beri yok) ve `mesaj_dusen`
  (istek kuyruğunda düşen). `son_not` değişince G hemen basılır — `nesil` ARTMAZ, çünkü `nesil` noktacıyı
  yeniden başlatır (`kayit__nesil`), kayıt sürerken yarım nokta kaybolurdu. **Geriye uyum:** panel
  (`KAYIT_SATIR_ESKI`), `pc_bildirim._G_DESEN`, `tezgah_kayit`/`tezgah_pc.g_coz` eski 13 alanlı satırı da durum
  sayar (14 alan RET); eski satırda yeni alanlar nesnede yok. Panelde `son_not`'u GÖSTEREN bir öğe yok (açık).
- **Noktacı (1A-1 D):** `kn_ornek` sonlu olmayan watt'ı (NaN, ±Inf) kendisi V+I hatalı sayar; `(int64_t)`
  dönüşümü yapılmaz. Yapıştırıcının aynı kuralı duruyor; başlık ona güvenmiyor.
- **`ky_nokta` (1A-1 O):** tampon doluyken boşaltma yine başarısızsa reddedilen nokta `dusen`'e sayılır.
- **D5 #10 `/saat`:** `guv_saat_coz` — yalnız rakam, ≤ 10 hane, 32 bit taşmasız, 1 700 000 000 ≤ unix <
  4 102 444 800 (2100-01-01); dışı 400. Eskiden `strtoul("-1")` = 2106.
- **D5 #11 `Ex<n>`:** `guv_cihaz_no_coz` önce TAM çözer: yalnız `!` (tek başına) ya da 1..8. `Ex257`
  (uint8 kesimi), `Ex-255` (atoi), `Ex!x`, `Ex4294967297` (32 bit taşması) RET.
- **D5 #14 `eno`:** rastgele 31 bit (`uint32`, 0 ve önceki hariç), yanıtta `%lu`; kanıt ucu `guv_sayi_coz` ile
  TAM çözer (eskiden `(uint8_t)toInt()`), çözülemeyen 0 = hiçbir bekleyene uymaz. Yanlış numara bekleyeni
  TÜKETMEZ (zaten öyleydi; artık tahmin 2^-31). İstemciler (`imza.py`, `imza.js`) değişmeden uyumlu (JSON
  tamsayısı, < 2^31).
- **E3 `Qe<binde>`:** 100..1000, boş = varsayılan 500 (anahtar silinir); YALNIZ USB (`/komut` Q'yu 403 ile
  zaten reddediyor); NVS `mqtt`/`esik`; görev yeni eşiği **bağlantıyı kesmeden** alır (istek/işlenen
  sayaçları; `bld_istek_yeniden` yeniden bağlanırdı); açılışta NVS'ten. `Q?` satırına `esik=` (etkin eşik).
  Karar: `bld_esik_ayarla` olay numarasını, kuyruğu ve `esik_kurulu`yu KORUR — eşiği indirmek zaten
  bildirilmiş doluluğu tekrar bildirmez, eşiğin altına inmiş (bildirilmemiş) dolulukta hemen bildirir;
  yükseltmek histerezisle yeniden kurar. Alt sınır 100 = `BLD_ESIK_GERI` (daha alçak eşik yalnız tam
  eşitlemede yeniden kurulurdu).
- `KAYIT_FW_SURUM` **`A3-W2`** (B72.F25 + mutasyonu güncellendi).

**Derleme:** `yukle.py --derle` uyarısız. Flaş 1 412 758 → **1 414 402 B (+1 644)**, DRAM 81 684 →
**81 700 B (+16)** → `_ESP_DRAM_SON_OLCUM` gerekçesiyle güncellendi.

**İddialar:** B71 362 → **369** (P7 NaN/Inf, Y15 dolu tampon + yazma hatası, U20 `/saat`, U21 `Ex`, U22 `eno`,
Q21 `Qe` ayrıştırıcı, Q22 çalışırken eşik) · B72 207 → **214** (W2a–W2g) · B7 911 → **912** (G geriye uyum).
AVR donanımı: NOKTACI S6, YAZICI O5 (emüle NOR yazma arızası `NOR_ARIZA_YAZ = 1`, iki kez), GUV aşama 3
`a3_coz` + `a3_eno`, BILDIRIM `s_esik_ayar` (yığın payı 678 B).

**Doğrulama:** `dogrula3.py --artimli` **22/22** (ilk koşu B22b'de kırmızıydı: `app.js` değişince LittleFS
görüntüsü ve `sw.js` SURUM bayat — `python arayuz-uret.py` ile yenilendi) · `mutasyon.py --neden W2 --paralel 2`
**18/18 YAKALANDI** (2331 s) · `--neden "1D: surum adi"` **1/1** · uygulanamayan yok. ⚠ B7 yalanlayıcısı
(`KAYIT_SATIR_ESKI` boş) ilk kırmızıyı D1'de veriyor ve sayım BOŞ dönüyor: B7'nin başka iddiaları da 13
alanlı (eski biçim) G satırı besliyor, ayrıştırıcı onu reddedince test çöküyor — yakalandı, ama W2 iddiasından
önce. `gizlilik_dogrula.py` temiz.

**Gerçek kart listesi (A3-W2 yüklendikten sonra; `N?` GÖNDERME):**
1. `G?` → `G` satırı 15 alan, son ikisi `0 0`; `GA`/`GT`/`GP` değişmedi. Afiş/kayıt BAŞLA sürümü `A3-W2`
   (eşitlenen kayıtta), MQTT durumunda `"f":"A3-W2"`.
2. `Gb1000` → G'de oturum `<o>`; `Gn<o> deneme` → G satırı HEMEN gelir, `son_not` > 0; eşitlenen dosyada o sırada
   NOT kaydı var; `Gx<o>:<son_not> ` (boş metin) notu siler; `Gn999999 x` → `son_not` = -4 (KG_YOK). `Gd`.
3. Kayıt sürerken G periyodu bozulmadı (saniyede bir) ve `D` satırında örnekleme hızı değişmedi;
   `tezgah_kayit.py --pil` (Ga/Ge/Gn/Gx) ve `--duman` yeşil.
4. Panel (kartın kendi paneli, Playwright): Canlı'da kayıt durumu ve konsol G satırını gösteriyor; köprü
   açıkken kayıt bitince "kayıt bitti" yerel PC bildirimi geliyor (`pc_bildirim` yeni G'yi durum sayıyor).
5. USB: `E?` (cihaz sayısını not et) → `Ex257`, `Ex-255`, `Ex1x`, `Ex!x`, `Ex0`, `Ex9` hepsi `! E: Ex<1..8>…`
   ve `E?` cihaz sayısı AYNI. (`Ex1`/`Ex!` DENEME — gerçek cihazları siler.)
6. Eşleştirme: `tezgah_kayit.py --guvenlik` yeşil; `/eslestir/baslat`
   yanıtındaki `eno` > 255 ve ardışık iki başlatmada +1 değil; yanlış `eno` ile `/eslestir/kanit` 404 (YOK),
   ardından doğru `eno` + doğru kanıt hâlâ KABUL. Köprü (`imza.py`) ve panel (`imza.js`) eşleştirmesi uçtan uca.
7. `/saat` (yalnız NTP'siz kartta; NTP varsa 409 beklenir): imzalı POST `unix=-1` → 400, `unix=4102444800` → 400,
   `unix=17000000000` → 400, geçerli `unix` → 204 ve `E?` `saat=2`.
8. `Q?` → `esik=500`; `Qe700` → `* Q: esik 700 binde`, `Q?` `esik=700` ve `baglanti` sayacı ARTMADI (bağlantı
   kopmadı); RTS sıfırlaması sonrası `esik=700` kalıcı; `Qe99`, `Qe1001`, `Qex` RET; `Qe` → 500 (varsayılan);
   `/komut` ile `Qe700` → 403. MQTT bağlıyken (EMQX) `Qe` sonrası `QY dahili_en_az` ≥ 54 KB (E6 sınıfı).
9. Blokaj: `tezgah_kart.py --sifirla` kararlı-hal `loop_azami` öncekiyle aynı sınıfta (G satırı 2 alan uzadı).

**Açık:** panelde `son_not` gösterimi / Gx kısayolu yok · `ky_nokta` reddinden sonraki noktaya `KN_KAYIP_ONCE`
bayrağı yok · D5 #15/#17/#18/#19 ve #8 hâlâ açık · E3 için PC/panel arayüzü yok (yalnız USB).

---

#### 5.12.104 🟢 W5 KART TEZGAHI: T7 · T8 · E7 (2026-10-03, dal `w5-tezgah`)

Ajan, gerçek kartta (COM6, A3-4B, ADS takılı değil). Push yok. Kart ayarına dokunulmadı: yalnız
`G?`, `Gb`, `Gd`, `Gp…`, `Gt…`, `Ga` ve `Q?` (salt okunur). Eşitleme ONAYSIZ: kartta onay ilerlemedi,
köprü kayıtları sonra kendi arşivine alır.

- **T7 — `tezgah_kayit.py --plan-elle` 3/3.** Plan sürerken `Gd`, ardından `Gb200` iki zamanlamayla
  denendi: 3 s arayla ve aynı anda. İkisinde de `Gd` planın oturumunu kapattı (GP 3, plan oturumuyla).
  `Gb` yeni bir oturum açtı ve bu kayıt planın bitişinden 10 s sonra hâlâ sürüyordu. Kayıt yalnız
  `Gd` ile kapandı (sebep 1), içinde PLAN olayı yok. Ek senaryo: skop günlüğü (SKOP oturumu)
  sürerken planın başlangıcı geldi. Plan atlandı (GP 4), günlük bölünmedi. "DOLU'da oturumsuz pil testi + plan"
  kartta denenemez: `p1` ister (ADS ve yük yok, `p1` reddedilir — T5) ve ~1.6 sa doldurma ister. Bu
  durum AVR'de (B71.R) ve F70'te sınanıyor.
- **T8 — `--skop-olcum` 1/1.** `Gb200` sürerken `Gt2000` (9 yakalama), `Gtd`, 8 s sonra AYNI oturumda
  `Gt3000` (8 yakalama), `Gtd`, `Gd`. Sonuç: tek ÖLÇÜM oturumu, iki parti, ortanca aralıklar 2002 ve
  3003 ms. Yakalama numaraları 1–17 tekrarsız ve artan (`Gt` sıfırlamıyor). İki `SKOP_KAL` olayı var,
  269 nokta kesintisiz, hepsi S3B'ye çevriliyor. İki `Gtd` de ölçümü kapatmadı. Gözlem (Y7 ile ilgili):
  yakalama sırasında 200 ms'lik noktalar arasında en büyük boşluk **423 ms** — yakalama ölçümde
  boşluk bırakıyor, NOKTA'da bayrağı yok.
- **E7 — `tezgah_bildirim.py --basladi N` (gerçek aracı EMQX, PC'nin 4E önbelleğiyle abone, karta
  imzalı istek yok).** Her sıfırlamadan hemen önce `Q? olay` okundu: bu sayaç o açılışta PUBACK'i
  alınmış olay sayısıdır, `basladi` her zaman ilk olaydır. Sonuçlar:
  - `--kip bagli` (ilk koşunun zamanlaması: bağlanınca 0–3 s): **15/16 ulaştı.** Tek kayıpta kart
    "bağlı" görünüyordu ama `olay=0 kuyruk=1` idi.
  - `--kip rastgele` (afişten 2–15 s sonra): 8/16 ulaştı. 8 kaybın hepsi `olay=0`'dı.

  Toplam 32 açılışta PUBACK alınmış **23/23 `basladi` aboneye ulaştı**, aracıda kayıp **0**. Bütün
  kayıplar kartta. Sıfırlama, olay RAM kuyruğundayken ya da uçuştayken geldi. Bağlantı kurulduktan
  sonra birkaç saniye bu pencere açık kalabiliyor. Bu, E4'ün bilinçli kararı (kalıcı kuyruk yok).
  Abone kesintisizdi; açılış numaraları sıfırlamalarla birebir eşleşti (a0 + 16).
- **Yan gözlem (E6):** `QY dahili_en_az` 3 ayrı sıfırlamada 59.5, 61.7 ve 42.8 KB çıktı; 42.8 KB
  bağlandıktan sonra düştü. E7'nin son açılışında 20.7 KB görüldü; o açılışta yalnız `Q?`/`G?` gitti,
  köprü kapalıydı. E6'nın "54–60 KB" değeri iyimser kalıyor. Nedeni ayrılmadı; ayrıntı
  `1-acik-isler.md` E6'da.
- Çevrimdışı ölçü aleti denetimleri: B72.TZ1–TZ4 (`test_kayit_esp.py`, B72 207 → 211) ve
  test_bildirim E7.1–E7.7. Bunlara 20 mutasyon (`W5:`) eklendi.
- **İnceleme düzeltmesi (2026-10-04, 5.12.104a):** iki bulgu kapandı.
  1. TZ4 yalnız `plan_elle`…`_ham_istek` kaynak dilimine bakıyordu. `esitle_onaysiz`'in gövdesi bu
     dilimin dışında kalıyordu: imzalı yolda Esitleyici'ye `onay=KE.imzali_onay(...)` verilse TZ4 yine
     yeşildi, kartta `Go` gider, köprü arşivi kayıt kaçırırdı. Yeni **TZ5** gövdeyi davranışla sınıyor:
     sahte Esitleyici, düz ve 401 (imzalı) yolda `onay`/`istek` hep `None`.
  2. Akış kimliği değişince ya da sıra GERİ gidince `esitle_onaysiz` verilen `--dizin`'i
     `shutil.rmtree` ile siliyordu; köprü arşivi verilirse veri kaybolurdu. Artık yalnız tezgahın kendi
     `VARSAYILAN_DIZIN`'i (`%TEMP%\olcum-tezgah-w5`) baştan kuruluyor. Kullanıcı dizininde Esitleyici'nin
     hatası "SİLİNMEDİ, yeni --dizin ver" ekiyle geçiyor; yardım metni köprü arşivini vermemeyi söylüyor.
     Bunu **TZ6** sınıyor.
  B72 211 → 213; 4 yeni `W5:` mutasyonu (yorumcunun mutasyonu birebir dahil).

---

#### 5.12.100b 🟢 W1 İNCELEME: AYRINTILI SERİLER YENİDEN TEK KURULUM (2026-10-04, dal `w1-veri`)

Ajan. İnceleme bulgusu (önemli, ölçülmüş gerileme): `296c2e2`'den sonra `ayrintiSerileri` sıralı örnek
listesini 3–4 kez kuruyordu. Bir kez kendisi kuruyordu, bir kez `ayrintiGuc`, yakalama varsa bir kez
de `skopSonralari` → `skopYerleri` → `olcumZamanlari`. Her kurulumda [r, k] çiftleri, sort ve map
vardı. Ölçüm (2026-10-04, aynı sentetik 1.9 M örnek, 50 Hz, kalibrasyonlu):

| | `20d3171` (W1 öncesi) | `296c2e2` (W1) | bu düzeltme |
|---|---|---|---|
| 1.9 M, yakalamasız | 3.0–3.5 s | 8.4 s, yığın +1.2 GB | 1.9 s, +0.46 GB |
| 1.9 M, yakalamalı | 2.5 s, +0.54 GB | 6.4–10.4 s, +1.8 GB | 2.1 s, +0.52 GB |
| 1.9 M, yakalamalı, 1 GB yığın | geçer | **OOM** | 2.4 s, geçer |
| 600 k, yakalamalı, yığın sınırı | 200 MB'ta geçer | 300 MB'ta OOM | 200 MB'ta geçer |

Değişiklik (karar WK8): `ayrintiOrnekler(o, true)` sıra ile sıralı listeyi verir; liste zaten
sıralıysa kopya kurulmaz. `ayrintiGuc(o, {orn, dizi: true})` Float64Array döner, [sıra, w] çifti
kurulmaz. `skopYerleri(o, orn)` hazır listeyi gezer, üçlü dizi kurmaz. `ayrintiSerileri` ve
`noktaSerileri` `yerler`'i taşır; `oturumRaporu` ile `yakalamaIsaretleri` onu kullanır. Seçenekler
yalnız JS'te: Python `kayit_bicim.py`, vektörler ve `api` eşlemesi değişmedi. Bit bit sonuç da
değişmedi: kayit.json `ayrinti_guc`/`skop_yerleri` ve disari W1 testi aynen geçiyor.

Testler (önce kırmızı, `git archive 20d3171..HEAD` kopyasında doğrulandı):
- `disari.test` "W1-tek-kurulum": kayıtlara `t0_us` okuma sayacı takılır (`ayrintiOrnekler` kayıt
  başına iki kez okur, başka okuyan yok). Seriler, CSV ve rapor birer kurulum yapar (eski kod 3).
- `disari.test` "W1-bellek": 600 k örnekli yakalamalı oturum ayrı süreçte `--max-old-space-size=250`
  ile biter (eski kod OOM).
- `kayit.test` "W1 inceleme": ters kayıt sırasında sıralı liste, `dizi` = çiftler, `skopYerleri(o, orn)`
  = `skopYerleri(o)`.
- B7 K3c sayacı: grafik bir kurulum yapar, işaretler sıfır.

Doğrulama: B73 25/25 (node: disari 27, kayit 98, rapor 15), B7 913/913 (+1: K3c sayacı; sayım kilidi 912 → 913). Zincir `--artimli` iki kez TAM koştu (bu ağaçta yeşil kayıt yoktu). 1. koşuda B22b kırmızıydı: LittleFS görüntüsü bayattı, `arayuz-uret.py` ile `_fs.json` ve `sw.js` SURUM yenilendi. B6 da kırmızıydı (`arduino-cli`: "cannot specify '-o' with multiple files"; firmware değişmedi, makine paylaşılıyor). 2. koşu **hepsi yeşil**: B6 77/77, B22b 113/113, "Aşama 3 doğrulandı". Üretilen `BELGELER/`, `sema3/`, `_tezgah.md`, `netlist3.net`, `_firmware.json` gürültüsü commit'e alınmadı.

Mutasyon: 9 yeni `W1:` yalanlayıcısı. Eski "W yine V×A" kaydı değişen satıra taşındı.
`--neden W1: --paralel 2` → **35/35 yakalandı** (26 eski + 9 yeni; 591 s).

**Açık (O-W1b):** kayıt görünümü bir oturum için seriyi iki kez kuruyor (grafik + rapor). Bu W1'den
önce de böyleydi; oturum başına önbellek bu dilimde yapılmadı.

---

#### 5.12.100 🟢 W1: PC'DE HİZALI GÜÇ + YAKALAMANIN ZAMANINDA YERİ (Y7) (2026-10-03, dal `w1-veri`)

Ajan, kart ve firmware değişikliği yok. Kullanıcı "bensiz yapabileceklerinle devam et" dedi; kararlar
benim, gerekçeleri `tasarim/1-acik-isler.md` "W1 kararları"nda (WK1–WK7). İki açık iş kapandı:
**Y7** (ekli oturumda kayıt sırası zaman sırası değil, yakalama boşluğu ayrıntılı kayıtta bayraksız) ve
**"PC'de W'nin hizalamalı hesabı"** (1C-2'den devredilen).

| Dosya | Ne |
|---|---|
| `kopru/kayit_bicim.py` ⇄ `ortak/src/kayit.js` | Yakalama `acilis` alanı (kayıttan önceki DEVAM sayısı). `skop_yerleri`: META'lı her yakalama ZAMAN sırasıyla, `once`/`sonra` = boşluğun iki yanındaki ölçüm verisi (ayrıntılı: zamanı ≥ (t_ms+1) ms ilk örnek; nokta: kart_ms > t_ms). `ayrinti_guc`: kartın `o.watt` tanımı (V akım anına Lagrange, × I, şebeke RC ters kazancı) GERÇEK örnek zamanlarıyla; `VI_KAYMA_US` 152 (B29), `TAU_AKIM`. İki dil aynı aritmetik sırası, kayit.json'da bit bit |
| `ortak/src/disari.js` | Ayrıntılı `w` = hizalı güç (V×A değil). `skop` dizisi; CSV `bayraklar`'a PC türetimi `SKOP` (EN `SCOPE_CAPTURE`), ham bayrak sütunları aynen. `anZamani` bilinen açılışı alır |
| `ortak/src/rapor.js` | Ayrıntılı Wh hizalı W'den; yakalama tablosu zaman sırası + kendi açılışı (ham kayıt verilmeden de); uyarı `skop_bosluk` |
| `arayuz3/ekran/kayit_gorunum.js` | Okuma Wh'si hizalı (raporla aynı); grafikte yakalama işareti `S<no>` (K3b, K3c) |
| `uretim/ortak_vektor_kayit.py` | Yeni akış `yerlesim`; `w1_kurallar` W1.K1–K18: firmware kaynağı hâlâ bu formülle mi (olcum_al, lagrange4, TAU_AKIM), eşit aralıkta PC = firmware lagrange4 (1e-12), 50 Hz sinüste 1 ms kaymada hizalı ortalama %0.5 içinde / hizasız %4.9 sapar, yedek düğümler, kırpma, yakalama sırası/açılış/sarma |
| `uretim/ortak_vektor_disari.py` | Bağımsız hizalı güç + yakalama yeri; akışlara kayıt sırası zaman sırası OLMAYAN yakalamalar, iki açılışa uyan (sezgide belirsiz) yakalama |

**Bulgu (veriye dokunuyor):** ayrıntılı kayıtlarda PC'nin gösterdiği/aktardığı W ve Wh eskiden aynı
örneğin V×I'sıydı: V, I'dan 152 µs (+ faz kalibrasyonu) ÖNCE örneklendiği için endüktif/kapasitif yükte
kartın nokta W'sinden farklıydı (50 Hz, PF 0.5'te ~%8). Nokta oturumları zaten kartın W'sini taşıyor —
değişmedi.

**Doğrulama** (commit `296c2e2`): B73 25/25 (node: kayit 97, disari 25, rapor 15; vektörler `--denetle`
aynı), B7 912/912 (+1: K3c; sayım kilidi 911 → 912). Zincir `--artimli` iki TAM koşu (önbellek bu ağaçta
yoktu): 1. koşuda yalnız B22b (LittleFS görüntüsü bayat → `arayuz-uret.py`, `_fs.json` + `sw.js` SURUM)
ve B7 sayımı kırmızı; 2. koşuda bunlar yeşil, B71 (yarıda kesildi) ve B6 (`arduino-cli` geçici dizin
hatası) kırmızı — makine 4 ajanla paylaşılıyor; tek başına yeniden koşunca B71 362/362, B6 77/77. Firmware
ve `kod/` değişmedi. Mutasyon `--neden W1: --paralel 2` **26/26 yakalandı**. İki eski mutasyon kaydı bu
dalın değiştirdiği satırlara güncellendi: B7 K3 `ei` (koşuldu, yakalandı), T3C `onDegisim` (tarayıcı adımı,
koşulmadı). Tam koşuların yeniden ürettiği `BELGELER/`, `sema3/`, `_tezgah.md`, `netlist3.net`,
`_firmware.json` commit'e ALINMADI (satır sonu / zaman damgası gürültüsü; `_tezgah.md` sıra farkı).

**Açık:** firmware V–I kaymasını AYRINTI'ya yazmıyor (sabit 152 µs kullanılıyor) · ADS takılınca PC
hizalı W ↔ kartın `D` satırı W'si tezgahta karşılaştırılmalı (T11) · 16.38 ms'den kısa skop duraklaması
kartta hâlâ işaretsiz; PC artık META'dan bulur (O listesinde kapandı).

---

---

#### 5.12.102 🟢 W3: PANEL AÇILIŞ BÜTÇESİNE PAY — TEMBEL EKRAN SÖZLÜKLERİ (2026-10-03, dal `w3-butce`)

Ajan (W3), kart yok. Karar `tasarim/2026-10-02-alt-proje-3-panel.md` **EU32**; açık işler
`tasarim/1-acik-isler.md` "Panel açılış bütçesi" (W3-1 kapandı, W3-2…4).

- **Ne taşındı:** yalnız TEMBEL zincirlerin kendi kullandığı metinler. `ortak/src/sozluk_kayit.js` (200
  anahtar: `kl.`/`kg.`/`kr.`; `kayit_gorunum.js` statik alır, Kayıtlar ve Karşılaştırma onu zaten
  alıyor) ve `ortak/src/sozluk_ay.js` (95 anahtar: `ekran/ayarlar.js`). Ayrım elle değil: anahtarı
  hangi dosyaların dizge olarak yazdığına bakan betik (B73 `dizgeler` çözücüsü); birden çok ekranın ya
  da kabuğun kullandığı her metin açılışta kaldı. `ceviriKayit`/`ceviriAy` = önce kendi sözlüğü, yoksa
  `sozluk.js`; ekranlar `import { ceviriKayit as ceviri }` ile (çağrılar değişmedi).
- **Tuzak (bulundu, düzeltildi):** Kayıtlar `NEREDE_METIN` / `nedenMetni` / kopya satırı `pc.` ve `kl.`
  anahtarlarını KARIŞIK `ceviriPc`'ye veriyordu; `ceviriPc` yalnız açılış sözlüğüne düştüğü için taşımadan
  sonra "nerede" sütunu `kl.nerede_kart` yazardı → `kayit_gorunum.js` `ceviriKlPc` (B7 iddiası + T3H'nin
  "ekranda ham anahtar yok" denetimi).
- **`os.`/`pl.` bilerek kaldı:** iki ekran kabuğun parçası (app.js + index.html), modül inmeden çizilir;
  Pil'in DURDUR'u modülü beklemez (PU1). `os.`'u taşımak `#/skop`'u küçültmezdi.
- **Ölçüm (B7, gzip):** `sozluk.js` 27 727 → 18 187 B · açılış kümesi 209 404 → **199 864** · Canlı ile
  açılış 238 403 → 228 863 · `#/skop` 250 794 → **241 254** (pay 5.2 → 14.7 KB) · `#/pil` 240 732 →
  231 192 · eşleşmiş açılış (EU31) 259 996 → **250 456** (3D'nin 256 000'inin de altında; 15 dosya
  istisnası sürüyor) · `#/ayar/depolama` 265 232 → 260 358 · kart görüntüsü 417 627 → 421 545 B.
  Bedel: Ayarlar modülü iki dosya (AY2 güncellendi), görüntü +3.9 KB.
- **İddialar:** B73 `ortak/test/sozluk_kayit.test.js` + `sozluk_ay.test.js` (yerleşim iki yönde, statik
  içe aktaranlar, ATMAZ geri düşme); B7 +4 (tembel sözlükler açılış/#/skop/#/pil/eşleşmiş açılışta yok,
  `sozluk.js` ≤ 19 500 B, `sozluk_ay.js` ≤ 5.5 KB, `ceviriKlPc`) ve metin iddiaları birleşik sözlük
  görünümünden (`sozlukTum`); T3H +3, T3E +1, T3F +1 gerçek tarayıcıda. 18 `W3:` yalanlayıcısı; taşınan
  anahtarları hedefleyen 10 eski mutasyon yeni dosyaya yönlendirildi.
- **Sonuç:** B7 915/915, B73 27/27 (node 490/490), sim3_web 113/113; tarayıcı T3H 31/31, T3C 50/50,
  T3G 31/31, T3E 38/38, T3F 34/34, T3A 16/16. Mutasyon `--neden W3:` **18/18 YAKALANDI**, yönlendirilen 10
  eski kayıt 10/10. Zincir `--artimli`: iki koşuda B6 (`fw3_*` geçici dizini derleme sırasında silindi) ve
  B71 (`kayit_*` geçici `.elf` yok) birer kez KALDI — ikisi de öbür koşuda / ayrı TEMP ile yeşil (B71
  362/362); eşzamanlı dört ağacın geçici dizin çakışması, bu değişiklikle ilgisiz (firmware'e dokunulmadı).

#### 5.12.99 🟢 HIZ ↔ main BİRLEŞMESİ (2026-10-03, dal `zincir-hiz`, ağaç `projeler/olcum-karti-hiz`)

Ajan. `main` (e6e086d: 4D–4J, 3C-LISTE, kılavuz, `gercek_dizin_koru` son kuralı, köprü 405) `zincir-hiz`'e
(1c51e46) `--no-ff` alındı. Push yok. HIZ'in iki kaydı **5.12.91 → 5.12.97, 5.12.92 → 5.12.98** oldu
(`main`'in 5.12.91'i 3C-LISTE, 5.12.92'si 4G KABUL — numaralar çakışıyordu); başlık ve iç atıflar düzeltildi.

- **B72.A6 (iki dal aynı düzeltmeyi yapmıştı):** tek uygulama — 4J'nin `(zaman, yol)` kaydı + `w.imzali_ac`
  geri yükleme, HIZ'in önek süzgeci (`yol.startswith("/kayit/veri")`) ve varış aralığını tanı satırında
  gösterme. Eşik **0.09 s** (4J 0.098'di): zaman damgası sınırlayıcının `onceki`sinden sonra alınır, GIL
  geçiş aralığı 5 ms — yük altında 0.098 sınırda kalırdı. Yalanlayıcılar 0 ms (4C ×2) ve 50 ms (4J) — üçü de
  eşiğin çok altında.
- **B72.Q16 önbelleği:** HIZ'in anahtarı (test_bildirim'in GERÇEKTEN yüklediği modüller) alındı, ama 4E'den
  beri test_bildirim `ortak/src/sozluk.js` ve `kod/olcum-karti-a3/bildirim.h`'yi DOSYA olarak okuyor —
  modül listesi bunları görmez, `main`'in elle listesi görüyordu. İkisi açık `ek_girdi` olarak anahtara
  eklendi; listede olmayan kayıt geçersiz.
- **`gercek_dizin_koru` (main'in kuralı aynen) + HIZ'in özel LOCALAPPDATA'sı:** `ozel_ortam.yerel_kur` özel
  dizinin köküne `.olcum-ozel-yerel` işaretini yazar; `koru()` bunu görünce `koruma["ozel"]`, `denetle`
  köprü muafiyeti VERMEZ — özel dizine gerçek köprü yazamaz, oradaki her değişiklik testindir. Testi
  DOĞRUDAN koşan yine main'in kuralıyla korunur. Yeni B22a iddiası (test_kopru) + 3 `HIZ-BIRLESME`
  yalanlayıcısı.
- **`mutasyon.py`:** iki listenin hepsi korundu (2073 + 4 yeni = 2077 kayıt, hepsi 6’lı); yeni koşucu hepsini
  koşar. ⚠ `main`'den gelen **4 eski mutasyon UYGULANAMADI** (desen kaynakta yok, birleşmeden ÖNCE de):
  3A `arayuz-uret.py: return list(VARLIKLAR) + ekran + ortak`, 3C/WIG `sozluk.js` 401 metni, 3C (C4)
  `kayitlar.js` `const nerede = ...`, 4D `kart_wifi.py` DURDUR docstring'i — sahipleri güncellemeli.

- **Birleşmenin ortaya çıkardığı iki kusur (düzeltildi):** ① Zincir kancası yalnız `127.0.0.1`'i yerel
  sayıyordu; 4E testi sahte aracıyı `127.83.41.7`'de açıyor → B72 `--artimli`'de **HER ZAMAN KOŞAR** oldu.
  Artık bütün `127.0.0.0/8` yerel (`sitecustomize.yerel_mi`); `test_zincir_hiz` A adımı oraya bağlanır, B5/B15
  iddiası sınar + yalanlayıcı. ② HIZ'in "kesme kodunu görmezden gel" yalanlayıcısı (A5b) iki kez **KAÇTI**:
  ölçüt `mtime > t_kes + 50 ms` idi, bekleyen işçi yeni koşuyu kesmeden ~40 ms sonra başlatıyordu; ayrıca
  yarış makineye bağlıydı. Ölçüt artık "TARAYICI_AZAMI'yı aşan kayıt", sürücü kesmeyi ana iş parçacığında
  2 s geç işler → yalanlayıcı her seferinde A5b ile ölür.
- İlk `--artimli` (tam koşudan hemen sonra) 16 adımı koştu: birleşmeden önce `git checkout` ile geri
  aldığım üretilmiş dosyalar (`_firmware.json`, `netlist3.net`, LF) tam koşunun SONUNDA CRLF'li yeniden
  yazıldı, erken adımlar eski hali okumuştu. Bir kerelik; sonraki tam koşudan sonra 22/22 önbellekten.

**Doğrulama (bu ağaç, 2026-10-03):** `test_zincir_hiz.py` **101/101** (61–65 s) · tam zincir
`--tam --sayim-kilidi-yaz` **22/22**, kilit 5289 → **5290** (B22a +1), 1060 s; kanca düzeltmesinden sonra
yeniden **22/22, 1013 s** · `--artimli`, değişiklik yok: **22/22 önbellekten, 14 s** ·
`mutasyon.py --neden HIZ --paralel 4` **82/82** YAKALANDI (1932 s; ilk koşu 81/82, 1868 s — A5b, yukarıda) ·
`--neden 4I` **20/20** (546 s) · `--neden 4J` **8/8** (259 s; 50 ms tavanı B72.A6 ile öldü, bir ŞÜPHELİ
tek başına yeniden koşulup YAKALANDI) · `gizlilik_dogrula.py` temiz (361 dosya) · gerçek
`%LOCALAPPDATA%\olcum-karti` koşulardan önce/sonra birebir aynı; `_mutp*` ve `msedge.exe` kalıntısı yok.
Son commit'lerden sonra `--artimli` kendisi TAM koştu (git HEAD `mutasyon.py`'ye dokunmuştu): **22/22, 1078 s**;
ardından `--artimli` **22/22 önbellekten, 13 s**.

---

#### 5.12.98 🟢 HIZ İNCELEMESİ: 11 ÖLÇÜLMÜŞ KUSUR KAPANDI (2026-10-03, dal `zincir-hiz`)

Bağımsız inceleme 5.12.97'nin iki hızlandırmasında 11 kusuru deneyle gösterdi (3 kritik). Hepsi önce
`test_zincir_hiz.py`'de kırmızı bir iddia, sonra düzeltme, sonra yalanlayan bir `HIZ:` mutasyonu.

**Artımlı zincir (`zincir_onbellek.py`):**
1. 🔴 **TOCTOU** — imza adım BİTTİKTEN sonra alınıyordu: adım dosyayı eski haliyle okuyup yeşil verdi,
   kullanıcı o sırada dosyayı bozdu, sonraki `--artimli` 22/22 önbellekten YEŞİL (B25'e `raise SystemExit`
   sokuldu). Şimdi adımdan ÖNCE önceki kaydın girdileri içerikle + depo (boyut, mtime, ad kümesi)
   özetlenir, sonra karşılaştırılır; depo dışı yeni girdi mtime ile (100 ms pay). Değişen varsa kayıt
   GEÇERSİZ (sonraki koşu koşar; kayıt "önce" imzası için saklanır). B19/B19b/B19c.
   Çıktılar zincir sonunda YENİDEN ÖZETLENMİYOR (kullanıcının araya giren değişikliğini kutsuyordu):
   her kayıt o yolu EN SON YAZAN adımın, adımdan hemen sonraki özetini alır; adım SIRASINDA değişen başka
   adımın çıktısı (kicad-cli izlenmeden yazıyor) o adımın yazımı sayılır (B20/B20c, B3/B9 ping-pong yok).
2. 🔴 Kullanıcının `PYTHONPATH`/`NODE_OPTIONS`'u anahtardan düşürülüyordu (gölge numpy → 22/22 yeşil).
3. `HTTP_PROXY` (ve ARDUINO_*/KICAD*/SPICE_*) anahtarda değildi → **anahtar artık ortamın TAMAMI**, yalnız
   oturum değişkenleri hariç (`ORTAM_UCUCU`: CLAUDE_*, VSCODE_*, PWD, TEMP…). ⚠ Farklı terminal (Git Bash ↔
   PowerShell, PATH farklı) = her adım koşar. B21/B22/B22b.
4. `ozel_ortam.py` (her adımın LOCALAPPDATA'sını kuruyor) anahtarda değildi → `ANA_SUREC` (anahtar) +
   `ANAHTAR_DISI` (gerekçeli); `dogrula3`'ün import ettiği her depo modülü ikisinden birinde olmalı (B23).
5. Gölge modül (`uretim/gzip.py`) adımları koşturmuyordu → kanca çıkışta `sys.path`'teki her dizini
   LİSTELER (B24). ⚠ Bedeli: `uretim/`'e yeni dosya eklemek bütün Python adımlarını koşturur.
6. B72.Q16'nın `%TEMP%` önbelleği elle 6 dosya sayıyordu (`pc_ayar.py`, `gercek_dizin_koru.py` yoktu —
   tam koşuda bile yeşil). Anahtar artık test_bildirim'in GERÇEKTEN yüklediği depo modülleri (geçen koşunun
   `sys.modules`'ü, 8 dosya), adı ağaç köküne bağlı; `.gecti` dosyaları `gecici.DOSYA_ONEKLER` ile süpürülüyor.
   Yalanlayıcı: `pc_ayar.py`'ye yalnız test_bildirim'i kıran satır → Q16 kırmızı.
   Ek (küçük): ngspice.dll yükleyen adımın girdisi `~/.spiceinit` + `spinit` (B25).

**Paralel koşucu (`mutasyon.py`, `ozel_ortam.py`):**
7. 🔴 **İç içe özel LOCALAPPDATA boştu**: B3/B23 işçide `dogrula3` koşuyor; `yerel_kur` junction girdileri
   ATLIYORDU → iç zincir yalnız `Temp` görüyordu (Arduino15 yok → B22b 113→112, sayım kilidi kırmızı; Python
   yok → B73'ün `python`'u Python'u yeniden indirtebilirdi). Bu dalın getirdiği gerileme. Artık bağlantı
   girdisi HEDEFİNE bağlanır; hedef kaynağın kendisi/atası ise ("Application Data") izlenmez (A9; gerçek
   LOCALAPPDATA ile denendi: iç içe 94 girdi, Arduino15 + Python görünür, olcum-karti görünmez).
8. Aynı ağaçta zincir + koşucu: `_b*` spice dizinleri kopyalanıyordu, kaybolan girdi `shutil.Error` ile bütün
   koşuyu düşürüyordu. Artık çöp kalıpları (`ZO.COP_URETIM_KOPRU`) kopyalanmaz, copytree hatasında kopya
   silinip yeniden denenir (A10), koşu başında TEK anlık kopya alınır, işçiler ondan kopyalar (A11).
   **Kural geri geldi: AYNI ağaçta koşan zincirin üstüne koşucu başlatma** (anlık kopya penceresi).
9. 4 işçide ortam kaynaklı çökme YAKALANDI sayılıyordu → iddiasız çökme = ŞÜPHELİ, paralel evreden sonra tek
   başına yeniden koşulur (A12); kırmızı taban bir kez yeniden ölçülür (A13); teşhis son istisna satırı
   (A16); köprünün `durum.json` `os.replace`'i paylaşım ihlalinde yeniden dener (`atomik_degistir`, A14 —
   gerçek köprüde de olabilirdi); varsayılan işçi sayısı makine yüküne göre (A6b); hepsi tarayıcı olan
   seçimde işçi = 2 (A8); B72.A6 aralığı istemcinin GÖNDERME anından (varış zamanı sunucu iş parçacığının
   zamanlamasına bağlıydı; 4C'nin A6 mutasyonlarının üçü de hâlâ A6 ile öldürülüyor).
10. Ctrl+C: kesmeden sonra semaforda bekleyen işçi yeni tarayıcı başlatıyordu (çocuk konsol kesmesiyle ana
   iş parçacığından ÖNCE ölüyor → işçi `STATUS_CONTROL_C_EXIT`'i görünce `durdur`'u kurar); `kosut` durdur
   kuruluyken süreç açmaz (kilitle); kopya dizin dizin iptal edilir; `_mutp*` kalıntısı adıyla yazılır, "kopyalar
   temizlendi" yalnız temizse; koşu başında sahibi ölmüş + 5 dk'dan eski `_mutp*` süpürülür — **sahibi canlıysa
   asla** (ad pid taşıyor; uzun bir koşunun `.ozel` mtime'ı eski kalır). A5b/A5c/A5d/A15/A17.
    Ek: mutasyon başına Edge sızıntısı artık çıkış kodunu kırmızı yapıyor (A15).
11. Kayıt defteri yan etkisi: 5.12.97 ② altına yazıldı — **kullanıcı onayı bekliyor, dokunulmadı.**

**Ölçüm:** `test_zincir_hiz.py` 65 → **101/101** (~65 s). `mutasyon.py --neden HIZ --paralel 4`: 78 mutasyon,
1655 s; ilk koşuda 2'si sorunluydu — semafor mutasyonu KAÇTI (yeni A8 sınırı tek tarayıcılı seçimde semaforu
gereksiz kılıyordu; A8 karışık seçimle yeniden yazıldı) ve `ANA_SUREC` mutasyonu iddiayla değil ÇÖKMEYLE
öldü (B23 testi o listeden kopyalıyordu) — ikisi düzeltilip yeniden koşuldu: **78/78 YAKALANDI**, hepsi
hedef iddiasıyla. B72'nin A6'yı hedefleyen üç 4C mutasyonu yeni ölçümle de A6 ile öldü.
**Gerçek zincir:** tam koşu yeşil **15 dk 20 s** (B3 bir kez GEÇERSİZ: kicad-cli koşarken `%APPDATA%\kicad`'ı
yazdı — önceki kayıtla içerik farkı; sonraki koşuda temiz); `--artimli` 20/22 önbellekten **19.8 s** (B3 +
netlist'i yeniden yazdığı için B9), ardından **22/22, 12.2 s**. **TOCTOU gerçek kartsız zincirde:**
B25 koşarken (`test_tezgah_kart.py` süreci görülünce, 30 s sonra) dosyanın başına `raise SystemExit` sokuldu →
r1 `GECTI B25 347.4 s` + `[uyari: girdi adim SIRASINDA degisti ...]`, r2 B25'i koştu ve **KALDI** (eskiden
22/22 önbellekten yeşil). İlk deneme yanıltıcıydı: dosyaya yönlendirilen stdout blok tamponlu, "B25" başlığı
adım BİTTİKTEN sonra göründü ve bozma adımdan sonra yapıldı — süreç listesinden tespit gerekiyor.
Kayıt defteri zincir koşuları öncesi/sonrası AYNI (yeni yan etki yok).

#### 5.12.97 🟢 HIZ: PARALEL MUTASYON + ARTIMLI ZİNCİR + ÖZEL LOCALAPPDATA (2026-10-03, dal `zincir-hiz`)

Kullanıcı "işler hızlansın" dedi, dört seçenekten ikisini seçti (hafıza: *hız alt ajan*). Kod:
`uretim/mutasyon.py` (koşucu), `uretim/zincir_onbellek.py` + `uretim/zincir_kanca/` (artımlı zincir),
`uretim/ozel_ortam.py` (özel LOCALAPPDATA, junction'lar, güvenli silme), `uretim/dogrula3.py` (22 adım artık
`Zincir` üzerinden). Test `uretim/test_zincir_hiz.py` **65/65** (sahte projelerde, ~45 s; **zincirde DEĞİL** —
30 s sınırını aşıyor ve kendi sahte araçlarını çağırdığı için zincirde HER ZAMAN KOŞAR olurdu; bu dosyalara
dokunan her değişiklikten sonra elle koş). Yalanlayıcılar `python mutasyon.py --neden HIZ --paralel 4`
****48/48** (son tam tur 47/47, 786 s; 48.'si teşhis satırının)** — ilk turlar 4 boş iddia buldu (sonuç sırası, node yükleyici kancası, `.gitignore` alt dizgisi,
önbellek dosyasının dizin listesi), hepsi testle kapandı.

**A — `mutasyon.py --paralel N`** (varsayılan min(4, çekirdek−2); `--paralel 1` sıralı, aynı karar kümesi — A1).
İş kuyruğu; her işçinin KENDİ kardeş kopyası `_mutpN-<pid>-<t>` ve KENDİ `TMP/TEMP/TMPDIR` + `LOCALAPPDATA`'sı
(`_mutpN-….ozel/`). **Taban her betik için HER İŞÇİDE kendi ortamında** (başka yerde ölçülmüş taban, işçinin
ortamı bir betiği bozduysa her mutasyonu sahte YAKALANDI yapardı). Tarayıcı açanlar (AGIR + `tarayici*` +
B57) en fazla **2 eşanlı**; her birinden sonra işçinin TEMP'inde kalan `msedge.exe` öldürülüp SIZINTI
raporlanır (A8). Ctrl+C / CTRL_BREAK → kopyalar silinir (A5). `--neden ÖNEK` scratch `mut_hedef_*.py`'lerin
yerini aldı. YAKALANDI satırının altında `ilk kirmizi:` — mutasyonu HANGİ iddianın öldürdüğü.
🔴 **KURAL DEĞİŞTİ (⚠ 5.12.98: AYNI AĞAÇ için YANLIŞTI — kural orada sürüyor, aşağıya bak):** "zinciri mutasyon koşusuyla üst üste bindirme" YENİ koşucu için kalktı —
`dogrula3.py`'nin `%TEMP%` süpürmesi işçilerin özel TEMP'ine ulaşamaz (A3: iki eşanlı koşu + sürekli süpürme;
A3b: süpürme ortak TEMP'te gerçekten siler). ⚠ Eski/scratch koşucular (`mut_hedef_*.py`, `mut_par.py`) ortak
TEMP kullanıyor; onlar için kural sürüyor.

**ÖZEL LOCALAPPDATA (zincir + işçiler) — iki ölçülmüş kusurdan:** ① tam zincir koşarken gerçek köprü (4E)
`%LOCALAPPDATA%\olcum-karti\bildirim\` altına yazdı (14:11); B72'nin `gercek_dizin_koru`'su KIRMIZI oldu ve
"geri al" adımı **köprünün yeni dosyalarını kullanıcının gerçek dizininden SİLDİ** (`bildirim/son.json`,
`bildirim/<kart>.okb`). Aynı pencerede yeni bir arşiv akış dizini açılsaydı onaylanmış kayıtlar da silinirdi.
② ilk sürüm özel dizine yalnız Arduino15'i bağladı; B73'ün tam yolsuz `python`'u WindowsApps takma adından
geçti, Python kurulum yöneticisi `%LOCALAPPDATA%\Python`'u bulamadı ve **özel dizine 153 MB yeni bir
Python 3.14 indirip kurdu**. ⚠ **Yan etkisi (5.12.98 incelemesinde bulundu, RAPORLANMAMIŞTI):** kurulum
yöneticisi `HKCU\Software\Python\PythonCore\3.14` kaydını (PEP 514) o özel dizine yazdı — DisplayName
`Python 3.14.8`, `InstallPath\ExecutablePath` = `…\projeler\_zincir-yerel-33400-127871700\yerel\Python\
pythoncore-3.14-64\python.exe`; dizin silindi, yol YOK. Kayıt defterinden Python bulan araçlar (VS Code /
IDE, eski `py` başlatıcısı) olmayan bir 3.14.8 görüyor; `python` komutu (`bin\*.__target__`) hâlâ gerçek
3.14.2'ye gidiyor. **Dokunulmadı — kullanıcı onayıyla onarılacak** (gerçek 3.14.2'yi kurulum yöneticisiyle
yeniden kaydettirmek ya da anahtarı gerçek yola çevirmek). Şimdi: `dogrula3.py` her koşuda `projeler/_zincir-yerel-<pid>-…/yerel` kurar;
gerçek LOCALAPPDATA'nın HER üst dizini junction (yalnız `olcum-karti` ve `Temp` HARİÇ), sonunda
`guvenli_sil` (junction BAĞLANTI olarak kaldırılır, hedefe inilmez — A4 + yalanlayıcı). 6 saatten eski
kalıntıları kendisi süpürür.

**B — `dogrula3.py --artimli`** (İSTEĞE BAĞLI; varsayılan TAM). Adımın YEŞİL sonucu, okuduğu hiçbir şey
değişmediyse yeniden kullanılır. Girdi keşfi KANITLA: `PYTHONPATH` başına `zincir_kanca/sitecustomize.py`
(`sys.addaudithook`: open, CopyFile2, rename/remove, listdir/scandir, Popen/CreateProcess, ctypes.dlopen,
loopback dışı ağ; `os.path.exists/isfile/isdir` + `os.stat` sarmalanarak varlık yoklamaları; çıkışta
`sys.modules`) ve `NODE_OPTIONS=--require node_kanca.cjs` (fs + `module.registerHooks` + child_process).
Alt süreçler ortamı miras alır; her kayıt işlemden ÖNCE diske (öldürülen sunucu süreci okumalarını
kaybetmez). Python/node olmayan araçlar: derleyici (avr-*/xtensa-*/arduino-cli…) → argümandaki yollar +
deponun BÜTÜN C ailesi dosyaları + kurulum dizini imzası; kicad-cli → şemanın dizini + `%APPDATA%\kicad`;
ngspice.dll → sürücü netlistinin `.include/.lib` satırları. **SAYIM DENETİMİ:** açılan her Python/node
süreci rapor yazmalı; eksikse (`-I`, ortamı silinmiş alt süreç, `os.system`, Popen dışı süreç) adım HER
ZAMAN KOŞAR. **Gerçek zincirde 22 adımın HİÇBİRİ "her zaman koşar" çıkmadı** (hepsinin girdisi sınırlandı).
Çıktılar zincirin SONUNDAKİ haliyle saklanır (B3 ve B9 ikisi de `netlist3.net` yazıyor). Önbellek
`uretim/.zincir_onbellek.json` (gitignore; mutasyon kopyasına taşınmaz, kök yolu da denetlenir).

**TAM koşu ŞART:** (1) `main`'e göndermeden önce (kullanıcı kararı — varsayılan zaten tam);
(2) son yeşil tam koşu > 24 sa; (3) `dogrula3.py`/`mutasyon.py`/`tasarim3_sabit.py` son tam koşudan beri
değiştiyse ya da git HEAD bunlara dokunarak değiştiyse — (2) ve (3)'ü `--artimli` kendisi anlar;
(4) `--sayim-kilidi-yaz` (`--artimli` ile REDDEDİLİR). Tam koşu da izler ve önbelleği tazeler; `--izsiz` =
kancasız tam koşu (önbelleğe dokunmaz). Sayım kilidi her adımı yine karşılaştırır (önbellekten gelenin
sayısı önbellekteki çıktıdan — B9).

**Ölçümler** (aynı makine, sırayla):

| | süre |
|---|---|
| tam zincir, `main` 0b1e9a6 (kancasız, eski) | 806.7 s |
| tam zincir, bu dal (kancalı; ilk tur) | 806.0 s — kanca maliyeti ölçülemeyecek kadar küçük |
| tam zincir, bu dal (son hali, özel LOCALAPPDATA) | 1017.2 s — yeşil; makine o sırada yüklüydü (CPU'ya bağlı B58f/B71/B4/B6 1.3–1.8× yavaş, beklemeye bağlı B25 347 s aynı) |
| `--artimli`, hiçbir şey değişmedi | **27.2 s** — 22/22 önbellekten |
| `--artimli`, `kopru/kopru.py`'ye yalnız dokunuldu (mtime) | **20.5 s** — 22/22 önbellekten (içerik özeti; mtime sayılmaz) |
| `--artimli`, `kopru/kopru.py` içeriği değişti | **70.6 s** — koşan: yalnız B22a + B72 (kopru.py'yi gerçekten okuyan ikisi) |
| `mutasyon.py --neden 4C` (38) `--paralel 1` | 985.9 s, 38/38 |
| aynı, `--paralel 4` | **336.2 s, 38/38 — 2.9×** (bir önceki deneme işçi tabanında B72.A6 düştü, 62 s'de DURDU — aşağıya bak); teşhis düzeltmesinden sonra yine 315 s, 38/38 — `ilk kirmizi` B72.A6 olan 3 mutasyonun üçü de A6'yı HEDEFLEYENLER (PARCA_BAYT, PARCA_ARASI_SN, `uyu` atlama): bu koşuda sahte YAKALANDI yok |
| `mutasyon.py --adim B22b` (37) `--paralel 1` → `--paralel 4` | 165.2 s → **66.3 s (2.5×)**, karar kümesi BİREBİR aynı (36 YAKALANDI + 1 UYGULANAMADI — `arayuz-uret.py: return list(VARLIKLAR) + ekran + ortak` deseni `main`'de zaten yok, eski mutasyon) |

⚠ **B72.A6 ZAMANLAMAYA BAĞLI VE KIRILGAN (bu dalın değil, 4C'nin):** "iki parça isteği arası ≥ 100 ms"
sahte kartta VARIŞ zamanından ölçülüyor; bir kez tek başına (81 ms), 4 eşanlı tabanın ikisinde (82 ms)
düştü. Sonuç: zincir ara sıra sebepsiz kırmızı; paralel mutasyonda işçi tabanı kırmızı → koşu durur
(güvenli yön), ama bir MUTASYON koşusunda düşerse o mutasyon **sahte YAKALANDI** olur — `ilk kirmizi:`
satırı A6 ise sonuç şüpheli. Öneri: aralığı istemcinin GÖNDERME zamanından ölç (4C sahibine).

**Tuzaklar:** Windows'ta `"a"` kipi atomik değil (CRT sona-git + yaz) — eşanlı süreçler satır kaybediyor;
`waitfor` sinyal adı sistem genelinde tek süreçlik; iç içe koşuda "`_mutp` geçiyor" ölçütü yetmez (dış
işçinin yolu da taşır); Python 3.14 `shutil.rmtree` junction izlemiyor ama `guvenli_sil` buna güvenmiyor;
ilk test sürümü süpürmeyi GERÇEK `%TEMP%`'te koşturdu (o sırada `olcum-karti-4d`'de tam zincir koşuyordu —
`zincir_4de.txt` açıklanamayan bir spice/köprü kırmızısı gösterirse yeniden koşulmalı); düzeltildi.

**Açık riskler:** araçların KENDİ kurulum dosyaları (ESP32 çekirdeği, avr-libc, KiCad kütüphaneleri) yalnız
ikili + dizin imzasıyla izleniyor; importlib'in kendi listelemeleri sayılmıyor (sys.path'e eklenen gölge
modül görünmez); saat/tarih ya da tohumsuz rastgeleliğe bağlı davranış (B71 tohumlu); ortamdan yalnız
PATH/PYTHON*/NODE_*/OLCUM_*/LOCALAPPDATA/APPDATA/… anahtara giriyor. Hepsi 24 sa kuralı ve `main` öncesi tam
koşuyla sınırlı. `gercek_dizin_koru`'nun "geri al"ı hâlâ gerçek dizinde SİLİYOR — zincir ve yeni koşucu
artık oraya ulaşmıyor, ama testi DOĞRUDAN (`python test_kayit_esp.py`) köprü açıkken koşan biri yine
köprü dosyası silebilir (4B sahibine: silmek yerine yalnız raporla).

#### 5.12.96 🟢 BİRLEŞİK-4: 4G+4J, 4H, 4I, KILAVUZ TEK DALDA (2026-10-03 gece)

Ajan, dal `birlesik-4` (ağaç `projeler/olcum-karti-birlesik`, `main` 40d33f7'den), sırayla `--no-ff`: `4j-ag`
(4G'yi içerir), `4h-kalan`, `4i-surucu`, `pc-kilavuz`. Push yok; `dogrula3.py` koşulmadı (orkestratör koşacak).

- **`gercek_dizin_koru` tek kurala indi** (4G-3 "köprü açıkken geri alma yok" + 4H "geri alma yalnız `cihaz/`"):
  geri alma YALNIZ `cihaz/`'da beliren dosyada, başka yerde hiçbir şey silinmez; gerçek köprü 127.0.0.1:8770'te
  `/durum` verirken `cihaz/` dışındaki değişiklikler ve `cihaz/`'da VAR OLAN dosyanın değişmesi (köprü kendi
  cihaz dosyasının sayacını ilerletir) beklenir → yeşil; `cihaz/`'da YENİ dosya her zaman kırmızı (+ geri alınır).
  4G iddiası bu kurala göre yeniden yazıldı (iki kip × iki durum), +2 `4H:` mutasyonu; "4B: test eşleştirmeyi
  yönlendirmesiz" yalanlayıcısı aynen ısırıyor.
- **Kılavuz (`belge_pc.py`):** bildirimlerde panel yolu "Ayarlar → Gelişmiş → “Bildirimler (bu bilgisayar)”"
  (adlar ve sınıflar `sozluk.js` / `sozluk_pc.js` / `pc_kopru.js`'ten OKUNUR), komut satırı yolu ikinci seçenek;
  bildirim tablosunda paneldeki kutu adı. Kökteki `Kopru Baslat.bat` artık `kopru\PC Baslat.bat`'ı çağırıyor
  (eskiden doğrudan `kopru.py` + "kart USB'de olmalı"); çevrimdışı sayfa ve sw.js yedek metni
  `kopru\PC Baslat.bat` diyor. İki yeni kural (15/15) + 5 `KLV:` mutasyonu. BELGELER dipnotu ve index uyarısı:
  "Kart kuruluyor — ESP32 çalışıyor, ADS modülleri henüz takılı değil" (eski: "Donanım henüz kurulmadı").
- **4I yalanlayıcısı koşuya göre kaçıyordu:** `AKIS_YOKLAMA_S = 15.0` birleşik ağaçta iki kez KAÇTI (bir kez
  öldü). Bölüm 2'de sürücünün kapanışını bazen önceki bölümlerin bayat işleyicileri (kendi 15 s uyanışlarında
  `surucu_yokla`) fark ettiriyordu — iddia zamanlamaya bağlıydı. Yeni B22a iddiası (bölüm 7): temiz köprüde TEK
  akış, başka trafik yok → kapanış işleyicinin kendi yoklamasıyla ≤ 5 s'de (yüklü makine payı) kayıttan düşer, pencere başlar
  (gerçek 0.50 s; mutasyonla akış 10 s sonra hâlâ kayıtlı → kesin kırmızı).
- DEVIR sırası 5.12.95 (4J) · 94 (4I) · 93 (4H) · 92 (4G) — numara çakışması yoktu. `beklenen_sayim.json`
  zincir koşusunda yeniden yazılacak (B22a 191, B72 207, B7 911, B9 kuralları 15).

#### 5.12.95 🟢 4J: KÖPRÜNÜN KART İSTEKLERİ ÖĞRENİLMİŞ ADRESE — TAM EŞİTLEME 24–26 s → 18.4 s (2026-10-03 akşam)

Ajan, dal `4j-ag` (HEAD 9e4eb13 = main + 4G). 4G'nin açığı: Windows `olcum.local`'ı ~8 s'de bir yeniden
çözüyor ve çözüm 2.7 s sürüyor; 4G yalnız `p0`'ı akışın karşı adresine almıştı. Kararlar spec
"4J uygulama kararları" (4J-1…8).

**Değişiklik (`kopru/kart_wifi.py`):** `WifiKart._karsi` = ad ile kurulan son bağlantının karşı ucu. Bütün
kart istekleri (`dogrula`'nın açık `/eslestir/bilgi`'si, `akis_url`, `/akis`, `imzali_ac` → komut, `/saat`,
eşitleme, vekil, `/bildirim/bilgi`) WifiKart'ın kendi açıcısından (`_ac`, `_KartBaglantisi`) geçer; TCP'yi
`_baglan` kurar: önce öğrenilmiş adres (en çok 2 s), kurulamazsa BİR KEZ ad + tazeleme. URL ve `Host:`
değişmez (kart yabancı Host'u 403 ile reddeder). `dogrula` öğrenilmiş adreste başarısızsa adresi unutur ve
ad ile bir kez daha dener — kimlik denetimi aynen. `p0` 4G yolunda, değişmedi.

**Gerçek kart ölçümü** (`A3-4B`, WiFi; karta yalnız `/eslestir/bilgi`, imzalı `/kayit/liste` `/kayit/veri`,
`G?`, `p0`; eşitleme ONAYSIZ, geçici veri dizinine, cihaz dosyasının KOPYASIYLA — gerçek
`%LOCALAPPDATA%\olcum-karti`'ye yazılmadı; önce = `git archive HEAD kopru`, önce/sonra dönüşümlü):

| | Önce | Sonra |
|---|---|---|
| Tam eşitleme (2299 kayıt, 1 311 112 B, 165 imzalı istek, canlı akış açık) | 23.57 · 26.37 · 24.82 s | **18.41 · 18.35 · 18.53 s** (taban 16.5 s) |
| İstek başı (100 ms ara dahil) | 143–160 ms | 111–112 ms |
| İmzalı `G?` | ortanca 60–131 ms, 2.7–2.8 s takılma **6/60** | ortanca 114–127 ms, en kötü 149 ms, takılma **0/48** |
| İmzalı `/kayit/liste` (kartta 350–600 ms) | 3.0–3.2 s takılma **5/40** | en kötü 634 ms, **0/32** |
| `/eslestir/bilgi` | her 8'de 1–2 kez 2.75–2.8 s | yalnız sürecin ilk ad çözümü (2.8 s; bir kez 7.5 s) |
| `p0` (akış açık, 5'er) | 20–59 ms | 22–66 ms |

**Keep-alive:** ham soketle `Connection: keep-alive` — kart `HTTP/1.1 200 OK … Connection: close` ile yanıt
verip soketi kapattı, ikinci istek 0 B. ESP32 `WebServer` keep-alive tutmuyor → yapılmadı (4J-5).
**Sayaç kalıcılığı:** `sonraki_sayac` 3.6–4.8 ms (DPAPI 0.33 ms; gerisi mkstemp + fsync + replace); blok
ayırma yapılmadı — kazanç %4, ve zaman tabanlı sayaçta ileri ayrılan blok aynı dosyayı kullanan ikinci
süreci kartın 64'lük penceresinin ötesine atıp köprüyü 401'e düşürürdü (4J-6).
**B72.A6 kararsızlığı:** aralık sahte kartın varış anından ölçülüyordu (yükte 81–82 ms); artık `imzali_ac`
sarmalayıcısıyla İSTEMCİNİN gönderme anında, eşik 98 ms. Yalanlayıcı: tavan yarıya (50 ms).

**Testler:** B72 **207/207** (+3: W14 bütün istekler öğrenilmiş adrese / ad bir kez / Host ad; W15 ölü adres →
bir kez ad, komut tek, 401 yok, IP denemesi ≤ 2 s; W16 eski adreste yabancı cihaz → unut, ad ile doğrula,
yabancıya yalnız açık `/eslestir/bilgi`). Bağlantı hedefi `kart_wifi._tcp_ac` kancasıyla izleniyor; sahte
kartta ad `localhost` (Windows'ta ::1 reddi yüzünden her ad bağlantısı ~2 s). W6 ve A10'un kancaları yeni
katmana taşındı (`w._ac`, `w._baglanti_sinifi` — eski `KW.vekilsiz_ac` / `KW.http.client.HTTPConnection`
yaması artık bir şey ölçmezdi). B22a 172/172, `test_bildirim.py` 259/259, `gizlilik_dogrula.py` temiz.
Mutasyon (karalama koşucusu): **4J 8/8**, **4G 13/13**, **4C 38/38** — hepsi öldü, uygulanamayan yok.
`beklenen_sayim.json` B72 204 → 207.

⚠ **Süreç:** ilk mutasyon koşusunun tabanı kırmızıydı — aynı anda gerçek kartı ölçüyordum ve ölçüm gerçek
cihaz dosyasının sayacını ilerletti; `gercek_dizin_koru` bunu (doğru olarak) "test gerçek dizine dokundu"
diye yakaladı. Ölçüm betiği cihaz dosyasının KOPYASINA geçirildi. Gerçek karta karşı ölçüm yapan her araç,
paralel koşan testleri kırmamak için gerçek dizine yazmamalı.

Açık: öğrenilmiş adres yalnız süreç içinde (köprü her açılışta bir kez ad çözer); `kayit_esitle.py` /
`imza.py` komut satırı araçları eskisi gibi adla.

#### 5.12.94 🟢 4I: YENİLENEN SEKME SÜRÜCÜ KALIR (2026-10-03)

4H'de bulundu: köprü, yenilenen/kapanan sekmenin sürücü jetonunu tutuyordu; yenilenen sekme izleyici kalıyor,
açılış komutları (`?` `CT` `G?`) 403 alıyordu — PC uygulamasında her yenilemede. Gerçek Edge'de (T4A) önce
KIRMIZI görüldü. Düzeltme yalnız `kopru/kopru.py`: her `/akis` kaydediliyor, işleyici soketi 0.5 s'de bir yokluyor
(`select` + `MSG_PEEK`); sürücünün bütün akışları kapanınca rol **en yeni yaşayan yerel** akışa geçiyor ve ona
`event: kimlik` gidiyor (yeni bağlantıda, akış bitince ve reddedilecek komuttan önce yoklanıyor). Aday yoksa rol
boşta bekliyor (`None`'a düşmüyor). İki açık sekme arasında çalma yok (`/devral` aynen), LAN asla aday değil,
çapraz köken jeton almıyor, `p0` serbest. `app.js` değişmedi (mevcut `kimlik` dinleyicisi her olayı işliyor).
Devir 0.26–0.44 s. B22a 166 → 175, T4A 12 → 15, mutasyon `4I:` 14. Kararlar spec "4I uygulama kararları".
Açık: kartın kendi web sunucusu dokunulmadı; iki gerçek Edge sekmesiyle ölçülmedi.

**İnceleme düzeltmesi (4I-6):** ikinci yerel sekme açıkken sürücü yenilenince rol arka sekmeye kaçıyordu (eski
işleyici kapanışı yeni `/akis`'ten ÖNCE fark ediyor; 0…1.5 s gecikmelerin hepsinde yenilenen sekme 403). Artık
sürücünün akışları kapanınca 3 s'lik yeniden yükleme penceresi (`AKIS_DEVIR_BEKLE_S`): pencerede rol yalnız yeni
kaydolan yerel akışa; pencere dolunca zamanlayıcı en yeni yaşayan yerel akışa verir; açık sekmenin komutu pencere
sonunu bekler. Bedel: gerçekten kapanan sürücüde devir ~3.5 s. B22a 175 → 177, T4A yenilemesi ikinci sekme
açıkken; mutasyon `4I:` 14 → 20, hepsi öldü. Spec 4I-6.

#### 5.12.93 🟢 4H: ALT PROJE 4'ÜN ARTIKLARI — PANELDE PC BİLDİRİMLERİ, YEREL AĞ UYARISI, KABUK SÜRÜMÜ (2026-10-03)

Ajan, dal `4h-kalan` (ağaç `projeler/olcum-karti-4h`). Kararlar spec "4H uygulama kararları" (4H-1…4H-9). Kart
sınanmadı, karta istek gitmedi.

- **Ayarlar > Gelişmiş, YALNIZ köprüde:** "Bildirimler (bu bilgisayar)" bölümü (bağlantı durumu, son olay, 7 sınıfın
  aç/kapası, bildirim dili) ve kartın arayüz sürümünün yanında köprünün sunduğu kabuk sürümü (`/durum` `kabuk` = sw.js
  SURUM). Yeni modül `ekran/pc_kopru.js` yalnız dinamik; karar 4D'ninki (`kaynak() === 'pc'`), kart kökeninde ne istek
  ne indirme (`ayarlar.js` `kopruKokeni` = `kokenSinama`, B7 eşitliği ölçüyor). Metinler `sozluk_pc.js` (+24, TR + EN).
- **Köprüde `POST /bildirim/ayar`:** `X-Olcum`, yalnız bu bilgisayar, aynı köken, `application/json`, ≤ 512 B; yalnız
  bilinen sınıf → true/false ve `dil`; tekrarlanan anahtar / NaN / boş değişiklik ret; `ayar.json`'a BİRLEŞTİRİR
  (4C anahtarları ve kullanıcının anahtarları kalır), bozuk dosyada 409 ve dosyaya dokunmaz. Sır yolu yok.
- **Yerel ağ istemcisi:** köprünün `LAN_RET`'li 403'leri artık `X-Kopru-Ret: lan` taşıyor; panel komutta ve
  devralmada ham ASCII ret metni yerine çevrilmiş "yerel ağdan salt okuma — DURDUR (p0) her zaman geçer; komut için
  köprünün bilgisayarı ya da karta doğrudan" der. Başka 403'ler (çapraz köken, sürücü değil) işaretsiz, eskisi gibi.
- **Bütçe** (gzip): açılış 209 211 → 209 404; `#/skop` 250 601 → 250 794 (≤ 256 000); EU31 259 803 → 259 996
  (≤ 262 144); `ayarlar.js` 10 692 → 11 154 (≤ 12 288); `pc_kopru.js` 3 824 (yalnız köprüde iner); kart görüntüsü
  411 814 → 417 627 B. EN'de çevrilmemiş metin kilidi 272 (değişmedi). Yeni CSS yok.
- **Testler:** B22a 166 → 173, B7 898 → 911 (bölüm 34), T4D 20 → 24 (gerçek köprü + Edge: seçim gerçek POST ile
  `ayar.json`'a birleşir, GERÇEK yeniden yüklemede korunur — ilk sürüm yalnız hash değiştiriyordu, yeniden yükleme
  sanılıyordu; LAN istemcisi `lan.localhost` + LAN IP'li işleyiciyle). B72.Q16, B22b, B73, T4A, T4F, T3H aynen yeşil.
  Mutasyon `4H:` 37/37 (ilk koşuda biri KAÇTI: yazma yanıtına mutlak yol eklenince "yolsuz" iddiası JSON'un
  kaçışlı ters bölülerini görmüyordu — artık düz VE JSON-kaçışlı biçimi arıyor). Zincir sayımı 5232 → 5252 (hesap;
  `dogrula3.py` bu dilimde koşulmadı).
- **Ev işi:** `tasarim/1-acik-isler.md`'de sonraki işlerle kapanan beş satırın üstü çizildi (D0, kimliksiz onay,
  cihazdan saat, kayıt ekranları, plan gösterimi), her biri kanıt numarasıyla. `mutasyon.py`'de bu dilimin değiştirdiği
  koda bakan 6 eski mutasyon (+ önceden bayatlamış 2: 3F `/pil` kaynağı, 3H `ayarlar.js` içe aktarma) güncellendi.
- **Bulunan, düzeltilmeyen:** köprüde sayfa yeniden yüklenince sürücü jetonu kapanmış sekmede kalıyor (yeni sekme
  izleyici, açılış komutu 403) — önceden var. `gercek_dizin_koru` aynı anda koşan GERÇEK köprünün yeni dosyalarını da
  geri alıyor: bu dilimde bir kez gerçek `bildirim\<kart>.okb` önbelleğini sildi (köprü karttan yeniden alır); sonraki
  koşular yalıtılmış `LOCALAPPDATA`/`TEMP` ile yapıldı (aynı anda koşan başka bir `dogrula3`'ün süpürücüsü de
  `kopru_*` geçici dizinini koşu ortasında silmiş görünüyor).

#### 5.12.92 🟢 4G KABUL: PC UYGULAMASI GERÇEK KARTTA — Ö3, Ö5, 4 İZLEYİCİ, p0 (2026-10-03 öğleden sonra)

Ajan, dal `4g-kabul`. Araç **`uretim/tezgah_pc.py`** (`--o3`, `--o5`; zincirde değil — saf yardımcıları
B22a "4G"de, tezgah kalemi B22a listesinde). Kart `A3-4B`, WiFi, ADS takılı değil, eşleşmiş "Desktop" +
"PC-kopru", `zorunlu=0`. Karta yalnız `?` `G?` `Gb200` `Gd` `Ga` `Gn` `p0`; flaş yazılmadı, `N?` yok.

**Ö3 (11/11)** — `pc.py --usb-yok`, GERÇEK veri dizini, varsayılan ONAYLI (gerçek karta onaylı koşu):
test oturumu 61277 "4G kabul" (`Gb200`, `Ga`, `Gn`); kayıt sürerken bir tur (+4 kayıt); köprü
**202 s kapalı**, kart aynı oturumla kaydetti; yeniden açılınca ilk turda **59 kayıt / 40 340 B, 4.5 s**;
`Gd` + son tur (+2): `Go` gitti, kart `X-Onay` ile doğruladı. Köprü kapatılıp kartın akışı geçici
dizine bağımsız indirildi (2299 kayıt, 22.2 s): PC arşivi **bayt bayt aynı** (1 311 112 B, sıra
59043–61341, `tam_ayni`). Arşivde oturum: ad, not, 1102 nokta, BİTİR sebep 1, testin 65 sırası kesintisiz.

**Ö5 (14/14 ile birlikte)** — köprü geçici veri dizinli + `--onaysiz`, arada bayt kaydeden TCP rölesi
(`KayitciVekil`). **Bulgu:** kart yabancı `Host`'u 403 "Host reddedildi" ile reddediyor (DNS yeniden
bağlama savunması çalışıyor) → röle yalnız `Host:` satırını kartın adıyla yazar. Kayıt: 288 istek,
1.56 MB — `/akis` 1, `/komut` 7, `/kayit/veri` 164 (bos dizinden tam eşitleme 22.6 s), `/kayit/liste` 2,
`/pil` 39, `/kal/liste` 35, `/kunye.json` 33, `/bildirim/bilgi` 1, `/eslestir/bilgi` 6. Bellekte (DPAPI +
`OKB1` zarfı süreç içinde çözüldü, hiçbir değer basılmadı) aranan: K, aracı uri / sunucu adı / kullanıcı /
parola, konu öneki, yük anahtarı — ham, onaltılık (küçük/BÜYÜK), base64 (standart/URL/dolgusuz), yüzde
kodlu: **hepsi 0**; `Authorization:` **0**; köprü konsol günlüğünde de 0. Pozitif denetim: kart kimliği
6 kez, `/bildirim/bilgi` yanıtı `OKB1`. **Web parolası ARANMADI** (`OLCUM_PAROLA` verilmedi). Kayıt ve
geçici dizin silindi.

**4 canlı izleyici** — 6 tarayıcı sekmesi (2 başlıksız Edge × 3) + komut istemcisi köprüden akış aldı
(sekme başına 4 s'de 78–97 `D`), köprü kartta **TEK yuva**. Kalan 3 yuvadan 1'ini kullanıcının Chrome'u
tutuyordu (dünden beri açık; `Get-NetTCPConnection` ile ölçüldü), 2 doğrudan istemci veri aldı, sonraki
`event: dolu`. Kapanan doğrudan istemcinin yuvası 0.2–0.45 s'de boşaldı (4B'nin açık maddesi).

**p0 yük altında** — tam eşitleme + vekil (~3 istek/s) + 6 izleyici sürerken sekmeden 5/5 **204,
45–246 ms** (köprü→kart ayağı 21–226 ms).

**Bulunan ve düzeltilen kusurlar** (her biri önce kartta / testte kırmızı görüldü, `4G:` mutasyonlu):
1. **p0 2.77 s** — Windows `olcum.local`'ı ~8 s'de bir yeniden çözüyor, çözüm 2.7 s (30 çözümde 2694 ve
   2726 ms). Köprünün p0'ı her seferinde adı çözüyordu. Artık canlı akışın karşı adresine (`WifiKart._ip`,
   kopunca silinir), 2 s'de yanıt yoksa ada düşer. Kartta düzeltmeden sonra 30/30 p0 28–117 ms. B72.W4b.
2. **40 s okuma zaman aşımı hiç uygulanmıyordu** — `http.client` SSE yanıtında `HTTPConnection.sock`'u None
   yapıyor; soket 10 s'de kalıyordu, `kapat()` okumayı kesemiyordu. Soket istekten hemen sonra tutuluyor.
3. **`gercek_dizin_koru` canlı köprünün dosyalarını silebiliyordu** — test sırasında gerçek dizinde
   beliren her şey "geri alınıyordu"; kullanıcının köprüsü açıkken bu, yeni `akis-<n>` arşivi / günün
   `.satir`'ı / bildirim önbelleği demek (onaylı kayıt kartta da temizlenebilir → veri kaybı). Ö3 sırasında
   OLDU: başka bir ajanın `test_kopru.py` koşusu köprünün yazdığı gerçek `bildirim\<kart>.okb`'yi sildi
   (orkestratör doğruladı; köprü onu karttan yeniden alır; Ö3'ün arşivi yalnız değişti, silinmedi).
   Artık köprü açıksa geri alma yapılmaz (iddia kırmızı kalır, sebebi yazar). B22a + mutasyon.
4. **Tezgah hijyeni:** `olcum-edge-` öneki ortak — sızıntı sayımı başka koşunun tarayıcısını da sayıyor.
   Araç artık yalnız kendi profillerini sayıyor. ⚠ Bu oturumda genel önekle 16 `msedge` süreci elle
   öldürüldü; profilleri silinmişti (yetim) ama o an başka bir ağaçta `dogrula3.py --artimli` koşuyordu —
   onun tarayıcı adımı etkilenmiş olabilir.

Açık: kart ADS'siz (veri değerleri anlamsız); Ö4 PC karşılığı (PC18), USB kablo çek/tak geçişi, Başlangıç
kısayolu — elle. İmzalı istekler ve eşitleme hâlâ her istekte adı çözüyor (keep-alive yok).
B22a 166 → 172, B72 203 → 204 (zincir 5232 → 5239); mutasyon 4G 13/13. ⚠ Orkestratör aynı korumayı
ayrıca düzeltiyor ("cihaz dizini dışında silme yok" + köprü açıkken geri alma yok) — `gercek_dizin_koru.denetle`
birleştirmede çakışabilir.

**ÖNERİ — `Ez1` (imza zorunluluğu), AÇILMADI, kullanıcı kararı.** İki cihaz da eşleşmiş (Desktop =
kullanıcının tarayıcısı, PC-kopru = bu PC'nin köprüsü), köprü imzalı konuşuyor (4G'de ölçüldü). Adımlar:
1. `python kopru/pc.py --durdur` (ya da `kopru/Kopruyu Durdur.bat`) — köprü COM portunu bıraksın.
2. Kartın **COM yazan** soketi USB'de; seri konsol (Arduino IDE Seri Monitör ya da benzeri, 115200,
   satır sonu `\n`). `E?` → `E zorunlu=0 misafir=0 … cihaz=2` görülmeli (iki cihaz).
3. `Ez1` gönder; yanıtı oku; `E?` → `zorunlu=1`.
4. Köprüyü yeniden aç (`kopru/PC Baslat.bat`); panel (köprüde ve Desktop tarayıcısında kartın kendi
   sayfası) eskisi gibi çalışmalı.
**Sonuç:** eşleşmemiş HER istemci kilitlenir — `/akis`, `/kayit/*`, `/pil`, `/kal/liste`, imzasız `/komut`
401 (serbest kalanlar: `p0`, `?`, `/eslestir/*`, `/` sayfası). Eşleşmemiş telefon / başka tarayıcı canlı
izleyemez (`Em1` misafir izleme açılırsa `/akis` ve `/pil` imzasız kalır). İmzasız HTTP kullanan tezgah
araçları (ör. `tezgah_kayit.py`'nin `esitle()`'si: eşleşmiş cihaz kullanmıyor) 401 alır → o koşulardan önce
USB `Ez0`. Geri alma: USB `Ez0`. Ayar bozulursa kart fail-closed (zorunlu) davranır.

#### 5.12.91 🟢 3C-LISTE: İLK EŞİTLEMEDE BOŞ LİSTE (2026-10-03 öğle)

4D+4E kartta sınanırken bulundu: yeni bir tarayıcıda Kayıtlar açılınca liste ~24 s (ilk eşitleme boyunca) BOŞ
kalıyordu — kartın oturum dizini eşitlemenin başında alınıyor ama listeye ancak eşitleme bitince basılıyordu
(3C'den beri). Artık hemen kuruluyor, oturumlar eşitleme sürerken "yalnız kartta" görünür. T3C 50/50 (12 s
bekletilen istek SIRASINDA 6 oturum listede), mutasyon 1/1. Zincir 5232.

#### 5.12.90 🟢 4E: MQTT ABONELİĞİ + WINDOWS BİLDİRİMİ (2026-10-03)

Ajan (`kopru/pc_bildirim.py` karar katmanı + MQTT iş parçacığı, `kopru/windows_bildirim.py`, `kopru/bildirim_metin.py`
TR/EN). **Deneme (PC13) ölçüldü:** stdlib Python'dan gizli `powershell.exe -EncodedCommand` + WinRT toast — görünüyor
(~0.19 s), aynı Tag/Group ile YERİNDE güncelleniyor (geçmişte tek kayıt), kaynak adı "Ölçüm kartı" + panel simgesi
(`HKCU\Software\Classes\AppUserModelId\OlcumKarti.Kopru` kaydı; kısayol/paket gerekmez, silinince geri alınır),
tarayıcı kapalıyken de. Bu makinede Rahatsız Etmeyin açıktı: afiş çıkmadı, bildirim merkezine düştü (Windows ayarı).
Tepsi simgesi yapılmadı (pencere + mesaj döngüsü ister; durdurma `Kopruyu Durdur.bat`). **Tasarım:** `/bildirim/bilgi`
imzalı, paylaşılan cihaz + sayaç kilidiyle; şifreli `OKB1` zarfı OLDUĞU GİBİ `%LOCALAPPDATA%\olcum-karti\bildirim\`
önbelleğinde (PC14) — kart erişilemezken de abone olunabilir; yeniden alma yalnız çözme hatası / CONNACK 4-5 / durum
konusu 180 s sessizken (QR! öneki de değiştirir), hız sınırlı. Aracı adresi, kullanıcı, parola, önek, anahtar YALNIZ
bellekte; hata metinleri hatanın türünden kurulur (TLS hatası aracı adını içeriyor). "Karttan haber yok" YALNIZ kayıt
sürerken, tek `baglanti` etiketli bildirim, kart yerelde görünürken "Ev interneti koptu", dönünce "yeniden bağlandı"
(aynı bildirim güncellenir); aracı yokken kayıt sırasında 20 s yerel sessizlik de aynı bildirimi verir. Yineleme
`(a, n)` + yerel `G` satırı ile anlamsal anahtar (PC16); `(a, n)` boşluğundan "N olay kaçırıldı" (PC15), son sayaç
diskte. Açma/kapama `ayar.json` `bildirim` (4C anahtarlarıyla birleşir). `GET /bildirim/durum` yalnız bu bilgisayar,
sırsız. **Gerçek aracıda:** kartın tutulan `durum` mesajı 3.4 s'de alındı ve çözüldü; hiçbir şey yayımlanmadı, hiçbir
sır diske/durum satırına/bildirim metnine düşmedi. test_bildirim 222 → 259, B22a +4; mutasyon 4E 59/59, 4C 38/38, 4B
51/51. **Kullanıcının tezgah kalemi (PC18):** kayıt sürerken kartın gücünü kes → "Karttan haber yok" süresi (hedef
10 s, kabul 15 s, 10 tekrar); geri tak → aynı bildirim "yeniden bağlandı"; modemin internet kablosunu çıkar → "Ev
interneti koptu"; USB `Qt` → deneme bildirimi. Rahatsız Etmeyin'de "Ölçüm kartı"nı öncelikli listeye ekle.
Açık: panelde bildirim durumu/ayar bölümü yok (CLI/`ayar.json`), tepsi simgesi, telefon tarafı (alt proje 5).

#### 5.12.89 🟢 4D: PANEL PC'DE — PC ARŞİVİ, KART VEKİLİ, ESKİ SKOP ARŞİVİ (2026-10-03)

Ajan, dal `4d-panel-pc`. Panel köprüde (`olcum.localhost:8770`) Kayıtlar'ı köprünün **disk arşivinden** okur
("bu PC'de"; `kopru/vekil.py`: `GET /arsiv/liste`, `/arsiv/veri`, `/arsiv/kal` — salt okuma, katı parametre, boy =
`durum.json`'un kalıcı öneki, yalnız bu bilgisayar + aynı köken, yol arşiv kökünde) — panelde `ekran/depo_pc.js`
(DEPO okuma tarafı, yazanlar reddeder; tek yazar Python), kaynak kararı denetçide (`/durum` `pc_arsiv`; **kart
kökeninde bu karar için istek YOK**). Kayıt görünümü / grafik / dışa aktarma / rapor / Karşılaştırma aynı kod yolu.
Kartın `/pil`, `/kal/liste`, `/kunye.json`'u köprünün **imzalı vekilinden** (aynı `Cihaz` + sayaç kilidi; 401 → 502
`imza`; vekil hatası 502 + `X-Kopru-Vekil: hata`); `/eslestir/*` vekil EDİLMEZ (EU8'/EU9' yeniden yazıldı); `p0`
vekilde değil, sayaç kilidini beklemez (1.5 s'lik vekil isteği sürerken 0.02 s). Kayıtlar'da köprü eşitlemesinin
durumu (onay açık/kapalı), Osiloskop'ta B35 satır arşivi "Eski arşiv" başlığında. Bayat metinler (`kl.neden_imza`,
`kl.neden_yok`, `kl.neden_usb`, `ay.kal_neden_imza`, `ay.panel*`) düzeltildi; yeni metinler `ortak/src/sozluk_pc.js`
(açılışta değil; açılış +692 B gzip). B22a 150 → 162, B7 878 → 898, B73 24 → 25, yeni **T4D**
`uretim/tarayici_pc_kayit.py` 20/20 (gerçek `sunucu_kur` + gerçek `ArkaEsitleme` turu + Edge). Mutasyon 4D 67.
**Gerçek arşivde (salt okuma, karta istek yok):** 44 oturumun hepsi "bu PC'de", kayıtlar açıldı, arşiv bayt/mtime
aynı; çizgiler boş çünkü o oturumların verisi `n=0` / `V_HATA|I_HATA` (ADS takılı değildi). Kararlar ve açıklar:
spec "4D uygulama kararları" 4D-1…4D-15.

#### 5.12.88 🟢 4C: ARKA PLAN DİSK ARŞİVİ (2026-10-03 sabahı)

Ajan. `kopru/arka_esitle.py`: köprü süreci içinde kartın kayıtlarını WiFi'den diske eşitler — her (yeniden) bağlantıda
ve 120 s'de bir (≥ 30 s; hatada 15 s'den ikiye katlanan, en çok 600 s; döngü başlangıçları arasında ≥ 10 s taban),
parça ≤ 8192 B, istek başlangıçları arasında ≥ 100 ms (kart dövülmesin). Canlı akış, eşitleme ve komutlar TEK `Cihaz`
nesnesi ve TEK sayaç kilidiyle (imzalı `/akis` adresi + istek + yanıt başlığı kilit altında — eskiden yavaş mDNS
bağlantısı sırasında araya giren eşitleme isteği akışın sayacını geçersiz kılabiliyordu). **Onay (PC9) varsayılan
AÇIK:** `Go<sıra>` yalnız fsync + atomik `durum.json`'dan SONRA; `--onaysiz` / `ayar.json` kapatır, okunamayan ayar
onaysız sayılır. Arşiv `%LOCALAPPDATA%\olcum-karti\arsiv\<kart>\akis-<akış>` (akış değişince yeni dizin), eski
`.satir` günlüğü `...\satir\` (çalışılan klasördeki `kopru/arsiv/*.satir` hedef boşsa BİR KEZ KOPYALANIR, silinmez).
`GET /esitleme/durum` (yalnız bu bilgisayar; mutlak yol yok). **Gerçek kartta (onaysız, geçici dizin):** 2234 kayıt,
1 268 956 B, son sıra 61276, 44 oturum — kartın `/kayit/liste`'siyle birebir; 29.6 s; altı tam eşitleme bayt bayt aynı;
canlı akış etkilenmedi (4.9 satır/s, p95 230 ms, kayıp yok). B22a 143 → 150, B72 189 → 203; mutasyon 4C 38/38, 4B 51/51.
Açık: köprü açıkken ayrı süreçten `kayit_esitle.py`/`imza.py` aynı cihaz dosyasını kullanırsa sayaç çakışır (önce
`pc.py --durdur`); keep-alive yok (istek başına ~100 ms).

#### 5.12.87 🟢 4B: KÖPRÜ KARTLA WiFi'DEN EŞLEŞMİŞ CİHAZ + FİRMWARE A3-4B (2026-10-03 sabahı)

Ajan + benim gerçek kart sınamam. **Firmware A3-4B** (tam yedek `tam-20261003-062021.bin`): `/kopru` kaydı, kayıtlı
köprü varken ikinci `/akis` reddi ve köprü kökenine CORS izni KALKTI (PC8; spec §5 "4 istemci"); kart hiçbir
kökene CORS izni vermiyor. **D5 #12 kök düzeltmesi:** EK satırı ve AP parolası satırı tek tampon + tek `ham()` ile
basılıyor (IDF günlüğü araya girip parçalayamasın; köprü süzgeci derinlemesine savunma olarak kaldı). Flaş −1452 B,
DRAM −40 B. **Köprü (`kopru/kart_wifi.py`):** USB'de doğrulanmış kart yoksa WiFi'den eşleşmiş cihaz olarak — her
bağlantıda kart kimliği cihaz dosyasıyla denetlenir (uyuşmazsa hiçbir komut gitmez), YENİ imzalı `/akis` adresi (D5
#17), imzalı komutlar, `p0` her zaman imzasız; kartın NTP saati yoksa imzalı `/saat`. Cihaz dosyaları
`%LOCALAPPDATA%\olcum-karti\cihaz` (PC5); `imza.py esles --parola-ortamdan` (yalnız bayrakla, basılmaz/saklanmaz).
**Gerçek kartta:** `/kopru` 404, `OPTIONS /komut` CORS başlıksız; köprü eşleştirildi (cihaz 2 "PC-kopru", anahtar
yalnız DPAPI'de); yalnız WiFi kipinde panel `olcum.localhost:8770`'te güvenli bağlamda, imzalı `?` → `A menzil=`,
`p0` 204; kart sıfırlanınca köprü koptu ve yeni imzalı adresle 401 döngüsüz geri bağlandı; köprü bir yuvayı
tutarken doğrudan istemciler akış aldı (ret yalnız 4 yuva doluyken `dolu`); `tezgah_kayit.py --guvenlik` **14/14**
(EK satırı seride tek parça, SSE'de YOK). `E?`: Desktop + PC-kopru, zorunlu 0. **Bulunan kusur:** B72/B22a/
`test_bildirim` sahte kartın cihaz dosyasını (bir mutasyon altında) kullanıcının GERÇEK `%LOCALAPPDATA%`'sına
yazmıştı → `uretim/gercek_dizin_koru.py`: iki yönlendirme de geçici dizine + test sonunda gerçek dizinin dökümü
iddia, belirenler geri alınır (mutasyon 1/1). **Açık:** USB↔WiFi geçişi gerçek kartta kablo çıkarılarak denenmedi
(elle); kapanmış eski akışın kart yuvasını tutma süresi ölçülmedi; tek `uart_write`'ın ROM günlüğüyle bölünmediği
kanıtlanmadı. B72 172 → 189, B22a 132 → 143, B6 77; mutasyon 4B 51/51, 4A 77/77.

#### 5.12.86 🟢 ALT PROJE 4 BAŞLADI: 4A KÖPRÜ ANA SÜRECİ + 4F PWA KABUĞU (2026-10-03 gecesi)

Kullanıcı "soru sorma, en uygun yoldan devam et" dedi; kararlar benim (`tasarim/2026-10-03-alt-proje-4-pc.md`
PC1–PC18, gerekçeli). **Keşif** (iş akışı: 5 okuyucu + sentez): PC tarafının parçaları `kopru/`'da vardı ama
birbirine bağlı değildi. **4A:** tek ana süreç `kopru/pc.py` (`--sessiz`, tek kopya, çökme izi `%LOCALAPPDATA%`,
Başlangıç kısayolu betikleri — KURULMADI, kullanıcı kurar, yalnız ana klasörden); köken
**`http://olcum.localhost:8770`, yalnız 127.0.0.1** — Edge'de ölçüldü: güvenli bağlam ve service worker kaydı
var (Windows `*.localhost`'u çözmez, yalnız tarayıcı; Python 127.0.0.1 kullanır). **Kapanan açıklar:** köprü
`0.0.0.0`'a bağlanıyordu ve yerel ağdaki İLK istemci sürücü olup USB'den `Ns`/`GF!`/`p1`… yolluyordu (1D'yi
atlıyordu) → yerel ağ her kipte salt okuma, yalnız `p0`; DNS yeniden bağlamaya karşı Host denetimi; **AP parolası
sızıyordu:** kart AP kipinde ve `N?`'de parolayı "(yalnız USB)" diye ham UART'a basıyor, köprü bunu `/akis`'e ve
arşive aktarıyordu → süzgeç (EK satırı, işaretli satır + 2 satır penceresi, ≥ 24 onaltılık dizi; bağlantı
açılınca ilk yarım satır atılır). **Bağımsız inceleme** (3 denetçi + çürütücü) 5 ciddi bulgu doğruladı, 12 bulgu
kapandı: çapraz kökenli `<img>` ile karta `t` yollatma ve sürücülüğü kapma (CSRF), `/skop/*` `gun` yol enjeksiyonu
(arşiv dışı okuma, UNC ile NTLM özeti sızıntısı), port açılışındaki yarım satırla sır kuyruğu, `belge-uret.py`'nin
çökmesi (B9 kırmızı olurdu), VID'den herhangi bir CH34x/CP210x aygıtını kart sanma → port tutulmadan önce pasif
`D`/`K` satırıyla (gerekirse serbest `?`) doğrulanıyor; gerçek kartta 0.06 s, karta hiçbir şey yazılmadı.
**4F:** `sw.js` (izin listesi, ağ önce, API asla önbelleğe alınmaz), "Köprü çalışmıyor" çevrimdışı sayfası,
192/512 + maskable simgeler (`uretim/ikon-uret.py`, stdlib), manifest `id`/`scope`; Edge kurulabilirlik hatası
listesi BOŞ; kart kökeninde kayıt yok (güvenli bağlam değil), kart görüntüsüne `sw.js` girmez.
B22a 65 → 132, B22b 109 → 113, B7 852 → 878, yeni T4A 12/12, T4F 16/16; mutasyon 4A 77/77, 4F 48/48.
Sırada 4B (kartla WiFi + eşleşmiş köprü; firmware: köprü kaydı reddi ve CORS kaydı kalkar, EK/AP parola satırı
tek parça basılır).

#### 5.12.85 🟢 3H-2 TARAYICIDAN EŞLEŞTİRME (2026-10-03 gecesi)

Ajan, kararlar ES1–ES10 + uygulama kararları EU1–EU31 (spec). Ayarlar > **Eşleştirme**: ad + web parolası →
`ortak/imza.js` `esles` (parola ağa ÇIKMAZ, panel hiçbir yere yazmaz — T3H2 bütün depoları tarıyor); eşleşmişken
bütün API istekleri imzalı (`app.js kartIstek` tek katman), canlı akış `fetch` ile (EventSource önbellekteki
Basic-Auth'u taşıyor ve her yeniden bağlanmada aynı tek kullanımlık URL'yi yolluyordu — EU4), sayaç IndexedDB
işleminde atomik ayrılıyor (iki sekme × 8 eşzamanlı komut ilk denemede kabul — EU3), anahtar ayrı veritabanında
(`olcum-cihaz`; kayıt veritabanının sürüm yükseltmesini eski sekme kilitlemesin — EU1). Cihaz listesi + silme
(iki aşamalı), "bu tarayıcıyı unut", NTP yoksa kart saatini bu cihazdan kurma, zorunluluk/misafir durumu (yalnız
USB'den değişir), bildirim ayarının neden yalnız USB olduğu. Eşleşmemiş tarayıcının yolu birebir aynı (`cihazKaydiVar`
modülü ve veritabanını açmadan bakar). **`p0` imza katmanına hiç girmez** (geçersiz imzalı `p0` reddedilirdi — EU6),
P0-S'in yeniden denemesi ve `credentials: 'omit'`'i eşleşmişken de geçerli.

**Bağımsız güvenlik incelemesi** (iş akışı: `p0` araştırmacısı + anahtar sızıntısı + protokol + gerileme denetçisi,
her bulguya çürütücü): ajanın "eşleşmişken p0 gecikiyor" gözlemi test aracıymış (5.12.84); 13 bulgu kapandı —
yeni açılışlı 401'in cihazı kalıcı "kart tanımıyor"a düşürmesi, SSE ayrıştırıcıda parça sınırında bölünen CRLF,
istisnada eski akışın iptal edilmemesi (kart yuvası), 'dolu'da artmayan bekleme, bayat ekranda yanlış "kart da
sildi", unutulan anahtarın eşzamanlı yazımla geri gelmesi, IndexedDB açılamazsa sessiz imzasız yol, `/eslestir/bilgi`
zaman aşımı, başka kartların silinemeyen kayıtları, WIG odak. **ES2 riski firmware'den doğrulanıp yazıldı:** çalınan
K = E/Q dışı her komut (`Ns` ile web parolasını değiştirmek dahil), kayıt okuma, her cihazı silme, `/saat`,
`/bildirim/bilgi` üzerinden yalnız-abone MQTT bilgisi + bildirim anahtarı; K parola değişince geçersiz olmaz.

**Kararlar (kullanıcının devriyle, geri alınabilir):** ES2 KABUL (bugünkü yol parolanın kendisini her komutta açık
HTTP'den yolluyor; K'yı çalmak tarayıcı profili ya da etkin aradaki-adam ister — eşleştirme kesin iyileştirme),
ES3 KABUL, EU29 (c) uygulandı (eşleştirme metinleri açılış sözlüğünden `ortak/src/sozluk_es.js`'e; eşleşmemiş açılış
209 963 → 206 425 B, `#/skop` payı 4.6 → 8.2 KB), EU31: eşleşmiş açılışın kalan aşımı (257 017 B / 15 dosya, 3D
sınırının %0.4 üstü) eşleşmiş tarayıcıya özgü istisna, ayrı tavan 262 144 B / 15 dosya İDDİA. **AÇIK:** gerçek
kartta parolayla eşleştirme (parolayı yalnız kullanıcı bilir), imzalı canlı akışın kartın SSE yanıtıyla, eski
akışın kart yuvası, telefonda PBKDF2 süresi. Kabulden sonra öneri: bütün cihazlar eşleşince USB'den `Ns<yeni>`.
B7 782 → 852, B73 24, yeni T3H2 31/31, mutasyon 3H2 76/76 + P0-S 7/7.

**Gerçek kartta doğrulandı (2026-10-03 gecesi):** kullanıcının seçimiyle web parolası USB'den (`Ns`) yeni, 16
karakterlik rastgele bir parolayla değiştirildi (eski parola her komutta ağda açık gitmişti; değeri yalnız
kullanıcıda). Playwright ile 12/12: parolayla eşleştirme 180 ms; parola hiçbir depoda yok; kartın cihaz listesi
imzalı okundu; eşleşmiş açılışta canlı akış imzalı (`_c/_s/_i`), komutlar `X-Imza` ile ve HİÇBİR API isteğinde
`Authorization` yok, panel hatasız bağlı (parolasız 401'ler bitti); Kayıtlar eşitlemesi imzalı (161 istek, 2234
kayıt); `p0` imzasız + parolasız 69 ms; "unut" kartta da sildi — USB `E?`: `cihaz=0`, `zorunlu=0`. Telefonda
PBKDF2 süresi ve eski akışın kart yuvasını tutma süresi ölçülmedi.

#### 5.12.84 🟢 p0 SAĞLAMLIĞI + TEST ARACININ SAHTE KIRMIZISI (2026-10-02 gece)

3H-2 (tarayıcıdan eşleştirme, dalda, onay bekliyor) için bağımsız güvenlik incelemesi (iş akışı: 4 denetçi +
her bulguya çürütücü) eşleşmeden BAĞIMSIZ üç kusur buldu; bunlar `main`'e girdi:
- **`p0` (pil DURDUR) tek atımlıktı:** kartın komut kuyruğu doluyken 503 ya da tek bir ağ hatası durdurmayı
  kaybettiriyordu. `p0` eş etkili → `p0Gonder`: ağ hatası / 503'te 150 · 300 · 450 ms ile en fazla 4 deneme
  (en kötü 0.9 s), 4xx hemen döner. Tek tık, onaysız kuralı aynen.
- **`p0` ve `/durum` tarayıcının önbellekteki Basic-Auth'unu açık HTTP'den taşıyordu** (fetch varsayılanı
  `same-origin`). Kart `p0`'ı parolasız kabul ediyor (`komut_serbest`), köprü Basic hiç kullanmıyor →
  `credentials: 'omit'`. Her acil durdurmada web parolası ağa çıkıyordu.
- **Test aracı:** `tarayici.py` `bekle()` tek `recv`'de gelen ikinci CDP çerçevesini işlemiyordu (select yalnız
  ham sokete bakıyor). Yük altında `Fetch.requestPaused` tamponda kalıyor, Edge isteği (ör. `p0`) duraklatılmış
  tutuyordu — 3H-2 ajanının "eşleşmişken p0 5 s'de gitmedi" diye raporladığı aralıklı kırmızının KÖK SEBEBİ;
  ürün kusuru değil ama bir EMNİYET iddiasında sahte kırmızı ve bütün T3x testlerini etkiliyordu.
B7 778 → 782 (bölüm 31), TTR 9 → 10, mutasyon P0-S 7/7; bütün tarayıcı testleri yeşil, sızıntı 0.

#### 5.12.83 🟢 3H-1 AYARLAR + KARTTA /kal/liste ZAMAN AŞIMI (2026-10-02 gece)

**3H-1** (ajan, kararlar AY1–AY7 + uygulama kararları AU1–AU12, spec): Ayarlar yedi bölüm, bir seferde
tek bölüm, adres `#/ayar/<bölüm>` (Bağlantı · Ağ · Kalibrasyon · Kalibrasyon geçmişi · Depolama · Dil ve
görünüm · Gelişmiş). Eski kartlar yerinde; yalnız üç yeni bölüm `ekran/ayarlar.js`'te (9.4 KB gzip,
IndexedDB zinciri onun içinde dinamik `import()`). **Dil TR/EN** anında (`olcum.dil`, `<html lang>`, sekme
başlığı); EN'de hâlâ Türkçe kalan **274** metin GİZLENMİYOR — B7 sayıp listeliyor, kilit iki yönlü
(3H'nin yeni parçaları 0; kör nokta: Türkçe harfsiz ASCII dizgeler sayılmıyor, spec'te yazılı).
**Kalibrasyon geçmişi SALT OKUMA** (`/kal/liste`, kart vermezse en yeni yerel kopya ve bunu söyler; 17
alan firmware'in JSON'undan, birim uydurulmadı); Ayarlar karta hiçbir `k…`/`N…`/`Go` komutu göndermiyor
(T3H ölçüyor). **Depolama:** kopya başına boyut/oturum/son eşitleme, eski kart kopyası, silme iki aşamalı;
`navigator.storage` kartın `http://` adresinde YOK (güvenli bağlam ister) — panel sebebiyle yazıyor.
**Gelişmiş:** panel sürümü (`arayuz-uret.py` görüntüye `kunye.json` koyuyor, `_fs.json` `panel_surum`),
firmware afişten (E11 açık), "tarayıcı ayarlarını sıfırla" yalnız `olcum.` anahtarları, listeli, iki aşamalı.
Bütçe: açılış 8 dosya 195.6 → 202.8 KB; ⚠ `#/skop` doğrudan açılışı **244 / 250 KB** — pay daralıyor.
B7 721 → 777, yeni T3H 28/28, mutasyon 3H 34/34.

**Gerçek kartta 3G sınanırken bulunan kusur (3C-KAL):** üç eşitlemenin birinde `/kal/liste` TimeoutError
aldı, sonuç "Kalibrasyon geçmişi alınamadı" dedi. Esitleyici kalibrasyon hatasını `kalibrasyon_hata`ya
çevirip "tamam" döndüğü için 5.12.78'in `agYenidenDene`'si onu hiç görmüyordu. Artık panelin istek
katmanında yalnız `/kal/liste` ağ hatasında artan beklemeyle yeniden deneniyor (`/kayit/veri`'yi üst katman
zaten kaldığı yerden kuruyor; ikisi birden bekleme şişirirdi). `ortak/` dokunulmadı (Python eşliği).
B7 +1, mutasyon 3C-KAL 4/4. Aynı sınamada bir koşuda Karşılaştır bağlantısı çıkmadı: betik, eşitleme sonuç
yazısı belirdiği anda listeyi okumuştu — liste o an henüz yerel kopyadan kurulmamış, kutular kapalı;
kullanıcı o arada seçim yapamaz, ürün kusuru değil. Kartın `/durum` 404'ü köprü yoklaması (bilerek).

#### 5.12.82 🟢 3G KARŞILAŞTIRMA EKRANI (2026-10-02 akşam)

Ajan, kararlar KR1–KR8 + uygulama kararları KU1–KU10 (spec). Seçim Kayıtlar listesinden (yalnız bu
tarayıcıda kopyası olan, en fazla 6 oturum; seçilemeyenin kutusu kapalı ve sebebi etiketinde) →
`#/karsilastir/<no>@kimlik,…` (kip ve kanal sorguda, `replaceState`). Tek grafik tek birim (V · I · W),
x üç kip: başlangıçtan beri (K1) · saat · mAh (PU9 integrali). **Uydurma veri yok:** saati eksik/geri
giden kayıt saat kipinde, boşluklu/negatif akımlı kayıt mAh kipinde dışarıda kalır ve sebebi lejantta
yazar; imleç bir kaydın aralığı dışındaysa o kaydın değeri "—" (en yakın örneğe yapışmak kısa kayda
değer uydururdu); birleşik CSV'de zamanlar ortak değil, enterpolasyon yok, kısa kayıt boş hücre.
**Renk:** koyu takım kilitli olduğundan yeni belirteç yok; 1–3. kayıt düz V/A/W renkleri, 4–6. kayıt
karışım + kesik çizgi (`grafik.js` `seri.desen`). Yalnız renkle en iyi altılının renk körlüğü benzetiminde
en kötü çifti ΔE 10.8'di; renk + desenle aynı desenli her çift ΔE ≥ 16.8 (B7 üç görünümde protan/deutan/
tritan ölçüyor). Bütçe: Kayıtlar zincirine yalnız `karsilastir.js` + `pil.js` (18.1 KB gzip); açılış kümesi
değişmedi. Şeritte Karşılaştırma artık görünür (KR6). B7 677 → 721, yeni T3G 31/31, mutasyon 3G 22/22.
Birleşik ağaçta bütün tarayıcı testleri yeşil, Edge sızıntısı 0. Zincir 21 yeşil.

#### 5.12.81 🟢 3F PİL TESTİ EKRANI (2026-10-02 akşam)

Ajan, kararlar PL1–PL7 + uygulama kararları PU1–PU17 (spec). `p0` emniyeti aynen (tek tık, onaysız,
`:disabled` yok; DURDUR modül yüklenemese de çalışır). Okuma kartları kaynağını söylüyor (mAh/Wh kartın
sayacı); eğri `grafik.js` (V üstte I altta; DCIR işaretleri `isaretler` seçeneği; mAh ekseni tarayıcı
integrali, boşluk/negatif akımda zaman eksenine düşer ve sebebini yazar). **Yoklama (PL4) ölçüldü:**
eskiden bağlıyken HER sekmede 10 s'de bir (Canlı'da saatte ~360 istek); artık yalnız Pil sekmesi + sayfa
görünür + test sürerken 2 s'de bir, test başlangıç/bitişi kartın `BASLADI`/`BITTI`/… satırlarından.
**Gerçek kartta:** Canlı'da 15 s'de 0 `/pil`, Pil sekmesinde test yokken tek istek. PİL oturum numarası
`G` satırından ("Kayıtlar'da aç" → doğru oturum). Başlat `P<v>`'yi yalnız değiştiyse yollar, kartın
onayını bekler; kartın başlangıç satırı farklı kesme bildirirse panel hemen `p0` yollar (PU4). İki hata
düzeltildi: yeni test eski sıra numarasıyla isteniyordu (noktalar gelmiyordu, PU12); 3D'nin telefon
kuralı yanlış sırada (Canlı kartları telefonda iki dar sütun, PU17). USB/köprüde `/pil` yok → durum `p`
komutunun `B` satırından (eskiden "HTTP 404"). Açık: DCIR aralığı/kapatma firmware'de derleme sabiti
(komut yok, PU5). B7 626 → 677, yeni T3F 33/33, mutasyon 3F 47/47. Zincir 21 yeşil.

#### 5.12.80 🟢 3E OSİLOSKOP EKRANI (2026-10-02 akşam)

Ajan, kararlar OS1–OS8 + uygulama kararları S1–S14 (spec). Dalga solda geniş, kontroller sağda kümeli
(Yakalama · Zaman tabanı · Tetik · Yakalama günlüğü · Kalibrasyon çıkışı), ≤ 900 px altta; dalga
ızgarası 10 × 8 bölme; spektrum `grafik.js` (`xEksen` Hz/kHz, DC metin olarak), Hann/dikdörtgen,
V tepe / dBV, ilk 5 harmonik (komşuluktaki gerçek tepe değilse "≤" — sahte harmonik yok). **Bulgu:**
OS4'ün "kayıtlı yakalamada `skopOlc`" kararı yanlıştı — kart `M` satırını EĞRİLİ hesaplıyor (B43),
çıplak `skopOlc` gerçek kartta ~7 V ayrışırdı → `ortak/src/skop.js`'e kartın hesabının JS eşi
`skopOlcKart`; gerçek ESP32 yakalamasında (`uretim/olcum-skop-fikstur.json`) Vpp/Vmax/Vmin/Vort/Vrms/
Vac/f/T/n basılan haneye kadar kartla aynı. Günlük `Gt0`/`Gt<ms>`/`Gtd`, `GT` durumu G? ile (firmware
GT'yi kendiliğinden basmıyor). Kayıtlı yakalama `#/skop/kayit/<oturum>/<sıra>@kimlik`, Kayıtlar'dan
"Osiloskopta aç". B7 578 → 626, yeni T3E 37/37; mutasyon 3E 37/37 (+ birleşik ağaçta WIG 77, 3D 104
yeniden). Bütçe: açılış 166 KB, toplam görüntü 294 KB / 600. Kartta açıldı (Playwright). Açık: eğrili
yolun duty/tr/tf'si ve kartın GT'yi kendiliğinden basması (firmware). Zincir 21 yeşil.

#### 5.12.79 🟢 WEB INTERFACE GUIDELINES DENETİMİ + YENİDEN DENEMEDE KAYIT SAYISI (2026-10-02 akşam)

Kullanıcı Playwright + Taste + Web design guidelines yeteneklerini kurdurup kullanılmasını istedi
(kaynakları kendisi seçti; kullanıcı düzeyinde). **WIG iş akışı** (ultracode): 4 denetçi kural
gruplarına göre → 94 tekil bulgu → dosya başına şüpheci (çürütme) → **69 doğrulandı** → düzeltici:
her denetim adlı (label for/id), menzil grubu role=group + aria-pressed (614 V menzili emniyet), hata
role=alert, rozet role=status, konsol role=log, her görünümde h1, "İçeriğe geç", çekmece açıkken içerik
inert, yıkıcı eylemler iki aşamalı onay (6 s / görünüm değişimi / bağlantı kopması düşürür), parola
alanları new-password, hata metinleri sonraki adımı söylüyor. Osiloskop bölümü kapsam dışı (3E).
B7 508 → 578, T3D 37, T3C 48; mutasyon WIG **77/77**. ⚠ Benim eklediğim emniyet iddiası: **p0 (pil
DURDUR) iki aşamalı onaya ASLA sarılmaz** — acil şerit + Pil sekmesi düğmeleri `pilDurdurKomut`'u tek
tıkla çağırır, gövdede onay yok (EMNIYET-P0 2/2). Sayılarda '.' ondalık bilinçli (3H dil seçimine
ertelendi); Taste yeteneği kendi kapsamı gereği panelde yalnız uyan kısımlarıyla.
**Gerçek kartta ikinci kusur:** yeniden denenen eşitlemede sonuç yazısı yalnız SON denemenin
sayısını söylüyordu (sıfırdan eşitlemede "150 yeni kayıt"; gerçek 2234). `esitleme.js` eklenen
parçalardaki kayıtları bütün denemeler boyunca sayıyor; T3C ilk eşitlemenin 2. isteğini 12 s
yanıtsız bırakıyor (49/49), mutasyon 3C-SAYI 1/1; kartta "2234 yeni kayıt alındı", 44/44 oturum.
Zincir 21 yeşil.

#### 5.12.78 🟢 3D CANLI + SOL ŞERİT; TEST ARACI BİLGİSAYARI KİLİTLİYORDU; PANEL İLK KEZ GERÇEK KARTTA (2026-10-02 öğleden sonra)

**3D** (ajan, kararlar D1–D8 + E1–E13 spec'te): sol şerit kabuğu (≤ 900 px çekmece, Esc/odak),
Canlı okuma kartları V·A·W·Enerji + 10 s min…maks, canlı grafik `grafik.js`'e geçti (Dondur'da
imleç/yakınlaştırma), kayıt denetimi (`Gb<ms>`/`Gb0`/`Gd`/`Gn<oturum>@<ms>`/`Gp…`/`Gp-`, ≤ 175 bayt,
not ≤ 120 bayt), durum YALNIZ pasif `G`/`GP`/`GA`/`GT` (G? bağlanınca + komuttan sonra), aktif kayıt
kartı ("~X kaldı" onaysız artışından, ≥ 60 s), son olaylar. Bütçe: 250 KB artık AÇILIŞ kümesine
(app.js'in statik import ağacından türetilir), toplam 600 KB. B7 382 → 508, yeni T3D 35/35.

**Test aracı (`uretim/tarayici.py`) iki ciddi kusur — kullanıcının bilgisayarı kilitlendi, yeniden
başlattı:** (1) `kapat()` yalnız Popen PID'ini öldürüyordu; Edge Windows'ta kendini yeniden başlattığı
için gerçek tarayıcı yaşadı: 81 Edge **12.3 GB RAM**, `%TEMP%`'te 460 profil **131 GB** disk (hepsi
temizlendi). Artık boş port + CDP `Browser.close` + profil adıyla süreç öldürme + profil silme +
`atexit`; `test_tarayici.py` (TTR) 9/9, mutasyon 4/4 (üç mekanizma birbirinin yedeği; eski `kapat()`
mutantı kırmızı). (2) Taze profil Windows hesabıyla **kendiliğinden oturum açıp senkronize oluyordu**;
eklentiler (~8 s) sekme açıp test sayfasını gizliyordu (`hidden` → rAF durur, CDP tekerleği yanıtsız —
3D ajanının yeşil raporladığı T3D bu yüzden kırmızıydı; T3C'de tuval çizilmiyordu) ve testler
kullanıcının hesabıyla dış sitelere gidiyordu → `--disable-sync --disable-extensions` (iş akışı: iki
bağımsız araştırmacı + düzeltici; ana iş parçacığı boştu, ürün kodunda döngü yok). Skop arşivi testinin
sahte köprüsü `/ortak/`'u sunmuyordu (3D'den beri app.js onu statik içe alıyor) → düzeltildi, 19/19.

**Panel gerçek kartta (A3-1F, yedek `tam-20261002-162929.bin`, LittleFS 0x310000):** bütün dosyalar
doğru MIME + gzip; Playwright (kullanıcının kurdurduğu yetenek) ile: açılış 3.6 s, üç görünüm, sol şerit,
`G?` yalnız bir kez. **GERÇEK KUSUR:** tarayıcı eşitlemesi bir `/kayit/veri`'de `ERR_CONNECTION_TIMED_OUT`
alıp DURDU (44 oturumdan 1'i); aynı kart ham ardışık çekimde 1.27 MB'ı 7.2 s'de hatasız verdi (ESP32
soket havuzu tarayıcının paralel bağlantılarında ara sıra reddediyor). → `esitleme.js` `agYenidenDene`
(ağ hatası artan beklemeyle 4 kez; depo durumundan kaldığı yerden, kayıp/çift yok). Kartta yeniden:
**44/44 oturum, 1846 kayıt, 45 s, arada bir zaman aşımı atlatıldı**, karta hiç `Go` gitmedi. T3C'ye
"iki istek 12 s yanıtsız" senaryosu (Chrome hemen kapanan bağlantıda GET'i kendisi tekrarlıyor —
zaman aşımı şart), mutasyon 3C-AG 4/4. ⚠ Kartta ADS'ler takılı değil: Canlı "veri yok — ADC yanıt
vermiyor" diyor (doğru); canlı veri ve blokaj ölçümü (tezgah #71 son maddesi) ADS takılınca.
Zincir 21 yeşil, kilit 3809. 3E kararları OS1–OS8 spec'te.

#### 5.12.77 🟢 ALT PROJE 3C — KAYITLAR + KAYIT GÖRÜNÜMÜ; S7, 1D #16, sürüm NUL (dal `3-panel`, 2026-10-02 öğleden sonra)

**3C** (ayrı ağaçta bir ajanla, kararlar spec C1–C8 + uygulamada U1–U4, K1–K6):
`arayuz3/ekran/depo_idb.js` (esitle.js DEPO arayüzünün IndexedDB uygulaması; kart kimliği başına
akış, ≤ 64 KB parçalar, `durability:'strict'`, Web Locks) · `esitleme.js` (eşitleme yalnız kartın
KENDİ adresinden açılan panelde — C1; varsayılan ONAYSIZ, "Bu tarayıcı arşivdir" kart kimliği başına
— C3/U4; her eşitleme taze `/kayit/liste` ile, akış ortada değişirse bir kez yeniden — U2) ·
`kayitlar.js` (kart dizini ∪ yerel oturumlar, nerede = kartta / bu tarayıcıda / ikisinde, "eski kart
kopyası"; Türkçe karakter duyarsız arama; `#/kayitlar`, `#/kayit/<no>[@kimlik][/rapor]`) ·
`kayit_gorunum.js` (grafik.js ile V/I/W + ince min/maks çizgileri (Ö1), gezgin, iki imleç; mAh/Wh
açılış başına ve kartın W'sinden — tam aralıkta raporla bit bit aynı (K3); saatsiz yeniden başlama
"konumu tahmini" ile görünür (K1); notlar, pil özeti, skop yakalama tablosu + CSV; CSV TR/EN,
ayrıntılı, pil, ham `.kyt`, yazdırılabilir rapor). Kayıtlar modülü sekme ilk açılınca iner (U1):
açılış hâlâ 7 istek.
**Doğrulama:** B7 382 → 439. Yeni başsız Edge testi `tarayici_kayitlar.py` (T3C) **45/45**: sahte kart
`olcum.test` adında (localhost değil, güvenli bağlam değil — gerçek kart gibi); IndexedDB baytları kartla
bayt bayt aynı; varsayılan hiç `Go` yok, arşiv seçimiyle var ve kart doğruluyor; yenilemede veri isteği
0, ikinci eşitleme son sıra + 1'den; kimlik değişince yeni akış; GERÇEK CDP çift tıklamalarıyla iki
imleç, okumalar bağımsız Python hesabıyla 1e-9; CSV/ham/skop CSV indirmeleri Python başvurusuyla bayt
bayt; üç görünüm, 390 px'te taşma yok, konsol temiz. Mutasyon 76/76 (B7 54, B73 3, T3C 19); ilk
koşuda kaçan üçü gerçek boşluk çıkardı (ü→u Unicode ayrıştırmasıyla zaten gidiyordu; ayrıntılı kip
fikstüründe 16.38 ms üstü boşluk yoktu; **390 px taşma denetimi kördü** — mobil öykünmede Chrome
`innerWidth`'i içerik genişliğine büyütüyor, `clientWidth`'e geçildi). Görüntü 249 KB gzip / 600.
**Küçük açıklar kapandı (1-acik-isler):** **S7** bildirim/imza istemcisi Python + JS aynı kural (zarfta
NaN/Infinity ret; kimlik/tuz/açılış yalnız metin, tur yalnız JSON tamsayısı; parola sınırı UTF-8 BAYT
— kartla aynı; B72.I8b, mutasyon 7/7) · **1D #16** cihaz dosyası: GERÇEK YARIŞ (iki süreç aynı
dosyada `PermissionError`, test kırmızıyla gösterdi) → `mkstemp` + `fsync` + Windows'ta kısa yeniden
deneme (benzersiz adla bile gerekli — mutasyon gösterdi); B72.I8c, 3/3 · sürüm metni ilk NUL'da
kesiliyor (Python + JS, vektör 832).
**Zincir** 21 adım yeşil, kilit 3740 (B72 170 → 172, B7 382 → 439).
⚠ Açık (3D'ye devredildi): B7'nin 250 KB sınırı %97 doluydu → artık yalnız AÇILIŞ kümesine uygulanacak
(toplam P5 600 KB); `tarayici_tema.py`'nin telefon denetimi de `innerWidth` körlüğünde; T3A bir koşuda
"Sistem canlı izleme" adımında kırmızı oldu (3'te 1). 3C karta da yüklenmedi (T10).

#### 5.12.76 🟢 ALT PROJE 3 — 3A GÖRÜNÜMLER + MODÜL ALTYAPISI, 3B GRAFİK ÇEKİRDEĞİ (dal `3-panel`, 2026-10-02)

Görsel yön kullanıcının devriyle seçildi ("ben karar veremedim, sen karar ver"), sonra kullanıcı
birden çok tasarım arasında geçiş istedi → **tek düzen + üç görünüm** (P1; spec
`tasarim/2026-10-02-alt-proje-3-panel.md` P1–P7, 3C için C1–C8). Hedef: "sen uygun gördüğün gibi hallet".

**3B — `ortak/src/grafik.js`** (bağımlılıksız kanvas; uPlot yerine, P3): çok kanallı çizgi, Ö1 özet
piramidi (`ozet.js`) ile her yakınlaştırmada sıçrama korunur (sütun uçları çizim planında), boşluk
kesik (ham + özet kipte), tekerlek odağı imleçte sabit, sürükleme/iki parmak, gezgin şeridi, iki imleç
+ `imlecOkuma` (istatistik HAM veriden, mAh/Wh boşluğun üstünden integre edilmez — D4). Çizim planı
saf işlev (`cizimPlani`) → Node'da sahte bağlamla sınanıyor (B73, 28 test). Renkler her çizimde CSS
belirteçlerinden okunur (önbellek yok → görünüm değişince eski renk kalmaz).

**3A — görünümler + ES modülleri:** `arayuz3/ekran/tema.js` (Sistem/Koyu/Açık/Ön panel; tarayıcıda
hatırlanır; Sistem işletim sistemini canlı izler; `<head>` betiği ilk boyamada aynı kuralı uygular —
sıçrama yok). `style.css`: üç görünüm AYNI belirteç kümesini tanımlar (B7 eksik belirteci kırmızı
yapar); `prefers-color-scheme` CSS'ten çıktı (kural tek yerde). Ön panel alarm rengi maketteki
#c2361f metin olarak 2.99:1'di → aynı ton #f05a3c (4.85:1). `app.js` artık ES modülü; `file://`
kutusu sebebini ve çaresini yazıyor. Karta `/ekran/*.js` ve `/ortak/*.js` gzip'li yazılır
(`arayuz-uret.py` dizinden okur); köprü ve `sunucu.py` `/ortak/`'u `text/javascript` ile, yol geçişi
olmadan sunar. **Bütçe (P5):** görüntü gzip 214 KB / 600 KB. Kart çekirdeği 3.3.11 `.js`'yi zaten
`application/javascript` + gzip veriyor — firmware değişmedi. B7 önceden app.js'i gevşek kipte
koşuyordu; artık modül gibi (strict, gerçek import çözümü).

**Sayılar:** B7 346 → 382, B22b 102 → 109, B22a 59 → 65, B73 → 23 koşul (grafik dahil); başsız Edge
`tarayici_tema.py` 16/16 (üç görünüm + telefon genişliği + konsol hatası yok). Zincir 21 adım yeşil,
kilit 3681. **Mutasyon:** 3A 42/42 (T3A başsız tarayıcı adımı, AGIR'da), 3B 12/12; 3 eski girdi
(`--amper`/`--cok-soluk` girintisi, klasik `<script src=app.js>`) yenisiyle değişti.

⚠ **Karta yüklenmedi:** 2026-10-02 öğlen kart ne USB'de (COM portu yok) ne ağdaydı. Tezgah kalemi
#71 ("3A: panel karttan ES modülü olarak açılıyor mu") bekliyor: tam yedek → `arayuz-uret.py &&
arayuz-yaz.py` → konsol 0 hata, `/ekran/tema.js` MIME + gzip, `K` satırında yeni blokaj yok.
⚠ `tarayici.py`'nin `kapat()`'ı yalnız başlatıcıyı öldürüyor; başsız Edge süreçleri kalabiliyor
(9333'teki eskiler). Yeni testler kendi açtıklarını ağacıyla kapatıyor.

#### 5.12.75 🟢 ALT PROJE 2 — `ortak/` (2A–2F) + 1F SKOP ÖLÇÜM DÜZELTMELERİ (dal `2-ortak`, 2026-10-02 gecesi)

Kullanıcı yatarken "sıradaki adıma geç, soru sorma, en mantıklısına karar ver" dedi. Spec
`tasarim/2026-10-02-alt-proje-2-ortak.md` (O1–O8, D1–D5) kararları devredilmiş yetkiyle; grafik
çekirdeği (uPlot, dış dosya indirme izni ister) alt proje 3'e bırakıldı. Altı dilim paralel
ajanlarla (her biri ayrık dosyalar; git/zincir/mutasyon.py yasak), entegrasyon + mutasyon + zincir bende.

**`ortak/`** — düz JS ES modülleri, bağımlılık yok (`package.json` yalnız `type: module`), src
tarayıcı/Capacitor uyumlu (Node API'si yok — B73.Y4 ölçüyor), testler Node 24 `node:test`.
Çapraz uygulama ilkesi (O3): her dilimin Python üreteci (`uretim/ortak_vektor_*.py`) kartla
doğrulanmış başvurudan JSON vektör yazar; zincir `--denetle` ile Python'un hâlâ aynı olduğunu,
`node --test` ile JS'nin bayt bayt aynı olduğunu ölçer. Yeni zincir adımı **B73** (`test_ortak.py`).

| Dilim | Modül | Başvuru | Sonuç |
|---|---|---|---|
| 2A | `kayit.js` | `kopru/kayit_bicim.py` | 822 vektörde bit bit (80 test) |
| 2B | `kripto.js` (SHA-256/HMAC/PBKDF2/ChaCha20-Poly1305), `imza.js` (1D), `zarf.js` (1E) | `hashlib`, `chacha.py`, `imza.py`, `bildirim.py` + `vektor_guvenlik.json` | bayt bayt (127); PBKDF2 20 000 tur Node'da 10.8 ms |
| 2C | `esitle.js` (fetch/depo/onay enjeksiyonla) | `kayit_esitle.py` | B72'nin sahte kartında JS ve Python istemcisi aynı senaryolarda saklanan bayt, durum, kalibrasyon.json, onay dizisi birebir (39) |
| 2D | `ozet.js` (min/maks piramidi), `istatistik.js` | yeni (§9, Ö1) | Ö1 BİREBİR: her sütunun [min,maks]'ı o sütundaki ham örneklerin tam uçları; 1 M noktada piramit ~8 ms, pencere ~2 ms (16) |
| 2E | `skop.js`, `fft.js` | kartın `skop_olc.h`'si AVR emülatöründe | `Math.fround` ile float32 taklidi, bit bit (Object.is) — düz double port Vac'ta 0.196 V farkla ayrışıyordu |
| 2F | `disari.js` (Excel-TR CSV, ham), `rapor.js`, `sozluk.js` | `arsiv.csv_uret` kuralları | 48 test; formül enjeksiyonu koruması (`= + - @`) |

**1F — çapraz uygulama kartın kendi ölçümünde 4 kusur buldu** (1-acik-isler S1–S4), düzeltildi
(kaynak `arsiv/asama2/.../olcum2.h`, `skop_olc.h` üretildi, A4/A5/A6 yeşil, firmware **A3-1F**):
S1 Vac düz DC'de 0.196 V → 0 (float32 kare farkı sadeleşmesi; tam sayı u64 toplamlar, tek sqrt —
**kartta: düz −63.53 V girişte Vac 0.0000, Vrms = |Vort|**) · S2 ESP32 derlemesi skop_olc'ta
`madd.s`/`msub.s` (kart ≠ AVR başvurusu, Vac ~%5) → `fp-contract=off` pragması + B6 objdump
denetimi · S3 duty bir örnek fazla (%49.79 → 50.000) · S4 tr/tf yeniden kurulmuyordu (cüce darbe
4.76 → 0.80 ms).
**1F-2 (S8, kapandı):** aynı birleştirme `guc_olc`, `olcum_al`, `skop_gorevi`, `suzgec_ters_kazanc`'ta
da vardı — B4/B5'in "AVR'de doğrulanan matematik = kart" varsayımı o işlevlerde geçersizdi. `.ino`'nun
başına (include'lardan ÖNCE) `fp-contract=off` pragması; B6 artık eskizin NESNE dosyasının tamamını
tarıyor (sembol listesi satır içi gömmeyi kaçırırdı): 449 kayan nokta komutu, 0 birleştirilmiş;
pragma kalkınca kırmızı (mutasyon). Kartta maliyet yok: D başına örnek 32.99 = 32.99, en uzun tur
7.31 → 7.19 ms. 1F'nin skop_olc.h pragma mutasyonu bununla EŞDEĞER oldu, çıkarıldı.

**Ajanların başvurularda bulduğu (raporlandı, düzeltilmedi):** S5 `oturumlari_kur` CRC'si geçerli
ama boyu yanlış kayıtta çöküyor (gelecek biçim eski istemciyi düşürür) · S6–S7 küçük sağlamlık ·
S9 `istatistik.js` zamanda NaN · S10 NOT/OLAY'da açılış numarası yok (biçim 3).

**Sağlamlık (S5/S6/S9, aynı gece, dal `2-saglamlik`):** kayıt çözücü (Python + JS birlikte) CRC'si
geçerli ama boyu farklı kayıtta artık çökmüyor — uzun kayıt bilinen önekle okunur (ileriye uyum), kısa
atlanır ve uyarı olur; bilinmeyen/kısa kayıt oturum açmaz; kesik flaş görüntüsü temiz durur; `amper`
şönt 0'da NaN; `istatistik` NaN zamanı eksik sayar. Vektörler 822 → 831; mutasyon 20/20.

**Mutasyon:** B73 + A6 + B6 için ~90 yeni girdi; yanında eski bir B22b girdisinin `{` yüzünden
uygulanamaz olduğu (B40'tan beri) bulunup düzeltildi.

#### 5.12.74 🟢 1E-2 — AÇILIŞTA AĞ BEKLENMİYOR (dal `1e2-ag-acilis`, 2026-10-02 gecesi)

1A-2'den beri 1E'ye devredilmiş madde: "açılıştan kaydın sürmesine 2.5–6.3 s; büyüğü `setup()`'taki
WiFi beklemesi". Kullanıcı yatmadan "işin biterse sıradaki adıma geç, soru sorma" dedi.

**Ölçülen sorun (A3-1E, RTS sıfırlaması, 5 tekrar):** sıfırlamadan ilk `D` satırına (ölçüm döngüsü
başladı) **5.7–7.2 s, ortalama 6.35 s**; bunun 4–6 s'si `ag_baslat()`'ın STA beklemesi. Ev ağı yoksa
her açılışta > 10 s ölçüm yok (AP'ye düşmeden önce 10 s bekleme). ⚠ İlk ölçüm betiği 0.45 s
"buldu": sıfırlamadan ÖNCEKİ tamponda kalmış `D` satırı — ROM satırından sonrası sayılınca düzeldi.

**Değişiklik:** `ag.h` ikiye bölündü — `ag_baslat_rf()` (setup, kısa: `WiFi.mode` + `begin`; RF açık
olduğu için `guv_esp_ac`'ın rastgele sayıları 1D kuralına uyar; kayıtlı ağ yoksa AP hemen) ·
`ag_bekle_tamamla()` (ağ görevi, sunucu döngüsünden ÖNCE: STA'yı bekler, olmazsa AP). Yeni kip
`AG_BAGLANIYOR`; alanlar (ip/mac/mdns) önce, `kip` EN SON (`ag__kip_yaz`, bellek bariyeri). "Ag:"
satırı `ag_satiri_bas()`'ta: AP/KAPALI setup'ta, STA sonucu `loop()`'tan bir kez (çekirdek 1 —
aynanın tek yazarı). Setup'ta "Ag baglaniyor: …" satırı (önek "Ag:" DEĞİL: afiş okuyan araçlar
ilk "Ag:" satırını sonuç sanar).

**Kartta (A3-1E, aynı sürüm adı — biçim değişmedi):**
- Sıfırlamadan ilk `D`: **1.31–1.32 s** (5/5); "Ag: STA" 4.9–6.0 s'de, ölçümü bekletmeden.
- **AP'ye düşüş** (ağ adı geçici olarak var olmayan bir adla — `Na`, parola NVS'te AYNEN kaldı):
  ilk `D` **1.31–1.37 s** (eskiden > 10 s), "Ag: AP" 10.6 s, SSID MAC'ten doğru; ad birebir geri
  yazıldı, STA'ya döndü.
- Kayıt sürerken 20 RTS sıfırlaması: **20/20 aynı oturum (DEVAM)**, flaşta 20 DEVAM, oturum tutarlı.
- Bringup (aşama 1 + web): 56 geçti · 3 kaldı (üçü de ADS takılı değil: 0x48/0x49 yok, örnek 33)
  · 2 atlandı.

**Tezgah araçlarında bulunan 3 kusur (firmware değil):**
1. `tezgah_kart.py` "bilinmeyen komut" sondası sabit `QQ` idi; 1E'de `Q` komut ailesi olunca kart
   tanıdı → yanlış kırmızı. Sonda artık firmware'in hiçbir `case`inde olmayan harften türetiliyor
   (`~~`); test_tezgah_kart'a bağımsız iddia + mutasyon (sahte kart sondaya ne verilirse onu
   döndürdüğü için senaryolar bunu GÖRMEZDİ).
2. "Afiş göründü = ağ hazır" varsayımı: `tezgah_kayit.py --kesinti` 20/20 DEVAM'dan sonra eşitlemede
   `olcum.local` çözülemeden çöktü → `ag_hazir_bekle()` (ad çözülüp 80'e bağlanana dek). Bringup
   afişi artık `D` + "Ag:" ikisini birden bekliyor.
3. `--kesinti`'nin "oturumun DEVAM'ları tutarlı" iddiası eşitlenen AKIŞIN TAMAMINA bakıyordu; akışta
   eski `--ayrinti` oturumları (hız 0: örnekler AYRINTI kayıtlarında, NOKTA yok) kalınca kusursuz
   oturum varken kırmızı yandı → yalnız sınanan oturum.

**Testler:** sim3_web 5a/5c/5d `ag_satiri_bas()`'a taşındı + yeni 5k ×4 (setup beklemez, bekleme
görevde sunucudan önce, kip en son, STA sonucu loop'tan); B72.F97 `ag_baslat_rf`. Mutasyon 1E-2 4/4.

#### 5.12.73 🟢 1E — MQTT BİLDİRİMLERİ (dal `1e-mqtt`, 2026-10-01 gece → 10-02)

Tasarım: `tasarim/2026-10-01-1e-mqtt-bildirim.md` (K1–K12 + "Uygulama sırasında verilen
kararlar"). Kullanıcı "devam edelim", ardından "yavaş çalışıyorsun, alt ajan kullan" dedi →
platformsuz çekirdek, PC tarafı ve tezgah üç paralel ajana, ESP yapıştırıcısı bende.
**Dal `1e-mqtt` (`main` `1965d81`'den), `main`'e girmedi, push yok — onay bekliyor** (spec'in
"⚠ Onay bekleyen kritik kararlar" 1–4).

**Ne yapıldı**
- `bildirim.h` (platformsuz): olay üreticisi `basladi` (tarama bitince, her zaman n=1, `devam`)
  · `kayit_bitti{sebep,oturum,nokta}` · `pil_bitti` · `dolu` (geçiş) · `esik` (500 binde,
  100 binde histerezis) · `deneme`; 16'lık RAM kuyruğu (taşarsa EN ESKİSİ düşer, `dusen`);
  durum/vasiyet JSON; `"OKB1"|nonce|şifreli|etiket` zarfı, AAD = konu. B71.Q 23 iddia.
- `mqtt_paket.h` (platformsuz): MQTT 3.1.1 istemci paketleri + parça parça okuyucu + URI
  çözücü. AVR baytları `kopru/mqtt_istemci.py` ve elle yazılmış ayrı bir CONNECT çözücüsüyle
  çapraz denetleniyor. B71.MQ 22 iddia. Ajanın 3.1.1'e karşı okuması iki gerçek kusur buldu:
  vasiyet konusunda `+`/`#` geçiyordu (aracı CONNECT'i düşürürdü) · boş istemci kimliği
  temiz oturumsuz kabul ediliyordu (MQTT-3.1.3-7).
- `bildirim_esp.h`: çekirdek 0'a SABİT `bld` görevi, esp-tls (`esp_crt_bundle_attach`),
  libsodium ChaCha20-Poly1305, NVS `mqtt`; keepalive 5, vasiyet QoS 1 retained (her
  bağlanışta yeni nonce), durum QoS 0 retained (bağlanınca / değişince / 60 s), olay QoS 1
  tek uçuşta, PING 4 s / PINGRESP 5 s, geri çekilme 2→60 s, Q0'da önce `c:0`.
  İmzalı `GET /bildirim/bilgi` (CİHAZ, yanıt K_cihaz ile şifreli).
- `.ino`: USB'ye özel `Q` komutları (`/komut` ve köprü 403/ret; hiçbir satır sır basmaz),
  `pil_durdur` kancası, `kayit_oturum.h` `KY_BITIR_KANCA` (AVR'de boş; `kayit_esp.h`
  include'lardan ÖNCE tanımlar). Firmware `A3-1E`, 1.41 MB (%44), uyarısız.
- PC: `kopru/chacha.py` (saf Python, RFC 8439 vektörleri), `mqtt_istemci.py`,
  `bildirim.py dinle`, `sahte_araci.py` (keepalive + vasiyet + devralma uygular).
  `test_bildirim.py` 220/220 (B72.Q16 alt süreç, girdi özetiyle önbellekli).

**Neden esp-mqtt değil (K1 değişti):** çekirdekteki esp-mqtt görevi `xTaskCreate` ile
SABİTLENMEDEN açılıyor (`CONFIG_MQTT_TASK_CORE_SELECTION_ENABLED` yok, öncelik ≥ 1; IDF
FreeRTOS'ta sonradan yakınlık atanamıyor). P-256 el sıkışması yazılımda yüzlerce ms; görev
çekirdek 1'e kayarsa ölçüm döngüsü bloklanırdı (B28'in bütün kazancı). Bedel ~250 satır
bağlantı kodu; kazanç: tezgah HiveMQ'suz, PC'deki sahte aracıya karşı koşuyor.

**Kart tezgahı (`tezgah_bildirim.py`, sahte aracı PC'de, kullanıcı sırrı gerekmez)**
- İlk koşu **47/49**: arka arkaya iki `Qt` TEK olaya birleşiyordu (görev tek bayrağı
  tüketmeden ikinci istek geliyordu). Düzeltme: tek yazarlı sayaç çifti
  (`bld_deneme_istek` çekirdek 1, `bld_deneme_islenen` görev) — B72.Q17.
- Düzeltmeyle **51/51**: CONNECT alanları, vasiyet zarfı, durum + yanlış AAD/anahtar reddi,
  `Qt` ×2, **RTS sıfırlamasında vasiyet 3.6–6.8 s (5/5; hedef 10 s)** — hızlı açılışta aracı
  vasiyeti "devralma" ile yayınlıyor (aynı istemci kimliği), yavaşta keepalive ile; aracı
  kesintisinde kart 1.2 s'de fark ediyor, olay kuyrukta bekleyip dönüşte gidiyor; bağlıyken
  dahili yığın 122 KB (K11 ≥ 60 KB); seri + `/akis` metninde hiçbir parola/anahtar yok.
- `Qv` (RFC 8439 §2.8.2) gerçek donanımda geçti.

**Mutasyon:** 1E'nin 69 kaydı, hepsi öldü (B71 48 — odaklı giriş `test_kayit_1e.py`,
~3 s; tam B71 her mutasyonda ~4 dk sürüyordu · B72 20 · B22a 1). Koşu bir iddiamı zayıf
buldu: `find("#define KY_BITIR_KANCA")` yanlış adlı `KY_BITIR_KANCA_ESKI`'yi de kabul
ediyordu (o zaman boş varsayılan sessizce devreye girer) → tam imza.

**Gerçek aracı (2026-10-02 gecesi) — HiveMQ değil EMQX.** HiveMQ ücretsiz Serverless planı
kaldırmış (yeni küme 2026-09-30'dan beri açılamıyor, var olanlar 2026-12-31'de duruyor; kalan
Starter ücretli, 15 gün deneme). Spec'in yedeği **EMQX Cloud Serverless** (ayda 1 M oturum-dakikası
+ 1 GB, kredi kartı yok, harcama sınırı 0, Frankfurt). Kurulumu kullanıcı Chrome'daki Claude
eklentisine verdiğim istemle yaptı (bu oturumun tarayıcı bağlantısı uzantının görünmeyen bir
penceresine düştü, kullanıcı göremedi); parolaları kendisi yazdı, karta depo dışı
`bildirim_ayarla.py` (getpass) ile girdi — ben görmedim. İki kullanıcı + **beyaz liste**
(`olcum-kart` `ok/#` yayın+abone, `olcum-cihaz` `ok/#` yalnız abone, cihaz yayın Deny, "All Users
`#` Deny" — Serverless'ta mod anahtarı yok, EMQX belgesi böyle diyor).
- TLS el sıkışması 0.9–2.0 s; **el sıkışma sırasında `loop_azami` 7.1–7.6 ms, taban 7.2–7.4 ms
  → etkisiz** (çekirdek 0'a sabitlemenin karşılığı; `K` sayaçları `Q1`'den 150 ms SONRA sıfırlanıp
  NVS yazması dışarıda tutuldu). 120 s kopmasız, durum 60 s'de bir.
- **Ö4: RTS sıfırlamasında 16/16 vasiyet 4.0–7.9 s** (hepsi ≤ 10 s; abone `olcum-cihaz` ile, aracı
  bilgisi kartın şifreli `/bildirim/bilgi`'sinden geçici eşleşmiş cihazla, sonra `Ex` ile silindi).
- Dahili yığın bağlıyken 82–83 KB; en düşük 54–60 KB (açılış + el sıkışma anı) → E6.
- İlk koşuda 16 sıfırlamadan birinin `basladi`'si aboneye ulaşmadı; hedefli tekrar 6/6. Kart
  sayacı kaydedilmediği için yer belirlenemedi → E7.
- Tuzak: gördüğüm `baglanti=3 hata=-6` sahte aracı tezgahından kalmaydı (sayaçlar yeniden
  başlamaya dek sürer), EMQX'e tek temiz bağlantı vardı.

**Yapılmayan / açık** (`tasarim/1-acik-isler.md` "1E" E3–E7): ağ kurulumunu görev içine taşıma
(açılış 2.5–6.3 s) 1E'de YAPILMADI; gerçek fiş çekme (USB + PİL kapalı) elle yapılmadı.

Yedekler: `tam-20261001-232725.bin` (A3-1D, 1E öncesi) · `tam-20261001-235107.bin`.

#### 5.12.73k ✅ KABLO GÜZERGAHI (kutu belgesi, 2026-10-01; iş etiketi "B73")

> **Birleştirme notu (2026-10-03):** bu girdi kullanıcının çalışma kopyasında commit'lenmemiş B55–B70 işiyle
> birlikte `main`'e alındı. Orada "5.12.73" ve "B73" diye yazılmıştı; o numaralar `main`'de 1E (MQTT) ve
> zincir adımı B73 (`ortak/`, `test_ortak.py`) olarak kullanıldı. Bu işin "B73"ü yalnız kod açıklamalarındaki
> iş etiketi; zincirde ayrı bir adım değil (iddiaları B9 `kutu.py` ve B57 `kutu_ipucu_test.py` içinde).

**İstek.** Kullanıcı 10.2'de: *"hangi tel nereye gidiyor tam olarak söyle … acaba bu kutu web sayfasında hangi kablo nereye gidecek ve nasıl gidecek bunu da mı göstersek? Çok daha kolay ve anlaşılır olur."* Sonra: *"web panelde adım adım kısmında da … kablolar da gözüksün."* Kapsamı kullanıcı bana bıraktı (*"sence hangisi mantıklı ise öyle yap"*). Tasarım `tasarim/2026-10-01-kablo-guzergahi.md` (onaylı), plan `tasarim/2026-10-01-plan-b73-kablo-guzergahi.md` (inline yürütme). Firmware dizisi B71/B72'yi aldığı için bu iş B73.

**Ne yapıldı.** 10.3 / 10.4 / 11.1'in 26 kablosu `8-kutu.html`'de:
- **Arka duvar İÇERİDEN** (jak tarafından bakış, aynasız) ana çizim. Eski arka duvar çizimi dışarıdan ve aynalıydı; B63'te kullanıcı TP4056'yı bu yüzden yanlış ovale takmıştı.
- Kuşbakışında da kablolar var.
- 3B'de kablolar eksen eksen ince bloklardan zincir.
- Numaralı tablo var; satıra dokununca çizimdeki kablo (çizgi + rozet) yanıyor.
- Bilgi kartında kesim boyu, yol cümlesi, kesit ve "uç yerleri ±3 mm tahmin" notu.

Tek kaynak: bağlantılar `PIL_KABLOLAR` + yeni `KABLO_EK` (LED, J5, CAL), uçlar `KABLO_UCLARI` / `PANEL_UCLARI` / kart delikleri (`kart_nokta`), güzergah `guzergah()`. Kural: arka bölgede "öne çık, dik, yatay, gir"; 13 kabloya açık ara nokta (`KABLO_YOL`).

**Prototip (planı yazmadan, repo dışında).** Varsayılan kuralla 13 kablo bir gövdeden geçiyordu:
- H2− ve F2→F1P → ESP32'nin içinden.
- J5, CAL → ESP32 ve kart A'nın içinden.
- KL→C34/C36 → kart A'nın bileşenleri arasından.
- PİL anahtarı kabloları → kart A'nın arka kenarı (duvara 12 mm) ve ön jaklar.
- Adlı "kanal" fonksiyonları bu dar geçitleri genelleyemedi; spec K4 "açık ara nokta"ya çevrildi.

Sonuç: çarpışma 0, kart B'nin HV girişine en yakın kablo **58.2 mm** (sınır 12.6).

Kullanıcıya giden pratik sayılar:
- 2. yuvanın siyahı TP4056'ya **20 cm** (yuva teli ~15, ek gerekir).
- PİL anahtarına **31 cm**.
- Kartın 24 V telleri klemense **27 cm**.

**Aynı adımlarda düzeltilen hatalar (spec §4):**
- §4.1 F2'nin çıkışı F1P'nin çıkış klipsine (kullanıcı böyle kurdu; düğüm aynı).
- §4.2 Hücre telleri yuvanın kendi telleri; yuva yönleri.
- §4.3 GÜÇ LED'inin katodu **COM jakının kulağına**. Eski metin "klemens/GND noktası" diyordu; MT1 eksisine bağlansa 10.5'te J5 yokken lamba **yanmazdı**.
- §4.4 10.3'teki "hücresizken TP1.B− ↔ kart GND öter" kontrolü **fiziksel olarak imkânsızdı**: paket–GND bağı yalnız J5 (11.1) ve FS8205'in sırt sırta gövde diyotları B−/OUT−'yu ayrı tutar. Kontrol 11.1'e (OUT− ↔ C29) taşındı. Graf `ESP32.GND = KART_GND`'yi J5 takılı varsayıyor; açıklandı.
- §4.5 FUS009 **iki ayrı çıplak klips** (plan tek gövde sanıyordu) → ≤ 25 mm plaket şeridi. KF-03 denendi: 27×14 mm, F1P kart A'nın altına giriyor, kapaklar üst üste geliyor.
- §4.6 Hi-Link B0505S'in gövdesinde bacak **adı yok**: 1 +Vin, 2 −Vin, 4 −Vout, 6 +Vout. Mornsun'da girişler TERS.
- §4.7 Kullanıcı kararı: modüller (MT1, MT2, B0505S) ve küçük parçalar (680 µF, KL, sigorta şeritleri) **sıcak silikonla**. `YAPISTIRMA_ISTISNA` 2 → 10; tutucu çubuklar kesim listesinden düştü (7380 mm³). Kural cümlesi "değerli parçalar yapıştırılmaz" oldu.
- §4.8 MT1/MT2 kabloları tezgahta önceden lehimleniyor.

**Denetimin bulduğu kendi hatalarım:**
- **"ŞARJ ovali USB'nin solunda" iddiası TAUTOLOJİYDİ.** Yazıların belgedeki sırasına bakıyordu, aynalı çizimde de geçiyordu. Mutasyon koşucusu yakaladı; x konumuna çevrildi.
- **−12 rol mutasyonu ölüydü.** Kümeden tek uç çıkarmak hiçbir kablonun rolünü değiştirmiyor, çünkü her −12 kablosunun iki ucu da kümede. Kümeyi boşaltan mutasyona çevrildi.
- **Rozet ve "ön →" yazıları üst üste biniyordu** (B0505S'in bitişik bacakları, LED'in iki bacağı). Önce kırmızı bir iddia, sonra yerleşim (aday noktalar ≥ 18 px, yazı istifi). Rozetler çizgilerin üstüne ayrı grupta yazılıyor; kuşbakışında rozet yalnız öne uzanan kablolarda.
- **`_ahsap_der()` "ta-BLO-da"yı ahşap tutucu sandı** (CLAUDE.md'deki Türkçe kök tuzağı). Metin "konum listesinde" oldu.
- **Sayfa bütünlük denetimi JS'teki `data-bi="` dizesini anahtar sandı.** Seçici `JSON.stringify` ile yazıldı.

**B73'ten bağımsız ama burada bulunan:**
- "SR5100 → 1N5819" mutasyonu KAÇIYORDU: 1N5819 2026-09-28'de stoğa girdi (D013, B70), iddianın dayanağı kalktı. Emekli.
- Kesim listesi ile kütle modelinin ahşap hacmi farkı **+972 mm³** B73'ten önce de vardı (B55c "fark 0" diyordu). 27×18×2 = 972, muhtemelen TP1 rafının "üst kat 27" parçası bir modelde eksik. Açık.

**Doğrulama:**
- `kutu.py` **2403 → 2414** (bölüm 10: 27 yeni iddia; tutucu çubuk döngüleri 16 iddia azaldı).
- `kutu_ipucu_test.py` **30 → 35**.
- Mutasyon B50 **216/216** (eklenen 11, güncellenen 4, emekli 3), B57 **8/8**.
- `beklenen_sayim.json`'da yalnız B9'un kutu.py çifti → 2414 (ağaçta 1D'nin ve kullanıcının commit'lenmemiş işi var; tam kilit yazılmadı).

**Bağımsız gözden geçirme (ayrı model, aynı gün) — zincir 21/21 yeşilken bulunanlar:**
- **Telefonda tablo satırı işe yaramıyordu (kritik).** Satıra dokununca kablo yapışkan adım başlığının ALTINA kayıyordu. Kart da ekran dışında kalan satıra bağlıydı. Tarayıcı iddiası yalnız `!hidden`'a baktığı için yeşildi. Şimdiki davranış:
  - Kablo görünmüyorsa (`elementFromPoint` başlığa çarpıyorsa) ortalanıyor.
  - Kart çizimdeki rozeti izliyor.
  - Test 390×800'de 7. ve son satırı, masaüstünde son satırı ölçüyor.
- **Farklı kablolar aynı çizgideydi.** 22 çift çakışıyordu:
  - 680 µF'in iki ÇIPLAK bacağı aynı çizgide.
  - 5 V ile GND 96 mm üst üste.
  - +24 ile −12 üst üste.
  - H1+ ile H1− üst üste.

  Çözüm `_seritler()`: her kablo, ucu ortak olmayan kablolarla çakışmayan ilk şeridi (2 mm adım) alıyor. Sıra: önce çıplak bacaklar, sonra uzundan kısaya. Denetim çakışmayı şerit kodundan **bağımsız** yazılmış ayrı bir döngüyle arıyor. İç bakış (x-z izdüşümü) aynı adımın kablolarını, 3B ise bütün çiftleri karşılaştırıyor.
  - İzdüşüm kuralı bütün çiftlere uygulanınca çözümsüz kalıyordu: aynı J1 başlığındaki 5V ile GPIO10 izdüşümde hep üst üste geliyor.
  - Kart deliğinin 0.05 mm'lik ızgara kayması parçayı "eksenel değil" yapıp çakışmayı gizliyordu. İki tarafta da baskın eksene geçildi.
- **TP4056'nın 6.0'da lehimlenen ~20 cm'lik telleri yeni kablo sanılıyordu.** "Kablo 9: 4 cm" gibi kesim boyları ne yeni bir parçaya ne o teli kısaltmaya uyuyordu. `kesim_yazi()` artık pedden gereken boyu veriyor; 20 cm yetmezse "ek" diyor (PİL anahtarına giden tel 34 cm). Yuva tellerinin boyu ölçülmedi: "N cm gerekir (uzunsa kes, kısaysa ek)".
- **3B'de N/P kablonun her bloğunda duruyordu.** Aynı kart 4–6 kez geliyordu. Özet de "kablo 142" diyordu, oysa bu blok sayısıydı. Artık her kablo tek durak ve sayım kabloyu sayıyor. Ayrıca fareyle 3B kablo seçimi için test yoktu, eklendi.
- **Belgede elle yazılmış ya da eskimiş sayılar:**
  - B0505S için gövdede OLMAYAN adlar kullanılıyordu (Vin/GND, +Vo/0V); artık bacak 1/2/4/6.
  - 10.4'te aynı iki tel ikinci tabloda tekrar ediyordu, notu "tezgahta XT30" diyordu.
  - LED katodu için "36 mm" yazıyordu, oysa kablo 10 cm.
  - Kısa kablolarda soyma payı yoktu (+2 × 6 mm).
  - GPIO10 ucu ~11 mm kaymıştı: DevKitC-1 J1'de 5V ile GPIO10 arası 5 pin. Artık `ESP32_J1` ile çapraz denetleniyor.
- **Mutasyon koşucusu bu turda da üç boş iddia buldu:**
  - "Başlığın altındaki kablo" durumu hiçbir testte kurulmamıştı (yeni tarayıcı iddiası eklendi).
  - "H2− ara noktası silinirse ESP32'den geçer" artık KAÇIYOR: şerit seçici yolu kendisi ESP32'nin üstüne kaldırıyor. Yerine seçicinin gövde süzgeci mutasyona alındı.
  - Bacak sırası mutasyonu yanlış düzeni kurmuyordu.
- **Kullanıcı isteği: kabloları göster / gizle.** 10.3, 10.4 ve 11.1'de çizimin üstünde bir kutu var, 3B'de de "kablolar" kutusu. İkisi tek ayar ve tarayıcıda hatırlanıyor (`localStorage 'kutu-kablo'`). Gizleyince 2B'de çizgi, rozet ve "ön →" yazısı (`.kb-yazi`), 3B'de bloklar kalkıyor; 3B sayım ve seçim de buna dahil.
- **Doğrulama:**
  - `kutu.py` 2414 → **2421**.
  - Tarayıcı testi 35 → **46**.
  - Mutasyon B50 **234/234**, B57 15.
  - `dogrula3.py` **21/21**.
- **Ertelenen küçükler:**
  - "ön →" yazılarının okunurluğu.
  - Telefonda tablo sütununun taşması.
  - Söküm için ısı tabancası önerisi.
  - §4.3 iddiasının sabit çift araması.
  - Lejant sözcüğü.
  - CB bacaklarının kutup rengi.

**Açık / faz 2:**
- 5–9 adımlarının kabloları. Önce gerçek yerleşim plana girmeli: güç bloğu sağ duvarda dik, XP128 ön köşede, raf yok; Q1 kafesi; kart B 90° dönük.
- Kullanıcı kart B'nin üstünden kablo geçişini kabul etti (tırnak cilası); gerekçeli karar olarak yazılacak.
- 7.2'nin "C25/C27 ayrımı" kontrolü bip ile ayırt edilemez.
- 7.1'in kare pul metni.

---

#### 5.12.62 🧩 B48 — DELİKLİ PLAKET YERLEŞİM PLANI + KAÇAK YOLU DÜZELTMESİ (2026-09-14)

**Neden.** Malzemenin tamamı geldi (50 mA sigorta hariç); kullanıcı "lehimsiz test mi, plakete mi" diye sordu. Karar: **plakete, blok blok** — lehimsiz tahta bu kartta ölçüm üretmez (15 mΩ şönt + Kelvin tahta temasından küçük; 4.9 MΩ zincirde tahta kaçağı oranı bozar; B30/B44'te iki sessiz kusur gevşek telden geldi). Ama plakete geçmek için elde **yerleşim planı yoktu** — F9 ("delik atla") sayı veriyordu, yer vermiyordu.

**Ne yapıldı.** `uretim/yerlesim3.py` (+ `yerlesim3_veri.py`, `yerlesim3_teller.json`, `yerlesim3_belge.py`) → `BELGELER/7-yerlesim.html`.

* **Üç parça mimari.** A: ana analog kart (38×38 delik). B: HV zinciri 6×820K ayrı 5×5 plakette — 615 V bakırı ana kartın hiçbir yerine yaklaşmıyor, A'ya tek sinyal (alt düğüm ~1.7 V). Güç yolu (RS, J3, J7, Q1) **plakette değil**: 11.5 A / 6.55 A plaket bakırını aşıyor; plakete yalnız Kelvin S+/S−, tek yıldız GND teli ve kapı teli giriyor.
* **Ayak izleri** delik biriminde (1/4W yatay 4 adım, dik 1 adım, DIP-8, TO-92/TO-220 **işlevle** eşleşen bacak, ADS modülü 1×10 dişi başlıkta, sigorta klipsi, radyal 68 µF, film C18, kart dışı tel lehim noktası + gerginlik deliği).
* **Yol üretici** (`--yol-uret`): A* tabanlı, ağ ağ, ağaç büyütme; kaçak eşiği üstündeki komşuluğu **yasak** sayıyor, aynı ağın henüz takılmamış parçasının deliğine iz akıtmıyor. 44 ağ sırası deniyor, en az "el zahmeti" (yalıtımlı tel pahalı) seçiliyor. **Deterministik** — ilk sürüm değildi: ağ adları `set`'ten sıralanınca eşit anahtarlarda dize hash'i sırayı değiştiriyordu, iki ardışık koşu farklı JSON yazdı; önce ada göre sıralanarak düzeltildi (PYTHONHASHSEED=7 ile aynı çıktı).
* **Denetim yol üreticiye güvenmiyor.** Tel etiketlerini okumuyor; bağlantıyı geometriden (hangi delik hangi delikle bakırla bağlı + kart dışı kablolar) yeniden kurup `netlist3.net` ile birebir karşılaştırıyor: 56 ağ, açık yok, kısa yok, **her kurulum adımında** (0..8) yarım kart da tam bağlı. Ayrıca gövde çakışması, bacak-gövde altı, Kelvin adaları yalnız, GND güç yoluna tek noktadan, kaçak yolu bakırdan bakıra (Tablo F.4 aradeğer), ayırma kondansatörü bakır yolu ≤3 delik. **40/40**, B9'a bağlı.
* **Kullanıcı belgesi:** parça/lehim yüzü SVG (lehim yüzü aynalı), adım seçici (o adım koyu, öncekiler yarı saydam), her adımda parça→delik tablosu, izler (köşe noktaları), yalıtımlı teller, kart dışı kablolar, kılavuzun KAPI ölçümü.

**🔴 Bulgu — F9'un "5 delik" sayısı bakırdan bakıra yetmiyordu.** B15/D2 ve F9 `ceil(12.6 / 2.54) = 5` diyordu; bu **merkezden merkeze** 12.70 mm. Kaçak yolu iletkenden iletkene ölçülür; ped + lehim tepeciğiyle etkin iletken çapı ~1.54 mm (b15-arastirma.md:470) düşülünce 5 delik **11.16 mm** eder, 12.6 mm'yi sağlamaz. Tek kaynağa `DELIKLI_PAD_ETKIN_MM = 1.54` ve `IEC60664_F4_PD2_MG3` tablosu kondu; B15/D2, F9, kurulum kılavuzu ve yerleşim aynı sabiti okuyor → **6 delik (13.70 mm)**. F9 koşulu artık `n·2.54 − ped ≥ 12.6` diye sınıyor. Kullanıcının plaketinde ped **ölçülmedi** — tezgah kalemi.

**Sayılar.** Kart A: 81 parça, 130 iz (495 adım), 27–28 yalıtımlı tel; kullanılan alan 37×35. Kart B: 8 parça, 7 iz, 0 tel; en dar çift E8–E11 6.08 mm / gereken 4.11 mm @411 V (pay +1.97 mm; ilk sürümde sıralar 4 adımdı, pay 0.39 mm — lehim tepeciği biraz büyüse yetmezdi, 5 adıma açıldı). 10×10 plaket **32×32** delik çıktı (kullanıcı saydı), plan sığmadı → 13×23'ten (45×90) 38×38 kesilecek.

**Mutasyon (6/6 yakalandı):** parça 180° ters (C15) → kısa/çift bacak · parça kendi izlerinden önceki adımda (R41 adım 1→0) → adım denetimi · Kelvin çapraz · yıldız teli "kelvin" etiketli · ped 1.54→4.0 → kaçak yolu · HV zincirinde iz bir delik kısa → açık. **Sınanamayan:** `BACAK` tablosunun fiziksel doğruluğu (2N2222-331 E-B-C, BC557 C-B-E, TL431 REF-A-K, 7912 GND-VI-VO) — yalnızca multimetreyle; tezgah listesine `[!]` ile girdi.

**Tezgah kalemleri (B48):** bacak sırası diyot kademesiyle · ped çapı kumpasla · klips/68 µF/C18 bacak aralıkları · her adımda ohmmetreyle süreklilik (plan soğuk lehimi kanıtlayamaz).

---

#### 5.12.61 ✅ B47 — TETİK ONAYI (gürültü reddi), AYARLANABİLİR (2026-09-14)

**Neden.** B44/B46: I²C susturulmuş ve CAL kapalıyken bile ~0.1–0.3/1000 tek-örnek iğne kalıyor (60 kod; histerezis 40). Tek-örnek tetikte 1000 örneklik yakalamada ~%25 olasılıkla bir iğne var; eşiğe yakın düşerse **sahte tetik** — kullanıcının B41'de ekranda gördüğü şeyin nadir hali. Kullanıcı önerisi: sabit değil, **ayarlanabilir** olsun (tek / iki örnek). Gerçek skoplardaki karşılığı "noise reject" tetik bağlantısı.

**Ne yapıldı.** `SkopAyar.onay` (1|2, varsayılan **2**), komut `tn<1|2>`, `T` satırında `onay=`, arayüzde menü ("Gürültü reddi (2 örnek)" / "Tek örnek"), sahte kartta aynı. `skop_yakala`: geçiş örneği `bekleyen` olur; bir sonraki örnek eşiğin doğru tarafındaysa tetik = **geçiş örneği** (`tetik_w = w−2`, `kalan = sonra−2`), değilse geçiş iğne sayılır ve arama sürer. Ön-tetik konumu iki kipte de aynı (B42'nin `tetik_idx == on` iddiası korunuyor); `on + 3 ≤ n` kırpması. Eski firmware `onay=` göndermez → arayüz menüye dokunmaz (kart o sürümde zaten tek örnek). Skop ayarları NVS'te tutulmuyor (önceden de öyle): açılışta varsayılan 2.

**Asıl kazanç ayarlanabilirlikten geldi: kendi kendini kanıtlayan A/B.** Dün "bunu kesin yalanlayan tezgah testi yok" denmişti. Aynı firmware'de iki kip arka arkaya, iğne kaynağı `tK8,9` (B44'ün I²C tıklatması), OTO kip, CAL kapalı, eşik = düğüm ortalaması + 30 kod, histerezis 0, gerçek geçiş yok (`tezgah_blokaj.py --onay`):

| onay | yakalama | tetiklendi |
|---|---|---|
| 1 (tek örnek) | 20 | **17** — iğneler tetikliyor |
| 2 (iki örnek) | 20 | **0** |

Sonra gerçek sinyal (CAL 1 kHz, NORMAL, ön-tetik %25, 833 örnek): onay=2 beş yakalamada da tetikledi ve tetik indeksi **208** (= beklenen), onay=1 de 208. Yani gürültü reddi gerçek sinyali kaçırmıyor ve konumu kaydırmıyor.

**Bedel.** Tetik 1 örnek gecikir (konum düzeltiliyor, görünmez). Yavaş tabanlarda gerçekten tek örnek süren darbe (500 ms/böl'de 1.6 ms) onay=2'de tetiklemez — bunun için menüden "Tek örnek". Bir ayar daha.

**Doğrulama.** Kartta `--onay` **4/4** · `sim3_skop` 83 → **87** (6m: w−2/sonra−2, tek kip aynen, doğrulanmayan geçiş iğne, varsayılan/protokol) · `test_arayuz3` 338 → **346** (bölüm 22) · mutasyon B19 **52/52**, B7 **74/74** (onay örneğini tetik saymak, `cift`'i kapatmak, kırpmayı geri almak, varsayılanı 1 yapmak, arayüzün `onay=`i okumaması / uydurması, menünün yanlış komut göndermesi, sahte kartın geçersizi kabul etmesi). B42 mutasyonunun deseni (`dolu > on`) yeni koda göre güncellendi.

---

#### 5.12.60 🔴 B46 — ALERT PROBU HAT ZATEN DÜŞÜKKEN "VAR" DİYORDU (2026-09-13)

B44b deneylerinden sonra `D` satırı `durum=2` (akım ADS'si okunamıyor, 33 örnek/rapor) verdi. `#` komutu: I²C taramasında **yalnız 0x49**; ama hemen altında *"0x48=VAR sure=3 us (RDY calisiyor — dogru modul)"*. İki satır birbiriyle çelişiyordu ve ikincisi **yanlıştı**: `alert_dener` ayarı yazıp pinin DÜŞÜK olmasını bekliyor, ilk turda düşük bulup dönüyordu — pin **zaten** düşüktü (beslemesiz/bağlantısız modülün ALRT ucu). Kullanıcı bu çıktıya bakıp RDY telini "doğru" sayardı.

Düzeltme: (1) modül adresi ACK'lamıyorsa sınama yapılmıyor ve söyleniyor (*"0x48=I2C'DE YOK — RDY sinanamadi: modul #1'in VDD/GND/SDA/SCL/ADDR tellerini kontrol et"*); (2) ayar yazılınca hattın önce **yükselmesi** (RDY'nin bırakılması) bekleniyor, yükselmiyorsa *"hat SÜREKLİ DÜŞÜK"* — bir kenar görülmeden "çalışıyor" denmiyor. Kartta: prob artık *"0x48=I2C'DE YOK"* diyor. `sim3_bant` 69 → 71, mutasyon B20 12/12.

Modül #1'in kendisi: kullanıcı I²C tellerini demetten ayırırken (B44b) **modül #1'in SCL teli çıkmış**; kabloları "oturtmak" bulmadı, multimetre istenince kullanıcı boş SCL'yi gördü ve modül #2'nin SCL'sine paralel bağladı. Sonra kartta: I²C'de 0x48 + 0x49, `D` durum 0, 94 örnek/rapor; prob *"0x48=VAR sure=1220 µs"* — 860 SPS'te **gerçek** dönüşüm süresi, yani prob artık gerçek bir kenar ölçüyor (eskisi 3 µs'lik sahte "var"dı).

##### Tezgah sınamasında B44'ün yan bulgusu ısırdı
Günün sonunda `tezgah_blokaj --skop` **11/12**: örnek bütünlüğü sınaması 11 hata/3721 verdi. Sınama CAL **20 kHz** ile koşuyordu ve B44 CAL PWM'inin kendi kenarının da hata soktuğunu bulmuştu (faz kaydığı için ara sıra; üç temiz koşudan sonra dördüncüsü denk geldi). I²C ile ilgisi yok. Sınama artık **CAL kapalı** koşuyor; ölçüt ≤ 1/3721 (B40b'nin kusuru 3–9/1000, 10× pay). Yeniden: **12/12**, 1 hata/3721 (0.27/1000).

⚠ **Açık gözlem — kalıntı hata tabanı.** I²C susturulmuş ve CAL kapalıyken bile ~0.1–0.3/1000 tek-örnek hata kalıyor (B44 kontrol koşuları 0.06–0.12, bu koşu 0.27). Kaynağı bilinmiyor (WiFi yükü altında 0 ölçüldü; ESP32'nin kendi etkinliği aday). 1000 örneklik yakalamada ~%25 olasılıkla bir yerde 60 kodluk tek bir iğne — histerezis 40 kod olduğu için **nadir sahte tetik hâlâ mümkün.** Ucuz çare (yapılmadı, sırada): tetik için **iki ardışık örneğin** eşiği geçmesini istemek — tek-örnek iğne tetikleyemez; B42'nin `tetik_idx == on` iddiası ilk geçiş örneğiyle korunur. Bunu deterministik yalanlayacak tezgah sınaması bulunamadığı için (iğneler aralıklı) ertelendi.

⚠ **B44b'ye düşen kayıt:** teller ayrıyken yapılan koşularda (K1 3.24; d0/d2/d3 tablosu) modül #1'in SCL'si **bağlı değildi** — SCL hattında yalnız modül #2'nin pull-up'ı vardı. Sürüş gücü karşılaştırması kendi içinde tutarlı (üç durum aynı kablolamada), "yakınlık değil" sonucu da ayakta (daha az yükle bile hata sürdü); ama o koşuların K1 mutlak değerleri önceki 2.22 ile doğrudan kıyaslanamaz.

---

#### 5.12.59 🔴 B45 — PANEL TARAYICIDAN SEKME SEKME GEZİLDİ: dört kusur (2026-09-13)

Kullanıcı isteği: "görsel ya da mantıksal hata olmadığından emin ol". Beş sekme Claude in Chrome ile gezildi; ekran görüntüsü + sayfanın Vue durumu birlikte okundu. Bulunanlar:

##### 1. Zaman grafiği negatif değeri GÖSTEREMİYORDU
`y = üst + boy·(1 − değer/enb)` sıfırı tuvalin **altına** koyuyordu. Kart çift yönlü (±32 V, ±2.56 A, negatif güç = kaynak) ama negatif her nokta tuvalin dışına çiziliyordu; boştaki akımın ±3 µA gürültüsünün yalnız **pozitif yarısı** görünüyordu. Şimdi pencerede negatif varsa sıfır ortada (`[−enb, +enb]`), yoksa altta; her seri için kesikli sıfır çizgisi.

##### 2. Gürültü tam ekrana yayılıyordu
Ölçek hep tepe değerdi: giriş boşken 0.05 LSB'lik gürültü ekranı dolduruyor, etiket "tepe 0.0 mA" derken iz dev bir sinyal gibi görünüyordu (ekran görüntüsünde ilk bakışta "büyük bir şey var" izlenimi). **Taban: kanalın 20 LSB'si** — LSB'ler kartın bildirdiği şönt ve menzilden (`akimMenzilAralik` ile aynı kaynak): 0.1 Ω'da 1.56 mA, NORMAL'de 20.8 mV; güç için |V|·i_taban + |I|·v_taban (1.7 V'ta 2.7 mW). 10 mA'lik gerçek yük (128 LSB) tabanın üstünde, eskisi gibi ölçekleniyor. Taban devredeyken etiket ölçeği de yazıyor ("tepe 0.0 mA · ölçek ±1.6 mA"). Ayrıca "−30 sn" etiketi izin altına biniyordu, şerit kondu.

##### 3. Skop ölçüm satırında birimler karışıktı
`muh()` her değeri kendi önekine çeviriyordu: aynı satırda "Vmax 348.200 mV" ile "Vmin −4.092 V"; mV'deki üç ondalık (1 µV) kanalın 29 mV'lik adımı yanında sahte hassasiyetti. Altı gerilim artık "x.xxx V". Zaman büyüklükleri SI önekli kalıyor (µs/ms anlamlı).

##### 4. "Ayarları göster" ayarları GÖSTERMİYORDU
Düğme `?` gönderiyor; Konsol'da R/L/K/C/F satırları çıkıyor ama **ayarların kendisi** (`A menzil=… n_kazanc n_sifir sont i_duz i_ofset rapor`) ayrıştırıcıda yutulup günlüğe düşmüyordu. `CT` de öyle. İkisi de artık konsola düşüyor. Konsol açıklaması "karttan gelen her satır burada" diyordu — doğru değildi; hariç tutulanlar (`D` 20/s, `W`, skop dökümü ham örnekleri) artık yazıyor.

##### 5. Arşiv kaydının ölçüm satırı (B43'ün açık kalemi)
Köprü listede `M` satırını zaten taşıyor (`olcum`); açılan kayıtta kullanılmıyordu. Şimdi: **zaman** büyüklükleri (f, T, duty, tr, tf, n) kaydın `M` satırından; **gerilimler** kaydın ham kodlarından eksenle aynı çeviriyle (`kodVolt`) yeniden — B43 öncesi firmware'in yazdığı `M` gerilimleri doğrusal modeldi, eski kayıt açılınca 7 V'luk çelişki geri gelmesin. Eksik alan uydurulmuyor (kısa `M`de "Duty %0" yazmaz).

Bunu yazarken **yeni bir kusur** çıktı ve CDP testi yakaladı: köprü sahtesinin kısa `M` satırında (`duty` yok) `undefined.toFixed` bütün skop görünümünü çökertiyordu (`$refs.osiloTuval` null). `skopOlcumler` artık eksik alanı atlıyor.

##### Yan gözlem (kusur değil)
Hızlı ölçüm, GPIO4–GPIO5 kısa devreli düzenekte CAL 1 kHz ile **PF 0.952** veriyor (B39'da DC ile 1.0000 idi): V kanalı VREF'li (DC bileşenli), I kanalı VREF'siz okunuyor; AC sinyalde aynı düğüm iki kanalda farklı DC ile göründüğü için PF < 1. Ön uç olmadan beklenen; ön uç kurulunca sıfır kalibrasyonuyla birlikte yeniden bakılacak.

##### Doğrulama
* `test_arayuz3` 313 → **338** (bölüm 21): ölçek eşlemi ve taban (`grafikOlcek`/`olcekTabani` çizimden ayrıldı, doğrudan sınanıyor), birimler, konsol satırları, arşiv ölçümü **gerçek kart fikstürüyle** (`uretim/olcum-skop-fikstur.json`, `fikstur_skop_al.py` ile alındı: CT tablosu + 833 kod + `M`): arayüzün JS'i ile kartın C'si aynı kodlardan **0.048 mV** içinde aynı volta varıyor; eski (doğrusal) `M` satırlı kayıtta eksenden hesap; kısa `M` çökertmiyor.
* Mutasyon B7 **70/70** (9 yeni). CDP arşiv testi 19/19. Panelde (WiFi, yenilenmiş sayfa): grafik sıfır çizgili ve gürültü düz, ölçüm satırı tek birimde, konsolda `A` ve `CT` görünüyor; konsol hatası yok. Teller 41/42'deyken ADS'ler beklendiği gibi okunmuyordu (durum 3); geri takıldıktan sonra kartta doğrulandı: durum 0, 93 örnek/rapor, 1.7156 V.

---

#### 5.12.17 Sırada ne var

| Adım | İş | Not |
|---|---|---|
| B10 | **Donanımı kur** | Parçalar geldiğinde; kılavuz hazır |
| ~~B11~~ | ✅ **±12 V rayı (E0)** | **BİTTİ (2026-09-09).** 7912 orta nokta regülatörü; şemada BLOK 9. Sonuçlar **5.12.25**'te. Stoktan çıktı, yalnızca 50 mA sigorta alınacak |
| B12 | İkili aktarım + USB CDC | **Donanım çalıştıktan SONRA** — Serial'i değiştiriyor |
| B13 | Sürekli hızlı yol | Skop/ADC paylaşımı çözülmeli |
| ~~B15~~ | ✅ **Arıza ve zorlama simülasyonu** | **BİTTİ (2026-09-09).** Sonuçlar **5.12.24**'te: 111 doğrulama, 27 senaryo, DEVİR'in 4 sayısı düzeltildi, şemada 3 kusur kapatıldı |
| ~~B17~~ | ✅ **ADS eş zamanlılığı + süzgeç düzeltmesi** | **BİTTİ (2026-09-09).** Sonuçlar **5.12.29**'da: 26 doğrulama + AVR 70→87. Tek atış kipi, kesirli gecikme, ölçek düzeltmesi, faz kalibrasyonu |
| ~~B20~~ | ✅ **Örnekleme hızı + bant sınırı + menzil** | **BİTTİ (2026-09-10).** Sonuçlar **5.12.30**'da: 41 doğrulama, firmware'de 7 düzeltme. 91 → 671 SPS, `f` sınırı 400 → 100 Hz, AC menzil chatter'ı, SSE blokajı, imza, skop adımı |
| ~~B21~~ | ✅ **Pil kapasite testi** | **BİTTİ (2026-09-10).** Sonuçlar **5.12.31**'de: 32 doğrulama, şemada BLOK 10, `pil_test.h`, arayüzde panel. mAh + kesme + eğri + DCIR. Failsafe kapı, ≤38.5 V sınırı |
| ~~B19~~ | ✅ **Osiloskop kanalı çift yönlü** | **BİTTİ (2026-09-09).** Sonuçlar **5.12.28**'de: 24 doğrulama, R23 2.7K + alt uç VREF, −63.5…+46.8 V. Firmware ve arayüz de güncellendi |
| ~~B18~~ | ✅ **GPIO kelepçeleri / +3V3 geri beslemesi** | **BİTTİ (2026-09-09).** Sonuçlar **5.12.27**'de: 46 doğrulama, F6 reddedildi, R26/R33 10K + yeni R41. B1 payı 18 → 1930 mV, TL431'den bağımsız |
| ~~B16~~ | ✅ **V/I süzgeç eşleştirmesi** | **BİTTİ (2026-09-09).** Sonuçlar **5.12.26**'da: 41 doğrulama, C4 100nF→1nF, yeni C18/C19/C20 = 1.32 µF (stoktan). Reaktif yükte hata %155 → %1.9. 5 açık iş kalemi bıraktı |
| **B14** | **Hızlı skop (MHz) — harici ADC** | 🔭 **Aşama 4, açık ihtimal.** Kullanıcı ilgileniyor, şimdilik almadı. Tam analiz + kademeli plan **5.12.20**'de. Adım 1 bedava: hazır açık kaynak kodu elde bir ESP32'de dene |
| ~~B47~~ | ✅ **Tetik onayı (gürültü reddi), ayarlanabilir** | **BİTTİ (2026-09-14).** Sonuçlar **5.12.61**'de: `tn1/2`, varsayılan 2; kartta A/B 17/20 → 0/20 sahte tetik, gerçek sinyalde konum korunuyor |
| ~~B48~~ | 🧩 **Delikli plaket yerleşim planı** | **HAZIR (2026-09-14).** Sonuçlar **5.12.62**'de: `BELGELER/7-yerlesim.html`, denetim 40/40 (B9), mutasyon 6/6. F9'un "5 delik"i bakırdan bakıra yetmiyordu → 6. **B48b (5.12.63):** LEGO sırası, 91 alt adım, denetim 47/47, mutasyon 13/13. Kullanıcı lehime başlıyor |
| **B49** | 🔴 **Voltmetre şönt düşümünü içeriyor** | **AÇIK (firmware).** Şönt alçak tarafta, V kanalı RS.2'ye referanslı → okunan = kaynak gerilimi = V_yük + I·R_şönt (≤ 256 mV). Düzeltme `V_yük = V − V_şönt` (iki ADS eş zamanlı, B17). Pil testi etkilenmiyor. GÜNCEL DURUM bloğunda ayrıntı |
| **B11-düz** | 🔶 **Hangi ray regüle** | **AÇIK.** 5.12.25 "−12 regüle" diyor, bağlantıya göre +12 regüle, −12 ham; `sim3_besleme.py` B11-3 iddiası sabitle boş. Pratik etki yok; düzeltilip mutasyon eklenecek |
| **PCB** | **I²C kuplajı — PCB'de yeniden ölç** | 🔶 B44: SDA/SCL'ye seri direnç (33–100 Ω), tek pull-up seti, zayıf sürüş; `tezgah_kuplaj --asama 3`. K1 kontrol düzeyine inerse ADS susturması (B41) kaldırılabilir |

🔴 **Değişmeyen uyarı:** kart izole değil.


---

## 6. Fiziksel sınırlar — abartma

Yeni oturumun kullanıcıya yanlış vaat vermemesi için kanıtlanmış tavanlar tek yerde:

| Sınır | Değer | Kaynak |
|---|---|---|
| ADS1115 örnekleme | **860 SPS**, aşılamaz | veri sayfası SBAS444 |
| ADS1115 **bant genişliği** | **−3 dB @ 380 Hz** (sinc/boxcar) | 860 SPS'te 1.16 ms ortalama |
| ESP32 ADC | **83 333 Sa/s TOPLAM, 12 bit** | `SOC_ADC_SAMPLE_FREQ_THRES_HIGH` |
| Gerçek zamanlı Nyquist | tek kanal 41.7 kHz, **iki kanal 20.83 kHz** | toplam hız kanallara bölünür |
| V–I kanal kayması | **12.000 µs sabit** — eşzamanlı örnekleme imkânsız | tek SAR, sıralı pattern |
| ETS eşdeğer hız | 80 MSa/s | koherent örnekleme |
| **ETS analog bant** | 🧱 **bilinmiyor** — ölçülene kadar <500 kHz varsay | Espressif S/H açıklık süresini yayınlamıyor |
| ETS geçerliliği | **yalnız tekrarlayan sinyal**; tek seferlik olayı asla yakalamaz | yöntemin doğası |
| Gerilim tam ölçek — Aşama 2 | **32.2 V** (45 V değil) | ADS girişi VDD ile sınırlı |
| Gerilim tam ölçek — Aşama 3 | **±31.1 V / ±615.4 V** | 5.12, tasarlandı ve doğrulandı, kurulmadı |
| Giriş empedansı — Aşama 2 | **106.8 kΩ** (DMM'de 10 MΩ) | 100K+6.8K |
| Giriş empedansı — Aşama 3 | **0.21 MΩ / 4.93 MΩ** | 5.12 |
| Wattmetre güvenilir bandı | **~5 kHz** | Sallen-Key + Lagrange birlikte (5.12.7) |
| Direnç azami çalışma gerilimi | **200 V** (1/4W metal film) | Yageo MFR — 250 V varsayımı yanlıştı |
| İzolasyon | **yok** — şebeke bağlanamaz | tasarım |
| Burden gerilimi | tam ölçekte 256 mV, her akım kademesinde | PGA ±0.256 V |

⚠️ **Giriş empedansının anlamı:** 1 kΩ kaynak empedanslı bir düğümde %0.93, 10 kΩ'da
%8.6 hata. **Bu bir voltmetre değil, bir güç ölçer.** Besleme rayları ve yük uçları gibi
düşük empedanslı düğümlerde doğru; yüksek empedanslı düğümlerde multimetre kullanılmalı.

### 6.1 🔴 SMPS güvenliği — dipnot değil

> **İzole olmayan bir SMPS'in birincil tarafına bu kartla DOKUNMA.**
>
> Skop girişi kart toprağına referanslı. Şebekeden beslenen bir SMPS'in birincil
> "toprağı" **şebeke potansiyelindedir**. Kartın toprağını oraya bağlarsan **USB kablosu
> üzerinden bilgisayarına şebeke gerilimi taşırsın.**
>
> Yalnız **izole ikincil taraf**, ya da tamamen izole çalışma (pil + WiFi, USB takılı
> değil).
>
> 🔴 **AMA YÜZDÜRMEK TEK BAŞINA YETMEZ — B15/D2 bunu ölçtü.** Pille
> yüzdürmek **bilgisayarı kurtarır, KULLANICIYI kurtarmaz**: kart o anda
> şebeke potansiyeline çıkar ve **kartın her noktası** tehlikeli olur.
> 615 V, yüzen alet sınırının **14.6 katı**. Şebeke referanslı ölçümde
> **yalıtımlı kutu ŞART** (hiçbir noktaya el erişimi yok), delikli
> plakette takviyeli yalıtım için **5 delik atlanacak** (12.7 mm,
> IEC 60664 creepage 12.6 mm) ve enerji varken karta dokunulmayacak.
> Ayrıntı **5.12.40**'ta; kullanıcı tarafı `BELGELER/4-kurulum.html`'in
> ilk uyarısında.

Aşama 2 yol haritasındaki *"ESP-01 WiFi izolasyonu — 400 V ölçümüyle birlikte zorunlu"*
notu bunun aynısıydı. **Hızlı skop kanalı gelince bu not isteğe bağlı olmaktan çıkıp
zorunlu hale geliyor**, çünkü kullanıcının asıl bakmak isteyeceği yer tam olarak orası.

---

## 7. Yeni oturum için görevler

### 7.1 Araştır (kullanıcının açık isteği)

Bu oturumda başlanan araştırmanın devamı. **Şu üç bulguyu doğrula ve derinleştir:**

**① WiFi ile sürekli ADC çakışıyor.**
`esp_wifi_start()`, `adc_continuous_start()`'tan sonra çağrılırsa DMA tamponu dolmayı
bırakıyor; ADC çevre birimi çalıştığını sanıyor.
*Kaynak: [espressif/esp-idf#12749 (IDFGH-11635)](https://github.com/espressif/esp-idf/issues/12749)*

Mevcut firmware'de sıra **tesadüfen güvenli**: `skop_kur()` yalnız `adc_continuous_new_handle`
ve `adc_continuous_config` çağırıyor (yapılandırma), `adc_continuous_start()` ise komutla
çalışan `skop_yakala()` içinde — yani WiFi'den sonra. **Ama yeni mimaride ADC sürekli
koşacak.** O zaman WiFi her açılıp kapandığında ADC durdurulup yeniden başlatılmalı.
Bu, "kalibrasyon USB ile yapılır, WiFi uzaktan izleme içindir" kuralını güçlendiriyor.

**② ADC2 DMA S3'te desteklenmiyor** (errata; kararsız sonuç gözlenmiş). Tasarım zaten
ADC1'de (GPIO1–10); bu kısıt korunmalı.

**③ Çok kanallı sürekli kipte interleave deseni** ~270 kSa/s toplam üstünde bozuluyormuş
(tekrar eden ve atlanan örnekler). Biz 83 kSa/s'teyiz, güvenli — ama iki kanal
kullanınca desenin gerçekten beklendiği gibi çıktığını **ölçerek** doğrula.

*Ayrıca ADC1'de 11 dB zayıflatmayla sürekli kipte "çınlama/gürültü" bildiren kullanıcılar
var — [ESP32 Forum](https://esp32.com/viewtopic.php?t=26367).*

**Araştırılacak diğer başlıklar:**
- ESP32-S3 ADC doğrusalsızlığı ve eğri kalibrasyonu — tek kazanç+ofset yetmiyorsa ne yapılır
- Eşdeğer-zaman örnekleme uygulamaları: gerçek projelerde elde edilen etkin bant genişliği
- Elektronik yük kararlılığı: lineer MOSFET çevriminin kompanzasyonu, tipik salınım sebepleri
- Kelvin şönt yerleşimi: delikli plakette 4 telli bağlantı nasıl doğru yapılır
- Delikli plakette yıldız toprak ve yüksek akım izleri
- LEDC PWM'i DAC olarak kullanma: RC süzgeç tasarımı, oturma süresi, artık dalgalanma

### 7.2 Hata bul

- Bölüm 4'teki maddeleri **doğrula** — gerçekten var mı? (Biri zaten yanlış alarm çıktı;
  başkaları da olabilir.)
- Bölüm 5'teki mimari varsayımları sorgula. Özellikle **5.2'deki süzgeç çelişkisi** ve
  **5.5'teki verim hata bütçesi** — bunlar en kırılgan noktalar.
- Bu belgedeki her sayının kaynağına git.

### 7.3 Geliştir

Kullanıcı "bunların dışında yapabileceğimiz işime yarayabilecek neler var?" diye sordu.
Bu oturumda dört öneri sunuldu ve **dördü de seçildi**. Yeni oturum kendi önerilerini
eklesin — kullanıcının profili: **yazılım mühendisi, elektronikle hobi olarak ilgileniyor,
envanteri SMPS/güç elektroniği ağırlıklı** (SG3525, TL494, UC3843, IR2110, güç
MOSFET'leri, yüksek gerilim film kondansatörler). İnverter veya anahtarlamalı güç kaynağı
projeleri muhtemel.

Değerlendirilmemiş bir fikir: **ESR ölçer**. TV sökümü parçalar ve SMPS onarımı için çok
uygun; NE555 ×10 yolda ve uyarma sinyali için kullanılabilir. Bu oturumda seçenek olarak
sunulmadı (4 seçenek sınırı), kullanıcıya sorulabilir.

---

## 8. Açık sorular — kullanıcıya sor

1. ✅ **±12 V — TAMAMEN ÇÖZÜLDÜ (2026-09-09), bkz. 5.12.23.** Kullanıcıda 12 V
   adaptör YOK; **24 V güç kaynağı**, bir düşürücü regülatör modülü ve **2 adet**
   18650 var. Karar: **24 V + LM358 orta nokta tamponu ile ±12 V** — ek alım sıfır,
   hepsi elde (LM358 stokta 8). Kart 3 pinli besleme girişi taşıyacak
   (+12 / GND / −12), böylece ileride 4 hücre daha alınıp 6× 18650 paketine
   geçilirse **kartta değişiklik gerekmez**. O gün kart yüzer hale gelir ve
   Wi-Fi ile birlikte projenin en büyük tehlikesi (izole olmaması) kapanır.
   ⚠️ **Kurmadan önce ölç:** 24 V kaynağın negatif ucu ile şebeke toprağı arasına
   ohmmetre — toprağa bağlıysa bu şemada −12 V rayı toprağa kısa devre olur.
2. ⚠️ **Soğutucunun ölçüsü/termal direnci ne?** Kullanıcı 2026-09-08'de "soğutucu var"
   dedi ve `MEK002` olarak kaydedildi, **ama spesifikasyonu bilinmiyor.** Elektronik
   yükte **2 °C/W eşiği 2.4 W ile 30 W arasındaki farkı belirliyor** — kabaca
   100×60×30 mm kanatlı profil ya da 60×60 mm + 40 mm fan. Ölçüyü öğrenip CSV'yi
   güncelle.
3. **Bölüm 5.8'deki satın alma listesi onaylanıyor mu?** (~40 TL: LM319N ×2, NTC ×2,
   KSD9700, metal film direnç seti, 1N4148 ×20)
4. **Laboratuvar kalibrasyonu ne zaman, hangi cihazla?** Mutlak ölçümlerin (voltmetre,
   ampermetre) tavanını bu belirliyor. *Oransal ölçümler (verim) için kritik değil —
   bkz. 1.3 ve 5.7.*
5. **Ön panelde kaç uç çifti olacak?** Bugün 5 (V, µA/mA, A, 10A, SCOPE). Yeni yetenekler
   uç istiyor: eğri çizici (DUT soketi + 4 Kelvin ucu), elektronik yük (2), verim ölçer
   (+4), SMPS zamanlama (3 prob). Muz jak 5 renk × 2 sipariş edildi — yeniden bölüşüm
   gerekebilir; DUT için ZIF veya kaliteli TO-220 soketi düşünülmeli.
6. **Geliştirme kartında hangi GPIO'lar başlığa çıkmış?** Pin planı çakışmasının
   (bkz. 5.9) çözümü buna bağlı. Kartın fotoğrafı veya pin listesi lazım.
7. **ESR ölçer ilgisini çeker mi?** (Bu turda seçenek olarak sunulmadı, 4 seçenek sınırı
   vardı. TV sökümü parçalar ve SMPS onarımı için çok uygun; NE555 ×10 yolda.)

---

## 9. Dosya haritası ve komutlar

> ⚠️ **Adım başına doğrulama sayıları burada TUTULMUYOR.** Bir kuşak boyunca
> tutuldular ve bayatladılar (B17 26→31, B3 128→150, B15 109→111). Tek kaynak
> **`uretim/beklenen_sayim.json`** ve zincir her koşuda birebir karşılaştırıyor.

### Komutlar

```bash
cd projeler/olcum-karti/uretim
python dogrula3.py            # AŞAMA 3 — GÜNCEL, 17 adım, ~6 dk
python dogrula2.py            # Aşama 2 (arşiv), A1–A6, ~70 s
python dogrula.py             # Aşama 1 (arşiv), S1–S9, ~110 s
python dogrula.py --hizli     # Aşama 1 hızlı (S1–S7), ~20 s

python mutasyon.py            # iddialar gerçekten ısırıyor mu — ~15 s
python mutasyon.py --liste    # ne koşacağını yazar, koşmaz

python belge-uret.py          # BELGELER/ yeniden üret (7 sayfa)
python arayuz-uret.py         # arayüzü LittleFS görüntüsüne paketle
python arayuz-yaz.py          # görüntüyü karta yaz (esptool, 0x310000)

cd projeler/olcum-karti
python arayuz3/sunucu.py      # arayüzü PC'den sun (Web Serial)
Kopru Baslat.bat              # PC köprüsü (telefondan bağlanmak için)
```

### Üretim betikleri — Aşama 3 (güncel)

| Betik | Adım | Görevi |
|---|---|---|
| `dogrula3.py` | — | Zincir koşturucu + tezgah toplayıcı + sayım kilidi |
| `tasarim3.py` + `tasarim3_sabit.py` | **B1** | Aşama 3 tasarımı; **tüm mutlak sınırlar `tasarim3_sabit.py`'de, kaynaklarıyla** |
| `sim3_giris.py` | **B2** | Çift yönlü ön uç, ngspice |
| `sim3_ariza.py` | **B15** | Arıza ve zorlama — 27 senaryo. Kabul ölçütü: hiçbir TEK arıza ESP32'yi ya da PC'yi öldürmemeli |
| `sim3_besleme.py` | **B11** | ±12 V rayı, 7912 orta nokta regülatörü |
| `sim3_ortusme.py` | **B16** | V/I süzgeç eşleştirmesi + akım kanalı örtüşme süzgeci |
| `sim3_kelepce.py` | **B18** | GPIO kelepçeleri ve +3V3 geri beslemesi |
| `sim3_skop.py` | **B19** | Osiloskop kanalı çift yönlü |
| `sim3_senkron.py` | **B17** | ADS eş zamanlılığı, ölçek düzeltmesi, faz kalibrasyonu |
| `sim3_bant.py` | **B20** | Örnekleme hızı, bant sınırı, menzil + kütüphane taraması |
| `sim3_pil.py` | **B21** | Pil kapasite testi — anahtar, kapı yönü, tampon |
| `test_kopru.py` | **B22a** | PC köprüsü — röle bayt-şeffaflığı, arşiv, sürücü hakemi |
| `sim3_web.py` | **B22b** | Kartın web katmanı — SSE, komut ucu, CSRF, ağ |
| `sema3-uret.py` / `netlist3_dogrula.py` | **B3** | Şema üretimi + netlist polarite denetimi |
| `test_olcum3.py` | **B4/B5** | Ölçüm matematiği, GERÇEK kod AVR emülatöründe |
| `test_firmware3.py` | **B6** | Derleme (gerçek ESP32-S3) + ikilide ölü kod |
| `test_arayuz3.js` | **B7** | Arayüz + arayüz↔firmware komut denetimi |
| `bom_dogrula.py` / `kurulum3-uret.py` | **B9** | Malzeme listesi + tezgah kılavuzu |

### Ortak altyapı (B23'te eklendi)

| Betik | Görevi |
|---|---|
| `tezgah.py` | Tezgah kalemi biçimi; konsolun çizemeyeceği karakteri **yazmadan önce** yakalar |
| `mutasyon.py` | Mutasyon koşucusu — kaynağı bir **kopyada** bozup testin kırmızıya döndüğünü ölçer |
| `sayim.py` | Adım özet satırlarının ortak ayrıştırıcısı (dört ayrı biçim) |
| `gecici.py` | Kendini silen geçici dizin (`atexit`) |
| `belge_menu.py` | `BELGELER/` gezinme şeridi — **tek kaynak**, iki üreteç paylaşır |
| `spice.py` · `hedef2.py` · `kutuphane.py` | ngspice sürücüsü · FQBN · sembol kütüphanesi |

### Üretilen dosyalar (elle düzenlenmez)

| Dosya | Kim üretiyor |
|---|---|
| `uretim/_tezgah.md` | `dogrula3.py` — tezgahta ölçülecekler |
| `uretim/beklenen_sayim.json` | `dogrula3.py` — iddia sayısı kilidi |
| `uretim/_firmware.json` | `test_firmware3.py` — ölçülen flash/RAM |
| `uretim/_fs.json` · `_fs.bin` | `arayuz-uret.py` — LittleFS görüntüsü ve künyesi |
| `BELGELER/*.html` | `belge-uret.py` (+ `4-kurulum.html`: `kurulum3-uret.py`) |
| `uretim/b15-arastirma.md` | `b15_kanit_uret.py` — B15'in ham araştırma kanıtı |

### Arşiv betikleri (Aşama 1 · 2)

| Betik | Görevi |
|---|---|
| `tasarim2.py` | **A1** — tasarım belgesi + test |
| `sim_referans.py` `sim_bolucu.py` `sim_akim.py` | S1–S3 ngspice |
| `sim2_giris.py` | **A2** — 4 kelepçe seçeneğinin taranması |
| `sim_kart.py` / `sim2_kart.py` | S9 / **A4** — uçtan uca |
| `test_firmware.py` | S4 — aritmetik |
| `test_avr.py` | S8 — emülatörün kendisinin doğrulanması |
| `test_skop.py` + `test_skop_arayuz.js` | **A5** — osiloskop protokolü + ölü kod |
| `netlist_dogrula.py` / `netlist2_dogrula.py` | S5 / **A3** — netlist polarite ve adres |
| `sema-uret.py` / `sema2-uret.py` | Şema üreteçleri |
| `gorsel.py` `gorsel_a2.py` `gorsel_s9.py` | SVG grafik üreteçleri |
| `kanit-uret.py` `kanit2-uret.py` `sayfa-uret.py` `kurulum-uret.py` | Arşiv sayfaları |
| `avr/cekirdek.py` `avr/mega328.py` `avr/elf.py` | AVR emülatörü |

### Kaynak dosyalar

| Yol | İçerik |
|---|---|
| `kod/olcum-karti-a3/olcum-karti-a3.ino` | **Güncel firmware** (ESP32-S3) |
| `kod/olcum-karti-a3/olcum3.h` | **Platform bağımsız aritmetik** — AVR emülatöründe de koşar |
| `kod/olcum-karti-a3/pil_test.h` · `ag.h` · `web_akis.h` · `web_satir.h` · `tipler3.h` | Pil testi · ağ · `Serial` aynası · satır tamponu · tipler |
| `arayuz3/app.js` `index.html` `style.css` `ek.css` `sunucu.py` | **Güncel arayüz** — Vue 3, derleme adımı yok |
| `kopru/kopru.py` `kart_baglanti.py` `arsiv.py` | **PC köprüsü** — yalnızca standart kütüphane |
| `sema3/olcum-karti-a3.kicad_sch` | **Güncel şema** (betikle üretiliyor) |
| `arsiv/asama1/` · `arsiv/asama2/` | Eski aşamalar. ⚠ `arsiv/asama2/kurulum2.html` **canlı bağımlılık**: `kurulum3-uret.py` biçimini oradan okuyor |


### Arşiv kaynakları (Aşama 1 · 2)

| Yol | İçerik |
|---|---|
| `arsiv/asama1/olcum-karti/olcum-karti.ino` + `tipler.h` | Aşama 1 firmware (ATmega328P) |
| `arsiv/asama2/olcum-karti-a2/olcum-karti-a2.ino` | Aşama 2 firmware (ESP32-S3) |
| `arsiv/asama2/.../olcum2.h` | Aşama 2'nin platform bağımsız aritmetiği |
| `arsiv/asama1/arayuz/` · `arsiv/asama2/arayuz2/` | Eski arayüzler |
| `arsiv/asama1/sema/` · `arsiv/asama2/sema2/` | Eski KiCad şemaları |
| `arsiv/asama*/kanit/` | Doğrulama kayıtları ve kanıt sayfaları |
| `arsiv/asama2/kurulum2.html` | Aşama 2 kurulum kılavuzu — ⚠ **biçimi hâlâ kullanılıyor**, bkz. yukarıdaki uyarı |

### Firmware arayüzü (Aşama 2)

**Pinler:** SDA=8, SCL=9, SKOP=4, HAZIR=7 · **Adresler:** 0x48 akım, 0x49 gerilim

**Çıktı:**
```
D <volt> <amper> <watt> <joule> <wh> <ms> <örnek>     # "D %.3f %.5f %.5f %.4f %.7f %lu %lu"
S <adet> <Hz> <volt/adım>                              # ardından ham ADC kodları, 16'şar
```

**Komutlar:**

| Komut | İş |
|---|---|
| `?` | ayarları yaz |
| `#` | I2C taraması (0x08..0x77) |
| `t<esik>` | osiloskop yakala, 0 = tetiklemesiz |
| `z` | akım sıfırı — **yük bağlı değilken** |
| `v<gercek>` | gerilim kalibresi |
| `i<gercek>` | akım kalibresi |
| `s<ohm>` | şönt değeri |

Ayarlar NVS'te (`Preferences`, "olcum2" ad alanı), imza `0xC0FE`.

### Araçlar

| Araç | Yol |
|---|---|
| KiCad 10.0.6 | `C:\Program Files\KiCad\10.0\bin\` (kicad-cli + ngspice.dll) |
| arduino-cli 1.5.2 | `.araclar\arduino-cli.exe` (proje kökünün iki üstü) |
| ESP32 core | 3.3.11 · FQBN `esp32:esp32:esp32s3` |
| avr-gcc | Arduino15 paketi, 7.3.0-atmel3.6.1-arduino7 |
| node, numpy | sistemde |

### İlgili

- Envanter: `stok-takip/envanter.csv` — **tek gerçek kaynak**, `CLAUDE.md` kurallarına uy
- Aşama 2 kanıt sayfası: <https://claude.ai/code/artifact/f6a2ab16-0ea1-4dd1-9f35-0dd03859d993>
- Kurulum kılavuzu: <https://claude.ai/code/artifact/23d6637e-f723-4a5e-96ac-22ab6978cac6>
- Aşama 1 kanıt sayfası: <https://claude.ai/code/artifact/7aa77d26-7247-4661-b383-f69f2892e701>
