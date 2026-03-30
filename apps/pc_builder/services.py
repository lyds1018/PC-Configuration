from django.db.models import DecimalField, FloatField, IntegerField, Max, Min, Q
from django.shortcuts import get_object_or_404

from .catalog import (
    BUILD_CATEGORIES,
    COMPATIBILITY_REQUIRED_KEYS,
    PARTS_CONFIG,
    SELECTION_SESSION_KEY,
)
from .compatibility import run_checks

BRAND_FIELD_NAMES = ("brand", "chip_brand", "card_brand")
BRAND_LABEL_MAP = {
    "brand": "品牌",
    "chip_brand": "芯片品牌",
    "card_brand": "显卡品牌",
}
ENUM_FILTER_MAX_OPTIONS = 20
DEFAULT_ENUM_EXCLUDED_FIELDS = {"name", "brand", "chip_brand", "card_brand"}
COMPATIBILITY_FIELD_MAP = {
    "cpu": ("socket", "memory_type", "memory_speed", "tdp"),
    "mb": ("socket", "form", "memory_type", "memory_frequency", "memory_slots", "m2_slots", "sata_ports"),
    "ram": ("type", "frequency"),
    "cooler": ("type", "air_height", "water_size"),
    "gpu": ("length", "tdp"),
    "case": ("form", "gpu_length", "air_height", "water_size", "psu_form", "storage_2_5", "storage_3_5"),
    "psu": ("form", "wattage"),
}


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


def _model_has_field(model, field_name):
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def _distinct_non_empty_values(queryset, field_name):
    return list(
        queryset.exclude(**{f"{field_name}__isnull": True})
        .exclude(**{field_name: ""})
        .values_list(field_name, flat=True)
        .distinct()
        .order_by(field_name)
    )


def _parse_optional_float(raw_value):
    text = (raw_value or "").strip()
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _build_sort_query_prefix(request):
    params = request.GET.copy()
    params.pop("sort", None)
    params.pop("dir", None)
    query_prefix = params.urlencode()
    if query_prefix:
        query_prefix += "&"
    return query_prefix


def _extract_part_payload(part, field_names):
    return {field_name: getattr(part, field_name) for field_name in field_names}


def _normalize_sort_request(sort, direction, allowed_sort_fields):
    if sort not in allowed_sort_fields:
        sort = "price" if "price" in allowed_sort_fields else allowed_sort_fields[0]
    if direction not in {"asc", "desc"}:
        direction = "asc"
    return sort, direction


def _apply_brand_filters(request, model, base_queryset, queryset, enum_filters):
    brand_fields = [field_name for field_name in BRAND_FIELD_NAMES if _model_has_field(model, field_name)]
    for field_name in brand_fields:
        values = _distinct_non_empty_values(base_queryset, field_name)
        if not values:
            continue

        selected_values = request.GET.getlist(field_name)
        if selected_values:
            queryset = queryset.filter(**{f"{field_name}__in": selected_values})
        enum_filters.append(
            {
                "field": field_name,
                "label": BRAND_LABEL_MAP.get(field_name, "品牌"),
                "options": values,
                "selected": selected_values,
            }
        )
    return queryset


def _apply_column_filters(request, model, config, base_queryset, queryset, search_fields, numeric_filters, enum_filters):
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

            selected_min = _parse_optional_float(selected_min_raw)
            selected_max = _parse_optional_float(selected_max_raw)
            if selected_min is not None:
                queryset = queryset.filter(**{f"{field_key}__gte": selected_min})
            if selected_max is not None:
                queryset = queryset.filter(**{f"{field_key}__lte": selected_max})

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
            continue

        if field_key not in search_fields or field_key in DEFAULT_ENUM_EXCLUDED_FIELDS:
            continue

        values = _distinct_non_empty_values(base_queryset, field_key)
        if not values or len(values) > ENUM_FILTER_MAX_OPTIONS:
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
    return queryset


def _apply_keyword_search(queryset, q, search_fields):
    if not q:
        return queryset

    query = Q()
    for field in search_fields:
        query |= Q(**{f"{field}__icontains": q})
    return queryset.filter(query)


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

    for key, field_names in COMPATIBILITY_FIELD_MAP.items():
        part = selected.get(key)
        if not part:
            continue
        payload[key] = _extract_part_payload(part, field_names)

    if selected.get("ram"):
        payload["totals"]["total_memory"] = _as_int(getattr(selected["ram"], "module_count", 1), default=1)

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
    sort, direction = _normalize_sort_request(sort, direction, allowed_sort_fields)

    model = config["model"]
    base_queryset = model.objects.all()
    queryset = base_queryset
    search_fields = config.get("search_fields") or ["name"]

    numeric_filters = []
    enum_filters = []
    queryset = _apply_brand_filters(request, model, base_queryset, queryset, enum_filters)
    queryset = _apply_column_filters(
        request,
        model,
        config,
        base_queryset,
        queryset,
        search_fields,
        numeric_filters,
        enum_filters,
    )
    queryset = _apply_keyword_search(queryset, q, search_fields)

    order_by = f"-{sort}" if direction == "desc" else sort
    queryset = queryset.order_by(order_by)

    sort_query_prefix = _build_sort_query_prefix(request)

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
