# -*- coding: utf-8 -*-
"""AVR5 (ATmega328P) komut kumesi yorumlayicisi.

NEDEN: Firmware'in aritmetigini Python'da YENIDEN YAZMAK tasarim niyetini
dogrular ama GERCEK KODU dogrulamaz — iki uygulama sessizce ayrisabilir.
Burada gercek avr-g++ ciktisi, gercek komutlarla, gercek avr-libc yazilim
float kutuphanesi uzerinden calistiriliyor. Cikan bayt dizisi kartin seri
portundan cikacak olanin ta kendisidir.

Bellek modeli AVR'nin kendi modeli: kaydediciler veri uzayinin 0x00-0x1F
araligina gomulu, 0x20-0xFF G/C kaydedicileri, 0x100+ SRAM.

Bayraklar ayri alanlarda tutulur (SREG okununca birlestirilir) — her komutta
bit maskesi acip kapamaktan belirgin olcude hizli.
"""
from __future__ import annotations

# SREG bit sirasi: I T H S V N Z C  (7..0)
SREG = 0x5F
SPL, SPH = 0x5D, 0x5E

BAYRAK = ("C", "Z", "N", "V", "S", "H", "T", "I")


class Durdu(Exception):
    """Simulator durdurma istegi (kirilma noktasi, bilinmeyen komut, ...)."""


