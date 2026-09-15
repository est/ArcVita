#!/usr/bin/env python3
"""筛选流水线：AI 先筛（screen）→ 只采高分人物（extract）→ 定期 push
产出：
  data/extracted/daizhige_screening/<category>/<stem>.yaml  每份文献的筛选结论（含拒录理由）
  data/extracted/daizhige/<category>/<人名>.yaml            仅 score>=阈值 的人物档案
manifest 状态机：pending_screen → screened/rejected → done
"""
import sys, os, time, datetime, traceback, subprocess, re, json
sys.path.insert(0, "src")
sys.path.insert(0, "scripts")
import yaml as y
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from arcvita.core.yaml_utils import BlockDumper, dump_block_yaml
from collections import Counter

ROOT = Path(".")
MANIFEST = ROOT / ".mimocode/daizhige_manifest.yaml"
PLAN = ROOT / ".mimocode/daizhige_screen_plan.yaml"
SRC = ROOT / "daizhigev20"
SCREEN_OUT = ROOT / "data/extracted/daizhige_screening"
EXTRACT_OUT = ROOT / "data/extracted/daizhige"
KNOWN_PERSONS = ROOT / "data/processed/persons.yaml"

BATCH = 5
WORKERS = 3
MIN_SCORE = 7
PUSH_EVERY = 1  # 每批 push

from ai_batch_extract import call_ai

# ---------- env ----------
def _load_dotenv():
    envp = ROOT / ".env"
    if envp.exists():
        for line in envp.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() not in os.environ:
                os.environ[k.strip()] = v.strip().strip('"').strip("'")
_load_dotenv()

# ---------- manifest io ----------
def load_manifest():
    lines = open(MANIFEST, encoding="utf-8").read().splitlines()
    return y.safe_load("\n".join(l for l in lines if not l.startswith("#"))), lines

def save_manifest(data, lines):
    header = "\n".join(l for l in lines if l.startswith("#")) + "\n"
    body = y.dump(data, allow_unicode=True, sort_keys=False, width=100, default_flow_style=False, Dumper=BlockDumper)
    open(MANIFEST, "w", encoding="utf-8").write(header + body)

def git_push(msg):
    # 注意：.mimocode（manifest/plan）不入库，仅推送 data 子模块
    try:
        subprocess.run(["git", "-C", "data", "add", "extracted/"], check=False, timeout=120)
        r = subprocess.run(["git", "-C", "data", "diff", "--cached", "--stat"], capture_output=True, text=True, timeout=60)
        if r.stdout.strip():
            subprocess.run(["git", "-C", "data", "commit", "-m", msg], check=False, timeout=120)
            p = subprocess.run(["git", "-C", "data", "push"], capture_output=True, text=True, timeout=300)
            print(f"push data: rc={p.returncode}")
    except Exception as e:
        print(f"git fail: {e}")

def now():
    return datetime.datetime.now().isoformat()

HEARTBEAT = ROOT / "tmp" / "pipeline_heartbeat.json"

def heartbeat(stage, detail=""):
    try:
        HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
        HEARTBEAT.write_text(json.dumps({"time": now(), "stage": stage, "detail": detail, "pid": os.getpid()}, ensure_ascii=False))
    except Exception:
        pass

# ---------- 已有人物（防重） ----------
def known_names():
    try:
        ps = y.safe_load(open(KNOWN_PERSONS, encoding="utf-8")) or []
        return {p["name_zh"] for p in ps}
    except Exception:
        return set()

# ---------- 筛选 ----------
SCREEN_PROMPT = """你是 ArcVita 历史人物筛选官。判断一份古籍文献中哪些人物值得录入「成事儿时间轴」。

【价值标准】
1. 做事流完整：有可考的完整做事周期——缘起、阶段、关键决定、结果；不是只罗列官爵世系
2. 名场面潜力：成语/代表作/战役/发明/制度/演讲/关键决策的诞生点
3. 模范或教训：其经历能给后人启发或警示
4. 时间可考：生卒年或主要活动年代可考
5. 天下共主（君主）低优先：君主主要作时间坐标，除非有突出做事（如秦始皇商鞅变法级）

【评分】
9-10 必录：多条俱全；7-8 录：做事流较完整；5-6 缓：事迹简略；1-4 不录

【输出】只输出块式 YAML（禁 [] / {{}} / 双引号，列表用 - 每项一行）：
verdict: has_candidates 或 no_value
skip_reason: （仅 no_value 时填）
candidates:
  - name_zh: 张良
    score: 9
    worth_why: 运筹帷幄决胜千里；功成身退
    era: 秦末汉初
    dates_known: true
rejections:
  - name_zh: 某某
    why_not: 传文仅数十字无做事周期

candidates 至多 15 人。若文献为正史/大部头，可凭目录与你的史学知识列出其中最值得录入者。不要包裹 ```。

【格式铁律】
键名必须用英文：name_zh / score / worth_why / why_not / verdict / candidates / rejections / skip_reason / era / dates_known
冒号必须用英文半角冒号（: 后跟空格），禁止全角冒号
【示例】
verdict: has_candidates
candidates:
  - name_zh: 张良
    score: 9
    worth_why: 运筹帷幄决胜千里又功成身退
    era: 秦末汉初
    dates_known: true
rejections:
  - name_zh: 某某
    why_not: 无事迹文本
"""

