"""装机页兼容性服务

1. 从已选配件抽取兼容性相关字段；
2. 计算存储/内存数量统计；
3. 调用 compatibility 模块并返回统一检查结果
"""

from compatibility import run_checks

from .utils import COMPATIBILITY_FIELD_MAP, read_quantity, to_int


def extract_part_payload(part, field_names):
    """按字段名单抽取配件属性，避免把无关数据传入检查器。"""
    return {field_name: getattr(part, field_name) for field_name in field_names}


def derive_storage_totals(selected, selected_ids):
    """根据存储类型与数量推导数量（M.2 / SATA / HDD / SATA SSD）。"""
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
    """将已选配件对象转为兼容性检查模块输入格式。"""

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
        payload["totals"]["total_memory"] = to_int(
            getattr(selected["ram"], "module_count", 1), default=1
        )

    if selected.get("storage"):
        qty = read_quantity(selected_ids, "storage")
        payload["storages"] += [{"type": selected["storage"].type}] * qty

    payload["totals"].update(derive_storage_totals(selected, selected_ids))
    return payload


def check_compatibility(selected, selected_ids, can_check):
    """根据前置条件决定是否执行兼容性检查。"""
    if not can_check:
        return {"ok": True, "issues": []}

    return run_checks(build_compatibility_payload(selected, selected_ids))


def estimate_wattage(selected):
    """估算核心平台功耗，供页面展示。"""
    if not selected.get("cpu") or not selected.get("gpu"):
        return None

    cpu_tdp = float(selected["cpu"].tdp or 0)
    gpu_tdp = float(selected["gpu"].tdp or 0)

    tdp = to_int((cpu_tdp + gpu_tdp) * 1.3)

    return tdp

