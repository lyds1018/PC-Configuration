"""配件评分计算模块

特征提取，归一化，分项加权，
其中按不同应用场景，使用不同权重策略
"""

import math
from typing import Dict, Mapping

from ..utils import (
    SUB_WEIGHTS,
    TOTAL_WEIGHTS,
    WORKLOAD_ALIASES,
    ALLBounds,
)
from .extract import cpu_features, gpu_features, ram_features, storage_features
from .normalize import normalize_cpu, normalize_gpu, normalize_ram, normalize_storage


def weighted_score(features: Dict[str, float], weights: Dict[str, float]) -> float:
    """计算加权分数"""
    return sum(features[name] * weight for name, weight in weights.items())


def score_build(
    cpu: Mapping[str, float],
    gpu: Mapping[str, float],
    ram: Mapping[str, float],
    storage: Mapping[str, float],
    bounds: ALLBounds,
    workload: str,
) -> Dict[str, float]:
    """
    计算整机分数，
    返回值在 [0, 1]，包含 CPU/GPU/内存/存储子分与总分。
    """
    # 根据应用场景选择权重策略
    workload_key = WORKLOAD_ALIASES.get(workload)
    sub_weights = SUB_WEIGHTS[workload_key]
    total_weights = TOTAL_WEIGHTS[workload_key]

    # 对提取的评分字段进行归一化
    cpu_norm = normalize_cpu(cpu_features(cpu), bounds)
    gpu_norm = normalize_gpu(gpu_features(gpu), bounds)
    ram_norm = normalize_ram(ram_features(ram), bounds)
    storage_norm = normalize_storage(storage_features(storage), bounds)

    # 子分加权
    cpu_score = weighted_score(cpu_norm, sub_weights["cpu"])
    gpu_score = weighted_score(gpu_norm, sub_weights["gpu"])
    ram_score = weighted_score(ram_norm, sub_weights["ram"])
    storage_score = weighted_score(storage_norm, sub_weights["storage"])

    # 总分加权
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
