import { loadAll, parseYear, ageAt } from './modules/data.js';
import { computeDomain, stepFor, ticks } from './modules/scale.js';
import { initTip, showTip, hideTip, escapeHtml } from './modules/tip.js';
import { initMinimap } from './modules/minimap.js';

let DATA={ persons:[], events:[], highlights:[], index:null };
let filtered=[];
let zoom=1, focusedQid=null;
let filters={ role:null, era:null, dilemma:null, hl:null, q:'' };
let minY=-600, maxY=2000;
let minimap=null;
const BASE_PX=10;
const LABEL_W=160;
const ROW_N=52, ROW_F=148;
const HL_COLORS={'成语':'var(--c-成语)','代表作':'var(--c-代表作)','战役':'var(--c-战役)','决策':'var(--c-决策)','名言':'var(--c-名言)','发明':'var(--c-发明)','制度':'var(--c-制度)','演讲':'var(--c-演讲)','奖项':'var(--c-奖项)','远航':'var(--c-远航)','王表':'var(--c-王表)','朝代更替':'var(--c-朝代更替)','社会变革':'var(--c-社会变革)','文化':'var(--c-文化)','至暗时刻':'var(--c-至暗时刻)'};

function readHash(){
  const h=new URLSearchParams(location.hash.slice(1));
  focusedQid=h.get('focus')||null;
  const z=parseFloat(h.get('z')||'');
  if(!isNaN(z)) zoom=Math.max(0.15,Math.min(40,z));
  const q=h.get('q'); if(q!=null) filters.q=q;
  const role=h.get('role'); if(role) filters.role=role;
}
function writeHash(){
  const h=new URLSearchParams();
  if(focusedQid) h.set('focus',focusedQid);
  if(Math.abs(zoom-1)>0.01) h.set('z', String(Math.round(zoom*10)/10));
  if(filters.q) h.set('q', filters.q);
  if(filters.role) h.set('role', filters.role);
  if(filters.era) h.set('era', filters.era);
  if(filters.dilemma) h.set('dilemma', filters.dilemma);
  if(filters.hl) h.set('hl', filters.hl);
  const s=h.toString();
  history.replaceState(null,'', s?'#'+s: location.pathname+location.search);
}

async function init(){
  try{
    readHash();
    DATA=await loadAll();
    document.getElementById('stats').textContent=`${DATA.persons.length}人物 · ${DATA.events.length}事件 · ${DATA.highlights.length}名场面`;
    buildFilterUI();
    initTip();
    setupInteractions();
    // minimap
    const cv=document.getElementById('minimap');
    if(cv){ cv.width=cv.clientWidth*2; cv.height=48*2; cv.style.width=cv.clientWidth+'px'; cv.style.height='48px'; minimap=initMinimap(cv, DATA.persons, parseYear, (a,b)=>{ minY=a; maxY=b; zoom= Math.max(0.15, (maxY-minY)*BASE_PX / (document.getElementById('wrap').clientWidth-160) ); render(); }); }
    // search from hash
    const qInput=document.getElementById('q');
    if(qInput){ qInput.value=filters.q||''; qInput.addEventListener('input', debounce(e=>{ filters.q=e.target.value.trim(); applyFilter(); },200)); }
    applyFilter();
    window.addEventListener('hashchange', ()=>{ readHash(); applyFilter(); });
  }catch(e){
    const el=document.getElementById('stats'); if(el) el.textContent='加载失败: '+e.message;
    console.error(e);
  }
}

function uniq(arr){ return [...new Set(arr.filter(Boolean))]; }

