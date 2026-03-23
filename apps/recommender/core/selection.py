"""
配件选择策略模块

提供多种配件选择算法：
- 预算内最优选择
- 电源匹配
- 功耗估算
"""

from typing import Callable, Optional

from django.db.models import QuerySet

from ..algorithms.scoring import price


def select_components_with_budget(
    queryset: QuerySet,
    budget: float,
    score_fn: Callable,
) -> Optional[object]:
    """
    在预算范围内选择评分最高的配件

    Args:
        queryset: Django 查询集
        budget: 预算上限
        score_fn: 评分函数

    Returns:
        选中的配件对象
    """
    best = None
    best_score = -1

    for item in queryset:
        item_price = price(item.price)
        if item_price <= budget and item_price > 0:
            score = score_fn(item)
            if score > best_score:
                best = item
                best_score = score

    # 如果没有合适的，返回最便宜的
    if not best:
        return queryset.order_by("price").first()

    return best


def select_psu_for_wattage(
    queryset: QuerySet,
    required_wattage: float,
) -> Optional[object]:
    """
    根据所需瓦数选择合适的电源

    Args:
        queryset: 电源查询集
        required_wattage: 所需瓦数（已包含冗余）

    Returns:
        选中的电源对象
    """
    if required_wattage <= 0:
        return queryset.order_by("price").first()

    # 首先尝试找到满足瓦数的最便宜电源
    candidate = queryset.filter(wattage__gte=required_wattage).order_by("price").first()

    # 如果找不到，返回瓦数最大的
    if not candidate:
        candidate = queryset.order_by("-wattage").first()

    return candidate


def estimate_wattage(cpu, gpu) -> float:
    """
    估算系统总功耗

    Args:
        cpu: CPU 对象
        gpu: GPU 对象

    Returns:
        估算的系统总功耗（瓦特）
    """
    # CPU 功耗
    cpu_power = float(cpu.tdp or 0) if cpu else 0

    # GPU 功耗估算（基于 Boost 频率）
    gpu_clock = float(gpu.boost_clock or 0) if gpu else 0
    gpu_power = 0.16 * gpu_clock + 50 if gpu_clock else 0

    # 其他组件预留 100W
    other_power = 100

    return cpu_power + gpu_power + other_power
