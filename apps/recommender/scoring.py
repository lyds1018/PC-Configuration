"""装机推荐评分体系

特征提取，归一化，分项加权，
其中按不同应用场景，使用不同权重策略
"""

import math
from dataclasses import dataclass
from typing import Dict, Iterable, Mapping

from .utils import (
    WORKLOAD_ALIASES,
    WORKLOAD_GAME,
    WORKLOAD_OFFICE,
    WORKLOAD_PRODUCTIVITY,
    clamp_0_1,
    to_float,
    to_log,
)

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


# 边界类
@dataclass(frozen=True)
class MinMax:
    min_value: float
    max_value: float


# 整机边界类
@dataclass(frozen=True)
class NormalizationStats:
    cpu: Dict[str, MinMax]
    gpu: Dict[str, MinMax]
    ram: Dict[str, MinMax]
    storage: Dict[str, MinMax]
    cpu_ee: MinMax
    gpu_ee: MinMax


def linear_norm(value: float, bounds: MinMax) -> float:
    denom = bounds.max_value - bounds.min_value
    if denom <= 0:
        return 0.0
    return clamp_0_1((value - bounds.min_value) / denom)


def positive_log_norm(value: float, bounds: MinMax) -> float:
    span = bounds.max_value - bounds.min_value
    if span <= 0:
        return 0.0
    numerator = to_log(value - bounds.min_value + 1.0)
    denominator = to_log(span + 1.0)
    if denominator <= 0:
        return 0.0
    return clamp_0_1(numerator / denominator)


def cpu_features(cpu: Mapping[str, float]) -> Dict[str, float]:
    base_clock = to_float(cpu.get("base_clock"))
    boost_clock = to_float(cpu.get("boost_clock"))
    core_count = to_float(cpu.get("core_count"))
    thread_count = to_float(cpu.get("thread_count"))

    return {
        "single_score": to_float(cpu.get("single_score")),
        "multi_score": to_float(cpu.get("multi_score")),
        "bb": (base_clock + boost_clock) / 2.0,
        "ct": to_log(core_count * thread_count),
        "tdp": to_float(cpu.get("tdp")),
    }


def gpu_features(gpu: Mapping[str, float]) -> Dict[str, float]:
    core_clock = to_float(gpu.get("core_clock"))
    memory_clock = to_float(gpu.get("memory_clock"))
    return {
        "gaming_score": to_float(gpu.get("gaming_score")),
        "compute_score": to_float(gpu.get("compute_score")),
        "cm": (core_clock + memory_clock) / 2.0,
        "vram_size": to_float(gpu.get("vram_size")),
        "tdp": to_float(gpu.get("tdp")),
    }


def ram_features(ram: Mapping[str, float]) -> Dict[str, float]:
    frequency = to_float(ram.get("frequency"))
    latency = to_float(ram.get("latency"), default=1.0)
    if latency <= 0:
        latency = 1.0

    return {
        "capacity": to_float(ram.get("capacity")),
        "fl": frequency / latency,
    }


def storage_features(storage: Mapping[str, float]) -> Dict[str, float]:
    read_speed = to_float(storage.get("read_speed"))
    write_speed = to_float(storage.get("write_speed"))
    random_read_iops = to_float(storage.get("random_read_iops"))
    random_write_iops = to_float(storage.get("random_write_iops"))

    return {
        "capacity": to_float(storage.get("capacity")),
        "cache_size": to_float(storage.get("cache_size")),
        "sp": (read_speed + write_speed) / 2.0,
        "rand": (random_read_iops + random_write_iops) / 2.0,
    }


def build_bounds(
    items: Iterable[Mapping[str, float]], feature_builder
) -> Dict[str, MinMax]:
    """根据候选集计算每个特征的最小值与最大值，用于后续归一化。"""
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


def build_ee_bounds(items: Iterable[Mapping[str, float]], score_key: str) -> MinMax:
    """计算能效比（性能分数/功耗）的最小值与最大值，用于后续归一化。"""
    values = []

    for item in items:
        score = to_float(item.get(score_key))
        tdp = to_float(item.get("tdp"))
        if tdp <= 0:
            values.append(0.0)
            continue
        values.append(score / tdp)

    if not values:
        return MinMax(0.0, 0.0)
    return MinMax(min(values), max(values))


