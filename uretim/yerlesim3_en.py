# -*- coding: utf-8 -*-
"""Yerlesim rehberinin (BELGELER/7-yerlesim.html) INGILIZCE karsiliklari.

Anahtar, Turkce metnin KENDISI (`yerlesim3_belge.T()` onu birebir arar);
Turkce metin degisirse karsiligi eskir ve `python yerlesim3.py`'nin
"belge dili" denetimi kirmizi doner — ceviri sessizce bayatlamaz.

{ad} yer tutuculari (sayi, delik adi, parca referansi) Ingilizcede de AYNEN
kalmali; HTML etiketleri de. Parca referanslari (R40, J5, U3A...), sayilar ve
koordinatlar cevrilmez.

Terimler (cekirdek belgelerle ortak): KAPI -> GATE, delikli plaket ->
perfboard, born jak -> banana jack, klemens -> terminal block, sont -> shunt,
gerginlik deligi -> strain-relief hole, lehim yuzu / parca yuzu -> solder
side / component side.
"""
from belge_dil import M

CEVIRI = [
    M(' (pay ',
      ' (margin '),
    M('\n'
      '<div class="kpi">\n'
      '  <div><span>Alt adım</span><b>{n_aa}</b></div>\n'
      '  <div><span>Ana kart (A)</span><b>{aW}×{aH}</b></div>\n'
      '  <div><span>HV kartı (B)</span><b>{bW}×{bH}</b></div>\n'
      '  <div><span>Lehim izi · tel</span><b>{toplam_iz} · {toplam_tel}</b></div>\n'
      '  <div><span>Denetim</span><b>{gecti}/{toplam}</b></div>\n'
      '</div>\n'
      '\n'
      '<p>Kurulum <b>LEGO kılavuzu gibi</b>: {n_adim} büyük adım ({adimlar}),\n'
      'her biri kendi içinde küçük alt adımlara bölünmüş. Her alt adımda birkaç parça ya da birkaç\n'
      'lehim izi var; her büyük adım bir <b>KAPI</b> ölçümüyle bitiyor ve o geçmeden sonrakine\n'
      'geçilmiyor. Sıra: <b>önce alçak parçalar, sonra yüksekler</b>; ters takılabilen parça\n'
      '(elektrolitik, diyot, soket, transistör, regülatör, başlık) hep kendi alt adımında; '
      'lehim izleri\n'
      'parçalardan, kablolar izlerden sonra.</p>\n'
      '\n'
      '<p>Plaketler <b>her delikte ayrı pedli</b>. Ana kart (A), 13×23 cm plaketten\n'
      '({kaW}×{kaH} delik) <b>{aW}×{aH} delik</b> kesilerek yapılıyor;\n'
      'HV zinciri (B) ayrı bir 5×5 cm plakette ({bW}×{bH}). Şönt,\n'
      "J3, J7 ve Q1 <b>plakette değil</b>: 11.5 A'e varan yük akımını plaket bakırı\n"
      'taşımaz. Onlar kutuda (panel jakları, şönt altlığı, soğutucu); plakete yalnızca Kelvin\n'
      "uçları, tek yıldız toprak teli ve kapı teli geliyor. <b>615 V'luk giriş A kartına\n"
      "hiç girmez</b>: B kartındaki zincirden A'ya yalnızca ~1.7 V'luk alt düğüm gelir.</p>\n"
      '\n'
      '<div class="uy"><b>Koordinat:</b> sütun harf, satır sayı; <b>A1 parça yüzünden bakınca\n'
      'sol üst</b>. Lehim yüzü çizimi <b>aynalı</b> — plaketi ters çevirince aynı harf\n'
      'aynı deliğin üstüne gelir. Yalıtımlı teller lehim yüzünde; uçları oradaki\n'
      'bacağa ya da pede lehimlenir.</div>\n'
      '\n'
      '<h2>Önce bunlar</h2>\n'
      '<table>\n'
      '<tr><th>Ne</th><th>Neden</th></tr>\n'
      '<tr><td><b>Bacak sırasını multimetreyle doğrula</b></td>\n'
      '<td>2N2222-331: <b>{b_q2}</b> · BC557: <b>{b_q3}</b> ·\n'
      'TL431: <b>{b_u1}</b> · 7912: <b>{b_u9}</b>\n'
      '(yazılı yüz sana dönük, bacaklar aşağı, soldan sağa). Şemadaki Q2 sembolü\n'
      "BC547'den alınmış (C-B-E); numarayla lehimlenirse C ile E yer değiştirir ve\n"
      'transistör <b>yarı çalışır</b> — sessiz kusur. Diyot kademesinde baz, iki\n'
      'eklemin ortak ucudur. Her transistörün kendi alt adımında bu uyarı tekrar '
      'ediliyor.</td></tr>\n'
      '<tr><td><b>ADS modül pin sırası</b></td><td>Plan {ads} sırasını varsayıyor.\n'
      'Modülün üstünde yazanla karşılaştır.</td></tr>\n'
      '<tr><td><b>Ped çapını kumpasla ölç</b></td><td>Kaçak yolu hesabı lehimli iletken\n'
      'çapını {pad} mm alıyor. Ölçtüğün daha büyükse söyle, denetim yeniden\n'
      'koşsun.</td></tr>\n'
      '<tr><td><b>HV kartında aralık</b></td><td>615 V takviyeli yalıtım <b>bakırdan bakıra</b>\n'
      'ölçülür. Eski "5 delik atla" merkezden merkezeydi (12.70 mm); pedlerle bakırdan\n'
      'bakıra {bes} mm kalıyordu, yetmiyordu. Kılavuz ve\n'
      'bu plan artık <b>{f9} adım</b> diyor. HV kartında 615 V ucu ile alt\n'
      'düğüm zaten karşı köşelerde; en dar çift:\n'
      '{en_dar}.</td></tr>\n'
      '</table>\n',
      '\n'
      '<div class="kpi">\n'
      '  <div><span>Sub-steps</span><b>{n_aa}</b></div>\n'
      '  <div><span>Main board (A)</span><b>{aW}×{aH}</b></div>\n'
      '  <div><span>HV board (B)</span><b>{bW}×{bH}</b></div>\n'
      '  <div><span>Solder traces · wires</span><b>{toplam_iz} · {toplam_tel}</b></div>\n'
      '  <div><span>Checks</span><b>{gecti}/{toplam}</b></div>\n'
      '</div>\n'
      '\n'
      '<p>Assembly works <b>like LEGO instructions</b>: {n_adim} main steps ({adimlar}),\n'
      'each split into small sub-steps. Every sub-step has a few parts or a few\n'
      "solder traces; every main step ends with a <b>GATE</b> measurement, and you don't\n"
      'move on until it passes. Order: <b>low-profile parts first, then tall ones</b>; any '
      'part that\n'
      'can go in backwards (electrolytic, diode, socket, transistor, regulator, header) '
      'always gets its\n'
      'own sub-step; solder traces come after the parts, wires after the traces.</p>\n'
      '\n'
      '<p>The boards are <b>pad-per-hole</b> perfboard. The main board (A) is cut from a '
      '13×23 cm board\n'
      '({kaW}×{kaH} holes) down to <b>{aW}×{aH} holes</b>;\n'
      'the HV chain (B) sits on a separate 5×5 cm board ({bW}×{bH}). The shunt,\n'
      'J3, J7 and Q1 are <b>not on the perfboard</b>: perfboard copper cannot carry load\n'
      'currents of up to 11.5 A. They live in the enclosure (panel jacks, shunt mount, '
      'heatsink); only the Kelvin\n'
      'leads, the single star-ground wire and the gate wire come to the board. <b>The 615 '
      'V input never\n'
      'reaches board A</b>: from the chain on board B only the ~1.7 V bottom node comes '
      'over to A.</p>\n'
      '\n'
      '<div class="uy"><b>Coordinates:</b> column = letter, row = number; <b>A1 is top '
      'left seen from the\n'
      'component side</b>. The solder-side drawing is <b>mirrored</b> — when you flip the '
      'board, the same\n'
      'letter lands over the same hole. Insulated wires run on the solder side; their ends are\n'
      'soldered to the lead or pad there.</div>\n'
      '\n'
      '<h2>Do these first</h2>\n'
      '<table>\n'
      '<tr><th>What</th><th>Why</th></tr>\n'
      '<tr><td><b>Check the pin order with a multimeter</b></td>\n'
      '<td>2N2222-331: <b>{b_q2}</b> · BC557: <b>{b_q3}</b> ·\n'
      'TL431: <b>{b_u1}</b> · 7912: <b>{b_u9}</b>\n'
      '(printed face towards you, leads down, left to right). The Q2 symbol in the schematic\n'
      'comes from the BC547 (C-B-E); soldered by pin number, C and E swap and the\n'
      'transistor <b>half works</b> — a silent defect. On the diode range the base is the\n'
      "common terminal of the two junctions. This warning is repeated in each transistor's "
      'own sub-step.</td></tr>\n'
      '<tr><td><b>ADS module pin order</b></td><td>The plan assumes the order {ads}.\n'
      'Compare with what is printed on the module.</td></tr>\n'
      '<tr><td><b>Measure the pad diameter with calipers</b></td><td>The creepage '
      'calculation takes the soldered conductor\n'
      'diameter as {pad} mm. If you measure larger, say so and the check will be\n'
      're-run.</td></tr>\n'
      '<tr><td><b>Spacing on the HV board</b></td><td>615 V reinforced insulation is '
      'measured <b>copper to copper</b>.\n'
      'The old "skip 5 holes" was centre to centre (12.70 mm); with the pads, copper to\n'
      'copper left {bes} mm, which was not enough. The guide and\n'
      'this plan now say <b>{f9} pitches</b>. On the HV board the 615 V end and the bottom\n'
      'node already sit in opposite corners; the tightest pair:\n'
      '{en_dar}.</td></tr>\n'
      '</table>\n'),
    M('standart (karbon) olur',
      'standard (carbon) is fine'),
    M('TL431 ön gerilim direnci',
      'TL431 bias resistor'),
    M('metal film önerilir (standart da çalışır)',
      'metal film recommended (standard also works)'),
    M('Vref bölücü üst — sıfır noktasının kararlılığı',
      'Vref divider top — zero-point stability'),
    M('Vref bölücü alt — sıfır noktasının kararlılığı',
      'Vref divider bottom — zero-point stability'),
    M('metal film %1 ZORUNLU',
      'metal film 1% REQUIRED'),
    M('NORMAL kanal bölücü üst (oran)',
      'NORMAL channel divider top (ratio)'),
    M('NORMAL kanal bölücü alt (oran)',
      'NORMAL channel divider bottom (ratio)'),
    M('NORMAL kanal RC süzgeci — HV kanalıyla (R17) eşleşmeli',
      'NORMAL channel RC filter — must match the HV channel (R17)'),
    M("HV zinciri (oran) — 615 V'u 6'ya bölüyor",
      'HV chain (ratio) — splits 615 V into 6'),
    M('HV bölücü alt bacak (oran)',
      'HV divider bottom leg (ratio)'),
    M('HV kanal RC süzgeci — NORMAL kanalla (R7) eşleşmeli',
      'HV channel RC filter — must match the NORMAL channel (R7)'),
    M('şönt S+ Kelvin ucu RC direnci',
      'shunt S+ Kelvin lead RC resistor'),
    M('şönt S− Kelvin ucu RC direnci',
      'shunt S− Kelvin lead RC resistor'),
    M('skop bölücü üst (oran)',
      'scope divider top (ratio)'),
    M('Sallen-Key süzgeç (f0/Q)',
      'Sallen-Key filter (f0/Q)'),
    M('skop bölücü alt (oran)',
      'scope divider bottom (ratio)'),
    M('I²C SCL pull-up',
      'I²C SCL pull-up'),
    M('I²C SDA pull-up',
      'I²C SDA pull-up'),
    M('skop kelepçe seri direnci (ESP32 girişi koruma)',
      'scope clamp series resistor (ESP32 input protection)'),
    M('fark yükselteci giriş (oran: kazanç)',
      'difference amplifier input (ratio: gain)'),
    M('fark yükselteci geri besleme (oran: kazanç)',
      'difference amplifier feedback (ratio: gain)'),
    M('hızlı akım kelepçe seri direnci (ESP32 girişi koruma)',
      'fast-current clamp series resistor (ESP32 input protection)'),
    M('ADS giriş koruma seri direnci (V)',
      'ADS input protection series resistor (V)'),
    M('ADS giriş koruma seri direnci (HV)',
      'ADS input protection series resistor (HV)'),
    M('ADS giriş koruma seri direnci (VREF)',
      'ADS input protection series resistor (VREF)'),
    M('ADS giriş koruma seri direnci (şönt +)',
      'ADS input protection series resistor (shunt +)'),
    M('ADS giriş koruma seri direnci (şönt −)',
      'ADS input protection series resistor (shunt −)'),
    M('7912 asgari yükü (12 mA, 144 mW → 1/2 W)',
      '7912 minimum load (12 mA, 144 mW → 1/2 W)'),
    M('+3V3 boşaltma direnci',
      '+3V3 bleeder resistor'),
    M('Q1 kapı pull-down (failsafe)',
      'Q1 gate pull-down (failsafe)'),
    M('kapı sürücü Q2→Q3 baz direnci',
      'gate driver Q2→Q3 base resistor'),
    M("kapı sürücü Q2 baz direnci (ESP32'den)",
      'gate driver Q2 base resistor (from the ESP32)'),
    M('Q1 kapı seri direnci',
      'Q1 gate series resistor'),
    M('\n'
      '<h2 id="direncler">Dirençler — tür ve güç</h2>\n'
      '<p><b>Güç:</b> hepsi <b>1/4 W</b>, yalnız R40 <b>1/2 W</b>. Tasarım hesabı '
      '(tasarim3 §12): en çok\n'
      "yüklenen direnç R20, 1/4 W'ın %15'i; en yüksek gerilim 820K zincirinde 102 V (1/4 W'ın 200 V\n"
      "sınırının %51'i). Daha büyük gövde <b>alma</b>: parazitik kapasite skop bandını keser.</p>\n"
      '<p><b>Tür:</b> ölçüm <b>oranını kuran</b> {n_z} direnç <b>metal film %1</b> olmak '
      'zorunda — karbon\n'
      'filmin gerilime bağlı değeri ve 1000 saatte %1–3 sürüklenmesi kalibrasyonla silinmez (§11).\n'
      '{n_o} direnç için metal film önerilir (sıfır noktası ve süzgeç kararlılığı), geri '
      'kalanı standart\n'
      'karbon olabilir. Stoktaki direnc.net paketleri (mavi gövde, 5 halka) metal film; motorobit\n'
      'paketleri ve dökme dirençler bej gövde, 4 halka = karbon.</p>\n'
      '<table><tr><th>Direnç</th><th>Değer</th><th>Güç</th><th>Tür</th><th>Görevi</th><th '
      "class='s'>Adım</th></tr>\n"
      '{satir}</table>',
      '\n'
      '<h2 id="direncler">Resistors — type and power</h2>\n'
      '<p><b>Power:</b> all <b>1/4 W</b>, only R40 is <b>1/2 W</b>. Design calculation '
      '(tasarim3 §12): the most heavily\n'
      'loaded resistor is R20, at 15% of 1/4 W; the highest voltage is 102 V across an '
      '820K in the chain (51% of the\n'
      "200 V limit of a 1/4 W part). <b>Don't</b> use a larger body: its parasitic "
      'capacitance cuts the scope bandwidth.</p>\n'
      '<p><b>Type:</b> the {n_z} resistors that <b>set the measurement ratio</b> must be '
      '<b>metal film 1%</b> — carbon\n'
      "film's voltage-dependent value and its 1–3% drift over 1000 hours cannot be "
      'calibrated out (§11).\n'
      'For {n_o} resistors metal film is recommended (zero-point and filter stability); '
      'the rest can be standard\n'
      'carbon. The direnc.net packs in stock (blue body, 5 bands) are metal film; the motorobit\n'
      'packs and loose resistors have a beige body, 4 bands = carbon.</p>\n'
      "<table><tr><th>Resistor</th><th>Value</th><th>Power</th><th>Type</th><th>Role</th><th class='s'>Step</th></tr>\n"
      '{satir}</table>'),
    M('seramik disk (mercimek)',
      'ceramic disc'),
    M('TL431 kararlılık kondansatörü (B15: 100nF osilasyon yapıyordu → 1nF); tip fark etmez',
      'TL431 stability capacitor (B15: 100nF oscillated → 1nF); type does not matter'),
    M('multilayer seramik',
      'multilayer ceramic'),
    M('NORMAL kanal RC süzgeci — C3 ile AYNI tip; toleransı V/I eşleşmesine giriyor (B16)',
      'NORMAL channel RC filter — SAME type as C3; its tolerance enters the V/I matching (B16)'),
    M('HV kanal RC süzgeci — C2 ile AYNI tip; toleransı V/I eşleşmesine giriyor (B16)',
      'HV channel RC filter — SAME type as C2; its tolerance enters the V/I matching (B16)'),
    M('şönt Kelvin hattı RC süzgeci; tip fark etmez',
      'shunt Kelvin line RC filter; type does not matter'),
    M('Sallen-Key süzgeç (2×1nF paralel); C0G olsa daha iyi, stokta yok — disk olur',
      'Sallen-Key filter (2×1nF in parallel); C0G would be better, none in stock — disc is fine'),
    M('Sallen-Key süzgeç; disk olur',
      'Sallen-Key filter; disc is fine'),
    M('Sallen-Key süzgeç (2×1nF paralel); disk olur',
      'Sallen-Key filter (2×1nF in parallel); disc is fine'),
    M('U3 (+5V) ayırma — pine yakın',
      'U3 (+5V) decoupling — close to the pin'),
    M('U4 (+5V) ayırma — pine yakın',
      'U4 (+5V) decoupling — close to the pin'),
    M('U5 (+12V) ayırma',
      'U5 (+12V) decoupling'),
    M('U5 (−12V) ayırma',
      'U5 (−12V) decoupling'),
    M('U8 (+12V) ayırma',
      'U8 (+12V) decoupling'),
    M('U8 (−12V) ayırma',
      'U8 (−12V) decoupling'),
    M('ADS rayı (+3V3) ayırma',
      'ADS rail (+3V3) decoupling'),
    M('elektrolitik (KUTUPLU)',
      'electrolytic (POLARISED)'),
    M('7912 giriş kondansatörü — + ucu +12V, − ucu −12V (uzun bacak +)',
      '7912 input capacitor — + to +12V, − to −12V (long lead +)'),
    M('7912 çıkış kondansatörü — + ucu +12V, − ucu GND (uzun bacak +)',
      '7912 output capacitor — + to +12V, − to GND (long lead +)'),
    M('film (polyester)',
      'film (polyester)'),
    M('akım kanalı örtüşme süzgeci (B16), 1 µF film 15 mm bacak — C023 (CBB22 105J400V, '
      'polipropilen ±%5; ölçüldü 15 mm, 4 adet) ya da C022 (damla, ±%10, 1 adet); C021 22.5 mm sığmaz',
      'current channel anti-aliasing filter (B16), 1 µF film, 15 mm lead pitch — C023 '
      '(CBB22 105J400V, polypropylene ±5%; measured 15 mm, 4 pcs) or C022 (dipped, ±10%, 1 '
      'pc); C021 at 22.5 mm does not fit'),
    M('akım kanalı örtüşme süzgeci (B16) — C18/C20 ile paralel, toplam 1.32 µF',
      'current channel anti-aliasing filter (B16) — in parallel with C18/C20, 1.32 µF in total'),
    M('akım kanalı örtüşme süzgeci (B16) — ADS pinine en yakın olan',
      'current channel anti-aliasing filter (B16) — the one closest to the ADS pin'),
    M('\n'
      '<h2 id="kondansatorler">Kondansatörler — tip</h2>\n'
      '<p>Stokta iki çeşit küçük seramik var, ikisi aynı işi görmez:</p>\n'
      '<ul class="is">\n'
      '<li><b>Seramik disk ("mercimek")</b> — yassı, yuvarlak, koyu turuncu/kahverengi '
      'disk; bacakları dümdüz aşağı iner\n'
      '(stokta <b>C049 1nF</b>, 10 adet). Tolerans geniş, değeri sıcaklıkla oynar. '
      'Yalnızca <b>değerinin kritik\n'
      'olmadığı</b> yerlerde: TL431 kararlılık (C1), Kelvin RC (C4), Sallen-Key (C5–C8).</li>\n'
      '<li><b>Multilayer seramik (MLCC)</b> — yumru biçimli, açık sarı/hardal gövde; '
      'bacaklar gövdenin altından\n'
      'birbirine yakın çıkar (stokta <b>C051 100nF 2.5 mm</b>, C008 100nF 5 mm, C052 220nF). Ayırma\n'
      "kondansatörleri ve <b>süzgeçler</b> için: C2/C3'ün ve C19/C20'nin toleransı V/I "
      'eşleşmesine giriyor (B16).</li>\n'
      '<li><b>Film (polyester)</b> — dikdörtgen kutu ya da damla; C18 için 15 mm bacaklı '
      '<b>C022</b>.</li>\n'
      '<li><b>Elektrolitik</b> — silindir, <b>kutuplu</b>: uzun bacak +, gövdedeki şerit − '
      '(C16/C17, C035).</li>\n'
      '</ul>\n'
      '<p class="kucuk">Ayırt etme: diskin iki bacağı gövdenin kenarından çıkar ve gövde '
      'ince bir yassı tablettir;\n'
      "multilayer'ın gövdesi kalın bir yumrudur ve bacaklar altından çıkar. Renk kutudan "
      'kutuya değişebilir —\n'
      "biçime bak. Disk 1nF'lerin bacak aralığı 5 mm olabilir; plan 2.5 mm istiyor, "
      'bacakları bükerek yaklaştır.</p>\n'
      '<table><tr><th>Kondansatör</th><th>Değer</th><th>Tip</th><th>Görevi</th><th '
      "class='s'>Adım</th></tr>\n"
      '{satir}</table>',
      '\n'
      '<h2 id="kondansatorler">Capacitors — type</h2>\n'
      '<p>There are two kinds of small ceramic in stock, and they are not interchangeable:</p>\n'
      '<ul class="is">\n'
      '<li><b>Ceramic disc</b> — flat, round, dark orange/brown disc; the leads come straight down\n'
      '(in stock: <b>C049 1nF</b>, 10 pcs). Wide tolerance, value drifts with temperature. '
      'Only where the <b>value is not\n'
      'critical</b>: TL431 stability (C1), Kelvin RC (C4), Sallen-Key (C5–C8).</li>\n'
      '<li><b>Multilayer ceramic (MLCC)</b> — blob-shaped, light yellow/mustard body; the '
      'leads come out from under the\n'
      'body, close together (in stock: <b>C051 100nF 2.5 mm</b>, C008 100nF 5 mm, C052 '
      '220nF). For decoupling\n'
      'capacitors and <b>filters</b>: the tolerance of C2/C3 and of C19/C20 enters the V/I '
      'matching (B16).</li>\n'
      '<li><b>Film (polyester)</b> — rectangular box or dipped drop; for C18 the 15 mm '
      'pitch <b>C022</b>.</li>\n'
      '<li><b>Electrolytic</b> — cylinder, <b>polarised</b>: long lead +, the stripe on '
      'the body − (C16/C17, C035).</li>\n'
      '</ul>\n'
      '<p class="kucuk">Telling them apart: a disc\'s two leads leave from the edge of the '
      'body and the body is a thin flat tablet;\n'
      "a multilayer's body is a thick blob and the leads come out from underneath. Colours "
      'vary from batch to batch —\n'
      'go by the shape. The 1nF discs may have 5 mm lead spacing; the plan wants 2.5 mm, '
      'so bend the leads closer.</p>\n'
      '<table><tr><th>Capacitor</th><th>Value</th><th>Type</th><th>Role</th><th '
      "class='s'>Step</th></tr>\n"
      '{satir}</table>'),
    M('<h2>J5 → ESP32-S3 kablosu</h2><p><b>ESP32 karta lehimlenmez</b>: kutuda kartın '
      'yanında durur, J5 <b>dişi</b> başlığına 10 adet dişi-erkek jumper kabloyla bağlanır '
      "— dişi uç devkit'in erkek pinine, erkek uç J5'e (Adım 1'de, KAPI'dan önce). J5 pin "
      "sırası şemadan, GPIO numaraları firmware'deki <code>PIN_*</code> sabitlerinden. "
      "<b>Devkit'in 5V pini USB'den beslenir</b>; kart USB'siz çalışmaz (analog +5 V "
      'buradan). İki Type-C soketinden <b>COM yazan</b> doğru olan (CH343 köprüsü).</p>',
      '<h2>J5 → ESP32-S3 cable</h2><p><b>The ESP32 is not soldered to the board</b>: it '
      'sits next to the board in the enclosure and connects to the J5 <b>female</b> header '
      "with 10 female-to-male jumper wires — the female end onto the devkit's male pin, "
      'the male end into J5 (in Step 1, before the GATE). The J5 pin order comes from the '
      'schematic, the GPIO numbers from the <code>PIN_*</code> constants in the firmware. '
      "<b>The devkit's 5V pin is powered from USB</b>; the board does not work without USB "
      '(the analog +5 V comes from here). Of the two Type-C sockets, the one marked '
      '<b>COM</b> is the right one (CH343 bridge).</p>'),
    M("<table><tr><th class='s'>J5</th><th>Ağ</th><th>ESP32-S3 devkit pini</th></tr>",
      "<table><tr><th class='s'>J5</th><th>Net</th><th>ESP32-S3 devkit pin</th></tr>"),
    M("Kart A'yı",
      'board A'),
    M('{kart} hazırla',
      'Prepare {kart}'),
    M('direnç (1/2 W)',
      'resistor (1/2 W)'),
    M('sigorta klipsi',
      'fuse clip'),
    M('elektrolitik kondansatör',
      'electrolytic capacitor'),
    M('regülatör (TO-220)',
      'regulator (TO-220)'),
    M('24V+ (sigorta öncesi)',
      '24V+ (before the fuse)'),
    M('Lehim izleri — ',
      'Solder traces — '),
    M('Yalıtımlı teller ({n})',
      'Insulated wires ({n})'),
    M('Kart dışı bağlantılar — {bas}',
      'Off-board connections — {bas}'),
    M('Kontrol ve KAPI',
      'Check and GATE'),
    M('direnç',
      'resistor'),
    M('entegre soketi',
      'IC socket'),
    M('seramik kondansatör',
      'ceramic capacitor'),
    M('TO-92 parça',
      'TO-92 part'),
    M('J5 başlığı',
      'J5 header'),
    M('{u} {isaret} girişi',
      '{u} {isaret} input'),
    M('{j5} → ESP32-S3 kablosu',
      '{j5} → ESP32-S3 cable'),
    M('ADS modül başlığı',
      'ADS module header'),
    M('dik direnç',
      'upright resistor'),
    M('film kondansatör',
      'film capacitor'),
    M("S− Kelvin (GND'ye değmez)",
      'S− Kelvin (must not touch GND)'),
    M('HV alt düğüm (~1.7 V)',
      'HV bottom node (~1.7 V)'),
    M("Kart B'yi",
      'board B'),
    M('HV girişi',
      'HV input'),
    M('HV düğüm {k}',
      'HV node {k}'),
    M('diyot',
      'diode'),
    M('seramik kondansatör çifti',
      'ceramic capacitor pair'),
    M('kapı',
      'gate'),
    M('baz',
      'base'),
    M('kollektör',
      'collector'),
    M('Besleme: 24 V girisi, sigorta, 7912, ±12 V rayi',
      'Supply: 24 V input, fuse, 7912, ±12 V rails'),
    M('Vref: TL431 + U3A tamponu, J5 basligi (+3V3, +5V)',
      'Vref: TL431 + U3A buffer, J5 header (+3V3, +5V)'),
    M("ESP32 + I²C: iki ADS modulu, pull-up'lar",
      'ESP32 + I²C: two ADS modules, pull-ups'),
    M('Akim kanali: Kelvin uclari, 100R/1K, ortusme suzgeci',
      'Current channel: Kelvin leads, 100R/1K, anti-aliasing filter'),
    M('NORMAL gerilim kanali (±32 V)',
      'NORMAL voltage channel (±32 V)'),
    M('YUKSEK gerilim kanali: B karti + U4',
      'HIGH voltage channel: board B + U4'),
    M('Osiloskop kanali + Sallen-Key (U5A)',
      'Oscilloscope channel + Sallen-Key (U5A)'),
    M('Hizli akim yolu: fark yukselteci U8 + U5B',
      'Fast current path: difference amplifier U8 + U5B'),
    M('Pil testi: kapi surucusu Q2/Q3',
      'Battery test: gate driver Q2/Q3'),
    M('Kart {kart} parça yüzü',
      'Board {kart} component side'),
    M('vida (M3)',
      'screw (M3)'),
    M('katot bandı',
      'cathode band'),
    M('gerginlik deliği — telin yalıtımı buradan geçer, lehimlenmez',
      'strain-relief hole — the wire insulation passes through here, not soldered'),
    M('düz (yazılı) yüz',
      'flat (printed) face'),
    M('metal tab (arka)',
      'metal tab (back)'),
    M('V girişi (J1)',
      'V input (J1)'),
    M('COM jak',
      'COM jack'),
    M("HV alt (B'den)",
      'HV bottom (from B)'),
    M('Skop jak (J4)',
      'Scope jack (J4)'),
    M('S+ (şönt üst)',
      'S+ (shunt top)'),
    M('S− (şönt alt)',
      'S− (shunt bottom)'),
    M('GND yıldız (şönt alt BACAĞI, S− ile aynı nokta)',
      'GND star (shunt bottom LEAD, same point as S−)'),
    M('Q1 kapı',
      'Q1 gate'),
    M('24 V +',
      '24 V +'),
    M('24 V −',
      '24 V −'),
    M('Kart {kart} lehim yüzü',
      'Board {kart} solder side'),
    M('lehim izi',
      'solder trace'),
    M('YALITIMLI TEL',
      'INSULATED WIRE'),
    M('HV jak',
      'HV jack'),
    M('→ A:HV alt',
      '→ A:HV bottom'),
    M('\n'
      '<h2 id="adimadim">Adım adım</h2>\n'
      '<p class="kucuk">Üstteki çizim seçili alt adıma yakınlaşır: o adımın parçaları <b>koyu ve\n'
      'parlak</b>, öncekiler soluk, sonrakiler görünmez. Parça takarken <b>parça yüzü</b>, '
      'iz ve tel\n'
      'çekerken <b>lehim yüzü</b> gösterilir. <b>◀ ▶</b> düğmeleri ya da klavyede ← →; bir kartın\n'
      'başlığına tıklamak da seçer. İmleci bir bacağın ya da izin üstünde tut: ağ ve delik '
      'adı yazar.\n'
      '"Yaptım" işaretleri bu tarayıcıda saklanır.</p>\n'
      '<div class="gorus" id="gorus">\n'
      '  <div class="gorus-ust">\n'
      '    <button id="geri" aria-label="Önceki alt adım">◀</button>\n'
      '    <div class="gorus-bilgi"><span class="ano" id="g-no"></span> <span id="g-baslik"></span>\n'
      '      <span class="rozet" id="g-yuz"></span></div>\n'
      '    <button id="ileri" aria-label="Sonraki alt adım">▶</button>\n'
      '  </div>\n'
      '  <div class="sahne" id="sahne">{figurler}</div>\n'
      '  <div class="gorus-alt">\n'
      '    <div class="adimsec">{dugmeler}</div>\n'
      '    <label class="kucuk"><input type="checkbox" id="g-tum"> tüm plan</label>\n'
      '    <span class="kucuk" id="g-sayac"></span>\n'
      '  </div>\n'
      '  <div class="cubuk"><div id="g-cubuk"></div></div>\n'
      '</div>\n',
      '\n'
      '<h2 id="adimadim">Step by step</h2>\n'
      '<p class="kucuk">The drawing above zooms to the selected sub-step: that step\'s '
      'parts are <b>dark and\n'
      'highlighted</b>, earlier ones faded, later ones hidden. When fitting parts it shows '
      'the <b>component side</b>; when\n'
      'running traces and wires, the <b>solder side</b>. Use the <b>◀ ▶</b> buttons or ← → '
      "on the keyboard; clicking a card's\n"
      'title also selects it. Hover over a lead or a trace to see its net and hole name.\n'
      '"Done" ticks are stored in this browser.</p>\n'
      '<div class="gorus" id="gorus">\n'
      '  <div class="gorus-ust">\n'
      '    <button id="geri" aria-label="Previous sub-step">◀</button>\n'
      '    <div class="gorus-bilgi"><span class="ano" id="g-no"></span> <span id="g-baslik"></span>\n'
      '      <span class="rozet" id="g-yuz"></span></div>\n'
      '    <button id="ileri" aria-label="Next sub-step">▶</button>\n'
      '  </div>\n'
      '  <div class="sahne" id="sahne">{figurler}</div>\n'
      '  <div class="gorus-alt">\n'
      '    <div class="adimsec">{dugmeler}</div>\n'
      '    <label class="kucuk"><input type="checkbox" id="g-tum"> whole plan</label>\n'
      '    <span class="kucuk" id="g-sayac"></span>\n'
      '  </div>\n'
      '  <div class="cubuk"><div id="g-cubuk"></div></div>\n'
      '</div>\n'),
    M('Adım {k} — {ad}',
      'Step {k} — {ad}'),
    M('Delikli plaket — kart {kart}',
      'Perfboard — board {kart}'),
    M('13x23 cm (SRF023) plaketten kesilmis 45x45 delik',
      '45×45 holes cut from a 13x23 cm (SRF023) board'),
    M('5×20 PCB sigorta klipsi (çift)',
      '5×20 PCB fuse clip (pair)'),
    M('{deg} (kart dışı)',
      '{deg} (off-board)'),
    M('Yalıtımlı montaj kablosu',
      'Insulated hook-up wire'),
    M('teller / kart dışı kablolar',
      'wires / off-board cables'),
    M("<tr><th>Ne</th><th class='s'>Adet</th><th>Nereye</th>",
      "<tr><th>What</th><th class='s'>Qty</th><th>Where</th>"),
    M('Bu adım için gerekenler',
      'What you need for this step'),
    M('yaptım',
      'done'),
    M(' ve ',
      ' and '),
    M('altta',
      'at the bottom'),
    M('{n}. sıra',
      'row {n}'),
    M('{ks}×{kr} deliklik plaketten <b>{W}×{H} delik</b> kes: {kes} deliklerinin üstünden '
      'maket bıçağıyla iki yüzden çiz, kır; kenarı zımparala.',
      'From the {ks}×{kr} hole board cut <b>{W}×{H} holes</b>: score along the holes of '
      '{kes} with a utility knife on both sides, snap it off; sand the edge.'),
    M(' <b>Tek kesim</b> — üç kenar fabrika kenarı kalır.',
      ' <b>One cut</b> — the other three edges stay factory edges.'),
    M('Köşelere M3 delik aç (her köşede {n}×{n} delik boş).',
      'Drill M3 holes in the corners (each corner keeps {n}×{n} holes free).'),
    M("Çizimdeki beyaz çizgiler plaketindeki {c}'lik çizgilerin yerinde: A1'den sayınca "
      'ilk dikey çizgi <b>{s1} ile {s2}</b> sütunları, ilk yatay çizgi <b>{c}. ile '
      '{c1}.</b> sıra arasında. Plaketinde öyle değilse dur, söyle.',
      "The white lines in the drawing are where your board's every-{c}-holes lines are: "
      'counting from A1, the first vertical line is between columns <b>{s1} and {s2}</b>, '
      'the first horizontal line between rows <b>{c} and {c1}</b>. If your board differs, '
      'stop and say so.'),
    M('Ped çapını kumpasla ölç: plan <b>{pad} mm</b> varsayıyor; büyük çıkarsa dur, söyle '
      '— denetim yeniden koşsun.',
      'Measure the pad diameter with calipers: the plan assumes <b>{pad} mm</b>; if it is '
      'larger, stop and say so — the check needs to be re-run.'),
    M('Plaketi <b>parça yüzü</b> sana bakacak koy; <b>A1</b> sol üst köşe',
      'Place the board with the <b>component side</b> facing you; <b>A1</b> is the top left corner'),
    M(' (kesilen kenar {kesik} kalsın)',
      ' (keep the cut edge {kesik})'),
    M('. Köşeye kalemle A1 yaz — bundan sonraki her delik adı buna göre.',
      '. Write A1 in that corner with a pen — every hole name from here on is relative to it.'),
    M('Parçaları tablodaki deliklere <b>parça yüzünden</b> tak. Plaketi çevir, bacakları '
      'lehimle, fazlasını kes (izi bacak artığıyla çekeceksen bir iki delik boyu bırak).',
      'Insert the parts into the holes in the table <b>from the component side</b>. Flip '
      'the board, solder the leads, trim the excess (leave a hole pitch or two if you will '
      'run the trace with the lead offcut).'),
    M('Klipsleri <b>sigorta takılıyken</b> oturt (aralık kendiliğinden doğru olur), her '
      'bacağı kısa lehimle (2–3 sn — cam sigorta ısınmasın). Bacak delikleri tabloyla '
      'uymazsa dur, söyle.',
      'Seat the clips <b>with the fuse in them</b> (the spacing comes out right by '
      "itself), solder each lead briefly (2–3 s — don't let the glass fuse heat up). If "
      "the lead holes don't match the table, stop and say so."),
    M('<table><tr><th>Parça</th><th>Değer</th><th>Bacak → delik</th><th>Yön</th></tr>',
      '<table><tr><th>Part</th><th>Value</th><th>Lead → hole</th><th>Orientation</th></tr>'),
    M("7912'nin asgari yükü: 12 V / 1K = 12 mA, 144 mW → 1/2 W (R030). Değer kritik değil; "
      'metal film GEREKMEZ.',
      'Minimum load for the 7912: 12 V / 1K = 12 mA, 144 mW → 1/2 W (R030). The value is '
      'not critical; metal film is NOT required.'),
    M('Plakete lehimlenen: 5×20 sigorta YUVASI (2 klips, FUS009). 50mA, içine takılan cam '
      'sigortanın değeri — 50 mA geldi (FUS010, 2026-09-17); yuvada geçici 400 mA (FUS001) '
      'duruyorsa onunla DEĞİŞTİR.',
      'What gets soldered to the board: the 5×20 fuse HOLDER (2 clips, FUS009). 50mA is '
      'the rating of the glass fuse that goes into it — the 50 mA fuses have arrived '
      '(FUS010, 2026-09-17); if the temporary 400 mA (FUS001) is still in the holder, REPLACE it.'),
    M('<b>Kutuplu:</b> uzun bacak (+) tabloda <b>+</b> yazan deliğe; gövdedeki şerit (−) tarafı.',
      '<b>Polarised:</b> the long lead (+) into the hole marked <b>+</b> in the table; the '
      'stripe on the body is the (−) side.'),
    M('uzun bacak +',
      'long lead +'),
    M('<b>{ref}</b>: önce multimetrenin diyot kademesiyle bacak sırasını doğrula — '
      '<b>{sira}</b> (yazılı yüz sana dönük, bacaklar aşağı, soldan sağa).',
      "<b>{ref}</b>: first check the pin order with the multimeter's diode range — "
      '<b>{sira}</b> (printed face towards you, leads down, left to right).'),
    M("7912'nin <b>tabı −12 V'ta</b>: soğutucuya ya da kutuya vidalama (soğutucu gerekmiyor).",
      "The 7912's <b>tab is at −12 V</b>: do not screw it to a heatsink or the enclosure "
      '(no heatsink is needed).'),
    M('yukarı',
      'up'),
    M('yazılı yüz {yon}, tab arkada',
      'printed face {yon}, tab at the back'),
    M('Plaketi çevir: <b>lehim yüzü</b> (çizim aynalı — aynı harf aynı deliğin üstünde).',
      'Flip the board: <b>solder side</b> (the drawing is mirrored — the same letter is '
      'over the same hole).'),
    M("Yol köşe noktalarıyla verildi: <code>A1 → A5 → C5</code> = A1'den A5'e düz, oradan "
      "C5'e. Komşu pedleri lehimle köprüle; uzun yolda bacak artığı ya da kalaylı tel "
      'yatırıp lehimle.',
      'Each path is given by its corner points: <code>A1 → A5 → C5</code> = straight from '
      'A1 to A5, then on to C5. Bridge neighbouring pads with solder; on long runs lay '
      'down a lead offcut or tinned wire and solder it.'),
    M('Başka renkteki (başka ağdaki) komşu pede lehim taşırma.',
      "Don't let solder spill onto a neighbouring pad of another colour (another net)."),
    M("<table><tr><th>Ağ</th><th>Yol (köşeler)</th><th class='s'>Delik</th></tr>",
      "<table><tr><th>Net</th><th>Path (corners)</th><th class='s'>Holes</th></tr>"),
    M('Yalıtımlı tel, <b>lehim yüzünde</b> uçtan uca; uçları oradaki bacağa ya da pede lehimle.',
      'Insulated wire, end to end <b>on the solder side</b>; solder its ends to the lead '
      'or pad there.'),
    M('Teli plakete yatır, çıplak ucu kısa tut; başka bir pedin üstünden geçirme.',
      'Lay the wire flat on the board, keep the bare ends short; do not route it over another pad.'),
    M("<table><tr><th>Ağ</th><th>Uç 1</th><th>Uç 2</th><th class='s'>Delik</th></tr>",
      "<table><tr><th>Net</th><th>End 1</th><th>End 2</th><th class='s'>Holes</th></tr>"),
    M("öbür ucu XT30'a (siyah, −)",
      'other end to the XT30 (black, −)'),
    M("öbür ucu XT30'a (kırmızı, +)",
      'other end to the XT30 (red, +)'),
    M('<b>Şimdi yap:</b> karta <b>{n} tel</b> lehimle. Teli önce gerginlik deliğinden (boş '
      'halka) geçir, sonra lehim noktasına lehimle; 15–20 cm bırak.',
      '<b>Do now:</b> solder <b>{n} wires</b> to the board. First pass each wire through '
      'its strain-relief hole (the empty ring), then solder it to the solder point; leave 15–20 cm.'),
    M('Lehimden sonra telleri, girdikleri deliğin <b>yanından sıcak silikonla</b> plakete '
      'sabitle: sallanan tel lehimi çatlatır. Silikonu komşu delikleri kapatacak kadar yayma.',
      'After soldering, fix the wires to the board with <b>hot glue right next to</b> the '
      "hole they enter: a wobbling wire cracks the joint. Don't spread the glue so far "
      'that it covers neighbouring holes.'),
    M("Bu teller <b>hemen bağlanır</b>: öbür uçları XT30'un <b>erkek</b> ucuna (dişi uç "
      "güç kaynağının kablosuna) — bu adımın KAPI ölçümü 24 V'u buradan alıyor.",
      'These wires are <b>connected right away</b>: their other ends go to the <b>male</b> '
      "half of the XT30 (the female half goes on the power supply cable) — this step's "
      'GATE measurement takes its 24 V from here.'),
    M('<table><tr><th>Tel</th><th>Geçir</th><th>Lehimle</th><th>Öbür ucu</th></tr>',
      '<table><tr><th>Wire</th><th>Pass through</th><th>Solder at</th><th>Other end</th></tr>'),
    M('<details><summary>Sonra — kutu/panel kurulunca bu teller nereye gidiyor</summary>',
      '<details><summary>Later — where these wires go once the enclosure/panel is built</summary>'),
    M('24 V girişi. Tezgahta: XT30 (CON058) — kart tarafı ERKEK uç (pimli), güç kaynağı '
      'tarafı DİŞİ uç; gerilim taşıyan taraf kapalı soketli olsun. Kablo yalıtımlı, '
      'kırmızı = +, siyah = −. Kutuda (B58): XT30 kesilir, teller iç klemense (KL) — 24 '
      "V'u kutunun kendi pili (MT2) verir, dış besleme yok.",
      '24 V input. On the bench: XT30 (CON058) — the MALE half (pins) on the board side, '
      'the FEMALE half on the power supply side; the live side should be the shrouded '
      'socket. Insulated cable, red = +, black = −. In the enclosure (B58): the XT30 is '
      'cut off and the wires go into the internal terminal block (KL) — 24 V comes from '
      "the enclosure's own battery (MT2), no external supply."),
    M('<table><tr><th>Nereden</th><th>Nereye</th><th>Tür</th><th>Not</th></tr>',
      '<table><tr><th>From</th><th>To</th><th>Type</th><th>Note</th></tr>'),
    M('<b>Bu adımda lehim de kablo da yok</b> — yalnız multimetreyle kontrol. Önce '
      "enerjiyi kes: 24 V bağlıysa çıkar, ESP32'nin USB'sini çıkar.",
      '<b>No soldering and no wiring in this step</b> — only checks with the multimeter. '
      "Power down first: unplug the 24 V if connected, unplug the ESP32's USB."),
    M("<b>{ag}</b> GND'ye kısa değil",
      '<b>{ag}</b> not shorted to GND'),
    M('{r} bacağı · {yer}',
      '{r} lead · {yer}'),
    M('bip <b>ötmemeli</b> (ilk anda kısa bir “cik” olabilir: kondansatör doluyor). Emin '
      "değilsen ohm kademesine al: kısa devre 0–1 Ω'da <b>sabit</b> kalır, kondansatörde "
      'sayı hızla yükselir',
      'beeper <b>stays silent</b> (a short “chirp” at first is possible: the capacitor is '
      'charging). If unsure, switch to the ohms range: a short stays <b>steady</b> at 0–1 '
      'Ω, with a capacitor the reading climbs quickly'),
    M('<table><tr><th>Ne</th><th>Uç 1</th><th>Uç 2</th><th>Doğru sonuç</th></tr>',
      '<table><tr><th>What</th><th>Probe 1</th><th>Probe 2</th><th>Correct result</th></tr>'),
    M('<details><summary>Köprü kontrolü — bu adımda lehimlediğin deliklerin <b>farklı '
      "ağa</b> ait komşuları ({n} çift)</summary><p class='kucuk'>Lehim köprüsü en çok "
      'buralarda olur. Bip kademesinde her çifti ölç; “ötmemeli” yazan öterse aralarında '
      'lehim köprüsü var. Parantezdeki değer, ohm kademesinde aradaki dirençlerden '
      'beklenen okuma (takılı entegre/modül varsa biraz düşük çıkabilir). Ray–ray '
      'çiftlerinde ilk anda kısa bir “cik” normal: kondansatör doluyor; sürekli öterse '
      'köprü.</p><table><tr><th>Delik</th><th>Komşu</th><th>Doğru sonuç</th></tr>',
      '<details><summary>Bridge check — neighbours on a <b>different net</b> of the holes '
      "you soldered in this step ({n} pairs)</summary><p class='kucuk'>This is where "
      'solder bridges usually happen. Measure every pair on the continuity range; if a '
      'pair marked “stays silent” beeps, there is a solder bridge between them. The value '
      'in brackets is the expected reading on the ohms range through the resistors in '
      'between (it may read a little lower with an IC/module fitted). On rail–rail pairs a '
      'short “chirp” at first is normal: the capacitor is charging; a continuous beep '
      'means a bridge.</p><table><tr><th>Hole</th><th>Neighbour</th><th>Correct result</th></tr>'),
    M('bip <b>ötmemeli</b>',
      'beeper <b>stays silent</b>'),
    M('bip <b>ötmemeli</b> (ohm kademesinde ≈ {ohm})',
      'beeper <b>stays silent</b> (≈ {ohm} on the ohms range)'),
    M('Bu adımda çektiğin her izin iki ucu arasında bip <b>ötmeli</b>; yan yana iki farklı '
      'iz/ped arasında <b>ötmemeli</b>.',
      'Every trace you ran in this step must <b>beep</b> end to end; two different '
      'traces/pads side by side must <b>stay silent</b>.'),
    M('Ölçerken iki metal uca birden parmakla dokunma — vücudun yüksek direnç ölçümünü düşürür.',
      "Don't touch both metal probe tips with your fingers while measuring — your body "
      'lowers high-resistance readings.'),
    M('<b>KAPI — geçmeden ilerleme:</b>',
      "<b>GATE — don't proceed until it passes:</b>"),
    M('İlk elektrik — aşağıdaki sırayla.',
      'First power-up — in the order below.'),
    M('Sigorta yuvasında <b>50 mA</b> sigorta olsun (FUS010) — geçici 400 mA değil.',
      'There must be a <b>50 mA</b> fuse in the fuse holder (FUS010) — not the temporary 400 mA.'),
    M('ESP32 bağlı olmasın, ADS modülleri takılı olmasın.',
      'ESP32 not connected, ADS modules not fitted.'),
    M('Kaynak: 24 V güç kaynağının çıkışı <b>doğrudan</b> (düşürücü modül gerekmez). Akım '
      'sınırı yok; korumayı 50 mA sigorta yapıyor — kartın çekeceği ~15 mA.',
      'Source: the output of the 24 V power supply <b>directly</b> (no buck module '
      'needed). No current limit; protection comes from the 50 mA fuse — the board will draw ~15 mA.'),
    M("Takmadan önce XT30'un <b>dişi</b> ucunu ölç: kırmızı prob kırmızı tele, <b>+24 "
      'V</b> görmelisin. Eksi çıkarsa kaynaktaki kabloları yer değiştir.',
      'Before plugging in, measure the <b>female</b> half of the XT30: red probe on the '
      'red wire, you should see <b>+24 V</b>. If it reads negative, swap the wires at the supply.'),
    M("Kaynak <b>kapalıyken</b> XT30'u tak, sonra kaynağı aç; sökerken önce kaynağı kapat. "
      "Enerjili kaynağa takmak (kıvılcım) 136 µF'yi bir anda doldurur ve 50 mA'lik hızlı "
      'sigortayı attırabilir.',
      'Plug in the XT30 with the supply <b>switched off</b>, then switch the supply on; '
      'when disconnecting, switch the supply off first. Hot-plugging into a live supply '
      '(spark) charges the 136 µF all at once and can blow the 50 mA fast fuse.'),
    M("Tak, 5 saniye bekle, çek. 7912, C16, C17 ve R40'a dokun: ısınmamış olmalı (24 V'a "
      'dokunmak tehlikesiz).',
      'Plug in, wait 5 seconds, unplug. Touch the 7912, C16, C17 and R40: none of them '
      'should have warmed up (touching 24 V is harmless).'),
    M('Soketlerde entegre takılıysa <b>çıkar</b> ({refs}) — ilk elektrikte yalnız besleme '
      'bloğu çalışsın.',
      'If ICs are fitted in the sockets, <b>remove</b> them ({refs}) — at first power-up '
      'only the supply block should run.'),
    M('Elektrolitiklerin <b>şeritli (−) bacağı</b> doğru delikte mi: {liste}. Ters takılı '
      'elektrolitik ilk elektrikte ısınır, patlayabilir.',
      "Are the electrolytics' <b>striped (−) leads</b> in the right holes: {liste}. An "
      'electrolytic fitted backwards heats up at first power-up and can burst.'),
    M('Tekrar tak ve ölç — siyah prob <b>{gnd}</b> (GND): kırmızı prob <b>A:{arti}</b> → '
      '<b>+11.5 … +12.5 V</b>; kırmızı prob <b>A:{eksi}</b> → <b>yaklaşık −12 V</b> (−11 … −13).',
      'Plug in again and measure — black probe on <b>{gnd}</b> (GND): red probe on '
      '<b>A:{arti}</b> → <b>+11.5 … +12.5 V</b>; red probe on <b>A:{eksi}</b> → <b>about '
      '−12 V</b> (−11 … −13).'),
    M("Sigortanın iki ucu arasındaki düşümü ölç (A:{d1} ↔ A:{d2}): <b>0.1 V'un "
      'üzerinde</b> olmalı — gerçek 50 mA sigortanın direnci onlarca ohm, kart ~13 mA '
      'çekiyor. Birkaç mV okuyorsan sigortanın teli etiketinden çok kalın (ucuz '
      'sigortalarda olur): kart çalışır ama <b>koruma zayıf</b>, markalı sigorta al.',
      'Measure the drop across the two ends of the fuse (A:{d1} ↔ A:{d2}): it should be '
      '<b>above 0.1 V</b> — a genuine 50 mA fuse has a resistance of tens of ohms and the '
      'board draws ~13 mA. If you read only a few mV, the fuse wire is much thicker than '
      'its rating (happens with cheap fuses): the board works but <b>protection is '
      'weak</b>, buy a branded fuse.'),
    M('Sigorta atarsa, gerilim tutmazsa ya da bir şey ısınırsa: çek, devam etme, ölçtüğünü yaz.',
      'If the fuse blows, the voltage does not hold or something heats up: unplug, do not '
      'continue, write down what you measured.'),
    M(' metal film (önerilir)',
      ' metal film (recommended)'),
    M('1×40 dişi header — 10 pin kes (J5)',
      '1×40 female header — cut 10 pins (J5)'),
    M('DIP-8 entegre soketi',
      'DIP-8 IC socket'),
    M('Soketin çentiği tabloda yazan yöne. Entegreyi lehim bitince, bu adımın KAPI '
      'ölçümünden önce tak (çentik aynı yöne).',
      'Point the socket notch in the direction given in the table. Fit the IC after '
      "soldering is finished, before this step's GATE measurement (notch the same way)."),
    M('aşağı (satır no. artan)',
      'down (row number increasing)'),
    M('çentik {yon}',
      'notch {yon}'),
    M('<b>İki çeşit seramik var:</b> tabloda hangisi disk (mercimek), hangisi multilayer '
      "yazıyor — karıştırma (bkz. <a href='#kondansatorler'>Kondansatörler</a>).",
      '<b>There are two kinds of ceramic:</b> the table says which one is disc and which '
      "is multilayer — don't mix them up (see <a href='#kondansatorler'>Capacitors</a>)."),
    M('düz yüz {yon}',
      'flat face {yon}'),
    M("Şemadaki 'LP' kılıf kodu (TO-92), parça adı değil. Stoktaki parça: gövdede 'WS "
      "TL431A 819SB' = Wing Shing, A sınıfı (±%1; sıfır kalibrasyonu zaten siliyor). Wing "
      'Shing veri sayfası (datasheet/TL431A_WingShing_TO-92.pdf): TO-92 ön yüzden R-A-K — '
      "TI ile AYNI, plan doğru. Yine de lehimlemeden önce 5 V→1K→K, REF=K bağla, K'da 2.5 V okunmalı.",
      "'LP' in the schematic is the package code (TO-92), not the part name. The part in "
      "stock: marked 'WS TL431A 819SB' = Wing Shing, grade A (±1%; zero calibration "
      'removes it anyway). Wing Shing datasheet (datasheet/TL431A_WingShing_TO-92.pdf): '
      'TO-92 seen from the front is R-A-K — SAME as TI, the plan is correct. Still, before '
      'soldering, wire 5 V→1K→K with REF=K: K should read 2.5 V.'),
    M("<b>J5 dişi başlık</b> (erkek DEĞİL): 1×40 dişi header'dan 10'luk parça kes, plakete "
      "lehimle. ESP32'nin pinleri erkek olduğu için kablonun dişi ucu devkit'e, erkek ucu "
      'buraya girer — elindeki dişi-erkek jumper kablolar.',
      '<b>J5 female header</b> (NOT male): cut a 10-pin piece from a 1×40 female header '
      "and solder it to the board. Since the ESP32's pins are male, the cable's female end "
      'goes onto the devkit and its male end in here — the female-to-male jumper wires you have.'),
    M('DİŞİ başlık; jumper kablonun erkek ucu buraya girer',
      'FEMALE header; the male end of the jumper wire goes in here'),
    M('<b>ESP32 bu karta lehimlenmez.</b> Kutuda kartın yanında durur; J5 (dişi) başlığına '
      "10 adet <b>dişi-erkek</b> jumper kabloyla bağlanır: dişi uç devkit'in erkek pinine, "
      "erkek uç J5'e. Bu adımın KAPI ölçümü +3V3 ve +5V'u ESP32'den, bu kablo üzerinden alıyor.",
      '<b>The ESP32 is not soldered to this board.</b> It sits next to the board in the '
      'enclosure and connects to the J5 (female) header with 10 <b>female-to-male</b> '
      "jumper wires: the female end onto the devkit's male pin, the male end into J5. This "
      "step's GATE measurement takes +3V3 and +5V from the ESP32 through this cable."),
    M("Bağlamadan önce ESP32'nin pinlerinde başka tel kalmasın — tezgâh denemelerinden "
      'kalan GPIO4–GPIO5 kısa devre teli ve RC düzeneği dahil.',
      "Before connecting, make sure nothing else is left on the ESP32's pins — including "
      'the GPIO4–GPIO5 short-circuit wire and the RC setup left over from bench tests.'),
    M("Kabloyu tablodaki pin pin eşlemeyle tak; <b>3V3 ile 5V'u karıştırma</b>. Kabloyu "
      'kısa tut: I²C ile iki analog sinyal (skop, hızlı akım) aynı demette gidiyor.',
      "Fit the cable pin by pin as in the table; <b>don't mix up 3V3 and 5V</b>. Keep the "
      'cable short: I²C and two analog signals (scope, fast current) run in the same bundle.'),
    M("USB kablosunu devkit'in <b>COM yazan</b> Type-C soketine tak (CH343 köprüsü). Öteki "
      'soket de port açar ama firmware orada sessiz kalır.',
      "Plug the USB cable into the devkit's Type-C socket <b>marked COM</b> (CH343 "
      'bridge). The other socket also opens a port, but the firmware stays silent there.'),
    M('Kılavuz <b>01 Vref</b> kapısı: TL431 katodu ve U3A çıkışı (U3 soketine LM358 tak).',
      'Guide <b>01 Vref</b> gate: TL431 cathode and U3A output (fit an LM358 into the U3 socket).'),
    M('1×40 dişi header — 10 pin kes',
      '1×40 female header — cut 10 pins'),
    M('<b>Multilayer seramik</b> — yumru biçimli açık sarı gövde; disk (mercimek) değil.',
      '<b>Multilayer ceramic</b> — blob-shaped light yellow body; not a disc.'),
    M('<b>Bu adımda yalnız dişi yuvalar lehimlenir; ADS modülleri lehimlenmez.</b> 1×40 '
      "dişi header'dan 10'luk parçalar kes, plakete lehimle (lehimlerken yuvayı dik tutmak "
      "için modülü ya da bir erkek header'ı geçici takabilirsin).",
      '<b>In this step only the female sockets are soldered; the ADS modules are not '
      'soldered.</b> Cut 10-pin pieces from a 1×40 female header and solder them to the '
      'board (to hold the socket upright while soldering you can temporarily plug in the '
      'module or a male header).'),
    M('Modülleri bu adımın KAPI ölçümünden hemen önce yuvaya tak. Modül plakete <b>paralel '
      '(yatık)</b> durur, gövdesi yuvanın <b>sağına</b> uzanır — plan bu alanı boş '
      'bıraktı. Plan, pinleri modülün <b>lehim yüzünden</b> çıkan (bileşen yüzü yukarı, '
      'yazılar okunur) modül varsayıyor: o zaman üstten alta {sira} sırası tablodaki '
      'deliklerle çakışır. <b>Pinler bileşen yüzüne lehimlenmişse</b> modül gövde-sağda '
      "ancak ters (bileşen yüzü aşağı) takılabilir ve sıra A3…VDD'ye döner — o zaman ya "
      'başlık öbür yüze taşınır ya da plan ters sıraya göre yeniden üretilir; yuvaya öylece takma.',
      "Plug the modules into their sockets just before this step's GATE measurement. The "
      'module lies <b>parallel (flat)</b> to the board, its body extending to the '
      '<b>right</b> of the socket — the plan left that area free. The plan assumes a '
      'module whose pins come out of its <b>solder side</b> (component side up, printing '
      'readable): then, top to bottom, the order {sira} lines up with the holes in the '
      'table. <b>If the pins are soldered to the component side</b>, the module can only '
      'be fitted body-right upside down (component side down) and the order flips to '
      'A3…VDD — then either the header is moved to the other side or the plan is '
      "regenerated for the reversed order; don't just plug it in as is."),
    M('dişi başlık — modül LEHİMLENMEZ, sonra takılır; VDD yazan pini tabloda VDD yazan '
      'deliğe (yuva simetrik, ters takılabilir)',
      'female header — the module is NOT SOLDERED, it is plugged in later; the pin marked '
      'VDD into the hole marked VDD in the table (the socket is symmetric and accepts it backwards)'),
    M('<b>Dik montaj:</b> gövde tabloda <b>1</b> yazan deliğin üstünde durur, diğer bacak '
      "kıvrılıp 2'ye iner.",
      '<b>Upright mounting:</b> the body stands over the hole marked <b>1</b> in the '
      'table, the other lead bends over and comes down into 2.'),
    M("dik: gövde 1'in üstünde",
      'upright: body above 1'),
    M("Kılavuz <b>02</b>: firmware'de <code>#</code> — 0x48 ve 0x49 ikisi de görünmeli.",
      'Guide <b>02</b>: <code>#</code> in the firmware — both 0x48 and 0x49 must show up.'),
    M('öbür ucu <b>şimdilik boş</b>',
      'other end <b>left free for now</b>'),
    M('S+ ve S− tellerini birbirine bur (ince tel yeter).',
      'Twist the S+ and S− wires together (thin wire is enough).'),
    M('Tellerin öbür uçları <b>boş kalır</b>; kutu/panel kurulunca aşağıdaki parçalara bağlanacak.',
      'The other ends of the wires <b>stay free</b>; once the enclosure/panel is built '
      'they connect to the parts below.'),
    M('YÜK born jak çifti (büyük boy, yeşil ×2, panel): J3.1 → yük eksisi, J3.2 → kaynak '
      'eksisi. Jakların iç ucundan şöntün yanındaki bariyer klemense (HB950) kısa kalın '
      'kablo — jak tarafı lehim kulağı ya da iki somun arasında kalaysız halka, bariyer '
      'tarafı kalaysız burulmuş uç (kalay vida altında akar, gevşer; halka pabuç stokta '
      'yok, gerekmez); akım J3.1 → şönt → J3.2 yolunu izler.',
      'LOAD banana jack pair (large, green ×2, panel): J3.1 → load negative, J3.2 → source '
      "negative. From the jacks' inner ends a short thick cable to the barrier terminal "
      'block next to the shunt (HB950) — jack side on a solder lug or an untinned ring '
      'between two nuts, barrier side an untinned twisted end (solder creeps under a screw '
      'and loosens; no ring lugs in stock, none needed); the current follows the J3.1 → '
      'shunt → J3.2 path.'),
    M('Type-C şönt, kutuda 5 mΩ Ø1.6 mm manganin (R042, 9.5 A sürekli) takılı; 15 mΩ Ø1 mm '
      '(R044, 3.4 A, 0.52 mA adım) yedek. R042 veri sayfası: tek parça manganin tel Ø1.6, '
      '10 mm aralık, 10 A; bacaklardaki basık yer = ölçüm noktası, altında 3.5 mm bacak. '
      "Plakete GİRMEZ; bacaklar XP128 10 mm klemense (CON064); yük kabloları XP128'e "
      "girmez, yanındaki bariyer klemenste (HB950) birleşir, XP128'e tek köprü (B55n). "
      'Kelvin telleri bacaklardaki BASIK YERİN kendisine lehimlenir (veri sayfasının ölçüm '
      "noktası; altındaki 3.5 mm bacak klemense girer, vidaya lehim yok); 'RS.2' saydığın "
      'bacağa S−, yıldız GND ve J3.2 gider — tutarlı ol. Isıl sınır tel çapından (B53).',
      'Type-C shunt, the enclosure has a 5 mΩ Ø1.6 mm manganin (R042, 9.5 A continuous) '
      'fitted; 15 mΩ Ø1 mm (R044, 3.4 A, 0.52 mA step) as spare. R042 datasheet: '
      'single-piece manganin wire Ø1.6, 10 mm spacing, 10 A; the flattened spot on each '
      'leg = measuring point, with 3.5 mm of leg below it. NOT on the board; the legs go '
      'into an XP128 10 mm terminal block (CON064); the load cables do not go into the '
      'XP128, they join at the barrier terminal block next to it (HB950), with a single '
      'link to the XP128 (B55n). The Kelvin wires are soldered to the FLATTENED SPOT '
      "itself on the legs (the datasheet's measuring point; the 3.5 mm of leg below it "
      'goes into the terminal block, no solder under the screw); S−, star GND and J3.2 go '
      "to the leg you count as 'RS.2' — be consistent. The thermal limit comes from the "
      'wire gauge (B53).'),
    M('<b>YÜK AKIMI</b> taşıyan kablolar plakete girmez: kutuda, klemensler arasında; '
      'kalın kablo (≥1.5 mm²).',
      'Cables carrying the <b>LOAD CURRENT</b> do not go onto the board: they run in the '
      'enclosure, between terminal blocks; thick cable (≥1.5 mm²).'),
    M("Kelvin telleri (S+, S−) şönt BACAĞINA lehimlenir, klemens vidasına değil — 15 mΩ'da "
      'vida temas direnci bile ölçüme girer.',
      'The Kelvin wires (S+, S−) are soldered to the shunt LEG, not to the terminal screw '
      '— at 15 mΩ even the screw contact resistance enters the measurement.'),
    M('<b>YÜK AKIMI</b>',
      '<b>LOAD CURRENT</b>'),
    M('yuk donusu -> sont ust bacagi',
      'load return -> shunt top leg'),
    M('sont alt bacagi -> kaynak eksisi',
      'shunt bottom leg -> source negative'),
    M('kelvin',
      'kelvin'),
    M('S+ : sont BACAGINA, sikistirma izinin ustunden — klemensten degil',
      'S+ : onto the shunt LEG, above the clamping mark — not from the terminal block'),
    M('S- : ayni sekilde; S+ ile BURULU cift',
      'S- : the same way; TWISTED pair with S+'),
    M('yildiz',
      'star'),
    M('kart topraginin guc yoluna TEK baglantisi — S- ile AYNI noktaya, sont bacagina '
      "(klemens vidasina DEGIL: vida-bacak temas direnci COM'u S-'den I x R kadar kaydirir)",
      "the board ground's SINGLE connection to the power path — at the SAME point as S-, "
      'on the shunt leg (NOT the terminal screw: the screw-to-leg contact resistance '
      'shifts COM from S- by I x R)'),
    M('Kılavuz <b>03 Akım kanalı</b>: <code>Z</code> sıfırı, bilinen akım, ters akım.',
      'Guide <b>03 Current channel</b>: <code>Z</code> zero, known current, reverse current.'),
    M('<b>Enerjili test (KAPI) şimdi değil:</b> {disi} (kutu/panel parçası) gerekiyor, '
      'kutu kurulunca yapılacak — {kapi} Yukarıdaki ölçümler tamamsa <b>sonraki adıma geç</b>.',
      '<b>Powered test (GATE) not now:</b> {disi} (enclosure/panel part) is needed, so it '
      'is done once the enclosure is built — {kapi} If the measurements above are fine, '
      '<b>move on to the next step</b>.'),
    M(' (İstersen jak yerine tel ucuna krokodille geçici bağlayıp şimdi de yapabilirsin.)',
      ' (If you like, you can do it now by clipping a crocodile lead onto the wire end '
      'temporarily instead of the jack.)'),
    M(' metal film %1',
      ' metal film 1%'),
    M('Sinyal telini kendi COM/GND teliyle <b>burabilirsin</b> — zorunlu değil, gürültüye iyi.',
      'You <b>may twist</b> the signal wire with its own COM/GND wire — not required, but '
      'good against noise.'),
    M('V girişi born jak çifti (panel): kırmızı = V girişi, siyah = COM (kart GND).',
      'V input banana jack pair (panel): red = V input, black = COM (board GND).'),
    M('sinyal',
      'signal'),
    M('V girisi (KIRMIZI uc). COM teliyle burulabilir',
      'V input (RED lead). May be twisted with the COM wire'),
    M('COM jak -> kart GND (SIYAH uc)',
      'COM jack -> board GND (BLACK lead)'),
    M('Kılavuz <b>04 NORMAL</b>: <code>z</code>, <code>g&lt;volt&gt;</code>, ters giriş.',
      'Guide <b>04 NORMAL</b>: <code>z</code>, <code>g&lt;volt&gt;</code>, reversed input.'),
    M('5x5 cm (SRF020)',
      '5x5 cm (SRF020)'),
    M('Silikonlu prob kablosu (HV ucu)',
      'Silicone probe cable (HV lead)'),
    M('kart dışı kablo',
      'off-board cable'),
    M('Plaketi ({W}×{H} delik) <b>kesmeden</b> kullan.',
      'Use the board ({W}×{H} holes) <b>uncut</b>.'),
    M(' Köşelere M3 delik aç.',
      ' Drill M3 holes in the corners.'),
    M("Bu kart <b>615 V</b> taşır: parçaları takmadan önce plaketi temizle, sonunda flux'ı "
      'IPA ile sil — lehim kalıntısı kaçak yoludur.',
      'This board carries <b>615 V</b>: clean the board before fitting parts, and at the '
      'end wipe off the flux with IPA — solder residue is a leakage path.'),
    M('Parça yüzünden bakınca sol üst köşeye kalemle <b>B1</b> yaz.',
      'Seen from the component side, write <b>B1</b> in the top left corner with a pen.'),
    M('<b>HV zinciri:</b> gövdeler plakete yaslı; bacak artığını lehimin üstünden kısa kes '
      '— keskin uç ve lehim sivrisi kaçak yolunu kısaltır.',
      '<b>HV chain:</b> bodies flat against the board; trim lead offcuts short just above '
      'the solder — sharp ends and solder spikes shorten the creepage path.'),
    M('tek tel, iki ucu da lehimlenir — <b>{cm} cm</b> kes (kutuda iki kart arası; daha '
      'kısası yetişmez)',
      'one wire, both ends soldered — cut <b>{cm} cm</b> (the distance between the two '
      "boards in the enclosure; shorter won't reach)"),
    M('HV kablosunu silikondan <b>önce</b> öbür telden uzağa yatır — silikon konumu '
      'sabitler. HV kablosunu sağlam yapıştır: en çok çekilecek kablo o.',
      'Lay the HV cable away from the other wire <b>before</b> gluing — the glue fixes the '
      'position. Glue the HV cable firmly: it is the cable that will get pulled the most.'),
    M("Kart B'den kart A'ya giden tel <b>şimdi</b> lehimlenir: <b>{cm} cm</b> (kutuda iki "
      'kartın arası; daha kısası yetişmez).',
      'The wire from board B to board A is soldered <b>now</b>: <b>{cm} cm</b> (the '
      "distance between the two boards in the enclosure; shorter won't reach)."),
    M('HV girişi born jakı (panel): AYRI, işaretli ve kutudaki TEK SARI jak (B60); COM, '
      "J1'in COM'uyla ortak.",
      'HV input banana jack (panel): SEPARATE, labelled, and the ONLY YELLOW jack on the '
      "enclosure (B60); its COM is shared with J1's COM."),
    M('<b>HV kablosu</b>: yalıtımı sağlam, diğer kablolardan ayrı ve uzak.',
      '<b>HV cable</b>: sound insulation, separate from and away from the other cables.'),
    M('sanal',
      'virtual'),
    M('HV COM = ortak COM jaki (ayni fiziksel jak, tel yok)',
      'HV COM = the shared COM jack (same physical jack, no wire)'),
    M('hv',
      'hv'),
    M('HV jak -> B karti. 600 V silikon test kablosu',
      'HV jack -> board B. 600 V silicone test lead'),
    M('HV zinciri: {ilk}–{son} ({n} direnç)',
      'HV chain: {ilk}–{son} ({n} resistors)'),
    M(' + kartlar arası tel',
      ' + inter-board wire'),
    M('{ad} kablosunun boş (soyulmuş) ucu',
      'free (stripped) end of the {ad} cable'),
    M('{ad} lehimi · {yer}',
      '{ad} solder joint · {yer}'),
    M('20 MΩ kademesi. Çok büyük / OL = bir lehim kopuk',
      '20 MΩ range. Very large / OL = a broken joint'),
    M('Kılavuz <b>05 YÜKSEK</b>: <b>önce 12 V</b>, sonra kademeli. Tek el, eller uzakta.',
      'Guide <b>05 HIGH</b>: <b>12 V first</b>, then step up. One hand, hands away.'),
    M('<b>Kutuplu:</b> gövdedeki bant = katot (<b>K</b>) — tabloda K yazan deliğe.',
      '<b>Polarised:</b> the band on the body = cathode (<b>K</b>) — into the hole marked '
      'K in the table.'),
    M('bant = K',
      'band = K'),
    M('İki ayrı 1nF yan yana; paralel bağlantıyı lehim izi yapacak.',
      'Two separate 1nF side by side; a solder trace makes the parallel connection.'),
    M('iki ayrı 1nF, yan yana',
      'two separate 1nF, side by side'),
    M('Skop girişi born jakı (panel); COM ortak.',
      'Scope input banana jack (panel); shared COM.'),
    M('skop COM = ortak COM jaki (ayni fiziksel jak, tel yok)',
      'scope COM = the shared COM jack (same physical jack, no wire)'),
    M('skop girisi',
      'scope input'),
    M('Kılavuz <b>06 Osiloskop</b>: bilinen kare dalga, <code>ta</code>.',
      'Guide <b>06 Oscilloscope</b>: known square wave, <code>ta</code>.'),
    M('Kılavuz <b>07 Hızlı akım yolu</b>: dirençsel yükte <code>w</code> → PF ≈ 1.',
      'Guide <b>07 Fast current path</b>: resistive load, <code>w</code> → PF ≈ 1.'),
    M("Şemadaki sembol BC547'den (C-B-E); numarayla lehimlenirse C ile E yer değiştirir ve "
      'transistör <b>yarı çalışır</b>.',
      'The symbol in the schematic comes from the BC547 (C-B-E); soldered by pin number, C '
      'and E swap and the transistor <b>half works</b>.'),
    M('PİL born jak çifti (büyük boy, mavi ×2, panel): J7.1 → yük direnci, J7.2 → pil '
      "eksisi; J3'ten AYRI — karıştırılırsa kesme çalışmaz.",
      'BATTERY banana jack pair (large, blue ×2, panel): J7.1 → load resistor, J7.2 → '
      'battery negative; SEPARATE from J3 — if they are mixed up, the cutoff does not work.'),
    M('IRFZ44N (Q006), kutuda: kaynağı bariyer klemensin 1. kutbuna (= şöntün RS.1 düğümü, '
      "B55n), savağı J7.1'e (PİL 1), kapısı karta tek telle (T_KAPI). Soğutucusuz 6.55 A'e kadar.",
      'IRFZ44N (Q006), in the enclosure: source to pole 1 of the barrier terminal block (= '
      "the shunt's RS.1 node, B55n), drain to J7.1 (BATTERY 1), gate to the board with a "
      'single wire (T_KAPI). Up to 6.55 A without a heatsink.'),
    M('Q1 kaynagi -> sont ust bacagi',
      'Q1 source -> shunt top leg'),
    M('pil testi yuku -> Q1 savagi',
      'battery test load -> Q1 drain'),
    M('pil eksisi -> sont alt bacagi',
      'battery negative -> shunt bottom leg'),
    M('kapi teli',
      'gate wire'),
    M("Pil testi: Q1 kapısı kart kapalıyken ve RESET'te <b>kapalı</b> kalmalı (tezgâh "
      'listesindeki failsafe kalemi).',
      'Battery test: the Q1 gate must stay <b>off</b> with the board powered down and '
      'during RESET (the failsafe item on the bench list).'),
    M('\n'
      '<h2>Bu plan neyi garanti ediyor, neyi etmiyor</h2>\n'
      '<p>Denetim (<code>uretim/yerlesim3.py</code>) bakır bağlantıyı <b>geometriden</b>\n'
      'yeniden kurup şemanın netlistiyle birebir karşılaştırıyor: açık devre yok, kısa\n'
      'devre yok, her büyük kurulum adımında da. Gövdeler çakışmıyor, bacaklar başka gövdenin\n'
      'altına düşmüyor; Kelvin uçları kartta yalnız, toprak güç yoluna tek noktadan\n'
      'bağlı; 50 V üstü her bakır çifti IEC 60664-1 Tablo F.4 aralığını sağlıyor;\n'
      'ayırma kondansatörleri pinlerine yakın.</p>\n'
      '<p>Alt adım sırası da denetleniyor: her parça, iz, tel ve kablo <b>tam bir</b> alt adımda;\n'
      'hiçbir iz ya da tel, daha sonra takılacak bir parçanın deliğini lehimle doldurmuyor;\n'
      'aynı adımda alçak parçalar yükseklerden önce; ters takılabilen parçalar kendi alt\n'
      'adımında; her büyük adım KAPI kontrolüyle bitiyor.</p>\n'
      '<div class="uy"><b>Garanti etmediği:</b> parça ölçüleri tahmin — sigorta klipsinin\n'
      "bacak aralığı, 68 µF'ın çapı (8 mm varsayıldı), film C18'in bacak aralığı\n"
      '(15 mm). Parça yükseklikleri de yaklaşık (yalnız sıralama için). Tezgâhta parçayı\n'
      'plakete oturtup delikleri kontrol et; uymayan olursa söyle, plan yeniden üretilsin.\n'
      'Bakırın <b>kalitesi</b> (soğuk lehim, köprü) ancak multimetreyle sınanır.</div>\n',
      '\n'
      "<h2>What this plan guarantees, and what it doesn't</h2>\n"
      '<p>The check (<code>uretim/yerlesim3.py</code>) rebuilds the copper connectivity '
      '<b>from the geometry</b>\n'
      'and compares it one-to-one with the schematic netlist: no opens, no shorts,\n'
      "at every main assembly step as well. Bodies don't overlap, no lead lands under another\n"
      'body; the Kelvin leads are alone on the board, ground joins the power path at a single\n'
      'point; every copper pair above 50 V meets the IEC 60664-1 Table F.4 spacing;\n'
      'decoupling capacitors are close to their pins.</p>\n'
      '<p>The sub-step order is checked too: every part, trace, wire and cable is in '
      '<b>exactly one</b> sub-step;\n'
      'no trace or wire fills with solder a hole a later part still needs;\n'
      'within a step, low parts come before tall ones; parts that can go in backwards get their own\n'
      'sub-step; every main step ends with a GATE check.</p>\n'
      '<div class="uy"><b>What it doesn\'t guarantee:</b> part dimensions are estimates — '
      "the fuse clip's\n"
      "lead spacing, the 68 µF's diameter (8 mm assumed), film C18's lead pitch\n"
      '(15 mm). Part heights are approximate too (used only for ordering). On the bench, '
      'seat each part\n'
      "on the board and check the holes; if something doesn't fit, say so and the plan "
      'will be regenerated.\n'
      'The <b>quality</b> of the copper (cold joints, bridges) can only be tested with a '
      'multimeter.</div>\n'),
    M("'Kart B · '",
      "'Board B · '"),
    M("'Kart A · '",
      "'Board A · '"),
    M("'lehim yüzü'",
      "'solder side'"),
    M("'parça yüzü'",
      "'component side'"),
    M("' · yapılan '",
      "' · done '"),
    M('Başla',
      'Start'),
    M('Ne yapabilir',
      'What it can do'),
    M('Ölçümler',
      'Measurements'),
    M('Pil testi',
      'Battery test'),
    M('Bağlanma',
      'Connecting'),
    M('PC uygulaması',
      'PC app'),
    M('Malzemeler',
      'Parts'),
    M('Kurulum',
      'Assembly'),
    M('Yerleşim',
      'Layout'),
    M('Kutu',
      'Enclosure'),
    M('Mühendislik',
      'Engineering'),
    M('Yerleşim planı — Ölçüm Kartı',
      'Layout plan — Measurement Board'),
    M('\n'
      '<h1>Yerleşim planı</h1>\n'
      '<p class="alt">Delikli plakette hangi parça hangi deliğe, hangi tel nereden nereye —\n'
      'adım adım, LEGO kılavuzu sırasıyla.</p>\n',
      '\n'
      '<h1>Layout plan</h1>\n'
      '<p class="alt">Which part goes in which hole of the perfboard, which wire runs from '
      'where to where —\n'
      'step by step, in LEGO-instructions order.</p>\n'),
    M('\n'
      '<p class="kucuk" style="margin-top:60px;border-top:1px solid var(--cizgi);padding-top:14px">\n'
      'Bu sayfa <code>uretim/yerlesim3.py</code> tarafından, denetim geçtikten sonra üretildi.\n'
      "Delik adları <code>yerlesim3_veri.py</code> ve <code>yerlesim3_teller.json</code>'dan,\n"
      "alt adım sırası <code>yerlesim3_adim.py</code>'den geliyor, elle yazılmıyor.</p>\n",
      '\n'
      '<p class="kucuk" style="margin-top:60px;border-top:1px solid var(--cizgi);padding-top:14px">\n'
      'This page was generated by <code>uretim/yerlesim3.py</code> after the check passed.\n'
      'Hole names come from <code>yerlesim3_veri.py</code> and <code>yerlesim3_teller.json</code>,\n'
      'the sub-step order from <code>yerlesim3_adim.py</code> — nothing is written by hand.</p>\n'),
    M('besleme',
      'supply'),
    M('yuk',
      'load'),
    M('24 V arti — tezgahta XT30 (kodlu: ters takilamaz); kutuda ic klemens KL.+ (B58)',
      '24 V positive — XT30 on the bench (keyed: cannot be plugged in backwards); internal '
      'terminal block KL.+ in the enclosure (B58)'),
    M('24 V eksi = -12 V rayi',
      '24 V negative = -12 V rail'),
    M('zincir alt dugumu (~1.7 V, Thevenin 8.2K). 22 cm kes — kutuda iki kartin arasi bu '
      'kadar (kutu.py kart konumlarindan hesapliyor), daha kisasi YETMEZ; gereksiz uzatma '
      "da. GND ile BURMA (B'de GND yok). HV kablosundan ve 24 V hattindan uzak gecir",
      'chain bottom node (~1.7 V, Thevenin 8.2K). Cut 22 cm — that is the distance between '
      'the two boards in the enclosure (calculated from the board positions in kutu.py); '
      "shorter does NOT reach; don't make it needlessly long either. Do NOT twist with GND "
      '(there is no GND on B). Route it away from the HV cable and the 24 V line'),
    M('emiter',
      'emitter'),
    M('sağa',
      'right'),
    M('sola',
      'left'),
    M('<b>öter — normal</b> (aralarında ≈ {ohm})',
      '<b>beeps — normal</b> (≈ {ohm} between them)'),
    M('<th>Stokta (kayıt · kutu)</th>',
      '<th>In stock (record · box)</th>'),
    M('{n}. sütun',
      'column {n}'),
    M('kayıtta yok',
      'not in records'),
    M('yeri kayıtta yok',
      'location not recorded'),
    M('bu tipte kayıtta yok',
      'none of this type in records'),
    M('sağda',
      'on the right'),
    M('<b>Disk (mercimek) seramik</b> — yassı turuncu disk; multilayer değil. Bacak '
      "aralığı 5 mm ise 2.5 mm'ye bük.",
      '<b>Ceramic disc</b> — flat orange disc; not a multilayer. If the lead spacing is 5 '
      'mm, bend it to 2.5 mm.'),
    M('<b>Şimdi karta lehimlenecek bir şey yok</b>; aşağısı kutu kurulunca yapılacak bağlantılar.',
      '<b>Nothing to solder to the board now</b>; what follows are connections made once '
      'the enclosure is built.'),
    # semanin deger alanina yazilmis aciklamalar (netlist3.net; deger_adi())
    M('24V girisi', '24V input'),
    M('ADS1115 #1 akim', 'ADS1115 #1 current'),
    M('ADS1115 #2 gerilim', 'ADS1115 #2 voltage'),
    M('Pil testi yuk donusu', 'Battery test load return'),
    M('Skop girisi', 'Scope input'),
    M('V girisi +-32V', 'V input +-32V'),
    M('Yuk donusu', 'Load return'),
]

EN = {m["tr"]: m["en"] for m in CEVIRI}
# Ayni Turkce anahtar iki kez yazilirsa biri sessizce ezilir: denetim sayar.
CIFT = len(CEVIRI) - len(EN)
