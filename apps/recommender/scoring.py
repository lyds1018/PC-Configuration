import math
from dataclasses import dataclass
from typing import Dict, Iterable, Mapping

# 用途类型常量
WORKLOAD_GAME = "game"
WORKLOAD_OFFICE = "office"
WORKLOAD_PRODUCTIVITY = "productivity"

WORKLOAD_ALIASES = {
    "游戏": WORKLOAD_GAME,
    "办公": WORKLOAD_OFFICE,
    "生产力": WORKLOAD_PRODUCTIVITY,
    WORKLOAD_GAME: WORKLOAD_GAME,
    WORKLOAD_OFFICE: WORKLOAD_OFFICE,
    WORKLOAD_PRODUCTIVITY: WORKLOAD_PRODUCTIVITY,
}


SUB_WEIGHTS = {
    WORKLOAD_GAME: {
        "cpu": {
            "single_score": 0.35,
            "multi_score": 0.15,
            "bb": 0.25,
            "ct": 0.10,
            "tdp": 0.15,
        },
        "gpu": {
            "gaming_score": 0.50,
            "compute_score": 0.10,
            "cm": 0.20,
            "vram_size": 0.10,
            "tdp": 0.10,
        },
        "ram": {"capacity": 0.50, "fl": 0.50},
        "storage": {"capacity": 0.20, "cache_size": 0.10, "sp": 0.50, "rand": 0.20},
    },
    WORKLOAD_OFFICE: {
        "cpu": {
            "single_score": 0.30,
            "multi_score": 0.25,
            "bb": 0.20,
            "ct": 0.15,
            "tdp": 0.10,
        },
        "gpu": {
            "gaming_score": 0.10,
            "compute_score": 0.20,
            "cm": 0.20,
            "vram_size": 0.20,
            "tdp": 0.30,
        },
        "ram": {"capacity": 0.60, "fl": 0.40},
        "storage": {"capacity": 0.30, "cache_size": 0.10, "sp": 0.30, "rand": 0.30},
    },
    WORKLOAD_PRODUCTIVITY: {
        "cpu": {
            "single_score": 0.15,
            "multi_score": 0.40,
            "bb": 0.10,
            "ct": 0.25,
            "tdp": 0.10,
        },
        "gpu": {
            "gaming_score": 0.10,
            "compute_score": 0.45,
            "cm": 0.15,
            "vram_size": 0.20,
            "tdp": 0.10,
        },
        "ram": {"capacity": 0.70, "fl": 0.30},
        "storage": {"capacity": 0.25, "cache_size": 0.15, "sp": 0.25, "rand": 0.35},
    },
}

TOTAL_WEIGHTS = {
    WORKLOAD_GAME: {"cpu": 0.25, "gpu": 0.50, "ram": 0.15, "storage": 0.10},
    WORKLOAD_OFFICE: {"cpu": 0.40, "gpu": 0.10, "ram": 0.30, "storage": 0.20},
    WORKLOAD_PRODUCTIVITY: {"cpu": 0.35, "gpu": 0.30, "ram": 0.20, "storage": 0.15},
}


@dataclass(frozen=True)
class MinMax:
    min_value: float
    max_value: float


@dataclass(frozen=True)
class NormalizationStats:
    cpu: Dict[str, MinMax]
    gpu: Dict[str, MinMax]
    ram: Dict[str, MinMax]
    storage: Dict[str, MinMax]


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_log(value: float) -> float:
    if value <= 0:
        return 0.0
    return math.log(value)


def _clamp_0_1(value: float) -> float:
    return max(0.0, min(1.0, value))


def _linear_norm(value: float, bounds: MinMax) -> float:
    denom = bounds.max_value - bounds.min_value
    if denom <= 0:
        return 0.0
    return _clamp_0_1((value - bounds.min_value) / denom)


def _log_norm(value: float, max_value: float) -> float:
    if value <= 0 or max_value <= 1:
        return 0.0
    denom = _safe_log(max_value)
    if denom <= 0:
        return 0.0
    return _clamp_0_1(_safe_log(value) / denom)


def _inverse_log_norm(value: float, max_value: float) -> float:
    if value <= 0 or max_value <= 1:
        return 0.0
    denom = _safe_log(max_value)
    if denom <= 0:
        return 0.0
    return _clamp_0_1(1 - (_safe_log(value) / denom))


def _cpu_features(cpu: Mapping[str, float]) -> Dict[str, float]:
    base_clock = _to_float(cpu.get("base_clock"))
    boost_clock = _to_float(cpu.get("boost_clock"))
    core_count = _to_float(cpu.get("core_count"))
    thread_count = _to_float(cpu.get("thread_count"))

    return {
        "single_score": _to_float(cpu.get("single_score")),
        "multi_score": _to_float(cpu.get("multi_score")),
        "bb": (base_clock + boost_clock) / 2.0,
        "ct": _safe_log(core_count * thread_count),
        "tdp": _to_float(cpu.get("tdp")),
    }


def _gpu_features(gpu: Mapping[str, float]) -> Dict[str, float]:
    core_clock = _to_float(gpu.get("core_clock"))
    memory_clock = _to_float(gpu.get("memory_clock"))
    return {
        "gaming_score": _to_float(gpu.get("gaming_score")),
        "compute_score": _to_float(gpu.get("compute_score")),
        "cm": (core_clock + memory_clock) / 2.0,
        "vram_size": _to_float(gpu.get("vram_size")),
        "tdp": _to_float(gpu.get("tdp")),
    }


def _ram_features(ram: Mapping[str, float]) -> Dict[str, float]:
    frequency = _to_float(ram.get("frequency"))
    latency = _to_float(ram.get("latency"), default=1.0)
    if latency <= 0:
        latency = 1.0

    return {
        "capacity": _to_float(ram.get("capacity")),
        "fl": frequency / latency,
    }


