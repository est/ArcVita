# ArcVita — 人物传记结构化采集

厚重感 + 第一视角 + 做事流。用户迷茫时，按境遇匹配历史人物，得到启发。

> **License**: Code MIT (`LICENSE`), Data CC BY-SA 4.0 (`LICENSE-DATA.md`). 上游 Wikidata CC0 / Wikipedia CC BY-SA 4.0；精编叙述亦按 CC BY-SA 4.0 发布。

## 落盘
- `data/processed/persons.yaml` — 人物（YAML 真源，无引号转义，AI 可逐字段查证）
- `data/processed/endeavors.yaml` — 事业（每件事有始有终 + 地点轨迹 + 厚重第一视角叙述）
- `data/processed/events.yaml` — 事件（人物-时间-地点，最小三元组）
- `data/biography.db` — SQLite（可由 YAML 重建，含 `timeline` / `public_persons` 视图）
- `data/processed/_report.md` — 覆盖率与示例

敏感人物（如 Q352）打 `sensitivity=sensitive` + `visibility=restricted`，落盘保留、查询层过滤。

## 跑
```bash
uv sync
uv run python -m arcvita.cli          # 全量 25 人，离线优先（不依赖 Wikidata 限流）
uv run python -m arcvita.cli --limit 5
uv run python -c "from arcvita.query import find_by_dilemma; print(find_by_dilemma('被流放'))"
```

## 境遇检索
```python
from arcvita.query import find_by_dilemma, find_by_place, timeline
find_by_dilemma("被流放")   # 王阳明/林则徐/曼德拉/拿破仑/乔布斯
find_by_dilemma("技术瓶颈") # 张衡/牛顿/居里夫人/袁隆平/爱因斯坦
find_by_place("伦敦")
timeline("Q935")  # 牛顿时间线（出生-求学-研究-创作-逝世，含地点）
```

## 模型
- Person: qid/name_zh/lesson/summary_first_person/era/visibility
- Endeavor: title_zh/start_date-end_date/places/description_zh/outcome/lesson
- Event: date/place_name/event_type/title_zh

线上可复用：Wikidata Action API / SPARQL 链路已接（当前离线优先以绕开限流，后续可切回在线增量）。
