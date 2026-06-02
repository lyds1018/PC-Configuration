from typing import Dict, List, Mapping

from ..score.scoring import score_build
from ..utils import (
    MAX_CANDIDATES,
    is_compatible,
    part_price,
    scale_0_100,
    sum_price,
    to_score_dict,
)


def build_candidate_item(
    cpu, mb, ram, storage, gpu, case, psu, cooler, total_price, workload, norm_bounds
):
    """计算单个组合的总评分、各配件评分及性价比。"""
    scores = score_build(
        cpu=to_score_dict(cpu),
        gpu=to_score_dict(gpu),
        ram=to_score_dict(ram),
        storage=to_score_dict(storage),
        bounds=norm_bounds,
        workload=workload,
    )
    combo_value = scores["total_score"] / max(
        total_price, 1.0
    )  # 性价比 = 性能分 / 价格
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


def build_price_bounds(parts: Mapping[str, List[object]]) -> Dict[str, float]:
    """计算各枚举阶段剩余配件总价上下界。"""

    stage_parts = {
        "cpu": ["mbs", "rams", "gpus", "cases", "psus", "storages", "coolers"],
        "cpu_mb": ["rams", "gpus", "cases", "psus", "storages", "coolers"],
        "cpu_mb_ram": ["gpus", "cases", "psus", "storages", "coolers"],
        "gpu": ["cases", "psus", "storages", "coolers"],
        "gpu_case": ["psus", "storages", "coolers"],
        "gpu_case_psu": ["storages", "coolers"],
    }

    category_bounds = {
        key: (
            min(part_price(p) for p in parts[key]),
            max(part_price(p) for p in parts[key]),
        )
        for key in {part for values in stage_parts.values() for part in values}
    }

    price_bounds = {}

    for stage, categories in stage_parts.items():
        price_bounds[f"min_after_{stage}"] = sum(
            category_bounds[key][0] for key in categories
        )
        price_bounds[f"max_after_{stage}"] = sum(
            category_bounds[key][1] for key in categories
        )

    return price_bounds


def still_fit_budget(
    current_price: float,
    min_remaining: float,
    max_remaining: float,
    budget_min: float,
    budget_max: float,
) -> bool:
    """判断 当前价格 + 剩余配件总价上下界 是否仍满足预算范围。"""
    if current_price + min_remaining > budget_max:
        return False
    if current_price + max_remaining < budget_min:
        return False
    return True


def iter_cpu_mb_ram(
    parts: Mapping[str, List[object]],
    budget_min: float,
    budget_max: float,
    price_bounds: Mapping[str, float],
):
    """枚举 CPU + 主板 + 内存 的可行组合。"""
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
            ) or not is_compatible({"cpu": cpu, "mb": mb}):
                continue

            for ram in parts["rams"]:
                total_price = cpu_mb_price + part_price(ram)

                if not still_fit_budget(
                    total_price,
                    price_bounds["min_after_cpu_mb_ram"],
                    price_bounds["max_after_cpu_mb_ram"],
                    budget_min,
                    budget_max,
                ) or not is_compatible({"cpu": cpu, "mb": mb, "ram": ram}):
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
    """枚举 GPU + 机箱 + 电源 的可行组合。"""

    base_price = sum_price([cpu, mb, ram])

    for gpu in parts["gpus"]:
        gpu_price = base_price + part_price(gpu)

        if not still_fit_budget(
            gpu_price,
            price_bounds["min_after_gpu"],
            price_bounds["max_after_gpu"],
            budget_min,
            budget_max,
        ):
            continue

        for case in parts["cases"]:
            case_price = gpu_price + part_price(case)

            if not still_fit_budget(
                case_price,
                price_bounds["min_after_gpu_case"],
                price_bounds["max_after_gpu_case"],
                budget_min,
                budget_max,
            ) or not is_compatible({"mb": mb, "gpu": gpu, "case": case}):
                continue

            for psu in parts["psus"]:
                total_price = case_price + part_price(psu)

                if not still_fit_budget(
                    total_price,
                    price_bounds["min_after_gpu_case_psu"],
                    price_bounds["max_after_gpu_case_psu"],
                    budget_min,
                    budget_max,
                ) or not is_compatible(
                    {
                        "cpu": cpu,
                        "gpu": gpu,
                        "case": case,
                        "psu": psu,
                    }
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
    """枚举硬盘 + 散热器可行组合。"""

    base_price = sum_price([cpu, mb, ram, gpu, case, psu])

    for storage in parts["storages"]:
        storage_price = base_price + part_price(storage)

        if storage_price > budget_max:
            continue

        for cooler in parts["coolers"]:
            total_price = storage_price + part_price(cooler)

            if not (budget_min <= total_price <= budget_max):
                continue

            if not is_compatible(
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
            ):
                continue

            yield storage, cooler, total_price


def collect_feasible_candidates(
    parts,
    workload: str,
    budget_min: float,
    budget_max: float,
    norm_bounds,
):
    """枚举过滤满足预算与兼容性约束的候选组合。"""

    feasible: List[Dict[str, object]] = []

    cpu_gpu_counts: Dict[tuple[object, object], int] = {}
    cpu_cooler_counts: Dict[tuple[object, object], int] = {}
    max_cpu_gpu = 4
    max_cpu_cooler = 4

    price_bounds = build_price_bounds(parts)

    for cpu, mb, ram in iter_cpu_mb_ram(
        parts,
        budget_min,
        budget_max,
        price_bounds,
    ):
        for gpu, case, psu in iter_gpu_case_psu(
            parts,
            cpu,
            mb,
            ram,
            budget_min,
            budget_max,
            price_bounds,
        ):
            pair_key_cpu_gpu = (
                getattr(cpu, "id", getattr(cpu, "name", None)),
                getattr(gpu, "id", getattr(gpu, "name", None)),
            )

            if cpu_gpu_counts.get(pair_key_cpu_gpu, 0) >= max_cpu_gpu:
                continue

            for storage, cooler, total_price in iter_storage_cooler_candidates(
                parts,
                cpu,
                mb,
                ram,
                gpu,
                case,
                psu,
                budget_min,
                budget_max,
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
                        norm_bounds=norm_bounds,
                    )
                )

                pair_key_cpu_cooler = (
                    getattr(cpu, "id", getattr(cpu, "name", None)),
                    getattr(cooler, "id", getattr(cooler, "name", None)),
                )

                # 更新组合计数器
                cpu_gpu_counts[pair_key_cpu_gpu] = (
                    cpu_gpu_counts.get(pair_key_cpu_gpu, 0) + 1
                )
                cpu_cooler_counts[pair_key_cpu_cooler] = (
                    cpu_cooler_counts.get(pair_key_cpu_cooler, 0) + 1
                )

                if cpu_cooler_counts[pair_key_cpu_cooler] >= max_cpu_cooler: 
                    continue

                if len(feasible) >= MAX_CANDIDATES:
                    return feasible

    return feasible
