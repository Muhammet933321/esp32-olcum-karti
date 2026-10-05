# Diğer oturumdan istekler (alt proje 5 → firmware / ortak / PC)

Bu dosyayı Android oturumu yazar; paylaşılan dosyaları kendisi DEĞİŞTİRMEZ.

| # | Tarih | Ne | Neden | Hangi dosya | Durum |
|---|---|---|---|---|---|
| 1 | 2026-10-03 | `MDNS.addService("http", "tcp", 80)` ve TXT kaydında kart kimliği (16 onaltılık) | Android `.local` adlarını güvenilir çözmez; NSD servis taraması gerekir. TXT'deki kimlik, yanlış cihazı bağlanmadan elemeye yarar (asıl doğrulama yine `/eslestir/bilgi`) | `kod/olcum-karti-a3/ag.h` (`MDNS.begin` sonrası, iki yerde) | ✅ Geldi (2026-10-04): Xiaomi'de NSD ile görüldü, TXT kimliği `/eslestir/bilgi` ile aynı |
| 2 | 2026-10-05 | Panelin SAF kayıt yardımcılarının `ortak/src/`'a taşınması (ya da dışa aktarımlarının sabit tutulması): `grafikSerileri`, `gorunurluk`, `okumaHesapla`, `notListesi`, `tarihYaz` (`arayuz3/ekran/kayit_gorunum.js`) ve `listeBirlestir`, `satirSuz` (`arayuz3/ekran/kayitlar.js`) | Telefon bunları KOPYALAMADAN içe aktarıyor (`@panel` takma adı; PC ve telefon aynı kayıtta aynı sayıyı versin). Şimdilik çalışıyor ama `kayitlar.js` panelin IndexedDB / eşitleme zincirini de çekiyor ve imza değişirse telefon derlemesi kırılır (telefonun testleri bunu kırmızıyla yakalar: `mobil/test/kayit_veri.test.js`) | `arayuz3/ekran/kayit_gorunum.js`, `arayuz3/ekran/kayitlar.js` → öneri `ortak/src/kayit_ekran.js` | Açık — acil değil |

## Bilgi (istek değil)

- `ortak/src/imza.js` `ac()` kart kimliğini denetlemiyor (alt proje 4 spec'i 4B-15'te açık olarak
  yazılı). Telefon denetimi kendi sarmalayıcısında yapıyor; `ortak/`'ta değişiklik istenmiyor.
