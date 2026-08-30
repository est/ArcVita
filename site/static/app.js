// ArcVita — 单文件无构建 (site/design.md 契约)
let DATA = { persons: [], events: [], highlights: [], index: null };
let filtered = [];
let zoom = 1, focusedQid = null;
let filters = { q: '' };
let minY = -600, maxY = 2000;
const BASE_PX = 10;
const LABEL_W = 168;
const ROW_N = 50, ROW_F = 148;
const HL_COLORS = {
  '成语':'var(--c-成语)','代表作':'var(--c-代表作)','战役':'var(--c-战役)',
  '决策':'var(--c-决策)','名言':'var(--c-名言)','发明':'var(--c-发明)',
  '制度':'var(--c-制度)','演讲':'var(--c-演讲)','奖项':'var(--c-奖项)',
  '远航':'var(--c-远航)','王表':'var(--c-王表)','朝代更替':'var(--c-朝代更替)',
  '社会变革':'var(--c-社会变革)','文化':'var(--c-文化)','至暗时刻':'var(--c-至暗时刻)',
  '名场面':'var(--c-名场面)','仪式':'var(--c-仪式)','典故':'var(--c-成语)'
};

function parseYear(s){
  if(s==null) return null;
  const m = String(s).replace(/约/g,'').match(/-?\d+/);
  return m ? parseInt(m[0],10) : null;
}
function ageAt(b,y){ if(b==null||y==null) return null; return y-b; }
function escapeHtml(s){
  return (s==null?'':String(s)).replace(/[&<>"']/g, c=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));
}
function debounce(fn,ms){ let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a),ms); }; }

async function loadAll(){
  const fetchJSON = async u => { const r=await fetch(u); if(!r.ok) throw new Error(u+' '+r.status); return r.json(); };
  const fetchText = async u => { const r=await fetch(u); if(!r.ok) throw new Error(u+' '+r.status); return r.text(); };
  const index = await fetchJSON('data/index.json');
  const cks = Object.keys(index.centuries||{});
  const results = await Promise.allSettled(cks.map(ck=> fetchJSON('data/'+ck+'.json')));
  const persons = [];
  for(const r of results) if(r.status==='fulfilled' && Array.isArray(r.value)) persons.push(...r.value);
  // 兼容 fallback: 若分片缺失，尝试 persons.yaml 忽略
  let highlights = [], events = [];
  try{ highlights = await fetchJSON('data/highlights.json'); }catch(e){}
  try{
    const tlText = await fetchText('data/timeline.jsonl');
    events = tlText.trim().split('\n').filter(Boolean).map(l=>JSON.parse(l));
  }catch(e){}
  try{
    // 若 timeline 极少，补充从 persons.events 抽取以避免空白（仅作刻度，不影响渲染主路径）
    if(events.length < 20){
      const extra = [];
      persons.forEach(p=> (p.events||[]).forEach(ev=> extra.push({ date:ev.date, place:ev.place_name, title:ev.title_zh, type:ev.event_type, is_highlight:ev.is_highlight, highlight_type:ev.highlight_type, highlight_note:ev.highlight_note, person_qid:p.qid, person:p.name_zh })));
      // 去重
      const seen=new Set(events.map(e=>e.date+e.title));
      extra.forEach(e=>{ const k=e.date+e.title; if(!seen.has(k)){ events.push(e); seen.add(k); }});
    }
  }catch(e){}
  persons.sort((a,b)=> (parseYear(a.birth_date)||9999) - (parseYear(b.birth_date)||9999));
  events.sort((a,b)=> String(a.date||'9999').localeCompare(String(b.date||'9999')));
  return { index, persons, events, highlights };
}

