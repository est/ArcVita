// focus.js — 聚焦保留上下文（dim 而非消失）
import { parseYear } from './data.js';

export let focusedQid = null;

export function isFocused(){ return focusedQid!=null; }
export function getFocused(){ return focusedQid; }
export function setFocus(qid){
  focusedQid = (focusedQid===qid? null : qid);
  // 同步 hash 通过 router 模块
  return focusedQid;
}
export function clearFocus(){ focusedQid=null; }

export function focusWindow(person, fallbackSpan){
  if(!person) return null;
  const by=parseYear(person.birth_date), dy=parseYear(person.death_date);
  if(by==null) return null;
  const end = dy || (by+60);
  const span = end - by || 60;
  const pad = Math.max(12, span*0.2);
  return { minY: by - pad, maxY: end + pad };
}

// 应用 dim 类到非聚焦行（由 timeline 调用）
export function shouldDim(qid){
  return focusedQid && qid!==focusedQid;
}
