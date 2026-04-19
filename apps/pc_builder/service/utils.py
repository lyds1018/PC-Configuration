def as_int(value, default=0):
    """安全转换为整数"""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def read_quantity(selected_ids, key, default=1):
    """读取配件数量"""
    qty_key = f"{key}_qty"
    qty = as_int(selected_ids.get(qty_key), default=default)
    return max(1, qty)
