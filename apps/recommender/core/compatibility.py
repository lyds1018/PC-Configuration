"""
兼容性检查（清晰版）

假设输入数据完整可靠，不做字段推断与兼容旧数据的兜底。
"""

from typing import Dict, List


def _cpu_mb_socket(cpu, mb) -> List[str]:
    issues = []
    cpu_socket = str(cpu.socket).upper()
    mb_socket = str(mb.socket).upper()
    if cpu_socket not in mb_socket:
        issues.append(f"CPU插槽 {cpu_socket} 与主板插槽 {mb_socket} 不兼容。")
    return issues


def _ram_mb_capacity(ram, mb) -> List[str]:
    issues = []
    if int(ram.module_count) > int(mb.memory_slots):
        issues.append(
            f"内存条数 {ram.module_count} 超过主板插槽数 {mb.memory_slots}。"
        )
    if float(ram.total_capacity_gb) > float(mb.max_memory):
        issues.append(
            f"内存总容量 {ram.total_capacity_gb}GB 超过主板最大容量 {mb.max_memory}GB。"
        )
    if str(ram.ddr_generation).upper() != str(mb.ddr_generation).upper():
        issues.append(
            f"内存代际 {ram.ddr_generation} 与主板代际 {mb.ddr_generation} 不匹配。"
        )
    return issues


def _gpu_case(gpu, case) -> List[str]:
    issues = []
    if float(gpu.length) > float(case.max_gpu_length):
        issues.append(
            f"显卡长度 {gpu.length}mm 超过机箱限制 {case.max_gpu_length}mm。"
        )
    return issues


def _cooler_cpu_case(cooler, cpu, case) -> List[str]:
    issues = []
    if int(cpu.tdp) > int(cooler.tdp_capacity):
        issues.append(
            f"散热器解热能力 {cooler.tdp_capacity}W 低于 CPU TDP {cpu.tdp}W。"
        )

    supports = {s.strip().upper() for s in str(cooler.socket_support).split(",")}
    if str(cpu.socket).upper() not in supports:
        issues.append(f"散热器未标注支持 CPU 插槽 {cpu.socket}。")

    if float(cooler.size) > float(case.max_cooler_height):
        issues.append(
            f"散热器尺寸/冷排规格 {cooler.size}mm 超过机箱限制 {case.max_cooler_height}mm。"
        )
    return issues


def _psu_power(cpu, gpu, psu) -> List[str]:
    issues = []
    # 预留 100W 系统余量，再乘 1.3 安全系数
    required = (float(cpu.tdp) + float(gpu.tdp) + 100.0) * 1.3
    if required > float(psu.wattage):
        issues.append(
            f"电源功率 {psu.wattage}W 不足，建议至少 {required:.0f}W。"
        )
    return issues


def _storage_mb(storage, mb) -> List[str]:
    issues = []
    if int(storage.is_nvme) == 1 and int(mb.m2_slots) < 1:
        issues.append("NVMe 存储需要主板具备 M.2 插槽。")
    return issues


def check_compatibility(selection: Dict) -> Dict:
    """
    对完整装机方案做兼容性检查。
    """
    cpu = selection["cpu"]
    gpu = selection["gpu"]
    mb = selection["mb"]
    ram = selection["ram"]
    storage = selection["storage"]
    psu = selection["psu"]
    case = selection["case"]
    cooler = selection["cooler"]

    issues = []
    issues += _cpu_mb_socket(cpu, mb)
    issues += _ram_mb_capacity(ram, mb)
    issues += _gpu_case(gpu, case)
    issues += _cooler_cpu_case(cooler, cpu, case)
    issues += _psu_power(cpu, gpu, psu)
    issues += _storage_mb(storage, mb)

    return {"ok": len(issues) == 0, "issues": issues}

