from __future__ import annotations

from typing import Any, Dict, List

from . import all_checks
from .utils import read, to_upper


def _derive_storage_totals(parts: Dict[str, Any]) -> dict[str, int]:
    """从配件数据导出支持的存储设备总数"""
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
        storage_type = to_upper(read(storage, "type"))
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


def run_checks(parts: Dict[str, Any]) -> Dict[str, Any]:
    """
    运行所有兼容性检查

    参数:
        parts: 配件字典，包含 cpu, mb, ram, gpu, case, psu, cooler, storages, totals

    返回:
        {"ok": bool, "issues": list[str]} - ok 表示是否通过所有检查，issues 是问题列表
    """
    cpu = parts.get("cpu", {})
    mb = parts.get("mb", {})
    ram = parts.get("ram", {})
    gpu = parts.get("gpu", {})
    case = parts.get("case", {})
    psu = parts.get("psu", {})
    cooler = parts.get("cooler", {})

    totals = _derive_storage_totals(parts)

    issues: List[str] = []
    issues += all_checks.check_cpu_mb_socket(cpu, mb)
    issues += all_checks.check_cpu_ram(cpu, ram)
    issues += all_checks.check_mb_case(mb, case)
    issues += all_checks.check_mb_ram(mb, ram)
    issues += all_checks.check_gpu_case(gpu, case)
    issues += all_checks.check_cooler_case(cooler, case)
    issues += all_checks.check_psu_case(psu, case)
    issues += all_checks.check_power(cpu, gpu, psu)
    issues += all_checks.check_storage_totals(mb, case, totals)
    issues += all_checks.check_totals(mb, totals)

    return {"ok": len(issues) == 0, "issues": issues}
