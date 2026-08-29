# ArcVita — 网页设计需求 (site/design.md)

> 目标：人生迷茫时，查一个类似境遇的历史人物，从他的做事周期得到启发。网页是唯一的交付物 — 水平时间轴是主视图，不是可有可无的列表。

## 0. 约束

- **无构建**：`python -m http.server -d site` 直开即可。`site/static/app.js` 单文件普通 `<script>`，`site/static/style.css` 单文件，无 `import`、无 `node_modules`、无打包。
- **临时文件**：一律写项目内 `_tmp/`，不碰 `/tmp`。
- **数据只读**：前端只读 `site/data/*`，不改后端。`site/data` 由 `scripts/build_site.py` 生成，已按世纪分片，提交时保持 25 个 JSON + `timeline.jsonl/highlights.json/index.json`。
- **提交纪律**：用户说“提交再提交”，不要自动 `git commit/push`。

## 1. 卖点与信息架构

- **做事流**：每人 1–4 个 `Endeavor`（事业周期），每个 `Endeavor` 含 `phases[]`（酝酿→破局→高潮→收束）、地点轨迹、今地名、第一人称叙述。
- **名场面**：`Event.is_highlight + highlight_type`（王表/战役/成语/代表作/制度/名言/发明/演讲/奖项/远航…），共 517，人物 366 + 王表 113。
- **同期年龄对比**：hover 任一事件点，**左侧人名旁**显示当时存活者的年龄（本人棕色加粗，逝者不显示），这是灵魂功能，不能做成弹窗。
- **天下共主世系**：113 代君主已在数据中，视觉上与人物同为一行。
- **数据实体**：
  ```
  Person { qid, name_zh, era, archetype, role(模范/教训/中性), birth_date, death_date, birth_place, summary_zh, summary_first_person, lesson, dilemmas[], endeavors[] }
  Endeavor { title_zh, domain, start_date, end_date, places[], phases[{name, start_date, end_date, place, highlight}], description_zh, outcome, lesson }
  Event { date, place_name(已含今地名), event_type, title_zh, is_highlight, highlight_type, highlight_note }
  Century { bce2100…ce2000, unknown }  // index.json → century JSON 懒加载
  ```

## 2. 布局（已验证可行的骨架）

```
header (44px): [ArcVita 副标题] [搜索框] [− 1.0x·150年 + 重置] [stats]
timeline-wrap (flex:1, overflow:auto, min-height:0)
  tl-inner (position:relative, width = span*10px+240)
    axis-row (sticky top:0, 32px, 年刻度)
    p-row (50px, 相对定位, border-bottom)
      p-label (sticky left:0, 168px, z-index:3, background:paper)  ← 必须粘住，不随横向滚动消失
        dot(模范绿/教训红/中性灰)  p-name( flex:1; min-width:0 )  p-age(等宽)  arch  ed-count
      p-track (absolute left:168px, right:0)
        lifespan (4px 细线)
        ev-dot (birth绿/death红/normal黑/highlight金, 10→13px)
        ev-title / ev-age (仅 highlight/birth/death 在 zoom≥0.8 显示)
        ed-bar/phase (仅聚焦时展开, 148px 高)
tip (fixed, z-index:100, 380px, 跟随光标，防溢出)
detail (fixed right 380px 抽屉, 仅点击 dot/label 时打开)
```

- 已移除：**不要**再做 `#filters` / `.subbar` / `chips/minimap` 导航大坨。用户明确“删了，一大坨占地方，点了又没反应”。仅保留 header 的搜索与缩放。
- 响应式：`<768px` 时 `p-label` 112px，行高 44px，`detail` 全宽。

## 3. 视觉 Token（卷轴纸感，非中台卡片）

- `:root` 已在 `site/static/style.css` 定义：`--paper #f5f0e8, --ink #1a1a1a, --accent #7a3a10, --gold #9a7611, --jade #2b7a4a, --mist, --ruler`，`--c-成语/战役/王表…` 12 色，`--row-h 50px, --row-h-focus 148px, --label-w 168px`。
- 要求：**样式与逻辑解耦**，JS 只写 `data-qid/date`，颜色由 CSS 变量决定，换肤零 JS 改。
- 坚持纸+墨点+细线史学感，拒绝圆角卡片堆砌。动效仅 `150ms ease` 的 drawer/hover。

## 4. 交互（必须全部可用，否则视为失败）

