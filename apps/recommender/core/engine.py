"""
推荐引擎核心模块

根据用户输入的预算、用途和偏好，生成兼容的 PC 配置方案
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
from ..utils.logger import get_logger
from .compatibility import check_compatibility
from .config import (
    get_budget_weights,
    get_usage_weights,
    validate_profile,
    validate_usage,
)
from .selection import (
    estimate_wattage,
    select_components_with_budget,
    select_psu_for_wattage,
)

logger = get_logger(__name__)

PROFILE_TARGET_BUDGET = {
    "value": lambda budget_min, budget_max: budget_min,
    "balanced": lambda budget_min, budget_max: (budget_min + budget_max) / 2,
    "performance": lambda budget_min, budget_max: budget_max,
}

PROFILE_LABELS = {
    "value": "性价比方案",
    "balanced": "均衡方案",
    "performance": "性能方案",
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
    """
    构建推荐配置方案

    Args:
        profile: 方案类型 ('value', 'balanced', 'performance')
        usage: 用途 ('gaming', 'office', 'productivity')
        budget_min: 最低预算（元）
        budget_max: 最高预算（元）
        cpu_qs: CPU 查询集
        gpu_qs: GPU 查询集
        ram_qs: 内存查询集
        storage_qs: 存储查询集
        mb_qs: 主板查询集
        psu_qs: 电源查询集
        case_qs: 机箱查询集
        cooler_qs: 散热器查询集
        priority_mode: 优先级模式 ('auto', 'cpu', 'gpu', 'storage')

    Returns:
        推荐结果字典，包含配件列表、总价、兼容性等信息
    """
    # 验证参数
    if not validate_profile(profile):
        logger.warning(f"Invalid profile: {profile}")
        return None

    if not validate_usage(usage):
        logger.warning(f"Invalid usage: {usage}")
        return None

    if budget_min <= 0 or budget_max <= 0 or budget_min > budget_max:
        logger.warning(f"Invalid budget: {budget_min}-{budget_max}")
        return None

    # 计算目标预算（根据方案类型）
    target_budget = PROFILE_TARGET_BUDGET[profile](budget_min, budget_max)

    # 获取预算分配权重
    budget_weights = get_budget_weights(profile, priority_mode)
    usage_weights = get_usage_weights(usage)

    logger.info(
        f"Building recommendation: profile={profile}, usage={usage}, "
        f"budget={budget_min}-{budget_max}, priority={priority_mode}"
    )

    # 1. 预筛选 CPU 和 GPU（按性能排序取前 N 个）
    cpu_candidates = _filter_top_components(
        list(cpu_qs), lambda c: cpu_score(c, usage), top_n=30
    )
    gpu_candidates = _filter_top_components(
        list(gpu_qs), lambda g: gpu_score(g, usage), top_n=30
    )

    # 2. 计算其他配件的最低预算
    other_min_cost = _calculate_minimum_costs(
        ram_qs, storage_qs, mb_qs, case_qs, cooler_qs
    )

    # 3. 寻找最佳 CPU+GPU 组合
    best_combo = _find_best_cpu_gpu_combo(
        cpu_candidates,
        gpu_candidates,
        budget_max,
        other_min_cost,
        usage,
        usage_weights,
    )

    if not best_combo:
        logger.warning("No suitable CPU-GPU combination found")
        return None

    score, cpu, gpu = best_combo

    # 4. 计算剩余预算
    cpu_price = price(cpu.price)
    gpu_price = price(gpu.price)
    remaining = max(target_budget - cpu_price - gpu_price, 0)

    # 5. 选择其他配件
    ram = select_components_with_budget(
        ram_qs, remaining * budget_weights["ram"], ram_score
    )
    storage = select_components_with_budget(
        storage_qs, remaining * budget_weights["storage"], storage_score
    )
    mb = select_components_with_budget(
        mb_qs, remaining * budget_weights["mb"], lambda m: price(m.price)
    )
    case = select_components_with_budget(
        case_qs, remaining * budget_weights["case"], lambda c: price(c.price)
    )
    cooler = select_components_with_budget(
        cooler_qs, remaining * budget_weights["cooler"], lambda c: price(c.price)
    )

    # 6. 选择合适的电源
    estimated_watt = estimate_wattage(cpu, gpu)
    psu = select_psu_for_wattage(psu_qs, estimated_watt)

    # 7. 组装配置
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

    # 8. 计算总价
    total = sum(price(item.price) for item in selection.values() if item)

    # 9. 验证预算范围
    if total < budget_min * 0.95 or total > budget_max * 1.05:
        logger.info(f"Total {total} outside budget range [{budget_min}, {budget_max}]")
        # 允许 5% 的浮动范围

    # 10. 兼容性检查
    compatibility = check_compatibility(selection)
    if not compatibility["ok"]:
        logger.warning(f"Compatibility issues: {compatibility['issues']}")
        # 如果有严重兼容性问题，返回 None
        critical_issues = [
            i for i in compatibility["issues"] if "不兼容" in i or "无法" in i
        ]
        if critical_issues:
            return None

    # 11. 生成推荐理由
    cpu_sc = cpu_score(cpu, usage)
    gpu_sc = gpu_score(gpu, usage)

    reasons = _generate_recommendation_reasons(selection, usage, profile, cpu_sc, gpu_sc)

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
        "reasons": reasons,
        "budget_weights": budget_weights,
    }


def _filter_top_components(candidates: List, score_func, top_n: int = 30) -> List:
    """
    筛选评分最高的组件

    Args:
        candidates: 候选组件列表
        score_func: 评分函数
        top_n: 返回前 N 个

    Returns:
        筛选后的组件列表
    """
    sorted_candidates = sorted(
        candidates,
        key=score_func,
        reverse=True,
    )
    return sorted_candidates[:top_n]


def _calculate_minimum_costs(ram_qs, storage_qs, mb_qs, case_qs, cooler_qs) -> float:
    """
    计算其他配件的最低成本

    Returns:
        最低总成本
    """
    price_fields = []
    for queryset in (ram_qs, storage_qs, mb_qs, case_qs, cooler_qs):
        item = queryset.order_by("price").first()
        if not item:
            logger.warning("Empty queryset while calculating minimum component costs")
            return 0.0
        price_fields.append(price(item.price))

    return sum(price_fields)


def _find_best_cpu_gpu_combo(
    cpu_candidates: List,
    gpu_candidates: List,
    budget_max: float,
    other_min_cost: float,
    usage: str,
    usage_weights: Dict,
) -> Optional[Tuple[float, object, object]]:
    """
    寻找最佳的 CPU+GPU 组合

    Args:
        cpu_candidates: CPU 候选列表
        gpu_candidates: GPU 候选列表
        budget_max: 最大预算
        other_min_cost: 其他配件最低成本
        usage: 用途
        usage_weights: 用途权重

    Returns:
        (综合评分，CPU, GPU) 元组
    """
    best = None
    best_score = -1

    for cpu in cpu_candidates:
        for gpu in gpu_candidates:
            total_cost = price(cpu.price) + price(gpu.price) + other_min_cost

            # 跳过超出预算的组合
            if total_cost > budget_max:
                continue

            # 计算加权综合评分
            cpu_sc = cpu_score(cpu, usage) * usage_weights.get("cpu", 1.0)
            gpu_sc = gpu_score(gpu, usage) * usage_weights.get("gpu", 1.0)
            score = cpu_sc * 0.55 + gpu_sc * 0.65

            if score > best_score:
                best = (score, cpu, gpu)
                best_score = score

    return best


def _generate_recommendation_reasons(
    selection: Dict,
    usage: str,
    profile: str,
    cpu_sc: float,
    gpu_sc: float,
) -> List[str]:
    """
    生成推荐理由

    Args:
        selection: 配件选择字典
        usage: 用途
        profile: 方案类型
        cpu_sc: CPU 评分
        gpu_sc: GPU 评分

    Returns:
        理由列表
    """
    reasons = []

    cpu = selection.get("cpu")
    gpu = selection.get("gpu")

    if not cpu or not gpu:
        return reasons

    # 根据用途生成理由
    if usage == "gaming":
        if gpu_sc > cpu_sc:
            reasons.append(f"显卡性能强劲，适合游戏需求（GPU 评分：{gpu_sc:.0f}）")
        else:
            reasons.append("CPU 与显卡性能均衡，无明显瓶颈")
    elif usage == "office":
        reasons.append("配置满足日常办公和多媒体需求")
    elif usage == "productivity":
        reasons.append("多核 CPU 和大内存配置，适合生产力应用")

    # 根据方案类型生成理由
    if profile == "value":
        reasons.append("注重性价比，选择价格合理的配件")
    elif profile == "performance":
        reasons.append("追求极致性能，优先选择高端配件")
    else:
        reasons.append("平衡性能和价格，适合大多数用户")

    # 能效评价
    avg_efficiency = (efficiency_score(cpu, "cpu") + efficiency_score(gpu, "gpu")) / 2
    if avg_efficiency > 70:
        reasons.append("配件能效表现优秀")
    elif avg_efficiency > 50:
        reasons.append("配件能效表现良好")

    return reasons