function buildFilterUI(){
  const wrap=document.getElementById('filters');
  if(!wrap) return;
  const roles=uniq(DATA.persons.map(p=>p.role));
  const eras=uniq(DATA.persons.map(p=>p.era)).slice(0,12);
  const dilemmas=uniq(DATA.persons.flatMap(p=>p.dilemmas||[])).slice(0,16);
  const hls=uniq(DATA.highlights.map(h=>h.highlight_type)).slice(0,12);
  function pills(label, key, values){
    let h=`<span class=\"flabel\">${label}</span>`;
    h+=`<button class=\"fb ${!filters[key]?'active':''}\" data-k=\"${key}\" data-v=\"\">全部</button>`;
    values.forEach(v=>{ h+=`<button class=\"fb ${filters[key]===v?'active':''}\" data-k=\"${key}\" data-v=\"${escapeHtml(v)}\">${escapeHtml(v)}</button>`; });
    return `<div class=\"fpills\" data-group=\"${key}\">${h}</div>`;
  }
  wrap.innerHTML = pills('角色','role',roles) + pills('朝代','era',eras) + pills('境遇','dilemma',dilemmas) + pills('名场面','hl',hls);
  wrap.querySelectorAll('.fb').forEach(b=>{
    b.addEventListener('click', ()=>{
      const k=b.dataset.k, v=b.dataset.v;
      filters[k]=v||null;
      wrap.querySelectorAll(`[data-group=\"${k}\"] .fb`).forEach(x=>x.classList.toggle('active', x===b));
      writeHash(); applyFilter();
    });
  });
  // century chips
  const cc=document.getElementById('centuryChips');
  if(cc && DATA.index){
    cc.innerHTML=Object.entries(DATA.index.centuries).sort((a,b)=>a[0].localeCompare(b[0])).map(([ck,info])=>{
      return `<button class=\"chip\" data-ck=\"${ck}\">${escapeHtml(info.label)}<span class=\"cnt\">${info.count}</span></button>`;
    }).join('');
    cc.querySelectorAll('.chip').forEach(c=>{
      c.addEventListener('click', ()=>{
        const ck=c.dataset.ck;
        // estimate center year of century
        let y=0;
        if(ck.startsWith('bce')) y=-parseInt(ck.slice(3));
        else if(ck.startsWith('ce')) y=parseInt(ck.slice(2));
        else y=0;
        zoom=1.2;
        // jump domain centered at y
        const span= 400/zoom;
        minY=y-span/2; maxY=y+span/2;
        render();
      });
    });
  }
}

function personMatches(p){
  if(filters.role && p.role!==filters.role) return false;
  if(filters.era && p.era!==filters.era) return false;
  if(filters.dilemma && !(p.dilemmas||[]).includes(filters.dilemma)) return false;
  if(filters.hl){
    const has = (p.highlights||[]).some(h=>h.highlight_type===filters.hl) || DATA.highlights.some(h=>h.person_qid===p.qid && h.highlight_type===filters.hl);
    if(!has) return false;
  }
  if(filters.q){
    const q=filters.q.toLowerCase();
    const hay=[p.name_zh, p.name_en, p.archetype, p.era, ...(p.dilemmas||[])].join(' ').toLowerCase();
    if(!hay.includes(q)) return false;
  }
  return true;
}

function applyFilter(){
  filtered=DATA.persons.filter(personMatches);
  // keep sorted by birth
  filtered.sort((a,b)=>(parseYear(a.birth_date)||9999)-(parseYear(b.birth_date)||9999));
  // if focused person filtered out, keep it but dim others? keep focus but show it
  writeHash();
  render();
}

function setupInteractions(){
  const wrap=document.getElementById('wrap');
  // zoom with anchor
  wrap.addEventListener('wheel', e=>{
    if(e.ctrlKey||e.metaKey){
      e.preventDefault();
      const rect=wrap.getBoundingClientRect();
      const cursorX=e.clientX-rect.left;
      const anchorPct=(cursorX- LABEL_W)/(wrap.clientWidth-LABEL_W);
      const span=maxY-minY;
      const anchorY=minY+span*anchorPct;
      const factor=e.deltaY<0?1.18:0.85;
      const newZoom=Math.max(0.15,Math.min(40, zoom*factor));
      const newSpan=span*(zoom/newZoom);
      // keep anchorY at same cursor pct
      minY=anchorY - newSpan*anchorPct;
      maxY=minY+newSpan;
      zoom=newZoom;
      render();
    }
  }, {passive:false});
  document.getElementById('zoomIn')?.addEventListener('click', ()=>{ zoom=Math.min(40, zoom*1.35); render(); writeHash(); });
  document.getElementById('zoomOut')?.addEventListener('click', ()=>{ zoom=Math.max(0.15, zoom*0.74); render(); writeHash(); });
  document.getElementById('zoomReset')?.addEventListener('click', ()=>{ zoom=1; focusedQid=null; writeHash(); applyFilter(); });
  // drag to scroll
  let dragging=false, sx, sl;
  wrap.addEventListener('mousedown', e=>{ dragging=true; sx=e.pageX-wrap.offsetLeft; sl=wrap.scrollLeft; });
  wrap.addEventListener('mouseleave', ()=>dragging=false);
  wrap.addEventListener('mouseup', ()=>dragging=false);
  wrap.addEventListener('mousemove', e=>{ if(!dragging) return; e.preventDefault(); wrap.scrollLeft=sl-(e.pageX-wrap.offsetLeft-sx)*1.2; });
  // keyboard
  document.addEventListener('keydown', e=>{
    if(e.key==='Escape'){ if(focusedQid){ focusedQid=null; writeHash(); applyFilter(); } else closeDetail(); }
    if(e.key==='/' && !e.ctrlKey && !e.metaKey){ const q=document.getElementById('q'); if(q){ e.preventDefault(); q.focus(); } }
    if(e.key==='+'){ zoom=Math.min(40, zoom*1.25); render(); }
    if(e.key==='-'){ zoom=Math.max(0.15, zoom*0.8); render(); }
  });
  document.getElementById('clearSearch')?.addEventListener('click', ()=>{ filters.q=''; const q=document.getElementById('q'); if(q) q.value=''; applyFilter(); });
}

