"""推荐引擎主流程

参数解析、候选集加载、组合枚举、兼容性约束过滤、性能评分与排序后处理
"""

from dataclasses import dataclass
from math import ceil
from typing import Dict, List, Mapping

from pc_builder.models import Case, Cpu, CpuCooler, Gpu, Mb, Psu, Ram, Storage

from .scoring import (
    build_normalization_stats,
    score_build,
)
from .utils import (
    WORKLOAD_GAME,
    WORKLOAD_OFFICE,
    as_parts_payload,
    is_compatible,
    is_limit_reached,
    normalize_brand,
    normalize_workload,
    obj_to_score_dict,
    part_price,
    scale_0_100,
    sum_price,
    to_float,
    to_int,
)


@dataclass
class RecommendationRequest:
    """推荐请求参数：由表单输入。"""

    budget_min: float = 0.0
    budget_max: float = 0.0
    workload: str = WORKLOAD_GAME
    cpu_brand: str = ""
    gpu_chip_brand: str = ""
    gpu_card_brand: str = ""
    free_text: str = ""
    top_k: int = 3


def brand_filter(queryset, brand: str):
    normalized = normalize_brand(brand)
    if not normalized:
        return queryset
    if normalized == "NVIDIA":
        return queryset.filter(brand__icontains="NVIDIA") | queryset.filter(
            brand__icontains="英伟达"
        )
    if normalized == "英特尔":
        return queryset.filter(brand__icontains="英特尔") | queryset.filter(
            brand__icontains="Intel"
        )
    return queryset.filter(brand__icontains=normalized)


def gpu_chip_brand_filter(queryset, chip_brand: str):
    normalized = normalize_brand(chip_brand)
    if not normalized:
        return queryset
    return queryset.filter(chip_brand__iexact=normalized)


def gpu_card_brand_filter(queryset, card_brand: str):
    text = (card_brand or "").strip()
    if not text:
        return queryset
    return queryset.filter(card_brand__icontains=text)


def shortlist(queryset, limit: int):
    """
    按价格分布抽样候选，而不是只拿最便宜的前 N 个。
    高预算场景如果只取低价件，整机总价很容易永远达不到预算下限。
    """
    items = list(queryset.order_by("price"))
    if len(items) <= limit:
        return items

    if limit <= 1:
        return [items[0]]

    selected = []
    seen_ids = set()
    last_index = len(items) - 1
    for i in range(limit):
        index = round(i * last_index / (limit - 1))
        item = items[index]
        item_id = getattr(item, "id", id(item))
        if item_id in seen_ids:
            continue
        seen_ids.add(item_id)
        selected.append(item)
    return selected


def score_reason(workload: str, scores: Mapping[str, float]) -> str:
    if workload == WORKLOAD_GAME:
        return f"游戏侧重显卡，GPU分 {scores['gpu_score_100']:.1f}/100，整机总分 {scores['total_score_100']:.1f}/100。"
    if workload == WORKLOAD_OFFICE:
        return f"办公侧重稳定与效率，CPU分 {scores['cpu_score_100']:.1f}/100，内存分 {scores['ram_score_100']:.1f}/100。"
    return f"生产力侧重并行与计算，CPU分 {scores['cpu_score_100']:.1f}/100，GPU分 {scores['gpu_score_100']:.1f}/100。"


def normalize_budget_range(params: RecommendationRequest) -> tuple[float, float]:
    budget_min = max(0.0, to_float(params.budget_min, 0.0))
    budget_max = max(0.0, to_float(params.budget_max, 0.0))
    if budget_max <= 0:
        budget_max = 20000.0
    if budget_min > budget_max:
        budget_min, budget_max = budget_max, budget_min
    return budget_min, budget_max


