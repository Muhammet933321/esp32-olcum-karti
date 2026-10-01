# -*- coding: utf-8 -*-
"""Emule NOR flas — AVR testlerinde kayit gunlugunun altindaki 'disk' (B71).

Kayit gunlugu (kod/olcum-karti-a3/kayit_gunluk.h) kartta ESP32'nin
esp_partition_* cagrilariyla GERCEK NOR flasa yazar. AVR emulatorunde ayni
C kodu bu cevre birimine yazar. NOR'un iki kurali birebir:
  * yazma yalniz 1 -> 0 yapar (eski & yeni); 0'i 1'e ancak silme dondurur
  * silme bir SEKTORU 0xFF yapar ve ZAMAN alir (`sil_cevrim`)
Iki ariza modeli:
  * yazma bayt bayt ilerler: elektrik kesilirse kaydin bir kismi kalir
  * suren bir silme kesilirse sektor YARI SILINMIS kalir: baytlarin bir
    kismi 0xFF, bir kismi eski, bir kismi rastgele (`kes()`)

Yazmaclar (ATmega328P veri uzayinda REZERV adresler; gercek cipte bos,
emulatorde `gc_oku`/`gc_yaz` kancalari 0x20-0xFF arasinda calisiyor):
  0xE0 KOMUT   yaz 0x5E: adresin sektorunu sil · oku bit0: silme suruyor
  0xE1..0xE3   adres bayt 0/1/2 (kucuk uclu)
  0xE4 VERI    oku: bayt, adres++ · yaz: bayt &= v, adres++
  0xE5 ARIZA_OKU  yaz n: sonraki n. okuma baytinda islem BASARISIZ olur
  0xE6 ARIZA_YAZ  yaz n: sonraki n. yazma baytinda islem BASARISIZ olur
       Basarisiz islem, durum (KOMUT) okunana kadar surer: okumalar 0xFF
       dondurur, yazmalar PROGRAMLANMAZ. Durum bit1 = "son islem hatali",
       okununca temizlenir. Yalniz TEST icin (son inceleme bulgu 4: flas
       G/C hata yollari hic sinanmiyordu).
"""
from __future__ import annotations

import random

KOMUT, A0, A1, A2, VERI = 0xE0, 0xE1, 0xE2, 0xE3, 0xE4
ARIZA_OKU, ARIZA_YAZ = 0xE5, 0xE6
SIL = 0x5E
# B72: emule NVS (ESP32 Preferences yerine). Anahtar SIRA ile; deger u32.
# Degerler NorFlas nesnesinde kalir -> acilistan acilisa KALICI.
NVS_ANAHTAR, NVS_V0, NVS_KOMUT = 0xE7, 0xE8, 0xEC     # V0..V3 = 0xE8..0xEB
NVS_ADLAR = ["acilis", "kimlik", "taban", "onay", "kapat", "t_adim", "t_rast",
             "pl_bas", "pl_sure", "pl_hiz", "pl_no", "pl_dur", "pl_ot", "pl_bu"]   # 1C-4
# 1B: ADA gore blob (kalibrasyon gecmisi). 0xED ad portu (karakter karakter,
# komut adi tuketir) · 0xEE veri portu (yaz: tampona ekle, oku: siradaki
# bayt) · 0xEF NVS'te bos giris (Python `nvs_bos` ile ayarlar).
# Komut 3 = blob oku (durum bit0: var; V0..V1 = uzunluk) · 4 = blob yaz.
NVS_AD, NVS_BLOB, NVS_BOS = 0xED, 0xEE, 0xEF