function clusterEvents(events, parseYear, minY, maxY, W){
  // group events whose x within 6px and not highlight
  const span=maxY-minY||100;
  const withX=events.map(ev=>{ const y=parseYear(ev.date); const x=y==null?null: 80+(y-minY)/span*(W-160); return {...ev, _x:x, _y:y}; }).filter(e=>e._x!=null).sort((a,b)=>a._x-b._x);
  const out=[];
  let i=0;
  while(i<withX.length){
    const base=withX[i];
    if(base.is_highlight || base.highlight_type){ out.push(base); i++; continue; }
    const cluster=[base];
    let j=i+1;
    while(j<withX.length && withX[j]._x - base._x < 12 && !withX[j].is_highlight){
      cluster.push(withX[j]); j++;
    }
    if(cluster.length>1){
      const avgX=cluster.reduce((s,c)=>s+c._x,0)/cluster.length;
      out.push({ _cluster:true, _x:avgX, _count:cluster.length, _members:cluster, date:cluster[0].date, title_zh:`+${cluster.length}`, is_highlight:false });
      i=j;
    }else{ out.push(base); i++; }
  }
  return out;
}

function render(){
  const inner=document.getElementById('inner');
  if(!inner) return;
  // compute domain
  const [dMin, dMax]=computeDomain(DATA.persons, DATA.events, DATA.highlights, focusedQid, parseYear);
  if(!focusedQid){ // when not focused, allow minY/maxY from zoom but keep centered
    // if user has manually jumped via minimap/chips, respect minY/maxY else use domain
    // we keep minY/maxY synced to zoom domain unless user jumped
    // simple: if zoom changed via wheel, we already set minY/maxY; if not, set to domain with zoom scaling
    const span=dMax-dMin||100;
    const ppx=zoom*BASE_PX;
    const desiredSpan= (inner.parentElement?.clientWidth ? (inner.parentElement.clientWidth-160)/ppx : span);
    if(Math.abs((maxY-minY)-desiredSpan)>50 || filtered.length===DATA.persons.length){
      const cx=(dMin+dMax)/2;
      minY=cx - desiredSpan/2; maxY=cx+desiredSpan/2;
    }
  }else{
    minY=dMin; maxY=dMax;
  }
  const span=maxY-minY||100;
  const ppx=zoom*BASE_PX;
  const W=Math.max(900, span*ppx+160+80);
  const step=stepFor(span, ppx);
  const tickArr=ticks(minY,maxY,step,W,span);

  // build axis
  let axisHtml=`<div class=\"axis-row\" style=\"width:${W}px\">`;
  tickArr.forEach(t=>{ axisHtml+=`<div class=\"tick\" style=\"left:${t.x}px\"><span class=\"tl\">${t.label}</span><div class=\"line\"></div></div>`; });
  axisHtml+=`</div>`;

  // build rows via DocumentFragment
  const frag=document.createDocumentFragment();
  const tmp=document.createElement('div');
  tmp.innerHTML=axisHtml;
  while(tmp.firstChild) frag.appendChild(tmp.firstChild);

  let totalHeight=32;
  const byMap=new Map(DATA.persons.map(p=>[p.qid, parseYear(p.birth_date)]));
  // filtered already
  const rowsToRender= focusedQid ? filtered.filter(p=>p.qid===focusedQid || true) : filtered; // keep all for dim mode

  const edColors={'军事/政治':'#8b4513','政治/军事':'#8b4513','政治':'#2e8b57','军事':'#8b0000','科学':'#4169e1','文化':'#8b4513','文化/政治':'#6b4226','航海/外交':'#2e8b57','艺术/科学':'#9370db','商业/技术':'#daa520','思想':'#8b0000'};

  for(const p of rowsToRender){
    const by=parseYear(p.birth_date), dy=parseYear(p.death_date);
    if(by==null) continue;
    const endY=dy??by+60;
    const isFocused=focusedQid===p.qid;
    const isDim=focusedQid && !isFocused;
    const RH=isFocused?ROW_F:ROW_N;
    totalHeight+=RH;
    const x1=80+(by-minY)/span*(W-160);
    const x2=80+(endY-minY)/span*(W-160);
    const roleClass=p.role||'中性';
    // cluster events
    const pEvents=DATA.events.filter(e=>e.person_qid===p.qid);
    const clustered=clusterEvents(pEvents, parseYear, minY, maxY, W);

    let trackInner=`<div class=\"lifespan\" style=\"left:${x1}px;width:${Math.max(4,x2-x1)}px\"></div>`;

    if(isFocused && p.endeavors?.length){
      p.endeavors.forEach((ed,ei)=>{
        const sy=parseYear(ed.start_date), ey=parseYear(ed.end_date);
        if(sy==null||ey==null) return;
        const ex1=80+(sy-minY)/span*(W-160), ex2=80+(ey-minY)/span*(W-160);
        const color=edColors[ed.domain]||'var(--accent)';
        const barTop=14+ei*38;
        trackInner+=`<div class=\"ed-bar\" style=\"left:${ex1}px;width:${Math.max(14,ex2-ex1)}px;top:${barTop}px;background:${color}\"></div>`;
        trackInner+=`<div class=\"ed-title\" style=\"left:${ex1+6}px;top:${barTop+3}px;color:${color}\">${escapeHtml(ed.title_zh)}</div>`;
        trackInner+=`<div class=\"ed-range\" style=\"left:${ex2+6}px;top:${barTop+6}px\">${escapeHtml(ed.start_date||'?')}→${escapeHtml(ed.end_date||'?')}</div>`;
        if(ed.phases) ed.phases.forEach((ph,pi)=>{
          const psy=parseYear(ph.start_date)||sy, pey=parseYear(ph.end_date)||ey;
          const px1=80+(psy-minY)/span*(W-160), px2=80+(pey-minY)/span*(W-160);
          trackInner+=`<div class=\"phase\" style=\"left:${px1}px;width:${Math.max(3,px2-px1)}px;top:${barTop+20+pi*4}px;background:${color}\"></div>`;
          if(px2-px1>36) trackInner+=`<div class=\"phase-label\" style=\"left:${px1+2}px;top:${barTop+9+pi*4}px;color:${color}\">${escapeHtml(ph.name)}</div>`;
          if(ph.highlight && px2-px1>76) trackInner+=`<div class=\"phase-hl\" style=\"left:${(px1+px2)/2}px;top:${barTop-6}px\">${escapeHtml(ph.highlight)}</div>`;
        });
      });
      // events onto bars: place near bar
      clustered.forEach(ev=>{
        const ey=parseYear(ev.date); if(ey==null) return;
        const ex=ev._x;
        const age=ageAt(by,ey);
        const cls=ev._cluster?'cluster': ev.is_highlight?'highlight': ev.event_type==='出生'?'birth':ev.event_type==='逝世'?'death':'normal';
        const w = ev.is_highlight?12:8;
        trackInner+=`<div class=\"ev-dot ${cls}\" style=\"left:${ex}px;top:34px;width:${w}px;height:${w}px\" data-qid=\"${p.qid}\" data-date=\"${escapeHtml(ev.date||'')}\" data-title=\"${escapeHtml(ev.title_zh||ev._count? ev._members?.map(m=>m.title_zh).join(' · '):'')}\" data-place=\"${escapeHtml(ev.place_name||ev.place||'')}\" data-desc=\"${escapeHtml(ev.description||ev.description_zh||'')}\" data-hl=\"${escapeHtml(ev.highlight_note||'')}\" data-age=\"${age??''}\" data-type=\"${escapeHtml(ev.highlight_type||ev.event_type||'')}\" data-cluster=\"${ev._cluster?1:0}\"></div>`;
        if(!ev._cluster && ev.title_zh){ trackInner+=`<div class=\"ev-title focus\" style=\"left:${ex+8}px;top:30px\">${escapeHtml(ev.title_zh)}</div>`; trackInner+=`<div class=\"ev-sub\" style=\"left:${ex+8}px;top:42px\">${escapeHtml(ev.date||'')} ${age!=null?age+'岁':''} ${escapeHtml(ev.place_name||ev.place||'')}</div>`; }
        if(ev._cluster){ trackInner+=`<div class=\"cluster-badge\" style=\"left:${ex}px;top:30px\">${ev._count}</div>`; }
      });
    }else{
      clustered.forEach(ev=>{
        const ey=parseYear(ev.date); if(ey==null) return;
        const ex=ev._x; const age=ageAt(by,ey);
        const cls=ev._cluster?'cluster': ev.is_highlight?'highlight': ev.event_type==='出生'?'birth':ev.event_type==='逝世'?'death':'normal';
        trackInner+=`<div class=\"ev-dot ${cls}\" style=\"left:${ex}px\" data-qid=\"${p.qid}\" data-date=\"${escapeHtml(ev.date||'')}\" data-title=\"${escapeHtml(ev.title_zh||'')}\" data-place=\"${escapeHtml(ev.place_name||ev.place||'')}\" data-desc=\"${escapeHtml(ev.description||ev.description_zh||'')}\" data-hl=\"${escapeHtml(ev.highlight_note||'')}\" data-age=\"${age??''}\" data-type=\"${escapeHtml(ev.highlight_type||ev.event_type||'')}\" data-cluster=\"${ev._cluster?1:0}\"></div>`;
        if((ev.is_highlight||ev.event_type==='出生'||ev.event_type==='逝世') && ev.title_zh && !ev._cluster){
          trackInner+=`<div class=\"ev-title\" style=\"left:${ex}px\">${escapeHtml(ev.title_zh)}</div>`;
          if(ev.is_highlight) trackInner+=`<div class=\"ev-age\" style=\"left:${ex}px\">${age!=null?age+'岁':''}</div>`;
        }
        if(ev._cluster) trackInner+=`<div class=\"cluster-badge\" style=\"left:${ex}px\">${ev._count}</div>`;
      });
    }

    const row=document.createElement('div');
    row.className='p-row'+(isFocused?' focused':'')+(isDim?' dim':'');
    row.dataset.qid=p.qid;
    row.style.height=RH+'px';
    row.innerHTML=`<div class=\"p-label\" data-qid=\"${p.qid}\"><span class=\"dot ${roleClass}\"></span><span class=\"p-name\">${escapeHtml(p.name_zh)}</span><span class=\"p-age\" id=\"age-${p.qid}\"></span><span class=\"arch\">${escapeHtml(p.archetype||'')}</span><span class=\"ed-count\">${p.endeavors?.length? (isFocused?'▾':'▸')+p.endeavors.length+'事':''}</span></div><div class=\"p-track\" style=\"width:${W-LABEL_W}px\">${trackInner}</div>`;
    frag.appendChild(row);
  }

  inner.replaceChildren(frag);
  inner.style.width=W+'px';
  inner.style.height=totalHeight+'px';

  const zEl=document.getElementById('zoomLevel');
  if(zEl){
    if(focusedQid){ const fp=DATA.persons.find(p=>p.qid===focusedQid); zEl.textContent=`聚焦 ${fp?.name_zh||''}`; zEl.style.color='var(--accent)'; }
    else{ zEl.textContent=`${zoom.toFixed(1)}x · ${Math.round(maxY-minY)}年`; zEl.style.color='var(--mist)'; }
  }
  if(minimap) minimap.draw(Math.min(...DATA.persons.map(p=>parseYear(p.birth_date)).filter(v=>v!=null))-50, Math.max(...DATA.persons.map(p=>parseYear(p.death_date)).filter(v=>v!=null))+50, minY, maxY);

  // bind row focus
  inner.querySelectorAll('.p-label').forEach(el=>{
    el.addEventListener('click', ()=>{ const qid=el.dataset.qid; focusedQid= focusedQid===qid?null:qid; writeHash(); render(); });
  });

  // delegated hover with rAF throttling
  let raf=null, lastTarget=null;
  inner.addEventListener('mouseover', e=>{
    const dot=e.target.closest('.ev-dot');
    if(!dot){ hideTip(); clearAges(); return; }
    lastTarget=dot;
    if(raf) cancelAnimationFrame(raf);
    raf=requestAnimationFrame(()=>{
      const d=lastTarget; if(!d) return;
      showDotTip(d);
      syncAges(d);
    });
  });
  inner.addEventListener('mousemove', e=>{
    const dot=e.target.closest('.ev-dot');
    if(dot && dot!==lastTarget){
      lastTarget=dot;
      if(raf) cancelAnimationFrame(raf);
      raf=requestAnimationFrame(()=>{ showDotTip(dot); syncAges(dot); });
    }
    if(lastTarget) showTip(document.getElementById('tip').innerHTML, e.clientX, e.clientY);
  });
  inner.addEventListener('mouseout', e=>{
    const to=e.relatedTarget;
    if(!to || !inner.contains(to)){ hideTip(); clearAges(); }
  });
  // click dot -> detail
  inner.addEventListener('click', e=>{
    const dot=e.target.closest('.ev-dot');
    if(dot && dot.dataset.cluster!=='1'){
      const qid=dot.dataset.qid;
      const p=DATA.persons.find(x=>x.qid===qid);
      if(p) showDetail(p, dot.dataset.date);
      e.stopPropagation();
    }
  });
}

