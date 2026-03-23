"""
推荐系统视图模块

处理用户请求，生成推荐方案
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from pc_builder.models import Case, Cpu, CpuCooler, Gpu, Mb, Psu, Ram, Storage

from .core.engine import build_recommendation
from .core.filters import filter_cpu_brand, filter_gpu_brand
from .forms import RecommendationForm
from .models import RecommendationHistory


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
            # 提取表单数据
            budget_min = form.cleaned_data["budget_min"]
            budget_max = form.cleaned_data["budget_max"]
            usage = form.cleaned_data["usage"]
            cpu_brand = form.cleaned_data["cpu_brand"]
            gpu_brand = form.cleaned_data["gpu_brand"]
            priority_mode = form.cleaned_data.get("priority_mode", "auto")

            # 获取配件查询集
            cpu_qs = Cpu.objects.all()
            gpu_qs = Gpu.objects.all()
            ram_qs = Ram.objects.all()
            storage_qs = Storage.objects.all()
            mb_qs = Mb.objects.all()
            psu_qs = Psu.objects.all()
            case_qs = Case.objects.all()
            cooler_qs = CpuCooler.objects.all()

            # 应用品牌过滤
            cpu_list = filter_cpu_brand(cpu_qs, cpu_brand)
            gpu_list = filter_gpu_brand(gpu_qs, gpu_brand)

            # 生成三种方案的推荐
            results = []
            for profile in ("value", "balanced", "performance"):
                try:
                    result = build_recommendation(
                        profile=profile,
                        usage=usage,
                        budget_min=budget_min,
                        budget_max=budget_max,
                        cpu_qs=cpu_list,
                        gpu_qs=gpu_list,
                        ram_qs=ram_qs,
                        storage_qs=storage_qs,
                        mb_qs=mb_qs,
                        psu_qs=psu_qs,
                        case_qs=case_qs,
                        cooler_qs=cooler_qs,
                        priority_mode=priority_mode,
                    )
                    if result:
                        results.append(result)
                except Exception as e:
                    # 记录错误但不中断其他方案生成
                    print(f"Error generating {profile} recommendation: {e}")

            # 保存推荐历史
            if results:
                try:
                    RecommendationHistory.objects.create(
                        user=request.user,
                        budget_min=budget_min,
                        budget_max=budget_max,
                        usage=usage,
                        cpu_brand=cpu_brand,
                        gpu_brand=gpu_brand,
                        priority_mode=priority_mode,
                        selected_profile=results[0]["profile"] if results else "",
                        total_price=results[0]["total"] if results else 0,
                        estimated_wattage=results[0]["estimated_watt"]
                        if results
                        else 0,
                    )
                except Exception as e:
                    print(f"Error saving history: {e}")

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
