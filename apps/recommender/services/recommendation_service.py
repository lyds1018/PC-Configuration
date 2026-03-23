from dataclasses import dataclass
from typing import Dict, List

from pc_builder.models import Case, Cpu, CpuCooler, Gpu, Mb, Psu, Ram, Storage

from ..core.engine import build_recommendation
from ..core.filters import filter_cpu_brand, filter_gpu_brand
from ..models import RecommendationHistory

RECOMMENDATION_PROFILES = ("value", "balanced", "performance")
DEFAULT_PRIORITY_MODE = "auto"


@dataclass(frozen=True)
class RecommendationRequest:
    budget_min: float
    budget_max: float
    usage: str
    cpu_brand: str
    gpu_brand: str
    priority_mode: str


def build_request_from_form(cleaned_data: Dict[str, object]) -> RecommendationRequest:
    return RecommendationRequest(
        budget_min=cleaned_data["budget_min"],
        budget_max=cleaned_data["budget_max"],
        usage=cleaned_data["usage"],
        cpu_brand=cleaned_data["cpu_brand"],
        gpu_brand=cleaned_data["gpu_brand"],
        priority_mode=cleaned_data.get("priority_mode", DEFAULT_PRIORITY_MODE),
    )


def _get_component_querysets() -> Dict[str, object]:
    return {
        "cpu_qs": Cpu.objects.all(),
        "gpu_qs": Gpu.objects.all(),
        "ram_qs": Ram.objects.all(),
        "storage_qs": Storage.objects.all(),
        "mb_qs": Mb.objects.all(),
        "psu_qs": Psu.objects.all(),
        "case_qs": Case.objects.all(),
        "cooler_qs": CpuCooler.objects.all(),
    }


def _apply_brand_filters(component_qs: Dict[str, object], request_data: RecommendationRequest):
    component_qs["cpu_qs"] = filter_cpu_brand(component_qs["cpu_qs"], request_data.cpu_brand)
    component_qs["gpu_qs"] = filter_gpu_brand(component_qs["gpu_qs"], request_data.gpu_brand)
    return component_qs


def generate_recommendation_results(request_data: RecommendationRequest) -> List[dict]:
    component_qs = _apply_brand_filters(_get_component_querysets(), request_data)
    results = []
    for profile in RECOMMENDATION_PROFILES:
        result = build_recommendation(
            profile=profile,
            usage=request_data.usage,
            budget_min=request_data.budget_min,
            budget_max=request_data.budget_max,
            priority_mode=request_data.priority_mode,
            **component_qs,
        )
        if result:
            results.append(result)
    return results


def save_recommendation_history(user, request_data: RecommendationRequest, results: List[dict]):
    if not results:
        return

    top_result = results[0]
    RecommendationHistory.objects.create(
        user=user,
        budget_min=request_data.budget_min,
        budget_max=request_data.budget_max,
        usage=request_data.usage,
        cpu_brand=request_data.cpu_brand,
        gpu_brand=request_data.gpu_brand,
        priority_mode=request_data.priority_mode,
        selected_profile=top_result.get("profile", ""),
        total_price=top_result.get("total", 0),
        estimated_wattage=top_result.get("estimated_watt", 0),
    )
