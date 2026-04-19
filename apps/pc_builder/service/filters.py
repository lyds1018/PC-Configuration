from django.db.models import DecimalField, FloatField, IntegerField, Max, Min, Q

BRAND_FIELD_NAMES = ("brand", "chip_brand", "card_brand")
BRAND_LABEL_MAP = {
    "brand": "品牌",
    "chip_brand": "芯片品牌",
    "card_brand": "显卡品牌",
}
ENUM_FILTER_MAX_OPTIONS = 20
DEFAULT_ENUM_EXCLUDED_FIELDS = {"name", "brand", "chip_brand", "card_brand"}


def model_has_field(model, field_name):
    """检查模型是否包含指定字段"""
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def distinct_non_empty_values(queryset, field_name):
    """获取字段的所有非空唯一值"""
    return list(
        queryset.exclude(**{f"{field_name}__isnull": True})
        .exclude(**{field_name: ""})
        .values_list(field_name, flat=True)
        .distinct()
        .order_by(field_name)
    )


def parse_optional_float(raw_value):
    """解析可选的浮点数值"""
    text = (raw_value or "").strip()
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def build_sort_query_prefix(request):
    """构建排序查询参数前缀"""
    params = request.GET.copy()
    params.pop("sort", None)
    params.pop("dir", None)
    query_prefix = params.urlencode()
    if query_prefix:
        query_prefix += "&"
    return query_prefix


def normalize_sort_request(sort, direction, allowed_sort_fields):
    """规范化排序请求参数"""
    if sort not in allowed_sort_fields:
        sort = "price" if "price" in allowed_sort_fields else allowed_sort_fields[0]
    if direction not in {"asc", "desc"}:
        direction = "asc"
    return sort, direction


def apply_brand_filters(request, model, base_queryset, queryset, enum_filters):
    """应用品牌过滤器"""
    brand_fields = [
        field_name
        for field_name in BRAND_FIELD_NAMES
        if model_has_field(model, field_name)
    ]
    for field_name in brand_fields:
        values = distinct_non_empty_values(base_queryset, field_name)
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


def apply_column_filters(
    request,
    model,
    config,
    base_queryset,
    queryset,
    search_fields,
    numeric_filters,
    enum_filters,
):
    """应用列过滤器（数值范围和枚举）"""
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

            selected_min = parse_optional_float(selected_min_raw)
            selected_max = parse_optional_float(selected_max_raw)
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

        values = distinct_non_empty_values(base_queryset, field_key)
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


def apply_keyword_search(queryset, q, search_fields):
    """应用关键字搜索"""
    if not q:
        return queryset

    query = Q()
    for field in search_fields:
        query |= Q(**{f"{field}__icontains": q})
    return queryset.filter(query)
