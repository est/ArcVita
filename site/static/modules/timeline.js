// timeline.js — 渲染引擎：虚拟化 + LOD + DocumentFragment + RAF + 事件委托
import { DATA, parseYear, ageAt } from './data.js';
import { BASE_PX, ppx, tickStep, yearToX, computeSpan } from './scale.js';
import { focusedQid, shouldDim } from './focus.js';
import { showTip, hideTip, moveTip, buildTipFromDataset } from './tip.js';
import { showAge, hideAge } from './age.js';

let inner, wrap;
let lastFiltered=[];
let minY=0, maxY=1;
let zoomLevel=1;
let rafId=0;
let pendingRender=null;

// density threshold
function shouldCluster(zoom){
  return zoom < 0.9;
}

export function initTimeline(){
  inner=document.getElementById('inner');
  wrap=document.getElementById('wrap');
  // 事件委托：tooltip + age
  inner.addEventListener('mouseover', onHover);
  inner.addEventListener('mouseout', onLeave);
  inner.addEventListener('mousemove', e=>{
    if(e.target.closest('.ev-dot')) moveTip(e.clientX, e.clientY);
  });
  // 点击聚焦
  inner.addEventListener('click', e=>{
    const label = e.target.closest('.p-label');
    if(label){
      const qid = label.closest('.p-row')?.dataset.qid;
      if(qid) document.dispatchEvent(new CustomEvent('arcvita:focus',{detail:{qid}}));
    }
    const dot=e.target.closest('.ev-dot');
    if(dot){
      const qid=dot.dataset.qid;
      if(qid) showDetail(qid);
    }
  });
  // 拖拽滚动
  let dragging=false, sx=0, sl=0;
  wrap.addEventListener('mousedown',e=>{ dragging=true; sx=e.pageX - wrap.offsetLeft; sl=wrap.scrollLeft; });
  wrap.addEventListener('mouseleave',()=> dragging=false);
  wrap.addEventListener('mouseup',()=> dragging=false);
  wrap.addEventListener('mousemove',e=>{
    if(!dragging) return;
    e.preventDefault();
    wrap.scrollLeft = sl - (e.pageX - wrap.offsetLeft - sx)*1.3;
  });
  // 触摸
  wrap.addEventListener('touchstart',e=>{
    if(e.touches.length===1){ sx=e.touches[0].pageX; sl=wrap.scrollLeft; }
  },{passive:true});
  wrap.addEventListener('touchmove',e=>{
    if(e.touches.length===1){ wrap.scrollLeft = sl - (e.touches[0].pageX - sx); }
  },{passive:true});
}

function onHover(e){
  const dot=e.target.closest('.ev-dot');
  if(!dot) return;
  const html=buildTipFromDataset(dot.dataset);
  showTip(html);
  showAge(dot.dataset.date, lastFiltered, dot.dataset.qid);
  // 不要再写每行 age 文本
  moveTip(e.clientX, e.clientY);
}
function onLeave(e){
  const to = e.relatedTarget;
  if(to && to.closest && to.closest('.ev-dot')) return;
  hideTip();
  hideAge();
}

export function setZoom(z){ zoomLevel=z; schedule(); }
export function getZoom(){ return zoomLevel; }

export function scheduleRender(filtered, newMinY, newMaxY){
  pendingRender={filtered, minY:newMinY, maxY:newMaxY};
  if(rafId) return;
  rafId=requestAnimationFrame(()=>{
    rafId=0;
    if(pendingRender){
      doRender(pendingRender.filtered, pendingRender.minY, pendingRender.maxY);
      pendingRender=null;
    }
  });
}
function schedule(){ if(lastFiltered) scheduleRender(lastFiltered, minY, maxY); }

