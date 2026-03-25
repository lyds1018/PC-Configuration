from __future__ import annotations

import json
import re
from typing import Any, Dict, List

FORM_ORDER = {"ITX": 1, "MATX": 2, "M-ATX": 2, "MICROATX": 2, "MICRO ATX": 2, "ATX": 3}
PSU_FORM_ORDER = {"SFX": 1, "ATX": 2}
DDR_RE = re.compile(r"DDR\s*(\d+)", re.IGNORECASE)


def _read(source: Any, *fields: str) -> Any:
    if source is None:
        return None
    for field in fields:
        if isinstance(source, dict) and field in source:
            return source[field]
        if hasattr(source, field):
            return getattr(source, field)
    return None


def _to_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _to_upper(value: Any) -> str:
    return _to_text(value).upper()


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    num = _to_float(value)
    return int(num) if num is not None else None


def _parse_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [_to_upper(v) for v in value if _to_text(v)]

    text = _to_text(value)
    if not text:
        return []

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [_to_upper(v) for v in parsed if _to_text(v)]
    except (TypeError, ValueError, json.JSONDecodeError):
        pass

    text = text.strip("[]")
    parts = re.split(r"[,/|\\]+", text)
    normalized = []
    for part in parts:
        cleaned = part.strip().strip("\"'")
        if cleaned:
            normalized.append(cleaned.upper())
    return normalized


def _ddr_rank(value: Any) -> int | None:
    text = _to_upper(value)
    if not text:
        return None
    match = DDR_RE.search(text)
    if match:
        return int(match.group(1))
    return None


def _max_ddr_rank(value: Any) -> int | None:
    values = _parse_list(value)
    if not values:
        return _ddr_rank(value)

    ranks = [rank for rank in (_ddr_rank(v) for v in values) if rank is not None]
    return max(ranks) if ranks else None


def _contains_ddr(supported: Any, target: Any) -> bool:
    target_upper = _to_upper(target)
    if not target_upper:
        return True

    supported_list = _parse_list(supported)
    if supported_list:
        return target_upper in supported_list

    return _to_upper(supported) == target_upper


def _form_rank(value: Any) -> int | None:
    key = _to_upper(value).replace("_", "").replace("-", "-")
    return FORM_ORDER.get(key)


def _psu_form_rank(value: Any) -> int | None:
    return PSU_FORM_ORDER.get(_to_upper(value))


def _max_radiator(value: Any) -> int | None:
    sizes = []
    for entry in _parse_list(value):
        number = _to_int(re.sub(r"[^0-9]", "", entry))
        if number is not None:
            sizes.append(number)
    return max(sizes) if sizes else None


def _check_cpu_mb_socket(cpu: Any, mb: Any) -> list[str]:
    cpu_socket = _to_upper(_read(cpu, "socket"))
    mb_socket = _to_upper(_read(mb, "socket"))
    if not cpu_socket or not mb_socket:
        return []
    if cpu_socket != mb_socket:
        return [f"CPU 接口 {cpu_socket} 与主板接口 {mb_socket} 不兼容。"]
    return []


def _check_cpu_ram(cpu: Any, ram: Any) -> list[str]:
    issues: list[str] = []

    cpu_memory_type = _read(cpu, "memory_type")
    ram_type = _read(ram, "type")
    if ram_type and cpu_memory_type and not _contains_ddr(cpu_memory_type, ram_type):
        issues.append(f"CPU 支持内存类型 {_to_text(cpu_memory_type)}，不支持内存类型 {_to_text(ram_type)}。")

    cpu_memory_speed = _to_int(_read(cpu, "memory_speed"))
    ram_freq = _to_int(_read(ram, "frequency"))
    if cpu_memory_speed is not None and ram_freq is not None and cpu_memory_speed < ram_freq:
        issues.append(f"CPU 支持内存频率 {cpu_memory_speed}MHz，低于内存频率 {ram_freq}MHz。")

    return issues


