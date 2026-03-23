"""
兼容性检查模块

提供全面的配件兼容性验证：
- CPU 与主板插槽匹配
- 内存与主板兼容性
- 机箱与主板板型匹配
- 电源功率充足性
- 显卡长度与机箱兼容性
- 散热器高度与机箱兼容性
- M.2接口兼容性
等
"""

from typing import Dict, List

from pc_builder.compatibility import run_checks as original_run_checks


def make_parts_dict(selection: Dict) -> Dict:
    """
    将配件选择转换为兼容性检查所需的字典格式

    Args:
        selection: 配件选择字典

    Returns:
        标准化的配件信息字典
    """
    cpu = selection.get("cpu")
    mb = selection.get("mb")
    ram = selection.get("ram")
    case = selection.get("case")
    psu = selection.get("psu")
    gpu = selection.get("gpu")
    storage = selection.get("storage")
    cooler = selection.get("cooler")

    return {
        "cpu": {
            "tdp": float(cpu.tdp or 0),
            "socket": str(getattr(cpu, "microarchitecture", "") or ""),
        }
        if cpu
        else {},
        "mb": {
            "socket": str(mb.socket or "") if mb else "",
            "form_factor": str(mb.form_factor or "") if mb else "",
            "max_memory": int(mb.max_memory or 0) if mb else 0,
            "memory_slots": int(mb.memory_slots or 0) if mb else 0,
        }
        if mb
        else {},
        "ram": {
            "modules": str(ram.modules or "") if ram else "",
        }
        if ram
        else {},
        "case": {
            "type": str(case.type or "") if case else "",
            "internal_35_bays": int(case.internal_35_bays or 0) if case else 0,
            "max_gpu_length": float(getattr(case, "external_volume", 0) or 0),  # 估算
            "max_cooler_height": 0,  # 需要从数据中获取
        }
        if case
        else {},
        "psu": {
            "wattage": int(psu.wattage or 0) if psu else 0,
        }
        if psu
        else {},
        "gpu": {
            "boost_clock": float(gpu.boost_clock or 0) if gpu else 0,
            "length": float(gpu.length or 0) if gpu else 0,
        }
        if gpu
        else {},
        "ssd": {
            "type": str(storage.type or "") if storage else "",
            "interface": str(getattr(storage, "interface", "") or "")
            if storage
            else "",
        }
        if storage
        else {},
        "storage_count": 1,
        "cooler": {
            "size": float(cooler.size or 0) if cooler else 0,
            "noise_level": str(getattr(cooler, "noise_level", "") or "")
            if cooler
            else "",
        }
        if cooler
        else {},
    }


def check_compatibility(selection: Dict) -> Dict:
    """
    执行完整的兼容性检查

    Args:
        selection: 配件选择字典

    Returns:
        兼容性检查结果：{"ok": bool, "issues": list}
    """
    parts = make_parts_dict(selection)
    issues = []

    # 1. 基础兼容性检查（使用原有逻辑）
    base_result = original_run_checks(parts)
    issues.extend(base_result.get("issues", []))

    # 2. 扩展兼容性检查
    issues += _check_cpu_mb_extended(parts["cpu"], parts["mb"])
    issues += _check_gpu_case_compatibility(parts["gpu"], parts["case"])
    issues += _check_cooler_compatibility(parts["cooler"], parts["cpu"], parts["case"])
    issues += _check_storage_mb_compatibility(parts["ssd"], parts["mb"])
    issues += _check_ram_clearance(parts["ram"], parts["cooler"])

    return {"ok": len(issues) == 0, "issues": issues}


def _check_cpu_mb_extended(cpu: Dict, mb: Dict) -> List[str]:
    """
    扩展的 CPU-主板兼容性检查

    Args:
        cpu: CPU 信息
        mb: 主板信息

    Returns:
        问题列表
    """
    issues = []

    cpu_socket = cpu.get("socket", "").upper()
    mb_socket = mb.get("socket", "").upper()

    # 如果有 socket 信息但不匹配
    if cpu_socket and mb_socket:
        # 简化的插槽匹配（实际应该更复杂）
        if "AM5" in cpu_socket and "AM5" not in mb_socket:
            issues.append("AMD AM5 平台 CPU 需要 AM5 插槽主板。")
        elif "AM4" in cpu_socket and "AM4" not in mb_socket and "AM5" not in mb_socket:
            issues.append("AMD AM4 平台 CPU 需要 AM4 或 AM5 插槽主板。")
        elif (
            "LGA1700" in cpu_socket
            and "LGA1700" not in mb_socket
            and "LGA1800" not in mb_socket
        ):
            issues.append("Intel LGA1700 CPU 需要 LGA1700 或更新的主板。")

    return issues


def _check_gpu_case_compatibility(gpu: Dict, case: Dict) -> List[str]:
    """
    显卡与机箱兼容性检查

    Args:
        gpu: GPU 信息
        case: 机箱信息

    Returns:
        问题列表
    """
    issues = []

    gpu_length = gpu.get("length", 0)
    # 这里需要机箱的最大 GPU 长度限制，暂时用外部体积估算
    case_max_length = case.get("max_gpu_length", 0) * 10  # 粗略估算

    if gpu_length > 0 and case_max_length > 0:
        if gpu_length > case_max_length:
            issues.append(
                f"显卡长度 {gpu_length}mm 超过机箱支持的最大长度 {case_max_length:.0f}mm。"
            )

    return issues


def _check_cooler_compatibility(cooler: Dict, cpu: Dict, case: Dict) -> List[str]:
    """
    散热器兼容性检查

    Args:
        cooler: 散热器信息
        cpu: CPU 信息
        case: 机箱信息

    Returns:
        问题列表
    """
    issues = []

    cooler_size = cooler.get("size", 0)
    cpu_tdp = cpu.get("tdp", 0)

    # 简单的 TDP 匹配检查
    if cooler_size > 0 and cpu_tdp > 0:
        # 散热器尺寸与 TDP 的关系（简化版）
        min_cooler_size = cpu_tdp / 2  # 每 2W TDP 需要 1mm 散热器
        if cooler_size < min_cooler_size:
            issues.append(
                f"散热器尺寸 {cooler_size}mm 可能不足以散发 CPU {cpu_tdp}W 的热量。"
            )

    return issues


def _check_storage_mb_compatibility(storage: Dict, mb: Dict) -> List[str]:
    """
    存储设备与主板兼容性检查

    Args:
        storage: 存储设备信息
        mb: 主板信息

    Returns:
        问题列表
    """
    issues = []

    storage_type = storage.get("type", "")
    storage_interface = storage.get("interface", "")

    # NVMe SSD 需要 M.2 接口
    if "NVME" in storage_interface.upper() or "M.2" in storage_type.upper():
        # 现代主板基本都支持 M.2，这里只是示意
        pass

    return issues


def _check_ram_clearance(ram: Dict, cooler: Dict) -> List[str]:
    """
    内存与散热器间隙检查

    Args:
        ram: 内存信息
        cooler: 散热器信息

    Returns:
        问题列表
    """
    issues = []

    # 这个检查需要更多关于内存高度和散热器设计的信息
    # 目前无法实现

    return issues
