let DATA={persons:[],events:[],highlights:[]};
let activeRole=null,filtered=[];

function py(s){if(!s)return null;const m=s.replace(/约/g,'').match(/^-?\d+/);return m?parseInt(m[0]):null}
function ageAt(b,y){return b&&y?y-b:null}
function poicare(t,k=2.2){return(Math.tanh(k*(t*2-1))/Math.tanh(k)+1)/2}
const HL_COLORS={'成语':'var(--c-成语)','代表作':'var(--c-代表作)','战役':'var(--c-战役)','决策':'var(--c-决策)','至暗时刻':'var(--c-至暗时刻)','名言':'var(--c-名言)','发明':'var(--c-发明)','制度':'var(--c-制度)','演讲':'var(--c-演讲)','奖项':'var(--c-奖项)','远航':'var(--c-远航)'};

async function fetchJSON(url){
  const r=await fetch(url+'?'+Date.now());
  if(!r.ok)throw new Error(`${url} ${r.status}`);
  return r.json();
}
async function fetchText(url){
  const r=await fetch(url+'?'+Date.now());
  if(!r.ok)throw new Error(`${url} ${r.status}`);
  return r.text();
}

async function init(){
  try{
    DATA.index=await fetchJSON('data/index.json');
    // load person files from year_dir
    for(const p of DATA.index.persons){
      try{
        const d=await fetchJSON(`data/${p.year_dir}/${p.name_zh}.yaml`);
        DATA.persons.push(d);
      }catch(e){console.warn('skip',p.name_zh,e.message)}
    }
    // load events from JSONL
    const text=await fetchText('data/timeline.jsonl');
    DATA.events=text.trim().split('\n').filter(Boolean).map(l=>JSON.parse(l));
    DATA.highlights=await fetchJSON('data/highlights.json');
    DATA.events.sort((a,b)=>(a.date||'9999').localeCompare(b.date||'9999'));
    document.getElementById('stats').innerHTML=
      `${DATA.persons.length}人物 · ${DATA.events.length}事件 · ${DATA.highlights.length}名场面`;
    renderFilters();applyFilter();
  }catch(e){
    console.error('init failed',e);
    document.getElementById('stats').innerHTML='加载失败: '+e.message;
  }
}

function renderFilters(){
  const roles=[...new Set(DATA.persons.map(p=>p.role).filter(Boolean))];
  let h='<label>角色:</label>';
  roles.forEach(r=>{h+=`<button class="fb" data-role="${r}">${r}</button>`});
  h+=`<button class="fb active" data-role="all" style="margin-left:8px">全部</button>`;
  document.getElementById('filters').innerHTML=h;
  document.querySelectorAll('.fb').forEach(b=>{b.addEventListener('click',()=>{
    if(b.dataset.role){activeRole=b.dataset.role==='all'?null:b.dataset.role;document.querySelectorAll('.fb[data-role]').forEach(x=>x.classList.remove('active'));b.classList.add('active')}
    applyFilter();
  })});
}

function applyFilter(){
  filtered=DATA.persons.filter(p=>{if(activeRole&&p.role!==activeRole)return false;return true});
  renderTimeline();
}

