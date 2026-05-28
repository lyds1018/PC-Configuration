"""推荐模块工具函数与常量"""

import math
from dataclasses import dataclass
from typing import Dict, List, Mapping

from compatibility import run_checks

# 组合枚举常量
MAX_CANDIDATES = 500
OUTPUT_CANDIDATES = 5

# 用途类型常量
WORKLOAD_GAME = "game"
WORKLOAD_OFFICE = "office"
WORKLOAD_PRODUCTIVITY = "productivity"

WORKLOAD_ALIASES = {
    "game": WORKLOAD_GAME,
    "office": WORKLOAD_OFFICE,
    "productivity": WORKLOAD_PRODUCTIVITY,
    "游戏": WORKLOAD_GAME,
    "办公": WORKLOAD_OFFICE,
    "生产力": WORKLOAD_PRODUCTIVITY,
}


@dataclass
class RecommendationRequest:
    """推荐请求参数：由表单输入。"""

    budget_min: float = 0.0
    budget_max: float = 0.0
    workload: str = WORKLOAD_GAME
    cpu_brand: str = ""
    gpu_chip_brand: str = ""
    gpu_card_brand: str = ""
    free_text: str = ""
    top_k: int = 3


def to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_log(value: float) -> float:
    if value <= 0:
        return 0.0
    return math.log(value)


def to_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def clamp_0_1(value: float) -> float:
    """限制在 [0, 1] 范围内。"""
    return max(0.0, min(1.0, value))


def normalize_brand(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    upper = text.upper()
    if upper in {"INTEL", "英特尔"}:
        return "英特尔"
    if upper in {"AMD"}:
        return "AMD"
    if upper in {"NVIDIA", "英伟达"}:
        return "NVIDIA"
    return text


def as_parts_payload(parts: Mapping[str, object]) -> Dict[str, object]:
    """将候选组合转换为兼容性检查所需的统一输入。"""
    storage = parts.get("storage")
    ram = parts.get("ram")
    storage_type = str(getattr(storage, "type", "")).upper()
    is_m2 = "M.2" in storage_type
    return {
        "cpu": parts.get("cpu"),
        "mb": parts.get("mb"),
        "ram": ram,
        "storage": storage,
        "gpu": parts.get("gpu"),
        "case": parts.get("case"),
        "psu": parts.get("psu"),
        "cooler": parts.get("cooler"),
        "storages": [{"type": getattr(storage, "type", "")}] if storage else [],
        "totals": {
            "total_m2": 1 if is_m2 else 0,
            "total_sata": 0 if is_m2 else 1,
            "total_sata_ssd": 1 if "SATA SSD" in storage_type else 0,
            "total_hdd": 1 if "HDD" in storage_type else 0,
            "total_memory": to_int(getattr(ram, "module_count", 1), 1),
        },
    }


def part_price(part) -> float:
    """读取单个配件价格并容错转换。"""
    return to_float(getattr(part, "price", 0.0), 0.0)


def sum_price(parts: List[object]) -> float:
    """计算配件列表总价。"""
    return sum(part_price(p) for p in parts if p is not None)


def scale_0_100(value: float) -> float:
    return max(0.0, min(100.0, value * 100.0))


def obj_to_score_dict(obj) -> Dict[str, float]:
    fields = [
        "single_score",
        "multi_score",
        "base_clock",
        "boost_clock",
        "core_count",
        "thread_count",
        "tdp",
        "gaming_score",
        "compute_score",
        "core_clock",
        "memory_clock",
        "vram_size",
        "capacity",
        "frequency",
        "latency",
        "cache_size",
        "read_speed",
        "write_speed",
        "random_read_iops",
        "random_write_iops",
    ]
    return {field: to_float(getattr(obj, field, 0.0), 0.0) for field in fields}


def is_compatible(parts: Mapping[str, object]) -> bool:
    """调用兼容性引擎并返回是否通过。"""
    return run_checks(dict(parts)).get("ok", False)


def min_price(parts: Mapping[str, List[object]], key: str) -> float:
    values = [part_price(item) for item in parts.get(key, [])]
    return min(values) if values else 0.0


def max_price(parts: Mapping[str, List[object]], key: str) -> float:
    values = [part_price(item) for item in parts.get(key, [])]
    return max(values) if values else 0.0


def normalize_budget_range(params: RecommendationRequest) -> tuple[float, float]:
    budget_min = max(0.0, to_float(params.budget_min, 0.0))
    budget_max = max(0.0, to_float(params.budget_max, 0.0))
    if budget_max <= 0:
        budget_max = 20000.0
    if budget_min > budget_max:
        budget_min, budget_max = budget_max, budget_min
    return budget_min, budget_max
