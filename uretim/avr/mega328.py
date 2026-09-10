# -*- coding: utf-8 -*-
"""ATmega328P cevre birimleri — Timer0, ADC, USART0, EEPROM.

Firmware'in gercekten dokundugu her sey burada. Dokunmadigi seyler (SPI, TWI,
Timer1/2 kesmeleri, PWM cikislari) bilerek YOK: yazmalari sessizce yutuluyor.
Bir gun firmware onlari kullanmaya baslarsa test coker — bu istenen davranis,
sessizce yanlis cevap vermekten iyidir.

ADC modeli, ATmega328/P veri sayfasindan (Atmel-42735B, 11/2016) DOGRULANMIS
degerleri kullanir — hicbiri hafizadan yazilmadi:

  Tablo 28-1 "ADC Conversion Time"
    ilk donusum                      ornekle-tut 13.5 saat,  toplam 25 saat
    normal, tek uclu                 ornekle-tut  1.5 saat,  toplam 13 saat
    otomatik tetiklemeli             ornekle-tut  2   saat,  toplam 13.5 saat

  Sekil 28-7 "ADC Timing Diagram, Free Running Conversion"
    Serbest calismada cevrim 13 saat: 13. saatte donusum biter, hemen
    ardindan yeni donusumun 1. saati baslar, ornekle-tut 2. saatte olur.
    Tablo 28-1'in 13.5'i prescaler'in sifirlandigi DIS tetikleme icindir;
    serbest calismada prescaler sifirlanmaz. Bu modelde 13 kullaniliyor —
    firmware'in 76923 Hz sabiti de (16 MHz / 16 / 13) bununla tutarli.

  Sekil 28-8 "Analog Input Circuitry"
    C_S/H = 14 pF, seri direnc 1..100 kohm, alt plaka VCC/2'ye bagli.
    Ayni sayfa: "The ADC is optimized for analog signals with an output
    impedance of approximately 10 kohm or less. If such a source is used,
    the sampling time will be negligible."

  Bolum 28.7 sonuc denklemi: ADC = V_in x 1024 / V_REF  (asagi yuvarlar)

Kaynak direnci verilirse RC oturmasi hesaplanir; boylece "kanal sizmasi"
iddiasi VARSAYIM degil, olculebilir bir buyukluk haline gelir. Bolucu
dugumu 9.09 kohm, yani veri sayfasinin 10 kohm sinirinin ICINDE.
"""
from __future__ import annotations

import math

F_CPU = 16_000_000

# --- G/C adresleri (ATmega328P veri sayfasi, Bolum 36)
TIFR0, TIFR1, TIFR2 = 0x35, 0x36, 0x37
EECR, EEDR, EEARL, EEARH = 0x3F, 0x40, 0x41, 0x42
TCCR0A, TCCR0B, TCNT0, OCR0A, OCR0B = 0x44, 0x45, 0x46, 0x47, 0x48
SMCR, MCUSR = 0x53, 0x54
SPMCSR = 0x57
WDTCSR, CLKPR = 0x60, 0x61
PRR = 0x64
TIMSK0, TIMSK1, TIMSK2 = 0x6E, 0x6F, 0x70
ADCL, ADCH, ADCSRA, ADCSRB, ADMUX, DIDR0 = 0x78, 0x79, 0x7A, 0x7B, 0x7C, 0x7E
UCSR0A, UCSR0B, UCSR0C = 0xC0, 0xC1, 0xC2
UBRR0L, UBRR0H, UDR0 = 0xC4, 0xC5, 0xC6

# --- kesme vektorleri (bayt adresi)
V_TIMER0_OVF = 0x0040
V_USART_RX = 0x0048
V_USART_UDRE = 0x004C
V_ADC = 0x0054

# Timer0 saat secimi (CS02:0) — Tablo 19-9. 6/7 dis saat, bu kartta kullanilmiyor.
T0_ONBOLUCU = {0: 0, 1: 1, 2: 8, 3: 64, 4: 256, 5: 1024, 6: 0, 7: 0}

# ADC on bolucusu (ADPS2:0) — Tablo 24-5. AYRI BIR TABLO: Timer0'inkiyle
# karistirmak ADC'yi 64 kat hizlandirip yanlis ornekleme hizi ve sahte
# kanal sizmasi uretir.
ADC_ONBOLUCU = (2, 2, 4, 8, 16, 32, 64, 128)

