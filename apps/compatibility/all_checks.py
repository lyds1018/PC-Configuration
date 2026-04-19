from __future__ import annotations

from typing import Any

# 引入工具函数
from .utils import (
    contains_ddr,
    form_rank,
    max_radiator,
    psu_form_rank,
    read,
    to_float,
    to_int,
    to_text,
    to_upper,
)


def check_cpu_mb_socket(cpu: Any, mb: Any) -> list[str]:
    """检查 CPU 接口与主板接口是否匹配"""
    cpu_socket = to_upper(read(cpu, "socket"))
    mb_socket = to_upper(read(mb, "socket"))
    if not cpu_socket or not mb_socket:
        return []
    if cpu_socket != mb_socket:
        return [f"CPU 接口 {cpu_socket} 与主板接口 {mb_socket} 不兼容。"]
    return []


def check_cpu_ram(cpu: Any, ram: Any) -> list[str]:
    """检查 CPU 与内存兼容性（类型和频率）"""
    issues: list[str] = []

    cpu_memory_type = read(cpu, "memory_type")
    ram_type = read(ram, "type")
    if ram_type and cpu_memory_type and not contains_ddr(cpu_memory_type, ram_type):
        issues.append(
            f"CPU 支持内存类型 {to_text(cpu_memory_type)}，不支持内存类型 {to_text(ram_type)}。"
        )

    cpu_memory_speed = to_int(read(cpu, "memory_speed"))
    ram_freq = to_int(read(ram, "frequency"))
    if (
        cpu_memory_speed is not None
        and ram_freq is not None
        and cpu_memory_speed < ram_freq
    ):
        issues.append(
            f"CPU 支持内存频率 {cpu_memory_speed}MHz，低于内存频率 {ram_freq}MHz。"
        )

    return issues


def check_mb_case(mb: Any, case: Any) -> list[str]:
    """检查主板板型与机箱是否兼容"""
    mb_form = read(mb, "form")
    case_form = read(case, "form", "mb_form")
    mb_rank = form_rank(mb_form)
    case_rank = form_rank(case_form)
    if mb_rank is None or case_rank is None:
        return []
    if mb_rank > case_rank:
        return [
            f"主板尺寸 {to_text(mb_form)} 不能安装进机箱尺寸 {to_text(case_form)}。"
        ]
    return []


def check_mb_ram(mb: Any, ram: Any) -> list[str]:
    """检查主板与内存兼容性"""
    issues: list[str] = []

    mb_memory_type = read(mb, "memory_type")
    ram_type = read(ram, "type")
    if mb_memory_type and ram_type and not contains_ddr(mb_memory_type, ram_type):
        issues.append(
            f"主板支持内存类型 {to_text(mb_memory_type)}，不支持内存类型 {to_text(ram_type)}。"
        )

    mb_freq = to_int(read(mb, "memory_frequency"))
    ram_freq = to_int(read(ram, "frequency"))
    if mb_freq is not None and ram_freq is not None and mb_freq < ram_freq:
        issues.append(f"主板支持内存频率 {mb_freq}MHz，低于内存频率 {ram_freq}MHz。")

    return issues


def check_gpu_case(gpu: Any, case: Any) -> list[str]:
    """检查显卡长度是否超过机箱限制"""
    gpu_length = to_int(read(gpu, "length"))
    case_limit = to_int(read(case, "gpu_length"))
    if gpu_length is None or case_limit is None:
        return []
    if gpu_length > case_limit:
        return [f"显卡长度 {gpu_length}mm 超过机箱限制 {case_limit}mm。"]
    return []


