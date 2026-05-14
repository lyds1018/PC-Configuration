import re
from dataclasses import dataclass
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
    从自然语言中提取用户偏好。
    解析失败时返回空值，由后续显式表单字段兜底。
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
    return list(queryset.order_by("price")[:limit])


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
        "cpus": _shortlist(cpu_qs, 12),
        "mbs": _shortlist(Mb.objects.all(), 15),
        "rams": _shortlist(Ram.objects.all(), 12),
        "storages": _shortlist(Storage.objects.all(), 12),
        "gpus": _shortlist(gpu_qs, 12),
        "cases": _shortlist(Case.objects.all(), 12),
        "psus": _shortlist(Psu.objects.all(), 12),
        "coolers": _shortlist(CpuCooler.objects.all(), 10),
    }


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


def _iter_cpu_mb_ram(parts: Mapping[str, List[object]], budget_max: float):
    for cpu in parts["cpus"]:
        if part_price(cpu) > budget_max:
            continue
        for mb in parts["mbs"]:
            if sum_price([cpu, mb]) > budget_max:
                continue
            if not is_compatible({"cpu": cpu, "mb": mb}):
                continue
            for ram in parts["rams"]:
                if sum_price([cpu, mb, ram]) > budget_max:
                    continue
                if not is_compatible({"cpu": cpu, "mb": mb, "ram": ram}):
                    continue
                yield cpu, mb, ram


def _iter_gpu_case_psu(parts: Mapping[str, List[object]], cpu, mb, ram, budget_max: float):
    for gpu in parts["gpus"]:
        if sum_price([cpu, mb, ram, gpu]) > budget_max:
            continue
        for case in parts["cases"]:
            if sum_price([cpu, mb, ram, gpu, case]) > budget_max:
                continue
            if not is_compatible({"mb": mb, "gpu": gpu, "case": case}):
                continue
            for psu in parts["psus"]:
                if sum_price([cpu, mb, ram, gpu, case, psu]) > budget_max:
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
    for cpu, mb, ram in _iter_cpu_mb_ram(parts, budget_max):
        for gpu, case, psu in _iter_gpu_case_psu(parts, cpu, mb, ram, budget_max):
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
                if is_limit_reached(feasible):
                    return feasible
    return feasible


def _post_process_candidates(feasible: List[Dict[str, object]]):
    """按性价比粗筛后再按性能排序，并生成 0-100 的性价比展示分。"""
    feasible.sort(key=lambda x: x["combo_value"], reverse=True)
    cutoff = int(len(feasible) * 0.7)
    trimmed = feasible[: max(cutoff, 1)]
    trimmed.sort(
        key=lambda x: (x["scores"]["total_score"], x["combo_value"]), reverse=True
    )

    min_combo = min(item["combo_value"] for item in trimmed)
    max_combo = max(item["combo_value"] for item in trimmed)
    combo_range = max_combo - min_combo
    for item in trimmed:
        if combo_range <= 0:
            item["combo_value_100"] = 100.0
        else:
            item["combo_value_100"] = (
                (item["combo_value"] - min_combo) / combo_range
            ) * 100.0
    return trimmed


def recommend_builds(params: RecommendationRequest) -> Dict[str, object]:
    """推荐主入口：加载候选、枚举可行组合、打分排序并返回 Top-K 结果。"""
    workload = normalize_workload(params.workload)
    budget_min, budget_max = _normalize_budget_range(params)
    top_k = max(1, to_int(params.top_k, 3))

    candidate_parts = _load_candidate_parts(params)
    if not _has_required_candidate_parts(candidate_parts):
        return {"items": [], "meta": {"reason": "配件数据不足，无法生成组合。"}}

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
    top_items = feasible[:top_k]

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