def load_candidate_parts(params: RecommendationRequest) -> Dict[str, List[object]]:
    cpu_qs = brand_filter(Cpu.objects.all(), params.cpu_brand)
    gpu_qs = gpu_chip_brand_filter(Gpu.objects.all(), params.gpu_chip_brand)
    gpu_qs = gpu_card_brand_filter(gpu_qs, params.gpu_card_brand)

    return {
        "cpus": shortlist(cpu_qs, 16),
        "mbs": shortlist(Mb.objects.all(), 18),
        "rams": shortlist(Ram.objects.all(), 18),
        "storages": shortlist(Storage.objects.all(), 18),
        "gpus": shortlist(gpu_qs, 24),
        "cases": shortlist(Case.objects.all(), 16),
        "psus": shortlist(Psu.objects.all(), 16),
        "coolers": shortlist(CpuCooler.objects.all(), 14),
    }


def min_price(parts: Mapping[str, List[object]], key: str) -> float:
    values = [part_price(item) for item in parts.get(key, [])]
    return min(values) if values else 0.0


def max_price(parts: Mapping[str, List[object]], key: str) -> float:
    values = [part_price(item) for item in parts.get(key, [])]
    return max(values) if values else 0.0


def still_fit_budget(
    current_price: float,
    min_remaining: float,
    max_remaining: float,
    budget_min: float,
    budget_max: float,
) -> bool:
    if current_price + min_remaining > budget_max:
        return False
    if current_price + max_remaining < budget_min:
        return False
    return True


def require_candidate_parts(parts: Mapping[str, List[object]]) -> bool:
    return all(
        parts.get(key)
        for key in (
            "cpus",
            "mbs",
            "rams",
            "storages",
            "gpus",
            "cases",
            "psus",
            "coolers",
        )
    )


def build_scoring_stats(parts: Mapping[str, List[object]]):
    return build_normalization_stats(
        cpus=[obj_to_score_dict(x) for x in parts["cpus"]],
        gpus=[obj_to_score_dict(x) for x in parts["gpus"]],
        rams=[obj_to_score_dict(x) for x in parts["rams"]],
        storages=[obj_to_score_dict(x) for x in parts["storages"]],
    )


def order_candidate_parts(
    parts: Dict[str, List[object]], workload: str
) -> Dict[str, List[object]]:
    """让组合枚举先看到更可能进入 Top-K 的配件，避免早停被低端组合占满。"""
    ordered = {key: list(value) for key, value in parts.items()}

    ordered["cpus"].sort(
        key=lambda x: (
            to_float(getattr(x, "single_score", 0.0)),
            to_float(getattr(x, "multi_score", 0.0)),
        ),
        reverse=True,
    )
    ordered["gpus"].sort(
        key=lambda x: (
            to_float(getattr(x, "gaming_score", 0.0)),
            to_float(getattr(x, "compute_score", 0.0)),
        ),
        reverse=True,
    )
    ordered["rams"].sort(
        key=lambda x: (
            to_float(getattr(x, "capacity", 0.0))
            * to_int(getattr(x, "module_count", 1), 1),
            to_float(getattr(x, "frequency", 0.0)),
        ),
        reverse=True,
    )
    ordered["storages"].sort(
        key=lambda x: (
            to_float(getattr(x, "read_speed", 0.0)),
            to_float(getattr(x, "capacity", 0.0)),
        ),
        reverse=True,
    )

    if workload == WORKLOAD_OFFICE:
        ordered["cpus"].sort(key=lambda x: part_price(x))
        ordered["gpus"].sort(key=lambda x: part_price(x))

    return ordered


def build_candidate_item(
    cpu, mb, ram, storage, gpu, case, psu, cooler, total_price, workload, stats
):
    scores = score_build(
        cpu=obj_to_score_dict(cpu),
        gpu=obj_to_score_dict(gpu),
        ram=obj_to_score_dict(ram),
        storage=obj_to_score_dict(storage),
        stats=stats,
        workload=workload,
    )
    combo_value = scores["total_score"] / max(total_price, 1.0)
    scores["cpu_score_100"] = scale_0_100(scores["cpu_score"])
    scores["gpu_score_100"] = scale_0_100(scores["gpu_score"])
    scores["ram_score_100"] = scale_0_100(scores["ram_score"])
    scores["storage_score_100"] = scale_0_100(scores["storage_score"])
    scores["total_score_100"] = scale_0_100(scores["total_score"])
    return {
        "parts": {
            "cpu": cpu,
            "mb": mb,
            "ram": ram,
            "gpu": gpu,
            "storage": storage,
            "case": case,
            "psu": psu,
            "cooler": cooler,
        },
        "total_price": total_price,
        "scores": scores,
        "combo_value": combo_value,
    }


