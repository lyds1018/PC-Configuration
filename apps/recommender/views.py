from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from pc_builder.models import Cpu, Gpu

from .agent import run_agent_recommendation
from .recommendation import RecommendationRequest, parse_user_preferences, recommend_builds
from .scoring import WORKLOAD_GAME


def _brand_options(queryset):
    values = (
        queryset.exclude(brand__isnull=True)
        .exclude(brand="")
        .values_list("brand", flat=True)
        .distinct()
        .order_by("brand")
    )
    return list(values)


@login_required
def recommend_page(request):
    form_data = {
        "budget_min": request.POST.get("budget_min", ""),
        "budget_max": request.POST.get("budget_max", ""),
        "workload": request.POST.get("workload", WORKLOAD_GAME),
        "cpu_brand": request.POST.get("cpu_brand", ""),
        "gpu_brand": request.POST.get("gpu_brand", ""),
        "free_text": request.POST.get("free_text", ""),
        "top_k": request.POST.get("top_k", "3"),
    }

    recommendations = []
    meta = {}
    parse_result = {}
    agent_result = {}

    if request.method == "POST":
        parse_result = parse_user_preferences(form_data["free_text"])
        budget_min = form_data["budget_min"] or parse_result.get("budget_min", "")
        budget_max = form_data["budget_max"] or parse_result.get("budget_max", "")
        workload = form_data["workload"] or parse_result.get("workload", WORKLOAD_GAME)
        cpu_brand = form_data["cpu_brand"] or parse_result.get("cpu_brand", "")
        gpu_brand = form_data["gpu_brand"] or parse_result.get("gpu_brand", "")

        result = recommend_builds(
            RecommendationRequest(
                budget_min=budget_min or 0,
                budget_max=budget_max or 0,
                workload=workload,
                cpu_brand=cpu_brand,
                gpu_brand=gpu_brand,
                free_text=form_data["free_text"],
                top_k=form_data["top_k"] or 3,
            )
        )
        recommendations = result.get("items", [])
        meta = result.get("meta", {})
        agent_result = run_agent_recommendation(
            user_text=form_data["free_text"],
            form_data=form_data,
            recommendations=recommendations,
        )

        form_data.update(
            {
                "budget_min": budget_min,
                "budget_max": budget_max,
                "workload": workload,
                "cpu_brand": cpu_brand,
                "gpu_brand": gpu_brand,
            }
        )

    return render(
        request,
        "recommender/recommend.html",
        {
            "form_data": form_data,
            "recommendations": recommendations,
            "meta": meta,
            "parse_result": parse_result,
            "agent_result": agent_result,
            "cpu_brands": _brand_options(Cpu.objects.all()),
            "gpu_brands": _brand_options(Gpu.objects.all()),
        },
    )
