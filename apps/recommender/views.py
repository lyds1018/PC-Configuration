from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from pc_builder.models import Cpu

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


GPU_CHIP_BRAND_OPTIONS = ["AMD", "NVIDIA"]
LAST_FORM_SESSION_KEY = "recommender_last_form_data"


def _build_default_form_data(request):
    default = {
        "budget_min": "",
        "budget_max": "",
        "workload": WORKLOAD_GAME,
        "cpu_brand": "",
        "gpu_chip_brand": "",
        "free_text": "",
        "top_k": "3",
    }
    cached = request.session.get(LAST_FORM_SESSION_KEY)
    if isinstance(cached, dict):
        default.update({k: cached.get(k, v) for k, v in default.items()})
    return default


def _build_recommendation_result(form_data):
    parse_result = parse_user_preferences(form_data["free_text"])
    budget_min = form_data["budget_min"] or parse_result.get("budget_min", "")
    budget_max = form_data["budget_max"] or parse_result.get("budget_max", "")
    workload = form_data["workload"] or parse_result.get("workload", WORKLOAD_GAME)
    cpu_brand = form_data["cpu_brand"] or parse_result.get("cpu_brand", "")
    gpu_chip_brand = form_data["gpu_chip_brand"] or parse_result.get("gpu_chip_brand", "")
    if gpu_chip_brand not in GPU_CHIP_BRAND_OPTIONS:
        gpu_chip_brand = ""

    normalized_form_data = {
        "budget_min": budget_min,
        "budget_max": budget_max,
        "workload": workload,
        "cpu_brand": cpu_brand,
        "gpu_chip_brand": gpu_chip_brand,
        "free_text": form_data["free_text"],
        "top_k": form_data["top_k"] or "3",
    }

    result = recommend_builds(
        RecommendationRequest(
            budget_min=budget_min or 0,
            budget_max=budget_max or 0,
            workload=workload,
            cpu_brand=cpu_brand,
            gpu_chip_brand=gpu_chip_brand,
            free_text=form_data["free_text"],
            top_k=form_data["top_k"] or 3,
        )
    )
    recommendations = result.get("items", [])
    meta = result.get("meta", {})
    agent_result = run_agent_recommendation(
        user_text=form_data["free_text"],
        form_data=normalized_form_data,
        recommendations=recommendations,
    )

    choice_reason_map = {}
    for choice in agent_result.get("choices", []) if isinstance(agent_result, dict) else []:
        if not isinstance(choice, dict):
            continue
        combo_index = choice.get("combo_index")
        reason = str(choice.get("reason", "")).strip()
        if isinstance(combo_index, int) and combo_index > 0 and reason:
            choice_reason_map[combo_index] = reason

    for idx, item in enumerate(recommendations, start=1):
        if isinstance(item, dict):
            item["reason"] = choice_reason_map.get(idx, "—")

    return normalized_form_data, recommendations, meta, parse_result, agent_result


@login_required
def recommend_page(request):
    form_data = _build_default_form_data(request)
    return render(
        request,
        "recommender/recommend.html",
        {
            "form_data": form_data,
            "cpu_brands": _brand_options(Cpu.objects.all()),
            "gpu_chip_brands": GPU_CHIP_BRAND_OPTIONS,
        },
    )


@login_required
def recommend_result_page(request):
    form_data = {
        "budget_min": request.GET.get("budget_min", ""),
        "budget_max": request.GET.get("budget_max", ""),
        "workload": request.GET.get("workload", WORKLOAD_GAME),
        "cpu_brand": request.GET.get("cpu_brand", ""),
        "gpu_chip_brand": request.GET.get("gpu_chip_brand", ""),
        "free_text": request.GET.get("free_text", ""),
        "top_k": request.GET.get("top_k", "3"),
    }
    return render(
        request,
        "recommender/recommend_result.html",
        {
            "form_data": form_data,
        },
    )


@login_required
def recommend_result_data(request):
    form_data = {
        "budget_min": request.GET.get("budget_min", ""),
        "budget_max": request.GET.get("budget_max", ""),
        "workload": request.GET.get("workload", WORKLOAD_GAME),
        "cpu_brand": request.GET.get("cpu_brand", ""),
        "gpu_chip_brand": request.GET.get("gpu_chip_brand", ""),
        "free_text": request.GET.get("free_text", ""),
        "top_k": request.GET.get("top_k", "3"),
    }
    normalized_form_data, recommendations, meta, _parse_result, agent_result = _build_recommendation_result(form_data)
    request.session[LAST_FORM_SESSION_KEY] = normalized_form_data

    rows = []
    for item in recommendations:
        parts = item.get("parts", {})
        scores = item.get("scores", {})
        rows.append(
            {
                "cpu": getattr(parts.get("cpu"), "name", ""),
                "mb": getattr(parts.get("mb"), "name", ""),
                "ram": getattr(parts.get("ram"), "name", ""),
                "storage": getattr(parts.get("storage"), "name", ""),
                "gpu": getattr(parts.get("gpu"), "name", ""),
                "case": getattr(parts.get("case"), "name", ""),
                "psu": getattr(parts.get("psu"), "name", ""),
                "cooler": getattr(parts.get("cooler"), "name", ""),
                "total_price": float(item.get("total_price", 0.0) or 0.0),
                "total_score_100": float(scores.get("total_score_100", 0.0) or 0.0),
                "combo_value_100": float(item.get("combo_value_100", 0.0) or 0.0),
                "reason": str(item.get("reason", "—") or "—"),
            }
        )

    request.session["recommender_last_rows"] = rows
    request.session["recommender_last_agent_summary"] = (
        str(agent_result.get("summary", "")).strip() if isinstance(agent_result, dict) else ""
    )

    return JsonResponse(
        {
            "meta": meta,
            "agent_enabled": bool(agent_result.get("enabled")) if isinstance(agent_result, dict) else False,
            "agent_summary": str(agent_result.get("summary", "")).strip() if isinstance(agent_result, dict) else "",
            "agent_reason": str(agent_result.get("reason", "")).strip() if isinstance(agent_result, dict) else "",
            "rows": rows,
        }
    )
