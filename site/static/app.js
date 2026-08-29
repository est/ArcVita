let DATA={persons:[],events:[],highlights:[]};
let activeRole=null,filtered=[];
let zoomLevel=1;
let focusedQid=null;

function py(s){if(!s)return null;const m=s.replace(/约/g,'').match(/^-?\d+/);return m?parseInt(m[0]):null}
function ageAt(b,y){return b&&y?y-b:null}
const HL_COLORS={'成语':'var(--c-成语)','代表作':'var(--c-代表作)','战役':'var(--c-战役)','决策':'var(--c-决策)','至暗时刻':'var(--c-至暗时刻)','名言':'var(--c-名言)','发明':'var(--c-发明)','制度':'var(--c-制度)','演讲':'var(--c-演讲)','奖项':'var(--c-奖项)','远航':'var(--c-远航)','朝代更替':'var(--c-朝代更替)','社会变革':'var(--c-社会变革)','文化':'var(--c-文化)','王表':'var(--c-王表)'};
const BASE_PX=10;
let minY=0,maxY=1;

async function fetchJSON(url){const r=await fetch(url);if(!r.ok)throw new Error(`${url} ${r.status}`);return r.json()}
async function fetchText(url){const r=await fetch(url);if(!r.ok)throw new Error(`${url} ${r.status}`);return r.text()}

async function init(){
  try{
    DATA.index=await fetchJSON('data/index.json');
    for(const ck of Object.keys(DATA.index.centuries||{})){
      try{const p=await fetchJSON(`data/${ck}.json`);if(Array.isArray(p))DATA.persons.push(...p)}catch(e){}
    }
    DATA.events=(await fetchText('data/timeline.jsonl')).trim().split('\n').filter(Boolean).map(l=>JSON.parse(l));
    DATA.highlights=await fetchJSON('data/highlights.json');
    DATA.events.sort((a,b)=>(a.date||'9999').localeCompare(b.date||'9999'));
    document.getElementById('stats').innerHTML=`${DATA.persons.length}人物 · ${DATA.events.length}事件 · ${DATA.highlights.length}名场面`;
    renderFilters();applyFilter();setupZoom();
  }catch(e){document.getElementById('stats').innerHTML='加载失败: '+e.message}
}

function setupZoom(){
  const wrap=document.getElementById('wrap');
  wrap.addEventListener('wheel',e=>{
    if(e.ctrlKey||e.metaKey){
      e.preventDefault();
      zoomLevel=Math.max(0.1,Math.min(50,zoomLevel*(e.deltaY<0?1.2:0.83)));
      renderTimeline();
    }
  },{passive:false});
  document.getElementById('zoomIn').onclick=()=>{zoomLevel=Math.min(50,zoomLevel*1.5);renderTimeline()};
  document.getElementById('zoomOut').onclick=()=>{zoomLevel=Math.max(0.1,zoomLevel*0.67);renderTimeline()};
  document.getElementById('zoomReset').onclick=()=>{zoomLevel=0;focusedQid=null;renderTimeline()};
}

function renderFilters(){
  const roles=[...new Set(DATA.persons.map(p=>p.role).filter(Boolean))];
  let h='<label>角色:</label>';
  roles.forEach(r=>{h+=`<button class="fb" data-role="${r}">${r}</button>`});
  h+=`<button class="fb active" data-role="all" style="margin-left:8px">全部</button>`;
  document.getElementById('filters').innerHTML=h;
  document.querySelectorAll('.fb').forEach(b=>{b.addEventListener('click',()=>{
    if(b.dataset.role){activeRole=b.dataset.role==='all'?null:b.dataset.role;document.querySelectorAll('.fb').forEach(x=>x.classList.remove('active'));b.classList.add('active')}
    applyFilter();})});
}

function applyFilter(){
  filtered=DATA.persons.filter(p=>{if(activeRole&&p.role!==activeRole)return false;return true});
  filtered.sort((a,b)=>{const ya=py(a.birth_date)||9999,yb=py(b.birth_date)||9999;return ya-yb});
  renderTimeline();
}

