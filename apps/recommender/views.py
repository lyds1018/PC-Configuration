"""推荐模块视图层

负责表单参数接收、偏好归一化、推荐结果渲染与 JSON 数据接口输出
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from pc_builder.models import Cpu

from .agent import run_agent_recommendation, warmup_agent_client
from .service.recommend.recommendation import RecommendationRequest, recommend_builds
from .service.utils import WORKLOAD_GAME


def brand_options(queryset):
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


def extract_form_data(request):
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


def agent_value(agent_result, key, default=""):
    """安全读取 AI 助手输出字段，统一做字符串清洗。"""
    if not isinstance(agent_result, dict):
        return default
    return str(agent_result.get(key, default)).strip()


def extract_choice_reason_map(agent_result):
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


def inject_agent_reason(recommendations, agent_result):
    choice_reason_map = extract_choice_reason_map(agent_result)
    for idx, item in enumerate(recommendations, start=1):
        if isinstance(item, dict):
            item["reason"] = choice_reason_map.get(idx, EMPTY_REASON)


def build_default_form_data(request):
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


def build_recommendation_result(form_data):
    """
    组合推荐流程：
    1. 解析自由文本并补全缺失表单项
    2. 调用推荐引擎生成组合
    3. 调用 agent 生成解释并回填到每个组合
    """
    result = recommend_builds(
        RecommendationRequest(
            budget_min=form_data["budget_min"] or 0,
            budget_max=form_data["budget_max"] or 0,
            workload=form_data["workload"],
            cpu_brand=form_data["cpu_brand"],
            gpu_chip_brand=form_data["gpu_chip_brand"],
            free_text=form_data["free_text"],
        )
    )
    recommendations = result.get("items", [])
    meta = result.get("meta", {})
    agent_result = run_agent_recommendation(
        user_text=form_data["free_text"],
        form_data=form_data,
        recommendations=recommendations,
    )
    inject_agent_reason(recommendations, agent_result)

    top_k = int(form_data["top_k"])
    recommendations = recommendations[:top_k]

    return form_data, recommendations, meta, agent_result


@login_required
def recommend_page(request):
    # 页面打开时预热一次 LLM client，降低后续首次推荐时延。
    warmup_agent_client()
    form_data = build_default_form_data(request)
    return render(
        request,
        "recommender/recommend.html",
        {
            "form_data": form_data,
            "cpu_brands": brand_options(Cpu.objects.all()),
            "gpu_chip_brands": GPU_CHIP_BRAND_OPTIONS,
        },
    )


@login_required
def recommend_result_page(request):
    form_data = extract_form_data(request)
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
    form_data = extract_form_data(request)
    form_data, recommendations, meta, agent_result = build_recommendation_result(
        form_data
    )
    request.session[LAST_FORM_SESSION_KEY] = form_data

    rows = [recommendation_item_to_row(item) for item in recommendations]
    request.session["recommender_last_rows"] = rows
    request.session["recommender_last_agent_summary"] = agent_value(
        agent_result, "summary"
    )

    return JsonResponse(
        {
            "meta": meta,
            "agent_enabled": bool(agent_result.get("enabled"))
            if isinstance(agent_result, dict)
            else False,
            "agent_summary": agent_value(agent_result, "summary"),
            "agent_reason": agent_value(agent_result, "reason"),
            "rows": rows,
        }
    )


def part_payload(obj):
    if obj is None:
        return {"name": "", "price": 0.0}
    return {
        "name": str(getattr(obj, "name", "") or ""),
        "price": float(getattr(obj, "price", 0.0) or 0.0),
    }


def recommendation_item_to_row(item):
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
            "cpu": part_payload(cpu),
            "mb": part_payload(mb),
            "ram": part_payload(ram),
            "storage": part_payload(storage),
            "gpu": part_payload(gpu),
            "case": part_payload(case),
            "psu": part_payload(psu),
            "cooler": part_payload(cooler),
        },
        "total_price": float(item.get("total_price", 0.0) or 0.0),
        "total_score_100": float(scores.get("total_score_100", 0.0) or 0.0),
        "combo_value_100": float(item.get("combo_value_100", 0.0) or 0.0),
        "reason": str(item.get("reason", EMPTY_REASON) or EMPTY_REASON),
    }
