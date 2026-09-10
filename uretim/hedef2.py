# -*- coding: utf-8 -*-
"""Asama 2 derleme hedefi — TEK KAYNAK.

NEDEN AYRI DOSYA: FQBN daha once `sim2_kart.py` ve `test_skop.py` icinde
AYRI AYRI yaziliydi. Ikisi de duz `esp32:esp32:esp32s3` diyordu, yani
PSRAM kapaliydi (kart varsayilani `PSRAM=disabled`). Iki kopya oldugu icin
birini duzeltip otekini unutmak mumkundu. Artik tek yerden geliyor.

KUSUR (DEVIR 4.9): PSRAM acik olmadan `ps_malloc()` / `heap_caps_malloc(
MALLOC_CAP_SPIRAM)` SESSIZCE NULL doner. Bugun firmware PSRAM kullanmiyor,
ama derin skop bellegi (500 000 ornek) icin ayrilmaya calisildiginda skop
hic acilmaz ve sebebi gorunmez.

  N16R8  ->  16 MB flash + 8 MB OKTAL PSRAM  ->  PSRAM=opi

⚠ TEZGAH NOTU: bazi "N16R8" etiketli kartlarda quad PSRAM cikiyor. Firmware
acilista `psramFound()` sonucunu yaziyor; "PSRAM: yok" gorursen bu dosyada
PSRAM=opi yerine PSRAM=enabled (quad) dene. Derleme basarili olmasi kartta
PSRAM bulundugunu KANITLAMAZ — kanit acilis satiridir.
"""
from __future__ import annotations

# Kart ailesi (secenek eki olmadan) — regresyon denetimleri bunu kullanir.
KART = "esp32:esp32:esp32s3"

# Secenekler:
#   PSRAM=opi              8 MB oktal PSRAM (N16R8) — 4.9'un asil duzeltmesi
#   FlashSize=16M          N16R8'in gercek flash boyutu (varsayilan 4M idi)
#   PartitionScheme=huge_app   3 MB uygulama — 473 KB'lik firmware buyuyecek
#
# BILEREK EKLENMEDI: CDCOnBoot=cdc / USBMode=hwcdc. Bunlar `Serial`i UART
# koprusunden yerel USB CDC'ye tasir; 4.11 (ikili aktarim) icin gerekli ama
# tezgah ilk acilisini bozabilecegi icin o is ayri ele alinacak.
SECENEKLER = "PSRAM=opi,FlashSize=16M,PartitionScheme=huge_app"

FQBN = f"{KART}:{SECENEKLER}"


def secenek_sozlugu() -> dict[str, str]:
    """FQBN'in secenek kismini ayristirir (testlerin okumasi icin)."""
    return dict(p.split("=", 1) for p in SECENEKLER.split(","))
