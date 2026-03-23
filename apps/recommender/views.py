"""
推荐系统视图模块

处理用户请求，生成推荐方案
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .forms import RecommendationForm
from .services.recommendation_service import (
    build_request_from_form,
    generate_recommendation_results,
    save_recommendation_history,
)


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
            request_data = build_request_from_form(form.cleaned_data)
            results = generate_recommendation_results(request_data)
            save_recommendation_history(request.user, request_data, results)

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
