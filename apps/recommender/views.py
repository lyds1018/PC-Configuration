"""推荐模块视图层

负责表单参数接收处理、调用推荐算法、推荐结果渲染
"""
import threading
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from .service.agent.agent import run_agent_recommendation, get_agent_client
from .service.recommend.recommendation import RecommendationRequest, recommend_builds
from .service.utils import (
    CPU_BRAND_OPTIONS,
    GPU_CHIP_BRAND_OPTIONS,
    WORKLOAD_GAME,
    EMPTY_REASON,
)


def extract_form_data(request):
    """读取推荐页请求参数。"""
    return {
        "budget_min": request.GET.get("budget_min", ""),
        "budget_max": request.GET.get("budget_max", ""),
        "workload": request.GET.get("workload", WORKLOAD_GAME),  # 默认游戏
        "cpu_brand": request.GET.get("cpu_brand", ""),
        "gpu_chip_brand": request.GET.get("gpu_chip_brand", ""),
        "free_text": request.GET.get("free_text", ""),
        "top_k": request.GET.get("top_k", "3"),  # 默认返回3套配置
    }


def build_default_form_data(request):
    """构建推荐页表单，优先使用上次会话缓存。"""
    form_data = {
        "budget_min": "",
        "budget_max": "",
        "workload": WORKLOAD_GAME,
        "cpu_brand": "",
        "gpu_chip_brand": "",
        "free_text": "",
        "top_k": "3",
    }

    # 使用上次会话内容填充
    cached = request.session.get("recommender_last_form_data")
    if isinstance(cached, dict):
        form_data.update({k: cached.get(k, v) for k, v in form_data.items()})

    return form_data


def read_agent(agent_result, key, default=EMPTY_REASON):
    """读取智能体输出中的指定文本类字段，并转字符串返回。"""
    if not isinstance(agent_result, dict):
        return default
    return str(agent_result.get(key, default)).strip()


def inject_agent_reason(recommendations, agent_result):
    """给组合注入推荐理由，再按 Agent 推荐排名排序"""
    selected = []

    # 过滤出 Agent 推荐列表中的组合，并注入推荐理由
    choices = agent_result.get("choices", [])
    for choice in choices:
        item = recommendations[choice.get("combo_index") - 1]

        item["reason"] = choice.get("reason", "").strip()

        selected.append((choice["rank"], item))

    # 按 Agent 推荐排名排序
    selected.sort(key=lambda x: x[0])

    return [item for _, item in selected]


def build_recommendation_result(form_data):
    """
    智能推荐流程：
    1. 推荐算法生成候选组合
    2. Agent 结合用户需求对候选组合进行二次筛选与排序
    3. 生成推荐理由，返回推荐方案
    """
    # 推荐算法生成候选组合
    result = recommend_builds(
        RecommendationRequest(
            budget_min=form_data["budget_min"] or 0,
            budget_max=form_data["budget_max"] or 0,
            workload=form_data["workload"],
            cpu_brand=form_data["cpu_brand"],
            gpu_chip_brand=form_data["gpu_chip_brand"],
        )
    )

    # Agent 智能推荐
    recommendations = result.get("items", [])
    meta = result.get("meta", {})
    agent_result = run_agent_recommendation(
        form_data=form_data,
        recommendations=recommendations,
    )

    # 注入推荐理由并按 Agent 推荐排名排序
    recommendations = inject_agent_reason(
        recommendations,
        agent_result,
    )

    return form_data, recommendations, meta, agent_result


def part_payload(obj):
    """提取配件名称、价格，用于保存进方案中"""
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


@login_required
def recommend_page(request):
    """渲染智能推荐首页框架，初始化智能体。"""
    
    # 后台线程并发完成智能体的初始化
    threading.Thread(target=get_agent_client, daemon=True).start()

    form_data = build_default_form_data(request)
    return render(
        request,
        "recommender/recommend.html",
        {
            "form_data": form_data,
            "cpu_brands": CPU_BRAND_OPTIONS,
            "gpu_chip_brands": GPU_CHIP_BRAND_OPTIONS,
        },
    )


@login_required
def recommend_result_page(request):
    """渲染推荐结果页面框架"""
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
    """填充推荐结果页面数据。"""
    form_data = extract_form_data(request)

    # 调用智能推荐算法
    form_data, recommendations, meta, agent_result = build_recommendation_result(
        form_data
    )
    rows = [recommendation_item_to_row(item) for item in recommendations]
    error_reason = read_agent(agent_result, "error_reason")
    agent_summary = read_agent(agent_result, "summary")
    agent_enabled = (
        bool(agent_result.get("enabled")) if isinstance(agent_result, dict) else False
    )

    request.session["recommender_last_form_data"] = form_data
    request.session["recommender_last_rows"] = rows
    request.session["recommender_last_agent_summary"] = agent_summary

    return JsonResponse(
        {
            "meta": meta,
            "rows": rows,
            "agent_enabled": agent_enabled,
            "error_reason": error_reason,
            "agent_summary": agent_summary,
        }
    )
