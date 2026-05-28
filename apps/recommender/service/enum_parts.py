from typing import Dict, List, Mapping

from ..scoring import score_build
from .utils import (
    MAX_CANDIDATES,
    as_parts_payload,
    is_compatible,
    max_price,
    min_price,
    obj_to_score_dict,
    part_price,
    scale_0_100,
    sum_price,
)


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
                if len(feasible) >= MAX_CANDIDATES:
                    return feasible
    return feasible
