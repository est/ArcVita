#!/usr/bin/env python3
"""监督闭环：自动采集 -> 定期检查&push -> 改进 -> 继续"""
import pathlib, yaml, json, time, subprocess, datetime, sys, os, traceback
ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT/".mimocode/daizhige_manifest.yaml"
EXTRACTED = ROOT/"data/extracted/daizhige"
TMP = ROOT/"tmp/daizhige_work"
TMP.mkdir(parents=True, exist_ok=True)
import sys as _sys
_sys.path.insert(0, str(ROOT/"src"))
from arcvita.core.yaml_utils import BlockDumper
import yaml as y

# 加载 .env（不打印密钥）
def _load_dotenv():
    envp = ROOT/".env"
    if envp.exists():
        for line in envp.read_text().splitlines():
            line=line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k,v=line.split("=",1)
            k=k.strip(); v=v.strip().strip('"').strip("'")
            if k not in os.environ:
                os.environ[k]=v
_load_dotenv()
BATCH_SIZE = int(os.environ.get("AI_BATCH_SIZE","5"))
CHECK_INTERVAL = 300  # 5min 检查一次
MAX_FILES = 105  # 优先 史藏/传记 105 档试点，跑完再扩

def load_manifest():
    lines = open(MANIFEST, encoding="utf-8").read().splitlines()
    body = "\n".join(l for l in lines if not l.startswith("#"))
    return y.safe_load(body), lines

def save_manifest(data, header_lines):
    header = "\n".join(l for l in header_lines if l.startswith("#"))+"\n"
    body = y.dump(data, allow_unicode=True, sort_keys=False, width=100, default_flow_style=False, Dumper=BlockDumper)
    open(MANIFEST,"w",encoding="utf-8").write(header+body)

def git_push(msg):
    try:
        subprocess.run(["git","-C","data","add","extracted/daizhige","extracted/manifest.yaml"], check=False)
        # 根 manifest 在主仓，不进 data 子模块
        subprocess.run(["git","add",".mimocode/daizhige_manifest.yaml"], check=False)
        r = subprocess.run(["git","-C","data","diff","--cached","--stat"], capture_output=True, text=True)
        if not r.stdout.strip():
            return False
        subprocess.run(["git","-C","data","commit","-m",msg], check=False)
        p = subprocess.run(["git","-C","data","push"], capture_output=True, text=True)
        print(f"git push: {p.returncode} {p.stdout[:200]} {p.stderr[:200]}")
        return p.returncode==0
    except Exception as e:
        print(f"git fail {e}")
        return False

def run_batch():
    sys.path.insert(0, str(ROOT/"scripts"))
    from ai_batch_extract import call_ai
    import concurrent.futures
    data, header = load_manifest()
    pending = [e for e in data if e["status"]=="pending" and e["category"].startswith("史藏/传记")]
    if not pending:
        pending = [e for e in data if e["status"]=="pending"]
    batch = pending[:BATCH_SIZE]
    if not batch:
        print("no pending")
        return 0
    # 5并发
    def _process(entry):
        src = ROOT/"daizhigev20"/entry["source"]
        if not src.exists():
            entry["status"]="skipped"; entry["reason"]="missing"
            entry["updated_at"]=datetime.datetime.now().isoformat()
            return entry
        try:
            text = src.read_text(encoding="utf-8", errors="ignore")
            hint = entry["source"].split("/")[-1].replace(".md","")
            out = call_ai(text[:8000], hint)
            out = out.strip()
            if out.startswith("```"):
                out = "\n".join(out.splitlines()[1:])
                if out.endswith("```"):
                    out = out[:-3]
            parsed = y.safe_load(out)
            if not isinstance(parsed, dict) or "person" not in parsed:
                raise ValueError("missing person key")
            person = parsed["person"]
            qid = person.get("qid") or f"guji-{person.get('name_zh','unknown')}"
            out_path = EXTRACTED/entry["category"]/f"{person.get('name_zh')}.yaml"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            from arcvita.core.yaml_utils import dump_block_yaml
            dump_block_yaml(out_path, parsed, strip_empty=True)
            entry["status"]="done"
            entry["output_qids"]=[qid]
            print(f"done {entry['source']} -> {qid}")
        except Exception as e:
            traceback.print_exc()
            entry["status"]="error"
            entry["reason"]=str(e)[:500]
            open(TMP/f"error_{entry['source'].replace('/','_')}.log","w",encoding="utf-8").write(traceback.format_exc())
        entry["updated_at"]=datetime.datetime.now().isoformat()
        return entry

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        batch = list(ex.map(_process, batch))
    save_manifest(data, header)
    return len(batch)

if __name__=="__main__":
    print(f"supervise start {datetime.datetime.now().isoformat()} batch={BATCH_SIZE}")
    while True:
        n = run_batch()
        if n==0:
            print("all done, sleep")
            time.sleep(CHECK_INTERVAL)
            continue
        git_push(f"daizhige: batch {datetime.datetime.now().isoformat()} {n} files")
        # 简单改进钩子：若本批 error>2 则暂停提示改 prompt
        time.sleep(10)
