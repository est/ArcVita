// filters.js — role / era / century / highlight_type / search 联合过滤
import { parseYear } from './data.js';

export const FilterState = {
  role: null,        // 模范|教训|null
  era: null,         // era 字符串
  century: null,     // ck like bce0400
  types: new Set(),  // highlight_type set
  q: ''              // search query lower
};

export function setRole(r){ FilterState.role = r; }
export function setEra(e){ FilterState.era = e; }
export function setCentury(ck){ FilterState.century = ck; }
export function setQuery(q){ FilterState.q = (q||'').trim().toLowerCase(); }
export function toggleType(t){
  if(FilterState.types.has(t)) FilterState.types.delete(t);
  else FilterState.types.add(t);
  return FilterState.types.has(t);
}
export function clearFilters(){
  FilterState.role=null; FilterState.era=null; FilterState.century=null; FilterState.types.clear(); FilterState.q='';
}

function personMatchesSearch(p, q){
  if(!q) return true;
  const hay = [
    p.name_zh, p.archetype, p.era, p.lesson, p.summary_first_person, p.summary_zh,
    ...(p.endeavors||[]).map(e=>e.title_zh),
    ...(p.events||[]).map(e=>e.title_zh)
  ].join(' ').toLowerCase();
  return hay.includes(q);
}

export function visibleHighlightTypes(persons){
  const s=new Set();
  for(const p of persons) for(const e of (p.events||[])) if(e.is_highlight && e.highlight_type) s.add(e.highlight_type);
  return s;
}

export function applyFilters(persons, opts={}){
  // opts: {timelineEvents可选}
  return persons.filter(p=>{
    if(FilterState.role && p.role!==FilterState.role) return false;
    if(FilterState.era && p.era!==FilterState.era) return false;
    if(FilterState.century && p.century!==FilterState.century) return false;
    if(!personMatchesSearch(p, FilterState.q)) return false;
    // type filter: 如果选中 types，则至少有一个匹配类型的 highlight 才显示
    if(FilterState.types.size){
      const has = (p.events||[]).some(e=> e.is_highlight && FilterState.types.has(e.highlight_type));
      if(!has) return false;
    }
    return true;
  }).sort((a,b)=>{
    const ya=parseYear(a.birth_date)||9999, yb=parseYear(b.birth_date)||9999;
    return ya-yb;
  });
}

// 给legend用的计数
export function countByType(highlights){
  const m=new Map();
  for(const h of highlights){ const t=h.highlight_type||'其他'; m.set(t,(m.get(t)||0)+1); }
  return [...m.entries()].sort((a,b)=>b[1]-a[1]);
}
