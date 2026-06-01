"""装机模块服务层

负责处理页面上下文、配件列表构建及筛选、配件选择、兼容性检查
"""

from django.shortcuts import get_object_or_404

from .catalog import (
    BUILD_CATEGORIES,
    PARTS_CONFIG,
)
from .service import (
    to_int,
    read_quantity,
    resolve_selected_parts,
    apply_brand_filters,
    apply_column_filters,
    apply_keyword_search,
    normalize_sort_request,
    build_sort_query_prefix,
    estimate_wattage,
    check_compatibility,
    get_session_selection,
    save_session_selection,
)


def build_builder_context(request):
    """DIY 装机主页上下文处理器，选取配件刷新后返回上下文字典。"""

    # 从 session 获取用户选择的配件
    selected_ids = get_session_selection(request)
    selected, total_price = resolve_selected_parts(selected_ids)

    # 进行兼容性检查
    can_check = len(selected) >= 2
    compatibility = check_compatibility(selected, selected_ids, can_check)

    # 读取存储设备的数量，计算总价
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
    """配件选择处理逻辑。"""

    # 验证所选配件 ID 是否存在
    config = PARTS_CONFIG.get(part_type)
    model = config["model"]
    get_object_or_404(model, id=pk)

    # 取出 session 并更新至对应配件类型
    selected = get_session_selection(request)
    selected[part_type] = pk

    # 存储设备需要额外更新数量
    if part_type == "storage":
        qty = to_int(request.POST.get("qty") or request.GET.get("qty"), default=1)
        selected["storage_qty"] = max(1, qty)

    # 保存更新后的 session
    save_session_selection(request, selected)

    return True


def build_part_list_context(request, part_type):
    """
    构建配件列表页面的上下文处理器。

    根据配件类型获取对应的配件列表，处理用户提交的筛选/搜索/排序请求。
    """

    # 获取配置的列表字段
    config = PARTS_CONFIG.get(part_type)

    # 解析请求参数：搜索关键字、排序字段、排序方向
    q = (request.GET.get("q") or "").strip()
    sort = (request.GET.get("sort") or "price").strip()
    direction = (request.GET.get("dir") or "asc").strip().lower()

    # 构建对应字段组成的列表
    columns = [{"key": key, "label": label} for key, label in config["columns"]]

    # 规范排序参数
    allowed_sort_fields = [col["key"] for col in columns]
    sort, direction = normalize_sort_request(sort, direction, allowed_sort_fields)

    # 获取数据全集
    model = config["model"]
    base_queryset = model.objects.all()
    queryset = base_queryset

    # 获取配置的筛选字段
    search_fields = config.get("search_fields") or ["name"]

    # 应用各类筛选器
    numeric_filters = []
    enum_filters = []

    # 品牌筛选
    queryset = apply_brand_filters(
        request, model, base_queryset, queryset, enum_filters
    )

    # 字段筛选（数值/类型）
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

    # 关键字搜索
    queryset = apply_keyword_search(queryset, q, search_fields)

    # 排序
    order_by = f"-{sort}" if direction == "desc" else sort
    queryset = queryset.order_by(order_by)

    # 构建排序 URL 前缀，即记录当前筛选条件，供后续追加筛选
    sort_query_prefix = build_sort_query_prefix(request)

    # 获取已选存储设备数量，供存储设备列表页面渲染
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
