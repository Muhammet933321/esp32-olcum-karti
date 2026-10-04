import { readFileSync, writeFileSync, rmSync, mkdtempSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
const [,, KAYNAK, EDGE, SHOT] = process.argv;
const BURASI = import.meta.dirname;
const BETIK = `<script>(function(){
const f=+new URLSearchParams(location.search).get('f')||100;document.documentElement.style.fontSize=f+'%';if(new URLSearchParams(location.search).get('m'))document.documentElement.style.setProperty('--mono','"Courier New",monospace');
const cik=[];const ad=e=>e.tagName.toLowerCase()+(e.className&&e.className.baseVal===undefined?'.'+String(e.className).trim().replace(/ +/g,'.'):'')+':'+(e.textContent||'').trim().slice(0,14);
document.querySelectorAll('.telefon').forEach((t,i)=>{
 const fr=t.getBoundingClientRect(),s={i,et:t.getAttribute('aria-label'),w:fr.width,h:fr.height,kucuk:[],saran:[],tasan:[],kirpik:[],cakisan:[],durdur:null,dikey:0,enkucuk:999};
 const bs=[...t.querySelectorAll('button')];
 bs.forEach(b=>{const r=b.getBoundingClientRect();s.enkucuk=Math.min(s.enkucuk,r.width,r.height);if(r.width<47.99||r.height<47.99)s.kucuk.push(ad(b)+' '+r.width.toFixed(1)+'x'+r.height.toFixed(1));});
 const icr=t.querySelector('.icerik').getBoundingClientRect();const kr=b=>{const r=b.getBoundingClientRect();if(!b.closest('.icerik'))return r;return{left:r.left,right:r.right,top:Math.max(r.top,icr.top),bottom:Math.min(r.bottom,icr.bottom)}};
 for(let a=0;a<bs.length;a++)for(let b=a+1;b<bs.length;b++){const p=kr(bs[a]),q=kr(bs[b]);if(p.bottom<=p.top||q.bottom<=q.top)continue;if(p.left<q.right-.5&&q.left<p.right-.5&&p.top<q.bottom-.5&&q.top<p.bottom-.5)s.cakisan.push(ad(bs[a])+' & '+ad(bs[b]));}
 const d=t.querySelector('.durdur'),dr=d.getBoundingClientRect();const tepe=document.elementFromPoint(dr.left+dr.width/2,dr.top+dr.height/2);
 s.durdur={w:+dr.width.toFixed(1),h:+dr.height.toFixed(1),ustte:!!tepe&&(tepe===d||d.contains(tepe)),cerceveIci:dr.top>=fr.top&&dr.bottom<=fr.bottom&&dr.left>=fr.left&&dr.right<=fr.right};
 const ic=t.querySelector('.icerik');s.dikey=ic.scrollHeight-ic.clientHeight;
 t.querySelectorAll('*').forEach(e=>{if(e.closest('svg'))return;const r=e.getBoundingClientRect();
  if(r.right>fr.right+.5||r.left<fr.left-.5)s.tasan.push(ad(e));
  if(e.scrollWidth>e.clientWidth+1&&e!==ic)s.kirpik.push(ad(e)+' '+e.scrollWidth+'>'+e.clientWidth);
  if((e.tagName==='B'||e.tagName==='TD'||e.tagName==='BUTTON'||e.tagName==='H2')&&e.children.length<3){const cs=getComputedStyle(e),lh=parseFloat(cs.lineHeight)||parseFloat(cs.fontSize)*1.3;const ih=e.tagName==='BUTTON'?0:r.height;if(ih>lh*1.7)s.saran.push(ad(e));}
  const p=e.parentElement;if(p&&p!==ic&&p!==t&&!ic.contains(e)===false){const pr=p.getBoundingClientRect();if(r.right>pr.right+1||r.bottom>pr.bottom+1||r.left<pr.left-1||r.top<pr.top-1)s.tasan.push('ebeveynden: '+ad(e));}
  });
 // kardeş üst üste binmesi (içerik akışı)
 [...ic.children].forEach((c,k,a)=>{if(k&&a[k-1].getBoundingClientRect().bottom>c.getBoundingClientRect().top+.5)s.cakisan.push('akış: '+ad(a[k-1])+' & '+ad(c));});
 cik.push(s);});
document.documentElement.innerHTML='<body><pre id="sonuc">'+JSON.stringify(cik).replace(/</g,'&lt;')+'</pre></body>';})();</script>`;
const html = readFileSync(KAYNAK, 'utf8');
const gecici = join(BURASI, 'gecici.html');
const prof = mkdtempSync(join(BURASI, 'prof-'));
const ortak = ['--headless=new', '--disable-gpu', '--no-first-run', '--disable-sync', '--disable-extensions', '--disable-background-networking', `--user-data-dir=${prof}`, '--window-size=1400,2000', '--virtual-time-budget=2000'];
try {
  for (const [f, m] of [[100, ''], [130, ''], [100, '1'], [130, '1']]) {
    writeFileSync(gecici, html.replace('</body>', BETIK + '</body>'));
    const dom = execFileSync(EDGE, [...ortak, '--dump-dom', pathToFileURL(gecici).href + '?f=' + f + (m ? '&m=1' : '')], { encoding: 'utf8', timeout: 60000, stdio: ['ignore', 'pipe', 'ignore'] });
    const es = dom.match(/<pre id="sonuc">([\s\S]*?)<\/pre>/);
    const veri = JSON.parse(es[1].replace(/&lt;/g, '<').replace(/&amp;/g, '&').replace(/&gt;/g, '>'));
    for (const s of veri) { const temiz = !s.kucuk.length && !s.tasan.length && !s.kirpik.length && !s.cakisan.length && !s.saran.length && s.durdur.ustte && s.durdur.cerceveIci && s.durdur.h >= 56; if (temiz) { console.log(f + '%' + (m ? ' 0.6em' : ''), s.et, 'TEMİZ enküçük', s.enkucuk.toFixed(1), 'durdur', s.durdur.w + 'x' + s.durdur.h, 'dikey kaydırma', s.dikey); continue; } console.log(f + '%' + (m ? ' 0.6em' : ''), JSON.stringify(s)); }
    if (SHOT && !m) {
      writeFileSync(gecici, html.replace('<html lang="tr">', `<html lang="tr" style="font-size:${f}%">`));
      execFileSync(EDGE, [...ortak, `--screenshot=${SHOT}-${f}.png`, pathToFileURL(gecici).href], { timeout: 60000, stdio: 'ignore' });
    }
  }
} finally { try { rmSync(prof, { recursive: true, force: true }); rmSync(gecici, { force: true }); } catch {} }
