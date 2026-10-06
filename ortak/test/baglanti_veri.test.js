// ortak/src/baglanti_veri.js — ÜRETİLEN veri (uretim/baglanti.py); içeriğin doğruluğu orada
// (BG1–BG12, kutu_veri ile). Burada: paneli besleyen YAPI ve v-html güvenliği.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { BAGLANTI } from '../src/baglanti_veri.js';

const kalemler = () => Object.values(BAGLANTI.ekranlar).flat();

test('her ekran (canli, pil, skop) için en az bir kalem; kimlikler benzersiz', () => {
  for (const e of ['canli', 'pil', 'skop']) assert.ok(BAGLANTI.ekranlar[e].length >= 1, e);
  const k = kalemler().map((x) => x.kimlik);
  assert.equal(new Set(k).size, k.length);
});

test('her kalem iki dilde: başlık, SVG, satırlar (aynı sayıda); uyarı varsa iki dilde', () => {
  for (const k of kalemler()) {
    for (const d of ['tr', 'en']) {
      assert.ok(k.baslik[d], `${k.kimlik} baslik ${d}`);
      assert.match(k.svg[d], new RegExp(`^<svg [^>]*data-sema="${k.kimlik}"`), `${k.kimlik} svg ${d}`);
      assert.ok(k.satirlar[d].length >= 1);
      if (k.uyari) assert.ok(k.uyari[d]);
    }
    assert.equal(k.satirlar.tr.length, k.satirlar.en.length, k.kimlik);
  }
});

test('v-html güvenli: script / olay özniteliği / javascript: yok; metinde yalnız <b> ve <code>', () => {
  for (const k of kalemler()) {
    const hepsi = [k.svg.tr, k.svg.en, ...k.satirlar.tr, ...k.satirlar.en, ...(k.uyari ? [k.uyari.tr, k.uyari.en] : [])];
    for (const t of hepsi) {
      assert.doesNotMatch(t, /<script|\son[a-z]+\s*=|javascript:|<foreignObject/i, k.kimlik);
    }
    for (const t of [...k.satirlar.tr, ...k.satirlar.en, ...(k.uyari ? [k.uyari.tr, k.uyari.en] : [])]) {
      const etiket = [...t.matchAll(/<\/?([a-zA-Z]+)/g)].map((m) => m[1]);
      assert.ok(etiket.every((e) => e === 'b' || e === 'code'), `${k.kimlik}: ${etiket}`);
    }
  }
});

test('kullanılan jaklar resimde parlak (data-kul="1"), en az biri; HV kalemi menzil 1', () => {
  for (const k of kalemler()) assert.ok(/data-kul="1"/.test(k.svg.tr), k.kimlik);
  const hv = kalemler().filter((k) => k.menzil === 1);
  assert.deepEqual(hv.map((k) => k.kimlik), ['hv']);
  assert.match(hv[0].svg.tr, /<g data-jak="J2\.1" data-kul="1"/);
});

test('pencere yazıları iki dilde', () => {
  for (const a of ['pencere', 'kapat', 'uyari']) assert.ok(BAGLANTI.yazi[a].tr && BAGLANTI.yazi[a].en, a);
});