function computeDomain(persons, events, highlights, focusedQid){
  if(focusedQid){
    const fp = persons.find(p=>p.qid===focusedQid);
    if(fp){
      const by = parseYear(fp.birth_date);
      const dy = parseYear(fp.death_date);
      if(by!=null){
        const end = dy!=null? dy : by+60;
        const span = Math.max(30, end-by);
        const pad = Math.max(12, span*0.2);
        return [by-pad, end+pad];
      }
    }
  }
  const years = [...events.map(e=>parseYear(e.date)), ...highlights.map(h=>parseYear(h.date))].filter(v=>v!=null);
  if(!years.length) return [-600,2000];
  return [Math.min(...years)-20, Math.max(...years)+20];
}
function stepFor(span, ppx){
  const visible = span/ppx;
  if(visible<32) return 5;
  if(visible<85) return 10;
  if(visible<210) return 20;
  if(visible<520) return 50;
  if(visible<1050) return 100;
  return 200;
}
function ticksArr(minY,maxY,step,W,span){
  const arr=[]; const start=Math.ceil(minY/step)*step;
  for(let y=start; y<=maxY; y+=step){
    const x = 168 + (y-minY)/span*(W-240 - 0); // label 168, total W = span*ppx+240
    // spec: tl-inner width = span*10+240, p-track left 168
    // so usable track width = W-168
    // we keep axis ticks aligned to track: x = 168 + (y-minY)/span*(W-168)
    // recompute correctly below in render scope
    arr.push({y,x,label: y<0? Math.abs(y)+' BCE' : String(y)});
  }
  return arr;
}

let tipEl=null;
function initTip(){ tipEl=document.getElementById('tip'); }
function showTip(html,x,y){
  if(!tipEl) initTip();
  tipEl.innerHTML=html; tipEl.style.display='block';
  const pad=12; let lx=x+pad, ty=y-16;
  // wait for layout
  const r=tipEl.getBoundingClientRect();
  if(lx+r.width+12>window.innerWidth) lx=x - r.width - pad;
  if(ty+r.height+12>window.innerHeight) ty=y - r.height - 12;
  if(lx<8) lx=8;
  if(ty<8) ty=8;
  tipEl.style.left=lx+'px'; tipEl.style.top=ty+'px';
}
function hideTip(){ if(tipEl) tipEl.style.display='none'; }

function readHash(){
  const h=new URLSearchParams(location.hash.slice(1));
  const f=h.get('focus'); if(f) focusedQid=f;
  const z=parseFloat(h.get('z')||''); if(!isNaN(z)) zoom=Math.max(0.15,Math.min(40,z));
  const q=h.get('q'); if(q!=null) filters.q=q;
}
function writeHash(){
  const h=new URLSearchParams();
  if(focusedQid) h.set('focus',focusedQid);
  if(Math.abs(zoom-1)>0.01) h.set('z', String(Math.round(zoom*10)/10));
  if(filters.q) h.set('q', filters.q);
  const s=h.toString();
  history.replaceState(null,'', s? '#'+s : location.pathname+location.search);
}

function personMatches(p){
  if(!filters.q) return true;
  const q=filters.q.toLowerCase();
  const hay=[p.name_zh, p.name_en, p.archetype, p.era, ...(p.dilemmas||[]), p.summary_zh||'', p.lesson||''].join(' ').toLowerCase();
  return hay.includes(q);
}
function applyFilter(){
  filtered = DATA.persons.filter(personMatches);
  filtered.sort((a,b)=> (parseYear(a.birth_date)||9999)-(parseYear(b.birth_date)||9999));
  writeHash();
  render();
}

