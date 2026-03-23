"""
推荐系统视图模块

处理用户请求，生成推荐方案
"""

from typing import Dict, List

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from pc_builder.models import Case, Cpu, CpuCooler, Gpu, Mb, Psu, Ram, Storage

from .core.engine import build_recommendation
from .core.filters import filter_cpu_brand, filter_gpu_brand
from .forms import RecommendationForm
from .models import RecommendationHistory
from .utils.logger import get_logger

logger = get_logger(__name__)

RECOMMENDATION_PROFILES = ("value", "balanced", "performance")
DEFAULT_PRIORITY_MODE = "auto"


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


def _generate_results(
    budget_min: float,
    budget_max: float,
    usage: str,
    priority_mode: str,
    component_qs: Dict[str, object],
) -> List[dict]:
    results = []

    for profile in RECOMMENDATION_PROFILES:
        try:
            result = build_recommendation(
                profile=profile,
                usage=usage,
                budget_min=budget_min,
                budget_max=budget_max,
                priority_mode=priority_mode,
                **component_qs,
            )
            if result:
                results.append(result)
        except Exception:
            # 单个档位失败不影响其他档位
            logger.exception(
                "Error generating recommendation profile=%s usage=%s budget=%s-%s",
                profile,
                usage,
                budget_min,
                budget_max,
            )

    return results


def _save_recommendation_history(request_user, form_data: Dict[str, object], results):
    if not results:
        return

    top_result = results[0]
    try:
        RecommendationHistory.objects.create(
            user=request_user,
            budget_min=form_data["budget_min"],
            budget_max=form_data["budget_max"],
            usage=form_data["usage"],
            cpu_brand=form_data["cpu_brand"],
            gpu_brand=form_data["gpu_brand"],
            priority_mode=form_data["priority_mode"],
            selected_profile=top_result.get("profile", ""),
            total_price=top_result.get("total", 0),
            estimated_wattage=top_result.get("estimated_watt", 0),
        )
    except Exception:
        logger.exception("Error saving recommendation history for user=%s", request_user)


@login_required
def recommend(request):
    """
    推荐配置主视图

    处理用户输入的预算、用途等参数，生成个性化的 PC 配置方案
    """
    context = {
        "form": RecommendationForm(),
        "results": [],
    }

    if request.method == "POST":
        form = RecommendationForm(request.POST)

        if form.is_valid():
            form_data = {
                "budget_min": form.cleaned_data["budget_min"],
                "budget_max": form.cleaned_data["budget_max"],
                "usage": form.cleaned_data["usage"],
                "cpu_brand": form.cleaned_data["cpu_brand"],
                "gpu_brand": form.cleaned_data["gpu_brand"],
                "priority_mode": form.cleaned_data.get(
                    "priority_mode", DEFAULT_PRIORITY_MODE
                ),
            }

            component_qs = _get_component_querysets()
            component_qs["cpu_qs"] = filter_cpu_brand(
                component_qs["cpu_qs"], form_data["cpu_brand"]
            )
            component_qs["gpu_qs"] = filter_gpu_brand(
                component_qs["gpu_qs"], form_data["gpu_brand"]
            )

            results = _generate_results(
                budget_min=form_data["budget_min"],
                budget_max=form_data["budget_max"],
                usage=form_data["usage"],
                priority_mode=form_data["priority_mode"],
                component_qs=component_qs,
            )

            _save_recommendation_history(request.user, form_data, results)

            context["results"] = results
            context["form"] = form  # 保留已填写的表单

            if not results:
                messages.warning(
                    request, "未找到合适的配置方案，请尝试调整预算或选择其他选项。"
                )
        else:
            messages.error(request, "表单验证失败，请检查输入。")
            context["form"] = form

    return render(request, "recommender/index.html", context)
