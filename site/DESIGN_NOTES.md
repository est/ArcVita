# ArcVita · site 设计备忘

> 供后续设计迭代参考：方向沿革、令牌、交互实现要点、踩过的坑。

## 方向沿革

- **2026-09 landing 版**（已废弃）：hero 设问 + 出发点/设计理念/交互规格/数据来源/快速开始五个说明 section，时间轴只是中间一节。
- **2026-09 应用版（现行）**：用户明确「不做 landing 和说明，直接时间轴」。index.html 只剩全屏应用壳：顶栏（品牌 + 数据规模计数）+ 100% 视口 canvas。说明类内容以 README 为唯一载体，页面内不再重复。
- **一句话概念不变**：漆黑档案室里的一条朝代光谱轴 —— 颜色即时间。

## 令牌（未变）

| 令牌 | 值 | 用途 |
|---|---|---|
| `--lacquer` | #16100A | 暖调漆黑底（非纯黑） |
| `--paper` | #EFE3CC | 陈纸正文 |
| `--cinnabar` | #E8502F | 朱砂主强调（名场面点/印章） |
| `--gold` | #D9A441 | 鎏金次强调（年份/年龄/刻度） |
| `--brown` | #D08B54 | 同期年龄“本人”高亮（README 要求棕色，为深底提亮） |
| 朝代色谱 | 8 色 | 数据编码：上古玉绿→周春秋青金→战国朱漆→秦玄紫→两汉鎏金→三国松石→帝制之后赭→近现代青灰 |
| 阶段四色 | 酝酿灰蓝/破局金/高潮朱/收束玉绿 | 做事周期条 |

**字体**：刻本宋体 display、楷体第一人称引文、苹方正文、等宽年份，全系统栈（中文 webfont 太大）。

## 应用版布局要点

- `body = flex column + height 100% + overflow hidden`；topbar 58px 静态行（不再是 fixed 浮层）；`.app/.tl-frame` flex 撑满余下视口，全幅无圆角。
- 顶栏右侧 `#tl-counts` 由 app.js 在数据载入后填充（渲染口径，见下）。
- 首访操作提示 `.tl-hints`：7s 或首次 pointerdown 后加 `.gone` 淡出。
- 移动端 720px 断点：topbar 52px、counts 隐藏、搜索缩窄、panel 变底部抽屉。375px 实测无横向溢出。

## 交互实现要点（改版前先读）

- 视图模型 `{x: 左缘年份, ppy: px/年, y}`；拖拽直控，释放转惯性（`exp(-4.5t)` 衰减），滚轮/聚焦/快跳走 tween（easeInOutCubic）。
- **默认视野 ≈ 200 年**：boot 目标 `ppy = W/200`（1920px 屏 ≈ README 1x = 10px/年）。用户反馈：一屏只看 2–3 个人、一辈子的事件点稀疏可点，比全局密铺好用。
- **hover 变暗要 subtle**：不在场行/条 alpha 0.55（用户反馈 0.2x 太暗）。
- 人物行 = 按生年排序；聚焦缩放 = 人生范围 ±15% 缓冲，行中心对视口中心：`view.y = row*ROW_H + ROW_H/2 - (H-RULER_H)/2`。
- 日期解析兼容「约-2100 / 前5 / -100-07-12 / 32」；卒年不详（曹沫）→ 生年+60 虚化尾段。
- 数据只预载 `index.json + timeline.jsonl`（事件点），世纪分片 `data/<century>.json` 在聚焦时惰性拉取并缓存。
- 全部动效有 `prefers-reduced-motion` 分支；canvas DPR ≤ 2。

## 数据口径（顶栏计数 vs 构建输出）

- 顶栏「99 人 · 626 事 · 366 幕名场面」= **实际渲染在轴上**的数字：事件流过滤掉无年份/所属人物无生年的条目（627→626）；朱砂点只画 `is_highlight=true` 的事件（366）。
- 构建输出「627 events / 517 highlights」是 YAML 条目总数：highlights.yaml 有 151 条未挂进事件流。两边口径不同，别当 bug 对齐。

## 踩过的坑

- **行绘制用 `p.name`，但数据映射没建 `name` 字段** → 左列全渲染 “undefined”。已修：loadTimelineData 映射时补 `name: p.name_zh`。新增字段消费时务必检查映射层。
- **数据未就绪时 `draw()` 越界**：`persons.length-1 = -1`，clamp 后仍访问 `persons[0].qid` 崩掉 RAF。已修：draw 开头 `if (!persons.length) return`。loading 期由状态浮层遮盖。
- 事件点悬停必须同时出“同期年龄”（README 明确），别把准线和 popover 做成互斥。
- 聚焦 y 目标要用世界坐标推（screenY = RULER_H + worldY - view.y），别把当前 view.y 混进公式。
- 高亮事件可能落在人物卒年之后（如大泽乡起义之于秦制）——空心点样式画在条外，别当 bug 过滤掉。

## 本地开发 / 数据

- `data/` 是 submodule（CloudSettler/ArcVita-Data），**已含 bulk-import 的旧数据**（0bd879d：extracted 76 + processed 109，99 人/627 事/517 幕；主仓 ac0b3c8 pin）。代码与数据各司其职：数据改动进子模块并推送，代码改动进主仓。
- 构建前端数据（读 data/processed → 写 gitignore 的 site/data/）：`uv run python scripts/build_site.py`。
- 预览：`uv run python -m http.server -d site 8080`。
- 历史备注：旧数据一度只能从主仓 git 历史（b3c6716）恢复到 .tmp/dev-data 做调试，bulk import 落地后该流程作废。

## 测试现状（2026-09）

- `uv run pytest tests/` **32 全过**。此前 `test_processed_yamls_exist` 因空骨架失败（bulk import 自愈）、`test_cache_store_dual_probe` 因 data/raw 目录缺失失败（测试已改为自建目录；子模块 .gitignore 改 `raw/* + !raw/.gitkeep` 让 raw/.gitkeep 可入库）。

## 未做 / 留给下一轮

- 非欧几里得（Poincaré）斜向滚动：README「高级交互」，尚未实现。
- 同龄对比（不同朝代同年龄对齐）与境遇检索：README 路线图 04/05。
- 名场面落地页（popover 内的成语/代表作跳专述）。
- playwright-cli 走 msedge（本机无 Chrome；`--browser msedge`）。