function setupInteractions(){
  const wrap=document.getElementById('wrap');
  if(!wrap) return;
  // zoom wheel
  wrap.addEventListener('wheel', e=>{
    if(e.ctrlKey||e.metaKey){
      e.preventDefault();
      const rect=wrap.getBoundingClientRect();
      const cursorX=e.clientX-rect.left;
      const trackW=Math.max(1, wrap.clientWidth - LABEL_W);
      const pct=Math.max(0,Math.min(1,(cursorX - LABEL_W)/trackW));
      const span=maxY-minY||100;
      const anchorY=minY+span*pct;
      const factor=e.deltaY<0?1.18:0.85;
      const newZoom=Math.max(0.15,Math.min(40, zoom*factor));
      const newSpan=span*(zoom/newZoom);
      minY=anchorY - newSpan*pct;
      maxY=minY+newSpan;
      zoom=newZoom;
      render();
    }
  }, {passive:false});
  document.getElementById('zoomIn')?.addEventListener('click', ()=>{ zoom=Math.min(40, zoom*1.32); render(); writeHash(); });
  document.getElementById('zoomOut')?.addEventListener('click', ()=>{ zoom=Math.max(0.15, zoom*0.76); render(); writeHash(); });
  document.getElementById('zoomReset')?.addEventListener('click', ()=>{ zoom=1; focusedQid=null; filters.q=''; const inp=document.getElementById('q'); if(inp) inp.value=''; writeHash(); applyFilter(); });
  document.getElementById('clearSearch')?.addEventListener('click', ()=>{ filters.q=''; const q=document.getElementById('q'); if(q) q.value=''; applyFilter(); });
  // drag
  let dragging=false, sx=0, sl=0;
  wrap.addEventListener('mousedown', e=>{ if(e.button!==0) return; dragging=true; sx=e.pageX - wrap.offsetLeft; sl=wrap.scrollLeft; wrap.style.cursor='grabbing'; });
  wrap.addEventListener('mouseleave', ()=>{ dragging=false; wrap.style.cursor='grab'; });
  wrap.addEventListener('mouseup', ()=>{ dragging=false; wrap.style.cursor='grab'; });
  wrap.addEventListener('mousemove', e=>{ if(!dragging) return; e.preventDefault(); wrap.scrollLeft = sl - (e.pageX - wrap.offsetLeft - sx)*1.2; });
  document.addEventListener('keydown', e=>{
    if(e.key==='Escape'){
      if(document.getElementById('detail')?.classList.contains('open')){ closeDetail(); return; }
      if(focusedQid){ focusedQid=null; writeHash(); render(); }
      else { hideTip(); clearAges(); }
    }
    if(e.key==='/' && !e.ctrlKey && !e.metaKey && !e.altKey){
      const q=document.getElementById('q'); if(q && document.activeElement!==q){ e.preventDefault(); q.focus(); }
    }
    if(e.key==='+'){ zoom=Math.min(40, zoom*1.25); render(); writeHash(); }
    if(e.key==='-'){ zoom=Math.max(0.15, zoom*0.8); render(); writeHash(); }
  });
  // delegated hover/click — single binding guard
  const inner=document.getElementById('inner');
  if(inner && !inner._hoverBound){
    inner._hoverBound=true;
    let raf=null, lastTarget=null;
    const showDotTip=(dot)=>{
      const hlColor = HL_COLORS[dot.dataset.type]||'var(--gold)';
      let t='<div class="t-name">'+escapeHtml(dot.dataset.title||'')+'</div><div class="t-date">'+escapeHtml(dot.dataset.date||'')+(dot.dataset.age? ' · '+escapeHtml(dot.dataset.age)+'岁':'')+'</div>';
      if(dot.dataset.place) t+='<div class="t-place">📍 '+escapeHtml(dot.dataset.place)+'</div>';
      if(dot.dataset.hl) t+='<div class="t-hl">★ '+escapeHtml(dot.dataset.hl)+'</div>';
      else if(dot.dataset.desc) t+='<div class="t-desc">'+escapeHtml(dot.dataset.desc)+'</div>';
      if(dot.dataset.type) t+='<div class="t-type"><span class="hl-tag" style="background:'+hlColor+'">'+escapeHtml(dot.dataset.type)+'</span></div>';
      // tip inner prepared for showTip wrapper to position
      if(!tipEl) initTip();
      tipEl.innerHTML=t;
    };
    const syncAges=(dot)=>{
      const y=parseYear(dot.dataset.date);
      if(y==null) return;
      filtered.forEach(p=>{
        const by=parseYear(p.birth_date), dy=parseYear(p.death_date);
        const el=document.getElementById('age-'+p.qid);
        if(!el) return;
        if(by==null){ el.textContent=''; el.style.display='none'; return; }
        const alive = dy==null || y<=dy;
        const age=ageAt(by,y);
        if(age==null || !alive || age<-80){ el.textContent=''; el.style.display='none'; return; }
        const isMe=p.qid===dot.dataset.qid;
        el.textContent = age<0? Math.abs(age)+'前生' : age+'岁';
        el.style.display='inline';
        el.style.color=isMe?'var(--accent)':'var(--mist)';
        el.style.fontWeight=isMe?'800':'500';
        el.style.background=isMe?'rgba(122,58,16,.08)':'transparent';
        el.style.borderRadius=isMe?'4px':'0';
        el.style.padding=isMe?'0 4px':'0';
      });
    };
    inner.addEventListener('mouseover', e=>{
      const dot=e.target.closest('.ev-dot');
      if(!dot){ hideTip(); clearAges(); lastTarget=null; return; }
      lastTarget=dot;
      if(raf) cancelAnimationFrame(raf);
      raf=requestAnimationFrame(()=>{ if(!lastTarget) return; showDotTip(lastTarget); syncAges(lastTarget); });
    });
    inner.addEventListener('mousemove', e=>{
      const dot=e.target.closest('.ev-dot');
      if(dot){
        if(dot!==lastTarget){
          lastTarget=dot;
          if(raf) cancelAnimationFrame(raf);
          raf=requestAnimationFrame(()=>{ showDotTip(dot); syncAges(dot); });
        }
        // follow cursor — only when over dot, reuse current tip HTML
        if(tipEl && tipEl.style.display==='block'){
          const html=tipEl.innerHTML;
          showTip(html, e.clientX, e.clientY);
        } else if(tipEl){
          showTip(tipEl.innerHTML, e.clientX, e.clientY);
        }
      }else{
        hideTip(); clearAges(); lastTarget=null;
      }
    });
    inner.addEventListener('mouseleave', ()=>{ hideTip(); clearAges(); lastTarget=null; });
    inner.addEventListener('mouseout', e=>{
      if(!e.relatedTarget || !inner.contains(e.relatedTarget)){ hideTip(); clearAges(); lastTarget=null; }
    });
    inner.addEventListener('click', e=>{
      const label=e.target.closest('.p-label');
      if(label){
        const qid=label.dataset.qid;
        focusedQid = focusedQid===qid? null : qid;
        writeHash(); render();
        return;
      }
      const dot=e.target.closest('.ev-dot');
      if(dot && dot.dataset.cluster!=='1'){
        const qid=dot.dataset.qid;
        const p=DATA.persons.find(x=>x.qid===qid);
        if(p) showDetail(p, dot.dataset.date);
        e.stopPropagation();
      }
    });
  }
}

