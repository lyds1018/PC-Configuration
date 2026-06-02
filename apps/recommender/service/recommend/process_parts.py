import random
from ..utils import normalize_brand, to_float, to_int, RecommendationRequest
from pc_builder.models import Case, Cpu, CpuCooler, Gpu, Mb, Psu, Ram, Storage
from typing import Dict, List

def cpu_brand_filter(queryset, brand: str):
    """过滤CPU品牌"""
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
    """过滤GPU芯片品牌"""
    normalized = normalize_brand(chip_brand)
    if not normalized:
        return queryset
    return queryset.filter(chip_brand__iexact=normalized)


def evenly_sample(queryset, limit: int):
    """按价格均匀抽样"""
    items = list(queryset.order_by("price"))
    total_count = len(items)

    selected = []
    block_size = total_count / limit

    for i in range(limit):
        # 当前块索引
        start_index = int(i * block_size)
        end_index = int((i + 1) * block_size) - 1
        end_index = min(end_index, total_count - 1)

        final_index = random.randint(start_index, end_index)
        selected.append(items[final_index])

    return selected


def preference_parts(params: RecommendationRequest) -> Dict[str, List[object]]:
    """根据用户偏好过滤配件。"""
    cpu_qs = cpu_brand_filter(Cpu.objects.all(), params.cpu_brand)
    gpu_qs = gpu_chip_brand_filter(Gpu.objects.all(), params.gpu_chip_brand)

    return {
        "cpus": evenly_sample(cpu_qs, 40),
        "mbs": evenly_sample(Mb.objects.all(), 24),
        "rams": evenly_sample(Ram.objects.all(), 24),
        "storages": evenly_sample(Storage.objects.all(), 24),
        "gpus": evenly_sample(gpu_qs, 28),
        "cases": evenly_sample(Case.objects.all(), 28),
        "psus": evenly_sample(Psu.objects.all(), 28),
        "coolers": evenly_sample(CpuCooler.objects.all(), 28),
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
    """按评分与性价比排序，并对性价比做分位映射。"""
    trimmed = feasible
    trimmed.sort(
        key=lambda x: (x["scores"]["total_score"], x["combo_value"]), reverse=True
    )

    sorted_by_value = sorted(trimmed, key=lambda x: x["combo_value"])
    n = len(sorted_by_value)

    # 如果只有一个组合，返回默认分值
    if n <= 1:
        trimmed[0]["combo_value_100"] = 80.0
        return trimmed

    # 将分位值映射到 [35, 95]
    for rank, item in enumerate(sorted_by_value):
        percentile = rank / (n - 1)
        item["combo_value_100"] = 35.0 + percentile * 60.0
    
    return trimmed