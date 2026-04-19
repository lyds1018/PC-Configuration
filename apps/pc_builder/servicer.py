from .catalog import (
    BUILD_CATEGORIES,
    COMPATIBILITY_REQUIRED_KEYS,
    PARTS_CONFIG,
)
from .service import (
    apply_brand_filters,
    apply_column_filters,
    apply_keyword_search,
    as_int,
    build_sort_query_prefix,
    check_compatibility,
    estimate_wattage,
    get_session_selection,
    normalize_sort_request,
    read_quantity,
    resolve_selected_parts,
    save_session_selection,
)


def build_builder_context(request):
    """
    整合用户已选配件、兼容性检查结果、价格估算等信息，
    用于渲染装机主页面

    返回:
        dict: 包含以下键的上下文字典
            categories: 配件分类列表
            selected: 已选配件对象字典
            storage_qty: 存储设备数量
            storage_line_price: 存储设备总价
            total_price: 所有配件总价
            compatibility: 兼容性检查结果
            can_check: 是否满足兼容性检查条件
            estimated_wattage: 估算功耗
    """
    # 从 session 获取用户选择并解析为配件对象
    selected_ids = get_session_selection(request)
    selected, total_price = resolve_selected_parts(selected_ids)

    # 检查是否包含所有必需配件以进行兼容性检查
    can_check = all(selected.get(key) for key in COMPATIBILITY_REQUIRED_KEYS)
    compatibility = check_compatibility(selected, selected_ids, can_check)

    # 计算存储设备的数量和价格
    storage_qty = (
        read_quantity(selected_ids, "storage") if selected.get("storage") else 0
    )
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
    """
    验证配件 ID 有效性后，将配件选择保存到用户 session 中
    对于存储设备，还会记录用户选择的数量

    返回:
        bool: 选择成功返回 True，配件类型无效返回 False
    """
    from django.shortcuts import get_object_or_404

    # 验证配件类型是否有效
    config = PARTS_CONFIG.get(part_type)
    if not config:
        return False

    # 验证配件 ID 是否存在（如果不存在会抛出 404）
    model = config["model"]
    get_object_or_404(model, id=pk)

    # 保存配件选择到 session
    selected = get_session_selection(request)
    selected[part_type] = pk

    # 存储设备需要额外记录数量
    if part_type == "storage":
        qty = as_int(request.POST.get("qty") or request.GET.get("qty"), default=1)
        selected["storage_qty"] = max(1, qty)

    save_session_selection(request, selected)
    return True


def build_part_list_context(request, part_type):
    """
    构建配件列表页面的上下文数据

    根据配件类型获取对应的配件列表，应用用户提交的筛选条件
    （品牌、数值范围、关键字搜索等），并处理排序逻辑
    """
    # 获取配件类型配置
    config = PARTS_CONFIG.get(part_type)
    if not config:
        return {"invalid": True, "title": "配件"}

    # 解析请求参数：搜索关键字、排序字段、排序方向
    q = (request.GET.get("q") or "").strip()
    sort = (request.GET.get("sort") or "price").strip()
    direction = (request.GET.get("dir") or "asc").strip().lower()

    # 构建列配置并规范化排序参数
    columns = [{"key": key, "label": label} for key, label in config["columns"]]
    allowed_sort_fields = [col["key"] for col in columns]
    sort, direction = normalize_sort_request(sort, direction, allowed_sort_fields)

    # 获取基础查询集
    model = config["model"]
    base_queryset = model.objects.all()
    queryset = base_queryset
    search_fields = config.get("search_fields") or ["name"]

    # 应用各类筛选器
    numeric_filters = []
    enum_filters = []
    queryset = apply_brand_filters(
        request, model, base_queryset, queryset, enum_filters
    )
    queryset = apply_column_filters(
        request,
        model,
        config,
        base_queryset,
        queryset,
        search_fields,
        numeric_filters,
        enum_filters,
    )
    queryset = apply_keyword_search(queryset, q, search_fields)

    # 应用排序
    order_by = f"-{sort}" if direction == "desc" else sort
    queryset = queryset.order_by(order_by)

    # 构建排序 URL 前缀
    sort_query_prefix = build_sort_query_prefix(request)

    # 获取用户已选配件信息
    selected_ids = get_session_selection(request)
    selected_qty = (
        read_quantity(selected_ids, "storage") if part_type == "storage" else 1
    )

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
