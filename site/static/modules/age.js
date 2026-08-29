// age.js — 固定右侧面板的同期年龄，不写到每行名字旁
import { parseYear, ageAt } from './data.js';

let panel=null;

export function initAge(){
  panel = document.getElementById('agePanel');
  if(!panel){
    panel = document.createElement('div');
    panel.id='agePanel';
    panel.className='age-panel';
    panel.setAttribute('role','complementary');
    panel.setAttribute('aria-label','同期年龄');
    document.body.appendChild(panel);
  }
}

export function showAge(evtDateStr, persons, activeQid){
  if(!panel) initAge();
  const y = parseYear(evtDateStr);
  if(y==null){ hideAge(); return; }
  const rows = persons.map(p=>{
    const by=parseYear(p.birth_date), dy=parseYear(p.death_date);
    const a = ageAt(by,y);
    const alive = by!=null && (dy==null || y<=dy) && a!==null && a>=-50;
    return {p, by, dy, a, alive, isMe: p.qid===activeQid};
  }).filter(r=> r.alive && r.a!==null && r.a<150)
    .sort((a,b)=> b.a - a.a); // 年长在前

  if(!rows.length){ hideAge(); return; }

  const html = `<h4>${escapeHtml(evtDateStr)} · 同期 ${rows.length} 人存活</h4>` +
    rows.map(r=>{
      const cls = r.isMe ? 'yr me alive' : (r.alive? 'yr alive':'yr dead');
      const ageTxt = r.a<0 ? Math.abs(r.a)+'年前' : r.a+'岁';
      return `<div class="${cls}"><span class="nm">${escapeHtml(r.p.name_zh)}</span><span class="age">${ageTxt}</span><span class="era">${escapeHtml(r.p.era||'')}</span></div>`;
    }).join('') +
    `<div style="margin-top:8px;font-size:10px;color:var(--mist)">以事件年份减去生年计算；负数为未出生。</div>`;
  panel.innerHTML = html;
  panel.classList.add('open');
}

export function hideAge(){
  if(panel) panel.classList.remove('open');
}

function escapeHtml(s){ return String(s||'').replace(/[&<>"]/g,c=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
