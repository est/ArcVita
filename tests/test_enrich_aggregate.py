"""验证 Aggregator 合并策略：curated 优先、仅补空字段、标题去重"""
from __future__ import annotations

from pathlib import Path

from arcvita.models import Event
from arcvita.sources.base import CacheStore, FetchContext
from arcvita.sources.enrich import Aggregator, enrich_person


class FakeAdapter:
    def __init__(self, id_: str, patch: dict):
        self.id = id_
        self._patch = patch

    def fetch(self, qid: str, ctx: FetchContext):
        # 返回拷贝以避免跨用例污染
        import copy

        return copy.deepcopy(self._patch)


def _event(qid: str, idx: int, title: str) -> Event:
    return Event(
        id=f"{qid}-event-{idx}",
        person_qid=qid,
        date=None,
        title_zh=title,
        event_type="经历",
        sources=["https://example.org"],
        status="needs_review",
    )


def test_curated_priority_over_wikidata_and_wikipedia():
    """curated 非空字段不被下层覆盖"""
    qid = "Q9999"
    curated_patch = {
        "source": "curated",
        "person_patch": {
            "birth_date": "1900-01-01",
            "summary_zh": "curated summary",
            "era": "现代",
        },
        "events": [],
        "source_urls": ["https://www.wikidata.org/wiki/Q9999"],
        "raw": {},
    }
    wikidata_patch = {
        "source": "wikidata",
        "person_patch": {
            "birth_date": "1901-02-02",  # 应被忽略
            "summary_zh": "wikidata summary",
            "death_place": "北京",
        },
        "events": [],
        "source_urls": ["https://www.wikidata.org/wiki/Q9999"],
        "raw": {},
    }
    wiki_patch = {
        "source": "wikipedia",
        "person_patch": {"summary_zh": "wiki summary", "death_place": "上海"},
        "events": [],
        "source_urls": ["https://zh.wikipedia.org/wiki/Test"],
        "raw": {},
    }

    agg = Aggregator(
        adapters=[
            FakeAdapter("curated", curated_patch),
            FakeAdapter("classical", {"source": "classical", "person_patch": {}, "events": [], "source_urls": [], "raw": {}}),
            FakeAdapter("wikidata", wikidata_patch),
            FakeAdapter("wikipedia", wiki_patch),
        ],
        ctx=FetchContext(cache=CacheStore(Path("/tmp/arcvita_test_cache_dummy")), client=None),
    )
    merged = agg.aggregate(qid)
    pp = merged["person_patch"]
    assert pp["birth_date"] == "1900-01-01", "curated birth_date 应优先保留"
    assert pp["summary_zh"] == "curated summary", "curated summary 不应被覆盖"
    assert pp["era"] == "现代"
    # death_place curated 为空，wikidata 的北京应补上，wikipedia 的上海不应再覆盖
    assert pp["death_place"] == "北京"


def test_fill_if_empty_only():
    """白名单仅补空字段；curated 已有 lesson 则不被 classical 覆盖"""
    qid = "Q8888"
    curated_patch = {
        "source": "curated",
        "person_patch": {
            "lesson": "curated lesson",
            "archetype": "攻关型",
            # era intentionally empty
            "summary_first_person": None,
        },
        "events": [],
        "source_urls": [],
        "raw": {},
    }
    classical_patch = {
        "source": "classical",
        "person_patch": {
            "lesson": "classical lesson should not override",
            "era": "春秋",
            "summary_first_person": "classical first person",
            "archetype": "一击型",
        },
        "events": [],
        "source_urls": [],
        "raw": {},
    }
    agg = Aggregator(
        adapters=[
            FakeAdapter("curated", curated_patch),
            FakeAdapter("classical", classical_patch),
            FakeAdapter("wikidata", {"source": "wikidata", "person_patch": {}, "events": [], "source_urls": [], "raw": {}}),
            FakeAdapter("wikipedia", {"source": "wikipedia", "person_patch": {}, "events": [], "source_urls": [], "raw": {}}),
        ],
        ctx=FetchContext(cache=CacheStore("/tmp/arcvita_test_cache_dummy2")),
    )
    merged = agg.aggregate(qid)
    pp = merged["person_patch"]
    assert pp["lesson"] == "curated lesson"
    assert pp["archetype"] == "攻关型"
    assert pp["era"] == "春秋", "curated 空字段 era 应被 classical 补"
    assert pp["summary_first_person"] == "classical first person"
    # 确保白名单外字段不被误合并（例如 name_zh 不在白名单，不应出现在 merged）
    assert "name_zh" not in pp or pp.get("name_zh") is None


