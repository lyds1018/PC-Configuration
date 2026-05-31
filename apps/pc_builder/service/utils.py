# 兼容性检查字段
COMPATIBILITY_FIELD_MAP = {
    "cpu": ("socket", "memory_type", "memory_speed", "tdp"),
    "mb": (
        "socket",
        "form",
        "memory_type",
        "memory_frequency",
        "memory_slots",
        "m2_slots",
        "sata_ports",
    ),
    "ram": ("type", "frequency"),
    "cooler": ("type", "air_height", "water_size"),
    "gpu": ("length", "tdp"),
    "case": (
        "form",
        "gpu_length",
        "air_height",
        "water_size",
        "psu_form",
        "storage_2_5",
        "storage_3_5",
    ),
    "psu": ("form", "wattage"),
}


def to_int(value, default=0):
    """转整数，失败返回0。"""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def read_quantity(selected_ids, key, default=1):
    """读取配件数量"""
    qty_key = f"{key}_qty"
    qty = to_int(selected_ids.get(qty_key), default=default)
    return max(1, qty)
