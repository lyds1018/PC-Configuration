"""推荐引擎主流程

参数解析、候选集加载、组合枚举、兼容性约束过滤、性能评分与排序后处理
"""
from typing import Dict, List, Mapping
from ..scoring import build_normalization_stats
from .process_parts import preference_parts, order_candidate_parts, price_score
from .enum_parts import collect_feasible_candidates
from .select_parts import select_diverse_top_items
from .utils import RecommendationRequest, normalize_budget_range, obj_to_score_dict, OUTPUT_CANDIDATES


def build_scoring_stats(parts: Mapping[str, List[object]]):
    return build_normalization_stats(
        cpus=[obj_to_score_dict(x) for x in parts["cpus"]],
        gpus=[obj_to_score_dict(x) for x in parts["gpus"]],
        rams=[obj_to_score_dict(x) for x in parts["rams"]],
        storages=[obj_to_score_dict(x) for x in parts["storages"]],
    )


def recommend_builds(params: RecommendationRequest) -> Dict[str, object]:
    """推荐程序入口：在预算与兼容性约束下生成并返回 Top-K 组合。"""
    workload = params.workload
    budget_min, budget_max = normalize_budget_range(params)

    candidate_parts = preference_parts(params)  # 偏好过滤
    candidate_parts = order_candidate_parts(candidate_parts, workload)  # 按性能字段排序

    stats = build_scoring_stats(candidate_parts)  # 构建归一化的评分统计数据

    feasible = collect_feasible_candidates(
        candidate_parts,
        workload=workload,
        budget_min=budget_min,
        budget_max=budget_max,
        stats=stats,
    )   # 枚举过滤可行组合

    feasible = price_score(feasible) # 计算性价比分数
    top_items = select_diverse_top_items(feasible, OUTPUT_CANDIDATES)   # 返回多样化组合

    return {
        "items": top_items,
        "meta": {
            "workload": workload,
            "budget_min": budget_min,
            "budget_max": budget_max,
            "candidate_count": len(feasible),
        },
    }
