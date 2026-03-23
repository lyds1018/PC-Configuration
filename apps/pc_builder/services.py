from django.db.models import Q
from django.shortcuts import get_object_or_404

from .catalog import (
    BUILD_CATEGORIES,
    COMPATIBILITY_REQUIRED_KEYS,
    PARTS_CONFIG,
    SELECTION_SESSION_KEY,
)
from .compatibility import run_checks


def _default_compatibility():
    return {"ok": True, "issues": []}


def get_session_selection(request):
    return request.session.get(SELECTION_SESSION_KEY, {})


def save_session_selection(request, selected):
    request.session[SELECTION_SESSION_KEY] = selected


def resolve_selected_parts(selected_ids):
    selected = {}
    total_price = 0.0

    for category in BUILD_CATEGORIES:
        key = category["key"]
        item_id = selected_ids.get(key)
        if not item_id:
            continue

        config = PARTS_CONFIG.get(key)
        if not config:
            continue

        model = config["model"]
        try:
            obj = model.objects.get(id=item_id)
        except model.DoesNotExist:
            continue

        selected[key] = obj
        total_price += float(getattr(obj, "price", 0) or 0)

    return selected, total_price


def build_compatibility_payload(selected):
    parts = {
        "cpu": {},
        "mb": {},
        "ram": {},
        "case": {},
        "psu": {},
        "gpu": {},
        "ssd": {},
        "storage_count": 1,
    }

    if selected.get("cpu"):
        parts["cpu"] = {"tdp": selected["cpu"].tdp}
    if selected.get("mb"):
        parts["mb"] = {
            "socket": selected["mb"].socket,
            "form_factor": selected["mb"].form_factor,
            "max_memory": selected["mb"].max_memory,
            "memory_slots": selected["mb"].memory_slots,
        }
    if selected.get("ram"):
        parts["ram"] = {"modules": selected["ram"].modules}
    if selected.get("case"):
        parts["case"] = {
            "type": selected["case"].type,
            "internal_35_bays": selected["case"].internal_35_bays,
        }
    if selected.get("psu"):
        parts["psu"] = {"wattage": selected["psu"].wattage}
    if selected.get("gpu"):
        parts["gpu"] = {"boost_clock": selected["gpu"].boost_clock}
    if selected.get("storage"):
        parts["ssd"] = {"type": selected["storage"].type}

    return parts


def estimate_wattage(selected):
    if not selected.get("cpu") or not selected.get("gpu"):
        return None

    cpu_power = float(selected["cpu"].tdp or 0)
    gpu_clock = float(selected["gpu"].boost_clock or 0)
    return cpu_power + (0.16 * gpu_clock + 50 if gpu_clock else 0)


def build_builder_context(request):
    selected_ids = get_session_selection(request)
    selected, total_price = resolve_selected_parts(selected_ids)

    can_check = all(selected.get(key) for key in COMPATIBILITY_REQUIRED_KEYS)
    compatibility = (
        run_checks(build_compatibility_payload(selected))
        if can_check
        else _default_compatibility()
    )

    return {
        "categories": BUILD_CATEGORIES,
        "selected": selected,
        "total_price": total_price,
        "compatibility": compatibility,
        "can_check": can_check,
        "estimated_wattage": estimate_wattage(selected),
    }


def select_part(request, part_type, pk):
    config = PARTS_CONFIG.get(part_type)
    if not config:
        return False

    model = config["model"]
    get_object_or_404(model, id=pk)

    selected = get_session_selection(request)
    selected[part_type] = pk
    save_session_selection(request, selected)
    return True


def build_part_list_context(request, part_type):
    config = PARTS_CONFIG.get(part_type)
    if not config:
        return {"invalid": True, "title": "配件"}

    q = (request.GET.get("q") or "").strip()
    sort = (request.GET.get("sort") or "price").strip()
    direction = (request.GET.get("dir") or "asc").strip().lower()

    columns = [{"key": key, "label": label} for key, label in config["columns"]]
    allowed_sort_fields = [col["key"] for col in columns]

    if sort not in allowed_sort_fields:
        sort = "price" if "price" in allowed_sort_fields else allowed_sort_fields[0]
    if direction not in {"asc", "desc"}:
        direction = "asc"

    queryset = config["model"].objects.all()
    if q:
        search_fields = config.get("search_fields") or ["name"]
        query = Q()
        for field in search_fields:
            query |= Q(**{f"{field}__icontains": q})
        queryset = queryset.filter(query)

    order_by = f"-{sort}" if direction == "desc" else sort
    queryset = queryset.order_by(order_by)

    selected_ids = get_session_selection(request)
    return {
        "title": config["title"],
        "part_type": part_type,
        "columns": columns,
        "items": queryset,
        "q": q,
        "sort": sort,
        "dir": direction,
        "selected_id": selected_ids.get(part_type),
    }
