// Ayarlar › Esitleme'nin saf yardimcilari (DOM'suz sinanir).

// bayt -> "0 B" | "512 B" | "12.3 kB" | "4.56 MB" (1000 tabani: dosya yoneticileriyle ayni)
export function boyutYaz(bayt) {
  if (!Number.isFinite(bayt) || bayt < 0) return "—";
  if (bayt < 1000) return `${Math.round(bayt)} B`;
  if (bayt < 1e6) return `${(bayt / 1e3).toFixed(1)} kB`;
  if (bayt < 1e9) return `${(bayt / 1e6).toFixed(2)} MB`;
  return `${(bayt / 1e9).toFixed(2)} GB`;
}