def _storage_features(storage: Mapping[str, float]) -> Dict[str, float]:
    read_speed = _to_float(storage.get("read_speed"))
    write_speed = _to_float(storage.get("write_speed"))
    random_read_iops = _to_float(storage.get("random_read_iops"))
    random_write_iops = _to_float(storage.get("random_write_iops"))

    return {
        "capacity": _to_float(storage.get("capacity")),
        "cache_size": _to_float(storage.get("cache_size")),
        "sp": (read_speed + write_speed) / 2.0,
        "rand": (random_read_iops + random_write_iops) / 2.0,
    }


def _build_bounds(
    items: Iterable[Mapping[str, float]], feature_builder
) -> Dict[str, MinMax]:
    values_by_feature: Dict[str, list] = {}
    for item in items:
        features = feature_builder(item)
        for name, value in features.items():
            values_by_feature.setdefault(name, []).append(value)

    bounds: Dict[str, MinMax] = {}
    for name, values in values_by_feature.items():
        if not values:
            bounds[name] = MinMax(0.0, 0.0)
            continue
        bounds[name] = MinMax(min(values), max(values))
    return bounds


def build_normalization_stats(
    cpus: Iterable[Mapping[str, float]],
    gpus: Iterable[Mapping[str, float]],
    rams: Iterable[Mapping[str, float]],
    storages: Iterable[Mapping[str, float]],
) -> NormalizationStats:
    """根据候选数据集构建归一化边界。"""
    return NormalizationStats(
        cpu=_build_bounds(cpus, _cpu_features),
        gpu=_build_bounds(gpus, _gpu_features),
        ram=_build_bounds(rams, _ram_features),
        storage=_build_bounds(storages, _storage_features),
    )


def _normalize_cpu(
    features: Dict[str, float], stats: NormalizationStats
) -> Dict[str, float]:
    return {
        "single_score": _linear_norm(
            features["single_score"], stats.cpu["single_score"]
        ),
        "multi_score": _linear_norm(features["multi_score"], stats.cpu["multi_score"]),
        "bb": _linear_norm(features["bb"], stats.cpu["bb"]),
        "ct": _linear_norm(features["ct"], stats.cpu["ct"]),
        "tdp": _inverse_log_norm(features["tdp"], stats.cpu["tdp"].max_value),
    }


def _normalize_gpu(
    features: Dict[str, float], stats: NormalizationStats
) -> Dict[str, float]:
    return {
        "gaming_score": _linear_norm(
            features["gaming_score"], stats.gpu["gaming_score"]
        ),
        "compute_score": _linear_norm(
            features["compute_score"], stats.gpu["compute_score"]
        ),
        "cm": _linear_norm(features["cm"], stats.gpu["cm"]),
        "vram_size": _linear_norm(features["vram_size"], stats.gpu["vram_size"]),
        "tdp": _inverse_log_norm(features["tdp"], stats.gpu["tdp"].max_value),
    }


def _normalize_ram(
    features: Dict[str, float], stats: NormalizationStats
) -> Dict[str, float]:
    return {
        "capacity": _linear_norm(features["capacity"], stats.ram["capacity"]),
        "fl": _linear_norm(features["fl"], stats.ram["fl"]),
    }


def _normalize_storage(
    features: Dict[str, float], stats: NormalizationStats
) -> Dict[str, float]:
    return {
        "capacity": _linear_norm(features["capacity"], stats.storage["capacity"]),
        "cache_size": _linear_norm(features["cache_size"], stats.storage["cache_size"]),
        "sp": _linear_norm(features["sp"], stats.storage["sp"]),
        "rand": _log_norm(features["rand"], stats.storage["rand"].max_value),
    }


def _weighted_score(features: Dict[str, float], weights: Dict[str, float]) -> float:
    return sum(features[name] * weight for name, weight in weights.items())


def _normalize_workload(workload: str) -> str:
    normalized = WORKLOAD_ALIASES.get(workload)
    if not normalized:
        raise ValueError(f"unsupported workload: {workload}")
    return normalized


def score_build(
    cpu: Mapping[str, float],
    gpu: Mapping[str, float],
    ram: Mapping[str, float],
    storage: Mapping[str, float],
    stats: NormalizationStats,
    workload: str,
) -> Dict[str, float]:
    """
    计算整机性能分数。
    返回值范围约为 [0, 1]，包含各子项分数与总分。
    """
    workload_key = _normalize_workload(workload)
    sub_weights = SUB_WEIGHTS[workload_key]
    total_weights = TOTAL_WEIGHTS[workload_key]

    cpu_norm = _normalize_cpu(_cpu_features(cpu), stats)
    gpu_norm = _normalize_gpu(_gpu_features(gpu), stats)
    ram_norm = _normalize_ram(_ram_features(ram), stats)
    storage_norm = _normalize_storage(_storage_features(storage), stats)

    cpu_score = _weighted_score(cpu_norm, sub_weights["cpu"])
    gpu_score = _weighted_score(gpu_norm, sub_weights["gpu"])
    ram_score = _weighted_score(ram_norm, sub_weights["ram"])
    storage_score = _weighted_score(storage_norm, sub_weights["storage"])

    total_score = (
        cpu_score * total_weights["cpu"]
        + gpu_score * total_weights["gpu"]
        + ram_score * total_weights["ram"]
        + storage_score * total_weights["storage"]
    )

    return {
        "cpu_score": cpu_score,
        "gpu_score": gpu_score,
        "ram_score": ram_score,
        "storage_score": storage_score,
        "total_score": total_score,
    }