export function doRender(filtered, nMinY, nMaxY){
  lastFiltered=filtered;
  minY=nMinY; maxY=nMaxY;
  const span=computeSpan(minY,maxY);
  const ppxVal = ppx(zoomLevel);
  const W = Math.max(900, span*ppxVal + 160);
  const ROW_N=50, ROW_F=160;
  // ticks
  const step=tickStep(span, ppxVal);
  let ticksHTML='';
  for(let y=Math.ceil(minY/step)*step; y<=maxY; y+=step){
    const x=yearToX(y, minY, span, W);
    ticksHTML+=`<div class="tick" style="left:${x}px"><span class="tl">${y<0? Math.abs(y)+' BCE': y}</span><div class="line"></div></div>`;
  }
  // 虚拟化：视口+-1屏 (按 scrollTop 估算行索引)
  const viewportH = wrap.clientHeight - 32;
  const scrollTop = wrap.scrollTop;
  const startIdx = Math.max(0, Math.floor(scrollTop / 50)-8);
  const visibleCount = Math.ceil(viewportH/50)+16;
  const endIdx = Math.min(filtered.length, startIdx + visibleCount);
  // 决定显示哪些行：聚焦时仍显示全部但 dim，其余虚拟化
  let rowsToRender;
  if(focusedQid){
    rowsToRender = filtered; // 保留上下文，全显但 dim
  } else {
    rowsToRender = filtered.slice(startIdx, endIdx);
  }

  const frag=document.createDocumentFragment();
  const container=document.createElement('div');
  container.style.width=W+'px';

  // axis
  const axis=document.createElement('div');
  axis.className='axis-row';
  axis.style.width=W+'px';
  axis.innerHTML=ticksHTML;
  container.appendChild(axis);

  // 为虚拟化占位：顶部空白
  if(!focusedQid && startIdx>0){
    const spacer=document.createElement('div');
    spacer.style.height=(startIdx*ROW_N)+'px';
    container.appendChild(spacer);
  }

  // rows
  for(const p of rowsToRender){
    const by=parseYear(p.birth_date), dy=parseYear(p.death_date);
    if(by==null) continue;
    const endY = dy || (by+60);
    const isF = focusedQid===p.qid;
    const dim = shouldDim(p.qid);
    const RH = isF? ROW_F: ROW_N;
    const x1=yearToX(by, minY, span, W);
    const x2=yearToX(endY, minY, span, W);
    const roleClass=p.role||'中性';
    const row=document.createElement('div');
    row.className='p-row'+(dim?' dim':'')+(isF?' focused':'');
    row.dataset.qid=p.qid;
    row.style.height=RH+'px';
    row.setAttribute('tabindex','0');
    row.setAttribute('role','row');
    // label
    const label=document.createElement('div');
    label.className='p-label';
    label.style.height=RH+'px';
    const dotCls = `dot ${roleClass}`;
    label.innerHTML=`<span class="${dotCls}"></span><span class="p-name" title="${escapeHtml(p.name_zh)}">${escapeHtml(p.name_zh)}</span><span class="arch">${escapeHtml(p.archetype||'')}</span>${(p.endeavors||[]).length?`<span style="font-size:8px;color:var(--gold);margin-left:auto">${isF?'▾':'▸'}${p.endeavors.length}事</span>`:''}`;
    row.appendChild(label);
    // track
    const track=document.createElement('div');
    track.className='p-track';
    track.style.width=(W-168)+'px';
    track.style.height=RH+'px';
    // lifespan
    const ls=document.createElement('div');
    ls.className='lifespan';
    ls.style.left=x1+'px';
    ls.style.width=Math.max(4,x2-x1)+'px';
    track.appendChild(ls);

    // endeavors expanded when focused
    if(isF && (p.endeavors||[]).length){
      const edColors={'军事/政治':'#8b4513','政治/军事':'#8b4513','政治':'#2e8b57','军事':'#8b0000','科学':'#4169e1','文化':'#8b4513','航海/外交':'#2e8b57','艺术/科学':'#9370db','商业/技术':'#daa520','思想':'#8b0000'};
      (p.endeavors||[]).forEach((ed,ei)=>{
        const esy=parseYear(ed.start_date), eey=parseYear(ed.end_date); if(esy==null||eey==null) return;
        const ex1=yearToX(esy,minY,span,W), ex2=yearToX(eey,minY,span,W);
        const color=edColors[ed.domain]||'var(--accent)';
        const barTop=14+ei*34;
        const bar=document.createElement('div');
        bar.className='focus-endeavor-bar';
        bar.style.left=ex1+'px'; bar.style.top=barTop+'px'; bar.style.width=Math.max(18,ex2-ex1)+'px'; bar.style.background=color;
        track.appendChild(bar);
        const lbl=document.createElement('div');
        lbl.className='focus-endeavor-label';
        lbl.style.left=(ex1+4)+'px'; lbl.style.top=(barTop+2)+'px'; lbl.style.color=color; lbl.style.maxWidth=Math.max(80,ex2-ex1-8)+'px';
        lbl.textContent=ed.title_zh;
        track.appendChild(lbl);
        const dates=document.createElement('div');
        dates.style.position='absolute'; dates.style.left=(ex2+4)+'px'; dates.style.top=(barTop+5)+'px'; dates.style.fontSize='9px'; dates.style.color='var(--mist)';
        dates.textContent=(ed.start_date||'?')+'→'+(ed.end_date||'?');
        track.appendChild(dates);
        // phases
        if(ed.phases) ed.phases.forEach((ph,pi)=>{
          const psy=parseYear(ph.start_date)||esy, pey=parseYear(ph.end_date)||eey;
          const phx1=yearToX(psy,minY,span,W), phx2=yearToX(pey,minY,span,W);
          const phTop=barTop+18+pi*4;
          const phEl=document.createElement('div');
          phEl.className='focus-phase';
          phEl.style.left=phx1+'px'; phEl.style.top=phTop+'px'; phEl.style.width=Math.max(4,phx2-phx1)+'px'; phEl.style.background=color;
          phEl.title=`${ph.name}: ${ph.highlight||''}`;
          track.appendChild(phEl);
        });
        // events inside endeavor when focused
        (p.events||[]).filter(ev=>{ const ey=parseYear(ev.date); return ey!=null && esy<=ey && ey<=eey; }).forEach(ev=>{
          const ey=parseYear(ev.date); if(ey==null) return;
          const ex=yearToX(ey,minY,span,W), age=ageAt(by,ey);
          const cls=ev.is_highlight?'highlight':ev.event_type==='出生'?'birth':ev.event_type==='逝世'?'death':'normal';
          const dot=makeDot(ev, ex, cls, age, 14+16);
          track.appendChild(dot.el);
          if(ev.title_zh){
            const t1=document.createElement('div');
            t1.style.position='absolute'; t1.style.left=(ex+8)+'px'; t1.style.top=(14+14)+'px'; t1.style.fontSize='9px'; t1.style.color='var(--ink)'; t1.style.whiteSpace='nowrap'; t1.style.maxWidth='160px'; t1.style.overflow='hidden'; t1.style.textOverflow='ellipsis';
            t1.textContent=ev.title_zh; track.appendChild(t1);
            const t2=document.createElement('div');
            t2.style.position='absolute'; t2.style.left=(ex+8)+'px'; t2.style.top=(14+24)+'px'; t2.style.fontSize='8px'; t2.style.color='var(--mist)';
            t2.textContent=`${ev.date||''} ${age!=null?age+'岁':''} ${ev.place_name||''}`; track.appendChild(t2);
          }
        });
      });
    } else {
      // normal LOD with optional clustering
      const evs = (p.events||[]).map(ev=> ({ev, x: parseYear(ev.date)!=null? yearToX(parseYear(ev.date),minY,span,W): null, y:parseYear(ev.date)} )).filter(o=>o.x!=null);
      evs.sort((a,b)=>a.x-b.x);
      const clusterThreshold = 18; // px
      const useCluster = shouldCluster(zoomLevel);
      let i=0;
      while(i<evs.length){
        const cur=evs[i];
        // 收集簇
        if(useCluster){
          const group=[cur];
          let j=i+1;
          while(j<evs.length && evs[j].x - cur.x < clusterThreshold && group.length<8){
            // 只簇 non-highlight
            if(!evs[j].ev.is_highlight && !cur.ev.is_highlight) group.push(evs[j]);
            else break;
            j++;
          }
          if(group.length>=3){
            const avgX = group.reduce((s,g)=>s+g.x,0)/group.length;
            const cdot=document.createElement('div');
            cdot.className='ev-dot cluster';
            cdot.style.left=avgX+'px';
            cdot.textContent='▸'+group.length;
            cdot.title=group.map(g=> g.ev.title_zh||g.ev.date).join(' · ');
            cdot.dataset.qid=p.qid; cdot.dataset.date=group[0].ev.date||''; cdot.dataset.title=group.length+'个事件';
            cdot.dataset.place=''; cdot.dataset.desc='点击聚焦查看详情'; cdot.dataset.hl=''; cdot.dataset.age=String(ageAt(by, group[0].y)||''); cdot.dataset.type='簇';
            track.appendChild(cdot);
            i=j; continue;
          }
        }
        const age=ageAt(by, cur.y);
        const cls=cur.ev.is_highlight?'highlight':cur.ev.event_type==='出生'?'birth':cur.ev.event_type==='逝世'?'death':'normal';
        const dot=makeDot(cur.ev, cur.x, cls, age, null);
        track.appendChild(dot.el);
        // 标题 LOD: 仅 highlight/birth/death 在 zoom>=0.8 时显示
        const showLabel = (cur.ev.is_highlight || cur.ev.event_type==='出生' || cur.ev.event_type==='逝世') && zoomLevel>=0.8;
        if(showLabel && cur.ev.title_zh){
          const t=document.createElement('div');
          t.className='ev-title'+(cur.ev.is_highlight?' hl':'');
          t.style.left=cur.x+'px';
          t.textContent=cur.ev.title_zh;
          track.appendChild(t);
          if(age!=null){
            const aEl=document.createElement('div');
            aEl.className='ev-age'; aEl.style.left=cur.x+'px'; aEl.textContent=age+'岁';
            track.appendChild(aEl);
          }
        }
        i++;
      }
    }

    row.appendChild(track);
    container.appendChild(row);
  }

  if(!focusedQid && endIdx < filtered.length){
    const spacer=document.createElement('div');
    spacer.style.height=((filtered.length - endIdx)*ROW_N)+'px';
    container.appendChild(spacer);
  }

  frag.appendChild(container);
  // 单次写入
  inner.innerHTML='';
  inner.appendChild(frag);
  inner.style.width=W+'px';
  const totalH = 32 + (focusedQid? filtered.reduce((s,p)=> s + (p.qid===focusedQid? ROW_F: ROW_N),0) : filtered.length*ROW_N);
  inner.style.height=totalH+'px';

  // 触发可见性观察（为下一帧虚拟化准备）
  requestAnimationFrame(updateVirtualOnScroll);
}

