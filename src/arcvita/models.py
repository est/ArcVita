from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["模范", "教训", "中性"]
Sensitivity = Literal["none", "sensitive"]
Visibility = Literal["public", "restricted"]
Status = Literal["verified", "needs_review", "ai_filled"]
DatePrecision = Literal["day", "month", "year"]


class Person(BaseModel):
    qid: str = Field(description="Wikidata QID, e.g. Q935")
    name_zh: str
    name_en: str | None = None
    aliases: list[str] = Field(default_factory=list)
    birth_date: str | None = None
    death_date: str | None = None
    birth_place: str | None = None
    death_place: str | None = None
    occupations: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    era: str | None = Field(default=None, description="朝代/世纪，如 唐/17世纪")
    role: Role = "中性"
    sensitivity: Sensitivity = "none"
    visibility: Visibility = "public"
    lesson: str | None = None
    summary_zh: str | None = Field(default=None, description="一句话厚重感概述")
    summary_first_person: str | None = Field(default=None, description="第一视角自述引述或拟述，突出境遇与抉择")
    # 境遇-启发检索：用于“迷茫时查找类似境遇人物”
    dilemmas: list[str] = Field(default_factory=list, description="境遇标签，如 流放/被贬/众叛亲离/从零开始/技术瓶颈/至暗时刻/被误解")
    keywords: list[str] = Field(default_factory=list, description="检索关键词，与 dilemmas 联动，可扩展至领域/心态标签")
    source_urls: list[str] = Field(default_factory=list)
    status: Status = "needs_review"
    needs_review_reason: str | None = None


class Endeavor(BaseModel):
    id: str = Field(description="如 Q935-endeavor-1")
    person_qid: str
    title_zh: str = Field(description="做事标题，如 万有引力研究 / 三次北伐")
    domain: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    start_precision: DatePrecision | None = None
    end_precision: DatePrecision | None = None
    places: list[str] = Field(default_factory=list, description="核心地点轨迹")
    place_qids: list[str] = Field(default_factory=list)
    status: Literal["完成", "未竟", "中断", "进行中"] | str = "完成"
    description_zh: str | None = Field(default=None, description="厚重叙述：背景-动机-阻力-抉择")
    outcome: str | None = None
    lesson: str | None = Field(default=None, description="对后人的启发/教训")
    # 境遇-启发检索：做事维度的境遇标签，便于按“技术瓶颈/至暗时刻”等检索做事流
    dilemmas: list[str] = Field(default_factory=list, description="境遇标签，如 流放/被贬/技术瓶颈/至暗时刻")
    keywords: list[str] = Field(default_factory=list, description="检索关键词，与 dilemmas 联动")
    event_ids: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    review_status: Status = "needs_review"


class Event(BaseModel):
    id: str = Field(description="如 Q935-event-1")
    person_qid: str
    endeavor_id: str | None = Field(default=None, description="归属的做事单元，无则为人生节点")
    date: str | None = Field(default=None, description="ISO-8601, YYYY / YYYY-MM / YYYY-MM-DD")
    date_precision: DatePrecision | None = None
    place_name: str | None = None
    place_qid: str | None = None
    place_coord: list[float] | None = None
    event_type: str = Field(description="出生/求学/任职/创作/战役/获奖/逝世等")
    title_zh: str
    description_zh: str | None = None
    first_person_quote: str | None = Field(default=None, description="第一视角引述或拟述，增强代入感")
    sources: list[str] = Field(default_factory=list)
    status: Status = "needs_review"
    needs_review_reason: str | None = None