function showDotTip(d){
  let t=`<div class=\"t-name\">${escapeHtml(d.dataset.title)}</div><div class=\"t-date\">${escapeHtml(d.dataset.date)}${d.dataset.age? ' · '+escapeHtml(d.dataset.age)+'岁':''}</div>`;
  if(d.dataset.place) t+=`<div class=\"t-place\">📍 ${escapeHtml(d.dataset.place)}</div>`;
  if(d.dataset.hl) t+=`<div class=\"t-hl\">★ ${escapeHtml(d.dataset.hl)}</div>`;
  else if(d.dataset.desc) t+=`<div class=\"t-desc\">${escapeHtml(d.dataset.desc)}</div>`;
  if(d.dataset.type) t+=`<div class=\"t-type\" style=\"margin-top:4px\"><span class=\"hl-tag\" style=\"background:${HL_COLORS[d.dataset.type]||'var(--gold)'}\">${escapeHtml(d.dataset.type)}</span></div>`;
  if(d.dataset.cluster==='1') t+=`<div class=\"t-desc\">聚合 ${d.dataset.title}</div>`;
  const tip=document.getElementById('tip'); if(tip) tip.innerHTML=t;
}

function syncAges(dot){
  const y=parseYear(dot.dataset.date);
  if(y==null) return;
  filtered.forEach(p=>{
    const by=parseYear(p.birth_date), dy=parseYear(p.death_date);
    const el=document.getElementById(`age-${p.qid}`);
    if(!el) return;
    if(by==null){ el.textContent=''; el.style.display='none'; return; }
    const alive= dy==null || y<=dy;
    const age=ageAt(by,y);
    if(age==null || !alive || age<-80){ el.textContent=''; el.style.display='none'; return; }
    const isMe=p.qid===dot.dataset.qid;
    el.textContent= age<0? `${Math.abs(age)}前生` : `${age}岁`;
    el.style.display='inline';
    el.style.color=isMe?'var(--accent)':'var(--mist)';
    el.style.fontWeight=isMe?'700':'400';
  });
}
function clearAges(){ filtered.forEach(p=>{ const el=document.getElementById(`age-${p.qid}`); if(el){ el.textContent=''; el.style.display='none'; } }); }