function renderTimeline(){
  const inner=document.getElementById('inner');
  const allYears=[...DATA.events.map(e=>py(e.date)),...DATA.highlights.map(h=>py(h.date))].filter(Boolean);
  if(!allYears.length)return;

  if(focusedQid){
    const fp=DATA.persons.find(p=>p.qid===focusedQid);
    if(fp){const by=py(fp.birth_date),dy=py(fp.death_date)||by+60;const pad=Math.max(10,(dy-by)*0.2);minY=by-pad;maxY=dy+pad}
  }else{
    minY=Math.min(...allYears);maxY=Math.max(...allYears);
  }

  const span=maxY-minY||100;
  const ppx=zoomLevel*BASE_PX;
  const W=Math.max(800,span*ppx+160);
  const ROW_N=50,ROW_E=160;
  const LH=42,LABEL_W=160;

  // adaptive ticks
  const yearsVisible=span/ppx;
  const step=yearsVisible<30?5:yearsVisible<80?10:yearsVisible<200?20:yearsVisible<500?50:100;
  let ticks='';
  for(let y=Math.ceil(minY/step)*step;y<=maxY;y+=step){
    const x=80+(y-minY)/span*(W-160);
    ticks+=`<div class="tick" style="left:${x}px"><span class="tl">${y<0?Math.abs(y)+' BCE':y}</span><div class="line"></div></div>`;
  }

  // person rows
  let rows='';if(!filtered.length)filtered=DATA.persons;
  filtered.forEach(p=>{
    const by=py(p.birth_date),dy=py(p.death_date);
    if(!by)return;
    const endYear=dy||by+60;
    if(focusedQid&&p.qid!==focusedQid)return;
    const pEvents=DATA.events.filter(e=>e.person_qid===p.qid);
    const pEds=(p.endeavors||[]);
    const isFocused=focusedQid===p.qid;
    const RH=isFocused?ROW_E:ROW_N;
    const x1=80+(by-minY)/span*(W-160);
    const x2=80+(endYear-minY)/span*(W-160);
    const roleClass=p.role||'中性';
    let track=`<div class="lifespan" style="left:${x1}px;width:${Math.max(4,x2-x1)}px;background:var(--accent)"></div>`;

    if(isFocused&&pEds.length){
      // focused: endeavor bars + phases + events
      const edColors={'军事/政治':'#8b4513','政治/军事':'#8b4513','政治':'#2e8b57','军事':'#8b0000','科学':'#4169e1','文化':'#8b4513','文化/政治':'#6b4226','航海/外交':'#2e8b57','艺术/科学':'#9370db','商业/技术':'#daa520','思想':'#8b0000'};
      pEds.forEach((ed,ei)=>{
        const esy=py(ed.start_date),eey=py(ed.end_date);if(!esy||!eey)return;
        const ex1=80+(esy-minY)/span*(W-160);
        const ex2=80+(eey-minY)/span*(W-160);
        const color=edColors[ed.domain]||'var(--accent)';
        const barTop=12+ei*40;
        track+=`<div style="position:absolute;left:${ex1}px;top:${barTop}px;width:${Math.max(12,ex2-ex1)}px;height:24px;border-radius:5px;background:${color};opacity:.18"></div>`;
        track+=`<div style="position:absolute;left:${ex1+4}px;top:${barTop+2}px;font-size:11px;font-weight:bold;color:${color};white-space:nowrap;max-width:${Math.max(80,ex2-ex1-8)}px;overflow:hidden;text-overflow:ellipsis" title="${ed.title_zh}">${ed.title_zh}</div>`;
        track+=`<div style="position:absolute;left:${ex2+4}px;top:${barTop+5}px;font-size:9px;color:var(--mist)">${ed.start_date||'?'}→${ed.end_date||'?'}</div>`;
        if(ed.phases&&ed.phases.length){
          ed.phases.forEach((ph,pi)=>{
            const psy=py(ph.start_date)||esy,pey=py(ph.end_date)||eey;
            const phx1=80+(psy-minY)/span*(W-160);
            const phx2=80+(pey-minY)/span*(W-160);
            const phTop=barTop+18+pi*5;
            track+=`<div style="position:absolute;left:${phx1}px;top:${phTop}px;width:${Math.max(4,phx2-phx1)}px;height:4px;border-radius:2px;background:${color};opacity:.5" title="${ph.name}: ${ph.highlight||''}"></div>`;
            if(phx2-phx1>40)track+=`<div style="position:absolute;left:${phx1+2}px;top:${phTop-10}px;font-size:9px;color:${color};white-space:nowrap">${ph.name} ${ph.start_date||''}~${ph.end_date||''}</div>`;
            if(ph.highlight&&phx2-phx1>80)track+=`<div style="position:absolute;left:${(phx1+phx2)/2}px;top:${phTop-20}px;font-size:8px;color:var(--gold);white-space:nowrap;transform:translateX(-50%);font-style:italic">${ph.highlight}</div>`;
          });
        }
        pEvents.filter(ev=>{const ey=py(ev.date);if(!ey)return false;return esy<=ey&&ey<=eey}).forEach(ev=>{
          const ey=py(ev.date);if(!ey)return;
          const ex=80+(ey-minY)/span*(W-160);
          const age=ageAt(by,ey);
          const cls=ev.is_highlight?'highlight':ev.event_type==='出生'?'birth':ev.event_type==='逝世'?'death':'normal';
          const evTop=barTop+16;
          track+=`<div class="ev-dot ${cls}" style="left:${ex}px;top:${evTop}px;width:${ev.is_highlight?12:8}px;height:${ev.is_highlight?12:8}px;transform:translateX(-50%)" data-qid="${p.qid}" data-date="${ev.date}" data-title="${ev.title_zh||''}" data-place="${ev.place_name||''}" data-desc="${(ev.description||ev.description_zh||'').replace(/"/g,'&quot;')}" data-hl="${ev.highlight_note||''}" data-age="${age??''}" data-type="${ev.highlight_type||ev.event_type||''}"></div>`;
          if(ev.title_zh){
            track+=`<div style="position:absolute;left:${ex+8}px;top:${evTop-2}px;font-size:9px;color:var(--ink);white-space:nowrap;max-width:160px;overflow:hidden;text-overflow:ellipsis" title="${ev.title_zh}">${ev.title_zh}</div>`;
            track+=`<div style="position:absolute;left:${ex+8}px;top:${evTop+10}px;font-size:8px;color:var(--mist)">${ev.date||''} ${age?age+'岁':''} ${ev.place_name||''}</div>`;
          }
        });
      });
    }else{
      // compact: all events as dots along lifespan, highlighted ones bigger
      pEvents.forEach(ev=>{
        const ey=py(ev.date);if(!ey)return;
        const ex=80+(ey-minY)/span*(W-160);
        const age=ageAt(by,ey);
        const cls=ev.is_highlight?'highlight':ev.event_type==='出生'?'birth':ev.event_type==='逝世'?'death':'normal';
        track+=`<div class="ev-dot ${cls}" style="left:${ex}px" data-qid="${p.qid}" data-date="${ev.date}" data-title="${ev.title_zh||''}" data-place="${ev.place_name||''}" data-desc="${(ev.description||ev.description_zh||'').replace(/"/g,'&quot;')}" data-hl="${ev.highlight_note||''}" data-age="${age??''}" data-type="${ev.highlight_type||ev.event_type||''}"></div>`;
        // show title on highlighted events and birth/death
        if((ev.is_highlight||ev.event_type==='出生'||ev.event_type==='逝世')&&ev.title_zh){
          track+=`<div class="ev-title" style="left:${ex}px">${ev.title_zh}</div>`;
          track+=`<div class="ev-age" style="left:${ex}px">${age!==null?age+'岁':''}</div>`;
        }
      });
    }
    rows+=`<div class="p-row" data-qid="${p.qid}" style="height:${RH}px"><div class="p-label" onclick="focusPerson('${p.qid}')"><span class="dot ${roleClass}"></span>${p.name_zh}<span class="arch">${p.archetype||''}</span>${pEds.length?`<span style="font-size:8px;color:var(--gold);margin-left:auto">${isFocused?'▾':'▸'}${pEds.length}事</span>`:''}</div><div class="p-track" style="width:${W-LABEL_W}px">${track}</div></div>`;
  });

  inner.innerHTML=`<div class="axis-row" style="width:${W}px">${ticks}</div>${rows}`;
  inner.style.width=W+'px';
  const totalH=32+filtered.reduce((s,p)=>{const by=py(p.birth_date);if(!by)return s;if(focusedQid&&p.qid!==focusedQid)return s;return s+(focusedQid===p.qid?ROW_E:ROW_N)},0);
  inner.style.height=totalH+'px';

  const zEl=document.getElementById('zoomLevel');
  if(focusedQid){const fp=DATA.persons.find(p=>p.qid===focusedQid);zEl.textContent=`聚焦 ${fp?.name_zh||''}`;zEl.style.color='var(--accent)'}
  else{zEl.textContent=`${zoomLevel.toFixed(1)}x (${Math.round(span)}年)`;zEl.style.color='var(--mist)'}

  const tip=document.getElementById('tip');
  inner.querySelectorAll('.ev-dot').forEach(d=>{
    d.addEventListener('mouseenter',()=>{
      let t=`<div class="t-name">${d.dataset.title}</div><div class="t-date">${d.dataset.date}</div>`;
      if(d.dataset.age&&d.dataset.age!=='')t+=`<div class="t-age">${d.dataset.age}岁</div>`;
      if(d.dataset.place)t+=`<div class="t-place">📍 ${d.dataset.place}</div>`;
      if(d.dataset.desc)t+=`<div class="t-desc">${d.dataset.desc}</div>`;
      if(d.dataset.hl)t+=`<div class="t-hl">★ ${d.dataset.hl}</div>`;
      tip.innerHTML=t;tip.style.display='block';
    });
    d.addEventListener('mousemove',e=>{tip.style.left=(e.clientX+12)+'px';tip.style.top=(e.clientY-8)+'px'});
    d.addEventListener('mouseleave',()=>{tip.style.display='none'});
  });
}