function makeDot(ev, x, cls, age, top){
  const el=document.createElement('div');
  el.className='ev-dot '+cls;
  el.style.left=x+'px';
  if(top!=null) el.style.top=top+'px';
  el.dataset.qid=ev.person_qid||'';
  el.dataset.date=ev.date||'';
  el.dataset.title=ev.title_zh||'';
  el.dataset.place=ev.place_name||ev.place||'';
  el.dataset.desc=ev.description||ev.description_zh||'';
  el.dataset.hl=ev.highlight_note||'';
  el.dataset.age= age!=null? String(age): '';
  el.dataset.type=ev.highlight_type||ev.event_type||ev.type||'';
  el.setAttribute('role','button');
  el.setAttribute('aria-label', (ev.title_zh||'')+' '+ (ev.date||''));
  return {el};
}

function updateVirtualOnScroll(){
  // 下次滚动时重绘（节流）
  // 由外层 wrap scroll 监听触发 scheduleRender
}

function escapeHtml(s){ return String(s||'').replace(/[&<>"]/g,c=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

function showDetail(qid){
  const p=DATA.persons.find(x=>x.qid===qid);
  if(!p) return;
  const dc=document.getElementById('dc');
  const detail=document.getElementById('detail');
  let h=`<h3>${escapeHtml(p.name_zh)} ${p.archetype?'<span style="color:var(--jade);font-size:12px">'+escapeHtml(p.archetype)+'</span>':''}</h3>`;
  h+=`<div style="font-size:11px;color:var(--mist)">${escapeHtml(p.era||'')} · ${escapeHtml(p.birth_date||'?')} → ${escapeHtml(p.death_date||'?')}</div>`;
  if(p.summary_first_person) h+=`<div class="fp">"${escapeHtml(p.summary_first_person)}"</div>`;
  if(p.summary_zh) h+=`<div style="margin-bottom:10px">${escapeHtml(p.summary_zh)}</div>`;
  if(p.lesson) h+=`<div style="color:var(--accent);margin-bottom:10px">💡 ${escapeHtml(p.lesson)}</div>`;
  if(p.endeavors && p.endeavors.length){
    h+=`<div class="section"><h3>成事儿周期</h3>`;
    p.endeavors.forEach(ed=>{
      h+=`<div class="ph"><b>${escapeHtml(ed.title_zh)}</b> <span style="color:var(--mist)">${escapeHtml(ed.start_date||'?')}→${escapeHtml(ed.end_date||'?')}</span>`;
      if(ed.description_zh) h+=`<div style="font-style:italic;margin:4px 0">${escapeHtml(ed.description_zh)}</div>`;
      if(ed.phases) ed.phases.forEach(ph=>{ h+=`<div>· ${escapeHtml(ph.name)} <span style="color:var(--mist)">${escapeHtml(ph.start_date||'')}~${escapeHtml(ph.end_date||'')} ${escapeHtml(ph.place||'')}</span>`; if(ph.highlight) h+=`<span class="hl"> ${escapeHtml(ph.highlight)}</span>`; h+=`</div>`; });
      if(ed.outcome) h+=`<div style="color:var(--jade)">结果: ${escapeHtml(ed.outcome)}</div>`;
      if(ed.lesson) h+=`<div style="color:var(--accent);font-size:11px">启发: ${escapeHtml(ed.lesson)}</div>`;
      h+=`</div>`;
    });
    h+=`</div>`;
  }
  const pEvents=p.events||[];
  if(pEvents.length){
    h+=`<div class="section"><h3>事件时间线</h3>`;
    [...pEvents].sort((a,b)=>(a.date||'').localeCompare(b.date||'')).forEach(ev=>{
      const col = ev.is_highlight? 'var(--gold)':'var(--ink)';
      const hlColors={'成语':'var(--c-成语)','代表作':'var(--c-代表作)','战役':'var(--c-战役)','决策':'var(--c-决策)','至暗时刻':'var(--c-至暗时刻)','名言':'var(--c-名言)','发明':'var(--c-发明)','制度':'var(--c-制度)','演讲':'var(--c-演讲)','奖项':'var(--c-奖项)','远航':'var(--c-远航)','朝代更替':'var(--c-朝代更替)','社会变革':'var(--c-社会变革)','文化':'var(--c-文化)','王表':'var(--c-王表)'};
      h+=`<div style="padding:4px 0;border-bottom:1px solid #f5f0e8"><span style="color:${col};font-weight:${ev.is_highlight?'700':'400'}">`;
      if(ev.is_highlight && ev.highlight_type) h+=`<span class="hl-tag" style="background:${hlColors[ev.highlight_type]||'var(--gold)'};font-size:8px">${escapeHtml(ev.highlight_type)}</span> `;
      h+=`${escapeHtml(ev.title_zh||'')}</span> <span style="color:var(--mist);font-size:10px">${escapeHtml(ev.date||'')} ${escapeHtml(ev.place_name||'')}</span>`;
      if(ev.highlight_note) h+=`<div style="font-style:italic;color:var(--gold);font-size:10px;margin-top:2px">${escapeHtml(ev.highlight_note)}</div>`;
      else if(ev.description_zh) h+=`<div style="font-size:10px;color:var(--mist);margin-top:2px">${escapeHtml(ev.description_zh)}</div>`;
      h+=`</div>`;
    });
    h+=`</div>`;
  }
  dc.innerHTML=h;
  detail.classList.add('open');
}
