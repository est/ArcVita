#!/usr/bin/env python3
"""批量 AI 抽取流水线 — 读 .env 密钥，块式 YAML 标准"""
from __future__ import annotations
import os, pathlib, json, time, sys, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".mimocode/daizhige_manifest.yaml"
DATA_EXTRACTED = ROOT / "data/extracted/daizhige"
TMP_WORK = ROOT / "tmp/daizhige_work"

# 不打印密钥，仅校验存在
def load_env():
    env_path = ROOT / ".env"
    if not env_path.exists():
        print("missing .env — 请按 .env.example 填写", file=sys.stderr)
        sys.exit(1)
    # 轻量 dotenv，不依赖外部库
    for line in env_path.read_text().splitlines():
        line=line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k,v=line.split("=",1)
        k=k.strip(); v=v.strip().strip('"').strip("'")
        if k not in os.environ:
            os.environ[k]=v
    for k in ("AI_API_KEY","AI_BASE_URL","AI_MODEL"):
        if not os.environ.get(k):
            print(f"missing {k} in .env", file=sys.stderr)
            sys.exit(1)
    print(f"env ok: base={os.environ['AI_BASE_URL']} model={os.environ['AI_MODEL']} batch={os.environ.get('AI_BATCH_SIZE','5')}")

PROMPT_SYSTEM = open(ROOT/"docs/YAML_STANDARD.md", encoding="utf-8").read()[:2000] if (ROOT/"docs/YAML_STANDARD.md").exists() else ""

PROMPT_TEMPLATE = """你是 ArcVita 古籍抽取器。按块式 YAML 标准从给定古文传记中提取 1 个人物。

【块式硬约束】
- 列表用 `- ` 每项一行，禁流式 [] / {{"a":1}} / ["a","b"]
- 外层禁双引号，必要时单引号；中文明文；空集合省略
- 见 docs/YAML_STANDARD.md

【模型】
person: {{qid: guji-<人名>, name_zh, names{{zh,en}}, lifespan{{birth{{date,precision,is_circa,raw}},death}}, birth_date/death_date(兼容旧), era, reign_ref, archetype, dilemmas[], lesson, summary_first_person, source_urls[]}}
endeavors: 每人≥2，含 phases[{{key: brewing/breakthrough/climax/closure, name, labels{{zh}}, start_date, highlight_event_id}}] + decisions[{{date,title_zh,rationale}}]
events: 含 birth/death + ≥2 事业事件，date 用 ISO（约-77 / -551-09-28），year_of 需可解析

【输出】
只输出一个 YAML 文档，结构正为：
person: {{...}}
endeavors:
  - id: guji-<人名>-endeavor-1
    ...
events:
  - id: guji-<人名>-event-birth
    ...

不要包裹 ```yaml，不要额外解释。
"""

def _ensure_env():
    if os.environ.get("AI_API_KEY") and os.environ.get("AI_BASE_URL"):
        return
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

def call_ai(text: str, person_hint: str) -> str:
    """调 Responses 接口 — 不打印密钥"""
    _ensure_env()
    import httpx
    base = os.environ["AI_BASE_URL"].rstrip("/")
    key = os.environ["AI_API_KEY"]
    model = os.environ["AI_MODEL"]
    # opencode zen uses /v1/responses
    url = base if base.endswith("/responses") else base + "/responses"
    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": PROMPT_TEMPLATE},
            {"role": "user", "content": f"人名提示：{person_hint}\n\n古文：\n{text[:8000]}"}
        ],
    }
    # 兼容 openai 风格：responses 失败（404/500等）则回落 chat/completions
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    for attempt in range(5):
        try:
            r = httpx.post(url, json=payload, headers=headers, timeout=300)
            if r.status_code != 200 and "responses" in url:
                # fallback chat/completions
                url2 = base.replace("/responses","/chat/completions")
                payload2 = {"model": model, "messages": [{"role":"system","content":PROMPT_TEMPLATE},{"role":"user","content": f"人名提示：{person_hint}\n\n古文：\n{text[:8000]}"}]}
                r = httpx.post(url2, json=payload2, headers=headers, timeout=300)
            r.raise_for_status()
            j = r.json()
            # responses API: output[0].content[0].text
            if "output" in j:
                out = j["output"]
                # flatten
                txt = ""
                for item in out:
                    if isinstance(item, dict) and "content" in item:
                        for c in item["content"]:
                            if c.get("type")=="output_text":
                                txt += c.get("text","")
                    elif isinstance(item, str):
                        txt+=item
                if txt.strip():
                    return txt
            if "choices" in j:
                return j["choices"][0]["message"]["content"]
            return json.dumps(j, ensure_ascii=False)
        except Exception as e:
            msg = str(e)
            # 429 限流 / 超时：指数退避更长等待（5次，最长 ~80s）
            if "429" in msg or "timed out" in msg:
                max_attempts = 5
            else:
                max_attempts = 3
            print(f"ai call attempt {attempt+1}/{max_attempts} failed: {msg[:200]}", file=sys.stderr)
            if attempt < max_attempts - 1:
                wait = 15 * (2 ** attempt) if ("429" in msg or "timed out" in msg) else 2 * (attempt + 1)
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("ai failed")

def test_connection():
    try:
        out = call_ai("测试：请只返回 YAML：person: {name_zh: 测试}", "测试")
        print("AI 连接成功，返回前200字：")
        print(out[:500].replace("\n","\\n")[:500])
        return True
    except Exception as e:
        print(f"AI 连接失败: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    load_env()
    if not test_connection():
        sys.exit(1)
    print("ready for batch — 后续批处理由 supervise 按 manifest 驱动")