KEY_MAP = {
    "中文名": "name_zh", "中文名称": "name_zh", "姓名": "name_zh", "name": "name_zh",
    "评分": "score", "得分": "score", "分数": "score",
    "价值原因": "worth_why", "入选理由": "worth_why", "推荐理由": "worth_why",
    "值得入选理由": "worth_why", "入选原因": "worth_why",
    "时代": "era", "朝代": "era",
    "生卒可考": "dates_known", "时间可考": "dates_known", "年代可考": "dates_known",
    "为何不录": "why_not", "不录理由": "why_not", "拒绝理由": "why_not", "原因": "why_not",
    "裁定": "verdict", "判决": "verdict", "验证结果": "verdict", "结论": "verdict",
    "判词": "verdict", "判断结果": "verdict", "判定": "verdict",
    "候选者": "candidates", "候选对象": "candidates", "候选人": "candidates",
    "候选项": "candidates", "候选": "candidates",
}

_INVISIBLE = re.compile("[\u200b\u200c\u200d\u200e\u200f\ufeff\u00a0]")

def _clean_key(k):
    return _INVISIBLE.sub("", str(k)).strip()

def _norm_keys(obj):
    if isinstance(obj, dict):
        return {KEY_MAP.get(_clean_key(k), _clean_key(k)): _norm_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_norm_keys(x) for x in obj]
    return obj

def _tolerant_load(text):
    """容错 YAML 解析：先直接解析，失败则修全角冒号再试，最后归一键名"""
    try:
        return _norm_keys(y.safe_load(text))
    except Exception:
        pass
    fixed = text.replace("：//", "://").replace("：", ": ")
    fixed = re.sub(r": +", ": ", fixed)
    fixed = re.sub(r":(?=[\u4e00-\u9fff])", ": ", fixed)
    return _norm_keys(y.safe_load(fixed))

def _coerce_score(v):
    try:
        return int(v)
    except Exception:
        m = re.search(r"\d+", str(v))
        return int(m.group(0)) if m else 0

def _strip_fence(t):
    t = t.strip()
    if t.startswith("```"):
        t = "\n".join(t.splitlines()[1:])
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()

def screen_one(entry, known):
    src = SRC / entry["source"]
    if not src.exists():
        return {"status": "skipped", "reason": "源文件缺失"}
    text = src.read_text(encoding="utf-8", errors="ignore")
    # 去掉 frontmatter，取正文头部 4000 字
    body = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
    head = body[:4000]
    prompt = SCREEN_PROMPT + f"\n\n【已有库人物】（已在库勿重复列）\n{'、'.join(sorted(known))[:800]}\n"
    prompt += f"\n【文献】{entry['category']} / {Path(entry['source']).name}\n{head}"
    out = _strip_fence(call_ai("", prompt))
    try:
        data = _tolerant_load(out)
    except Exception:
        # 重试一次：明确提醒格式
        out2 = _strip_fence(call_ai("", prompt + "\n\n上次输出格式不对。请严格只输出英文键名+英文半角冒号的 YAML，不要中文键名，不要全角冒号。"))
        data = _tolerant_load(out2)
        out = out2
    if not isinstance(data, dict) or "verdict" not in data:
        # 兜底：verdict 缺失但顶层有候选人列表 → 视为有候选
        found = None
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list) and v and isinstance(v[0], dict) and "name_zh" in v[0]:
                    found = v
                    break
        if found is not None:
            data["verdict"] = "has_candidates"
            data["candidates"] = found
        else:
            raise ValueError(f"筛选输出不合规: {out[:120]}")
    # verdict 归一（模型可能输出中文）
    v = str(data.get("verdict", "")).strip()
    if "无" in v or v.lower().startswith("no"):
        data["verdict"] = "no_value"
    elif "有" in v or v.lower().startswith("has"):
        data["verdict"] = "has_candidates"
    # 落盘筛选结论
    rel = Path(entry["source"]).with_suffix(".yaml")
    dst = SCREEN_OUT / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dump_block_yaml(dst, {"source": entry["source"], "category": entry["category"], **data}, strip_empty=True)
    # 生成 manifest 结论
    if data.get("verdict") == "no_value":
        return {"status": "rejected", "reason": (data.get("skip_reason") or "AI 判定无值得记录人物")[:300]}
    cands = [c for c in (data.get("candidates") or []) if c.get("name_zh")]
    if not cands:
        return {"status": "rejected", "reason": (data.get("skip_reason") or "筛选无候选人")[:300]}
    entry["candidates"] = [{"name_zh": _INVISIBLE.sub("", str(c["name_zh"])).strip(), "score": _coerce_score(c.get("score")), "worth_why": (str(c.get("worth_why") or ""))[:200]} for c in cands]
    entry["candidates_total"] = len(entry["candidates"])
    entry["extracted_qids"] = []
    return {"status": "screened", "n_candidates": len(cands)}

