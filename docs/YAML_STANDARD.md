# YAML 块式标准（ArcVita 数据层）

> 目标：AI 批量产出不翻车、Git diff 可读、人类可手改。所有 `data/**/*.yaml` 必须遵循。

## 硬性规则

1. **只用块式（block style），禁用流式**
   - 禁止 `{}` / `[]` / `["a", "b"]` / `{"zh": "孔子"}` 这种行内 JSON 写法。
   - 列表一律 `- ` 开头，每项一行；映射一律 `key: value` 换行缩进。
   - 空集合不输出：空列表/空字典/`null` 字段直接省略（而非 `aliases: []` / `death_place: null`）。

   ```yaml
   # 好
   occupations:
     - 思想家
     - 教育家
   dilemmas:
     - 怀才不遇
     - 被误解

   # 坏
   occupations: ["思想家", "教育家"]
   dilemmas: []
   ```

2. **尽量无引号，必须引号时用单引号**
   - 纯文本、中文字段一律不加引号：`title_zh: 虎门销烟`。
   - 仅当 YAML 会误解析时才加单引号：`'1472-10-31'`（否则会被当作 date 类型）、`'yes'` / `'null'` 等保留字、以 `:` / `#` 开头的字符串。
   - 禁止双引号 `"`（AI 易忘记转义内部引号，且 diff 噪音大）。

3. **Unicode 明文，不转义**
   - `allow_unicode: true`，中文直接写 `孔子` 而非 `\u5b54\u5b50`。

4. **缩进与宽度**
   - 缩进 2 空格；`width: 100` 后自动换行，长文案靠前换行而非行内折叠。

## 多语言与结构化字段的写法

多语言对象用块式映射，而非行内字典：

```yaml
# 好
names:
  zh: 孔子
  en: Confucius
titles:
  zh: 奇迹年四篇论文
  en: Four papers in Annus Mirabilis

# 坏
names: {zh: 孔子, en: Confucius}
```

结构化日期/地点同样块式：

```yaml
lifespan:
  birth:
    date: -551-09-28
    precision: day
    is_circa: false
  birth_place:
    name_zh: 曲阜
    qid: Q12345
```

阶段四色用 `key` 枚举 + `labels` 块式：

```yaml
phases:
  - key: brewing
    name: 酝酿
    labels:
      zh: 酝酿
      en: Brewing
    start_date: '-497'
    highlight_event_id: Q4604-event-2
```

## 工具约束

- 写盘统一走 `arcvita.core.yaml_utils.dump_block_yaml`（`default_flow_style=False` + `BlockDumper` + `strip_empty`），禁止直接 `yaml.safe_dump(..., width=100)`。
- 新增的 `Person.lifespan/names/titles`、`Endeavor.decisions/places_ref`、`Event.date_info/place` 均为可选，旧 `name_zh/birth_date` 保留兼容期，AI 产出优先新块式字段。
- CI 校验：`grep -R '\["' data/` / `grep -R '"title' data/` 命中即失败；空 `[]` / `{}` 命中即失败。

## 为什么这样定

- **AI 翻车率**：流式括号/逗号/引号嵌套是 AI 最易漏闭合、错转义的语法；块式每行一键值对，容错率高。
- **Git diff**：`["a","b"] -> ["a","b","c"]` 是一行改一行；块式是 `+   - c` 一行新增，Review 可精确定位。
- **与现有数据一致**：`site/data/persons.yaml:9` 已是 `occupations:\n  - 思想家` 块式，仅需把残留的 `aliases: []` / `death_place: null` / `'1472-10-31'` 单引号收敛为空省略或必要单引号。

## 反例自检

```bash
# 应无输出才算通过
rg '\[.*\]' data/processed/*.yaml
rg '\{' data/processed/*.yaml
rg '"' data/curated/classical/*.yaml
```
