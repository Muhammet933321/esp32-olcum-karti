# Diğer oturumdan istekler (alt proje 5 → firmware / ortak / PC)

Bu dosyayı Android oturumu yazar; paylaşılan dosyaları kendisi DEĞİŞTİRMEZ.

| # | Tarih | Ne | Neden | Hangi dosya | Durum |
|---|---|---|---|---|---|
| 1 | 2026-10-03 | `MDNS.addService("http", "tcp", 80)` ve TXT kaydında kart kimliği (16 onaltılık) | Android `.local` adlarını güvenilir çözmez; NSD servis taraması gerekir. TXT'deki kimlik, yanlış cihazı bağlanmadan elemeye yarar (asıl doğrulama yine `/eslestir/bilgi`) | `kod/olcum-karti-a3/ag.h` (`MDNS.begin` sonrası, iki yerde) | Planlı; telefon buna bağımlı değil |

## Bilgi (istek değil)

- `ortak/src/imza.js` `ac()` kart kimliğini denetlemiyor (alt proje 4 spec'i 4B-15'te açık olarak
  yazılı). Telefon denetimi kendi sarmalayıcısında yapıyor; `ortak/`'ta değişiklik istenmiyor.