def extract_one(entry, cand, taken_names, known):
    name = cand["name_zh"]
    if name in taken_names or name in known:
        return {"skip": "已有库或本批已采"}
    out_path = EXTRACT_OUT / entry["category"] / f"{name}.yaml"
    if out_path.exists():
        return {"skip": "已存在"}
    src = SRC / entry["source"]
    text = src.read_text(encoding="utf-8", errors="ignore")
    body = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
    idx = body.find(name)
    window = body[max(0, idx - 2000): idx + 6000] if idx >= 0 else body[:8000]
    out = _strip_fence(call_ai("", f"人名提示：{name}\n\n古文：\n{window}"))
    try:
        parsed = _tolerant_load(out)
    except Exception:
        out = _strip_fence(call_ai("", f"人名提示：{name}\n\n古文：\n{window}\n\n上次输出格式不对。请严格只输出英文键名+英文半角冒号的 YAML。"))
        parsed = _tolerant_load(out)
    if not isinstance(parsed, dict) or "person" not in parsed:
        raise ValueError(f"抽取输出不合规: {out[:120]}")
    if "insufficient" in out.lower():
        return {"skip": "传文不足"}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    dump_block_yaml(out_path, parsed, strip_empty=True)
    return {"qid": (parsed.get("person") or {}).get("qid") or f"guji-{name}"}

# ---------- 主循环 ----------
def pick(entries, status, n):
    pool = [e for e in entries if e.get("status") == status]
    pool.sort(key=lambda e: (e.get("priority", 5), e.get("source", "")))
    return pool[:n]

def _qid_to_name(q):
    """extracted_qids 条目 → 候选人名：skip:名:原因 → 名；guji-名 → 名；其余原样"""
    q = str(q)
    if q.startswith("skip:"):
        parts = q.split(":")
        return parts[1] if len(parts) > 1 else ""
    if q.startswith("guji-"):
        return q[len("guji-"):]
    return q

def extracted_names(e):
    names = set()
    for q in (e.get("extracted_qids") or []):
        n = _qid_to_name(q)
        if n:
            names.add(n)
    return names