function clusterEvents(events, W, span){
  const withX=events.map(ev=>{
    const y=parseYear(ev.date);
    const x=y==null?null : (y-minY)/span*(W-168) + 168; // align to p-track coordinate
    return {...ev, _x:x, _y:y};
  }).filter(e=>e._x!=null).sort((a,b)=>a._x-b._x);
  const out=[];
  let i=0;
  while(i<withX.length){
    const base=withX[i];
    if(base.is_highlight){ out.push(base); i++; continue; }
    const cluster=[base];
    let j=i+1;
    while(j<withX.length && withX[j]._x - base._x < 12 && !withX[j].is_highlight){
      cluster.push(withX[j]); j++;
    }
    if(cluster.length>1){
      const avgX=cluster.reduce((s,c)=>s+c._x,0)/cluster.length;
      out.push({ _cluster:true, _x:avgX, _count:cluster.length, _members:cluster, date:cluster[0].date, title_zh:'+'+cluster.length, is_highlight:false, event_type:'cluster' });
      i=j;
    }else{ out.push(base); i++; }
  }
  return out;
}

function render(){
  const inner=document.getElementById('inner');
  const wrap=document.getElementById('wrap');
  if(!inner||!wrap) return;
  if(!DATA.persons.length){ inner.innerHTML='<div style="padding:28px;color:var(--mist);font-size:12px">数据加载中…</div>'; return; }
  const [dMin,dMax]=computeDomain(DATA.persons, DATA.events, DATA.highlights, focusedQid);
  if(!focusedQid){
    const wrapW=wrap.clientWidth||980;
    const ppx=zoom*BASE_PX;
    const desiredSpan=(wrapW-240)/ppx;
    const curSpan=maxY-minY||100;
    if(Math.abs(curSpan-desiredSpan)>48){
      const cx=(dMin+dMax)/2;
      minY=cx - desiredSpan/2; maxY=cx + desiredSpan/2;
    }
    if(!isFinite(minY)||!isFinite(maxY)){ minY=dMin; maxY=dMax; }
  }else{
    minY=dMin; maxY=dMax;
  }
  const span=maxY-minY||100;
  const ppx=zoom*BASE_PX;
  const W=Math.max(900, span*ppx + 240);
  const step=stepFor(span, ppx);
  const usableW=W-168;
  // build axis ticks aligned to track
  const tickStart=Math.ceil(minY/step)*step;
  let axisHtml='<div class="axis-row" style="width:'+W+'px">';
  for(let y=tickStart; y<=maxY; y+=step){
    const x=168 + (y-minY)/span*usableW;
    axisHtml+='<div class="tick" style="left:'+x+'px"><span>'+(y<0? Math.abs(y)+' BCE' : y)+'</span><div class="line"></div></div>';
  }
  axisHtml+='</div>';

  const frag=document.createDocumentFragment();
  const tmp=document.createElement('div');
  tmp.innerHTML=axisHtml;
  while(tmp.firstChild) frag.appendChild(tmp.firstChild);

  const rowsToRender = filtered.length? filtered : DATA.persons;
  let totalH=32;
  const edColorMap={
    '军事':'#8b1a1a','政治':'#2e6b4a','军事/政治':'#7a3a10','政治/军事':'#7a3a10',
    '科学':'#415bdb','文化':'#6b5bb0','航海/外交':'#2e7a6a','商业/技术':'#b8860b',
    '思想':'#7a3a10','艺术/科学':'#7a5bd8','军事/文化':'#6b4226'
  };

  for(const p of rowsToRender){
    const by=parseYear(p.birth_date), dy=parseYear(p.death_date);
    if(by==null) continue;
    const endY= dy==null? by+60 : dy;
    const isFocused= focusedQid===p.qid;
    const isDim= focusedQid && !isFocused;
    totalH += isFocused? ROW_F:ROW_N;
    const x1=168 + (by-minY)/span*usableW;
    const x2=168 + (endY-minY)/span*usableW;
    const roleClass=p.role||'中性';
    const pEvents=(p.events && p.events.length? p.events : DATA.events.filter(e=>e.person_qid===p.qid));
    const clustered=clusterEvents(pEvents, W, span);

    let trackInner='<div class="lifespan" style="left:'+x1+'px;width:'+Math.max(4,x2-x1)+'px"></div>';

    if(isFocused && p.endeavors?.length){
      p.endeavors.forEach((ed,ei)=>{
        const sy=parseYear(ed.start_date), ey=parseYear(ed.end_date);
        if(sy==null||ey==null) return;
        const ex1=168 + (sy-minY)/span*usableW;
        const ex2=168 + (ey-minY)/span*usableW;
        const color=edColorMap[ed.domain]||'var(--accent)';
        const w=Math.max(14, ex2-ex1);
        trackInner+='<div class="ed-bar" style="left:'+ex1+'px;width:'+w+'px;background:'+color+'"></div>';
        trackInner+='<div class="ed-title" style="left:'+(ex1+6)+'px;color:'+color+'">'+escapeHtml(ed.title_zh)+'</div>';
        trackInner+='<div class="ed-range" style="left:'+(ex2+6)+'px">'+escapeHtml(ed.start_date||'?')+' → '+escapeHtml(ed.end_date||'?')+'</div>';
        if(ed.phases) ed.phases.forEach((ph,pi)=>{
          const psy=parseYear(ph.start_date)||sy, pey=parseYear(ph.end_date)||ey;
          const px1=168 + (psy-minY)/span*usableW, px2=168 + (pey-minY)/span*usableW;
          const pw=Math.max(2, px2-px1);
          trackInner+='<div class="phase" style="left:'+px1+'px;width:'+pw+'px;top:'+(92+pi*6)+'px;background:'+color+'"></div>';
          if(pw>36) trackInner+='<div class="phase-label" style="left:'+(px1+2)+'px;top:'+(82+pi*6)+'px;color:'+color+'">'+escapeHtml(ph.name)+'</div>';
          if(ph.highlight && pw>76) trackInner+='<div class="phase-hl" style="left:'+((px1+px2)/2)+'px;top:60px">'+escapeHtml(ph.highlight)+'</div>';
        });
      });
      clustered.forEach(ev=>{
        const y=parseYear(ev.date); if(y==null) return;
        const ex=ev._x;
        const age=ageAt(by,y);
        const cls=ev._cluster? 'cluster' : ev.is_highlight? 'highlight' : ev.event_type==='出生'? 'birth' : ev.event_type==='逝世'? 'death':'normal';
        trackInner+='<div class="ev-dot '+cls+'" style="left:'+ex+'px" data-qid="'+p.qid+'" data-date="'+escapeHtml(ev.date||'')+'" data-title="'+escapeHtml(ev.title_zh||ev.title||'')+'" data-place="'+escapeHtml(ev.place_name||ev.place||'')+'" data-desc="'+escapeHtml(ev.description||ev.description_zh||ev.highlight_note||'')+'" data-hl="'+escapeHtml(ev.highlight_note||'')+'" data-age="'+(age??'')+'" data-type="'+escapeHtml(ev.highlight_type||ev.event_type||'')+'" data-cluster="'+(ev._cluster?1:0)+'"></div>';
        if(ev._cluster){
          trackInner+='<div class="cluster-badge" style="left:'+ex+'px">+'+ev._count+'</div>';
        } else if(ev.title_zh||ev.title){
          trackInner+='<div class="ev-title focus" style="left:'+(ex+9)+'px">'+escapeHtml(ev.title_zh||ev.title)+'</div>';
          trackInner+='<div class="ev-sub" style="left:'+(ex+9)+'px;top:46px">'+escapeHtml(ev.date||'')+(age!=null?' '+age+'岁':'')+'</div>';
        }
      });
    }else{
      clustered.forEach(ev=>{
        const ex=ev._x; const age=ageAt(by, parseYear(ev.date));
        const cls=ev._cluster? 'cluster' : ev.is_highlight? 'highlight' : ev.event_type==='出生'? 'birth' : ev.event_type==='逝世'? 'death':'normal';
        trackInner+='<div class="ev-dot '+cls+'" style="left:'+ex+'px" data-qid="'+p.qid+'" data-date="'+escapeHtml(ev.date||'')+'" data-title="'+escapeHtml(ev.title_zh||ev.title||'')+'" data-place="'+escapeHtml(ev.place_name||ev.place||'')+'" data-desc="'+escapeHtml(ev.description||ev.description_zh||ev.highlight_note||'')+'" data-hl="'+escapeHtml(ev.highlight_note||'')+'" data-age="'+(age??'')+'" data-type="'+escapeHtml(ev.highlight_type||ev.event_type||'')+'" data-cluster="'+(ev._cluster?1:0)+'"></div>';
        if(ev._cluster){
          trackInner+='<div class="cluster-badge" style="left:'+ex+'px">'+ev._count+'</div>';
        } else if((ev.is_highlight||ev.event_type==='出生'||ev.event_type==='逝世') && (ev.title_zh||ev.title)){
          // only highlight/birth/death show labels when zoom >=0.8 per spec — we respect via CSS opacity or JS gate
          if(zoom>=0.8){
            trackInner+='<div class="ev-title" style="left:'+ex+'px">'+escapeHtml(ev.title_zh||ev.title)+'</div>';
            if(ev.is_highlight) trackInner+='<div class="ev-age" style="left:'+ex+'px">'+(age!=null?age+'岁':'')+'</div>';
          }
        }
      });
    }

    const row=document.createElement('div');
    row.className='p-row'+(isFocused?' focused':'')+(isDim?' dim':'');
    row.dataset.qid=p.qid;
    row.innerHTML='<div class="p-label" data-qid="'+p.qid+'"><span class="dot '+roleClass+'"></span><span class="p-name">'+escapeHtml(p.name_zh)+'</span><span class="p-age" id="age-'+p.qid+'"></span><span class="arch">'+escapeHtml((p.archetype||'').slice(0,8))+'</span><span class="ed-count">'+(p.endeavors?.length? (isFocused? '▾':'▸')+p.endeavors.length : '')+'</span></div><div class="p-track">'+trackInner+'</div>';
    frag.appendChild(row);
  }

  inner.replaceChildren(frag);
  inner.style.width=W+'px';
  inner.style.height=totalH+'px';

  const zEl=document.getElementById('zoomLevel');
  if(zEl){
    if(focusedQid){
      const fp=DATA.persons.find(p=>p.qid===focusedQid);
      zEl.textContent='聚焦 · '+(fp?.name_zh||focusedQid);
      zEl.style.color='var(--accent)'; zEl.style.fontWeight='700';
    }else{
      zEl.textContent= zoom.toFixed(1)+'x · '+Math.round(span)+'年';
      zEl.style.color='var(--mist)'; zEl.style.fontWeight='400';
    }
  }
}

