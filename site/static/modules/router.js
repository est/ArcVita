// router.js — URL hash 同步
import { FilterState } from './filters.js';
import { focusedQid } from './focus.js';

export function parseHash(){
  const h=location.hash.replace(/^#/,'');
  const p=new URLSearchParams(h);
  return {
    focus: p.get('focus')||null,
    century: p.get('century')||null,
    zoom: p.get('zoom')? parseFloat(p.get('zoom')): null,
    x: p.get('x')? parseInt(p.get('x'),10): null,
    q: p.get('q')||'',
    role: p.get('role')||'',
    types: p.get('types')? p.get('types').split(',').filter(Boolean): []
  };
}

let writeTimer=null;
export function writeHash(state){
  // state: {focus, century, zoom, x, q, role, types}
  clearTimeout(writeTimer);
  writeTimer=setTimeout(()=>{
    const p=new URLSearchParams();
    if(state.focus) p.set('focus', state.focus);
    if(state.century) p.set('century', state.century);
    if(state.zoom) p.set('zoom', String(state.zoom.toFixed(2)));
    if(state.x!=null) p.set('x', String(state.x));
    if(state.q) p.set('q', state.q);
    if(state.role) p.set('role', state.role);
    if(state.types && state.types.length) p.set('types', state.types.join(','));
    const s=p.toString();
    const next = s? '#'+s : '#';
    if(location.hash!==next) history.replaceState(null,'', next || location.pathname);
  }, 300);
}
