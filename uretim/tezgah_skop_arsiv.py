# -*- coding: utf-8 -*-
"""B35 — SKOP ARSIVI GERCEK KARTTA (tezgah kosucusu).

    python tezgah_skop_arsiv.py            # portu otomatik bul
    python tezgah_skop_arsiv.py --port COM6

🔴 NEDEN AYRI BIR KOSUCU: `test_kopru.py` yukari-akis olarak `KayitKart`
   kullaniyor — yani kartin `t` yanitini BEN yaziyorum. O test protokolu
   ve kopruyu siniyor, KARTI sinamiyor. Bu projede "yesil test bir sey
   kanitlamaz" kurali tam olarak bunun icin var: B22'de arayuz zincir
   15/15 yesilken tarayicida HIC acilmiyordu.

   Burada gercek kart, gercek seri port, gercek ASCII dokum var. Sinanan
   sey: kopru kipinde yakalama CALISIYOR mu, ve yakalama ARSIVE dusuyor
   mu — ikisi de B35 oncesi YOKTU.

⚠ Kart COM6'da ve kopru cipi CH343. Kartin iki Type-C soketi var; COM
  yazan dogru olan. Yerel USB soketi de port acar (VID_303A) ama
  firmware `Serial`i UART0'da tuttugu icin SESSIZ kalir.
"""
from __future__ import annotations

import struct
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

