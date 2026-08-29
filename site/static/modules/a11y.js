// a11y.js — 键盘可达性
export function initA11y({onZoom, onFocusClear, onSearchFocus}){
  document.addEventListener('keydown',e=>{
    // 不在输入框时响应
    const tag=(document.activeElement?.tagName||'').toLowerCase();
    const inInput = tag==='input' || tag==='textarea';
    if(inInput && e.key!=='Escape') return;
    if(e.key==='+'||e.key==='='){ e.preventDefault(); onZoom && onZoom(1.25); }
    if(e.key==='-'||e.key==='_'){ e.preventDefault(); onZoom && onZoom(0.8); }
    if(e.key==='0' && (e.ctrlKey||e.metaKey)){ e.preventDefault(); onZoom && onZoom('reset'); }
    if(e.key==='Escape'){ onFocusClear && onFocusClear(); }
    if(e.key==='/' && !inInput){ e.preventDefault(); onSearchFocus && onSearchFocus(); }
    if(e.key==='ArrowLeft'){ document.getElementById('wrap').scrollBy({left:-120, behavior:'smooth'}); }
    if(e.key==='ArrowRight'){ document.getElementById('wrap').scrollBy({left:120, behavior:'smooth'}); }
  });
  // roving tabindex for rows
  const inner=document.getElementById('inner');
  if(inner){
    inner.addEventListener('keydown',e=>{
      if(e.key==='Enter'){
        const r=e.target.closest('.p-row');
        if(r) r.querySelector('.p-label')?.click();
      }
    });
  }
}