def build_normalization_stats(
    cpus: Iterable[Mapping[str, float]],
    gpus: Iterable[Mapping[str, float]],
    rams: Iterable[Mapping[str, float]],
    storages: Iterable[Mapping[str, float]],
) -> NormalizationStats:
    """计算候选集构建归一化边界。"""
    return NormalizationStats(
        cpu=build_bounds(cpus, cpu_features),
        gpu=build_bounds(gpus, gpu_features),
        ram=build_bounds(rams, ram_features),
        storage=build_bounds(storages, storage_features),
        cpu_ee=build_ee_bounds(cpus, "multi_score"),
        gpu_ee=build_ee_bounds(gpus, "gaming_score"),
    )


def normalize_cpu(
    features: Dict[str, float], stats: NormalizationStats
) -> Dict[str, float]:
    tdp = features["tdp"]
    multi_score = features["multi_score"]
    ee_cpu = (multi_score / tdp) if tdp > 0 else 0.0
    ee_norm = linear_norm(ee_cpu, stats.cpu_ee)
    multi_score_max = stats.cpu["multi_score"].max_value
    perf_ratio = (multi_score / multi_score_max) if multi_score_max > 0 else 0.0

    return {
        "single_score": linear_norm(
            features["single_score"], stats.cpu["single_score"]
        ),
        "multi_score": linear_norm(features["multi_score"], stats.cpu["multi_score"]),
        "bb": linear_norm(features["bb"], stats.cpu["bb"]),
        "ct": linear_norm(features["ct"], stats.cpu["ct"]),
        "tdp": clamp_0_1(ee_norm * perf_ratio),
    }


def normalize_gpu(
    features: Dict[str, float], stats: NormalizationStats
) -> Dict[str, float]:
    tdp = features["tdp"]
    gaming_score = features["gaming_score"]
    ee_gpu = (gaming_score / tdp) if tdp > 0 else 0.0
    ee_norm = linear_norm(ee_gpu, stats.gpu_ee)
    gaming_score_max = stats.gpu["gaming_score"].max_value
    perf_ratio = (gaming_score / gaming_score_max) if gaming_score_max > 0 else 0.0

    return {
        "gaming_score": linear_norm(
            features["gaming_score"], stats.gpu["gaming_score"]
        ),
        "compute_score": linear_norm(
            features["compute_score"], stats.gpu["compute_score"]
        ),
        "cm": linear_norm(features["cm"], stats.gpu["cm"]),
        "vram_size": linear_norm(features["vram_size"], stats.gpu["vram_size"]),
        "tdp": clamp_0_1(ee_norm * perf_ratio),
    }


def normalize_ram(
    features: Dict[str, float], stats: NormalizationStats
) -> Dict[str, float]:
    return {
        "capacity": linear_norm(features["capacity"], stats.ram["capacity"]),
        "fl": linear_norm(features["fl"], stats.ram["fl"]),
    }


def normalize_storage(
    features: Dict[str, float], stats: NormalizationStats
) -> Dict[str, float]:
    return {
        "capacity": linear_norm(features["capacity"], stats.storage["capacity"]),
        "cache_size": linear_norm(features["cache_size"], stats.storage["cache_size"]),
        "sp": linear_norm(features["sp"], stats.storage["sp"]),
        "rand": positive_log_norm(features["rand"], stats.storage["rand"]),
    }


def weighted_score(features: Dict[str, float], weights: Dict[str, float]) -> float:
    return sum(features[name] * weight for name, weight in weights.items())


def normalize_workload(workload: str) -> str:
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
    计算整机综合分数
    返回值在 [0, 1]，包含 CPU/GPU/内存/存储子分与总分
    """
    workload_key = normalize_workload(workload)
    sub_weights = SUB_WEIGHTS[workload_key]
    total_weights = TOTAL_WEIGHTS[workload_key]

    cpu_norm = normalize_cpu(cpu_features(cpu), stats)
    gpu_norm = normalize_gpu(gpu_features(gpu), stats)
    ram_norm = normalize_ram(ram_features(ram), stats)
    storage_norm = normalize_storage(storage_features(storage), stats)

    cpu_score = weighted_score(cpu_norm, sub_weights["cpu"])
    gpu_score = weighted_score(gpu_norm, sub_weights["gpu"])
    ram_score = weighted_score(ram_norm, sub_weights["ram"])
    storage_score = weighted_score(storage_norm, sub_weights["storage"])

    total_score = (
        cpu_score * total_weights["cpu"]
        + gpu_score * total_weights["gpu"]
        + ram_score * total_weights["ram"]
        + storage_score * total_weights["storage"]
    )

    total_score = 1 / (1 + math.exp(-6 * (total_score - 0.35)))

    return {
        "cpu_score": cpu_score,
        "gpu_score": gpu_score,
        "ram_score": ram_score,
        "storage_score": storage_score,
        "total_score": total_score,
    }
