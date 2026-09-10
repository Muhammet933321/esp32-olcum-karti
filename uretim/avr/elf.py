# -*- coding: utf-8 -*-
"""Kucuk ELF32 okuyucu — avr-g++ ciktisindaki program baytlarini cikarir.

Sadece ihtiyac duyulan kadari: 32 bit, little-endian ELF'in PROGRAM
BASLIKLARI (program headers) okunur. Bolum (section) tablosu degil program
tablosu kullaniliyor cunku yukleyicinin gordugu sey odur: .text ve .data
zaten ayni LOAD parcasinda pes pese durur ve avr-libc'nin baslangic kodu
.data'yi flash'in sonundan RAM'e kendisi kopyalar.

Donen `bellek` bytearray'i flash goruntusudur — simulator bunu dogrudan
program bellegine koyar.
"""
from __future__ import annotations

import struct
from pathlib import Path


class ElfHata(Exception):
    pass


def flash_goruntusu(yol: Path, boyut: int = 32768) -> tuple[bytearray, int]:
    """ELF dosyasindan flash goruntusunu ve baslangic adresini dondurur."""
    ham = Path(yol).read_bytes()
    if ham[:4] != b"\x7fELF":
        raise ElfHata("ELF sihirli sayisi yok")
    if ham[4] != 1 or ham[5] != 1:
        raise ElfHata("32 bit little-endian ELF bekleniyordu")

    # e_machine 83 = EM_AVR
    (e_machine,) = struct.unpack_from("<H", ham, 18)
    if e_machine != 83:
        raise ElfHata(f"AVR degil (e_machine={e_machine})")

    e_entry, e_phoff = struct.unpack_from("<II", ham, 24)
    e_phentsize, e_phnum = struct.unpack_from("<HH", ham, 42)

    goruntu = bytearray(boyut)
    yuklenen = 0
    for i in range(e_phnum):
        o = e_phoff + i * e_phentsize
        p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, _, _ = \
            struct.unpack_from("<IIIIIIII", ham, o)
        if p_type != 1 or p_filesz == 0:     # PT_LOAD degilse atla
            continue
        # p_paddr fiziksel (flash) adres; .data icin bu flash'taki kopyadir.
        # AVR ELF'inde RAM adresleri 0x800000 ile isaretlenir, maskele.
        adres = p_paddr & 0x7FFFFF
        if adres + p_filesz > boyut:
            raise ElfHata(f"parca flash disina tasti: {adres:#x}+{p_filesz}")
        goruntu[adres:adres + p_filesz] = ham[p_offset:p_offset + p_filesz]
        yuklenen += p_filesz

    if yuklenen == 0:
        raise ElfHata("yuklenebilir parca bulunamadi")
    return goruntu, e_entry & 0x7FFFFF


def semboller(yol: Path) -> dict[str, int]:
    """.symtab'dan {isim: adres} — hata ayiklama ve dogrulama icin."""
    ham = Path(yol).read_bytes()
    e_shoff, = struct.unpack_from("<I", ham, 32)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", ham, 46)

    def bolum(i):
        o = e_shoff + i * e_shentsize
        return struct.unpack_from("<IIIIIIIIII", ham, o)

    cikti = {}
    for i in range(e_shnum):
        b = bolum(i)
        if b[1] != 2:                       # SHT_SYMTAB
            continue
        strtab = bolum(b[6])                # sh_link -> .strtab
        str_off = strtab[4]
        off, boy, giris = b[4], b[5], b[9]
        for j in range(boy // giris):
            o = off + j * giris
            st_name, st_value, _, st_info, _, _ = struct.unpack_from("<IIIBBH", ham, o)
            son = ham.index(b"\0", str_off + st_name)
            ad = ham[str_off + st_name:son].decode("ascii", "replace")
            if ad:
                cikti[ad] = st_value & 0x7FFFFF
    return cikti
