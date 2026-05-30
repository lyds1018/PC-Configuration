from typing import Dict, Iterable, Mapping

from ..utils import ALLBounds, MinMax, to_float
from .extract import cpu_features, gpu_features, ram_features, storage_features


def build_bounds(
    items: Iterable[Mapping[str, float]], feature_builder
) -> Dict[str, MinMax]:
    """计算性能字段边界，用于后续归一化。"""
    values_by_feature: Dict[str, list] = {}  # 字段名 -> 值列表
    for item in items:
        features = feature_builder(item)  # 调用指定的提取函数
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
    """计算能效比的边界，用于后续归一化。"""
    values = []

    for item in items:
        score = to_float(item.get(score_key))
        tdp = to_float(item.get("tdp"))
        values.append(score / tdp)

    if not values:
        return MinMax(0.0, 0.0)

    return MinMax(min(values), max(values))


def build_all_bounds(
    cpus: Iterable[Mapping[str, float]],
    gpus: Iterable[Mapping[str, float]],
    rams: Iterable[Mapping[str, float]],
    storages: Iterable[Mapping[str, float]],
) -> ALLBounds:
    """计算候选配件的归一化边界，用于后续归一化。"""
    return ALLBounds(
        cpu=build_bounds(cpus, cpu_features),
        gpu=build_bounds(gpus, gpu_features),
        ram=build_bounds(rams, ram_features),
        storage=build_bounds(storages, storage_features),
        cpu_ee=build_ee_bounds(cpus, "multi_score"),
        gpu_ee=build_ee_bounds(gpus, "gaming_score"),
    )
