from compatibility import run_checks

from .utils import as_int, read_quantity

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


def default_compatibility():
    """返回默认兼容性结果"""
    return {"ok": True, "issues": []}


def extract_part_payload(part, field_names):
    """提取配件的兼容性相关字段"""
    return {field_name: getattr(part, field_name) for field_name in field_names}


def derive_storage_totals(selected, selected_ids):
    """推导存储设备总数"""
    storage = selected.get("storage")
    totals = {
        "total_m2": 0,
        "total_sata": 0,
        "total_sata_ssd": 0,
        "total_hdd": 0,
    }

    if not storage:
        return totals

    qty = read_quantity(selected_ids, "storage")
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
    """构建兼容性检查的payload"""

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
        payload[key] = extract_part_payload(part, field_names)

    if selected.get("ram"):
        payload["totals"]["total_memory"] = as_int(
            getattr(selected["ram"], "module_count", 1), default=1
        )

    if selected.get("storage"):
        qty = read_quantity(selected_ids, "storage")
        payload["storages"] += [{"type": selected["storage"].type}] * qty

    payload["totals"].update(derive_storage_totals(selected, selected_ids))
    return payload


def estimate_wattage(selected):
    """估算功耗（CPU TDP + GPU TDP）"""
    if not selected.get("cpu") or not selected.get("gpu"):
        return None

    cpu_tdp = float(selected["cpu"].tdp or 0)
    gpu_tdp = float(selected["gpu"].tdp or 0)
    return cpu_tdp + gpu_tdp


def check_compatibility(selected, selected_ids, can_check):
    """执行兼容性检查"""
    if not can_check:
        return default_compatibility()

    return run_checks(build_compatibility_payload(selected, selected_ids))
