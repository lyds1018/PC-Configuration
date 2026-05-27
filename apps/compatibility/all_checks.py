"""兼容性规则集合

本模块只负责“单条规则”的判断，每个函数输入若干配件对象，
输出该规则对应的问题列表（无问题则返回空列表）
"""

from __future__ import annotations

from typing import Any

# 数据格式规范化工具
from .utils import (
    contains_ddr,
    form_rank,
    psu_form_rank,
    read,
    to_float,
    to_int,
    to_text,
    to_upper,
)


def check_cpu_mb_socket(cpu: Any, mb: Any) -> list[str]:
    """检查 CPU 与主板的插槽接口是否一致。"""
    issues: list[str] = []
    cpu_socket = to_upper(read(cpu, "socket"))
    mb_socket = to_upper(read(mb, "socket"))

    # 如果接口数据缺失，暂时不进行兼容性判断
    if not cpu_socket or not mb_socket:
        return issues

    # 比较 CPU 插槽接口与主板插槽接口
    if cpu_socket != mb_socket:
        issues.append(f"CPU 接口 {cpu_socket} 与主板接口 {mb_socket} 不兼容。")

    return issues


def check_cpu_ram(cpu: Any, ram: Any) -> list[str]:
    """检查 CPU 与内存在类型与频率上的兼容性。"""
    issues: list[str] = []
    cpu_memory_type = read(cpu, "memory_type")
    ram_type = read(ram, "type")
    cpu_memory_speed = to_int(read(cpu, "memory_speed"))
    ram_freq = to_int(read(ram, "frequency"))

    # 如果内存类型数据缺失，暂时不进行兼容性判断
    if not cpu_memory_type or not ram_type:
        return issues

    # 检查 CPU 支持的内存类型中是否包含内存条的类型
    if not contains_ddr(cpu_memory_type, ram_type):
        issues.append(
            f"CPU 支持内存类型 {to_text(cpu_memory_type)}，不支持内存类型 {to_text(ram_type)}。"
        )

    # 如果内存频率数据缺失，暂时不进行兼容性判断
    if not cpu_memory_speed or not ram_freq:
        return issues

    # 检查 CPU 支持的内存频率是否不低于内存条的频率
    if cpu_memory_speed < ram_freq:
        issues.append(
            f"CPU 支持内存频率 {cpu_memory_speed}MHz，低于内存频率 {ram_freq}MHz。"
        )

    return issues


def check_mb_case(mb: Any, case: Any) -> list[str]:
    """检查主板板型是否可安装进机箱。"""
    issues: list[str] = []
    mb_form = read(mb, "form")
    case_form = read(case, "form")
    mb_rank = form_rank(mb_form)
    case_rank = form_rank(case_form)

    # 如果尺寸数据缺失，暂时不进行兼容性判断
    if not mb_rank or not case_rank:
        return issues

    # 比较主板版型与机箱支持的最大版型
    if mb_rank > case_rank:
        issues.append(
            f"主板尺寸 {to_text(mb_form)} 超过机箱最大尺寸 {to_text(case_form)}。"
        )

    return issues


def check_mb_ram(mb: Any, ram: Any) -> list[str]:
    """检查主板与内存的类型和频率是否匹配。"""
    issues: list[str] = []
    mb_memory_type = read(mb, "memory_type")
    ram_type = read(ram, "type")
    mb_freq = to_int(read(mb, "memory_frequency"))
    ram_freq = to_int(read(ram, "frequency"))

    # 如果内存类型数据缺失，暂时不进行兼容性判断
    if not mb_memory_type or not ram_type:
        return issues

    #  检查主板支持的内存类型中是否包含内存条的类型
    if not contains_ddr(mb_memory_type, ram_type):
        issues.append(
            f"主板支持内存类型 {to_text(mb_memory_type)}，不支持内存类型 {to_text(ram_type)}。"
        )

    # 如果内存频率数据缺失，暂时不进行兼容性判断
    if not mb_freq or not ram_freq:
        return issues

    # 检查主板支持的内存频率是否不低于内存条的频率
    if mb_freq < ram_freq:
        issues.append(f"主板支持内存频率 {mb_freq}MHz，低于内存频率 {ram_freq}MHz。")

    return issues


def check_gpu_case(gpu: Any, case: Any) -> list[str]:
    """检查显卡长度是否超过机箱显卡限长。"""
    issues: list[str] = []
    gpu_length = to_int(read(gpu, "length"))
    case_limit = to_int(read(case, "gpu_length"))

    # 如果尺寸数据缺失，暂时不进行兼容性判断
    if not gpu_length or not case_limit:
        return issues

    # 比较显卡长度与机箱显卡限长
    if gpu_length > case_limit:
        issues.append(f"显卡长度 {gpu_length}mm 超过机箱限制 {case_limit}mm。")

    return issues