def iter_cpu_mb_ram(
    parts: Mapping[str, List[object]],
    budget_min: float,
    budget_max: float,
    price_bounds: Mapping[str, float],
):
    for cpu in parts["cpus"]:
        cpu_price = part_price(cpu)
        if not still_fit_budget(
            cpu_price,
            price_bounds["min_after_cpu"],
            price_bounds["max_after_cpu"],
            budget_min,
            budget_max,
        ):
            continue
        for mb in parts["mbs"]:
            cpu_mb_price = cpu_price + part_price(mb)
            if not still_fit_budget(
                cpu_mb_price,
                price_bounds["min_after_cpu_mb"],
                price_bounds["max_after_cpu_mb"],
                budget_min,
                budget_max,
            ):
                continue
            if not is_compatible({"cpu": cpu, "mb": mb}):
                continue
            for ram in parts["rams"]:
                cpu_mb_ram_price = cpu_mb_price + part_price(ram)
                if not still_fit_budget(
                    cpu_mb_ram_price,
                    price_bounds["min_after_cpu_mb_ram"],
                    price_bounds["max_after_cpu_mb_ram"],
                    budget_min,
                    budget_max,
                ):
                    continue
                if not is_compatible({"cpu": cpu, "mb": mb, "ram": ram}):
                    continue
                yield cpu, mb, ram


def iter_gpu_case_psu(
    parts: Mapping[str, List[object]],
    cpu,
    mb,
    ram,
    budget_min: float,
    budget_max: float,
    price_bounds: Mapping[str, float],
):
    base_price = sum_price([cpu, mb, ram])
    for gpu in parts["gpus"]:
        with_gpu_price = base_price + part_price(gpu)
        if not still_fit_budget(
            with_gpu_price,
            price_bounds["min_after_gpu"],
            price_bounds["max_after_gpu"],
            budget_min,
            budget_max,
        ):
            continue
        for case in parts["cases"]:
            with_case_price = with_gpu_price + part_price(case)
            if not still_fit_budget(
                with_case_price,
                price_bounds["min_after_gpu_case"],
                price_bounds["max_after_gpu_case"],
                budget_min,
                budget_max,
            ):
                continue
            if not is_compatible({"mb": mb, "gpu": gpu, "case": case}):
                continue
            for psu in parts["psus"]:
                with_psu_price = with_case_price + part_price(psu)
                if not still_fit_budget(
                    with_psu_price,
                    price_bounds["min_after_gpu_case_psu"],
                    price_bounds["max_after_gpu_case_psu"],
                    budget_min,
                    budget_max,
                ):
                    continue
                if not is_compatible(
                    {"cpu": cpu, "gpu": gpu, "case": case, "psu": psu}
                ):
                    continue
                yield gpu, case, psu


def iter_storage_cooler_candidates(
    parts: Mapping[str, List[object]],
    cpu,
    mb,
    ram,
    gpu,
    case,
    psu,
    budget_min: float,
    budget_max: float,
):
    for storage in parts["storages"]:
        if sum_price([cpu, mb, ram, gpu, case, psu, storage]) > budget_max:
            continue
        for cooler in parts["coolers"]:
            total_price = sum_price([cpu, mb, ram, gpu, case, psu, storage, cooler])
            if total_price > budget_max or total_price < budget_min:
                continue
            payload = as_parts_payload(
                {
                    "cpu": cpu,
                    "mb": mb,
                    "ram": ram,
                    "storage": storage,
                    "gpu": gpu,
                    "case": case,
                    "psu": psu,
                    "cooler": cooler,
                }
            )
            if not is_compatible(payload):
                continue
            yield storage, cooler, total_price