class NorFlas:
    def __init__(self, boyut: int, sektor: int = 4096, sil_cevrim: int = 0):
        if boyut % sektor:
            raise ValueError("boyut sektorun kati olmali")
        self.bellek = bytearray(b"\xff" * boyut)
        self.sektor = sektor
        self.sil_cevrim = sil_cevrim
        self.adres = 0
        self.cpu = None
        self._silinen: int | None = None    # suren silmenin sektor adresi
        self._sil_bitis = 0
        self.yazilan_bayt = 0
        self.silme_adet = 0
        self.kesilen_silme = 0
        self.okunan_bayt = 0      # kurtarma maliyeti olculsun (B72)
        self.nvs: dict[str, int] = {}          # B72: kalici NVS
        self.nvs_hata: set[str] = set()        # bu anahtarlara YAZMA basarisiz
        self.nvs_gunluk: list[tuple] = []      # (ad, deger, silme_adet, yazilan_bayt)
        self._nvs_i = 0
        self._nvs_v = [0, 0, 0, 0]
        self._nvs_d = 0
        self.nvs_bos = 200                     # 1B: emule "bos giris" (nvs_get_stats)
        self._nvs_ad = bytearray()
        self._nvs_yaz_tampon = bytearray()
        self._nvs_oku_tampon = b""
        self._nvs_oku_i = 0
        self._ariza_oku = 0       # n > 0: n. okuma baytinda hata
        self._ariza_yaz = 0
        self._hata = False        # durum okunana kadar islem basarisiz

    # ------------------------------------------------------------ baglanti
    def tak(self, kart) -> None:
        """Yazmaclari bir emulator kartina bagla (her acilista yeniden)."""
        self.cpu = kart.cpu
        o, y = kart.cpu.gc_oku, kart.cpu.gc_yaz
        y[A0] = lambda v: self._adres_bayt(0, v)
        y[A1] = lambda v: self._adres_bayt(1, v)
        y[A2] = lambda v: self._adres_bayt(2, v)
        o[VERI] = self._veri_oku
        y[VERI] = self._veri_yaz
        o[KOMUT] = self._durum
        y[KOMUT] = self._komut
        y[ARIZA_OKU] = lambda v: setattr(self, "_ariza_oku", v & 0xFF)
        y[ARIZA_YAZ] = lambda v: setattr(self, "_ariza_yaz", v & 0xFF)
        y[NVS_ANAHTAR] = lambda v: setattr(self, "_nvs_i", v & 0xFF)
        for j in range(4):
            y[NVS_V0 + j] = (lambda j: lambda v: self._nvs_v.__setitem__(j, v & 0xFF))(j)
            o[NVS_V0 + j] = (lambda j: lambda: self._nvs_v[j])(j)
        y[NVS_KOMUT] = self._nvs_komut
        o[NVS_KOMUT] = lambda: self._nvs_d
        y[NVS_AD] = lambda v: self._nvs_ad.append(v & 0xFF)
        y[NVS_BLOB] = lambda v: self._nvs_yaz_tampon.append(v & 0xFF)
        o[NVS_BLOB] = self._nvs_blob_oku
        o[NVS_BOS] = lambda: max(0, min(255, self.nvs_bos))

    def _nvs_blob_oku(self) -> int:
        if self._nvs_oku_i >= len(self._nvs_oku_tampon):
            return 0xFF
        v = self._nvs_oku_tampon[self._nvs_oku_i]
        self._nvs_oku_i += 1
        return v

    # ------------------------------------------------------------ NVS
    def _nvs_komut(self, v: int) -> None:
        """1 = oku (durum bit0: anahtar var) · 2 = yaz (durum bit1: HATA)."""
        ad = NVS_ADLAR[self._nvs_i] if self._nvs_i < len(NVS_ADLAR) else f"?{self._nvs_i}"
        if v == 1:
            d = self.nvs.get(ad)
            self._nvs_v = list((d or 0).to_bytes(4, "little"))
            self._nvs_d = 1 if d is not None else 0
        elif v == 2:
            if ad in self.nvs_hata:
                self._nvs_d = 2
                return
            deger = int.from_bytes(bytes(self._nvs_v), "little")
            self.nvs[ad] = deger
            self.nvs_gunluk.append((ad, deger, self.silme_adet, self.yazilan_bayt))
            self._nvs_d = 0
        elif v in (3, 4):                     # 1B: ADA gore blob
            ad = self._nvs_ad.decode("ascii", "replace")
            self._nvs_ad = bytearray()
            if v == 3:
                d = self.nvs.get(ad)
                self._nvs_oku_tampon = d if isinstance(d, bytes) else b""
                self._nvs_oku_i = 0
                n = len(self._nvs_oku_tampon)
                self._nvs_v = [n & 0xFF, (n >> 8) & 0xFF, 0, 0]
                self._nvs_d = 1 if isinstance(d, bytes) else 0
            else:
                veri = bytes(self._nvs_yaz_tampon)
                self._nvs_yaz_tampon = bytearray()
                if ad in self.nvs_hata:
                    self._nvs_d = 2
                    return
                self.nvs[ad] = veri
                self.nvs_gunluk.append((ad, veri, self.silme_adet, self.yazilan_bayt))
                self._nvs_d = 0
        else:
            raise RuntimeError(f"bilinmeyen NVS komutu {v}")

    def _adres_bayt(self, i: int, v: int) -> None:
        self.adres = (self.adres & ~(0xFF << (8 * i))) | ((v & 0xFF) << (8 * i))

    # ------------------------------------------------------------ silme
    def _silme_bitti_mi(self) -> None:
        if (self._silinen is not None and self.cpu is not None
                and self.cpu.cevrim >= self._sil_bitis):
            s = self._silinen
            self.bellek[s:s + self.sektor] = b"\xff" * self.sektor
            self._silinen = None

    def _mesgul(self, a: int) -> bool:
        return (self._silinen is not None
                and self._silinen <= a < self._silinen + self.sektor)

    def _alan(self, a: int) -> None:
        if not 0 <= a < len(self.bellek):
            raise IndexError(f"NOR erisimi alan disi: {a:#x}")

    # ------------------------------------------------------------ yazmaclar
    def _veri_oku(self) -> int:
        self._silme_bitti_mi()
        a = self.adres
        self._alan(a)
        self.adres = a + 1
        self.okunan_bayt += 1
        if self._ariza_oku:
            self._ariza_oku -= 1
            if not self._ariza_oku:
                self._hata = True
        if self._hata:
            return 0xFF
        return 0xFF if self._mesgul(a) else self.bellek[a]

    def _veri_yaz(self, v: int) -> None:
        self._silme_bitti_mi()
        a = self.adres
        self._alan(a)
        if self._mesgul(a):
            raise RuntimeError(f"silme surerken yazma: {a:#x}")
        if self._ariza_yaz:
            self._ariza_yaz -= 1
            if not self._ariza_yaz:
                self._hata = True
        if self._hata:
            self.adres = a + 1
            return
        self.bellek[a] &= v & 0xFF
        self.adres = a + 1
        self.yazilan_bayt += 1

    def _komut(self, v: int) -> None:
        self._silme_bitti_mi()
        if v != SIL:
            raise RuntimeError(f"bilinmeyen NOR komutu {v:#x}")
        s = (self.adres // self.sektor) * self.sektor
        self._alan(s)
        self.silme_adet += 1
        if self.sil_cevrim <= 0 or self.cpu is None:
            self.bellek[s:s + self.sektor] = b"\xff" * self.sektor
        else:
            self._silinen = s
            self._sil_bitis = self.cpu.cevrim + self.sil_cevrim

    def _durum(self) -> int:
        self._silme_bitti_mi()
        v = (1 if self._silinen is not None else 0) | (2 if self._hata else 0)
        self._hata = False
        return v

    # ------------------------------------------------------------ ariza
    def kes(self, rng: random.Random) -> None:
        """Elektrik kesildi. Suren bir silme YARIM kalir."""
        self._silme_bitti_mi()
        if self._silinen is not None:
            s = self._silinen
            for a in range(s, s + self.sektor):
                r = rng.random()
                if r < 0.45:
                    self.bellek[a] = 0xFF
                elif r < 0.55:
                    self.bellek[a] = rng.randrange(256)
                # kalan %45: eski bayt oldugu gibi
            self._silinen = None
            self.kesilen_silme += 1
        self.cpu = None
