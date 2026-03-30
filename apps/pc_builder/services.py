from django.db.models import DecimalField, FloatField, IntegerField, Max, Min, Q
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


def _read_quantity(selected_ids, key, default=1):
    qty_key = f"{key}_qty"
    qty = _as_int(selected_ids.get(qty_key), default=default)
    return max(1, qty)


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
        qty = _read_quantity(selected_ids, key) if key == "storage" else 1
        total_price += float(getattr(obj, "price", 0) or 0) * qty

    return selected, total_price


def _derive_storage_totals(selected, selected_ids):
    storage = selected.get("storage")
    totals = {
        "total_m2": 0,
        "total_sata": 0,
        "total_sata_ssd": 0,
        "total_hdd": 0,
    }

    if not storage:
        return totals

    qty = _read_quantity(selected_ids, "storage")
    storage_type = str(getattr(storage, "type", "") or "").upper()
    if "M.2" in storage_type:
        totals["total_m2"] = qty
    else:
        totals["total_sata"] = qty
        if "HDD" in storage_type:
            totals["total_hdd"] = qty
        elif "SATA SSD" in storage_type:
            totals["total_sata_ssd"] = qty

    return totals


def build_compatibility_payload(selected, selected_ids):
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
            "air_height": selected["cooler"].air_height,
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
        qty = _read_quantity(selected_ids, "storage")
        payload["storages"] += [{"type": selected["storage"].type}] * qty

    payload["totals"].update(_derive_storage_totals(selected, selected_ids))
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
        run_checks(build_compatibility_payload(selected, selected_ids))
        if can_check
        else _default_compatibility()
    )

    storage_qty = _read_quantity(selected_ids, "storage") if selected.get("storage") else 0
    storage_line_price = (
        float(getattr(selected["storage"], "price", 0) or 0) * storage_qty
        if selected.get("storage")
        else None
    )

    return {
        "categories": BUILD_CATEGORIES,
        "selected": selected,
        "storage_qty": storage_qty,
        "storage_line_price": storage_line_price,
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
    if part_type == "storage":
        qty = _as_int(request.POST.get("qty") or request.GET.get("qty"), default=1)
        selected["storage_qty"] = max(1, qty)

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

    model = config["model"]
    base_queryset = model.objects.all()
    queryset = base_queryset
    search_fields = config.get("search_fields") or ["name"]

    numeric_filters = []
    enum_filters = []

    # Brand filters: generic 'brand' for most parts, and GPU-specific chip/card brands.
    label_map = {
        "brand": "品牌",
        "chip_brand": "芯片品牌",
        "card_brand": "显卡品牌",
    }
    brand_fields = []
    for field_name in ("brand", "chip_brand", "card_brand"):
        try:
            model._meta.get_field(field_name)
            brand_fields.append(field_name)
        except Exception:
            continue

    for field_name in brand_fields:
        values = list(
            base_queryset.exclude(**{f"{field_name}__isnull": True})
            .exclude(**{field_name: ""})
            .values_list(field_name, flat=True)
            .distinct()
            .order_by(field_name)
        )
        if not values:
            continue

        selected_values = request.GET.getlist(field_name)
        if selected_values:
            queryset = queryset.filter(**{f"{field_name}__in": selected_values})
        enum_filters.append(
            {
                "field": field_name,
                "label": label_map.get(field_name, "品牌"),
                "options": values,
                "selected": selected_values,
            }
        )

    for field_key, label in config["columns"]:
        try:
            field_obj = model._meta.get_field(field_key)
        except Exception:
            continue

        if isinstance(field_obj, (IntegerField, FloatField, DecimalField)):
            bounds = base_queryset.aggregate(min_v=Min(field_key), max_v=Max(field_key))
            db_min = bounds.get("min_v")
            db_max = bounds.get("max_v")
            if db_min is None or db_max is None:
                continue

            min_param = f"{field_key}_min"
            max_param = f"{field_key}_max"
            selected_min_raw = (request.GET.get(min_param) or "").strip()
            selected_max_raw = (request.GET.get(max_param) or "").strip()

            selected_min = None
            selected_max = None
            if selected_min_raw != "":
                try:
                    selected_min = float(selected_min_raw)
                    queryset = queryset.filter(**{f"{field_key}__gte": selected_min})
                except ValueError:
                    selected_min = None
            if selected_max_raw != "":
                try:
                    selected_max = float(selected_max_raw)
                    queryset = queryset.filter(**{f"{field_key}__lte": selected_max})
                except ValueError:
                    selected_max = None

            current_min = selected_min if selected_min is not None else float(db_min)
            current_max = selected_max if selected_max is not None else float(db_max)

            numeric_filters.append(
                {
                    "field": field_key,
                    "label": label,
                    "db_min": db_min,
                    "db_max": db_max,
                    "selected_min": selected_min_raw,
                    "selected_max": selected_max_raw,
                    "current_min": current_min,
                    "current_max": current_max,
                    "step": "1" if isinstance(field_obj, IntegerField) else "0.1",
                }
            )
        elif field_key in search_fields and field_key not in {"name", "brand", "chip_brand", "card_brand"}:
            values = list(
                base_queryset.exclude(**{f"{field_key}__isnull": True})
                .exclude(**{field_key: ""})
                .values_list(field_key, flat=True)
                .distinct()
                .order_by(field_key)
            )
            if not values or len(values) > 20:
                continue

            selected_values = request.GET.getlist(field_key)
            if selected_values:
                queryset = queryset.filter(**{f"{field_key}__in": selected_values})

            enum_filters.append(
                {
                    "field": field_key,
                    "label": label,
                    "options": values,
                    "selected": selected_values,
                }
            )

    if q:
        query = Q()
        for field in search_fields:
            query |= Q(**{f"{field}__icontains": q})
        queryset = queryset.filter(query)

    order_by = f"-{sort}" if direction == "desc" else sort
    queryset = queryset.order_by(order_by)

    sort_params = request.GET.copy()
    sort_params.pop("sort", None)
    sort_params.pop("dir", None)
    sort_query_prefix = sort_params.urlencode()
    if sort_query_prefix:
        sort_query_prefix += "&"

    selected_ids = get_session_selection(request)
    selected_qty = _read_quantity(selected_ids, "storage") if part_type == "storage" else 1
    return {
        "title": config["title"],
        "part_type": part_type,
        "columns": columns,
        "items": queryset,
        "q": q,
        "numeric_filters": numeric_filters,
        "enum_filters": enum_filters,
        "sort_query_prefix": sort_query_prefix,
        "sort": sort,
        "dir": direction,
        "selected_id": selected_ids.get(part_type),
        "selected_qty": selected_qty,
    }
