// search.js — 输入防抖 + 轻量索引
import { FilterState, setQuery } from './filters.js';

let timer=null;
export function initSearch(onSearch){
  const inp=document.getElementById('q');
  if(!inp) return;
  inp.addEventListener('input',()=>{
    clearTimeout(timer);
    timer=setTimeout(()=>{
      setQuery(inp.value);
      onSearch && onSearch();
      // 脉冲高亮
      pulseResults(inp.value);
    }, 180);
  });
  inp.addEventListener('keydown',e=>{
    if(e.key==='Enter'){
      clearTimeout(timer);
      setQuery(inp.value);
      onSearch && onSearch(true);
    }
    if(e.key==='Escape'){ inp.value=''; setQuery(''); onSearch && onSearch(); }
  });
}

function pulseResults(q){
  if(!q) return;
  const kw=q.trim().toLowerCase();
  if(!kw) return;
  document.querySelectorAll('.p-row').forEach(r=>{
    const name=r.querySelector('.p-name')?.textContent?.toLowerCase()||'';
    if(name.includes(kw)){
      r.style.outline='2px solid var(--gold)';
      setTimeout(()=> r.style.outline='', 1200);
    }
  });
}
export function focusSearchInput(){
  document.getElementById('q')?.focus();
}