C_SH = 14e-12          # ornekle-tut kondansatoru (F)


class Kart:
    """ATmega328P + firmware'in gordugu dis dunya."""

    def __init__(self, flash: bytearray, cekirdek_sinifi,
                 aref: float = 2.470,
                 kanal_gerilim=None,
                 kaynak_direnc: float = 0.0,
                 eeprom: bytearray | None = None):
        self.cpu = cekirdek_sinifi(flash)
        self.aref = aref
        self.kanal_gerilim = kanal_gerilim or (lambda k: 0.0)
        self.kaynak_direnc = kaynak_direnc
        self.eeprom = eeprom if eeprom is not None else bytearray(b"\xff" * 1024)

        # --- Timer0
        self.t0_taban = 0          # TCNT0 = 0 oldugu andaki cevrim
        self.t0_onbol = 0

        # --- ADC
        self.adc_bitis = None      # donusumun bitecegi cevrim
        self.adc_sonuc = 0
        self.adc_kilit = False     # ADCL okundu, ADCH bekleniyor
        self.adc_bekleyen = None
        self.sh_gerilim = 0.0      # ornekle-tut kondansatorunun tasidigi yuk
        self.adc_ilk = True
        self.adc_donusum = 0
        self.ornek_cevrim = 0   # orneklemenin tamamlandigi ideal cevrim

        # --- USART
        self.tx = bytearray()      # karttan cikan her sey
        self.rx_kuyruk = bytearray()
        self.rx_dolu = False
        self.rx_bayt = 0
        self.rx_hazir_cevrim = 0
        self.udr_dolu = False      # veri kaydedicisi dolu (UDRE = 0)
        self.udr_bekleyen = 0
        self.kaydirma_bitis = 0    # kaydirma kaydedicisi ne zaman bosalir
        self.bit_cevrim = 1666     # UBRR yazilinca guncellenir

        self._kancalari_tak()

    # ------------------------------------------------------------- kanca
    def _kancalari_tak(self) -> None:
        o, y = self.cpu.gc_oku, self.cpu.gc_yaz
        o[TCNT0] = self._tcnt0_oku
        y[TCCR0B] = self._tccr0b_yaz
        y[TCNT0] = self._tcnt0_yaz
        y[TIFR0] = self._tifr0_yaz

        y[ADCSRA] = self._adcsra_yaz
        o[ADCL] = self._adcl_oku
        o[ADCH] = self._adch_oku

        o[UCSR0A] = self._ucsr0a_oku
        y[UCSR0A] = self._ucsr0a_yaz
        y[UDR0] = self._udr0_yaz
        o[UDR0] = self._udr0_oku
        y[UBRR0L] = self._ubrr_yaz
        y[UBRR0H] = self._ubrr_yaz

        y[EECR] = self._eecr_yaz

    # ------------------------------------------------------------ Timer0
    def _tcnt0_oku(self) -> int:
        if self.t0_onbol == 0:
            return self.cpu.m[TCNT0]
        return ((self.cpu.cevrim - self.t0_taban) // self.t0_onbol) & 0xFF

    def _tcnt0_yaz(self, v: int) -> None:
        self.t0_taban = self.cpu.cevrim - v * max(self.t0_onbol, 1)

    def _tccr0b_yaz(self, v: int) -> None:
        yeni = T0_ONBOLUCU[v & 0x07]
        if yeni != self.t0_onbol:
            self.t0_onbol = yeni
            self.t0_taban = self.cpu.cevrim

    def _tifr0_yaz(self, v: int) -> None:
        # bayrak yazmakla TEMIZLENIR (1 yaz -> sil)
        self.cpu.m[TIFR0] &= ~v & 0xFF

    def _timer0_isle(self) -> None:
        if self.t0_onbol == 0:
            return
        gecen = self.cpu.cevrim - self.t0_taban
        if gecen >= 256 * self.t0_onbol:
            self.t0_taban += 256 * self.t0_onbol
            self.cpu.m[TIFR0] |= 0x01          # TOV0

    # --------------------------------------------------------------- ADC
    def _adcsra_yaz(self, v: int) -> None:
        if v & 0x10:                            # ADIF'e 1 yazilirsa temizle
            self.cpu.m[ADCSRA] &= ~0x10 & 0xFF
        if (v & 0x80) and (v & 0x40) and self.adc_bitis is None:
            self._donusum_baslat()

    def _adc_saat(self) -> int:
        return ADC_ONBOLUCU[self.cpu.m[ADCSRA] & 0x07]

    def _donusum_baslat(self, baslangic: int | None = None) -> None:
        """Donusumu baslatir.

        `baslangic` verilmezse su anki cevrim kullanilir. SERBEST CALISMADA
        bir onceki donusumun IDEAL bitis cevrimi verilmelidir: donanimda
        donusumler ADC saatine kilitlidir, oysa simulator bitisi ancak komut
        sinirinda fark eder. Her turda o gecikmeyi tabana eklersek ornekleme
        araligi yavasca uzar; 1000 ornekte bu, temel frekansin etrafinda
        yan bantlar olarak goruluyordu (RMS artik 30 mV yerine 78 mV).
        """
        saat = self._adc_saat()
        kanal = self.cpu.m[ADMUX] & 0x0F
        t0 = self.cpu.cevrim if baslangic is None else baslangic
        if self.adc_ilk:
            ornek_saat, toplam_saat = 13.5, 25       # Tablo 28-1, ilk donusum
        elif self.cpu.m[ADCSRA] & 0x20:              # ADATE: serbest calisma
            ornek_saat, toplam_saat = 2.0, 13        # Tablo 28-1 + Sekil 28-7
        else:
            ornek_saat, toplam_saat = 1.5, 13        # Tablo 28-1, normal tek uclu
        self.adc_ilk = False
        # Ornekleme, donusumun basindan ornek_saat kadar sonra tamamlanir.
        # Dis dunya gerilimi TAM O ANDA okunmali, komutun calistigi anda degil.
        self.ornek_cevrim = t0 + int(ornek_saat * saat)

        # --- ornekle-tut: kaynak direnci uzerinden RC ile dolar
        kaynak = self.kanal_gerilim(kanal)
        if self.kaynak_direnc > 0:
            t = ornek_saat * saat / F_CPU
            tau = self.kaynak_direnc * C_SH
            k = 1.0 - math.exp(-t / tau) if tau > 0 else 1.0
            self.sh_gerilim += (kaynak - self.sh_gerilim) * k
        else:
            self.sh_gerilim = kaynak

        ham = int(self.sh_gerilim / self.aref * 1024.0)   # veri sayfasi denklemi
        self.adc_bekleyen = 0 if ham < 0 else (1023 if ham > 1023 else ham)
        self.adc_bitis = t0 + int(toplam_saat * saat)

    def _adc_isle(self) -> None:
        if self.adc_bitis is None or self.cpu.cevrim < self.adc_bitis:
            return
        bitis = self.adc_bitis
        self.adc_bitis = None
        self.adc_sonuc = self.adc_bekleyen
        self.adc_donusum += 1
        if not self.adc_kilit:
            self._sonucu_yaz()
        self.cpu.m[ADCSRA] |= 0x10              # ADIF
        self.cpu.m[ADCSRA] &= ~0x40 & 0xFF      # ADSC temizlenir
        if self.cpu.m[ADCSRA] & 0x20:           # ADATE: serbest calisma
            self.cpu.m[ADCSRA] |= 0x40
            # Bir sonraki donusum IDEAL bitisten baslar, tespit aninden degil.
            self._donusum_baslat(bitis)

    def _sonucu_yaz(self) -> None:
        s = self.adc_sonuc
        if self.cpu.m[ADMUX] & 0x20:            # ADLAR: sola hizali
            s <<= 6
        self.cpu.m[ADCL] = s & 0xFF
        self.cpu.m[ADCH] = (s >> 8) & 0xFF

    def _adcl_oku(self) -> int:
        self.adc_kilit = True                   # ADCH okunana dek guncelleme yok
        return self.cpu.m[ADCL]

    def _adch_oku(self) -> int:
        v = self.cpu.m[ADCH]
        if self.adc_kilit:
            self.adc_kilit = False
            self._sonucu_yaz()
        return v

    # ------------------------------------------------------------- USART
    def _ubrr_yaz(self, v: int) -> None:
        ubrr = self.cpu.m[UBRR0L] | (self.cpu.m[UBRR0H] << 8)
        catal = 8 if (self.cpu.m[UCSR0A] & 0x02) else 16      # U2X0
        self.bit_cevrim = catal * (ubrr + 1)

    def _ucsr0a_oku(self) -> int:
        v = self.cpu.m[UCSR0A] & 0x03           # U2X0, MPCM0 korunur
        if self.rx_dolu:
            v |= 0x80                           # RXC0
        if not self.udr_dolu:
            v |= 0x20                           # UDRE0
        if self.cpu.cevrim >= self.kaydirma_bitis and not self.udr_dolu:
            v |= 0x40                           # TXC0
        return v

    def _ucsr0a_yaz(self, v: int) -> None:
        self.cpu.m[UCSR0A] = v & 0x03
        self._ubrr_yaz(0)                       # U2X0 degismis olabilir

    def _udr0_yaz(self, v: int) -> None:
        if not (self.cpu.m[UCSR0B] & 0x08):     # TXEN0 kapali
            return
        if self.cpu.cevrim >= self.kaydirma_bitis:
            self.kaydirma_bitis = self.cpu.cevrim + 10 * self.bit_cevrim
        else:
            self.udr_dolu = True
            self.udr_bekleyen = v
        self.tx.append(v)                       # gonderilen bayti kaydet

    def _udr0_oku(self) -> int:
        self.rx_dolu = False
        return self.rx_bayt

    def _usart_isle(self) -> None:
        if self.udr_dolu and self.cpu.cevrim >= self.kaydirma_bitis:
            self.udr_dolu = False
            self.kaydirma_bitis = self.cpu.cevrim + 10 * self.bit_cevrim
        if (not self.rx_dolu and self.rx_kuyruk
                and self.cpu.cevrim >= self.rx_hazir_cevrim
                and (self.cpu.m[UCSR0B] & 0x10)):           # RXEN0
            self.rx_bayt = self.rx_kuyruk.pop(0)
            self.rx_dolu = True
            self.rx_hazir_cevrim = self.cpu.cevrim + 10 * self.bit_cevrim

    def seri_gonder(self, veri) -> None:
        """Bilgisayardan karta bayt gonder (RX)."""
        if isinstance(veri, str):
            veri = veri.encode("ascii")
        self.rx_kuyruk.extend(veri)

    # ------------------------------------------------------------ EEPROM
    def _eecr_yaz(self, v: int) -> None:
        adres = (self.cpu.m[EEARL] | (self.cpu.m[EEARH] << 8)) & 0x3FF
        if v & 0x01:                            # EERE: oku
            self.cpu.m[EEDR] = self.eeprom[adres]
            self.cpu.m[EECR] &= ~0x01 & 0xFF
        elif (v & 0x02) and (v & 0x04):         # EEMPE + EEPE: yaz
            self.eeprom[adres] = self.cpu.m[EEDR]
            self.cpu.m[EECR] &= ~0x06 & 0xFF    # yazma bitti

    # ------------------------------------------------------------- kesme
    def _kesmeleri_gozet(self) -> None:
        if not self.cpu.I or self.cpu.kesme_bekleyen is not None:
            return
        m = self.cpu.m
        if (m[TIMSK0] & 0x01) and (m[TIFR0] & 0x01):
            m[TIFR0] &= ~0x01 & 0xFF
            self.cpu.kesme_ver(V_TIMER0_OVF)
            return
        if (m[UCSR0B] & 0x80) and self.rx_dolu:            # RXCIE0
            self.cpu.kesme_ver(V_USART_RX)
            return
        if (m[UCSR0B] & 0x20) and not self.udr_dolu:       # UDRIE0
            self.cpu.kesme_ver(V_USART_UDRE)
            return
        if (m[ADCSRA] & 0x08) and (m[ADCSRA] & 0x10):      # ADIE + ADIF
            m[ADCSRA] &= ~0x10 & 0xFF
            self.cpu.kesme_ver(V_ADC)

    # ------------------------------------------------------------ surucu
    def adim(self) -> int:
        n = self.cpu.adim()
        self._timer0_isle()
        self._adc_isle()
        self._usart_isle()
        self._kesmeleri_gozet()
        return n

    def cevrim_kadar_kos(self, cevrim: int) -> None:
        hedef = self.cpu.cevrim + cevrim
        adim = self.adim
        cpu = self.cpu
        while cpu.cevrim < hedef:
            adim()

    def saniye_kadar_kos(self, saniye: float) -> None:
        self.cevrim_kadar_kos(int(saniye * F_CPU))

    def satirlar(self) -> list[str]:
        return self.tx.decode("ascii", "replace").splitlines()