def _check_mb_case(mb: Any, case: Any) -> list[str]:
    mb_form = _read(mb, "form")
    case_form = _read(case, "form", "mb_form")
    mb_rank = _form_rank(mb_form)
    case_rank = _form_rank(case_form)
    if mb_rank is None or case_rank is None:
        return []
    if mb_rank > case_rank:
        return [f"主板尺寸 {_to_text(mb_form)} 不能安装进机箱尺寸 {_to_text(case_form)}。"]
    return []


def _check_mb_ram(mb: Any, ram: Any) -> list[str]:
    issues: list[str] = []

    mb_memory_type = _read(mb, "memory_type")
    ram_type = _read(ram, "type")
    if mb_memory_type and ram_type and not _contains_ddr(mb_memory_type, ram_type):
        issues.append(f"主板支持内存类型 {_to_text(mb_memory_type)}，不支持内存类型 {_to_text(ram_type)}。")

    mb_freq = _to_int(_read(mb, "memory_frequency"))
    ram_freq = _to_int(_read(ram, "frequency"))
    if mb_freq is not None and ram_freq is not None and mb_freq < ram_freq:
        issues.append(f"主板支持内存频率 {mb_freq}MHz，低于内存频率 {ram_freq}MHz。")

    return issues


def _check_gpu_case(gpu: Any, case: Any) -> list[str]:
    gpu_length = _to_int(_read(gpu, "length"))
    case_limit = _to_int(_read(case, "gpu_length"))
    if gpu_length is None or case_limit is None:
        return []
    if gpu_length > case_limit:
        return [f"显卡长度 {gpu_length}mm 超过机箱限制 {case_limit}mm。"]
    return []


def _check_cooler_case(cooler: Any, case: Any) -> list[str]:
    cooler_type = _to_upper(_read(cooler, "type", "cooler_type"))
    if not cooler_type:
        return []

    issues: list[str] = []

    if cooler_type == "AIR":
        cooler_height = _to_int(_read(cooler, "air_height", "height", "size"))
        case_air_height = _to_int(_read(case, "air_height"))
        if cooler_height is not None and case_air_height is not None and cooler_height > case_air_height:
            issues.append(f"风冷高度 {cooler_height}mm 超过机箱风冷限高 {case_air_height}mm。")

    if cooler_type == "WATER":
        cooler_water = _max_radiator(_read(cooler, "water_size", "watersize"))
        case_water = _max_radiator(_read(case, "water_size", "watersize"))
        if cooler_water is not None and case_water is not None and cooler_water > case_water:
            issues.append(f"水冷排规格 {cooler_water} 超过机箱支持的最大冷排规格 {case_water}。")

    return issues


def _check_psu_case(psu: Any, case: Any) -> list[str]:
    psu_form = _read(psu, "form", "type")
    case_psu_form = _read(case, "psu_form")
    psu_rank = _psu_form_rank(psu_form)
    case_rank = _psu_form_rank(case_psu_form)
    if psu_rank is None or case_rank is None:
        return []
    if psu_rank > case_rank:
        return [f"电源规格 {_to_text(psu_form)} 不受机箱电源位规格 {_to_text(case_psu_form)} 支持。"]
    return []


def _check_power(cpu: Any, gpu: Any, psu: Any) -> list[str]:
    cpu_tdp = _to_float(_read(cpu, "tdp"))
    gpu_tdp = _to_float(_read(gpu, "tdp"))
    psu_wattage = _to_float(_read(psu, "wattage"))
    if cpu_tdp is None or gpu_tdp is None or psu_wattage is None:
        return []

    required = (cpu_tdp + gpu_tdp) * 1.3
    if required > psu_wattage:
        return [f"电源额定功率 {psu_wattage:.0f}W 不足，至少需要 {required:.0f}W。"]
    return []


