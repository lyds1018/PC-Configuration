from .utils import normalize_brand, to_float, to_int, RecommendationRequest
from pc_builder.models import Case, Cpu, CpuCooler, Gpu, Mb, Psu, Ram, Storage
from typing import Dict, List

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


def evenly_sample(queryset, limit: int):
    '''按价格均匀抽样'''
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


def preference_parts(params: RecommendationRequest) -> Dict[str, List[object]]:
    cpu_qs = brand_filter(Cpu.objects.all(), params.cpu_brand)
    gpu_qs = gpu_chip_brand_filter(Gpu.objects.all(), params.gpu_chip_brand)

    return {
        "cpus": evenly_sample(cpu_qs, 16),
        "mbs": evenly_sample(Mb.objects.all(), 18),
        "rams": evenly_sample(Ram.objects.all(), 18),
        "storages": evenly_sample(Storage.objects.all(), 18),
        "gpus": evenly_sample(gpu_qs, 24),
        "cases": evenly_sample(Case.objects.all(), 16),
        "psus": evenly_sample(Psu.objects.all(), 16),
        "coolers": evenly_sample(CpuCooler.objects.all(), 14),
    }


def order_candidate_parts(
    parts: Dict[str, List[object]], workload: str
) -> Dict[str, List[object]]:
    """按性能字段对候选件进行排序。"""
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

    return ordered


def price_score(feasible: List[Dict[str, object]]):
    """按性能分值排序，计算出性价比分值。"""
    trimmed = feasible
    trimmed.sort(
        key=lambda x: (x["scores"]["total_score"], x["combo_value"]), reverse=True
    )

    # 分位映射
    sorted_by_value = sorted(trimmed, key=lambda x: x["combo_value"])
    n = len(sorted_by_value)
    if n <= 1:
        trimmed[0]["combo_value_100"] = 70.0
        return trimmed

    for rank, item in enumerate(sorted_by_value):
        percentile = rank / (n - 1)
        # 将分位值映射到 [35, 95]
        item["combo_value_100"] = 35.0 + percentile * 60.0
    return trimmed