function clearAges(){ filtered.forEach(p=>{ const el=document.getElementById('age-'+p.qid); if(el){ el.textContent=''; el.style.display='none'; el.style.background='transparent'; } }); }

function showDetail(p, dateHint){
  const el=document.getElementById('dc');
  if(!el) return;
  let h='<div class="detail-head"><h3>'+escapeHtml(p.name_zh)+' <span class="arch">'+escapeHtml(p.archetype||'')+'</span></h3><div class="detail-meta">'+escapeHtml(p.era||'')+' · '+(p.birth_date? escapeHtml(p.birth_date):'?')+' → '+(p.death_date? escapeHtml(p.death_date):'?')+' · '+escapeHtml(p.birth_place||'')+'</div>';
  if(p.summary_first_person) h+='<blockquote class="fp">“'+escapeHtml(p.summary_first_person)+'”</blockquote>';
  if(p.summary_zh) h+='<p class="summary">'+escapeHtml(p.summary_zh)+'</p>';
  if(p.lesson) h+='<div class="lesson">💡 '+escapeHtml(p.lesson)+'</div>';
  if(p.dilemmas?.length) h+='<div class="muted" style="margin-top:6px">境遇：'+p.dilemmas.map(d=>'<span style="display:inline-block;border:1px solid var(--ruler);border-radius:10px;padding:1px 6px;margin:2px;font-size:10px;background:#fff">'+escapeHtml(d)+'</span>').join('')+'</div>';
  h+='</div>';
  if(p.endeavors?.length){
    h+='<div class="section"><h4>成事儿周期 · '+p.endeavors.length+'</h4>';
    p.endeavors.forEach(ed=>{
      h+='<div class="ed-card"><div class="ed-card-head"><b>'+escapeHtml(ed.title_zh)+'</b><span class="muted">'+escapeHtml(ed.domain||'')+'</span><span class="muted" style="margin-left:auto">'+escapeHtml(ed.start_date||'?')+' → '+escapeHtml(ed.end_date||'?')+'</span></div>';
      if(ed.description_zh) h+='<div class="ed-desc">'+escapeHtml(ed.description_zh)+'</div>';
      if(ed.phases?.length){ h+='<div class="phases">'; ed.phases.forEach(ph=>{ h+='<div class="phase-row">· <b>'+escapeHtml(ph.name)+'</b><span class="muted">'+escapeHtml(ph.start_date||'')+' ~ '+escapeHtml(ph.end_date||'')+' '+escapeHtml(ph.place||'')+'</span>'+(ph.highlight? '<em class="hl"> '+escapeHtml(ph.highlight)+'</em>':'')+'</div>'; }); h+='</div>'; }
      if(ed.places?.length) h+='<div class="muted" style="font-size:10px;margin-top:4px">📍 '+ed.places.map(escapeHtml).join(' → ')+'</div>';
      if(ed.outcome) h+='<div class="ok">结果 · '+escapeHtml(ed.outcome)+'</div>';
      if(ed.lesson) h+='<div class="tip-lesson">启发 · '+escapeHtml(ed.lesson)+'</div>';
      h+='</div>';
    });
    h+='</div>';
  }
  const evs=(p.events && p.events.length? p.events : DATA.events.filter(e=>e.person_qid===p.qid)).slice().sort((a,b)=> String(a.date||'9999').localeCompare(String(b.date||'9999')));
  if(evs.length){
    h+='<div class="section"><h4>时间线 · '+evs.length+' 条</h4><div class="ev-list">';
    evs.forEach(ev=>{
      const hl=ev.is_highlight;
      const active= ev.date===dateHint? ' active':'';
      h+='<div class="ev-row'+(hl?' hl':'')+active+'"><div class="ev-row-head"><span class="ev-title-sm" style="color:'+(hl?'var(--gold)':'var(--ink)')+';font-weight:'+(hl?'700':'500')+'">'+(hl&&ev.highlight_type? '<span class="hl-tag small" style="background:'+(HL_COLORS[ev.highlight_type]||'var(--gold)')+'">'+escapeHtml(ev.highlight_type)+'</span> ':'')+escapeHtml(ev.title_zh||ev.title||'')+'</span><span class="muted" style="margin-left:auto;font-size:10px;white-space:nowrap">'+escapeHtml(ev.date||'')+' '+escapeHtml(ev.place_name||ev.place||'')+'</span></div>';
      if(ev.highlight_note) h+='<div class="hl-note">'+escapeHtml(ev.highlight_note)+'</div>';
      else if(ev.description_zh) h+='<div class="muted" style="font-size:11px;margin-top:2px">'+escapeHtml(ev.description_zh)+'</div>';
      else if(ev.description) h+='<div class="muted" style="font-size:11px;margin-top:2px">'+escapeHtml(ev.description)+'</div>';
      h+='</div>';
    });
    h+='</div></div>';
  }
  h+='<div class="muted" style="margin-top:14px;font-size:10px">按 ESC 关闭 · 点击左侧人名聚焦事业周期 · hover 事件点查看同期年龄</div>';
  el.innerHTML=h;
  document.getElementById('detail')?.classList.add('open');
}
function closeDetail(){ document.getElementById('detail')?.classList.remove('open'); }
window.closeDetail=closeDetail;

async function init(){
  try{
    readHash();
    DATA=await loadAll();
    const s=document.getElementById('stats'); if(s) s.textContent= DATA.persons.length+' 人物 · '+DATA.events.length+' 事件 · '+DATA.highlights.length+' 名场面';
    initTip();
    setupInteractions();
    const qInput=document.getElementById('q');
    if(qInput){
      qInput.value=filters.q||'';
      qInput.addEventListener('input', debounce(e=>{ filters.q=e.target.value.trim(); applyFilter(); },200));
    }
    applyFilter();
    window.addEventListener('hashchange', ()=>{ readHash(); const q=document.getElementById('q'); if(q) q.value=filters.q||''; applyFilter(); });
  }catch(e){
    const el=document.getElementById('stats'); if(el) el.textContent='加载失败: '+e.message;
    console.error(e);
    const inner=document.getElementById('inner');
    if(inner) inner.innerHTML='<div style="padding:24px;color:var(--crimson)">加载失败：'+escapeHtml(e.message)+'<br><span style="color:var(--mist)">请确认 python -m http.server -d site 启动且 data/*.json 可访问</span></div>';
  }
}
init();
