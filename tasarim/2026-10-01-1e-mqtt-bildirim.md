# 1E — MQTT bildirimleri (kart tarafı)

> Üst tasarım: `2026-09-29-yazilim-sistemi.md` §8 "Bildirimler" ve "MQTT düzeni" (onaylı),
> §6 sırların aktarımı, §11 riskler. Bu belge kartın yapacağını ve PC'deki küçük doğrulama
> dinleyicisini kesinleştirir. Telefon uygulaması alt proje 5, PC uygulaması alt proje 4.
> Kullanıcı 2026-10-01: "devam edelim"; kararlar önerilerle, kritik olanlar aşağıda ayrı.

## Amaç

Kayıt sürerken kart düşerse ya da bir olay olursa telefona/PC'ye **dışarıdayken de**
haber gitsin. Kart düşmesi: hedef ≤ 10 s, kabul ≤ 15 s (Ö4).

## Kararlar

| # | Karar | Gerekçe |
|---|---|---|
| K1 | **İstemci:** çekirdekteki ESP-IDF **esp-mqtt** (Arduino-ESP32 3.3.11'de hazır, MQTT 3.1.1, TLS). Kendi görevinde, **çekirdek 0**. TLS doğrulaması `esp_crt_bundle_attach` (CA demeti; sertifika depoda tutulmaz) | Ek kütüphane yok; yeniden bağlanma ve giden kutusu hazır; ölçüm çekirdeği (1) etkilenmez |
| K2 | **Aracı:** HiveMQ Cloud Serverless (ücretsiz: 100 bağlantı, 10 GB/ay, TLS 8883, WebSocket 8884). Kart aracıdan bağımsız: yalnız URI + kullanıcı + parola. EMQX Serverless ya da kendi Mosquitto'ya geçiş = ayar değişikliği | Trafik payı en geniş; tahmini kullanım ≤ 100 MB/ay |
| K3 | **İki aracı kullanıcısı:** `kart` (yayın + abone, `ok/<önek>/#`) ve `cihaz` (yalnız abone, `ok/<önek>/#`). Kart ikisini de NVS'te tutar (`mqtt` ad alanı), cihaz bilgisini yalnız eşleşmiş cihazlara verir (K10). **Depoya asla** | Cihaz parolası sızsa bile sahte yayın yapılamaz |
| K4 | **Konular:** `ok/<önek>/durum` (retained), `ok/<önek>/olay` (QoS 1). `<önek>` = 16 B rastgele → 32 küçük hex; ilk kurulumda üretilir (NVS) | Tahmin edilemez konu; aracıda başka kullanıcıların konularıyla karışmaz |
| K5 | ⚠ **Uçtan uca şifreleme:** her yük **ChaCha20-Poly1305 IETF** (RFC 8439) ile, kartın ürettiği 32 B **bildirim anahtarı** (`mqtt/anahtar`) ile şifrelenir; AAD = konu adı. Zarf biçimi aşağıda | Aracı içerik okuyamaz, sahte olay üretemez (etiket tutmaz). §6 sırlar için ChaCha20-Poly1305 zaten gerekiyor |
| K6 | **Durum (retained):** bağlanınca, değişince ve **60 s'de bir** (son görülme). Vasiyet (LWT): aynı konu, `{"c":0,…}`, retained, QoS 1 — **her bağlanışta yeni nonce ile** şifrelenir | Uygulama açılır açılmaz son durumu görür; ~6 MB/ay |
| K7 | **Olaylar:** `kayit_bitti` (sebep, oturum, nokta) · `pil_bitti` (durum, mAh, Wh, süre) · `dolu` · `esik` (eşitlenmemiş ≥ eşik; tekrar ancak eşiğin 100 binde altına inip yeniden çıkınca) · `basladi` (açılış; açık oturum DEVAM aldı mı / kapandı mı). Her olayda açılış başına artan `no` (tekrar ayıklama). İnternet yokken RAM kuyruğu **16** olay; taşarsa en eskisi düşer, düşen sayılır | §8 olay listesi. Ölçüm verisi yayınlanmaz (dışarıdan canlı izleme kapsam dışı) |
| K8 | ⚠ **Bağlantı:** yalnız STA kipinde ve ayar tamamsa **sürekli**; keepalive **5 s** (aracı 7.5 s'de ilan eder). AP kipinde MQTT yok, `Q?` söyler | Olayların hemen gitmesi; Ö4 |
| K9 | **Ayar yalnız USB:** `Q?` durum (sır yazmaz) · `Qu<uri>` · `Qk<kart kullanıcı>` · `Qp<kart parola>` · `Qc<cihaz kullanıcı>` · `Qd<cihaz parola>` · `Q1`/`Q0` aç/kapat · `Qt` deneme olayı · `Qv` kendi sınaması (RFC 8439 vektörü). Web `/komut` ve köprü `Q`'yu reddeder (E gibi) | Sırlar ağa çıkmaz |
| K10 | **Cihazlara dağıtım:** imzalı `GET /bildirim/bilgi` (sınıf CİHAZ, yalnız eşleşmiş). Yanıt = ChaCha20-Poly1305(K_cihaz, JSON{uri, kullanici, parola, onek, anahtar}), AAD = `OK1-bildirim\n<kimlik>\n<n>` | §6; cihaz anahtarı `K` 1D'den |
| K11 | **RAM ölçütü:** bağlıyken boş yığın ≥ 60 KB ve ölçüm döngüsünde yeni blokaj yok (`K` satırı `loop_azami` değişmez). Tutmazsa: yalnız kayıt sürerken bağlan (§11 yedek planı) | §11 riski |
| K12 | **PC dinleyicisi** `kopru/bildirim.py`: yalnız standart kütüphane — saf Python ChaCha20-Poly1305 (`kopru/chacha.py`, RFC 8439 vektörleri) + asgari MQTT 3.1.1 istemcisi (`kopru/mqtt_istemci.py`, `ssl` + `socket`). Tezgah ve alt proje 4 bunu kullanır | Proje kuralı (stdlib) |

### Zarf biçimi (kart ve PC birebir)

```
bayt 0..3   "OKB1"            sürüm/imza
bayt 4..15  nonce (12 B)      rastgele (RF açıkken üretilir)
bayt 16..   şifreli metin     ChaCha20-Poly1305 IETF, anahtar = bildirim anahtarı
son 16 B    etiket
AAD         konu adının UTF-8 baytları (ör. "ok/<önek>/durum")
düz metin   kısa JSON (UTF-8)
```

Durum düz metni: `{"c":1,"a":<açılış>,"t":<unix|0>,"k":<kayıt durumu>,"o":<oturum>,
"y":<oturum türü>,"d":<doluluk binde>,"e":<eşitlenmemiş binde>,"f":"<firmware>"}`;
vasiyet: `{"c":0,"a":<açılış>}`.
Olay düz metni: `{"n":<no>,"a":<açılış>,"t":<unix|0>,"o":"<olay adı>", …alanlar}`.

## Akış

1. USB'den `Qu/Qk/Qp/Qc/Qd` + `Q1` → NVS. Önek ve anahtar yoksa üretilir.
2. STA bağlanınca görev esp-mqtt'yi başlatır (vasiyet şifrelenmiş). Bağlanınca durum yayınlar.
3. Çekirdek 0 her turda kayıt/pil/açılış anlık görüntüsünü platformsuz olay üreticisine verir;
   üretilen olaylar kuyruğa, bağlıysa yayına.
4. Eşleşmiş cihaz `/bildirim/bilgi`'den şifreli bilgileri alır, aboneliği kurar.

## Doğrulama

- **AVR (B71):** platformsuz `bildirim.h` — olay üretimi (anlık görüntü dizileri), eşik
  histerezisi, kuyruk taşması, `no` sırası, zarf baytlarının yerleşimi (sahte AEAD ile).
- **B72:** kaynak iddiaları (görev çekirdek 0, keepalive 5, vasiyet retained/QoS1, `Q` yalnız
  USB, `/bildirim/bilgi` CİHAZ sınıfı, durum satırı sır yazmıyor) + PC dinleyicisi sahte aracıya
  karşı (yerel TCP) + saf Python ChaCha20-Poly1305 RFC 8439 vektörleri + istemci–kart zarf
  uyumu.
- **Kart:** `Qv` kendi sınaması (RFC 8439) · kartın yayınladığı zarfı PC çözer · fiş çekme →
  vasiyet ≤ 15 s (hedef 10), **10 tekrar** · RAM ölçütü (K11).
- Mutasyon: her yeni iddianın yalanlayıcısı.

## ⚠ Onay bekleyen kritik kararlar

1. **K5 uçtan uca şifreleme** — önerim evet (aracı içerik görmez, sahte olay yok).
2. **K8 sürekli bağlantı** — önerim evet; RAM ölçütü (K11) tutmazsa yalnız kayıt sürerken.
3. **K2 HiveMQ** — hesabı kullanıcı açar (kart tezgahından önce); iki kullanıcı (K3).
4. **K6 60 s'de bir durum** — "son görülme" için; ~6 MB/ay.

## Kapsam dışı

Telefon/PC uygulamalarının bildirim arayüzü (alt proje 4/5) · uzaktan yönetim · dışarıdan canlı
veri · MQTT 5 · kalıcı (flaşta) olay kuyruğu.
