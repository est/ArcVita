from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["模范", "教训", "中性"]
Sensitivity = Literal["none", "sensitive"]
Visibility = Literal["public", "restricted"]
Status = Literal["verified", "needs_review", "ai_filled"]
DatePrecision = Literal["day", "month", "year"]
HighlightType = Literal["成语", "代表作", "名言", "战役", "发明", "制度", "演讲", "奖项", "远航", "决策"]


class LocalizedNames(BaseModel):
    zh: str | None = None
    en: str | None = None

    model_config = {"extra": "allow"}  # 允许 ja/de 等扩展语言


class DateInfo(BaseModel):
    date: str | None = None  # ISO，如 -551-09-28 / 1905
    precision: DatePrecision | None = None
    is_circa: bool = False
    raw: str | None = None  # 原始写法，如 约-537 / 前5


class PlaceRef(BaseModel):
    name_zh: str | None = None
    names: dict[str, str] | None = None  # 多语言，块式
    qid: str | None = None
    coord: list[float] | None = None


class Lifespan(BaseModel):
    birth: DateInfo | None = None
    death: DateInfo | None = None
    birth_place: PlaceRef | None = None
    death_place: PlaceRef | None = None


class Person(BaseModel):
    qid: str = Field(description="Wikidata QID 优先，否则 av:guji-xxx，例 Q935")
    # 新式多语言名（块式），旧 name_zh/name_en 保留作兼容
    names: LocalizedNames | dict[str, str] | None = None
    name_zh: str
    name_en: str | None = None
    aliases: list[str] = Field(default_factory=list)
    # 新式 lifespan（块式），旧 birth_date 等保留作兼容
    lifespan: Lifespan | None = None
    birth_date: str | None = None
    death_date: str | None = None
    birth_place: str | None = None
    death_place: str | None = None
    occupations: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    era: str | None = Field(default=None, description="朝代/世纪，如 唐/17世纪")
    reign_ref: str | None = Field(default=None, description="天下共主外键，如 reign-qing-kangxi")
    role: Role = "中性"
    sensitivity: Sensitivity = "none"
    visibility: Visibility = "public"
    lesson: str | None = None
    summary_zh: str | None = Field(default=None, description="一句话厚重感概述")
    summary_first_person: str | None = Field(default=None, description="第一视角自述引述或拟述，突出境遇与抉择")
    archetype: str | None = Field(default=None, description="成事儿原型，如 统筹型/攻关型/开拓型/文化型")
    dilemmas: list[str] = Field(default_factory=list, description="境遇标签，如 流放/被贬/技术瓶颈/至暗时刻")
    keywords: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    status: Status = "needs_review"
    needs_review_reason: str | None = None


class Phase(BaseModel):
    key: str | None = Field(default=None, description="枚举：brewing/breakthrough/climax/closure，其余自定义")
    name: str = Field(description="阶段名，如 酝酿/破局/收束")
    labels: dict[str, str] | None = Field(default=None, description="多语言标签，块式，如 zh: 酝酿")
    start_date: str | None = None
    end_date: str | None = None
    place: str | None = None
    description_zh: str | None = None
    highlight: str | None = Field(default=None, description="本阶段名场面一句话")
    highlight_event_id: str | None = None


class Decision(BaseModel):
    date: str | None = None
    title_zh: str
    titles: dict[str, str] | None = None
    rationale: str | None = None
    alternatives: list[str] = Field(default_factory=list)
    place: str | None = None


class Endeavor(BaseModel):
    id: str = Field(description="如 Q935-endeavor-1")
    person_qid: str
    title_zh: str = Field(description="做事标题，如 万有引力研究 / 三次北伐")
    titles: dict[str, str] | None = Field(default=None, description="多语言标题，块式")
    domain: str | None = None
    domains: list[str] = Field(default_factory=list, description="多域，块式列表")
    start_date: str | None = None
    end_date: str | None = None
    start_precision: DatePrecision | None = None
    end_precision: DatePrecision | None = None
    places: list[str] = Field(default_factory=list, description="核心地点轨迹，块式")
    place_qids: list[str] = Field(default_factory=list)
    places_ref: list[PlaceRef] | None = Field(default=None, description="结构化地点，块式")
    status: Literal["完成", "未竟", "中断", "进行中"] | str = "完成"
    description_zh: str | None = Field(default=None, description="厚重叙述：背景-动机-阻力-抉择")
    outcome: str | None = None
    lesson: str | None = Field(default=None, description="对后人的启发/教训")
    phases: list[Phase] = Field(default_factory=list, description="成事儿周期分解，强调从开头到结束")
    decisions: list[Decision] = Field(default_factory=list, description="关键抉择，支撑“做了什么决定”")
    dilemmas: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    event_ids: list[str] = Field(default_factory=list)
    highlight_event_ids: list[str] = Field(default_factory=list, description="名场面事件ID")
    sources: list[str] = Field(default_factory=list)
    review_status: Status = "needs_review"


class Event(BaseModel):
    id: str = Field(description="如 Q935-event-1")
    person_qid: str
    endeavor_id: str | None = Field(default=None, description="归属的做事单元，无则为人生节点")
    date: str | None = Field(default=None, description="ISO-8601, YYYY / YYYY-MM / YYYY-MM-DD，块式纯文本")
    date_info: DateInfo | None = Field(default=None, description="结构化日期，块式")
    date_precision: DatePrecision | None = None
    place_name: str | None = None
    place_qid: str | None = None
    place_coord: list[float] | None = None
    place: PlaceRef | None = None
    event_type: str = Field(description="出生/求学/任职/创作/战役/获奖/逝世等")
    title_zh: str
    titles: dict[str, str] | None = Field(default=None, description="多语言标题，块式")
    description_zh: str | None = None
    first_person_quote: str | None = Field(default=None)
    is_highlight: bool = Field(default=False, description="是否为名场面/代表作/成语诞生点")
    highlight_type: HighlightType | str | None = None
    highlight_note: str | None = Field(default=None, description="名场面补充，如 成语释义/作品影响")
    # 内联高亮（替代独立 highlights.yaml）
    highlight: dict[str, Any] | None = Field(default=None, description="块式，如 type: 代表作, note: ...")
    sources: list[str] = Field(default_factory=list)
    status: Status = "needs_review"
    needs_review_reason: str | None = None


class Reign(BaseModel):
    id: str = Field(description="如 reign-qing-kangxi")
    polity: str = Field(description="政权，如 清/唐/罗马")
    title_zh: str | None = None
    titles: dict[str, str] | None = None
    names: dict[str, str] | None = None
    start_date: str | None = None
    end_date: str | None = None
    start: DateInfo | None = None
    end: DateInfo | None = None
    predecessor: str | None = None
    successor: str | None = None
    capital: str | None = None
    capitals: list[str] | None = None
    sources: list[str] = Field(default_factory=list)
