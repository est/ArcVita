/* ============================================================
   ArcVita · 成事儿时间轴
   签名元素：可玩 4000 年 canvas 时间轴
   数据：构建产物 site/data/（index.json + timeline.jsonl + 世纪分片）
   ============================================================ */
'use strict';

/* ---------------- 小工具 ---------------- */

const $  = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;

const esc = s => String(s ?? '')
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

/* 「约-2100」「前5」「-100-07-12」「32」→ 整数年（BCE 为负） */
function parseYear(s) {
  if (s == null) return null;
  const str = String(s);
  const m = str.match(/-?\d+/);
  if (!m) return null;
  let v = parseInt(m[0], 10);
  if (v > 0 && /前/.test(str)) v = -v;
  return v;
}

function fmtYear(y) { return y < 0 ? `前${-y}` : `${y}`; }

/* 「-210-07-10」→ 前210年7月；「-356」→ 前356 */
function fmtDate(s) {
  if (s == null) return '';
  const m = String(s).match(/^(-?\d+)(?:-(\d+))?(?:-(\d+))?/);
  if (!m) return String(s);
  const y = parseInt(m[1], 10);
  let out = fmtYear(y);
  if (m[2]) out += `年${+m[2]}月`;
  return out;
}

/* ---------------- 朝代色谱（数据编码） ---------------- */

const ERAS = [
  { f: -99999, u: -1047, name: '上古',     c: '#3FA083' },
  { f: -1046,  u: -478,  name: '西周·春秋', c: '#4E96C8' },
  { f: -477,   u: -222,  name: '战国',     c: '#D25544' },
  { f: -221,   u: -208,  name: '秦',       c: '#9B7BB8' },
  { f: -207,   u: 219,   name: '两汉',     c: '#DFA03C' },
  { f: 220,    u: 280,   name: '三国',     c: '#4E8FB0' },
  { f: 281,    u: 1911,  name: '帝制之后', c: '#B8734F' },
  { f: 1912,   u: 99999, name: '近现代',   c: '#8FA0B3' },
];

function eraOfYear(y) {
  for (const e of ERAS) if (y >= e.f && y <= e.u) return e;
  return ERAS[ERAS.length - 1];
}

const PHASE_COLORS = { '酝酿': '#7E8CA0', '破局': '#D9A441', '高潮': '#E8502F', '收束': '#3FA083' };

const JUMPS = [
  { label: '上古',     cy: -1600, ppy: 0.5 },
  { label: '春秋战国', cy: -390,  ppy: 1.3 },
  { label: '秦汉',     cy: 10,    ppy: 1.7 },
  { label: '三国',     cy: 250,   ppy: 2.4 },
  { label: '近世',     cy: 1400,  ppy: 0.42 },
];

/* ---------------- 数据 ---------------- */