def check_cooler_case(cooler: Any, case: Any) -> list[str]:
    """检查散热器与机箱兼容性（风冷高度/水冷规格）"""
    cooler_type = to_upper(read(cooler, "type", "cooler_type"))
    if not cooler_type:
        return []

    issues: list[str] = []

    if cooler_type == "AIR":
        cooler_height = to_int(read(cooler, "air_height", "height", "size"))
        case_air_height = to_int(read(case, "air_height"))
        if (
            cooler_height is not None
            and case_air_height is not None
            and cooler_height > case_air_height
        ):
            issues.append(
                f"风冷高度 {cooler_height}mm 超过机箱风冷限高 {case_air_height}mm。"
            )

    if cooler_type == "WATER":
        cooler_water = max_radiator(read(cooler, "water_size", "watersize"))
        case_water = max_radiator(read(case, "water_size", "watersize"))
        if (
            cooler_water is not None
            and case_water is not None
            and cooler_water > case_water
        ):
            issues.append(
                f"水冷排规格 {cooler_water} 超过机箱支持的最大冷排规格 {case_water}。"
            )

    return issues


def check_psu_case(psu: Any, case: Any) -> list[str]:
    """检查电源规格与机箱电源位是否兼容"""
    psu_form = read(psu, "form", "type")
    case_psu_form = read(case, "psu_form")
    psu_rank = psu_form_rank(psu_form)
    case_rank = psu_form_rank(case_psu_form)
    if psu_rank is None or case_rank is None:
        return []
    if psu_rank > case_rank:
        return [
            f"电源规格 {to_text(psu_form)} 不受机箱电源位规格 {to_text(case_psu_form)} 支持。"
        ]
    return []


def check_power(cpu: Any, gpu: Any, psu: Any) -> list[str]:
    """检查电源功率是否足够（CPU TDP + GPU TDP）* 1.3"""
    cpu_tdp = to_float(read(cpu, "tdp"))
    gpu_tdp = to_float(read(gpu, "tdp"))
    psu_wattage = to_float(read(psu, "wattage"))
    if cpu_tdp is None or gpu_tdp is None or psu_wattage is None:
        return []

    required = (cpu_tdp + gpu_tdp) * 1.3
    if required > psu_wattage:
        return [f"电源额定功率 {psu_wattage:.0f}W 不足，至少需要 {required:.0f}W。"]
    return []


def check_storage_totals(mb: Any, case: Any, totals: dict[str, int]) -> list[str]:
    """检查存储设备数量是否超过主板和机箱限制"""
    issues: list[str] = []

    total_m2 = totals.get("total_m2", 0)
    mb_m2 = to_int(read(mb, "m2_slots"))
    if mb_m2 is not None and mb_m2 < total_m2:
        issues.append(f"主板 M.2 插槽数 {mb_m2} 少于所需 {total_m2}。")

    total_sata = totals.get("total_sata", 0)
    mb_sata = to_int(read(mb, "sata_ports"))
    if mb_sata is not None and mb_sata < total_sata:
        issues.append(f"主板 SATA 接口数 {mb_sata} 少于所需 {total_sata}。")

    total_sata_ssd = totals.get("total_sata_ssd", 0)
    case_2_5 = to_int(read(case, "storage_2_5"))
    if case_2_5 is not None and case_2_5 < total_sata_ssd:
        issues.append(f"机箱 2.5 英寸位 {case_2_5} 少于所需 {total_sata_ssd}。")

    total_hdd = totals.get("total_hdd", 0)
    case_3_5 = to_int(read(case, "storage_3_5"))
    if case_3_5 is not None and case_3_5 < total_hdd:
        issues.append(f"机箱 3.5 英寸位 {case_3_5} 少于所需 {total_hdd}。")

    return issues


def check_totals(mb: Any, totals: dict[str, int]) -> list[str]:
    """检查内存插槽数量是否足够"""
    issues: list[str] = []

    total_memory = totals.get("total_memory", 0)
    mb_slots = to_int(read(mb, "memory_slots"))
    if mb_slots is not None and mb_slots < total_memory:
        issues.append(f"主板内存插槽数 {mb_slots} 少于所需 {total_memory}。")

    return issues
