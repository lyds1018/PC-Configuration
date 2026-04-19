from .catalog import BUILD_CATEGORIES, PARTS_CONFIG
from .utils import read_quantity


def resolve_selected_parts(selected_ids):
    """解析选中的配件对象并计算总价"""
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
        qty = read_quantity(selected_ids, key) if key == "storage" else 1
        total_price += float(getattr(obj, "price", 0) or 0) * qty

    return selected, total_price
