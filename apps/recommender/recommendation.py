import re
from dataclasses import dataclass
from typing import Dict, List, Mapping

from compatibility import run_pc_builder_checks
from pc_builder.models import Case, Cpu, CpuCooler, Gpu, Mb, Psu, Ram, Storage

from .scoring import (
    WORKLOAD_GAME,
    WORKLOAD_OFFICE,
    WORKLOAD_PRODUCTIVITY,
    build_normalization_stats,
    score_build,
)


WORKLOAD_TEXT_RULES = {
    WORKLOAD_GAME: ("游戏", "电竞", "3a", "fps"),
    WORKLOAD_OFFICE: ("办公", "文档", "表格", "日常"),
    WORKLOAD_PRODUCTIVITY: ("生产力", "渲染", "剪辑", "建模", "开发", "ai"),
}

KNOWN_CPU_BRANDS = ("AMD", "英特尔", "INTEL")
KNOWN_GPU_CARD_BRANDS = ("华硕", "微星", "技嘉", "七彩虹", "影驰", "蓝宝石")
MAX_FEASIBLE_COMBOS = 500


@dataclass
class RecommendationRequest:
    budget_min: float = 0.0
    budget_max: float = 0.0
    workload: str = WORKLOAD_GAME
    cpu_brand: str = ""
    gpu_chip_brand: str = ""
    gpu_card_brand: str = ""
    free_text: str = ""
    top_k: int = 3


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _normalize_brand(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    upper = text.upper()
    if upper in {"INTEL", "英特尔"}:
        return "英特尔"
    if upper in {"AMD"}:
        return "AMD"
    if upper in {"NVIDIA", "英伟达"}:
        return "NVIDIA"
    return text


def _normalize_workload(value: str) -> str:
    text = (value or "").strip().lower()
    if text in {WORKLOAD_GAME, "游戏"}:
        return WORKLOAD_GAME
    if text in {WORKLOAD_OFFICE, "办公"}:
        return WORKLOAD_OFFICE
    if text in {WORKLOAD_PRODUCTIVITY, "生产力"}:
        return WORKLOAD_PRODUCTIVITY
    return WORKLOAD_GAME


def parse_user_preferences(free_text: str) -> Dict[str, str]:
    """
    从自由文本中提取偏好，解析失败时保持空值。
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
                cpu_brand = _normalize_brand(brand)
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


def _as_parts_payload(
    cpu: Cpu,
    mb: Mb,
    ram: Ram,
    storage: Storage,
    gpu: Gpu,
    case: Case,
    psu: Psu,
    cooler: CpuCooler,
) -> Dict[str, object]:
    return {
        "cpu": cpu,
        "mb": mb,
        "ram": ram,
        "storage": storage,
        "gpu": gpu,
        "case": case,
        "psu": psu,
        "cooler": cooler,
        "storages": [{"type": storage.type}] if storage else [],
        "totals": {
            "total_m2": 1 if storage and "M.2" in str(storage.type).upper() else 0,
            "total_sata": 0 if storage and "M.2" in str(storage.type).upper() else 1,
            "total_sata_ssd": 1 if storage and "SATA SSD" in str(storage.type).upper() else 0,
            "total_hdd": 1 if storage and "HDD" in str(storage.type).upper() else 0,
            "total_memory": _to_int(getattr(ram, "module_count", 1), 1),
        },
    }


def _part_price(part) -> float:
    return _to_float(getattr(part, "price", 0.0), 0.0)


def _sum_price(parts: List[object]) -> float:
    return sum(_part_price(p) for p in parts if p is not None)


def _brand_filter(queryset, brand: str):
    normalized = _normalize_brand(brand)
    if not normalized:
        return queryset
    if normalized == "NVIDIA":
        return queryset.filter(brand__icontains="NVIDIA") | queryset.filter(brand__icontains="英伟达")
    if normalized == "英特尔":
        return queryset.filter(brand__icontains="英特尔") | queryset.filter(brand__icontains="Intel")
    return queryset.filter(brand__icontains=normalized)


def _gpu_chip_brand_filter(queryset, chip_brand: str):
    normalized = _normalize_brand(chip_brand)
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


def _scale_0_100(value: float) -> float:
    return max(0.0, min(100.0, value * 100.0))


def _obj_to_score_dict(obj) -> Dict[str, float]:
    fields = [
        "single_score",
        "multi_score",
        "base_clock",
        "boost_clock",
        "core_count",
        "thread_count",
        "tdp",
        "gaming_score",
        "compute_score",
        "core_clock",
        "memory_clock",
        "vram_size",
        "capacity",
        "frequency",
        "latency",
        "cache_size",
        "read_speed",
        "write_speed",
        "random_read_iops",
        "random_write_iops",
    ]
    return {field: _to_float(getattr(obj, field, 0.0), 0.0) for field in fields}


def _is_compatible(parts: Mapping[str, object]) -> bool:
    return run_pc_builder_checks(dict(parts)).get("ok", False)


def _is_limit_reached(feasible: List[Dict[str, object]]) -> bool:
    return len(feasible) >= MAX_FEASIBLE_COMBOS


def _normalize_budget_range(params: RecommendationRequest) -> tuple[float, float]:
    budget_min = max(0.0, _to_float(params.budget_min, 0.0))
    budget_max = max(0.0, _to_float(params.budget_max, 0.0))
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
    return all(parts.get(key) for key in ("cpus", "mbs", "rams", "storages", "gpus", "cases", "psus", "coolers"))


def _build_scoring_stats(parts: Mapping[str, List[object]]):
    return build_normalization_stats(
        cpus=[_obj_to_score_dict(x) for x in parts["cpus"]],
        gpus=[_obj_to_score_dict(x) for x in parts["gpus"]],
        rams=[_obj_to_score_dict(x) for x in parts["rams"]],
        storages=[_obj_to_score_dict(x) for x in parts["storages"]],
    )


def _build_candidate_item(cpu, mb, ram, storage, gpu, case, psu, cooler, total_price, workload, stats):
    scores = score_build(
        cpu=_obj_to_score_dict(cpu),
        gpu=_obj_to_score_dict(gpu),
        ram=_obj_to_score_dict(ram),
        storage=_obj_to_score_dict(storage),
        stats=stats,
        workload=workload,
    )
    combo_value = scores["total_score"] / max(total_price, 1.0)
    scores["cpu_score_100"] = _scale_0_100(scores["cpu_score"])
    scores["gpu_score_100"] = _scale_0_100(scores["gpu_score"])
    scores["ram_score_100"] = _scale_0_100(scores["ram_score"])
    scores["storage_score_100"] = _scale_0_100(scores["storage_score"])
    scores["total_score_100"] = _scale_0_100(scores["total_score"])
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


def _collect_feasible_candidates(parts, workload: str, budget_min: float, budget_max: float, stats):
    cpus = parts["cpus"]
    mbs = parts["mbs"]
    rams = parts["rams"]
    storages = parts["storages"]
    gpus = parts["gpus"]
    cases = parts["cases"]
    psus = parts["psus"]
    coolers = parts["coolers"]

    feasible: List[Dict[str, object]] = []
    for cpu in cpus:
        if _part_price(cpu) > budget_max:
            continue
        for mb in mbs:
            if _sum_price([cpu, mb]) > budget_max:
                continue
            if not _is_compatible({"cpu": cpu, "mb": mb}):
                continue
            for ram in rams:
                if _sum_price([cpu, mb, ram]) > budget_max:
                    continue
                if not _is_compatible({"cpu": cpu, "mb": mb, "ram": ram}):
                    continue
                for gpu in gpus:
                    if _sum_price([cpu, mb, ram, gpu]) > budget_max:
                        continue
                    for case in cases:
                        if _sum_price([cpu, mb, ram, gpu, case]) > budget_max:
                            continue
                        if not _is_compatible({"mb": mb, "gpu": gpu, "case": case}):
                            continue
                        for psu in psus:
                            if _sum_price([cpu, mb, ram, gpu, case, psu]) > budget_max:
                                continue
                            if not _is_compatible({"cpu": cpu, "gpu": gpu, "case": case, "psu": psu}):
                                continue
                            for storage in storages:
                                if _sum_price([cpu, mb, ram, gpu, case, psu, storage]) > budget_max:
                                    continue
                                for cooler in coolers:
                                    total_price = _sum_price([cpu, mb, ram, gpu, case, psu, storage, cooler])
                                    if total_price > budget_max or total_price < budget_min:
                                        continue

                                    payload = _as_parts_payload(cpu, mb, ram, storage, gpu, case, psu, cooler)
                                    if not _is_compatible(payload):
                                        continue

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
                                    if _is_limit_reached(feasible):
                                        break
                                if _is_limit_reached(feasible):
                                    break
                            if _is_limit_reached(feasible):
                                break
                        if _is_limit_reached(feasible):
                            break
                    if _is_limit_reached(feasible):
                        break
                if _is_limit_reached(feasible):
                    break
            if _is_limit_reached(feasible):
                break
        if _is_limit_reached(feasible):
            break
    return feasible


def _post_process_candidates(feasible: List[Dict[str, object]]):
    feasible.sort(key=lambda x: x["combo_value"], reverse=True)
    cutoff = int(len(feasible) * 0.7)
    trimmed = feasible[: max(cutoff, 1)]
    trimmed.sort(key=lambda x: (x["scores"]["total_score"], x["combo_value"]), reverse=True)

    min_combo = min(item["combo_value"] for item in trimmed)
    max_combo = max(item["combo_value"] for item in trimmed)
    combo_range = max_combo - min_combo
    for item in trimmed:
        if combo_range <= 0:
            item["combo_value_100"] = 100.0
        else:
            item["combo_value_100"] = ((item["combo_value"] - min_combo) / combo_range) * 100.0
    return trimmed


def recommend_builds(params: RecommendationRequest) -> Dict[str, object]:
    workload = _normalize_workload(params.workload)
    budget_min, budget_max = _normalize_budget_range(params)
    top_k = max(1, _to_int(params.top_k, 3))

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
