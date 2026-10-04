<script setup>
// Buyuk olcum satiri: etiket + es aralikli rakam + birim (Canli ekrani, A40).
defineProps({
  etiket: { type: String, required: true },
  deger: { type: String, required: true },
  birim: { type: String, required: true },
  renk: { type: String, required: true },
});
</script>

<template>
  <div class="deger">
    <span class="et">{{ etiket }}</span>
    <b :class="renk">{{ deger }}</b>
    <i :class="renk">{{ birim }}</i>
  </div>
</template>