def _check_storage_totals(mb: Any, case: Any, totals: dict[str, int]) -> list[str]:
    issues: list[str] = []

    total_m2 = totals.get("total_m2", 0)
    mb_m2 = _to_int(_read(mb, "m2_slots"))
    if mb_m2 is not None and mb_m2 < total_m2:
        issues.append(f"主板 M.2 插槽数 {mb_m2} 少于所需 {total_m2}。")

    total_sata = totals.get("total_sata", 0)
    mb_sata = _to_int(_read(mb, "sata_ports"))
    if mb_sata is not None and mb_sata < total_sata:
        issues.append(f"主板 SATA 接口数 {mb_sata} 少于所需 {total_sata}。")

    total_sata_ssd = totals.get("total_sata_ssd", 0)
    case_2_5 = _to_int(_read(case, "storage_2_5"))
    if case_2_5 is not None and case_2_5 < total_sata_ssd:
        issues.append(f"机箱 2.5 英寸位 {case_2_5} 少于所需 {total_sata_ssd}。")

    total_hdd = totals.get("total_hdd", 0)
    case_3_5 = _to_int(_read(case, "storage_3_5"))
    if case_3_5 is not None and case_3_5 < total_hdd:
        issues.append(f"机箱 3.5 英寸位 {case_3_5} 少于所需 {total_hdd}。")

    return issues


def _check_totals(mb: Any, totals: dict[str, int]) -> list[str]:
    issues: list[str] = []

    total_memory = totals.get("total_memory", 0)
    mb_slots = _to_int(_read(mb, "memory_slots"))
    if mb_slots is not None and mb_slots < total_memory:
        issues.append(f"主板内存插槽数 {mb_slots} 少于所需 {total_memory}。")

    return issues


def _derive_storage_totals(parts: Dict[str, Any]) -> dict[str, int]:
    if "totals" in parts and isinstance(parts["totals"], dict):
        values = parts["totals"]
        return {
            "total_m2": int(values.get("total_m2", 0) or 0),
            "total_sata": int(values.get("total_sata", 0) or 0),
            "total_sata_ssd": int(values.get("total_sata_ssd", 0) or 0),
            "total_hdd": int(values.get("total_hdd", 0) or 0),
            "total_memory": int(values.get("total_memory", 0) or 0),
        }

    total_m2 = total_sata = total_sata_ssd = total_hdd = 0
    for storage in parts.get("storages", []):
        storage_type = _to_upper(_read(storage, "type"))
        if "M.2" in storage_type:
            total_m2 += 1
        else:
            total_sata += 1
            if "HDD" in storage_type:
                total_hdd += 1
            elif "SATA SSD" in storage_type:
                total_sata_ssd += 1

    return {
        "total_m2": total_m2,
        "total_sata": total_sata,
        "total_sata_ssd": total_sata_ssd,
        "total_hdd": total_hdd,
        "total_memory": int(parts.get("total_memory", 0) or 0),
    }


def run_pc_builder_checks(parts: Dict[str, Any]) -> Dict[str, Any]:
    cpu = parts.get("cpu", {})
    mb = parts.get("mb", {})
    ram = parts.get("ram", {})
    gpu = parts.get("gpu", {})
    case = parts.get("case", {})
    psu = parts.get("psu", {})
    cooler = parts.get("cooler", {})

    totals = _derive_storage_totals(parts)

    issues: List[str] = []
    issues += _check_cpu_mb_socket(cpu, mb)
    issues += _check_cpu_ram(cpu, ram)
    issues += _check_mb_case(mb, case)
    issues += _check_mb_ram(mb, ram)
    issues += _check_gpu_case(gpu, case)
    issues += _check_cooler_case(cooler, case)
    issues += _check_psu_case(psu, case)
    issues += _check_power(cpu, gpu, psu)
    issues += _check_storage_totals(mb, case, totals)
    issues += _check_totals(mb, totals)

    return {"ok": len(issues) == 0, "issues": issues}
