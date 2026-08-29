export function computeDomain(persons, events, highlights, focusedQid, parseYear){
  if(focusedQid){
    const fp = persons.find(p=>p.qid===focusedQid);
    if(fp){ const by=parseYear(fp.birth_date), dy=parseYear(fp.death_date)||by+60; const pad=Math.max(12, (dy-by)*0.2); return [by-pad, dy+pad]; }
  }
  const years=[...events.map(e=>parseYear(e.date)), ...highlights.map(h=>parseYear(h.date))].filter(v=>v!=null);
  if(!years.length) return [-600, 2000];
  return [Math.min(...years)-20, Math.max(...years)+20];
}
export function stepFor(span, pxPerYear){
  const visible = span/pxPerYear;
  if(visible<30) return 5;
  if(visible<80) return 10;
  if(visible<200) return 20;
  if(visible<500) return 50;
  if(visible<1000) return 100;
  return 200;
}
export function ticks(minY,maxY,step,W, span){
  const arr=[];
  const start=Math.ceil(minY/step)*step;
  for(let y=start;y<=maxY;y+=step){
    const x=80+(y-minY)/span*(W-160);
    arr.push({y,x,label: y<0?Math.abs(y)+' BCE': String(y)});
  }
  return arr;
}