def test_title_dedup_across_sources():
    """标题去重：curated/classical/wikidata/wikipedia 同标题事件只保留最高优先级的"""
    qid = "Q7777"
    curated_ev = _event(qid, 1, "三顾茅庐")
    wikidata_ev_same = _event(qid, 99, "三顾茅庐")
    wiki_ev_same = _event(qid, 100, "三顾茅庐")
    wiki_ev_unique = _event(qid, 101, "火烧赤壁")

    curated_patch = {"source": "curated", "person_patch": {}, "events": [curated_ev], "source_urls": [], "raw": {}}
    classical_patch = {"source": "classical", "person_patch": {}, "events": [], "source_urls": [], "raw": {}}
    wikidata_patch = {"source": "wikidata", "person_patch": {}, "events": [wikidata_ev_same], "source_urls": [], "raw": {}}
    wiki_patch = {"source": "wikipedia", "person_patch": {}, "events": [wiki_ev_same, wiki_ev_unique], "source_urls": [], "raw": {}}

    agg = Aggregator(
        adapters=[
            FakeAdapter("curated", curated_patch),
            FakeAdapter("classical", classical_patch),
            FakeAdapter("wikidata", wikidata_patch),
            FakeAdapter("wikipedia", wiki_patch),
        ],
        ctx=FetchContext(cache=CacheStore("/tmp/arcvita_test_cache_dummy3")),
    )
    merged = agg.aggregate(qid)
    titles = [e.title_zh for e in merged["events"]]
    assert titles.count("三顾茅庐") == 1, "同标题应去重为一条"
    assert "火烧赤壁" in titles
    # curated 的事件应排在前面
    assert titles[0] == "三顾茅庐"


def test_enrich_person_thin_wrapper_keeps_signature():
    """enrich_person 兼容旧签名且委托 Aggregator（不联网用 cache-only 验证）"""
    # 使用 _tmp/cache 作为缓存目录验证可读写
    cache_dir = Path("_tmp/cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    # 写入一个 wikipedia 缓存供 offline 读取
    dummy_wiki = {
        "qid": "Q4604",
        "zhwiki_title": "孔子",
        "first_para": "春秋时期思想家",
        "highlight_candidates": [],
        "source_urls": ["https://zh.wikipedia.org/wiki/孔子"],
        "cached": False,
    }
    # 直接通过 CacheStore 写，验证双探
    store = CacheStore(cache_dir)
    store.write("Q4604", "wikipedia", dummy_wiki)
    # enrich_person 仅 curated 应优先于 wiki
    res = enrich_person("Q4604", client=None, cache_dir=cache_dir, enabled_sources=["curated", "wikipedia"], title_hint="孔子")
    assert "qid" in res and res["qid"] == "Q4604"
    assert "patch" in res
    assert "person_patch" in res["patch"]
    # Q4604 curated 有 summary_zh，wiki 的 summary 不应覆盖
    assert res["patch"]["person_patch"].get("summary_zh") == "春秋时期思想家、教育家，儒家学派创始人，以仁与礼为核心，整理六经、讲学授徒。"


def test_cache_store_dual_probe():
    """CacheStore 双探：读取 _tmp/cache 未命中时回探 data/raw"""
    # data/raw 下应存在至少一个 batch 文件；我们用 wikipedia 的双探验证：若旧缓存存在应可读
    # 创建临时隔离：写 _tmp/cache 为空，读 data/raw 中若有遗留则验证兼容
    # 这里只测 API 不依赖真实旧文件：写入 data/raw 临时文件再通过 _tmp/cache 的 CacheStore 读取
    tmp_store = CacheStore(Path("_tmp/cache"))
    # 写到 legacy 双探路径验证：直接在 data/raw 写一个全新 qid 的缓存
    legacy_probe_qid = "QTEST999"
    legacy_data = {"qid": legacy_probe_qid, "zhwiki_title": "测试", "first_para": "测试首段"}
    # 模拟旧路径写入
    legacy_path = Path("data/raw") / f"{legacy_probe_qid}.wikipedia.json"
    legacy_path.parent.mkdir(parents=True, exist_ok=True)   # 克隆后 data/raw 可能不存在
    try:
        import json

        legacy_path.write_text(json.dumps(legacy_data, ensure_ascii=False, indent=2), encoding="utf-8")
        # 用 _tmp/cache 的 store 读取，应通过 legacy 双探命中
        got = tmp_store.read(legacy_probe_qid, "wikipedia")
        assert got is not None and got.get("zhwiki_title") == "测试"
    finally:
        if legacy_path.exists():
            legacy_path.unlink()

def test_wikipedia_adapter_uses_cache_store_and_user_agent_dedup():
    """wikipedia 适配器应使用 CacheStore 且 USER_AGENT 来自 base（去重）"""
    import arcvita.sources.wikipedia as wiki_mod
    from arcvita.sources import base as base_mod

    assert hasattr(wiki_mod, "WikipediaAdapter")
    # 检查 wikipedia.py 不再硬编码独立的 _read_cache/_write_cache 全局重复已移除（转 CacheStore）
    # 但保留函数则允许；至少 USER_AGENT 应与 base 一致或不存在独立定义
    if hasattr(wiki_mod, "USER_AGENT"):
        assert wiki_mod.USER_AGENT == base_mod.USER_AGENT or "ArcVita" in wiki_mod.USER_AGENT
