from typing import Dict

from ..utils import ALLBounds, linear_norm, positive_log_norm


def normalize_cpu(features: Dict[str, float], bounds: ALLBounds) -> Dict[str, float]:
    """归一化 CPU 评分字段数据"""
    tdp = features["tdp"]
    multi_score = features["multi_score"]
    ee_cpu = (multi_score / tdp) if tdp > 0 else 0.0
    ee_norm = linear_norm(ee_cpu, bounds.cpu_ee)
    multi_score_max = bounds.cpu["multi_score"].max_value
    perf_ratio = (multi_score / multi_score_max) if multi_score_max > 0 else 0.0

    return {
        "single_score": linear_norm(
            features["single_score"], bounds.cpu["single_score"]
        ),
        "multi_score": linear_norm(features["multi_score"], bounds.cpu["multi_score"]),
        "bb": linear_norm(features["bb"], bounds.cpu["bb"]),
        "ct": linear_norm(features["ct"], bounds.cpu["ct"]),
        "tdp": ee_norm * perf_ratio,
    }


def normalize_gpu(features: Dict[str, float], bounds: ALLBounds) -> Dict[str, float]:
    """归一化 GPU 评分字段数据"""
    tdp = features["tdp"]
    gaming_score = features["gaming_score"]
    ee_gpu = (gaming_score / tdp) if tdp > 0 else 0.0
    ee_norm = linear_norm(ee_gpu, bounds.gpu_ee)
    gaming_score_max = bounds.gpu["gaming_score"].max_value
    perf_ratio = (gaming_score / gaming_score_max) if gaming_score_max > 0 else 0.0

    return {
        "gaming_score": linear_norm(
            features["gaming_score"], bounds.gpu["gaming_score"]
        ),
        "compute_score": linear_norm(
            features["compute_score"], bounds.gpu["compute_score"]
        ),
        "cm": linear_norm(features["cm"], bounds.gpu["cm"]),
        "vram_size": linear_norm(features["vram_size"], bounds.gpu["vram_size"]),
        "tdp": ee_norm * perf_ratio,
    }


def normalize_ram(features: Dict[str, float], bounds: ALLBounds) -> Dict[str, float]:
    """归一化内存评分字段数据"""
    return {
        "capacity": linear_norm(features["capacity"], bounds.ram["capacity"]),
        "fl": linear_norm(features["fl"], bounds.ram["fl"]),
    }


def normalize_storage(features: Dict[str, float], bounds: ALLBounds) -> Dict[str, float]:
    """归一化存储设备评分字段数据"""
    return {
        "capacity": linear_norm(features["capacity"], bounds.storage["capacity"]),
        "cache_size": linear_norm(features["cache_size"], bounds.storage["cache_size"]),
        "sp": linear_norm(features["sp"], bounds.storage["sp"]),
        "rand": positive_log_norm(features["rand"], bounds.storage["rand"]),
    }