def collect_feasible_candidates(
    parts, workload: str, budget_min: float, budget_max: float, stats
):
    feasible: List[Dict[str, object]] = []
    cpu_gpu_pair_counts: Dict[tuple[object, object], int] = {}
    max_per_cpu_gpu_pair = 8
    price_bounds = {
        "min_after_cpu": sum(
            min_price(parts, key)
            for key in ("mbs", "rams", "gpus", "cases", "psus", "storages", "coolers")
        ),
        "max_after_cpu": sum(
            max_price(parts, key)
            for key in ("mbs", "rams", "gpus", "cases", "psus", "storages", "coolers")
        ),
        "min_after_cpu_mb": sum(
            min_price(parts, key)
            for key in ("rams", "gpus", "cases", "psus", "storages", "coolers")
        ),
        "max_after_cpu_mb": sum(
            max_price(parts, key)
            for key in ("rams", "gpus", "cases", "psus", "storages", "coolers")
        ),
        "min_after_cpu_mb_ram": sum(
            min_price(parts, key)
            for key in ("gpus", "cases", "psus", "storages", "coolers")
        ),
        "max_after_cpu_mb_ram": sum(
            max_price(parts, key)
            for key in ("gpus", "cases", "psus", "storages", "coolers")
        ),
        "min_after_gpu": sum(
            min_price(parts, key) for key in ("cases", "psus", "storages", "coolers")
        ),
        "max_after_gpu": sum(
            max_price(parts, key) for key in ("cases", "psus", "storages", "coolers")
        ),
        "min_after_gpu_case": sum(
            min_price(parts, key) for key in ("psus", "storages", "coolers")
        ),
        "max_after_gpu_case": sum(
            max_price(parts, key) for key in ("psus", "storages", "coolers")
        ),
        "min_after_gpu_case_psu": sum(
            min_price(parts, key) for key in ("storages", "coolers")
        ),
        "max_after_gpu_case_psu": sum(
            max_price(parts, key) for key in ("storages", "coolers")
        ),
    }
    for cpu, mb, ram in iter_cpu_mb_ram(parts, budget_min, budget_max, price_bounds):
        for gpu, case, psu in iter_gpu_case_psu(
            parts, cpu, mb, ram, budget_min, budget_max, price_bounds
        ):
            pair_key = (
                getattr(cpu, "id", getattr(cpu, "name", None)),
                getattr(gpu, "id", getattr(gpu, "name", None)),
            )
            if cpu_gpu_pair_counts.get(pair_key, 0) >= max_per_cpu_gpu_pair:
                continue
            for storage, cooler, total_price in iter_storage_cooler_candidates(
                parts, cpu, mb, ram, gpu, case, psu, budget_min, budget_max
            ):
                feasible.append(
                    build_candidate_item(
                        cpu=cpu,
                        mb=mb,
                        ram=ram,
                        storage=storage,
                        gpu=gpu,
                        case=case,
                        psu=psu,
                        cooler=cooler,
                        total_price=total_price,
                        workload=workload,
                        stats=stats,
                    )
                )
                cpu_gpu_pair_counts[pair_key] = cpu_gpu_pair_counts.get(pair_key, 0) + 1
                if cpu_gpu_pair_counts[pair_key] >= max_per_cpu_gpu_pair:
                    break
                if is_limit_reached(feasible):
                    return feasible
    return feasible