def check_cooler_case(cooler: Any, case: Any) -> list[str]:
    """检查散热器与机箱在风冷限高/水冷冷排规格上的兼容性。"""
    issues: list[str] = []

    # 先根据散热器类型判断使用哪个尺寸参数进行比较
    cooler_type = to_upper(read(cooler, "type"))
    if not cooler_type:
        return issues

    # 风冷
    if cooler_type == "AIR":
        cooler_height = to_int(read(cooler, "air_height"))
        case_air_height = to_int(read(case, "air_height"))

        # 如果尺寸数据缺失，暂时不进行兼容性判断
        if not cooler_height or not case_air_height:
            return issues

        # 比较风冷高度与机箱风冷限高
        if cooler_height > case_air_height:
            issues.append(
                f"风冷高度 {cooler_height}mm 超过机箱风冷限高 {case_air_height}mm。"
            )

    # 水冷
    if cooler_type == "WATER":
        cooler_water = to_int(read(cooler, "water_size"))
        case_water = to_int(read(case, "water_size"))

        # 如果尺寸数据缺失，暂时不进行兼容性判断
        if not cooler_water or not case_water:
            return issues

        # 比较水冷排规格与机箱支持的最大冷排规格
        if cooler_water > case_water:
            issues.append(
                f"水冷排规格 {cooler_water} 超过机箱支持的最大冷排规格 {case_water}。"
            )

    return issues


def check_psu_case(psu: Any, case: Any) -> list[str]:
    """检查电源规格与机箱电源位规格是否匹配。"""
    issues: list[str] = []
    psu_form = read(psu, "form")
    case_psu_form = read(case, "psu_form")
    psu_rank = psu_form_rank(psu_form)
    case_rank = psu_form_rank(case_psu_form)

    # 如果尺寸数据缺失，暂时不进行兼容性判断
    if not psu_rank or not case_rank:
        return issues

    # 比较电源规格与机箱电源位规格
    if psu_rank > case_rank:
        issues.append(
            f"电源规格 {to_text(psu_form)} 不受机箱电源位规格 {to_text(case_psu_form)} 支持。"
        )

    return issues


def check_power(cpu: Any, gpu: Any, psu: Any) -> list[str]:
    """检查电源额定功率是否足够，参考 (CPU TDP + GPU TDP) * 1.3。"""
    issues: list[str] = []
    cpu_tdp = to_float(read(cpu, "tdp"))
    gpu_tdp = to_float(read(gpu, "tdp"))
    psu_wattage = to_float(read(psu, "wattage"))

    # 如果功率数据缺失，暂时不进行兼容性判断
    if not cpu_tdp or not gpu_tdp or not psu_wattage:
        return issues

    # 计算参考功率并与电源额定功率比较
    required = (cpu_tdp + gpu_tdp) * 1.3
    if required > psu_wattage:
        issues.append(
            f"电源额定功率 {psu_wattage:.0f}W 不足，至少需要 {required:.0f}W。"
        )

    return issues


def check_storage_totals(mb: Any, case: Any, totals: dict[str, int]) -> list[str]:
    """检查存储设备数量是否超出主板接口数与机箱硬盘位上限。"""
    issues: list[str] = []

    # M.2 接口 SSD
    total_m2 = totals.get("total_m2", 0)
    mb_m2 = to_int(read(mb, "m2_slots"))
    if mb_m2 and mb_m2 < total_m2:
        issues.append(f"主板 M.2 插槽数 {mb_m2} 少于所需 {total_m2}。")

    # SATA 接口 SSD/HDD，既要考虑主板接口数，也要考虑机箱硬盘位数
    total_sata = totals.get("total_sata", 0)
    mb_sata = to_int(read(mb, "sata_ports"))
    if mb_sata and mb_sata < total_sata:
        issues.append(f"主板 SATA 接口数 {mb_sata} 少于所需 {total_sata}。")

    # 2.5 英寸 SSD 硬盘位
    total_sata_ssd = totals.get("total_sata_ssd", 0)
    case_2_5 = to_int(read(case, "storage_2_5"))
    if case_2_5 and case_2_5 < total_sata_ssd:
        issues.append(f"机箱 2.5 英寸位 {case_2_5} 少于所需 {total_sata_ssd}。")

    # 3.5 英寸 HDD 硬盘位
    total_hdd = totals.get("total_hdd", 0)
    case_3_5 = to_int(read(case, "storage_3_5"))
    if case_3_5 and case_3_5 < total_hdd:
        issues.append(f"机箱 3.5 英寸位 {case_3_5} 少于所需 {total_hdd}。")

    return issues


def check_totals(mb: Any, totals: dict[str, int]) -> list[str]:
    """检查主板内存插槽是否满足当前内存条总数量。"""
    issues: list[str] = []

    total_memory = totals.get("total_memory", 0)
    mb_slots = to_int(read(mb, "memory_slots"))

    # 如果内存插槽数据缺失，暂时不进行兼容性判断
    if not mb_slots or not total_memory:
        return issues

    # 比较主板内存插槽数与内存条总数量
    if mb_slots < total_memory:
        issues.append(f"主板内存插槽数 {mb_slots} 少于所需 {total_memory}。")

    return issues
