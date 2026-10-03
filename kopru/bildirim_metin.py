# -*- coding: utf-8 -*-
"""4E — PC bildirimlerinin TR/EN metinleri (TEK yer; yalniz stdlib).

Anahtar aileleri `ortak/src/sozluk.js` ile AYNI adlandirma ve AYNI metin:
    sebep.<kod>  pil.durum.<kod>  oturum.tur.<kod>   (+ <aile>.bilinmeyen: {kod})
Bu ailelerin metinleri sozluk.js'tekiyle birebir ayni olmali — `uretim/test_bildirim.py` (4E)
sozluk.js'i okuyup karsilastirir; panel bir metni degistirirse burasi kirmiziya doner.
Bildirime ozgu metinler `bld.<ad>` ailesinde (panelde yok; PC Windows bildirimi icin).

    metin("bld.kopuk", "en", oturum=7)   -> "No news from the board — ..."
    kod_metni("sebep.", 5, "tr")        -> "kart yeniden başladı"

Kartin olay adlari (`kod/olcum-karti-a3/bildirim.h` `bld__olay_ac(... "<ad>")`) -> OLAY_ANAHTAR;
test her olay adinin burada TR VE EN metni oldugunu firmware basligindan olcer.

Hicbir zaman ATMAZ: bilinmeyen anahtar -> anahtarin kendisi; {ad} yer tutucusu verilmezse kalir.
"""
from __future__ import annotations

DILLER = ("tr", "en")


def _s(tr: str, en: str) -> dict:
    return {"tr": tr, "en": en}


METIN: dict[str, dict] = {
    # ── sozluk.js ile ORTAK (birebir ayni metin; test karsilastirir)
    "sebep.1": _s("kullanıcı durdurdu", "stopped by user"),
    "sebep.2": _s("bellek doldu", "storage full"),
    "sebep.3": _s("hata", "error"),
    "sebep.4": _s("pil testi bitti", "battery test finished"),
    "sebep.5": _s("kart yeniden başladı", "board restarted"),
    "sebep.6": _s("başka oturum başladı", "another session started"),
    "sebep.7": _s("planlı süre doldu", "scheduled duration elapsed"),
    "sebep.bilinmeyen": _s("bilinmeyen sebep ({kod})", "unknown reason ({kod})"),
    "oturum.tur.1": _s("Ölçüm kaydı", "Measurement recording"),
    "oturum.tur.2": _s("Pil testi", "Battery test"),
    "oturum.tur.3": _s("Osiloskop günlüğü", "Oscilloscope log"),
    "oturum.tur.bilinmeyen": _s("Bilinmeyen oturum türü ({kod})", "Unknown session type ({kod})"),
    "pil.durum.0": _s("beklemede", "idle"),
    "pil.durum.1": _s("çalışıyor", "running"),
    "pil.durum.2": _s("bitti (kesme gerilimine ulaşıldı)", "finished (cut-off voltage reached)"),
    "pil.durum.3": _s("kullanıcı durdurdu", "stopped by user"),
    "pil.durum.4": _s("hata", "error"),
    "pil.durum.bilinmeyen": _s("bilinmeyen durum ({kod})", "unknown state ({kod})"),

    # ── bildirime ozgu (bld.*)
    "bld.baslik": _s("Ölçüm kartı", "Measurement board"),
    "bld.kopuk": _s("Karttan haber yok — kayıt sürüyordu (oturum {oturum})",
                    "No news from the board — a recording was running (session {oturum})"),
    "bld.kopuk_yerel": _s("Karttan haber yok — kayıt sürüyordu (oturum {oturum}); yerel bağlantı da koptu",
                          "No news from the board — a recording was running (session {oturum}); "
                          "the local link is down too"),
    "bld.ev_interneti": _s("Ev interneti koptu — kart çalışıyor, kayıt sürüyor (oturum {oturum})",
                           "Home internet is down — the board is working, recording continues "
                           "(session {oturum})"),
    "bld.geri_kayit": _s("Kart yeniden bağlandı — kayıt sürüyor (oturum {oturum})",
                         "The board is back — recording continues (session {oturum})"),
    "bld.geri": _s("Kart yeniden bağlandı — kayıt sürmüyor",
                   "The board is back — no recording is running"),
    "bld.kayit_bitti": _s("Kayıt bitti — {sebep} (oturum {oturum}, {nokta} nokta)",
                          "Recording finished — {sebep} (session {oturum}, {nokta} points)"),
    "bld.kayit_bitti_yerel": _s("Kayıt bitti (oturum {oturum})", "Recording finished (session {oturum})"),
    "bld.dolu": _s("Bellek doldu, kayıt durdu", "Storage full, recording stopped"),
    "bld.dolu_oturum": _s("Bellek doldu, kayıt durdu (oturum {oturum})",
                          "Storage full, recording stopped (session {oturum})"),
    "bld.pil_bitti": _s("Pil testi bitti — {durum}: {mah} mAh, {wh} Wh, süre {sure}",
                        "Battery test finished — {durum}: {mah} mAh, {wh} Wh, duration {sure}"),
    "bld.esik": _s("Eşitlenmemiş veri %{deger} (eşik %{esik}) — kayıtları eşitleyin",
                   "Unsynced data {deger}% (threshold {esik}%) — sync the recordings"),
    "bld.basladi_devam": _s("Kart yeniden başladı — kayıt kesildi ve sürüyor (oturum {oturum})",
                            "The board restarted — the recording was interrupted and continues "
                            "(session {oturum})"),
    "bld.kesildi": _s("Kart yeniden başladı — {tur} kesildi (oturum {oturum}){saat}",
                      "The board restarted — {tur} was interrupted (session {oturum}){saat}"),
    "bld.kesildi_saat": _s(", son haber {saat}", ", last heard {saat}"),
    "bld.deneme": _s("Deneme bildirimi — bildirim yolu çalışıyor",
                     "Test notification — the notification path works"),
    "bld.kacirilan": _s("{adet} olay kaçırıldı (bu PC bağlı değilken) — ayrıntılar kayıtlar eşitlenince "
                        "arşivde",
                        "{adet} events were missed (while this PC was not connected) — details are in the "
                        "archive once recordings sync"),
}

# Kartin olay adi -> bildirim metni anahtari (test: bildirim.h'deki HER olay adi burada)
OLAY_ANAHTAR = {
    "basladi": "bld.basladi_devam",
    "kayit_bitti": "bld.kayit_bitti",
    "pil_bitti": "bld.pil_bitti",
    "dolu": "bld.dolu",
    "esik": "bld.esik",
    "deneme": "bld.deneme",
}


def metin(anahtar: str, dil: str = "tr", **degisken) -> str:
    d = dil if dil in DILLER else "tr"
    girdi = METIN.get(anahtar)
    if girdi is None:
        return anahtar
    s = girdi.get(d) or girdi.get("tr" if d == "en" else "en") or anahtar
    for ad, deger in degisken.items():
        s = s.replace("{" + ad + "}", str(deger))
    return s


def kod_metni(onek: str, kod, dil: str = "tr") -> str:
    """sozluk.js ceviriKod karsiligi: onek+kod varsa o, yoksa onek+'bilinmeyen' ({kod} ile)."""
    a = f"{onek}{kod}"
    if a in METIN:
        return metin(a, dil)
    return metin(f"{onek}bilinmeyen", dil, kod=kod)