- **横向滚动**：`timeline-wrap` 横向滚动不带走 `p-label`（sticky left:0）。纵向滚动正常。
- **缩放**：`Ctrl+滚轮` 以光标为锚点缩放（0.15–40x，1x=10px/年），`+/-` 按钮，`重置` 回 1x。`#zoomLevel` 显示 `1.2x · 320年` 或 `聚焦 XXX`。
- **搜索**：`#q` 实时过滤（debounce 200ms），匹配 `name_zh/name_en/archetype/era/dilemmas`，大小写不敏感；`/` 聚焦，`×` 清空；`#clearSearch` 可点；hash `q` 同步。
- **聚焦**：点击 `p-label` → 该行 148px 展开 `ed-bar/phase`，其余行 `dim 0.32`（**不要隐藏**，保留同期参照）；`minY/maxY` 锚到该人 `lifespan±20%`（至少 30 年）；`URL #focus=QID`，再点或 `ESC` 退出。
- **同期年龄**：hover 任一 `ev-dot` → 左侧所有存活者 `p-age` 显示 `ageAt(birth, eventYear)`，本人加粗棕色，逝者隐藏，`age<-80` 不显示；用单次委托 + `rAF`，**不能闪烁**。
- **事件点**：按 `W` 12px 阈值，`normal` 点可聚合成 `+N` 簇（`is_highlight` 永不聚），`highlight` 永远单点金色。
- **Tip**：`mouseover .ev-dot` 显示 `title/date/place/hl/desc/type`，`mousemove` 跟随光标且防溢出（翻面），`mouseleave/mouseout` 离开 `inner` 立即隐藏。**不能残留**。
- **详情**：点击 `ev-dot`（非簇）→ 右侧 `detail` 抽屉显示 `summary_first_person/summary_zh/lesson + endeavors + 时间线`，`×` 或 `ESC` 关闭。
- **拖拽**：`mousedown` 拖拽横向滚动，`1.2x` 阻尼；键盘 `+/-` 同缩放。

## 5. 数据加载

- `loadAll()`：`fetch data/index.json` → `Promise.allSettled` 并行拉 `century JSON` → 再并行 `timeline.jsonl + highlights.json`。`persons` 按 `birth_date` 排序。
- `pEvents` 优先用 `p.events`（世纪分片自带完整），`DATA.events` 仅备选。否则会出现“渲染不完全”。
- `computeDomain` 取 `events+highlights` 的 `parseYear` 最小最大 ±20 年；`focused` 时取该人 lifespan。
- `W = max(900, span*10+240)`，`stepFor` 按 `visible=span/ppx` 5/10/20/50/100。

## 6. 已知坑（本轮暴露，必须避免）

- **粘滞失效**：曾因 `.timeline-wrap` 未 `min-height:0` 或 `.p-name` 缺 `min-width:0; flex:1` 导致人名被挤成一字或随滚动消失。修复：`p-name {flex:1; min-width:0}`，`arch {flex-shrink:0}`，`timeline-wrap {overflow:auto; min-height:0}`。
- **事件缺失**：曾因 `clusterEvents` 阈值过大或用全局 `DATA.events` 而非 `p.events` 导致。修复：`p.events` 优先，簇阈 12px 且 highlight 永不聚。
- **Tip 残留**：曾因 `mousemove` 无 `dot` 时仍 `showTip(lastTarget)` 且 `render()` 内重复绑定监听导致。修复：监听一次性委托在 `setupInteractions`（`inner._hoverBound` 守卫），`mousemove` 空地上 `hideTip`。
- **导航大坨**：`#filters/.subbar/chips/minimap` 已按用户要求删除，不要再加回。

## 7. 文件与职责（无构建）

- `site/index.html`：仅结构（header + timeline-wrap/inner + tip/detail + `<script src="static/app.js">`），无 `type="module"`。
- `site/static/style.css`：单文件，合并 `tokens + timeline + overrides`，约 210 行。
- `site/static/app.js`：单文件普通 JS（~500 行），内联 `loadAll/parseYear/computeDomain/stepFor/ticks/initTip/showTip/hideTip/clusterEvents/render/setupInteractions/showDetail`，无 `import`。
- `site/data/*`：只读，`scripts/build_site.py` 生成。

## 8. 验收

- `python -m http.server -d site 8000` 直开：横向滚动人名**不消失**且宽度足够（≥6 字不截一字）、事件点**全部**可见、hover tip 移出**立即消失**、聚焦/搜索/缩放/拖拽均可用。
- 控制台无 `404`/`import` 错误，单请求 `app.js` + 单请求 `style.css`。
- `uv run pytest -q` 32 passed（仅校验 `site/data`，与前端无关但需保持）。

## 9. 给下一任的起点

- 从 `git log --oneline -3` 的 `19e3bd1` 开始，该提交已是单文件可用基线，但仍有上述 4 坑待验。
- 删掉当前 `site/static/app.js` 与 `site/static/style.css` 再重写，保留 `site/data` 与本 `design.md`。
- 临时文件一律 `_tmp/`，不碰 `/tmp`。
