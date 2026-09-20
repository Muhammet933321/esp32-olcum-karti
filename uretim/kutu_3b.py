# -*- coding: utf-8 -*-
"""8-kutu.html icindeki 3B goruntuleyici — WebGL, dis kutuphane YOK.

Neden WebGL: ilk surum canvas-2D "ressam algoritmasi" idi; yuz sirasi
ortalama derinlikle secildigi icin ince ic ice kutular yanlis ortuluyordu
(kullanici: "hangi obje onde hangisi arkada anlasilmiyor"). Derinlik
tamponu bu sorunu kokten kaldirir: her piksel kendi derinligini tutar.
Tarayicida yerlesik, cevrimdisi calisir, belge tek dosya kalir.

Bu modul yalnizca metin uretir: PANEL_HTML (kutunun isaretlemesi),
PANEL_CSS ve JS_3B (goruntuleyici). `kutu.py` bunlari belgeye gomer ve
`__SAHNE__` yer tutucusunu `sahne()` ciktisiyla degistirir. JS, disardaki
alt adim gorunumunun `cur` degiskenini ve `ciz()` cagrisini paylasir.

Kontroller (Blender gibi): sol tus surukle = dondur (nesneyi tutup cevirir),
orta/sag tus ya da Shift = kaydir, Ctrl+tekerlek ya da odakli tuvalde tekerlek =
imlece demirli yakinlastir (sayfa kaydirmasini calmaz), cift tik = sifirla,
ok tuslari = dondur, dokunmatikte tek parmak dondur / iki parmak kaydir +
yakinlastir.

B50g: "yakin olanlar saydam" karari duvarin DISA NORMALIYLE (sahne 'n'
alani) veriliyor — onceki surum blok merkezinin gorus-uzayi z'sine bakiyordu,
ust gorunumde tabani, egik gorunumde ic kat cubuklarini rastgele saydamlastiriyordu.
"hepsini goster" bitmis kutuyu OPAK cizer (soluk degil). WebGL baglami
kaybolursa (sekme arkada kalinca) yeniden kurulur. Bilgi satiri grup grup sayar.
"""
from __future__ import annotations

PANEL_HTML = """<div class="uc-boyut">
  <div class="uc-ust">
    <button id="uc-katla" aria-expanded="true" title="3B panelini aç/kapat">▾</button>
    <b>3B görünüm</b>
    <span class="kucuk">sol tuş: döndür · orta/sağ tuş ya da Shift: kaydır ·
      Ctrl+tekerlek (ya da tıklayıp tekerlek): yakınlaştır · çift tık: sıfırla ·
      ok tuşları: döndür</span>
  </div>
  <div id="uc-govde">
    <div class="uc-dugmeler">
      <button data-gorus="izo" aria-pressed="true">izometrik</button>
      <button data-gorus="ust">üst</button>
      <button data-gorus="on">ön</button>
      <button data-gorus="arka">arka</button>
      <button data-gorus="sol">sol</button>
      <button data-gorus="sag">sağ</button>
      <label class="kucuk">duvarlar
        <select id="uc-duvar">
          <option value="opak">opak</option>
          <option value="yakin">yakın olanlar saydam</option>
          <option value="saydam">hepsi saydam</option>
        </select></label>
      <label class="kucuk"><input type="checkbox" id="uc-hedef"> hedefi göster</label>
      <label class="kucuk"><input type="checkbox" id="uc-hepsi"> hepsini göster</label>
    </div>
    <div class="uc-sahne">
      <canvas id="uc-tuval" tabindex="0" aria-label="3B kutu görünümü"></canvas>
      <canvas id="uc-etiket"></canvas>
    </div>
    <div class="kucuk" id="uc-bilgi" style="margin-top:6px"></div>
  </div>
</div>"""