let persons = [];                 // {qid,name,era,archetype,role,b,d,est,row,nw}
let events = [];                  // {qid,row,year,title,type,isHl,htype,place,desc,note}
const eventsByQ = new Map();
const centuryCache = new Map();   // century → json

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url} → HTTP ${r.status}`);
  return r.json();
}

async function loadTimelineData() {
  const [index, tlText] = await Promise.all([
    getJSON('data/index.json'),
    fetch('data/timeline.jsonl').then(r => {
      if (!r.ok) throw new Error(`timeline.jsonl → HTTP ${r.status}`);
      return r.text();
    }),
  ]);

  persons = index.persons
    .map(p => {
      const b = parseYear(p.birth_date);
      let d = parseYear(p.death_date);
      const est = d == null && b != null;
      if (est) d = b + 60;
      return { ...p, name: p.name_zh, b, d, est };
    })
    .filter(p => p.b != null)   // 生年可考即可入轴；卒年不详者以虚化尾段示之
    .sort((a, b2) => a.b - b2.b);
  persons.forEach((p, i) => { p.row = i; });

  events = tlText.trim().split('\n').map(JSON.parse)
    .map(e => {
      const row = persons.findIndex(p => p.qid === e.person_qid);
      return {
        qid: e.person_qid, row,
        year: parseYear(e.date),
        dateStr: e.date || '',
        title: e.title || '（未命名事件）',
        type: e.type || '',
        isHl: !!e.is_highlight,
        htype: e.highlight_type || '',
        place: e.place || '',
        desc: e.description || e.highlight_note || '',
        person: e.person || '',
      };
    })
    .filter(e => e.year != null && e.row >= 0)
    .sort((a, b) => a.year - b.year);

  eventsByQ.clear();
  for (const e of events) {
    if (!eventsByQ.has(e.qid)) eventsByQ.set(e.qid, []);
    eventsByQ.get(e.qid).push(e);
  }
}

/* ---------------- 时间轴画布 ---------------- */

const frame  = $('#tl-frame');
const canvas = $('#tl-canvas');
const ctx    = canvas.getContext('2d');
const popEl  = $('#tl-pop');
const panelEl = $('#tl-panel');
const statusEl = $('#tl-status');

const RULER_H = 40;
const ROW_H = 36;
const MIN_PPY = 0.09, MAX_PPY = 64;

const MIN_YEAR = -2160, MAX_YEAR = 2020;

let W = 0, H = 0, dpr = 1;
let worldH = 0;
let RAIL = 100;   // 固定人名列宽度（userstory：横向滚动时名字不消失）

const view = { x: -2050, ppy: 0.085, y: 0 };   // x：左缘年份；y：纵向滚动 px
let mode = 'rest';                              // rest | drag | inertia | tween
let tween = null;
let vel = { x: 0, y: 0 };                       // inertia：年/s 与 px/s
let needs = true;

let hover = null;          // {px, py, yr} 时间准线
let hoverDot = null;       // 命中的事件
let pinned = null;         // 钉住的事件
let focusQ = null;         // 聚焦人物 qid
let focusData = null;      // 世纪分片中的完整档案
let focusReturn = null;    // 返回概览的快照

const yearX = y => (y - view.x) * view.ppy;
const xYear = px => view.x + px / view.ppy;
const rowTop = r => RULER_H + r * ROW_H - view.y;

function resize() {
  const rect = frame.getBoundingClientRect();
  W = Math.max(280, rect.width);
  H = Math.max(320, rect.height);
  dpr = clamp(window.devicePixelRatio || 1, 1, 2);
  canvas.width = Math.round(W * dpr);
  canvas.height = Math.round(H * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  RAIL = W < 560 ? 74 : 100;
  worldH = RULER_H + persons.length * ROW_H + 26;
  clampView();
  needs = true;
}

function clampView() {
  const span = W / view.ppy;
  const over = span * 0.3;
  view.x = clamp(view.x, MIN_YEAR - over, MAX_YEAR + over - span);
  view.y = clamp(view.y, 0, Math.max(0, worldH - H));
}

function tweenTo(to, dur = 700, ease = easeInOut) {
  if (RM || dur <= 0) { Object.assign(view, to); mode = 'rest'; needs = true; return; }
  tween = { t0: performance.now(), dur, from: { ...view }, to: { ...to }, ease };
  mode = 'tween';
  needs = true;
}

const easeInOut = t => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
const easeOut = t => 1 - Math.pow(1 - t, 3);

/* ---- 绘制 ---- */

const F_NAME = '600 13px "Songti SC","Noto Serif SC","SimSun",serif';
const F_AGE  = '10.5px "SF Mono",Menlo,Consolas,monospace';
const F_TICK = '11px "SF Mono",Menlo,Consolas,monospace';
const F_ERA  = '10px "SF Mono",Menlo,Consolas,monospace';

function draw() {
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = '#16100A';
  ctx.fillRect(0, 0, W, H);

  const viewL = view.x, viewR = xYear(W);
  const spotlight = !!focusQ;

  /* ---- 内容区（固定人名列右侧，裁剪） ---- */
  ctx.save();
  ctx.beginPath();
  ctx.rect(RAIL, RULER_H, W - RAIL, H - RULER_H);
  ctx.clip();

  /* 朝代色带（颜色 = 时间） */
  for (const e of ERAS) {
    const a = Math.max(viewL, e.f), b = Math.min(viewR, e.u);
    if (a >= b) continue;
    const x0 = yearX(a), x1 = yearX(b);
    ctx.fillStyle = e.c;
    ctx.globalAlpha = 0.055;
    ctx.fillRect(x0, RULER_H, x1 - x0, H - RULER_H);
    ctx.globalAlpha = 1;
  }

  if (!persons.length) return;   // 数据未就绪（loading 期状态浮层遮盖）

  /* 可见行范围 */
  const r0 = clamp(Math.floor((view.y - RULER_H) / ROW_H), 0, persons.length - 1);
  const r1 = clamp(Math.ceil((view.y - RULER_H + H) / ROW_H), 0, persons.length - 1);

  ctx.textBaseline = 'alphabetic';

  for (let r = r0; r <= r1; r++) {
    const p = persons[r];
    const top = rowTop(r);
    const barY = top + 13;
    const focused = focusQ === p.qid;
    const barH = focused ? 12 : 8;

    /* 时间准线悬停（含事件点）时：不在场的行淡出（README：死了的不显示） */
    let alpha = 1;
    if (hover != null) {
      const yr = hover.yr;
      if (yr < p.b || yr > p.d) alpha = 0.55;
    }
    if (spotlight && !focused) alpha = Math.min(alpha, 0.25);

    const barX = yearX(p.b);

    /* 人生横条 */
    const eBar = eraOfYear(p.b);
    const bx1 = yearX(p.d);
    ctx.globalAlpha = alpha;
    ctx.fillStyle = eBar.c;
    rr(barX, barY, Math.max(3, bx1 - barX), barH, barH / 2);
    if (p.est) {   // 卒年不详：尾段虚化
      ctx.globalAlpha = alpha * 0.35;
      rr(bx1 - (bx1 - barX) * 0.12, barY, (bx1 - barX) * 0.12, barH, barH / 2);
    }

    /* 聚焦人物：阶段热力条（酝酿·破局·高潮·收束） */
    if (focused && focusData) {
      const stripY = barY + barH + 5;
      const phases = [];
      for (const ed of focusData.endeavors || []) {
        for (const ph of ed.phases || []) {
          const s = parseYear(ph.start_date), e2 = parseYear(ph.end_date);
          if (s == null || e2 == null) continue;
          phases.push({ s, e: Math.max(s, e2), c: PHASE_COLORS[ph.name] || '#857761' });
        }
      }
      phases.sort((a, b) => a.s - b.s);
      for (const ph of phases) {
        const px0 = Math.max(barX, yearX(ph.s));
        const px1 = Math.min(bx1, yearX(ph.e));
        if (px1 <= px0) continue;
        ctx.globalAlpha = 0.85;
        ctx.fillStyle = ph.c;
        ctx.fillRect(px0, stripY, px1 - px0, 4);
      }
    }

    /* 事件点 */
    for (const ev of eventsByQ.get(p.qid) || []) {
      if (ev.year < viewL - 5 || ev.year > viewR + 5) continue;
      const cx = yearX(ev.year);
      const cy = barY + barH / 2;
      const inLife = ev.year >= p.b && ev.year <= p.d;
      ctx.globalAlpha = alpha;
      if (ev.isHl) {
        ctx.beginPath();
        ctx.arc(cx, cy, 4.4, 0, Math.PI * 2);
        ctx.fillStyle = '#16100A'; ctx.fill();
        ctx.lineWidth = 2; ctx.strokeStyle = '#E8502F'; ctx.stroke();
      } else {
        ctx.beginPath();
        ctx.arc(cx, cy, inLife ? 2.4 : 1.7, 0, Math.PI * 2);
        ctx.fillStyle = inLife ? 'rgba(239,227,204,.65)' : 'rgba(239,227,204,.3)';
        ctx.fill();
      }
    }
  }

  /* 时间准线 + 年份章 */
  if (hover != null) {
    const yr = hover.yr;
    const cx = yearX(yr);
    ctx.globalAlpha = 1;
    ctx.strokeStyle = 'rgba(217,164,65,.5)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(cx + 0.5, RULER_H);
    ctx.lineTo(cx + 0.5, H);
    ctx.stroke();

    const era = eraOfYear(yr);
    const label = `${fmtYear(yr)} · ${era.name}`;
    ctx.font = F_TICK;
    const tw = ctx.measureText(label).width;
    const chipX = clamp(cx - tw / 2 - 10, RAIL + 6, W - tw - 26);
    ctx.fillStyle = 'rgba(44,32,20,.95)';
    rr(chipX, 46, tw + 20, 22, 11);
    ctx.fillStyle = '#D9A441';
    ctx.fillText(label, chipX + 10, 61);
  }

  /* 悬停点的外圈 */
  if (hoverDot) {
    const top = rowTop(hoverDot.row) + 13 + ((focusQ === hoverDot.qid) ? 12 : 8) / 2;
    ctx.beginPath();
    ctx.arc(yearX(hoverDot.year), top, 8, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(239,227,204,.85)';
    ctx.lineWidth = 1.4;
    ctx.stroke();
  }

  ctx.restore();

  /* ---- 固定人名列（横向滚动时名字不消失） ---- */
  ctx.fillStyle = 'rgba(32,23,16,.8)';
  ctx.fillRect(0, RULER_H, RAIL, H - RULER_H);
  ctx.strokeStyle = 'rgba(239,227,204,.13)';
  ctx.beginPath();
  ctx.moveTo(RAIL - 0.5, RULER_H);
  ctx.lineTo(RAIL - 0.5, H);
  ctx.stroke();

  for (let r = r0; r <= r1; r++) {
    const p = persons[r];
    const top = rowTop(r);
    const focused = focusQ === p.qid;

    let alpha = 1;
    if (hover != null && (hover.yr < p.b || hover.yr > p.d)) alpha = 0.55;
    if (spotlight && !focused) alpha = Math.min(alpha, 0.3);

    ctx.font = F_NAME;
    if (p.nw == null) p.nw = ctx.measureText(p.name).width;
    ctx.globalAlpha = alpha * 0.95;
    ctx.fillStyle = (hoverDot && hoverDot.qid === p.qid) ? '#D08B54' : '#EFE3CC';
    ctx.fillText(p.name, 8, top + 21);

    /* 同期年龄：存活者名字旁显示当时年龄 */
    if (hover != null && hover.yr >= p.b && hover.yr <= p.d) {
      const age = Math.max(0, hover.yr - p.b);
      const label = `${age}岁`;
      ctx.font = F_AGE;
      const aw = ctx.measureText(label).width;
      ctx.fillStyle = '#D9A441';
      if (8 + p.nw + 6 + aw <= RAIL - 4) {
        ctx.fillText(label, 8 + p.nw + 6, top + 20.5);
      } else {   // 一行放不下：换到名字下方右对齐
        ctx.font = '9.5px "SF Mono",Menlo,Consolas,monospace';
        ctx.textAlign = 'right';
        ctx.fillText(label, RAIL - 6, top + 31);
        ctx.textAlign = 'left';
      }
    }
  }

  /* 标尺 */
  drawRuler(viewL, viewR);
  ctx.globalAlpha = 1;
}

function rr(x, y, w, h, r) {
  r = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.fill();
}

function drawRuler(viewL, viewR) {
  ctx.fillStyle = 'rgba(26,19,12,.96)';
  ctx.fillRect(0, 0, W, RULER_H);
  ctx.strokeStyle = 'rgba(239,227,204,.13)';
  ctx.beginPath();
  ctx.moveTo(0, RULER_H - 0.5);
  ctx.lineTo(W, RULER_H - 0.5);
  ctx.stroke();

  /* 朝代段落 */
  for (const e of ERAS) {
    const a = Math.max(viewL, e.f), b = Math.min(viewR, e.u);
    if (a >= b) continue;
    const x0 = yearX(a), x1 = yearX(b);
    ctx.fillStyle = e.c;
    ctx.globalAlpha = 0.9;
    ctx.fillRect(x0, RULER_H - 4, x1 - x0, 3);
    if (x1 - x0 > 64) {
      ctx.globalAlpha = 0.9;
      ctx.fillStyle = e.c;
      ctx.font = F_ERA;
      ctx.fillText(e.name, x0 + 8, RULER_H - 10);
    }
  }
  ctx.globalAlpha = 1;

  /* 自适应刻度 */
  const steps = [1000, 500, 200, 100, 50, 20, 10, 5, 2, 1];
  const step = steps.find(s => s * view.ppy >= 78) || 1;
  const y0 = Math.ceil(viewL / step) * step;
  ctx.font = F_TICK;
  ctx.textAlign = 'center';
  for (let y = y0; y <= viewR; y += step) {
    const x = yearX(y);
    ctx.strokeStyle = 'rgba(239,227,204,.3)';
    ctx.beginPath();
    ctx.moveTo(x + 0.5, RULER_H - 14);
    ctx.lineTo(x + 0.5, RULER_H - 5);
    ctx.stroke();
    ctx.fillStyle = '#B4A488';
    ctx.fillText(fmtYear(y), x, RULER_H - 20);
    if (step * view.ppy > 120) {   // 细分刻度
      const sub = step / 5;
      for (let k = 1; k < 5; k++) {
        const sx = yearX(y - step + sub * k);
        ctx.strokeStyle = 'rgba(239,227,204,.12)';
        ctx.beginPath();
        ctx.moveTo(sx + 0.5, RULER_H - 9);
        ctx.lineTo(sx + 0.5, RULER_H - 5);
        ctx.stroke();
      }
    }
  }
  ctx.textAlign = 'left';
}

/* ---- 主循环 ---- */

let lastT = performance.now();
function loop(now) {
  const dt = Math.min(0.05, (now - lastT) / 1000);
  lastT = now;

  if (mode === 'tween' && tween) {
    const t = (now - tween.t0) / tween.dur;
    if (t >= 1) {
      Object.assign(view, tween.to);
      tween = null; mode = 'rest';
    } else {
      const k = tween.ease(t);
      view.x = tween.from.x + (tween.to.x - tween.from.x) * k;
      view.ppy = tween.from.ppy + (tween.to.ppy - tween.from.ppy) * k;
      view.y = tween.from.y + (tween.to.y - tween.from.y) * k;
    }
    needs = true;
  } else if (mode === 'inertia') {
    view.x += vel.x * dt;
    view.y += vel.y * dt;
    const k = Math.exp(-dt * 4.5);
    vel.x *= k; vel.y *= k;
    if (Math.hypot(vel.x, vel.y) < 3) mode = 'rest';
    needs = true;
  }

  if (needs) {
    clampView();
    draw();
    needs = false;
  }
  requestAnimationFrame(loop);
}

/* ---- 指针交互 ---- */

let drag = null;   // {id, sx, sy, moved, t0, samples:[]}
const pointers = new Map();
let pinch = null;  // {dist, ppy, mx, my}

function hitDot(px, py) {
  let best = null, bestD = 10;
  for (const ev of events) {
    const r = ev.row;
    const top = rowTop(r);
    if (py < top - 2 || py > top + ROW_H - 4) continue;
    const cy = top + 13 + ((focusQ === ev.qid) ? 12 : 8) / 2;
    const dx = px - yearX(ev.year), dy = py - cy;
    const d = Math.hypot(dx, dy);
    const radius = ev.isHl ? 9 : 7;
    if (d < radius && d < bestD) { best = ev; bestD = d; }
  }
  return best;
}

function rowAt(py) {
  const r = Math.floor((py - RULER_H + view.y) / ROW_H);
  if (r < 0 || r >= persons.length) return null;
  const top = rowTop(r);
  return (py >= top - 4 && py <= top + ROW_H) ? persons[r] : null;
}

canvas.addEventListener('pointerdown', e => {
  canvas.setPointerCapture(e.pointerId);
  pointers.set(e.pointerId, { x: e.offsetX, y: e.offsetY });
  tween = null;

  if (pointers.size === 2) {   // 双指捏合
    const [a, b] = [...pointers.values()];
    pinch = {
      dist: Math.hypot(a.x - b.x, a.y - b.y),
      ppy: view.ppy,
      mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2,
    };
    drag = null;
    hidePop();
    return;
  }

  drag = {
    id: e.pointerId, sx: e.offsetX, sy: e.offsetY,
    lx: e.offsetX, ly: e.offsetY, lt: performance.now(),
    moved: 0, t0: performance.now(), samples: [],
  };
  mode = 'drag';
  vel = { x: 0, y: 0 };
  canvas.classList.add('dragging');
  hidePop();
  canvas.style.cursor = 'grabbing';
});

canvas.addEventListener('pointermove', e => {
  if (pointers.has(e.pointerId)) pointers.set(e.pointerId, { x: e.offsetX, y: e.offsetY });

  if (pinch && pointers.size === 2) {
    const [a, b] = [...pointers.values()];
    const dist = Math.hypot(a.x - b.x, a.y - b.y);
    if (pinch.dist > 0) {
      const factor = clamp(dist / pinch.dist, 0.5, 2);
      zoomAt(pinch.mx, pinch.my, factor);
    }
    pinch.dist = dist;
    return;
  }

  if (drag && e.pointerId === drag.id) {
    const dx = e.offsetX - drag.lx, dy = e.offsetY - drag.ly;
    const now = performance.now();
    const dt = Math.max(1, now - drag.lt);
    view.x -= dx / view.ppy;
    view.y -= dy;
    drag.moved += Math.abs(dx) + Math.abs(dy);
    drag.samples.push({ t: now, vx: dx / dt, vy: dy / dt });
    if (drag.samples.length > 6) drag.samples.shift();
    drag.lx = e.offsetX; drag.ly = e.offsetY; drag.lt = now;
    hover = null; hoverDot = null;
    needs = true;
    return;
  }

  /* 悬停：准线跟随光标；命中事件点则准线锁到事件年份并弹 popover */
  const ev = hitDot(e.offsetX, e.offsetY);
  const yr = ev ? ev.year : Math.round(xYear(e.offsetX));
  const changed = (ev?.title !== hoverDot?.title) || (hover?.yr !== yr);
  hover = { px: e.offsetX, py: e.offsetY, yr };
  hoverDot = ev;
  if (ev) {
    showPop(ev, e.offsetX, e.offsetY, false);
  } else if (pinned) {
    showPop(pinned, hover.px, hover.py, true);   // 保持钉住的 popover
  } else {
    hidePop();
  }
  if (changed) needs = true;
});

function endPointer(e) {
  pointers.delete(e.pointerId);
  if (pinch && pointers.size < 2) { pinch = null; }

  if (drag && e.pointerId === drag.id) {
    canvas.classList.remove('dragging');
    canvas.style.cursor = 'grab';
    const dur = performance.now() - drag.t0;
    const isClick = drag.moved < 6 && dur < 600;
    if (isClick) {
      onClick(e.offsetX, e.offsetY);
    } else {
      const s = drag.samples.slice(-4);
      const dt = Math.max(16, (s[s.length - 1]?.t ?? performance.now()) - (s[0]?.t ?? performance.now()));
      const vx = s.reduce((a, x) => a + x.vx, 0) / s.length;   // px/ms（屏幕）
      const vy = s.reduce((a, x) => a + x.vy, 0) / s.length;
      vel = {
        x: -vx * 1000 / view.ppy,   // 年/s
        y: -vy * 1000,              // px/s
      };
      if (Math.hypot(vel.x, vel.y) > 40) mode = 'inertia';
      else mode = 'rest';
    }
    drag = null;
    needs = true;
  }
}
canvas.addEventListener('pointerup', endPointer);
canvas.addEventListener('pointercancel', endPointer);
canvas.addEventListener('pointerleave', () => {
  if (!drag && !pinch) { hover = null; hoverDot = null; if (!pinned) hidePop(); needs = true; }
});

function zoomAt(px, py, factor) {
  const yr = xYear(px);
  view.ppy = clamp(view.ppy * factor, MIN_PPY, MAX_PPY);
  view.x = yr - px / view.ppy;
  clampView();
  needs = true;
}

canvas.addEventListener('wheel', e => {
  e.preventDefault();
  const factor = Math.exp(-e.deltaY * (e.deltaMode === 1 ? 0.05 : 0.0016));
  zoomAt(e.offsetX, e.offsetY, factor);
}, { passive: false });

function onClick(px, py) {
  const dot = hitDot(px, py);
  if (dot) {
    pinned = dot;
    showPop(dot, px, py, true);
    return;
  }
  if (pinned) { pinned = null; hidePop(); }

  const p = rowAt(py);
  if (p) {
    if (focusQ === p.qid) unfocus();
    else focusPerson(p);
  }
}

/* ---- popover ---- */

let popTimer = null;

function showPop(ev, px, py, pin) {
  clearTimeout(popTimer);
  const era = ev.year != null ? eraOfYear(ev.year) : null;
  popEl.innerHTML = `
    ${pin ? '<button class="pop-close" aria-label="关闭">✕</button>' : ''}
    <div class="pop-date">${fmtDate(ev.dateStr || String(ev.year))}</div>
    <div class="pop-title">${esc(ev.title)}</div>
    <div class="pop-meta">
      <span class="chip ${ev.isHl ? 'hl' : ''}">${esc(ev.isHl ? (ev.htype || '名场面') : (ev.type || '事件'))}</span>
      <span class="pop-owner">${esc(ev.person)}</span>${ev.place ? ' · ' + esc(ev.place) : ''}${era ? ' · ' + era.name : ''}
    </div>
    ${ev.desc ? `<p class="pop-desc">${esc(ev.desc)}</p>` : ''}
  `;
  popEl.classList.toggle('is-hl', ev.isHl);
  popEl.hidden = false;
  const pw = popEl.offsetWidth, ph = popEl.offsetHeight;
  let x = px + 16, y = py + 16;
  if (x + pw > W - 10) x = px - pw - 16;
  if (y + ph > H - 10) y = py - ph - 16;
  popEl.style.left = `${clamp(x, 8, W - pw - 8)}px`;
  popEl.style.top = `${clamp(y, 8, Math.max(8, H - ph - 8))}px`;
  requestAnimationFrame(() => popEl.classList.add('on'));
}

function hidePop() {
  popEl.classList.remove('on');
  clearTimeout(popTimer);
  popTimer = setTimeout(() => { popEl.hidden = true; }, 180);
}

popEl.addEventListener('click', e => {
  if (e.target.closest('.pop-close')) { pinned = null; hidePop(); }
});

/* ---- 聚焦模式 ---- */

async function focusPerson(p) {
  focusReturn = { ...view };
  focusQ = p.qid;
  focusData = null;

  const span = Math.max(p.d - p.b, 8);
  const from = p.b - span * 0.15, to = p.d + span * 0.15;
  const ppyT = clamp((W * 0.82) / (to - from), MIN_PPY, MAX_PPY);
  const xT = clamp(from - W * 0.08 / ppyT, MIN_YEAR, MAX_YEAR);
  /* 行中心（世界坐标）对到视口中心：screenY = RULER_H + worldY - view.y */
  const yT = clamp(p.row * ROW_H + ROW_H / 2 - (H - RULER_H) / 2, 0, Math.max(0, worldH - H));
  tweenTo({ x: xT, ppy: ppyT, y: yT }, RM ? 0 : 720, easeInOut);

  /* 面板：先骨架后档案 */
  panelEl.hidden = false;
  panelEl.innerHTML = `
    <button class="panel-close" aria-label="返回概览">✕</button>
    <p class="p-era">${esc(p.era || '')}</p>
    <h2 class="p-name">${esc(p.name)}</h2>
    <p class="p-archetype">${esc(p.archetype || '')}</p>
    <p class="p-dates">${fmtYear(p.b)} — ${p.est ? '?' : fmtYear(p.d)}</p>
    <p class="p-loading">载入档案……</p>
  `;
  requestAnimationFrame(() => panelEl.classList.add('on'));

  try {
    let detail = centuryCache.get(p.century);
    if (!detail) {
      detail = await getJSON(`data/${p.century}.json`);
      centuryCache.set(p.century, detail);
    }
    if (focusQ !== p.qid) return;   // 期间已切走
    const full = detail.find(x => x.qid === p.qid);
    focusData = full || null;
    renderPanel(p, full);
    needs = true;
  } catch (err) {
    if (focusQ === p.qid) {
      $('.p-loading', panelEl) && ($('.p-loading', panelEl).textContent = '档案载入失败，时间轴仍可浏览。');
    }
  }
}

function unfocus() {
  if (!focusQ) return;
  focusQ = null;
  focusData = null;
  panelEl.classList.remove('on');
  setTimeout(() => { if (!focusQ) panelEl.hidden = true; }, 340);
  if (focusReturn) tweenTo(focusReturn, RM ? 0 : 720, easeInOut);
}

function phaseBarHTML(ed) {
  const phases = (ed.phases || []);
  if (!phases.length) return '';
  const s0 = parseYear(ed.start_date), s1 = parseYear(ed.end_date);
  const total = Math.max(1, (s1 ?? 0) - (s0 ?? 0));
  let inner = '', labels = '';
  for (const ph of phases) {
    const a = parseYear(ph.start_date), b = parseYear(ph.end_date);
    if (a == null) continue;
    const w = clamp(((b ?? a) - a) / total * 100, 4, 100);
    const c = PHASE_COLORS[ph.name] || '#857761';
    inner += `<i style="width:${w}%;background:${c}" title="${esc(ph.name)} · ${fmtYear(a)}–${fmtYear(b ?? a)}${ph.highlight ? ' · ' + ph.highlight : ''}"></i>`;
    labels += `<b style="color:${c}">■</b> ${esc(ph.name)} `;
    if (ph.highlight) labels += `<em>${esc(ph.highlight)}</em> `;
  }
  return `<div class="e-phases">${inner}</div><div class="e-phase-labels">${labels}</div>`;
}

function renderPanel(p, full) {
  const wiki = /^Q\d+$/.test(p.qid)
    ? `<a href="https://www.wikidata.org/wiki/${esc(p.qid)}" target="_blank" rel="noopener" style="color:var(--paper-faint);font-size:11px;text-decoration:none;border-bottom:1px dashed var(--line-strong)">Wikidata ↗</a>`
    : '';
  const endeavors = (full?.endeavors || [])
    .slice()
    .sort((a, b) => (parseYear(a.start_date) ?? 9999) - (parseYear(b.start_date) ?? 9999));
  const highlights = (full?.highlights || []).slice(0, 8);

  panelEl.innerHTML = `
    <button class="panel-close" aria-label="返回概览">✕</button>
    <p class="p-era">${esc(p.era || '')}${p.role === '教训' ? ' · 教训' : ''}</p>
    <h2 class="p-name">${esc(p.name)}</h2>
    <p class="p-archetype">${esc(p.archetype || '')} ${wiki}</p>
    <p class="p-dates">${fmtYear(p.b)} — ${p.est ? '?' : fmtYear(p.d)} · 享年 ${p.d - p.b} 岁</p>

    ${full?.summary_first_person ? `
      <p class="p-quote-label">第一人称</p>
      <p class="p-quote">${esc(full.summary_first_person)}</p>` : ''}

    ${full?.lesson ? `<p class="p-lesson">${esc(full.lesson)}</p>` : ''}

    ${endeavors.length ? `
      <p class="p-sect">事业周期</p>
      ${endeavors.map(ed => `
        <div class="endeavor">
          <div class="e-head">
            <span class="e-title">${esc(ed.title_zh || '')}</span>
            ${ed.domain ? `<span class="e-domain">${esc(ed.domain)}</span>` : ''}
            <span class="e-dates">${fmtYear(parseYear(ed.start_date))}–${fmtYear(parseYear(ed.end_date))}</span>
          </div>
          ${ed.description_zh ? `<p class="e-desc">${esc(ed.description_zh)}</p>` : ''}
          ${ed.places?.length ? `<p class="e-places">地点 · ${ed.places.map(esc).join(' / ')}</p>` : ''}
          ${ed.outcome ? `<p class="e-outcome">结果 · ${esc(ed.outcome)}</p>` : ''}
          ${phaseBarHTML(ed)}
        </div>`).join('')}` : ''}

    ${highlights.length ? `
      <p class="p-sect">名场面</p>
      ${highlights.map(h => `
        <div class="hl-item">
          <i></i>
          <span class="d">${esc(h.date || '')}</span>
          <span class="t"><b>${esc(h.title_zh || '')}</b>${h.highlight_note ? `<small>${esc(h.highlight_note)}</small>` : ''}</span>
        </div>`).join('')}` : ''}

    <p class="p-lesson" style="border-left-color:var(--line-strong)">按 <kbd style="font-family:var(--f-mono);font-size:11px">ESC</kbd> 或再次点击该行返回全局概览</p>
  `;
}

panelEl.addEventListener('click', e => {
  if (e.target.closest('.panel-close')) unfocus();
});

/* ---- 键盘 ---- */

window.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    if (pinned) { pinned = null; hidePop(); return; }
    if (focusQ) { unfocus(); return; }
    hidePop();
  }
});

canvas.addEventListener('keydown', e => {
  const stepX = 140 / view.ppy, stepY = 110;
  if (e.key === 'ArrowLeft')  { tweenTo({ ...view, x: view.x - stepX }, 260); e.preventDefault(); }
  if (e.key === 'ArrowRight') { tweenTo({ ...view, x: view.x + stepX }, 260); e.preventDefault(); }
  if (e.key === 'ArrowUp')    { tweenTo({ ...view, y: view.y - stepY }, 260); e.preventDefault(); }
  if (e.key === 'ArrowDown')  { tweenTo({ ...view, y: view.y + stepY }, 260); e.preventDefault(); }
  if (e.key === '+' || e.key === '=') zoomAt(W / 2, H / 2, 1.3);
  if (e.key === '-') zoomAt(W / 2, H / 2, 1 / 1.3);
});

/* ---- 图例与快跳 ---- */

function buildLegend() {
  const box = $('#tl-legend');
  const dots = ERAS.map(e =>
    `<span class="era-dot"><i style="background:${e.c}"></i>${e.name}</span>`).join('');
  const jumps = JUMPS.map((j, i) =>
    `<button class="era-jump" data-i="${i}">${j.label}</button>`).join('');
  box.innerHTML = jumps + dots;
  box.addEventListener('click', e => {
    const btn = e.target.closest('.era-jump');
    if (!btn) return;
    const j = JUMPS[+btn.dataset.i];
    tweenTo({
      x: clamp(j.cy - W / 2 / j.ppy, MIN_YEAR, MAX_YEAR - W / j.ppy),
      ppy: j.ppy,
      y: view.y,
    }, RM ? 0 : 800, easeInOut);
  });
}

/* ---- 搜索（按人名快速定位） ---- */

const searchInput = $('#tl-search');
const suggestEl = $('#tl-suggest');

searchInput.addEventListener('input', () => {
  const q = searchInput.value.trim();
  if (!q) { suggestEl.hidden = true; suggestEl.innerHTML = ''; return; }
  const hits = persons
    .filter(p => (p.name || '').includes(q) || (p.archetype || '').includes(q) || (p.era || '').includes(q))
    .slice(0, 8);
  suggestEl.innerHTML = hits.length
    ? hits.map(p => `<button class="sg-item" data-qid="${esc(p.qid)}"><b>${esc(p.name)}</b><span>${esc(p.era || '')} · ${esc(p.archetype || '')}</span></button>`).join('')
    : `<div class="sg-empty">没有找到「${esc(q)}」</div>`;
  suggestEl.hidden = false;
});

suggestEl.addEventListener('click', e => {
  const btn = e.target.closest('.sg-item');
  if (!btn) return;
  const p = persons.find(x => x.qid === btn.dataset.qid);
  if (p) focusPerson(p);
  suggestEl.hidden = true;
  searchInput.value = '';
  searchInput.blur();
});

searchInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') { const first = $('.sg-item', suggestEl); if (first) first.click(); }
  if (e.key === 'Escape') { suggestEl.hidden = true; searchInput.blur(); }
});

document.addEventListener('click', e => {
  if (!e.target.closest('.tl-search')) suggestEl.hidden = true;
});

/* ---- 缩放按钮 ---- */

$$('.tl-zoom button').forEach(btn => btn.addEventListener('click', () => {
  const z = btn.dataset.z;
  if (z === 'in') zoomAt(W / 2, H / 2, 1.4);
  else if (z === 'out') zoomAt(W / 2, H / 2, 1 / 1.4);
  else if (z === 'fit') {
    tweenTo({
      x: MIN_YEAR - 30,
      ppy: clamp((W * 0.96) / (MAX_YEAR - MIN_YEAR + 60), MIN_PPY, MAX_PPY),
      y: 0,
    }, RM ? 0 : 800, easeInOut);
  }
}));

/* ---- 状态浮层 ---- */

function showLoading() {
  statusEl.hidden = false;
  statusEl.innerHTML = `
    <div class="ring" aria-hidden="true"></div>
    <p class="msg">正在展开四千年……</p>`;
}

function showError(err) {
  statusEl.hidden = false;
  statusEl.innerHTML = `
    <p class="err-title">数据没能载入</p>
    <p class="msg">${esc(err.message || err)}<br>请用 <b>uv run python -m http.server -d site 8080</b> 预览。</p>
    <button id="tl-retry">重试</button>`;
  $('#tl-retry').addEventListener('click', boot);
}

/* ---- 顶栏数据规模 + 首访提示 ---- */

function fillCounts() {
  const el = $('#tl-counts');
  if (!el) return;
  const hl = events.filter(e => e.isHl).length;
  el.innerHTML = `<b>${persons.length}</b> 人 · <b>${events.length}</b> 事 · <b>${hl}</b> 幕名场面`;
}

function armHints() {
  const hints = $('.tl-hints');
  if (!hints || hints.classList.contains('gone')) return;
  const hide = () => hints.classList.add('gone');
  setTimeout(hide, 7000);
  frame.addEventListener('pointerdown', hide, { once: true });
}

/* ---- 启动 ---- */

async function boot() {
  showLoading();
  try {
    await loadTimelineData();
    statusEl.hidden = true;
    resize();
    fillCounts();
    armHints();
    const ppy0 = clamp(W / 200, MIN_PPY, MAX_PPY);   // 默认视野 ≈ 200 年（1920px 屏 ≈ README 1x）
    if (RM) {
      Object.assign(view, { x: -820, ppy: ppy0, y: 0 });
    } else {
      Object.assign(view, { x: -2050, ppy: 0.085, y: 0 });
      tweenTo({ x: -820, ppy: ppy0, y: 0 }, 1600, easeOut);
    }
    needs = true;
  } catch (err) {
    showError(err);
  }
}

new ResizeObserver(() => resize()).observe(frame);
buildLegend();
requestAnimationFrame(loop);
boot();
