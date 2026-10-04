package tr.olcumkarti.mobil.kasa

/**
 * Hata TURU: `bicim` | `yok` | `bozuk` | `geri` | `ic-hata`. Mesaj = tur; istisna ayrintisi (yol, anahtar,
 * saglayici metni) kopruye ve gunluge GITMEZ (A45).
 */
class KasaHatasi(val tur: String) : Exception(tur)
