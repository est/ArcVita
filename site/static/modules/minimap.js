export function initMinimap(canvas, persons, parseYear, onJump){
  if(!canvas) return;
  const ctx=canvas.getContext('2d');
  function draw(minY,maxY, viewMin, viewMax){
    const W=canvas.width, H=canvas.height;
    ctx.clearRect(0,0,W,H);
    ctx.fillStyle='#f5f0e8'; ctx.fillRect(0,0,W,H);
    const span=maxY-minY||100;
    // lifespan lines
    ctx.strokeStyle='rgba(139,69,19,.18)'; ctx.lineWidth=1;
    persons.forEach(p=>{
      const by=parseYear(p.birth_date), dy=parseYear(p.death_date)||by+60;
      if(by==null) return;
      const x1=(by-minY)/span*W, x2=(dy-minY)/span*W;
      ctx.beginPath(); ctx.moveTo(x1, H*0.4); ctx.lineTo(x2, H*0.4); ctx.stroke();
    });
    // highlights
    // view box
    const vx1=(viewMin-minY)/span*W, vx2=(viewMax-minY)/span*W;
    ctx.fillStyle='rgba(139,69,19,.12)'; ctx.fillRect(vx1,0,vx2-vx1,H);
    ctx.strokeStyle='rgba(139,69,19,.6)'; ctx.lineWidth=1.5; ctx.strokeRect(vx1,0,vx2-vx1,H);
  }
  let viewMin=-600, viewMax=2000, gMin=-600,gMax=2000;
  canvas.addEventListener('click', e=>{
    const r=canvas.getBoundingClientRect();
    const x=e.clientX-r.left, pct=x/r.width;
    const center=gMin+pct*(gMax-gMin);
    const span=viewMax-viewMin;
    onJump(center-span/2, center+span/2);
  });
  // drag view box
  let dragging=false;
  canvas.addEventListener('mousedown', ()=>dragging=true);
  window.addEventListener('mouseup', ()=>dragging=false);
  canvas.addEventListener('mousemove', e=>{
    if(!dragging) return;
    const r=canvas.getBoundingClientRect();
    const pct=(e.clientX-r.left)/r.width;
    const center=gMin+pct*(gMax-gMin);
    const span=viewMax-viewMin;
    onJump(center-span/2, center+span/2);
  });
  return { draw: (mn,mx,vm,vM)=>{ gMin=mn; gMax=mx; viewMin=vm; viewMax=vM; draw(mn,mx,vm,vM); } };
}