def main():
    known = known_names()
    taken = set()
    print(f"screen pipeline start {now()} batch={BATCH} workers={WORKERS} min_score={MIN_SCORE}", flush=True)
    heartbeat("start")
    n_push = 0
    while True:
        t0 = time.time()
        data, lines = load_manifest()
        print(f"[{now()}] manifest loaded {len(data)} entries in {time.time()-t0:.1f}s", flush=True)
        heartbeat("loaded", f"{len(data)} entries")
        # --- 筛选批 ---
        todo = pick(data, "pending_screen", BATCH)
        if todo:
            print(f"[{now()}] screen batch start: {[e['source'] for e in todo]}", flush=True)
            heartbeat("screening", f"{len(todo)} files")
            def _do(e):
                e["status"] = "processing_screen"
                try:
                    r = screen_one(e, known)
                    e["status"] = r["status"]
                    if r["status"] in ("rejected", "skipped"):
                        e["reason"] = r.get("reason")
                    if r["status"] == "screened":
                        e["reason"] = None
                        print(f"screened {e['source']} -> {r['n_candidates']}人")
                except Exception as ex:
                    traceback.print_exc()
                    e["status"] = "error"
                    e["reason"] = str(ex)[:400]
                e["updated_at"] = now()
                return e
            with ThreadPoolExecutor(max_workers=WORKERS) as ex:
                list(ex.map(_do, todo))
            t1 = time.time()
            save_manifest(data, lines)
            print(f"[{now()}] screen batch done + manifest saved in {time.time()-t1:.1f}s", flush=True)
            heartbeat("screened_saved")
            n_push += 1
            if n_push % PUSH_EVERY == 0:
                git_push(f"daizhige screen batch {now()}")
                heartbeat("pushed")
            continue
        # --- 抽取批（score>=MIN_SCORE） ---
        screened = [e for e in data if e.get("status") == "screened" and e.get("candidates")]
        job = None
        swept = 0
        for e in sorted(screened, key=lambda x: (x.get("priority", 5), x.get("source", ""))):
            have = extracted_names(e)
            for c in e["candidates"]:
                if c["score"] >= MIN_SCORE and (EXTRACT_OUT / e.get("category", "") / f"{c['name_zh']}.yaml").exists():
                    have.add(c["name_zh"])
            scored = {c["name_zh"] for c in e["candidates"] if c["score"] >= MIN_SCORE}
            if not scored or scored <= have:
                # 无高分候选，或高分已全部落盘：直接 done，免得 idle 空转
                e["status"] = "done"
                e["reason"] = None if scored else "无 score>=7 候选"
                e["updated_at"] = now()
                swept += 1
                continue
            todo_c = [c for c in e["candidates"] if c["score"] >= MIN_SCORE and c["name_zh"] not in have]
            if todo_c:
                job = (e, todo_c)
                break
        if swept:
            save_manifest(data, lines)
            print(f"[{now()}] swept {swept} screened -> done", flush=True)
            heartbeat("swept", f"{swept} done")
            n_push += 1
            if n_push % PUSH_EVERY == 0:
                git_push(f"daizhige sweep batch {now()}")
                heartbeat("pushed")
            continue
        if job:
            e, todo_c = job
            print(f"[{now()}] extract batch start: {e['source']} {[c['name_zh'] for c in todo_c[:BATCH]]}", flush=True)
            heartbeat("extracting", e["source"])
            def _ex(c):
                try:
                    r = extract_one(e, c, taken, known)
                    if "qid" in r:
                        taken.add(c["name_zh"])
                        e.setdefault("extracted_qids", []).append(r["qid"])
                        print(f"extracted {e['source']} -> {c['name_zh']} ({c['score']})")
                    else:
                        e.setdefault("extracted_qids", []).append(f"skip:{c['name_zh']}:{r.get('skip','')}")
                except (ValueError, y.YAMLError) as ex:
                    # 单人格式错误是确定性的，重试无用：记 skip 让整批继续推进
                    traceback.print_exc()
                    e.setdefault("extracted_qids", []).append(f"skip:{c['name_zh']}:parse_err:{str(ex)[:120]}")
                    print(f"parse-skip {e['source']} -> {c['name_zh']}: {str(ex)[:100]}")
                except Exception as ex:
                    # 网络/API 类异常是 transient 的：整 source 置 error 待人工复核
                    traceback.print_exc()
                    e["status"] = "error"
                    e["reason"] = f"extract {c['name_zh']}: {str(ex)[:300]}"
                    e["updated_at"] = now()
            with ThreadPoolExecutor(max_workers=WORKERS) as ex:
                list(ex.map(_ex, todo_c[:BATCH]))
            # 该 source 候选采完则 done（文件已存在也算完成，避免空转）
            scored = {c["name_zh"] for c in e["candidates"] if c["score"] >= MIN_SCORE}
            have = extracted_names(e)
            for c in e["candidates"]:
                if c["score"] >= MIN_SCORE and (EXTRACT_OUT / e.get("category", "") / f"{c['name_zh']}.yaml").exists():
                    have.add(c["name_zh"])
            # 去重 extracted_qids（同名只留首次，防 manifest 膨胀）
            seen, deduped = set(), []
            for q in (e.get("extracted_qids") or []):
                k = _qid_to_name(q)
                if k not in seen:
                    seen.add(k)
                    deduped.append(q)
            e["extracted_qids"] = deduped
            if scored <= have:
                e["status"] = "done"
            t1 = time.time()
            save_manifest(data, lines)
            print(f"[{now()}] extract batch done + manifest saved in {time.time()-t1:.1f}s", flush=True)
            heartbeat("extracted_saved")
            n_push += 1
            if n_push % PUSH_EVERY == 0:
                git_push(f"daizhige extract batch {now()}")
                heartbeat("pushed")
            continue
        print(f"idle: {Counter(e['status'] for e in data)}", flush=True)
        heartbeat("idle")
        time.sleep(60)

if __name__ == "__main__":
    main()
