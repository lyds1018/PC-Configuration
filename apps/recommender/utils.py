from typing import Dict, List, Mapping

from compatibility import run_checks

from .scoring import WORKLOAD_GAME, WORKLOAD_OFFICE, WORKLOAD_PRODUCTIVITY


MAX_FEASIBLE_COMBOS = 500


def to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


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


def normalize_workload(value: str) -> str:
    text = (value or "").strip().lower()
    if text in {WORKLOAD_GAME, "游戏"}:
        return WORKLOAD_GAME
    if text in {WORKLOAD_OFFICE, "办公"}:
        return WORKLOAD_OFFICE
    if text in {WORKLOAD_PRODUCTIVITY, "生产力"}:
        return WORKLOAD_PRODUCTIVITY
    return WORKLOAD_GAME


def as_parts_payload(parts: Mapping[str, object]) -> Dict[str, object]:
    """将候选组合转换为兼容性检查所需的统一 payload。"""
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
    return to_float(getattr(part, "price", 0.0), 0.0)


def sum_price(parts: List[object]) -> float:
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
    return run_checks(dict(parts)).get("ok", False)


def is_limit_reached(feasible: List[Dict[str, object]]) -> bool:
    return len(feasible) >= MAX_FEASIBLE_COMBOS
