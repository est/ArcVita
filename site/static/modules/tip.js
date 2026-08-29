let tipEl=null;
export function initTip(){
  tipEl=document.getElementById('tip');
  if(!tipEl){ const d=document.createElement('div'); d.id='tip'; d.className='tip'; document.body.appendChild(d); tipEl=d; }
}
export function showTip(html, x, y){
  if(!tipEl) initTip();
  tipEl.innerHTML=html;
  tipEl.style.display='block';
  // flip if overflow
  const pad=12;
  let lx=x+pad, ty=y-8;
  const vw=window.innerWidth, vh=window.innerHeight;
  // measure after set
  const r=tipEl.getBoundingClientRect();
  if(lx+r.width+8>vw) lx=x-r.width-pad;
  if(ty+r.height+8>vh) ty=y-r.height-12;
  if(ty<0) ty=8;
  tipEl.style.left=lx+'px'; tipEl.style.top=ty+'px';
}
export function hideTip(){ if(tipEl) tipEl.style.display='none'; }
export function escapeHtml(s){ return (s||'').replace(/[&<>"]/g,c=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;' }[c])); }
