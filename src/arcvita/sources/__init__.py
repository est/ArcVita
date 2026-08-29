"""arcvita.sources — 多源聪明采集层（可插拔、带降级）

- curated 永远优先，不改静态数据
- wikipedia / wikidata(openalex_wb) 均为“补丁源”，失败自动降级到缓存/离线
- 对外统一入口: enrich_person(qid, client)
"""
from arcvita.sources.enrich import enrich_person

__all__ = ["enrich_person"]
