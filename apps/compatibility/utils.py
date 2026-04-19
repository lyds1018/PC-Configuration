from __future__ import annotations

import json
import re
from typing import Any

# 板型等级排序
FORM_ORDER = {"ITX": 1, "MATX": 2, "M-ATX": 2, "MICROATX": 2, "MICRO ATX": 2, "ATX": 3}
# 电源规格等级排序
PSU_FORM_ORDER = {"SFX": 1, "ATX": 2}
# DDR 代数正则表达式
DDR_RE = re.compile(r"DDR\s*(\d+)", re.IGNORECASE)

# 数据读取函数
def read(source: Any, *fields: str) -> Any:
    """从字典或对象中读取字段值"""
    if source is None:
        return None
    for field in fields:
        if isinstance(source, dict) and field in source:
            return source[field]
        if hasattr(source, field):
            return getattr(source, field)
    return None


# 数据转换函数
def to_text(value: Any) -> str:
    """转换为字符串"""
    return str(value).strip() if value is not None else ""


def to_upper(value: Any) -> str:
    """转换为大写字符串"""
    return to_text(value).upper()


def to_float(value: Any) -> float | None:
    """转换为浮点数"""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(value: Any) -> int | None:
    """安全转换为整数"""
    num = to_float(value)
    return int(num) if num is not None else None


def parse_list(value: Any) -> list[str]:
    """将字符串或列表转换为大写字符串列表，支持逗号、斜杠、管道等分隔符"""
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [to_upper(v) for v in value if to_text(v)]

    text = to_text(value)
    if not text:
        return []

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [to_upper(v) for v in parsed if to_text(v)]
    except (TypeError, ValueError, json.JSONDecodeError):
        pass

    text = text.strip("[]")
    parts = re.split(r"[,/|\\]+", text)
    normalized = []
    for part in parts:
        cleaned = part.strip().strip("\"'")
        if cleaned:
            normalized.append(cleaned.upper())
    return normalized

# 数值提取函数
def ddr_rank(value: Any) -> int | None:
    """提取 DDR 代数 (如 DDR4 → 4)"""
    text = to_upper(value)
    if not text:
        return None
    match = DDR_RE.search(text)
    if match:
        return int(match.group(1))
    return None


def max_ddr_rank(value: Any) -> int | None:
    """从列表中获取最高 DDR 代数"""
    values = parse_list(value)
    if not values:
        return ddr_rank(value)

    ranks = [rank for rank in (ddr_rank(v) for v in values) if rank is not None]
    return max(ranks) if ranks else None


def form_rank(value: Any) -> int | None:
    """获取主板板型等级"""
    key = to_upper(value).replace("_", "").replace("-", "-")
    return FORM_ORDER.get(key)


def psu_form_rank(value: Any) -> int | None:
    """获取电源规格等级"""
    return PSU_FORM_ORDER.get(to_upper(value))


def max_radiator(value: Any) -> int | None:
    """提取最大冷排规格"""
    sizes = []
    for entry in parse_list(value):
        number = to_int(re.sub(r"[^0-9]", "", entry))
        if number is not None:
            sizes.append(number)
    return max(sizes) if sizes else None


# 其他工具函数
def contains_ddr(supported: Any, target: Any) -> bool:
    """返回 DDR 检查结果"""
    target_upper = to_upper(target)
    if not target_upper:
        return True

    supported_list = parse_list(supported)
    if supported_list:
        return target_upper in supported_list

    return to_upper(supported) == target_upper