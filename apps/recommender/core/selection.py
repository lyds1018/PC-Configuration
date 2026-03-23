"""配件选择策略模块（清晰版）。"""

from typing import Callable, Optional

from ..algorithms.scoring import price


def select_components_with_budget(
    items,
    budget: float,
    score_fn: Callable,
) -> Optional[object]:
    """在预算内选择评分最高的组件；预算内无项返回 None。"""
    best = None
    best_score = -1

    items = list(items)
    if not items:
        return None

    for item in items:
        item_price = price(item.price)
        if item_price <= budget and item_price > 0:
            score = score_fn(item)
            if score > best_score:
                best = item
                best_score = score

    if not best:
        return None

    return best


def select_psu_for_wattage(
    items,
    required_wattage: float,
) -> Optional[object]:
    """选择满足功率需求且价格最低的电源；无满足项返回 None。"""
    items = list(items)
    if not items:
        return None

    candidates = [x for x in items if float(x.wattage) >= float(required_wattage)]
    if not candidates:
        return None
    return min(candidates, key=lambda x: price(x.price))


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

    # GPU 功耗（数据保证存在）
    gpu_power = float(gpu.tdp or 0) if gpu else 0

    # 其他组件预留 100W
    other_power = 100

    return cpu_power + gpu_power + other_power
