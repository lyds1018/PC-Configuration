"""
推荐引擎（清晰版）

设计原则：
1. 输入字段完整，规则直接表达，不做脏数据兼容。
2. 先定 CPU+GPU，再分配剩余预算给其他部件。
3. 最终方案必须通过兼容性检查。
"""

from typing import Dict, List, Optional, Tuple

from django.db.models import QuerySet

from ..algorithms.scoring import (
    cpu_score,
    efficiency_score,
    gpu_score,
    price,
    ram_score,
    storage_score,
    value_score,
)
from .compatibility import check_compatibility
from .config import get_budget_weights, get_usage_weights
from .selection import estimate_wattage, select_components_with_budget, select_psu_for_wattage

PROFILE_LABELS = {
    "value": "性价比方案",
    "balanced": "均衡方案",
    "performance": "性能方案",
}

PROFILE_TARGET_BUDGET = {
    "value": lambda bmin, bmax: bmin,
    "balanced": lambda bmin, bmax: (bmin + bmax) / 2,
    "performance": lambda bmin, bmax: bmax,
}


def build_recommendation(
    profile: str,
    usage: str,
    budget_min: float,
    budget_max: float,
    cpu_qs: QuerySet,
    gpu_qs: QuerySet,
    ram_qs: QuerySet,
    storage_qs: QuerySet,
    mb_qs: QuerySet,
    psu_qs: QuerySet,
    case_qs: QuerySet,
    cooler_qs: QuerySet,
    priority_mode: str = "auto",
) -> Optional[Dict]:

    target_budget = PROFILE_TARGET_BUDGET[profile](budget_min, budget_max)
    budget_weights = get_budget_weights(profile, priority_mode)
    usage_weights = get_usage_weights(usage)

    cpu_list = list(cpu_qs)
    gpu_list = list(gpu_qs)
    ram_list = list(ram_qs)
    storage_list = list(storage_qs)
    mb_list = list(mb_qs)
    psu_list = list(psu_qs)
    case_list = list(case_qs)
    cooler_list = list(cooler_qs)

    cpu_candidates = _top_candidates(cpu_list, lambda x: cpu_score(x, usage), 40)
    gpu_candidates = _top_candidates(gpu_list, lambda x: gpu_score(x, usage), 40)

    min_other_cost = _minimum_other_cost(ram_list, storage_list, mb_list, case_list, cooler_list, psu_list)
    combo = _choose_cpu_gpu_combo(
        cpu_candidates, gpu_candidates, budget_max, min_other_cost, usage, usage_weights
    )
    if not combo:
        return None

    _, cpu, gpu = combo
    remaining = max(target_budget - price(cpu.price) - price(gpu.price), 0.0)

    ram = select_components_with_budget(ram_list, remaining * budget_weights["ram"], ram_score)
    storage = select_components_with_budget(
        storage_list, remaining * budget_weights["storage"], storage_score
    )
    if ram is None or storage is None:
        return None

    mb_pool = [mb for mb in mb_list if _mb_matches_cpu_and_ram(mb, cpu, ram)]
    mb = select_components_with_budget(mb_pool, remaining * budget_weights["mb"], lambda m: -price(m.price))
    if mb is None:
        return None

    case_pool = [c for c in case_list if float(c.max_gpu_length) >= float(gpu.length)]
    case = select_components_with_budget(case_pool, remaining * budget_weights["case"], lambda c: -price(c.price))
    if case is None:
        return None

    cooler_pool = [
        c
        for c in cooler_list
        if int(c.tdp_capacity) >= int(cpu.tdp)
        and str(cpu.socket).upper() in {s.strip().upper() for s in str(c.socket_support).split(",")}
    ]
    cooler = select_components_with_budget(cooler_pool, remaining * budget_weights["cooler"], lambda c: -price(c.price))
    if cooler is None:
        return None

    estimated_watt = estimate_wattage(cpu, gpu)
    psu = select_psu_for_wattage(psu_list, estimated_watt * 1.3)
    if psu is None:
        return None

    selection = {
        "cpu": cpu,
        "gpu": gpu,
        "ram": ram,
        "storage": storage,
        "mb": mb,
        "psu": psu,
        "case": case,
        "cooler": cooler,
    }

    compatibility = check_compatibility(selection)
    if not compatibility["ok"]:
        return None

    total = sum(price(item.price) for item in selection.values())
    cpu_sc = cpu_score(cpu, usage)
    gpu_sc = gpu_score(gpu, usage)

    return {
        "profile": PROFILE_LABELS[profile],
        "total": total,
        "estimated_watt": estimated_watt,
        "compatibility": compatibility,
        "items": selection,
        "scores": {
            "cpu_score": cpu_sc,
            "gpu_score": gpu_sc,
            "cpu_efficiency": efficiency_score(cpu, "cpu"),
            "gpu_efficiency": efficiency_score(gpu, "gpu"),
            "cpu_value": value_score(cpu, cpu_sc),
            "gpu_value": value_score(gpu, gpu_sc),
        },
        "reasons": _build_reasons(profile, usage, cpu_sc, gpu_sc),
        "budget_weights": budget_weights,
    }


def _top_candidates(items: List, score_fn, top_n: int) -> List:
    return sorted(items, key=score_fn, reverse=True)[:top_n]


def _minimum_other_cost(ram_list, storage_list, mb_list, case_list, cooler_list, psu_list) -> float:
    return sum(
        min(price(x.price) for x in group)
        for group in (ram_list, storage_list, mb_list, case_list, cooler_list, psu_list)
    )


def _choose_cpu_gpu_combo(
    cpu_candidates: List,
    gpu_candidates: List,
    budget_max: float,
    min_other_cost: float,
    usage: str,
    usage_weights: Dict,
) -> Optional[Tuple[float, object, object]]:
    best = None
    best_score = -1.0

    for cpu in cpu_candidates:
        for gpu in gpu_candidates:
            pair_cost = price(cpu.price) + price(gpu.price)
            if pair_cost + min_other_cost > budget_max:
                continue

            cpu_sc = cpu_score(cpu, usage) * usage_weights.get("cpu", 1.0)
            gpu_sc = gpu_score(gpu, usage) * usage_weights.get("gpu", 1.0)
            score = cpu_sc * 0.55 + gpu_sc * 0.65

            if score > best_score:
                best_score = score
                best = (score, cpu, gpu)

    return best


def _mb_matches_cpu_and_ram(mb, cpu, ram) -> bool:
    socket_ok = str(cpu.socket).upper() in str(mb.socket).upper()
    ddr_ok = str(ram.ddr_generation).upper() == str(mb.ddr_generation).upper()
    capacity_ok = float(ram.total_capacity_gb) <= float(mb.max_memory)
    slots_ok = int(ram.module_count) <= int(mb.memory_slots)
    return socket_ok and ddr_ok and capacity_ok and slots_ok


def _build_reasons(profile: str, usage: str, cpu_sc: float, gpu_sc: float) -> List[str]:
    reasons = []

    if usage == "gaming":
        reasons.append("针对游戏场景优化了 CPU/GPU 组合。")
    elif usage == "office":
        reasons.append("优先保证办公稳定性与成本效率。")
    else:
        reasons.append("面向生产力场景强化了多线程与存储表现。")

    if profile == "value":
        reasons.append("预算分配偏向性价比。")
    elif profile == "performance":
        reasons.append("预算分配偏向性能上限。")
    else:
        reasons.append("预算分配偏向均衡体验。")

    if gpu_sc >= cpu_sc:
        reasons.append("图形性能与游戏帧率表现更优先。")
    else:
        reasons.append("处理器性能与系统响应更优先。")

    return reasons
