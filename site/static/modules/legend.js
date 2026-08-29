// legend.js — 名场面图例
import { FilterState, toggleType } from './filters.js';

const HL_LABELS = ['王表','战役','典故','名场面','转折','决策','成语','代表作','制度','名言','发明','至暗时刻','朝代更替','社会变革','文化','远航','演讲','奖项'];

function colorFor(type){
  // 读 CSS 变量
  const v = getComputedStyle(document.documentElement).getPropertyValue(`--c-${type}`)?.trim();
  if(v) return v;
  // fallback map
  const fb={ '王表':'#c71585','战役':'#8b0000','典故':'#b8860b','转折':'#6b4226','决策':'#2e8b57','朝代更替':'#dc143c' };
  return fb[type]||'#6b4226';
}

export function renderLegend(highlights, onChange){
  const el=document.getElementById('legend');
  if(!el) return;
  // count
  const counts=new Map();
  for(const h of highlights){ const t=h.highlight_type||'其他'; counts.set(t,(counts.get(t)||0)+1); }
  // sort by count desc
  const entries=[...counts.entries()].sort((a,b)=>b[1]-a[1]);
  // limit to 14 to keep one line
  const top=entries.slice(0,14);
  let html=`<span class="lg-title">图例</span>`;
  for(const [t,c] of top){
    const active = FilterState.types.has(t);
    const col=colorFor(t);
    html+=`<button class="legend-chip ${active?'active':''}" data-type="${t}" aria-pressed="${active}"><i style="background:${col}"></i>${t} ${c}</button>`;
  }
  html+=`<button class="legend-chip" id="lgClear" style="border-style:dashed">清除</button>`;
  el.innerHTML=html;
  el.querySelectorAll('.legend-chip[data-type]').forEach(b=>{
    b.addEventListener('click',()=>{
      const t=b.dataset.type;
      toggleType(t);
      b.classList.toggle('active');
      b.setAttribute('aria-pressed', FilterState.types.has(t)+'');
      onChange && onChange();
    });
  });
  el.querySelector('#lgClear')?.addEventListener('click',()=>{
    FilterState.types.clear();
    el.querySelectorAll('.legend-chip').forEach(x=>x.classList.remove('active'));
    onChange && onChange();
  });
}
