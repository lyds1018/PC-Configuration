from typing import Mapping
from ..utils import OUTPUT_CANDIDATES

ALL_PART_KEYS = ["cpu", "gpu", "mb", "ram", "storage", "case", "psu", "cooler"]


def part_id(item: Mapping[str, object], key: str) -> object:
    """获取配件的唯一标识"""
    part = (
        item.get("parts", {}).get(key) if isinstance(item.get("parts"), dict) else None
    )
    return getattr(part, "id", getattr(part, "name", None))


def select_diverse_items(feasible: list[dict]) -> list[dict]:
    """选取多样性组合（哈希表判断）"""
    
    selected: list[dict] = []

    # 准备哈希集合
    seen_cpu_gpu = set()       # CPU+GPU
    seen_cooler_case = set()   # Cooler+Case
    seen_ram_storage = set()   # RAM+Storage
    seen_mb_psu = set()        # MB+PSU

    for item in feasible:
        cpu_id = part_id(item, "cpu")
        gpu_id = part_id(item, "gpu")
        mb_id = part_id(item, "mb")
        ram_id = part_id(item, "ram")
        storage_id = part_id(item, "storage")
        case_id = part_id(item, "case")
        cooler_id = part_id(item, "cooler")
        psu_id = part_id(item, "psu")

        # 生成哈希 key
        cpu_gpu_sig = (cpu_id, gpu_id)
        cooler_case_sig = (cooler_id, case_id)
        ram_storage_sig = (ram_id, storage_id)
        mb_psu_sig = (mb_id, psu_id)

        # 判断是否已经存在
        if (cpu_gpu_sig in seen_cpu_gpu or
            cooler_case_sig in seen_cooler_case or
            ram_storage_sig in seen_ram_storage or
            mb_psu_sig in seen_mb_psu):
            continue

        selected.append(item)

        # 更新集合
        seen_cpu_gpu.add(cpu_gpu_sig)
        seen_cooler_case.add(cooler_case_sig)
        seen_ram_storage.add(ram_storage_sig)
        seen_mb_psu.add(mb_psu_sig)

        # 达到目标数量
        if len(selected) >= OUTPUT_CANDIDATES:
            break

    return selected