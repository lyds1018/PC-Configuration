"""推荐模块视图层

负责表单参数接收、偏好归一化、推荐结果渲染与 JSON 数据接口输出
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from pc_builder.models import Cpu

from .agent import run_agent_recommendation, warmup_agent_client
from .recommendation import RecommendationRequest, parse_user_preferences, recommend_builds
from .scoring import WORKLOAD_GAME


def _brand_options(queryset):
    """提取并排序品牌列表，用于渲染筛选选项。"""
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
EMPTY_REASON = "—"


def _extract_form_data(request):
    """统一读取推荐页查询参数，避免多处重复取值逻辑。"""
    return {
        "budget_min": request.GET.get("budget_min", ""),
        "budget_max": request.GET.get("budget_max", ""),
        "workload": request.GET.get("workload", WORKLOAD_GAME),
        "cpu_brand": request.GET.get("cpu_brand", ""),
        "gpu_chip_brand": request.GET.get("gpu_chip_brand", ""),
        "free_text": request.GET.get("free_text", ""),
        "top_k": request.GET.get("top_k", "3"),
    }


def _agent_value(agent_result, key, default=""):
    """安全读取 AI 助手输出字段，统一做字符串清洗。"""
    if not isinstance(agent_result, dict):
        return default
    return str(agent_result.get(key, default)).strip()


def _normalize_chip_brand(chip_brand: str) -> str:
    return chip_brand if chip_brand in GPU_CHIP_BRAND_OPTIONS else ""


def _normalize_form_data(form_data, parse_result):
    """融合显式表单输入与自由文本解析结果。"""
    budget_min = form_data["budget_min"] or parse_result.get("budget_min", "")
    budget_max = form_data["budget_max"] or parse_result.get("budget_max", "")
    workload = form_data["workload"] or parse_result.get("workload", WORKLOAD_GAME)
    cpu_brand = form_data["cpu_brand"] or parse_result.get("cpu_brand", "")
    gpu_chip_brand = form_data["gpu_chip_brand"] or parse_result.get("gpu_chip_brand", "")
    return {
        "budget_min": budget_min,
        "budget_max": budget_max,
        "workload": workload,
        "cpu_brand": cpu_brand,
        "gpu_chip_brand": _normalize_chip_brand(gpu_chip_brand),
        "free_text": form_data["free_text"],
        "top_k": form_data["top_k"] or "3",
    }


def _extract_choice_reason_map(agent_result):
    """提取 AI 返回的候选理由映射：combo_index -> reason。"""
    mapping = {}
    choices = agent_result.get("choices", []) if isinstance(agent_result, dict) else []
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        combo_index = choice.get("combo_index")
        reason = str(choice.get("reason", "")).strip()
        if isinstance(combo_index, int) and combo_index > 0 and reason:
            mapping[combo_index] = reason
    return mapping


def _inject_agent_reason(recommendations, agent_result):
    choice_reason_map = _extract_choice_reason_map(agent_result)
    for idx, item in enumerate(recommendations, start=1):
        if isinstance(item, dict):
            item["reason"] = choice_reason_map.get(idx, EMPTY_REASON)


def _build_default_form_data(request):
    """构建推荐页默认表单数据，优先使用上次会话缓存。"""
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
    """
    组合推荐流程：
    1) 解析自由文本并补全缺失表单项；
    2) 调用推荐引擎生成组合；
    3) 调用 agent 生成解释并回填到每个组合。
    """
    parse_result = parse_user_preferences(form_data["free_text"])
    normalized_form_data = _normalize_form_data(form_data, parse_result)

    result = recommend_builds(
        RecommendationRequest(
            budget_min=normalized_form_data["budget_min"] or 0,
            budget_max=normalized_form_data["budget_max"] or 0,
            workload=normalized_form_data["workload"],
            cpu_brand=normalized_form_data["cpu_brand"],
            gpu_chip_brand=normalized_form_data["gpu_chip_brand"],
            free_text=form_data["free_text"],
            top_k=normalized_form_data["top_k"] or 3,
        )
    )
    recommendations = result.get("items", [])
    meta = result.get("meta", {})
    agent_result = run_agent_recommendation(
        user_text=form_data["free_text"],
        form_data=normalized_form_data,
        recommendations=recommendations,
    )
    _inject_agent_reason(recommendations, agent_result)

    return normalized_form_data, recommendations, meta, parse_result, agent_result


@login_required
def recommend_page(request):
    # 页面打开时预热一次 LLM client，降低后续首次推荐时延。
    warmup_agent_client()
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
    form_data = _extract_form_data(request)
    return render(
        request,
        "recommender/recommend_result.html",
        {
            "form_data": form_data,
        },
    )


@login_required
def recommend_result_data(request):
    """返回推荐结果 JSON，供前端结果页异步加载。"""
    form_data = _extract_form_data(request)
    normalized_form_data, recommendations, meta, _parse_result, agent_result = _build_recommendation_result(form_data)
    request.session[LAST_FORM_SESSION_KEY] = normalized_form_data

    rows = [_recommendation_item_to_row(item) for item in recommendations]
    request.session["recommender_last_rows"] = rows
    request.session["recommender_last_agent_summary"] = _agent_value(agent_result, "summary")

    return JsonResponse(
        {
            "meta": meta,
            "agent_enabled": bool(agent_result.get("enabled")) if isinstance(agent_result, dict) else False,
            "agent_summary": _agent_value(agent_result, "summary"),
            "agent_reason": _agent_value(agent_result, "reason"),
            "rows": rows,
        }
    )


def _part_payload(obj):
    if obj is None:
        return {"name": "", "price": 0.0}
    return {
        "name": str(getattr(obj, "name", "") or ""),
        "price": float(getattr(obj, "price", 0.0) or 0.0),
    }


def _recommendation_item_to_row(item):
    parts = item.get("parts", {})
    scores = item.get("scores", {})
    cpu = parts.get("cpu")
    mb = parts.get("mb")
    ram = parts.get("ram")
    storage = parts.get("storage")
    gpu = parts.get("gpu")
    case = parts.get("case")
    psu = parts.get("psu")
    cooler = parts.get("cooler")
    return {
        "cpu": getattr(cpu, "name", ""),
        "mb": getattr(mb, "name", ""),
        "ram": getattr(ram, "name", ""),
        "storage": getattr(storage, "name", ""),
        "gpu": getattr(gpu, "name", ""),
        "case": getattr(case, "name", ""),
        "psu": getattr(psu, "name", ""),
        "cooler": getattr(cooler, "name", ""),
        "parts_detail": {
            "cpu": _part_payload(cpu),
            "mb": _part_payload(mb),
            "ram": _part_payload(ram),
            "storage": _part_payload(storage),
            "gpu": _part_payload(gpu),
            "case": _part_payload(case),
            "psu": _part_payload(psu),
            "cooler": _part_payload(cooler),
        },
        "total_price": float(item.get("total_price", 0.0) or 0.0),
        "total_score_100": float(scores.get("total_score_100", 0.0) or 0.0),
        "combo_value_100": float(item.get("combo_value_100", 0.0) or 0.0),
        "reason": str(item.get("reason", EMPTY_REASON) or EMPTY_REASON),
    }
