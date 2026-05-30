"""推荐引擎主流程

参数解析、候选集加载、组合枚举、兼容性约束过滤、性能评分与排序后处理
"""

from typing import Dict, List, Mapping

from ..score.bounds import build_all_bounds
from ..utils import (
    RecommendationRequest,
    normalize_budget_range,
    to_score_dict,
)
from .enum_parts import collect_feasible_candidates
from .process_parts import order_candidate_parts, preference_parts, price_score
from .select_parts import select_diverse_items


def build_scoring_bounds(parts: Mapping[str, List[object]]):
    """计算候选配件的归一化边界数据。"""
    return build_all_bounds(
        cpus=[
            to_score_dict(x) for x in parts["cpus"]
        ],  # 每个 cpu 对象转换为统一的评分字段字典
        gpus=[to_score_dict(x) for x in parts["gpus"]],
        rams=[to_score_dict(x) for x in parts["rams"]],
        storages=[to_score_dict(x) for x in parts["storages"]],
    )


def recommend_builds(params: RecommendationRequest) -> Dict[str, object]:
    """推荐程序入口：在预算与兼容性约束下生成并返回组合。"""
    workload = params.workload
    budget_min, budget_max = normalize_budget_range(params)

    candidate_parts = preference_parts(params)  # 偏好过滤
    candidate_parts = order_candidate_parts(candidate_parts, workload)  # 按性能字段排序
    norm_bounds = build_scoring_bounds(candidate_parts)  # 计算归一化边界

    feasible = collect_feasible_candidates(
        candidate_parts,
        workload=workload,
        budget_min=budget_min,
        budget_max=budget_max,
        norm_bounds=norm_bounds,
    )

    feasible = price_score(feasible)  # 处理性价比数值并排序
    top_items = select_diverse_items(feasible)

    return {
        "items": top_items,
        "meta": {
            "workload": workload,
            "budget_min": budget_min,
            "budget_max": budget_max,
            "candidate_count": len(feasible),
        },
    }
