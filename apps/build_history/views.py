from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from pc_builder.services import get_session_selection, resolve_selected_parts

from .models import BuildHistory

PART_LABELS = {
    "cpu": "CPU",
    "cooler": "CPU 散热器",
    "mb": "主板",
    "ram": "内存",
    "storage": "存储",
    "gpu": "显卡",
    "case": "机箱",
    "psu": "电源",
}
PART_ORDER = ["cpu", "cooler", "mb", "ram", "storage", "gpu", "case", "psu"]


@login_required
def history_list(request):
    histories = BuildHistory.objects.filter(user=request.user).order_by("-created_at")
    return render(
        request,
        "build_history/history.html",
        {"histories": histories, "part_labels": PART_LABELS, "part_order": PART_ORDER},
    )


@login_required
def history_detail(request, history_id):
    history = get_object_or_404(BuildHistory, id=history_id, user=request.user)
    return render(
        request,
        "build_history/history_detail.html",
        {"history": history, "part_labels": PART_LABELS, "part_order": PART_ORDER},
    )


@login_required
def delete_history(request, history_id):
    if request.method != "POST":
        return redirect("build_history:history_list")
    history = get_object_or_404(BuildHistory, id=history_id, user=request.user)
    history.delete()
    messages.success(request, "已删除该历史方案。")
    return redirect("build_history:history_list")


@login_required
def save_diy_build(request):
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method != "POST":
        if is_ajax:
            return JsonResponse({"ok": False, "message": "请求方式不正确。"}, status=405)
        return redirect("pc_builder:build_pc")

    selected_ids = get_session_selection(request)
    selected, total_price = resolve_selected_parts(selected_ids)
    if not selected:
        if is_ajax:
            return JsonResponse({"ok": False, "message": "当前没有可保存的配置，请先选择配件。"}, status=400)
        messages.warning(request, "当前没有可保存的配置，请先选择配件。")
        return redirect("pc_builder:build_pc")

    payload_parts = {}
    for key, obj in selected.items():
        payload_parts[key] = {
            "id": getattr(obj, "id", None),
            "name": getattr(obj, "name", ""),
            "price": float(getattr(obj, "price", 0.0) or 0.0),
        }
    payload = {
        "parts": payload_parts,
        "storage_qty": int(selected_ids.get("storage_qty", 1) or 1),
    }
    title = (request.POST.get("title") or "").strip() or f"DIY方案 {timezone.now().strftime('%Y-%m-%d %H:%M')}"

    BuildHistory.objects.create(
        user=request.user,
        source=BuildHistory.SOURCE_DIY,
        title=title,
        total_price=float(total_price or 0.0),
        payload=payload,
    )
    if is_ajax:
        return JsonResponse({"ok": True, "message": "已保存当前 DIY 装机方案。"})
    messages.success(request, "已保存当前 DIY 装机方案。")
    return redirect("build_history:history_list")


@login_required
def save_recommend_combo(request, index):
    if request.method != "POST":
        return redirect("build_history:history_list")

    rows = request.session.get("recommender_last_rows", [])
    summary = request.session.get("recommender_last_agent_summary", "")
    if not isinstance(rows, list) or index < 1 or index > len(rows):
        return JsonResponse({"ok": False, "message": "未找到可保存的推荐方案。"}, status=400)

    row = rows[index - 1]
    row_parts_detail = row.get("parts_detail", {})

    def _normalize_part(key):
        part = row_parts_detail.get(key)
        if isinstance(part, dict):
            return {
                "name": str(part.get("name", "") or ""),
                "price": float(part.get("price", 0.0) or 0.0),
            }
        # Backward compatibility for old session rows that only store part names.
        return str(row.get(key, "") or "")

    parts = {
        "cpu": _normalize_part("cpu"),
        "mb": _normalize_part("mb"),
        "ram": _normalize_part("ram"),
        "storage": _normalize_part("storage"),
        "gpu": _normalize_part("gpu"),
        "case": _normalize_part("case"),
        "psu": _normalize_part("psu"),
        "cooler": _normalize_part("cooler"),
    }
    payload = {
        "parts": parts,
        "scores": {
            "total_score_100": row.get("total_score_100", 0),
            "combo_value_100": row.get("combo_value_100", 0),
        },
        "reason": row.get("reason", "—"),
    }
    input_title = (request.POST.get("title") or "").strip()
    title = input_title or f"智能推荐 方案 #{index}"

    BuildHistory.objects.create(
        user=request.user,
        source=BuildHistory.SOURCE_RECOMMEND,
        title=title,
        total_price=float(row.get("total_price", 0.0) or 0.0),
        summary=str(summary or ""),
        payload=payload,
    )
    return JsonResponse({"ok": True, "message": "已保存推荐方案。"})
