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


def _as_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


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


def _derive_storage_totals(selected):
    storage = selected.get("storage")
    totals = {
        "total_m2": 0,
        "total_sata": 0,
        "total_sata_ssd": 0,
        "total_hdd": 0,
    }

    if not storage:
        return totals

    storage_type = str(getattr(storage, "type", "") or "").upper()
    if "M.2" in storage_type:
        totals["total_m2"] = 1
    else:
        totals["total_sata"] = 1
        if "HDD" in storage_type:
            totals["total_hdd"] = 1
        elif "SATA SSD" in storage_type:
            totals["total_sata_ssd"] = 1

    return totals


def build_compatibility_payload(selected):
    payload = {
        "cpu": {},
        "mb": {},
        "ram": {},
        "cooler": {},
        "gpu": {},
        "case": {},
        "psu": {},
        "storages": [],
        "totals": {
            "total_m2": 0,
            "total_sata": 0,
            "total_sata_ssd": 0,
            "total_hdd": 0,
            "total_memory": 0,
            "total_fan": 0,
        },
    }

    if selected.get("cpu"):
        payload["cpu"] = {
            "socket": selected["cpu"].socket,
            "memory_type": selected["cpu"].memory_type,
            "memory_speed": selected["cpu"].memory_speed,
            "tdp": selected["cpu"].tdp,
        }

    if selected.get("mb"):
        payload["mb"] = {
            "socket": selected["mb"].socket,
            "form": selected["mb"].form,
            "memory_type": selected["mb"].memory_type,
            "memory_frequency": selected["mb"].memory_frequency,
            "memory_slots": selected["mb"].memory_slots,
            "m2_slots": selected["mb"].m2_slots,
            "sata_ports": selected["mb"].sata_ports,
            "fan_slots": selected["mb"].fan_slots,
        }

    if selected.get("ram"):
        payload["ram"] = {
            "type": selected["ram"].type,
            "frequency": selected["ram"].frequency,
        }
        payload["totals"]["total_memory"] = _as_int(getattr(selected["ram"], "module_count", 1), default=1)

    if selected.get("cooler"):
        payload["cooler"] = {
            "type": selected["cooler"].type,
            "height": selected["cooler"].height,
            "water_size": selected["cooler"].water_size,
        }

    if selected.get("gpu"):
        payload["gpu"] = {
            "length": selected["gpu"].length,
            "tdp": selected["gpu"].tdp,
        }

    if selected.get("case"):
        payload["case"] = {
            "form": selected["case"].form,
            "gpu_length": selected["case"].gpu_length,
            "air_height": selected["case"].air_height,
            "water_size": selected["case"].water_size,
            "psu_form": selected["case"].psu_form,
            "storage_2_5": selected["case"].storage_2_5,
            "storage_3_5": selected["case"].storage_3_5,
        }

    if selected.get("psu"):
        payload["psu"] = {
            "form": selected["psu"].form,
            "wattage": selected["psu"].wattage,
        }

    if selected.get("storage"):
        payload["storages"].append({"type": selected["storage"].type})

    payload["totals"].update(_derive_storage_totals(selected))
    return payload


def estimate_wattage(selected):
    if not selected.get("cpu") or not selected.get("gpu"):
        return None

    cpu_tdp = float(selected["cpu"].tdp or 0)
    gpu_tdp = float(selected["gpu"].tdp or 0)
    return cpu_tdp + gpu_tdp


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
