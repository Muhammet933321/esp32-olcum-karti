'use strict';
// ZINCIR IZ KANCASI (node) — sitecustomize.py'nin node karsiligi.
//
// `zincir_onbellek.izli_ortam()` NODE_OPTIONS'a `--require <bu dosya>` koyar;
// `OLCUM_ZINCIR_IZ` yoksa HICBIR SEY yapmaz. node --test'in actigi alt node
// surecleri ortami miras aldigi icin onlar da kendi dosyalarini yazar.
//
// Kaydedilen: fs uzerinden okunan/yazilan/listelenen/yoklanan yollar, ES modul
// + CommonJS yuklemeleri (module.registerHooks — ikisi de buradan gecer) ve
// child_process ile acilan surecler. Her YENI kayit islemden ONCE diske yazilir
// (oldurulen surec kayit kaybetmez).
const IZ = process.env.OLCUM_ZINCIR_IZ;
if (IZ) {
  const fs = require('fs');
  const path = require('path');
  const mod = require('module');
  const { fileURLToPath } = require('url');
  const asil = {
    openSync: fs.openSync, writeSync: fs.writeSync, existsSync: fs.existsSync,
  };
  const fd = asil.openSync(path.join(IZ, `node-${process.pid}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}.jsonl`), 'a');
  const gorulen = new Set();
  let ic = false;
  const yaz = (t, p, e) => {
    const k = t + '\u0000' + p;
    if (gorulen.has(k)) return;
    gorulen.add(k);
    const s = { t, p };
    if (e !== undefined) s.e = e;
    asil.writeSync(fd, JSON.stringify(s) + '\n');
  };
  const yol = (p) => {
    try {
      if (p === undefined || p === null || typeof p === 'number') return null;
      if (p instanceof URL) p = fileURLToPath(p);
      else if (Buffer.isBuffer(p)) p = p.toString();
      else if (typeof p === 'string' && p.startsWith('file:')) p = fileURLToPath(p);
      if (typeof p !== 'string' || !p) return null;
      return path.resolve(p);
    } catch { return null; }
  };
  const kayit = (t, p, e) => {
    if (ic) return;
    ic = true;
    try { const y = yol(p); if (y) yaz(t, y, e); } catch (h) { try { yaz('kanca_hata', String(h)); } catch {} } finally { ic = false; }
  };
  const yazmaKipi = (b) => {
    if (b === undefined || b === null) return false;
    if (typeof b === 'number') return (b & (fs.constants.O_WRONLY | fs.constants.O_RDWR | fs.constants.O_APPEND | fs.constants.O_CREAT | fs.constants.O_TRUNC)) !== 0;
    return /[wax+]/.test(String(b));
  };
  const OKU = ['readFileSync', 'readFile', 'createReadStream', 'readlinkSync', 'readlink', 'realpathSync', 'realpath'];
  const YAZ = ['writeFileSync', 'writeFile', 'appendFileSync', 'appendFile', 'createWriteStream', 'mkdirSync', 'mkdir',
    'rmSync', 'rm', 'rmdirSync', 'rmdir', 'unlinkSync', 'unlink', 'truncateSync', 'truncate', 'mkdtempSync', 'mkdtemp'];
  const LISTE = ['readdirSync', 'readdir', 'opendirSync', 'opendir'];
  const YOKLA = ['existsSync', 'statSync', 'stat', 'lstatSync', 'lstat', 'accessSync', 'access'];
  const IKILI = ['renameSync', 'rename', 'copyFileSync', 'copyFile', 'cpSync', 'cp', 'symlinkSync', 'symlink', 'linkSync', 'link'];
  const sar = (nesne, ad, fn) => {
    const o = nesne[ad];
    if (typeof o !== 'function') return;
    const yeni = function (...a) { try { fn(a); } catch {} return o.apply(this, a); };
    Object.defineProperties(yeni, Object.getOwnPropertyDescriptors(o));
    nesne[ad] = yeni;
  };
  const varMi = (p) => { try { return asil.existsSync(p); } catch { return false; } };
  const kur = (nesne) => {
    for (const ad of OKU) sar(nesne, ad, (a) => kayit('oku', a[0]));
    for (const ad of YAZ) sar(nesne, ad, (a) => kayit('yaz', a[0]));
    for (const ad of LISTE) sar(nesne, ad, (a) => kayit('liste', a[0]));
    for (const ad of YOKLA) sar(nesne, ad, (a) => { const y = yol(a[0]); if (y) kayit('yokla', y, varMi(y)); });
    for (const ad of ['openSync', 'open']) sar(nesne, ad, (a) => kayit(yazmaKipi(a[1]) ? 'yaz' : 'oku', a[0]));
    for (const ad of IKILI) {
      sar(nesne, ad, (a) => {
        kayit(ad.startsWith('copyFile') || ad.startsWith('cp') ? 'oku' : 'yaz', a[0]);
        kayit('yaz', a[1]);
        if (ad.startsWith('cp')) kayit('liste', a[0]);
      });
    }
  };
  kur(fs);
  kur(fs.promises);
  // fs.promises.open(path, flags) ve FileHandle — kur() 'open'i kapsiyor.
  const cp = require('child_process');
  for (const ad of ['spawn', 'spawnSync', 'execFile', 'execFileSync', 'exec', 'execSync', 'fork']) {
    sar(cp, ad, (a) => {
      if (ic) return;
      const komut = ad.startsWith('exec') && !ad.startsWith('execFile') ? String(a[0]) : [String(a[0]), ...(Array.isArray(a[1]) ? a[1].map(String) : [])];
      const sec = (Array.isArray(a[1]) ? a[2] : a[1]) || {};
      const ortam = sec && typeof sec === 'object' ? sec.env : undefined;
      yaz('surec', JSON.stringify({
        exe: ad === 'fork' ? process.execPath : null,
        komut: ad === 'fork' ? [process.execPath, ...komut] : komut,
        cwd: yol(sec.cwd || process.cwd()),
        iz: !ortam || 'OLCUM_ZINCIR_IZ' in ortam,
        kabuk: ad === 'exec' || ad === 'execSync' || !!sec.shell,
      }));
    });
  }
  if (typeof mod.syncBuiltinESMExports === 'function') mod.syncBuiltinESMExports();
  if (typeof mod.registerHooks === 'function') {
    mod.registerHooks({
      load(url, ctx, sonraki) {
        // 'yukle' ayri tur: Node 24'te ESM kaynagi fs.readFileSync'ten de geciyor (o da
        // kaydediliyor) ama bu ic ayrinti; yukleyici kancasi ondan BAGIMSIZ kanit.
        if (typeof url === 'string' && url.startsWith('file:')) kayit('yukle', url);
        return sonraki(url, ctx);
      },
    });
  } else {
    yaz('diger', 'module.registerHooks yok — ES modul yuklemeleri gorulemez');
  }
  yaz('bas', JSON.stringify({ argv: process.argv, exe: process.execPath, cwd: process.cwd() }));
  process.on('exit', () => {
    ic = true;
    try {
      for (const f of Object.keys(require.cache)) yaz('mod', f);
      if (process.argv[1]) { const y = yol(process.argv[1]); if (y) yaz('oku', y); }
      yaz('son', '');
    } catch {}
  });
}
