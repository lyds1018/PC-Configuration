from typing import Dict, List, Mapping
from .utils import OUTPUT_CANDIDATES

ALL_PART_KEYS = ["cpu", "mb", "ram", "gpu", "storage", "cooler"]


def part_id(item: Mapping[str, object], key: str) -> object:
    part = (
        item.get("parts", {}).get(key) if isinstance(item.get("parts"), dict) else None
    )
    return getattr(part, "id", getattr(part, "name", None))


def core_signature(item: Mapping[str, object]) -> tuple[object, ...]:
    return tuple(part_id(item, key) for key in ("cpu", "gpu", "mb", "ram", "storage"))


def is_diverse(
    candidate: Mapping[str, object], selected: List[Dict[str, object]]
) -> bool:
    '''检查组合多样性。'''
    candidate_price = float(candidate.get("total_price", 0))

    for item in selected:
        if core_signature(candidate) == core_signature(item):
            return False

        cpu_diff = part_id(candidate, "cpu") != part_id(item, "cpu")
        gpu_diff = part_id(candidate, "gpu") != part_id(item, "gpu")
        if not (cpu_diff or gpu_diff):
            return False

        same_count = 0
        for key in ALL_PART_KEYS:
            if (
                part_id(candidate, key) == part_id(item, key)
                and part_id(candidate, key) is not None
            ):
                same_count += 1

        if same_count >= 3:
            return False

        item_price = float(item.get("total_price", 0))
        if abs(candidate_price - item_price) < 500.0:
            if not (cpu_diff and gpu_diff):
                return False

    return True


def select_diverse_items(feasible: List[Dict[str, object]]) -> List[Dict[str, object]]:
    '''选取多样性组合。'''
    selected: List[Dict[str, object]] = []
    
    for item in feasible:
        if is_diverse(item, selected):
            selected.append(item)
            
            if len(selected) >= OUTPUT_CANDIDATES:
                return selected
                
    return selected