"""
基于内容的推荐算法

根据用途和配件特征计算匹配度
"""

import math
from typing import List

from .scoring import (
    case_score,
    cooler_score,
    cpu_score,
    gpu_score,
    price,
    psu_score,
    ram_score,
    storage_score,
)

# 用途权重配置
USAGE_WEIGHTS = {
    "gaming": {
        "cpu": 0.85,
        "gpu": 1.4,
        "ram": 1.0,
        "storage": 0.8,
        "mb": 0.9,
        "psu": 1.0,
        "case": 0.8,
        "cooler": 0.9,
    },
    "office": {
        "cpu": 0.8,
        "gpu": 0.5,
        "ram": 0.9,
        "storage": 1.0,
        "mb": 0.8,
        "psu": 0.7,
        "case": 0.7,
        "cooler": 0.8,
    },
    "productivity": {
        "cpu": 1.3,
        "gpu": 1.1,
        "ram": 1.3,
        "storage": 1.2,
        "mb": 1.0,
        "psu": 1.1,
        "case": 0.9,
        "cooler": 1.1,
    },
}


def calculate_component_match(
    component, component_type: str, usage: str, budget_ratio: float = 1.0
) -> float:
    """
    计算单个配件与用途的匹配度

    Args:
        component: 配件对象
        component_type: 配件类型
        usage: 用途 ('gaming', 'office', 'productivity')
        budget_ratio: 预算占比（0-1）

    Returns:
        匹配度评分（0-100）
    """
    if not component:
        return 0.0

    # 获取基础评分
    score_funcs = {
        "cpu": lambda c: cpu_score(c, usage),
        "gpu": lambda c: gpu_score(c, usage),
        "ram": lambda c: ram_score(c),
        "storage": lambda c: storage_score(c),
        "psu": lambda c: psu_score(c),
        "case": lambda c: case_score(c),
        "cooler": lambda c: cooler_score(c),
    }

    score_func = score_funcs.get(component_type)
    if not score_func:
        return 0.0

    base_score = score_func(component)

    # 应用用途权重
    weights = USAGE_WEIGHTS.get(usage, {})
    weight = weights.get(component_type, 1.0)
    weighted_score = base_score * weight

    # 考虑性价比（如果预算紧张）
    if budget_ratio < 0.5:
        comp_price = price(getattr(component, "price", 0))
        if comp_price > 0:
            value_bonus = min(2.0, 1000 / comp_price)
            weighted_score *= value_bonus

    return weighted_score


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    计算两个向量的余弦相似度

    Args:
        vec1: 向量 1
        vec2: 向量 2

    Returns:
        相似度（0-1）
    """
    if not vec1 or not vec2:
        return 0.0

    # 点积
    dot_product = sum(a * b for a, b in zip(vec1, vec2))

    # 模长
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def euclidean_distance(vec1: List[float], vec2: List[float]) -> float:
    """
    计算欧氏距离

    Args:
        vec1: 向量 1
        vec2: 向量 2

    Returns:
        距离值
    """
    if not vec1 or not vec2:
        return float("inf")

    return math.sqrt(sum((a - b) ** 2 for a, b in zip(vec1, vec2)))


def match_cpu_to_usage(cpu, usage: str) -> float:
    """
    CPU 与用途的匹配度

    Args:
        cpu: CPU 对象
        usage: 用途

    Returns:
        匹配度（0-100）
    """
    return cpu_score(cpu, usage)


def match_gpu_to_usage(gpu, usage: str) -> float:
    """
    GPU 与用途的匹配度

    Args:
        gpu: GPU 对象
        usage: 用途

    Returns:
        匹配度（0-100）
    """
    return gpu_score(gpu, usage)


def match_ram_to_usage(ram, usage: str) -> float:
    """
    内存与用途的匹配度

    Args:
        ram: 内存对象
        usage: 用途

    Returns:
        匹配度（0-100）
    """
    if not ram:
        return 0.0

    # 办公需要基本容量，游戏需要速度，生产力需要大容量
    modules_str = str(getattr(ram, "modules", ""))
    parts = modules_str.split(",")

    if len(parts) >= 2:
        try:
            count = int(parts[0])
            size = float(parts[1])
            total = count * size

            if usage == "office":
                # 办公：16GB 足够
                return min(100, total / 16 * 80)
            elif usage == "gaming":
                # 游戏：32GB 为佳，重视速度
                speed_text = str(ram.speed or "")
                import re

                numbers = re.findall(r"\d+", speed_text)
                speed = float(numbers[0]) if numbers else 0
                return (total / 32 * 60) + (speed / 6000 * 40)
            else:  # productivity
                # 生产力：越大越好
                return min(100, total / 64 * 100)
        except (ValueError, IndexError):
            pass

    return ram_score(ram)


def select_best_components(
    candidates: List,
    component_type: str,
    usage: str,
    budget: float,
    priority: str = "balanced",
) -> object:
    """
    从候选列表中选择最佳配件

    Args:
        candidates: 候选配件列表
        component_type: 配件类型
        usage: 用途
        budget: 预算
        priority: 优先级 ('performance', 'value', 'balanced')

    Returns:
        选中的配件对象
    """
    if not candidates:
        return None

    best = None
    best_score = -1

    for component in candidates:
        comp_price = price(getattr(component, "price", 0))

        # 跳过超出预算的
        if comp_price > budget or comp_price <= 0:
            continue

        # 计算匹配度
        match_score = calculate_component_match(
            component, component_type, usage, budget / max(comp_price, 1)
        )

        # 根据优先级调整
        if priority == "performance":
            final_score = match_score
        elif priority == "value":
            final_score = match_score / (comp_price**0.3)
        else:  # balanced
            final_score = match_score / (comp_price**0.15)

        if final_score > best_score:
            best = component
            best_score = final_score

    # 如果没有合适的，返回最便宜的
    if not best:
        return min(candidates, key=lambda x: price(getattr(x, "price", 0)))

    return best
