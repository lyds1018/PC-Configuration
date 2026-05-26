"""推荐引擎主流程

包含参数解析、候选集加载、组合枚举、兼容性约束过滤、
性能打分与排序后处理，是推荐结果生成的核心编排模块
"""

import re
from dataclasses import dataclass
from math import ceil
from typing import Dict, List, Mapping

from pc_builder.models import Case, Cpu, CpuCooler, Gpu, Mb, Psu, Ram, Storage

from .scoring import (
    WORKLOAD_GAME,
    WORKLOAD_OFFICE,
    WORKLOAD_PRODUCTIVITY,
    build_normalization_stats,
    score_build,
)
from .utils import (
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

WORKLOAD_TEXT_RULES = {
    WORKLOAD_GAME: ("游戏", "电竞", "3a", "fps"),
    WORKLOAD_OFFICE: ("办公", "文档", "表格", "日常"),
    WORKLOAD_PRODUCTIVITY: ("生产力", "渲染", "剪辑", "建模", "开发", "ai"),
}

KNOWN_CPU_BRANDS = ("AMD", "英特尔", "INTEL")
KNOWN_GPU_CARD_BRANDS = ("华硕", "微星", "技嘉", "七彩虹", "影驰", "蓝宝石")


@dataclass
class RecommendationRequest:
    """推荐请求参数：由表单输入和自由文本共同补全。"""

    budget_min: float = 0.0
    budget_max: float = 0.0
    workload: str = WORKLOAD_GAME
    cpu_brand: str = ""
    gpu_chip_brand: str = ""
    gpu_card_brand: str = ""
    free_text: str = ""
    top_k: int = 3


def parse_user_preferences(free_text: str) -> Dict[str, str]:
    """
    从自然语言中提取预算、用途与品牌偏好。
    解析失败时返回空值，由显式表单字段兜底。
    """
    text = (free_text or "").strip()
    lowered = text.lower()

    workload = ""
    for key, keywords in WORKLOAD_TEXT_RULES.items():
        if any(word in lowered for word in keywords):
            workload = key
            break

    budget_min = ""
    budget_max = ""
    numbers = re.findall(r"(\d{3,6})", text)
    if "到" in text or "-" in text or "~" in text:
        if len(numbers) >= 2:
            budget_min = numbers[0]
            budget_max = numbers[1]
    elif numbers:
        budget_max = numbers[0]

    cpu_brand = ""
    gpu_chip_brand = ""
    gpu_card_brand = ""
    upper_text = text.upper()
    if "NVIDIA" in upper_text or "英伟达" in text:
        gpu_chip_brand = "NVIDIA"
    elif "AMD" in upper_text:
        if not gpu_chip_brand:
            gpu_chip_brand = "AMD"
        if not cpu_brand:
            cpu_brand = "AMD"
    elif "INTEL" in upper_text or "英特尔" in text:
        if not cpu_brand:
                cpu_brand = "英特尔"

    if not cpu_brand:
        for brand in KNOWN_CPU_BRANDS:
            if brand in upper_text or brand in text:
                cpu_brand = normalize_brand(brand)
                break

    for card_brand in KNOWN_GPU_CARD_BRANDS:
        if card_brand in text:
            gpu_card_brand = card_brand
            break

    return {
        "workload": workload,
        "budget_min": budget_min,
        "budget_max": budget_max,
        "cpu_brand": cpu_brand,
        "gpu_chip_brand": gpu_chip_brand,
        "gpu_card_brand": gpu_card_brand,
    }


def _brand_filter(queryset, brand: str):
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


def _gpu_chip_brand_filter(queryset, chip_brand: str):
    normalized = normalize_brand(chip_brand)
    if not normalized:
        return queryset
    return queryset.filter(chip_brand__iexact=normalized)


def _gpu_card_brand_filter(queryset, card_brand: str):
    text = (card_brand or "").strip()
    if not text:
        return queryset
    return queryset.filter(card_brand__icontains=text)


def _shortlist(queryset, limit: int):
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


def _score_reason(workload: str, scores: Mapping[str, float]) -> str:
    if workload == WORKLOAD_GAME:
        return f"游戏侧重显卡，GPU分 {scores['gpu_score_100']:.1f}/100，整机总分 {scores['total_score_100']:.1f}/100。"
    if workload == WORKLOAD_OFFICE:
        return f"办公侧重稳定与效率，CPU分 {scores['cpu_score_100']:.1f}/100，内存分 {scores['ram_score_100']:.1f}/100。"
    return f"生产力侧重并行与计算，CPU分 {scores['cpu_score_100']:.1f}/100，GPU分 {scores['gpu_score_100']:.1f}/100。"


def _normalize_budget_range(params: RecommendationRequest) -> tuple[float, float]:
    budget_min = max(0.0, to_float(params.budget_min, 0.0))
    budget_max = max(0.0, to_float(params.budget_max, 0.0))
    if budget_max <= 0:
        budget_max = 20000.0
    if budget_min > budget_max:
        budget_min, budget_max = budget_max, budget_min
    return budget_min, budget_max


def _load_candidate_parts(params: RecommendationRequest) -> Dict[str, List[object]]:
    cpu_qs = _brand_filter(Cpu.objects.all(), params.cpu_brand)
    gpu_qs = _gpu_chip_brand_filter(Gpu.objects.all(), params.gpu_chip_brand)
    gpu_qs = _gpu_card_brand_filter(gpu_qs, params.gpu_card_brand)

    return {
        "cpus": _shortlist(cpu_qs, 16),
        "mbs": _shortlist(Mb.objects.all(), 18),
        "rams": _shortlist(Ram.objects.all(), 18),
        "storages": _shortlist(Storage.objects.all(), 18),
        "gpus": _shortlist(gpu_qs, 24),
        "cases": _shortlist(Case.objects.all(), 16),
        "psus": _shortlist(Psu.objects.all(), 16),
        "coolers": _shortlist(CpuCooler.objects.all(), 14),
    }


def _min_price(parts: Mapping[str, List[object]], key: str) -> float:
    values = [part_price(item) for item in parts.get(key, [])]
    return min(values) if values else 0.0


def _max_price(parts: Mapping[str, List[object]], key: str) -> float:
    values = [part_price(item) for item in parts.get(key, [])]
    return max(values) if values else 0.0


def _can_still_fit_budget(
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


def _has_required_candidate_parts(parts: Mapping[str, List[object]]) -> bool:
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


def _build_scoring_stats(parts: Mapping[str, List[object]]):
    return build_normalization_stats(
        cpus=[obj_to_score_dict(x) for x in parts["cpus"]],
        gpus=[obj_to_score_dict(x) for x in parts["gpus"]],
        rams=[obj_to_score_dict(x) for x in parts["rams"]],
        storages=[obj_to_score_dict(x) for x in parts["storages"]],
    )


def _order_candidate_parts(parts: Dict[str, List[object]], workload: str) -> Dict[str, List[object]]:
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
            to_float(getattr(x, "capacity", 0.0)) * to_int(getattr(x, "module_count", 1), 1),
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


def _build_candidate_item(
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


def _iter_cpu_mb_ram(
    parts: Mapping[str, List[object]],
    budget_min: float,
    budget_max: float,
    price_bounds: Mapping[str, float],
):
    for cpu in parts["cpus"]:
        cpu_price = part_price(cpu)
        if not _can_still_fit_budget(
            cpu_price,
            price_bounds["min_after_cpu"],
            price_bounds["max_after_cpu"],
            budget_min,
            budget_max,
        ):
            continue
        for mb in parts["mbs"]:
            cpu_mb_price = cpu_price + part_price(mb)
            if not _can_still_fit_budget(
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
                if not _can_still_fit_budget(
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


def _iter_gpu_case_psu(
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
        if not _can_still_fit_budget(
            with_gpu_price,
            price_bounds["min_after_gpu"],
            price_bounds["max_after_gpu"],
            budget_min,
            budget_max,
        ):
            continue
        for case in parts["cases"]:
            with_case_price = with_gpu_price + part_price(case)
            if not _can_still_fit_budget(
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
                if not _can_still_fit_budget(
                    with_psu_price,
                    price_bounds["min_after_gpu_case_psu"],
                    price_bounds["max_after_gpu_case_psu"],
                    budget_min,
                    budget_max,
                ):
                    continue
                if not is_compatible({"cpu": cpu, "gpu": gpu, "case": case, "psu": psu}):
                    continue
                yield gpu, case, psu


def _iter_storage_cooler_candidates(
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


def _collect_feasible_candidates(parts, workload: str, budget_min: float, budget_max: float, stats):
    feasible: List[Dict[str, object]] = []
    cpu_gpu_pair_counts: Dict[tuple[object, object], int] = {}
    max_per_cpu_gpu_pair = 8
    price_bounds = {
        "min_after_cpu": sum(_min_price(parts, key) for key in ("mbs", "rams", "gpus", "cases", "psus", "storages", "coolers")),
        "max_after_cpu": sum(_max_price(parts, key) for key in ("mbs", "rams", "gpus", "cases", "psus", "storages", "coolers")),
        "min_after_cpu_mb": sum(_min_price(parts, key) for key in ("rams", "gpus", "cases", "psus", "storages", "coolers")),
        "max_after_cpu_mb": sum(_max_price(parts, key) for key in ("rams", "gpus", "cases", "psus", "storages", "coolers")),
        "min_after_cpu_mb_ram": sum(_min_price(parts, key) for key in ("gpus", "cases", "psus", "storages", "coolers")),
        "max_after_cpu_mb_ram": sum(_max_price(parts, key) for key in ("gpus", "cases", "psus", "storages", "coolers")),
        "min_after_gpu": sum(_min_price(parts, key) for key in ("cases", "psus", "storages", "coolers")),
        "max_after_gpu": sum(_max_price(parts, key) for key in ("cases", "psus", "storages", "coolers")),
        "min_after_gpu_case": sum(_min_price(parts, key) for key in ("psus", "storages", "coolers")),
        "max_after_gpu_case": sum(_max_price(parts, key) for key in ("psus", "storages", "coolers")),
        "min_after_gpu_case_psu": sum(_min_price(parts, key) for key in ("storages", "coolers")),
        "max_after_gpu_case_psu": sum(_max_price(parts, key) for key in ("storages", "coolers")),
    }
    for cpu, mb, ram in _iter_cpu_mb_ram(parts, budget_min, budget_max, price_bounds):
        for gpu, case, psu in _iter_gpu_case_psu(
            parts, cpu, mb, ram, budget_min, budget_max, price_bounds
        ):
            pair_key = (
                getattr(cpu, "id", getattr(cpu, "name", None)),
                getattr(gpu, "id", getattr(gpu, "name", None)),
            )
            if cpu_gpu_pair_counts.get(pair_key, 0) >= max_per_cpu_gpu_pair:
                continue
            for storage, cooler, total_price in _iter_storage_cooler_candidates(
                parts, cpu, mb, ram, gpu, case, psu, budget_min, budget_max
            ):
                feasible.append(
                    _build_candidate_item(
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


def _post_process_candidates(feasible: List[Dict[str, object]]):
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


def _part_id(item: Mapping[str, object], key: str) -> object:
    part = item.get("parts", {}).get(key) if isinstance(item.get("parts"), dict) else None
    return getattr(part, "id", getattr(part, "name", None))


def _core_signature(item: Mapping[str, object]) -> tuple[object, ...]:
    return tuple(_part_id(item, key) for key in ("cpu", "gpu", "mb", "ram", "storage"))


def _diff_count(left: Mapping[str, object], right: Mapping[str, object], keys) -> int:
    return sum(1 for key in keys if _part_id(left, key) != _part_id(right, key))


def _is_diverse_enough(candidate: Mapping[str, object], selected: List[Dict[str, object]]) -> bool:
    """展示方案必须在核心配置上有可感知差异。"""
    for item in selected:
        if _core_signature(candidate) == _core_signature(item):
            return False

        cpu_diff = _part_id(candidate, "cpu") != _part_id(item, "cpu")
        gpu_diff = _part_id(candidate, "gpu") != _part_id(item, "gpu")
        if not (cpu_diff or gpu_diff):
            return False
    return True


def _select_diverse_top_items(
    feasible: List[Dict[str, object]], top_k: int
) -> List[Dict[str, object]]:
    selected: List[Dict[str, object]] = []
    max_same_core_part = max(1, ceil(top_k / 2))
    for item in feasible:
        cpu_id = _part_id(item, "cpu")
        gpu_id = _part_id(item, "gpu")
        if sum(1 for selected_item in selected if _part_id(selected_item, "cpu") == cpu_id) >= max_same_core_part:
            continue
        if sum(1 for selected_item in selected if _part_id(selected_item, "gpu") == gpu_id) >= max_same_core_part:
            continue
        if _is_diverse_enough(item, selected):
            selected.append(item)
            if len(selected) >= top_k:
                return selected

    # 预算或品牌约束太窄时仍保证有结果，但尽量避免完全重复核心件。
    seen_signatures = {_core_signature(item) for item in selected}
    for item in feasible:
        signature = _core_signature(item)
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
    """推荐主入口：在预算与兼容性约束下生成并返回 Top-K 组合。"""
    workload = normalize_workload(params.workload)
    budget_min, budget_max = _normalize_budget_range(params)
    top_k = max(1, to_int(params.top_k, 3))

    candidate_parts = _load_candidate_parts(params)
    if not _has_required_candidate_parts(candidate_parts):
        return {"items": [], "meta": {"reason": "配件数据不足，无法生成组合。"}}

    candidate_parts = _order_candidate_parts(candidate_parts, workload)
    stats = _build_scoring_stats(candidate_parts)
    feasible = _collect_feasible_candidates(
        candidate_parts,
        workload=workload,
        budget_min=budget_min,
        budget_max=budget_max,
        stats=stats,
    )

    if not feasible:
        return {"items": [], "meta": {"reason": "未找到满足预算与兼容性要求的组合。"}}

    feasible = _post_process_candidates(feasible)
    top_items = _select_diverse_top_items(feasible, top_k)

    for item in top_items:
        item["reason"] = _score_reason(workload, item["scores"])

    return {
        "items": top_items,
        "meta": {
            "workload": workload,
            "budget_min": budget_min,
            "budget_max": budget_max,
            "candidate_count": len(feasible),
        },
    }