class Cekirdek:
    def __init__(self, flash: bytearray, ram_boyut: int = 0x900):
        self.flash = flash
        # komut getirme icin 16 bit sozcuk gorunumu
        self.soz = memoryview(flash).cast("H")
        self.m = bytearray(ram_boyut)   # 0x00-0x1F kaydedici, 0x20+ G/C, 0x100+ SRAM
        self.ram_boyut = ram_boyut
        self.pc = 0                     # SOZCUK adresi
        self.sp = ram_boyut - 1
        self.C = self.Z = self.N = self.V = self.S = self.H = self.T = self.I = 0
        self.cevrim = 0
        self.uyuyor = False
        self.onbellek: list = [None] * (len(flash) // 2)
        # G/C kancalari — cevre birimleri doldurur
        self.gc_oku = {}                # {adres: fn() -> int}
        self.gc_yaz = {}                # {adres: fn(deger)}
        self.kesme_bekleyen = None      # cevre birimlerin koydugu vektor (bayt adresi)

    # ------------------------------------------------------------ bellek
    def veri_oku(self, a: int) -> int:
        if a < 0x20:
            return self.m[a]
        if a < 0x100:
            f = self.gc_oku.get(a)
            if f is not None:
                return f() & 0xFF
            if a == SREG:
                return (self.I << 7 | self.T << 6 | self.H << 5 | self.S << 4
                        | self.V << 3 | self.N << 2 | self.Z << 1 | self.C)
            if a == SPL:
                return self.sp & 0xFF
            if a == SPH:
                return (self.sp >> 8) & 0xFF
            return self.m[a]
        return self.m[a] if a < self.ram_boyut else 0

    def veri_yaz(self, a: int, v: int) -> None:
        v &= 0xFF
        if a < 0x20:
            self.m[a] = v
            return
        if a < 0x100:
            if a == SREG:
                self.I = (v >> 7) & 1
                self.T = (v >> 6) & 1
                self.H = (v >> 5) & 1
                self.S = (v >> 4) & 1
                self.V = (v >> 3) & 1
                self.N = (v >> 2) & 1
                self.Z = (v >> 1) & 1
                self.C = v & 1
                return
            if a == SPL:
                self.sp = (self.sp & 0xFF00) | v
                return
            if a == SPH:
                self.sp = (self.sp & 0x00FF) | (v << 8)
                return
            self.m[a] = v
            f = self.gc_yaz.get(a)
            if f is not None:
                f(v)
            return
        if a < self.ram_boyut:
            self.m[a] = v

    def it(self, v: int) -> None:
        self.m[self.sp] = v & 0xFF
        self.sp -= 1

    def cek(self) -> int:
        self.sp += 1
        return self.m[self.sp]

    # ------------------------------------------------------------ bayrak
    def _nz(self, r: int) -> None:
        self.N = r >> 7
        self.Z = 1 if r == 0 else 0
        self.S = self.N ^ self.V

    # ------------------------------------------------------------ kesme
    def kesme_ver(self, vektor_bayt: int) -> None:
        """Cevre birimi kesme istedi (bayt adresi)."""
        self.kesme_bekleyen = vektor_bayt

    def _kesmeyi_isle(self) -> int:
        v = self.kesme_bekleyen
        self.kesme_bekleyen = None
        self.I = 0
        self.it(self.pc & 0xFF)
        self.it((self.pc >> 8) & 0xFF)
        self.pc = v >> 1
        self.uyuyor = False
        return 5

    # ------------------------------------------------------------ calisma
    def adim(self) -> int:
        if self.kesme_bekleyen is not None and self.I:
            n = self._kesmeyi_isle()
            self.cevrim += n
            return n
        if self.uyuyor:
            self.cevrim += 1
            return 1
        f = self.onbellek[self.pc]
        if f is None:
            f = self.onbellek[self.pc] = self.derle(self.pc)
        n = f()
        self.cevrim += n
        return n

    def _iki_sozcuk(self, pc: int) -> bool:
        """Atlanacak komut iki sozcuk mu (LDS/STS/JMP/CALL)?"""
        o = self.soz[pc]
        return ((o & 0xFE0F) in (0x9000, 0x9200)) or ((o & 0xFE0E) in (0x940C, 0x940E))

    # --------------------------------------------------------- kod cozme
    def derle(self, pc: int):
        op = self.soz[pc]
        ileri = pc + 1
        m = self.m

        if op == 0x0000:                                   # NOP
            def f():
                self.pc = ileri
                return 1
            return f

        ust = op & 0xFC00

        if (op & 0xFF00) == 0x0100:                        # MOVW
            d = ((op >> 4) & 0x0F) * 2
            r = (op & 0x0F) * 2

            def f():
                m[d] = m[r]
                m[d + 1] = m[r + 1]
                self.pc = ileri
                return 1
            return f

        if (op & 0xFF00) == 0x0200:                        # MULS
            d = 16 + ((op >> 4) & 0x0F)
            r = 16 + (op & 0x0F)

            def f():
                a = m[d] - 256 if m[d] > 127 else m[d]
                b = m[r] - 256 if m[r] > 127 else m[r]
                p = (a * b) & 0xFFFF
                m[0] = p & 0xFF
                m[1] = p >> 8
                self.C = p >> 15
                self.Z = 1 if p == 0 else 0
                self.pc = ileri
                return 2
            return f

        if (op & 0xFF00) == 0x0300:                        # MULSU/FMUL/FMULS/FMULSU
            d = 16 + ((op >> 4) & 0x07)
            r = 16 + (op & 0x07)
            ust_d = (op >> 7) & 1
            ust_r = (op >> 3) & 1

            def f():
                a = m[d]
                b = m[r]
                if ust_d == 0 and ust_r == 0:              # MULSU: d isaretli
                    a = a - 256 if a > 127 else a
                    p = a * b
                elif ust_d == 0 and ust_r == 1:            # FMUL
                    p = (a * b) << 1
                elif ust_d == 1 and ust_r == 0:            # FMULS
                    a = a - 256 if a > 127 else a
                    b = b - 256 if b > 127 else b
                    p = (a * b) << 1
                else:                                      # FMULSU
                    a = a - 256 if a > 127 else a
                    p = (a * b) << 1
                self.C = (p >> 16) & 1
                p &= 0xFFFF
                m[0] = p & 0xFF
                m[1] = p >> 8
                self.Z = 1 if p == 0 else 0
                self.pc = ileri
                return 2
            return f

        # ---------- iki kaydedicili aile ----------
        if ust in (0x0400, 0x0800, 0x0C00, 0x1000, 0x1400, 0x1800, 0x1C00,
                   0x2000, 0x2400, 0x2800, 0x2C00, 0x9C00):
            d = (op >> 4) & 0x1F
            r = ((op >> 5) & 0x10) | (op & 0x0F)

            if ust in (0x0C00, 0x1C00):                    # ADD / ADC
                adc = ust == 0x1C00

                def f():
                    a = m[d]
                    b = m[r]
                    c = self.C if adc else 0
                    t = a + b + c
                    rr = t & 0xFF
                    self.H = 1 if ((a & 0xF) + (b & 0xF) + c) > 0xF else 0
                    self.C = 1 if t > 0xFF else 0
                    self.V = 1 if ((a ^ rr) & (b ^ rr) & 0x80) else 0
                    m[d] = rr
                    self._nz(rr)
                    self.pc = ileri
                    return 1
                return f

            if ust in (0x1800, 0x0800, 0x1400, 0x0400):    # SUB / SBC / CP / CPC
                borc = ust in (0x0800, 0x0400)             # SBC, CPC
                sakla = ust in (0x1800, 0x0800)            # SUB, SBC

                def f():
                    a = m[d]
                    b = m[r]
                    c = self.C if borc else 0
                    t = a - b - c
                    rr = t & 0xFF
                    self.H = 1 if (a & 0xF) < ((b & 0xF) + c) else 0
                    self.C = 1 if t < 0 else 0
                    self.V = 1 if ((a ^ b) & (a ^ rr) & 0x80) else 0
                    self.N = rr >> 7
                    if borc:
                        self.Z = 1 if (rr == 0 and self.Z) else 0
                    else:
                        self.Z = 1 if rr == 0 else 0
                    self.S = self.N ^ self.V
                    if sakla:
                        m[d] = rr
                    self.pc = ileri
                    return 1
                return f

            if ust == 0x1000:                              # CPSE
                def f():
                    if m[d] == m[r]:
                        n = 2 if self._iki_sozcuk(ileri) else 1
                        self.pc = ileri + n
                        return 1 + n
                    self.pc = ileri
                    return 1
                return f

            if ust == 0x2000:                              # AND
                def f():
                    rr = m[d] & m[r]
                    m[d] = rr
                    self.V = 0
                    self._nz(rr)
                    self.pc = ileri
                    return 1
                return f

            if ust == 0x2400:                              # EOR
                def f():
                    rr = m[d] ^ m[r]
                    m[d] = rr
                    self.V = 0
                    self._nz(rr)
                    self.pc = ileri
                    return 1
                return f

            if ust == 0x2800:                              # OR
                def f():
                    rr = m[d] | m[r]
                    m[d] = rr
                    self.V = 0
                    self._nz(rr)
                    self.pc = ileri
                    return 1
                return f

            if ust == 0x2C00:                              # MOV
                def f():
                    m[d] = m[r]
                    self.pc = ileri
                    return 1
                return f

            if ust == 0x9C00:                              # MUL
                def f():
                    p = (m[d] * m[r]) & 0xFFFF
                    m[0] = p & 0xFF
                    m[1] = p >> 8
                    self.C = p >> 15
                    self.Z = 1 if p == 0 else 0
                    self.pc = ileri
                    return 2
                return f

        # ---------- anlik (immediate) aile ----------
        tur = op & 0xF000
        if tur in (0x3000, 0x4000, 0x5000, 0x6000, 0x7000):
            d = 16 + ((op >> 4) & 0x0F)
            k = ((op >> 4) & 0xF0) | (op & 0x0F)

            if tur in (0x3000, 0x4000, 0x5000):            # CPI / SBCI / SUBI
                borc = tur == 0x4000
                sakla = tur != 0x3000

                def f():
                    a = m[d]
                    c = self.C if borc else 0
                    t = a - k - c
                    rr = t & 0xFF
                    self.H = 1 if (a & 0xF) < ((k & 0xF) + c) else 0
                    self.C = 1 if t < 0 else 0
                    self.V = 1 if ((a ^ k) & (a ^ rr) & 0x80) else 0
                    self.N = rr >> 7
                    if borc:
                        self.Z = 1 if (rr == 0 and self.Z) else 0
                    else:
                        self.Z = 1 if rr == 0 else 0
                    self.S = self.N ^ self.V
                    if sakla:
                        m[d] = rr
                    self.pc = ileri
                    return 1
                return f

            if tur == 0x6000:                              # ORI
                def f():
                    rr = m[d] | k
                    m[d] = rr
                    self.V = 0
                    self._nz(rr)
                    self.pc = ileri
                    return 1
                return f

            def f():                                       # ANDI
                rr = m[d] & k
                m[d] = rr
                self.V = 0
                self._nz(rr)
                self.pc = ileri
                return 1
            return f

        # ---------- LDD / STD  (LD/ST Y,Z  q=0 dahil) ----------
        if (op & 0xD000) == 0x8000:
            d = (op >> 4) & 0x1F
            q = ((op >> 8) & 0x20) | ((op >> 7) & 0x18) | (op & 7)
            taban = 28 if (op & 8) else 30                 # Y=r28, Z=r30
            if op & 0x0200:                                # STD
                def f():
                    a = (m[taban] | (m[taban + 1] << 8)) + q
                    self.veri_yaz(a, m[d])
                    self.pc = ileri
                    return 2
                return f

            def f():                                       # LDD
                a = (m[taban] | (m[taban + 1] << 8)) + q
                m[d] = self.veri_oku(a)
                self.pc = ileri
                return 2
            return f

        # ---------- 1001 000x / 1001 001x ----------
        if (op & 0xFE00) in (0x9000, 0x9200):
            d = (op >> 4) & 0x1F
            alt = op & 0x0F
            depola = (op & 0xFE00) == 0x9200

            if alt == 0x0:                                 # LDS / STS (2 sozcuk)
                adr = self.soz[ileri]
                if depola:
                    def f():
                        self.veri_yaz(adr, m[d])
                        self.pc = ileri + 1
                        return 2
                    return f

                def f():
                    m[d] = self.veri_oku(adr)
                    self.pc = ileri + 1
                    return 2
                return f

            if alt == 0xF:                                 # PUSH / POP
                if depola:
                    def f():
                        self.it(m[d])
                        self.pc = ileri
                        return 2
                    return f

                def f():
                    m[d] = self.cek()
                    self.pc = ileri
                    return 2
                return f

            if alt in (0x4, 0x5) and not depola:           # LPM Rd,Z / Z+
                artir = alt == 0x5

                def f():
                    z = m[30] | (m[31] << 8)
                    m[d] = self.flash[z]
                    if artir:
                        z = (z + 1) & 0xFFFF
                        m[30] = z & 0xFF
                        m[31] = z >> 8
                    self.pc = ileri
                    return 3
                return f

            tablo = {0x1: (30, +1), 0x2: (30, -1), 0x9: (28, +1), 0xA: (28, -1),
                     0xC: (26, 0), 0xD: (26, +1), 0xE: (26, -1)}
            if alt in tablo:
                taban, yon = tablo[alt]

                def f():
                    a = m[taban] | (m[taban + 1] << 8)
                    if yon < 0:
                        a = (a - 1) & 0xFFFF
                        m[taban] = a & 0xFF
                        m[taban + 1] = a >> 8
                    if depola:
                        self.veri_yaz(a, m[d])
                    else:
                        m[d] = self.veri_oku(a)
                    if yon > 0:
                        b = (a + 1) & 0xFFFF
                        m[taban] = b & 0xFF
                        m[taban + 1] = b >> 8
                    self.pc = ileri
                    return 2
                return f

        # ---------- 1001 0100/0101 : tek islenenli + atlama/cagri ----------
        if (op & 0xFE00) == 0x9400:
            alt = op & 0x0F
            d = (op >> 4) & 0x1F

            if (op & 0xFF0F) == 0x9408:                    # BSET / BCLR
                s = (op >> 4) & 0x07
                ad = BAYRAK[s]
                deger = 0 if (op & 0x0080) else 1

                def f():
                    setattr(self, ad, deger)
                    self.pc = ileri
                    return 1
                return f

            if op == 0x9409:                               # IJMP
                def f():
                    self.pc = m[30] | (m[31] << 8)
                    return 2
                return f

            if op == 0x9509:                               # ICALL
                def f():
                    self.it(ileri & 0xFF)
                    self.it((ileri >> 8) & 0xFF)
                    self.pc = m[30] | (m[31] << 8)
                    return 3
                return f

            if op in (0x9508, 0x9518):                     # RET / RETI
                reti = op == 0x9518

                def f():
                    h = self.cek()
                    l = self.cek()
                    self.pc = (h << 8) | l
                    if reti:
                        self.I = 1
                    return 4
                return f

            if op == 0x9588:                               # SLEEP
                def f():
                    self.uyuyor = True
                    self.pc = ileri
                    return 1
                return f

            if op in (0x9598, 0x95A8):                     # BREAK / WDR
                def f():
                    self.pc = ileri
                    return 1
                return f

            if op == 0x95C8:                               # LPM R0,Z
                def f():
                    m[0] = self.flash[m[30] | (m[31] << 8)]
                    self.pc = ileri
                    return 3
                return f

            if (op & 0xFE0E) == 0x940C:                    # JMP
                hedef = (((op & 0x01F0) >> 3 | (op & 1)) << 16 | self.soz[ileri]) & 0x3FFFFF

                def f():
                    self.pc = hedef
                    return 3
                return f

            if (op & 0xFE0E) == 0x940E:                    # CALL
                hedef = (((op & 0x01F0) >> 3 | (op & 1)) << 16 | self.soz[ileri]) & 0x3FFFFF
                donus = ileri + 1

                def f():
                    self.it(donus & 0xFF)
                    self.it((donus >> 8) & 0xFF)
                    self.pc = hedef
                    return 4
                return f

            if alt == 0x0:                                 # COM
                def f():
                    rr = (~m[d]) & 0xFF
                    m[d] = rr
                    self.C = 1
                    self.V = 0
                    self._nz(rr)
                    self.pc = ileri
                    return 1
                return f

            if alt == 0x1:                                 # NEG
                def f():
                    a = m[d]
                    rr = (-a) & 0xFF
                    m[d] = rr
                    self.C = 1 if rr else 0
                    self.V = 1 if rr == 0x80 else 0
                    self.H = 1 if ((rr | a) & 0x08) else 0
                    self._nz(rr)
                    self.pc = ileri
                    return 1
                return f

            if alt == 0x2:                                 # SWAP
                def f():
                    a = m[d]
                    m[d] = ((a << 4) | (a >> 4)) & 0xFF
                    self.pc = ileri
                    return 1
                return f

            if alt == 0x3:                                 # INC
                def f():
                    rr = (m[d] + 1) & 0xFF
                    m[d] = rr
                    self.V = 1 if rr == 0x80 else 0
                    self._nz(rr)
                    self.pc = ileri
                    return 1
                return f

            if alt == 0xA:                                 # DEC
                def f():
                    rr = (m[d] - 1) & 0xFF
                    m[d] = rr
                    self.V = 1 if rr == 0x7F else 0
                    self._nz(rr)
                    self.pc = ileri
                    return 1
                return f

            if alt == 0x5:                                 # ASR
                def f():
                    a = m[d]
                    self.C = a & 1
                    rr = ((a >> 1) | (a & 0x80)) & 0xFF
                    m[d] = rr
                    self.N = rr >> 7
                    self.V = self.N ^ self.C
                    self.Z = 1 if rr == 0 else 0
                    self.S = self.N ^ self.V
                    self.pc = ileri
                    return 1
                return f

            if alt == 0x6:                                 # LSR
                def f():
                    a = m[d]
                    self.C = a & 1
                    rr = a >> 1
                    m[d] = rr
                    self.N = 0
                    self.V = self.C
                    self.Z = 1 if rr == 0 else 0
                    self.S = self.V
                    self.pc = ileri
                    return 1
                return f

            if alt == 0x7:                                 # ROR
                def f():
                    a = m[d]
                    c = self.C
                    self.C = a & 1
                    rr = (a >> 1) | (c << 7)
                    m[d] = rr
                    self.N = rr >> 7
                    self.V = self.N ^ self.C
                    self.Z = 1 if rr == 0 else 0
                    self.S = self.N ^ self.V
                    self.pc = ileri
                    return 1
                return f

        if (op & 0xFE00) == 0x9600:                        # ADIW / SBIW
            d = 24 + ((op >> 4) & 0x03) * 2
            k = ((op >> 2) & 0x30) | (op & 0x0F)
            cikar = (op & 0x0100) != 0

            def f():
                a = m[d] | (m[d + 1] << 8)
                t = a - k if cikar else a + k
                rr = t & 0xFFFF
                m[d] = rr & 0xFF
                m[d + 1] = rr >> 8
                if cikar:
                    self.C = 1 if t < 0 else 0
                    self.V = 1 if (a & ~rr & 0x8000) else 0
                else:
                    self.C = 1 if t > 0xFFFF else 0
                    self.V = 1 if (~a & rr & 0x8000) else 0
                self.N = rr >> 15
                self.Z = 1 if rr == 0 else 0
                self.S = self.N ^ self.V
                self.pc = ileri
                return 2
            return f

        if (op & 0xFC00) == 0x9800:                        # CBI/SBIC/SBI/SBIS
            a = 0x20 + ((op >> 3) & 0x1F)
            b = op & 0x07
            alt = op & 0xFF00

            if alt == 0x9800:                              # CBI
                def f():
                    self.veri_yaz(a, self.veri_oku(a) & ~(1 << b) & 0xFF)
                    self.pc = ileri
                    return 2
                return f

            if alt == 0x9A00:                              # SBI
                def f():
                    self.veri_yaz(a, self.veri_oku(a) | (1 << b))
                    self.pc = ileri
                    return 2
                return f

            beklenen = 1 if alt == 0x9B00 else 0           # SBIS : 1 ise atla

            def f():
                if ((self.veri_oku(a) >> b) & 1) == beklenen:
                    n = 2 if self._iki_sozcuk(ileri) else 1
                    self.pc = ileri + n
                    return 1 + n
                self.pc = ileri
                return 1
            return f

        if (op & 0xF800) == 0xB000:                        # IN
            d = (op >> 4) & 0x1F
            a = 0x20 + (((op >> 5) & 0x30) | (op & 0x0F))

            def f():
                m[d] = self.veri_oku(a)
                self.pc = ileri
                return 1
            return f

        if (op & 0xF800) == 0xB800:                        # OUT
            d = (op >> 4) & 0x1F
            a = 0x20 + (((op >> 5) & 0x30) | (op & 0x0F))

            def f():
                self.veri_yaz(a, m[d])
                self.pc = ileri
                return 1
            return f

        if tur == 0xC000:                                  # RJMP
            k = op & 0x0FFF
            if k > 0x7FF:
                k -= 0x1000
            hedef = (ileri + k) & 0xFFFF

            def f():
                self.pc = hedef
                return 2
            return f

        if tur == 0xD000:                                  # RCALL
            k = op & 0x0FFF
            if k > 0x7FF:
                k -= 0x1000
            hedef = (ileri + k) & 0xFFFF

            def f():
                self.it(ileri & 0xFF)
                self.it((ileri >> 8) & 0xFF)
                self.pc = hedef
                return 3
            return f

        if tur == 0xE000:                                  # LDI
            d = 16 + ((op >> 4) & 0x0F)
            k = ((op >> 4) & 0xF0) | (op & 0x0F)

            def f():
                m[d] = k
                self.pc = ileri
                return 1
            return f

        if (op & 0xF800) == 0xF000:                        # BRBS / BRBC
            ad = BAYRAK[op & 0x07]
            k = (op >> 3) & 0x7F
            if k > 0x3F:
                k -= 0x80
            hedef = (ileri + k) & 0xFFFF
            beklenen = 0 if (op & 0x0400) else 1           # BRBC : 0 ise dallan

            def f():
                if getattr(self, ad) == beklenen:
                    self.pc = hedef
                    return 2
                self.pc = ileri
                return 1
            return f

        if (op & 0xFE08) == 0xF800:                        # BLD
            d = (op >> 4) & 0x1F
            b = op & 7

            def f():
                if self.T:
                    m[d] |= (1 << b)
                else:
                    m[d] &= ~(1 << b) & 0xFF
                self.pc = ileri
                return 1
            return f

        if (op & 0xFE08) == 0xFA00:                        # BST
            d = (op >> 4) & 0x1F
            b = op & 7

            def f():
                self.T = (m[d] >> b) & 1
                self.pc = ileri
                return 1
            return f

        if (op & 0xFC08) == 0xFC00:                        # SBRC / SBRS
            d = (op >> 4) & 0x1F
            b = op & 7
            beklenen = 1 if (op & 0x0200) else 0           # SBRS : 1 ise atla

            def f():
                if ((m[d] >> b) & 1) == beklenen:
                    n = 2 if self._iki_sozcuk(ileri) else 1
                    self.pc = ileri + n
                    return 1 + n
                self.pc = ileri
                return 1
            return f

        raise Durdu(f"cozulemeyen komut {op:#06x} @ sozcuk {pc:#x}")