BURASI = Path(__file__).parent
KOK = BURASI.parent
sys.path.insert(0, str(KOK / "kopru"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import kart_baglanti                                       # noqa: E402
import kopru as kopru_mod                                  # noqa: E402
import gecici                                              # noqa: E402

gecti = kaldi = 0


def ok(ad: str, kosul: bool, ek: str = "") -> None:
    global gecti, kaldi
    if kosul:
        gecti += 1
        print(f"[OK] {ad}" + (f"  {ek}" if ek else ""))
    else:
        kaldi += 1
        print(f"[!!] {ad}" + (f"  {ek}" if ek else ""))


def istek(url, zaman_asimi=30):
    try:
        with urllib.request.urlopen(url, timeout=zaman_asimi) as y:
            return y.status, y.read(), dict(y.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def main() -> int:
    arg = sys.argv[1:]
    port = arg[arg.index("--port") + 1] if "--port" in arg else None

    print("=" * 78)
    print("  B35  SKOP ARSIVI — GERCEK KARTTA")
    print("=" * 78)

    kart = kart_baglanti.SeriKart(port)
    try:
        kart.ac()
    except RuntimeError as e:
        print(f"Karta baglanilamadi: {e}")
        print("Portlar:", ", ".join(kart_baglanti.portlari_listele()) or "(yok)")
        return 1
    print(f"     kart: {kart.ad}")

    gec = gecici.dizin("skop_arsiv_")
    k = kopru_mod.Kopru(kart, gec / "arsiv")
    kopru_mod.Isleyici.kopru = k
    threading.Thread(target=k.dongu, daemon=True).start()

    sunucu = kopru_mod.Sunucu(("127.0.0.1", 0), kopru_mod.Isleyici)
    taban = f"http://127.0.0.1:{sunucu.server_address[1]}"
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    print(f"     gecici kopru: {taban}\n")

    # Kart konussun; `D` satirlari akmaya baslasin.
    t0 = time.monotonic()
    while k.satir_adedi == 0 and time.monotonic() - t0 < 8:
        time.sleep(0.1)
    ok("Kart konusuyor (yukari-akis satir tasiyor)", k.satir_adedi > 0,
       f"{k.satir_adedi} satir")
    if not k.satir_adedi:
        print("\n  Kart sessiz — YANLIS SOKETE takili olabilir (VID_303A yerel USB).")
        sunucu.shutdown(); k.durdur(); kart.kapat()
        return 1

    # ── 1. CANLI YAKALAMA ────────────────────────────────────────────
    print("--- 1. Canli yakalama (/skop.bin) ---")
    t0 = time.monotonic()
    kod, govde, bas = istek(taban + "/skop.bin")
    sure = time.monotonic() - t0
    ok("[!] /skop.bin GERCEK kartta 200 donduruyor", kod == 200,
       f"HTTP {kod} · {sure:.2f} s" +
       ("" if kod == 200 else " · " + govde[:70].decode("utf-8", "replace")))
    if kod != 200:
        sunucu.shutdown(); k.durdur(); kart.kapat()
        print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
        return 1

    ok("Imza kartin biciminde (S3B)", govde[:3] == b"S3B", repr(govde[:4]))
    adet = struct.unpack_from("<H", govde, 4)[0]
    hz = struct.unpack_from("<I", govde, 8)[0]
    adim = struct.unpack_from("<f", govde, 12)[0]
    tdiv = struct.unpack_from("<I", govde, 20)[0]
    ornek = list(struct.unpack_from(f"<{adet}H", govde, 32))
    ok("Govde uzunlugu 32 + 2*adet", len(govde) == 32 + 2 * adet,
       f"{len(govde)} B · {adet} ornek")
    ok("Ornekleme hizi ve zaman tabani makul",
       0 < hz <= 100000 and tdiv > 0, f"hz={hz} tdiv={tdiv} us/bolme")
    ok("Volt/adim pozitif", adim > 0, f"{adim:.6f} V/adim")
    # 🔴 GERCEK ADC verisi 12 bit: 0..4095. Hepsi ayni degerse ya giris
    #    olu ya da cozucu sabit okuyor — ikisi de sessiz kalmamali.
    ok("[!] Ornekler 12 bit menzilinde (0..4095)",
       all(0 <= x <= 4095 for x in ornek),
       f"en kucuk {min(ornek)} · en buyuk {max(ornek)}")
    farkli = len(set(ornek))
    ok("Ornekler SABIT DEGIL (gercek olcum, dolgu degil)", farkli > 1,
       f"{farkli} farkli deger · tepe-tepe {max(ornek) - min(ornek)} kod")
    ok("Yakalama zaman butcesinde (< 20 s)", sure < 20.0, f"{sure:.2f} s")

    # ── 2. ARSIVE DUSTU MU ───────────────────────────────────────────
    print("\n--- 2. Geriye donuk kayit (arsiv) ---")
    k.arsiv.flush()
    bloklar = list(k.arsiv.skop_bloklari())
    ok("[!] Yakalama ARSIVE dustu", len(bloklar) >= 1, f"{len(bloklar)} blok")
    if bloklar:
        b = bloklar[-1]
        ok("Arsivdeki ornekler canli govdeyle BIREBIR", b["ornek"] == ornek,
           f"{len(b['ornek'])} ornek · tam={b['tam']}")
        ok("Canli yanitin kimligi arsivdekiyle AYNI",
           bas.get("X-Skop-Ms") == str(b["ms"]),
           f"baslik={bas.get('X-Skop-Gun')}/{bas.get('X-Skop-Ms')} · "
           f"arsiv={b['gun']}/{b['ms']}")
        ok("Blok icinde `D` satiri varsa SAYILDI (sessiz yutulmadi)",
           isinstance(b["atlanan"], int),
           f"atlanan={b['atlanan']} satir (olcum dongusu Serial'i paylasiyor)")

    kod, govde2, _ = istek(taban + "/skop/liste")
    import json
    liste = json.loads(govde2) if kod == 200 else {}
    ok("/skop/liste kaydi goruyor",
       kod == 200 and len(liste.get("kayitlar", [])) >= 1,
       f"HTTP {kod} · {len(liste.get('kayitlar', []))} kayit")

    if liste.get("kayitlar"):
        kyt = liste["kayitlar"][0]
        kod, govde3, _ = istek(
            taban + f"/skop/al?gun={kyt['gun']}&ms={kyt['ms']}")
        ok("[!] Arsivden geri okunan kayit CANLI govdeyle BAYT-BAYT ayni",
           kod == 200 and govde3 == govde,
           f"HTTP {kod} · {len(govde3)} B / {len(govde)} B")

    # ── 3. ARAYUZUN GERCEK AKISI ─────────────────────────────────────
    # Arayuz koprude duz `t` yolluyor ve dokumu SSE'den aliyor. Burada
    # onemli olan: kart IKI KEZ yakalamiyor ve blok yine arsive dusuyor.
    print("\n--- 3. Arayuzun akisi: `t` -> SSE + arsiv ---")
    onceki = len(list(k.arsiv.skop_bloklari()))
    k.skop_hazirla()
    kart.yaz("t")
    t0 = time.monotonic()
    while not k.skop_olay.wait(0.2) and time.monotonic() - t0 < 20:
        pass
    time.sleep(0.5)
    k.arsiv.flush()
    simdi = len(list(k.arsiv.skop_bloklari()))
    ok("[!] Duz `t` yakalamasi da arsive dusuyor", simdi == onceki + 1,
       f"{onceki} -> {simdi} blok")

    sunucu.shutdown()
    k.durdur()
    kart.kapat()
    print(f"\n{gecti}/{gecti + kaldi} dogrulama gecti")
    print(f"     arsiv: {k.arsiv.dizin}")
    return 1 if kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main())
