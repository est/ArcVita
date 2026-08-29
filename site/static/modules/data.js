export async function loadAll() {
  const fetchJSON = async (u) => { const r = await fetch(u); if (!r.ok) throw new Error(u + ' ' + r.status); return r.json(); };
  const fetchText = async (u) => { const r = await fetch(u); if (!r.ok) throw new Error(u + ' ' + r.status); return r.text(); };
  const index = await fetchJSON('data/index.json');
  const cks = Object.keys(index.centuries || {});
  // parallel fetch centuries
  const results = await Promise.allSettled(cks.map(ck => fetchJSON(`data/${ck}.json`)));
  const persons = [];
  for (const r of results) if (r.status === 'fulfilled' && Array.isArray(r.value)) persons.push(...r.value);
  // timeline + highlights parallel
  const [tlText, highlights] = await Promise.all([fetchText('data/timeline.jsonl'), fetchJSON('data/highlights.json')]);
  const events = tlText.trim().split('\n').filter(Boolean).map(l => JSON.parse(l));
  events.sort((a,b)=>(a.date||'9999').localeCompare(b.date||'9999'));
  // sort persons by birth
  const py = s=>{ if(!s) return 9999; const m=s.replace(/约/g,'').match(/^-?\d+/); return m?parseInt(m[0]):9999; };
  persons.sort((a,b)=>py(a.birth_date)-py(b.birth_date));
  return { index, persons, events, highlights };
}

export function parseYear(s){ if(!s) return null; const m=s.replace(/约/g,'').match(/^-?\d+/); return m?parseInt(m[0]):null; }
export function ageAt(b,y){ if(b==null||y==null) return null; return y-b; }
