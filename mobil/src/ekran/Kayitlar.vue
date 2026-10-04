<script setup>
// Kayitlar (A41): 5D'ye kadar bos yer tutucu.
import Ikon from "../bilesen/Ikon.vue";
import { c } from "./metin.js";
</script>

<template>
  <div class="ekran">
    <div id="ky-yakinda" class="kart">
      <div class="kb"><Ikon ad="kayitlar" /><h2>{{ c("m.ky.yakinda") }}</h2></div>
      <p class="bilgi">{{ c("m.ky.yakinda_not") }}</p>
    </div>
  </div>
</template>
