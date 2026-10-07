/* ag_komut.h — COKLU AG: cekirdek 1'in (komut / loop) yazicilari. Cikisi PARAMETRE alir (`Print &o`):
   bu baslik `#define Serial CIKIS`'tan ONCE dahil ediliyor; burada Serial adiyla yazilsaydi satirlar
   GERCEK UART'a gider, aynaya / WiFi akisina HIC gitmezdi (2026-10-07 telefonda bulundu: Nl / Nt
   listeleri USB'de geliyor, WiFi'de bos kaliyordu; sim3_web 1a bunu olcuyor). Cagiran `.ino`
   (makrodan sonra) `Serial` verir = ayna. Eskiden: Serial KULLANIR —
   ag.h'den AYRI (ag.h cekirdek 0 yapistiricisi, Serial kullanmaz; AVR'de sinaniyor).
   .ino'da diger proje basliklarindan SONRA (ama Serial makrosundan ONCE) icerilir: Arduino'nun otomatik on bildirimleri ilk
   fonksiyon tanimindan once girer — fonksiyon .ino'nun basinda olsaydi kayit turleri
   (KayitKalibrasyon ...) henuz tanimsizken bildirilirdi (derleme hatasi, 2026-10-06). */
#ifndef AG_KOMUT_H
#define AG_KOMUT_H
#include "ag.h"

/* ── COKLU AG (2026-10-06): ag gorevinin (cekirdek 0) sonuclarini BURADA bas ──
   Serial aynasi her satiri /akis'e tasiyor ve yalniz cekirdek 1 yaziyor (B28) — ag
   gorevi yalniz tampon + surum yazar. Parola hicbir satirda yok (CA9). */
static uint8_t ag_mesaj_basildi = 0, ag_tarama_basildi = 0;
static void ag_sonuclari_bas(Print &o) {
  if (!ag_c) return;
  if (ag_mesaj_surum != ag_mesaj_basildi) {
    ag_mesaj_basildi = ag_mesaj_surum;
    char m[AG_MESAJ];
    __sync_synchronize();
    memcpy(m, ag_c->mesaj, sizeof(m));
    m[sizeof(m) - 1] = 0;
    o.println(m);
  }
  if (ag_tarama_surum != ag_tarama_basildi) {
    const AglGorunen *ag_tarama = ag_c->tarama;
    ag_tarama_basildi = ag_tarama_surum;
    __sync_synchronize();
    AglKayit k[AGL_AZAMI];
    ag__liste_oku(k);
    /* ayni adli erisim noktalari tek satir (en guclu) — kullanici "ag" goruyor, AP degil */
    uint8_t basilan = 0;
    for (uint8_t j = 0; j < ag_tarama_adet; j++) {
      bool once = false;
      for (uint8_t q = 0; q < j; q++) if (strcmp(ag_tarama[q].ad, ag_tarama[j].ad) == 0) once = true;
      if (once) continue;
      int8_t en = ag_tarama[j].rssi;
      (void)agl_gorunur(ag_tarama, ag_tarama_adet, ag_tarama[j].ad, &en);
      const int8_t i = agl_bul(k, ag_tarama[j].ad);
      o.print(F("NT ")); o.print(en); o.print(' ');
      if (i >= 0) o.print(i); else o.print('-');
      o.print(' '); o.println(ag_tarama[j].ad);
      basilan++;
    }
    o.print(F("NT bitti ")); o.println(basilan);
  }
}

/* Nl: kayitli aglar — NL <i> <oncelik> <bagli> <ad> (parola YOK) */
static void ag_liste_bas(Print &o) {
  AglKayit k[AGL_AZAMI];
  ag__liste_oku(k);
  const bool sta = ag_durum.kip == AG_STA;
  for (uint8_t i = 0; i < AGL_AZAMI; i++) {
    if (!k[i].dolu) continue;
    o.print(F("NL ")); o.print(i); o.print(' '); o.print(k[i].oncelik);
    o.print(' '); o.print(sta && strcmp(ag_durum.ssid, k[i].ad) == 0 ? 1 : 0);
    o.print(' '); o.println(k[i].ad);
  }
  o.print(F("NL bitti ")); o.println(agl_adet(k));
}

static int8_t ag_secili = -1;   /* son Na'nin yuvasi — Np onun parolasini yazar (CA12) */

#endif /* AG_KOMUT_H */
