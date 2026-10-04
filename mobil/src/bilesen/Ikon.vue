<script setup>
// Satir ici SVG ikonlar (aday A'nin cizimleri). Dis kaynak yok (CSP), metin yok; suslemedir.
defineProps({ ad: { type: String, required: true } });
</script>

<template>
  <svg class="ik" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
    <template v-if="ad === 'durum'"><path d="M4 16a8 8 0 1 1 16 0" /><path d="M12 16l4-5" /><circle cx="12" cy="16" r="1.2" fill="currentColor" /></template>
    <template v-else-if="ad === 'canli'"><path d="M3 12h4l2-6 4 12 2-6h6" /></template>
    <template v-else-if="ad === 'kayitlar'"><path d="M8 6h12M8 12h12M8 18h12" /><path d="M4 6h.01M4 12h.01M4 18h.01" /></template>
    <template v-else-if="ad === 'ayarlar'"><path d="M4 7h9M19 7h1M4 17h1M11 17h9" /><circle cx="16" cy="7" r="2.4" /><circle cx="8" cy="17" r="2.4" /></template>
    <template v-else-if="ad === 'dur'"><rect x="6.5" y="6.5" width="11" height="11" rx="1.5" fill="currentColor" stroke="none" /></template>
    <template v-else-if="ad === 'kayit'"><circle cx="12" cy="12" r="5.5" fill="currentColor" stroke="none" /></template>
    <template v-else-if="ad === 'esitle'"><path d="M5 10a7 7 0 0 1 12-4l2 2M19 14a7 7 0 0 1-12 4l-2-2" /><path d="M19 4v4h-4M5 20v-4h4" /></template>
    <template v-else-if="ad === 'tamam'"><path d="M5 12.5l4.5 4.5L19 7.5" /></template>
    <template v-else-if="ad === 'uyari'"><path d="M12 4l9 16H3z" /><path d="M12 10v4M12 17h.01" /></template>
  </svg>
</template>