function focusPerson(qid){focusedQid=focusedQid===qid?null:qid;renderTimeline()}
function showDetail(qid){
  const p=DATA.persons.find(x=>x.qid===qid);if(!p)return;
  const el=document.getElementById('dc');
  let h=`<h3>${p.name_zh} ${p.archetype?'<span style="color:var(--jade);font-size:12px">'+p.archetype+'</span>':''}</h3>`;
  h+=`<div style="font-size:11px;color:var(--mist)">${p.era||''} · ${p.birth_date||'?'} → ${p.death_date||'?'}</div>`;
  if(p.summary_first_person)h+=`<div class="fp">"${p.summary_first_person}"</div>`;
  if(p.summary_zh)h+=`<div style="margin-bottom:10px">${p.summary_zh}</div>`;
  if(p.lesson)h+=`<div style="color:var(--accent);margin-bottom:10px">💡 ${p.lesson}</div>`;
  if(p.endeavors&&p.endeavors.length){
    h+=`<div class="section"><h3>成事儿周期</h3>`;
    p.endeavors.forEach(ed=>{
      h+=`<div class="ph"><b>${ed.title_zh}</b> <span style="color:var(--mist)">${ed.start_date||'?'}→${ed.end_date||'?'}</span>`;
      if(ed.phases&&ed.phases.length)ed.phases.forEach(ph=>{h+=`<div>· ${ph.name} <span style="color:var(--mist)">${ph.start_date||''}~${ph.end_date||''} ${ph.place||''}</span>`;if(ph.highlight)h+=`<span class="hl"> ${ph.highlight}</span>`;h+=`</div>`});
      if(ed.outcome)h+=`<div style="color:var(--jade)">结果: ${ed.outcome}</div>`;
      if(ed.lesson)h+=`<div style="color:var(--accent);font-size:11px">启发: ${ed.lesson}</div>`;
      h+=`</div>`;
    });
    h+=`</div>`;
  }
  if(p.highlights&&p.highlights.length){
    h+=`<div class="section"><h3>名场面</h3>`;
    p.highlights.forEach(hl=>{const col=HL_COLORS[hl.highlight_type]||'var(--gold)';h+=`<div><span class="hl-tag" style="background:${col}">${hl.highlight_type||''}</span>${hl.title_zh} <span style="color:var(--mist)">${hl.date||''} ${hl.place_name||''}</span>`;if(hl.highlight_note)h+=`<div style="font-style:italic;color:var(--gold);font-size:11px">${hl.highlight_note}</div>`;h+=`</div>`});
    h+=`</div>`;
  }
  el.innerHTML=h;document.getElementById('detail').classList.add('open');
}
function closeDetail(){document.getElementById('detail').classList.remove('open')}
document.addEventListener('keydown',e=>{if(e.key==='Escape'){if(focusedQid){focusedQid=null;renderTimeline()}else{closeDetail()}}});
(function(){const el=document.getElementById('wrap');let d=false,sx,sl;
el.addEventListener('mousedown',e=>{d=true;sx=e.pageX-el.offsetLeft;sl=el.scrollLeft});
el.addEventListener('mouseleave',()=>d=false);el.addEventListener('mouseup',()=>d=false);
el.addEventListener('mousemove',e=>{if(!d)return;e.preventDefault();el.scrollLeft=sl-(e.pageX-el.offsetLeft-sx)*1.5});})();
init();