function showDetail(p, dateHint){
  const el=document.getElementById('dc');
  if(!el) return;
  let h=`<div class=\"detail-head\"><h3>${escapeHtml(p.name_zh)} <span class=\"arch\">${escapeHtml(p.archetype||'')}</span></h3><div class=\"detail-meta\">${escapeHtml(p.era||'') } · ${escapeHtml(p.birth_date||'?')} → ${escapeHtml(p.death_date||'?')} · ${escapeHtml(p.birth_place||'')}</div>`;
  if(p.summary_first_person) h+=`<blockquote class=\"fp\">“${escapeHtml(p.summary_first_person)}”</blockquote>`;
  if(p.summary_zh) h+=`<p class=\"summary\">${escapeHtml(p.summary_zh)}</p>`;
  if(p.lesson) h+=`<div class=\"lesson\">💡 ${escapeHtml(p.lesson)}</div>`;
  h+=`</div>`;
  if(p.endeavors?.length){
    h+=`<div class=\"section\"><h4>成事儿周期</h4>`;
    p.endeavors.forEach(ed=>{
      h+=`<div class=\"ed-card\"><div class=\"ed-card-head\"><b>${escapeHtml(ed.title_zh)}</b> <span class=\"muted\">${escapeHtml(ed.domain||'')}</span><span class=\"muted\" style=\"float:right\">${escapeHtml(ed.start_date||'?')}→${escapeHtml(ed.end_date||'?')}</span></div>`;
      if(ed.description_zh) h+=`<div class=\"ed-desc\">${escapeHtml(ed.description_zh)}</div>`;
      if(ed.phases?.length){ h+=`<div class=\"phases\">`; ed.phases.forEach(ph=>{ h+=`<div class=\"phase-row\">· <b>${escapeHtml(ph.name)}</b> <span class=\"muted\">${escapeHtml(ph.start_date||'')}~${escapeHtml(ph.end_date||'')} ${escapeHtml(ph.place||'')}</span>${ph.highlight?`<em class=\"hl\"> ${escapeHtml(ph.highlight)}</em>`:''}</div>`; }); h+=`</div>`; }
      if(ed.outcome) h+=`<div class=\"ok\">结果: ${escapeHtml(ed.outcome)}</div>`;
      if(ed.lesson) h+=`<div class=\"tip-lesson\">启发: ${escapeHtml(ed.lesson)}</div>`;
      h+=`</div>`;
    });
    h+=`</div>`;
  }
  const evs=DATA.events.filter(e=>e.person_qid===p.qid).sort((a,b)=>(a.date||'9999').localeCompare(b.date||'9999'));
  if(evs.length){
    h+=`<div class=\"section\"><h4>时间线 · ${evs.length}条</h4><div class=\"ev-list\">`;
    evs.forEach(ev=>{
      const hl=ev.is_highlight;
      h+=`<div class=\"ev-row ${hl?'hl':''} ${ev.date===dateHint?'active':''}\"><div class=\"ev-row-head\"><span class=\"ev-title-sm\" style=\"color:${hl?'var(--gold)':'var(--ink)'};font-weight:${hl?'700':'400'}\">${hl && ev.highlight_type? `<span class=\"hl-tag small\" style=\"background:${HL_COLORS[ev.highlight_type]||'var(--gold)'}\">${escapeHtml(ev.highlight_type)}</span> `:''}${escapeHtml(ev.title_zh)}</span><span class=\"muted\" style=\"float:right;font-size:11px\">${escapeHtml(ev.date||'')} ${escapeHtml(ev.place_name||ev.place||'')}</span></div>`;
      if(ev.highlight_note) h+=`<div class=\"hl-note\">${escapeHtml(ev.highlight_note)}</div>`;
      else if(ev.description) h+=`<div class=\"muted\" style=\"font-size:11px\">${escapeHtml(ev.description)}</div>`;
      else if(ev.description_zh) h+=`<div class=\"muted\" style=\"font-size:11px\">${escapeHtml(ev.description_zh)}</div>`;
      h+=`</div>`;
    });
    h+=`</div></div>`;
  }
  el.innerHTML=h;
  document.getElementById('detail')?.classList.add('open');
  // highlight age as well
  document.querySelectorAll('.p-row').forEach(r=> r.classList.toggle('detail-target', r.dataset.qid===p.qid));
}
function closeDetail(){ document.getElementById('detail')?.classList.remove('open'); document.querySelectorAll('.p-row').forEach(r=>r.classList.remove('detail-target')); }
window.closeDetail=closeDetail;

function debounce(fn, ms){ let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a), ms); }; }

init();