def post_process_candidates(feasible: List[Dict[str, object]]):
    """按性能优先排序，并生成更有区分度的性价比展示分。"""
    trimmed = feasible
    trimmed.sort(
        key=lambda x: (x["scores"]["total_score"], x["combo_value"]), reverse=True
    )

    # 用分位映射替代 min-max，避免 Top-K 展示分长期扎堆接近 100。
    sorted_by_value = sorted(trimmed, key=lambda x: x["combo_value"])
    n = len(sorted_by_value)
    if n <= 1:
        trimmed[0]["combo_value_100"] = 70.0
        return trimmed

    for rank, item in enumerate(sorted_by_value):
        percentile = rank / (n - 1)
        # 将分位值映射到 [35, 95]，顶部组合保留优势但不“满分化”。
        item["combo_value_100"] = 35.0 + percentile * 60.0
    return trimmed


def part_id(item: Mapping[str, object], key: str) -> object:
    part = (
        item.get("parts", {}).get(key) if isinstance(item.get("parts"), dict) else None
    )
    return getattr(part, "id", getattr(part, "name", None))


def core_signature(item: Mapping[str, object]) -> tuple[object, ...]:
    return tuple(part_id(item, key) for key in ("cpu", "gpu", "mb", "ram", "storage"))


def is_diverse_enough(
    candidate: Mapping[str, object], selected: List[Dict[str, object]]
) -> bool:
    """展示方案必须在核心配置上有可感知差异。"""
    for item in selected:
        if core_signature(candidate) == core_signature(item):
            return False

        cpu_diff = part_id(candidate, "cpu") != part_id(item, "cpu")
        gpu_diff = part_id(candidate, "gpu") != part_id(item, "gpu")
        if not (cpu_diff or gpu_diff):
            return False
    return True


def select_diverse_top_items(
    feasible: List[Dict[str, object]], top_k: int
) -> List[Dict[str, object]]:
    selected: List[Dict[str, object]] = []
    max_same_core_part = max(1, ceil(top_k / 2))
    for item in feasible:
        cpu_id = part_id(item, "cpu")
        gpu_id = part_id(item, "gpu")
        if (
            sum(
                1
                for selected_item in selected
                if part_id(selected_item, "cpu") == cpu_id
            )
            >= max_same_core_part
        ):
            continue
        if (
            sum(
                1
                for selected_item in selected
                if part_id(selected_item, "gpu") == gpu_id
            )
            >= max_same_core_part
        ):
            continue
        if is_diverse_enough(item, selected):
            selected.append(item)
            if len(selected) >= top_k:
                return selected

    # 预算或品牌约束太窄时仍保证有结果，但尽量避免完全重复核心件。
    seen_signatures = {core_signature(item) for item in selected}
    for item in feasible:
        signature = core_signature(item)
        if signature in seen_signatures:
            continue
        selected.append(item)
        seen_signatures.add(signature)
        if len(selected) >= top_k:
            return selected

    for item in feasible:
        if item not in selected:
            selected.append(item)
            if len(selected) >= top_k:
                return selected
    return selected


def recommend_builds(params: RecommendationRequest) -> Dict[str, object]:
    """推荐程序入口：在预算与兼容性约束下生成并返回 Top-K 组合。"""
    workload = normalize_workload(params.workload)
    budget_min, budget_max = normalize_budget_range(params)
    top_k = max(1, to_int(params.top_k, 3))

    candidate_parts = load_candidate_parts(params)
    if not require_candidate_parts(candidate_parts):
        return {"items": [], "meta": {"reason": "配件数据不足，无法生成组合。"}}

    candidate_parts = order_candidate_parts(candidate_parts, workload)
    stats = build_scoring_stats(candidate_parts)
    feasible = collect_feasible_candidates(
        candidate_parts,
        workload=workload,
        budget_min=budget_min,
        budget_max=budget_max,
        stats=stats,
    )

    if not feasible:
        return {"items": [], "meta": {"reason": "未找到满足预算与兼容性要求的组合。"}}

    feasible = post_process_candidates(feasible)
    top_items = select_diverse_top_items(feasible, top_k)

    for item in top_items:
        item["reason"] = score_reason(workload, item["scores"])

    return {
        "items": top_items,
        "meta": {
            "workload": workload,
            "budget_min": budget_min,
            "budget_max": budget_max,
            "candidate_count": len(feasible),
        },
    }