function renderTimeline(){
  const inner=document.getElementById('inner');
  const allYears=[...DATA.events.map(e=>py(e.date)),...DATA.highlights.map(h=>py(h.date))].filter(Boolean);
  if(!allYears.length)return;
  const minY=Math.min(...allYears),maxY=Math.max(...allYears);
  const span=maxY-minY||100;
  const W=Math.max(2400,span*2);
  const LH=42,RH=50,LABEL_W=160;

  const step=span>2000?500:span>500?100:span>100?20:10;
  let ticks='';
  for(let y=Math.ceil(minY/step)*step;y<=maxY;y+=step){
    const x=80+poicare((y-minY)/span)*(W-160);
    ticks+=`<div class="tick" style="left:${x}px"><span class="tl">${y<0?Math.abs(y)+' BCE':y}</span><div class="line"></div></div>`;
  }

  //名场面轨道
  let hlRow=`<div class="hl-row" style="width:${W}px"><div class="hl-label">名场面</div><div class="hl-track">`;
  DATA.highlights.forEach(h=>{
    const hy=py(h.date);if(!hy)return;
    const hx=80+poicare((hy-minY)/span)*(W-160);
    const col=HL_COLORS[h.highlight_type]||'var(--gold)';
    const pname=DATA.index.persons.find(p=>p.qid===h.person_qid)?.name_zh||'';
    hlRow+=`<div class="hl-dot" style="left:${hx}px;background:${col};width:12px;height:12px;top:15px" data-qid="${h.person_qid}" data-date="${h.date}" data-title="${h.title_zh}" data-type="${h.highlight_type||''}" data-note="${h.highlight_note||''}" data-person="${pname}"><div class="lbl" style="color:${col}">${h.title_zh}</div></div>`;
  });
  hlRow+=`</div></div>`;

  let rows='';
  if(!filtered.length)filtered=DATA.persons;
  filtered.forEach(p=>{
    const by=py(p.birth_date),dy=py(p.death_date);
    if(!by)return;
    const endYear=dy||by+80;
    const pEvents=DATA.events.filter(e=>e.person_qid===p.qid);
    const pEds=(p.endeavors||[]);
    const x1=80+poicare((by-minY)/span)*(W-160);
    const x2=80+poicare((endYear-minY)/span)*(W-160);
    const roleClass=p.role||'中性';
    let track=`<div class="lifespan" style="left:${x1}px;width:${Math.max(4,x2-x1)}px;background:var(--accent)"></div>`;
    const edColors={'军事/政治':'#8b4513','政治/军事':'#8b4513','政治':'#2e8b57','军事':'#8b0000','科学':'#4169e1','文化':'#8b4513','文化/政治':'#6b4226','航海/外交':'#2e8b57','艺术/科学':'#9370db','商业/技术':'#daa520','思想':'#8b0000'};
    pEds.forEach((ed,ei)=>{
      const esy=py(ed.start_date),eey=py(ed.end_date);if(!esy||!eey)return;
      const ex1=80+poicare((esy-minY)/span)*(W-160);
      const ex2=80+poicare((eey-minY)/span)*(W-160);
      track+=`<div style="position:absolute;left:${ex1}px;top:calc(var(--row-h)/2+${14+ei*6}px);width:${Math.max(2,ex2-ex1)}px;height:4px;border-radius:2px;background:${edColors[ed.domain]||'var(--accent)'};opacity:.18" title="${ed.title_zh}"></div>`;
    });
    pEvents.forEach(ev=>{
      const ey=py(ev.date);if(!ey)return;
      const ex=80+poicare((ey-minY)/span)*(W-160);
      const age=ageAt(by,ey);
      const cls=ev.is_highlight?'highlight':ev.event_type==='出生'?'birth':ev.event_type==='逝世'?'death':'normal';
      track+=`<div class="ev-dot ${cls}" style="left:${ex}px" data-qid="${p.qid}" data-date="${ev.date}" data-title="${ev.title_zh||''}" data-place="${ev.place_name||''}" data-desc="${(ev.description||ev.description_zh||'').replace(/"/g,'&quot;')}" data-hl="${ev.highlight_note||''}" data-age="${age??''}" data-type="${ev.highlight_type||ev.event_type||''}"></div>`;
      if(age!==null&&age>=0&&ev.title_zh){track+=`<div class="ev-title" style="left:${ex}px">${ev.title_zh}</div>`;track+=`<div class="ev-age" style="left:${ex}px">${age}岁</div>`}
    });
    rows+=`<div class="p-row" data-qid="${p.qid}" style="height:${RH}px"><div class="p-label" onclick="showDetail('${p.qid}')"><span class="dot ${roleClass}"></span>${p.name_zh}<span class="arch">${p.archetype||''}</span></div><div class="p-track" style="width:${W-LABEL_W}px">${track}</div></div>`;
  });

  inner.innerHTML=`<div class="axis-row" style="width:${W}px">${ticks}</div>${hlRow}${rows}`;
  inner.style.width=W+'px';
  inner.style.height=(32+LH+filtered.length*RH)+'px';

  const tip=document.getElementById('tip');
  inner.querySelectorAll('.ev-dot,.hl-dot').forEach(d=>{
    d.addEventListener('mouseenter',()=>{
      let t='';
      if(d.classList.contains('hl-dot')){
        t=`<div class="t-name">${d.dataset.title}</div><div class="t-date">${d.dataset.date}</div><div class="t-name" style="color:var(--jade);font-size:11px">${d.dataset.person}</div><div class="t-hl">${d.dataset.type} · ${d.dataset.note}</div>`;
      }else{
        t=`<div class="t-name">${d.dataset.title}</div><div class="t-date">${d.dataset.date}</div>`;
        if(d.dataset.age&&d.dataset.age!=='')t+=`<div class="t-age">${d.dataset.age}岁</div>`;
        if(d.dataset.place)t+=`<div class="t-place">📍 ${d.dataset.place}</div>`;
        if(d.dataset.desc)t+=`<div class="t-desc">${d.dataset.desc}</div>`;
        if(d.dataset.hl)t+=`<div class="t-hl">★ ${d.dataset.hl}</div>`;
      }
      tip.innerHTML=t;tip.style.display='block';
    });
    d.addEventListener('mousemove',e=>{tip.style.left=(e.clientX+12)+'px';tip.style.top=(e.clientY-8)+'px'});
    d.addEventListener('mouseleave',()=>{tip.style.display='none'});
    if(d.classList.contains('hl-dot')){
      d.addEventListener('click',()=>{
        const row=document.querySelector(`.p-row[data-qid="${d.dataset.qid}"]`);
        if(row)row.scrollIntoView({behavior:'smooth',block:'center'});
      });
    }
  });
}

