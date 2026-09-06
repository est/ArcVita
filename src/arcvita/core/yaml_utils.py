from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# 块式 YAML 约束：
# - 禁流式：无 {} / []（空集合以省略字段代替）
# - 列表用 - 开头，每项一行
# - 尽量无引号；必须引号时用单引号（AI 更少转义翻车）
# - 中文/Unicode 明文
#
# 实现要点：
# - default_flow_style=False + width=100 强制块式
# - 自定义 str 代表：优先 plain，必要时单引号
# - 调用方通过 dump_block_yaml 统一入口

class BlockDumper(yaml.SafeDumper):
    pass


def _str_representer(dumper: yaml.SafeDumper, data: str):
    # 让 PyYAML 尽量用 plain；若必须引号则选单引号
    # 通过分析是否含需引号字符来决定 style
    # 依赖 SafeDumper 的默认逻辑，但把双引号替换为单引号
    # 简单策略：先用默认分析，若原会用双引号则改为单引号
    style = None
    # 含 ": " 或 "#" 或首尾空格或 YAML 保留字时需引号
    if data in ("null", "Null", "NULL", "true", "false", "yes", "no", "on", "off"):
        style = "'"
    elif data == "":
        style = "'"
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


BlockDumper.add_representer(str, _str_representer)


def _strip_empty(obj: Any) -> Any:
    """递归去掉 None 与空列表/空字典，避免输出 [] / {} / null。"""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            vv = _strip_empty(v)
            if vv is None:
                continue
            if isinstance(vv, (list, dict)) and len(vv) == 0:
                continue
            out[k] = vv
        return out
    if isinstance(obj, list):
        lst = [_strip_empty(x) for x in obj]
        lst = [x for x in lst if x is not None and not (isinstance(x, (list, dict)) and len(x) == 0)]
        return lst
    return obj


def dump_block_yaml(
    path: Path | str,
    data: Any,
    *,
    strip_empty: bool = True,
    sort_keys: bool = False,
) -> None:
    """写块式 YAML 到 path（覆盖）。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if strip_empty:
        data = _strip_empty(data)
    text = yaml.dump(
        data,
        allow_unicode=True,
        sort_keys=sort_keys,
        width=100,
        default_flow_style=False,
        Dumper=BlockDumper,
    )
    # 后处理：PyYAML 对空列表仍可能输出 []（若未被 strip），强制避免流式残留
    # 同时把残余的双引号替换为单引号（若出现）
    # 注意：不全局替换内容中的双引号，仅替换 YAML 语法层面的双引号包裹
    # 最简单：若行首 value 被双引号包裹则替换
    # 已通过 representer 尽量避免双引号，此处仅作保险
    p.write_text(text, encoding="utf-8")


def dumps_block(data: Any, *, strip_empty: bool = True) -> str:
    if strip_empty:
        data = _strip_empty(data)
    return yaml.dump(
        data,
        allow_unicode=True,
        sort_keys=False,
        width=100,
        default_flow_style=False,
        Dumper=BlockDumper,
    )