PANEL_CSS = """
.uc-boyut{border:1px solid var(--cizgi);border-radius:14px;padding:10px 12px;margin:14px 0;
          background:var(--yz2);scroll-margin-top:104px}
.uc-ust{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px}
#uc-katla{font:inherit;width:28px;height:28px;border-radius:8px;cursor:pointer;
          border:1px solid var(--cizgi);background:var(--yz);color:var(--m1)}
#uc-govde[hidden]{display:none}
.uc-dugmeler{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:8px}
.uc-dugmeler button{font:inherit;font-size:12px;padding:3px 10px;border-radius:99px;
          border:1px solid var(--cizgi);background:var(--yz);color:var(--m1);cursor:pointer}
.uc-dugmeler select{font:inherit;font-size:12px;padding:2px 6px;border-radius:8px;
          border:1px solid var(--cizgi);background:var(--yz);color:var(--m1)}
.uc-sahne{position:relative;width:100%;height:440px;border-radius:10px;overflow:hidden;
          background:linear-gradient(180deg,rgba(255,255,255,.04),rgba(0,0,0,.08))}
.uc-sahne canvas{position:absolute;inset:0;width:100%;height:100%;display:block}
#uc-tuval{cursor:grab;touch-action:none}
#uc-tuval:active{cursor:grabbing}
#uc-tuval:focus{outline:2px solid var(--s1);outline-offset:-2px}
.uc-dugmeler button[aria-pressed="true"]{background:var(--s1);color:#fff;border-color:var(--s1)}
#uc-etiket{pointer-events:none}
@media (max-width:640px){ .uc-sahne{height:320px} }
"""

