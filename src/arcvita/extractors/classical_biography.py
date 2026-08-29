"""古籍传记 AI 提取 prompt + 结构化输出"""

EXTRACTION_PROMPT = """你是一位精通文言文的历史数据工程师，任务是从《史记》章节中提取人物的结构化传记数据。

请从以下章节中识别所有重要人物，为每人输出一个 YAML 文档（用 `---` 分隔多人）。

## 输出格式（每人一个 YAML 块）

```yaml
person:
  name_zh: "人名"
  name_en: "pinyin or English"
  birth_date: "YYYY 或 约-YYYY (BCE用负数)"
  death_date: "YYYY 或 约-YYYY"
  birth_place: "当时地名"
  era: "朝代/时期"
  archetype: "做事原型"
  dilemmas: ["境遇标签"]
  summary_zh: "一句话厚重感概述"
  summary_first_person: "第一视角自述"
  lesson: "启发一句话"

endeavors:
  - title_zh: "做事标题"
    domain: "领域"
    start_date: "开始时间"
    end_date: "结束时间"
    places: ["地点1", "地点2"]
    phases:
      - name: "阶段名"
        start_date: "时间"
        end_date: "时间"
        place: "地点"
        highlight: "本阶段名场面"
    description_zh: "厚重叙述"
    outcome: "结果"
    lesson: "启发"

events:
  - date: "时间"
    place_name: "地点"
    event_type: "事件类型"
    title_zh: "事件标题"
    description_zh: "简述"
    is_highlight: true/false
    highlight_type: "成语/代表作/战役/决策/至暗时刻/名言"
    highlight_note: "名场面释义"
```

## 关键要求
1. 做事单元必须有完整的 开始→过程→结束
2. 地点用当时地名
3. 日期用公元纪年（BCE用负数如 -512）
4. 名场面标注 highlight_type
5. 第一人称叙述要有历史厚重感
6. 章节包含多人时每人都要提取

## 章节内容
```
{chapter_content}
```
"""


def build_prompt(chapter_content: str) -> str:
    return EXTRACTION_PROMPT.format(chapter_content=chapter_content[:8000])