function showDetail(qid){
  const p=DATA.persons.find(x=>x.qid===qid);if(!p)return;
  const el=document.getElementById('dc');
  let h=`<h3>${p.name_zh} ${p.archetype?'<span style="color:var(--jade);font-size:12px">'+p.archetype+'</span>':''}</h3>`;
  h+=`<div style="font-size:11px;color:var(--mist)">${p.era||''} · ${p.birth_date||'?'} → ${p.death_date||'?'}</div>`;
  if(p.summary_first_person)h+=`<div class="fp">"${p.summary_first_person}"</div>`;
  if(p.summary_zh)h+=`<div style="margin-bottom:10px">${p.summary_zh}</div>`;
  if(p.lesson)h+=`<div style="color:var(--accent);margin-bottom:10px">💡 ${p.lesson}</div>`;
  if(p.dilemmas&&p.dilemmas.length)h+=`<div style="margin-bottom:10px"><b>境遇:</b> ${p.dilemmas.join(' / ')}</div>`;
  if(p.endeavors&&p.endeavors.length){
    h+=`<div class="section"><h3>成事儿周期</h3>`;
    p.endeavors.forEach(ed=>{
      h+=`<div class="ph"><b>${ed.title_zh}</b> <span style="color:var(--mist)">${ed.start_date||'?'}→${ed.end_date||'?'}</span>`;
      if(ed.description_zh)h+=`<div style="font-style:italic;margin:4px 0">${ed.description_zh}</div>`;
      if(ed.phases&&ed.phases.length)ed.phases.forEach(ph=>{h+=`<div>· ${ph.name} <span style="color:var(--mist)">${ph.start_date||''}~${ph.end_date||''} ${ph.place||''}</span>`;if(ph.highlight)h+=`<span class="hl"> ${ph.highlight}</span>`;h+=`</div>`});
      if(ed.outcome)h+=`<div style="color:var(--jade)">结果: ${ed.outcome}</div>`;
      if(ed.lesson)h+=`<div style="color:var(--accent);font-size:11px">启发: ${ed.lesson}</div>`;
      h+=`</div>`;
    });
    h+=`</div>`;
  }
  if(p.highlights&&p.highlights.length){
    h+=`<div class="section"><h3>名场面</h3>`;
    p.highlights.forEach(hl=>{
      const col=HL_COLORS[hl.highlight_type]||'var(--gold)';
      h+=`<div><span class="hl-tag" style="background:${col}">${hl.highlight_type||''}</span>${hl.title_zh} <span style="color:var(--mist)">${hl.date||''} ${hl.place_name||''}</span>`;
      if(hl.highlight_note)h+=`<div style="font-style:italic;color:var(--gold);font-size:11px">${hl.highlight_note}</div>`;
      h+=`</div>`;
    });
    h+=`</div>`;
  }
  el.innerHTML=h;
  document.getElementById('detail').classList.add('open');
}
function closeDetail(){document.getElementById('detail').classList.remove('open')}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeDetail()});

// drag scroll
(function(){const el=document.getElementById('wrap');let d=false,sx,sl;
el.addEventListener('mousedown',e=>{d=true;sx=e.pageX-el.offsetLeft;sl=el.scrollLeft});
el.addEventListener('mouseleave',()=>d=false);el.addEventListener('mouseup',()=>d=false);
el.addEventListener('mousemove',e=>{if(!d)return;e.preventDefault();el.scrollLeft=sl-(e.pageX-el.offsetLeft-sx)*1.5});})();

init();