JS_3B = r"""
 // ── 3B: WebGL, dis kutuphane yok. Derinlik tamponu -> dogru orten/ortulen.
 var SAHNE = __SAHNE__;
 var tuval = document.getElementById('uc-tuval');
 var etuval = document.getElementById('uc-etiket');
 var sahneKutu = document.querySelector('.uc-sahne');
 var bilgi = document.getElementById('uc-bilgi');
 var gl = tuval.getContext('webgl', {antialias: true, alpha: true, premultipliedAlpha: false});
 var etx = etuval.getContext('2d');
 var ayar = {hedef: false, duvar: 'opak'};
 function koyuTema(){
   try {
     var t = document.documentElement.getAttribute('data-theme');
     if (t === 'dark') return true; if (t === 'light') return false;
     return !!(window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches);
   } catch(e) { return false; }
 }
 try {
   var k0 = JSON.parse(localStorage.getItem('kutu-3b') || '{}');
   ayar.hedef = !!k0.hedef; if (k0.duvar) ayar.duvar = k0.duvar;
 } catch(e) {}
 document.getElementById('uc-hedef').checked = ayar.hedef;
 document.getElementById('uc-duvar').value = ayar.duvar;
 function ayarKaydet(){ try { localStorage.setItem('kutu-3b', JSON.stringify(ayar)); } catch(e) {} }

 // kamera: donme (yaw/pitch), kaydirma (pan, mm), yakinlastirma (zoom)
 // izo: kamera ON-SAG kosede -> on duvar sol yuzde (alisilmis izometrik)
 var GORUSLER = {izo: [-0.66, 0.55], ust: [0, 1.5], on: [0, 0.04], arka: [3.14159, 0.04],
                 sol: [1.5708, 0.04], sag: [-1.5708, 0.04]};
 var yaw = GORUSLER.izo[0], pitch = GORUSLER.izo[1], zoom = 1, pan = {x: 0, y: 0};
 var merkez = (function(){
   var x0 = 1e9, y0 = 1e9, z0 = 1e9, x1 = -1e9, y1 = -1e9, z1 = -1e9;
   SAHNE.forEach(function(b){
     x0 = Math.min(x0, b.x); y0 = Math.min(y0, b.y); z0 = Math.min(z0, b.z);
     x1 = Math.max(x1, b.x + b.dx); y1 = Math.max(y1, b.y + b.dy); z1 = Math.max(z1, b.z + b.dz);
   });
   return {x: (x0 + x1) / 2, y: (y0 + y1) / 2, z: (z0 + z1) / 2, en: x1 - x0, boy: y1 - y0, yuk: z1 - z0};
 })();

 // ── kucuk matris kutuphanesi (sutun-oncelikli 4x4) ──
 function m4(){ return new Float32Array([1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]); }
 function m4mul(a, b){
   var o = new Float32Array(16);
   for (var c = 0; c < 4; c++) for (var r = 0; r < 4; r++) {
     var t = 0; for (var k = 0; k < 4; k++) t += a[k*4 + r] * b[c*4 + k];
     o[c*4 + r] = t;
   }
   return o;
 }
 function m4T(x, y, z){ var m = m4(); m[12] = x; m[13] = y; m[14] = z; return m; }
 function m4S(x, y, z){ var m = m4(); m[0] = x; m[5] = y; m[10] = z; return m; }
 function m4Rx(a){ var m = m4(), c = Math.cos(a), s = Math.sin(a); m[5] = c; m[6] = s; m[9] = -s; m[10] = c; return m; }
 function m4Rz(a){ var m = m4(), c = Math.cos(a), s = Math.sin(a); m[0] = c; m[1] = s; m[4] = -s; m[5] = c; return m; }
 function m4Orto(l, r, b, t, n, f){
   var m = m4();
   m[0] = 2/(r-l); m[5] = 2/(t-b); m[10] = -2/(f-n);
   m[12] = -(r+l)/(r-l); m[13] = -(t+b)/(t-b); m[14] = -(f+n)/(f-n);
   return m;
 }
 function v4(m, x, y, z){        // m * (x,y,z,1)
   return [m[0]*x + m[4]*y + m[8]*z + m[12], m[1]*x + m[5]*y + m[9]*z + m[13],
           m[2]*x + m[6]*y + m[10]*z + m[14]];
 }

 // ── WebGL kurulumu ──
 var prog = null, kupYuz = null, kupKenar = null, loc = {}, glHazir = false;
 function golge(tip, kaynak){
   var s = gl.createShader(tip); gl.shaderSource(s, kaynak); gl.compileShader(s);
   if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
   return s;
 }
 function kur(){
   var VS = 'attribute vec3 aP; attribute vec3 aN; uniform mat4 uPV; uniform mat4 uM; uniform mat4 uV;'
     + 'varying vec3 vN; void main(){ vN = mat3(uV) * aN; gl_Position = uPV * uM * vec4(aP, 1.0); }';
   var FS = 'precision mediump float; uniform vec4 uC; uniform float uDuz; varying vec3 vN;'
     + 'void main(){ vec3 n = normalize(vN); float d = max(dot(n, normalize(vec3(0.35, 0.55, 0.76))), 0.0);'
     + 'float i = mix(0.58 + 0.42 * d, 1.0, uDuz); gl_FragColor = vec4(uC.rgb * i, uC.a); }';
   prog = gl.createProgram();
   gl.attachShader(prog, golge(gl.VERTEX_SHADER, VS));
   gl.attachShader(prog, golge(gl.FRAGMENT_SHADER, FS));
   gl.linkProgram(prog);
   if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
   gl.useProgram(prog);
   ['aP', 'aN'].forEach(function(a){ loc[a] = gl.getAttribLocation(prog, a); });
   ['uPV', 'uM', 'uV', 'uC', 'uDuz'].forEach(function(u){ loc[u] = gl.getUniformLocation(prog, u); });
   // birim kup: 6 yuz x 2 ucgen; her kosede normal
   var Y = [[0,0,-1, [0,0,0],[0,1,0],[1,1,0],[1,0,0]], [0,0,1, [0,0,1],[1,0,1],[1,1,1],[0,1,1]],
            [0,-1,0, [0,0,0],[1,0,0],[1,0,1],[0,0,1]], [0,1,0, [0,1,0],[0,1,1],[1,1,1],[1,1,0]],
            [-1,0,0, [0,0,0],[0,0,1],[0,1,1],[0,1,0]], [1,0,0, [1,0,0],[1,1,0],[1,1,1],[1,0,1]]];
   var v = [];
   Y.forEach(function(y){
     var n = [y[0], y[1], y[2]], p = [y[3], y[4], y[5], y[6]];
     [[0,1,2],[0,2,3]].forEach(function(t){ t.forEach(function(i){ v.push(p[i][0], p[i][1], p[i][2], n[0], n[1], n[2]); }); });
   });
   kupYuz = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, kupYuz);
   gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(v), gl.STATIC_DRAW);
   var e = [], K = [[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]];
   [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]].forEach(function(l){
     l.forEach(function(i){ e.push(K[i][0], K[i][1], K[i][2], 0, 0, 1); }); });
   kupKenar = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, kupKenar);
   gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(e), gl.STATIC_DRAW);
   gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LEQUAL);
   gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
   gl.enable(gl.CULL_FACE); gl.cullFace(gl.BACK);
   glHazir = true;
 }
 // baglam kaybi: sekme uzun sure arkada kalinca tarayici WebGL'i geri alabilir
 tuval.addEventListener('webglcontextlost', function(e){ e.preventDefault(); glHazir = false; bilgi.textContent = '3B duraklatıldı…'; });
 tuval.addEventListener('webglcontextrestored', function(){ try { kur(); ciz(); } catch(err) { bilgi.textContent = '3B çizilemedi: ' + err.message; } });
 function bagla(buf){
   gl.bindBuffer(gl.ARRAY_BUFFER, buf);
   gl.enableVertexAttribArray(loc.aP); gl.vertexAttribPointer(loc.aP, 3, gl.FLOAT, false, 24, 0);
   gl.enableVertexAttribArray(loc.aN); gl.vertexAttribPointer(loc.aN, 3, gl.FLOAT, false, 24, 12);
 }
 function hexRgb(hex){ var n = parseInt(hex.slice(1), 16); return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255]; }
 function grupAdi(ad){ return ad.replace(/\s+\d+$/, ''); }

 var olcek = 1, PV = null, V = null;
 function boyutla(){
   var op = window.devicePixelRatio || 1;
   var w = sahneKutu.clientWidth, h = sahneKutu.clientHeight;
   if (tuval.width !== Math.round(w * op)) { tuval.width = Math.round(w * op); tuval.height = Math.round(h * op); }
   if (etuval.width !== Math.round(w * op)) { etuval.width = Math.round(w * op); etuval.height = Math.round(h * op); }
   return {w: w, h: h, op: op};
 }
 function kamera(w, h){
   // olcek: sahnenin sinir kutusunu BU donusle izdusurup sigdir — on/yan
   // gorunumlerde kutu kucuk kalmasin (eskiden sabit en/boy orani vardi)
   var R = m4mul(m4Rx(pitch - Math.PI / 2), m4mul(m4Rz(yaw), m4T(-merkez.x, -merkez.y, -merkez.z)));
   var x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
   for (var i = 0; i < 8; i++) {
     var c = v4(R, merkez.x + (i & 1 ? 1 : -1) * merkez.en / 2, merkez.y + (i & 2 ? 1 : -1) * merkez.boy / 2,
                merkez.z + (i & 4 ? 1 : -1) * merkez.yuk / 2);
     x0 = Math.min(x0, c[0]); x1 = Math.max(x1, c[0]); y0 = Math.min(y0, c[1]); y1 = Math.max(y1, c[1]);
   }
   olcek = Math.min(w / ((x1 - x0) * 1.25 + 40), h / ((y1 - y0) * 1.25 + 40)) * zoom;   // px / mm
   V = m4mul(m4T(pan.x, pan.y, 0), R);
   var hw = w / 2 / olcek, hh = h / 2 / olcek;
   PV = m4mul(m4Orto(-hw, hw, -hh, hh, -2000, 2000), V);
 }
 function ekran(w, h, x, y, z){
   var c = v4(PV, x, y, z);
   return {x: (c[0] * 0.5 + 0.5) * w, y: (1 - (c[1] * 0.5 + 0.5)) * h};
 }

 function ciz(){
   var gv = document.getElementById('uc-govde');
   if (!gl || !glHazir || (gv && gv.hidden)) return;
   var b = boyutla(), w = b.w, h = b.h, op = b.op;
   kamera(w, h);
   gl.viewport(0, 0, tuval.width, tuval.height);
   gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
   gl.uniformMatrix4fv(loc.uPV, false, PV);
   gl.uniformMatrix4fv(loc.uV, false, V);
   var hepsi = document.getElementById('uc-hepsi').checked;
   var koyu = koyuTema();
   var opak = [], saydam = [], etiketler = [], gruplar = {}, kuruldu = 0, sayim = {};
   SAHNE.forEach(function(bl){
     var ileride = bl.gor > cur && !hepsi;             // "hepsini goster" = bitmis kutu, opak
     if (!ileride) { kuruldu++; sayim[bl.g] = (sayim[bl.g] || 0) + 1; }
     var kapak = bl.g === 'kapak';
     if (ileride && !ayar.hedef) return;
     if (kapak && ileride) return;
     var vur = bl.vur.indexOf(cur) >= 0;
     var duvar = bl.g === 'duvar' || bl.g === 'duvar_ic' || bl.g === 'delik' || kapak;
     var zg = v4(V, bl.x + bl.dx / 2, bl.y + bl.dy / 2, bl.z + bl.dz / 2)[2];   // gorus uzayi z
     var alfa = 1.0;
     if (duvar) {
       if (ayar.duvar === 'saydam') alfa = 0.22;
       else if (ayar.duvar === 'yakin' && bl.n) {
         // disa normal kameraya bakiyorsa duvar bize yakin: saydam. Normal gorus
         // uzayina V'nin 3x3'uyle tasinir; kamera -z'ye bakar -> nz > 0 = bize donuk.
         var nz = V[2] * bl.n[0] + V[6] * bl.n[1] + V[10] * bl.n[2];
         if (nz > 0.12) alfa = 0.22;
       }
     }
     if (ileride) alfa = 0.10;
     var rgb = hexRgb(bl.r);
     if (vur) rgb = rgb.map(function(c){ return Math.min(1, c * 1.25 + 0.05); });
     var kayit = {bl: bl, rgb: rgb, alfa: alfa, vur: vur, ileride: ileride, zg: zg};
     (alfa >= 0.99 ? opak : saydam).push(kayit);
     if (!ileride) {
       if (bl.g === 'parca') etiketler.push({ad: bl.ad, x: bl.x + bl.dx / 2, y: bl.y + bl.dy / 2, z: bl.z + bl.dz, vur: vur});
       else if (vur) {
         var ga = grupAdi(bl.ad);
         var gr = gruplar[ga] || (gruplar[ga] = {n: 0, x: 0, y: 0, z: 0});
         gr.n++; gr.x += bl.x + bl.dx / 2; gr.y += bl.y + bl.dy / 2; gr.z = Math.max(gr.z, bl.z + bl.dz);
       }
     }
   });
   Object.keys(gruplar).forEach(function(ga){
     var gr = gruplar[ga];
     etiketler.push({ad: gr.n > 1 ? ga + ' ×' + gr.n : ga, x: gr.x / gr.n, y: gr.y / gr.n, z: gr.z, vur: true});
   });
   saydam.sort(function(a, b){ return a.zg - b.zg; });         // uzak once
   function blokCiz(k, kenarMi){
     var bl = k.bl;
     var M = m4mul(m4T(bl.x, bl.y, bl.z), m4S(bl.dx, bl.dy, bl.dz));
     gl.uniformMatrix4fv(loc.uM, false, M);
     if (!kenarMi) {
       gl.uniform4f(loc.uC, k.rgb[0], k.rgb[1], k.rgb[2], k.alfa);
       gl.uniform1f(loc.uDuz, 0.0);
       gl.drawArrays(gl.TRIANGLES, 0, 36);
     } else {
       var ka = k.ileride ? 0.3 : (k.alfa < 0.99 ? 0.35 : 0.9);
       if (k.vur) gl.uniform4f(loc.uC, 0.95, 0.76, 0.3, 1.0);
       else if (koyu) gl.uniform4f(loc.uC, 0.92, 0.88, 0.8, k.ileride ? 0.35 : ka * 0.75);
       else gl.uniform4f(loc.uC, 0.08, 0.06, 0.03, ka);
       gl.uniform1f(loc.uDuz, 1.0);
       gl.drawArrays(gl.LINES, 0, 24);
     }
   }
   // 1) opak yuzler (derinlik yazar), 2) kenarlar, 3) saydam yuzler uzak->yakin
   gl.enable(gl.POLYGON_OFFSET_FILL); gl.polygonOffset(1.0, 1.0);
   gl.depthMask(true); bagla(kupYuz);
   opak.forEach(function(k){ blokCiz(k, false); });
   gl.disable(gl.POLYGON_OFFSET_FILL);
   bagla(kupKenar);
   opak.forEach(function(k){ blokCiz(k, true); });
   gl.depthMask(false);
   bagla(kupYuz); gl.disable(gl.CULL_FACE);
   saydam.forEach(function(k){ blokCiz(k, false); });
   gl.enable(gl.CULL_FACE);
   bagla(kupKenar);
   saydam.forEach(function(k){ blokCiz(k, true); });
   gl.depthMask(true);
   // etiketler: 2B katman
   etx.setTransform(op, 0, 0, op, 0, 0);
   etx.clearRect(0, 0, w, h);
   etx.textAlign = 'center'; etx.textBaseline = 'bottom';
   // Ortulme: etiket noktasi opak bir blogun ardindaysa etiketi cizme (opak
   // duvarin ustunde ucan yazi yaniltiyordu). Bloklar eksen hizali: her yuzu
   // ekrana izdusur, nokta icindeyse duzlemden derinligi bul.
   var opakBloklar = opak.map(function(k){ return k.bl; });
   function ortulu(e){
     var q = v4(PV, e.x, e.y, e.z), px = q[0], py = q[1], pz = q[2];
     for (var i = 0; i < opakBloklar.length; i++) {
       var bl = opakBloklar[i];
       if (bl.ad === e.ad && bl.g === 'parca') continue;
       var X = [bl.x, bl.x + bl.dx], Yy = [bl.y, bl.y + bl.dy], Z = [bl.z, bl.z + bl.dz];
       var K8 = [];
       for (var a2 = 0; a2 < 8; a2++) K8.push(v4(PV, X[a2 & 1], Yy[(a2 >> 1) & 1], Z[(a2 >> 2) & 1]));
       var YZ = [[0,1,3,2],[4,5,7,6],[0,1,5,4],[2,3,7,6],[0,2,6,4],[1,3,7,5]];
       for (var f = 0; f < 6; f++) {
         var c0 = K8[YZ[f][0]], c1 = K8[YZ[f][1]], c2 = K8[YZ[f][2]], c3 = K8[YZ[f][3]];
         var tri = [[c0, c1, c2], [c0, c2, c3]];
         for (var t2 = 0; t2 < 2; t2++) {
           var A = tri[t2][0], B = tri[t2][1], C = tri[t2][2];
           var d = (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1]);
           if (Math.abs(d) < 1e-9) continue;
           var l1 = ((B[1] - C[1]) * (px - C[0]) + (C[0] - B[0]) * (py - C[1])) / d;
           var l2 = ((C[1] - A[1]) * (px - C[0]) + (A[0] - C[0]) * (py - C[1])) / d;
           var l3 = 1 - l1 - l2;
           if (l1 < -1e-4 || l2 < -1e-4 || l3 < -1e-4) continue;
           var zf = l1 * A[2] + l2 * B[2] + l3 * C[2];
           if (zf < pz - 1e-3) return true;      // klip z: kucuk = yakin
         }
       }
     }
     return false;
   }
   var gizliVurgu = false;
   etiketler.forEach(function(e){
     if (ortulu(e)) { if (e.vur) gizliVurgu = true; return; }
     var p = ekran(w, h, e.x, e.y, e.z);
     etx.font = (e.vur ? '600 ' : '') + '12px ui-monospace,Consolas,monospace';
     etx.lineWidth = 3; etx.strokeStyle = koyu ? 'rgba(0,0,0,.75)' : 'rgba(0,0,0,.6)';
     etx.strokeText(e.ad, p.x, p.y - 4);
     etx.fillStyle = e.vur ? '#f2c14e' : 'rgba(255,255,255,.9)';
     etx.fillText(e.ad, p.x, p.y - 4);
   });
   var GRUP = {kutu: 'taban', duvar: 'dış kat', duvar_ic: 'iç kat', direk: 'direk', delik: 'delik',
               panel: 'panel', tasiyici: 'ayak/altlık', parca: 'parça', kapak: 'kapak'};
   var ozet = Object.keys(GRUP).filter(function(g){ return sayim[g]; })
     .map(function(g){ return GRUP[g] + ' ' + sayim[g]; }).join(' · ');
   bilgi.textContent = (hepsi ? 'bitmiş kutu: ' + ozet
     : kuruldu ? 'bu adıma kadar: ' + ozet + (ayar.hedef ? ' · soluk olanlar sırada' : '')
     : 'henüz parça yok' + (ayar.hedef ? ' — soluk çizgiler yapacağın kutuyu gösteriyor' : ' — "hedefi göster" ile hedef kutuyu görebilirsin'))
     + (gizliVurgu && ayar.duvar === 'opak' ? ' · bu adımın parçası duvarın arkasında: "yakın olanlar saydam" seç ya da üstten bak' : '');
 }

 // ── etkilesim: Blender gibi ──
 var isaretler = {}, sonMerkez = null, sonUzak = null;
 function isaretListe(){ return Object.keys(isaretler).map(function(k){ return isaretler[k]; }); }
 tuval.addEventListener('contextmenu', function(e){ e.preventDefault(); });
 tuval.addEventListener('pointerdown', function(e){
   isaretler[e.pointerId] = {x: e.clientX, y: e.clientY,
     kaydir: e.button === 1 || e.button === 2 || e.shiftKey};
   tuval.setPointerCapture(e.pointerId); e.preventDefault();
   sonMerkez = null; sonUzak = null;
 });
 tuval.addEventListener('pointermove', function(e){
   var p = isaretler[e.pointerId]; if (!p) return;
   var L = isaretListe();
   if (L.length >= 2) {                                  // iki parmak: kaydir + yakinlastir
     p.x = e.clientX; p.y = e.clientY;
     var a = L[0], b2 = L[1];
     var m = {x: (a.x + b2.x) / 2, y: (a.y + b2.y) / 2}, u = Math.hypot(a.x - b2.x, a.y - b2.y);
     if (sonMerkez) { pan.x += (m.x - sonMerkez.x) / olcek; pan.y -= (m.y - sonMerkez.y) / olcek; }
     if (sonUzak) zoom = Math.max(0.4, Math.min(5, zoom * (u / sonUzak)));
     sonMerkez = m; sonUzak = u; ciz(); return;
   }
   var dx = e.clientX - p.x, dy = e.clientY - p.y;
   if (p.kaydir) { pan.x += dx / olcek; pan.y -= dy / olcek; }
   else {
     // nesneyi tutup cevirme: saga surukle -> nesne saga doner (Blender turntable)
     yaw += dx * 0.01;
     pitch = Math.max(-0.35, Math.min(1.55, pitch + dy * 0.008));
   }
   p.x = e.clientX; p.y = e.clientY; ciz();
 });
 function birak(e){ delete isaretler[e.pointerId]; sonMerkez = null; sonUzak = null; }
 tuval.addEventListener('pointerup', birak);
 tuval.addEventListener('pointercancel', birak);
 tuval.addEventListener('dblclick', function(){ gorus('izo'); });
 tuval.addEventListener('pointerdown', function(){ try { tuval.focus({preventScroll: true}); } catch(e) {} });
 tuval.addEventListener('wheel', function(e){
   // sayfayi kaydirirken tuvalin ustunden gecince yakinlastirma yapmasin:
   // Ctrl basili ya da tuval odakli (tiklanmis) olmali.
   if (!e.ctrlKey && document.activeElement !== tuval) return;
   e.preventDefault();
   var r = tuval.getBoundingClientRect();
   var cx = e.clientX - r.left - r.width / 2, cy = e.clientY - r.top - r.height / 2;   // px, merkezden
   var eski = olcek;
   zoom = Math.max(0.4, Math.min(5, zoom * (e.deltaY < 0 ? 1.12 : 0.9)));
   kamera(r.width, r.height);                                              // olcek guncellendi
   // imlecin altindaki nokta yerinde kalsin: pan += imlec_px * (1/olcek_yeni - 1/olcek_eski)
   pan.x += cx * (1 / olcek - 1 / eski);
   pan.y -= cy * (1 / olcek - 1 / eski);
   ciz();
 }, {passive: false});
 tuval.addEventListener('keydown', function(e){
   var k = e.key;
   if (k === 'ArrowLeft') yaw -= 0.08; else if (k === 'ArrowRight') yaw += 0.08;
   else if (k === 'ArrowUp') pitch = Math.min(1.55, pitch + 0.06);
   else if (k === 'ArrowDown') pitch = Math.max(-0.35, pitch - 0.06);
   else if (k === '+' || k === '=') zoom = Math.min(5, zoom * 1.12);
   else if (k === '-') zoom = Math.max(0.4, zoom * 0.9);
   else if (k === 'Home' || k === '0') { gorus('izo'); return; }
   else return;
   e.preventDefault(); ciz();
 });
 function gorus(ad){
   var g = GORUSLER[ad]; yaw = g[0]; pitch = g[1]; pan = {x: 0, y: 0}; zoom = 1;
   [].forEach.call(document.querySelectorAll('[data-gorus]'), function(b){
     b.setAttribute('aria-pressed', b.dataset.gorus === ad ? 'true' : 'false'); });
   ciz();
 }
 [].forEach.call(document.querySelectorAll('[data-gorus]'), function(b){
   b.addEventListener('click', function(){ gorus(b.dataset.gorus); });
 });
 document.getElementById('uc-hedef').addEventListener('change', function(e){ ayar.hedef = e.target.checked; ayarKaydet(); ciz(); });
 document.getElementById('uc-duvar').addEventListener('change', function(e){ ayar.duvar = e.target.value; ayarKaydet(); ciz(); });
 document.getElementById('uc-hepsi').addEventListener('change', ciz);
 // panel acilir-kapanir; tercih tarayicida saklanir
 var katla = document.getElementById('uc-katla');
 var govde = document.getElementById('uc-govde');
 function katlaUygula(kapali){
   govde.hidden = kapali;
   katla.textContent = kapali ? '▸' : '▾';
   katla.setAttribute('aria-expanded', kapali ? 'false' : 'true');
   try { localStorage.setItem('kutu-3b-kapali', kapali ? '1' : ''); } catch(e) {}
   if (!kapali) ciz();
 }
 katla.addEventListener('click', function(){ katlaUygula(!govde.hidden); });
 var kapaliBas = false;
 try { kapaliBas = localStorage.getItem('kutu-3b-kapali') === '1'; } catch(e) {}
 if (gl) { try { kur(); } catch(err) { gl = null; bilgi.textContent = '3B çizilemedi: ' + err.message; } }
 else bilgi.textContent = 'Tarayıcı WebGL desteklemiyor — 3B görünüm kapalı.';
 katlaUygula(kapaliBas);
 window.addEventListener('resize', ciz);
 try { matchMedia('(prefers-color-scheme: dark)').addEventListener('change', ciz); } catch(e) {}
"""
