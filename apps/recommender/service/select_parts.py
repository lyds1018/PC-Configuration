from math import ceil
from typing import Dict, List, Mapping


def part_id(item: Mapping[str, object], key: str) -> object:
    part = (
        item.get("parts", {}).get(key) if isinstance(item.get("parts"), dict) else None
    )
    return getattr(part, "id", getattr(part, "name", None))


def core_signature(item: Mapping[str, object]) -> tuple[object, ...]:
    return tuple(part_id(item, key) for key in ("cpu", "gpu", "mb", "ram", "storage"))


def is_diverse_enough(
    candidate: Mapping[str, object], selected: List[Dict[str, object]]
) -> bool:
    """展示方案必须在核心配置上有可感知差异。"""
    for item in selected:
        if core_signature(candidate) == core_signature(item):
            return False

        cpu_diff = part_id(candidate, "cpu") != part_id(item, "cpu")
        gpu_diff = part_id(candidate, "gpu") != part_id(item, "gpu")
        if not (cpu_diff or gpu_diff):
            return False
    return True


def select_diverse_top_items(
    feasible: List[Dict[str, object]], top_k: int
) -> List[Dict[str, object]]:
    selected: List[Dict[str, object]] = []
    max_same_core_part = max(1, ceil(top_k / 2))
    for item in feasible:
        cpu_id = part_id(item, "cpu")
        gpu_id = part_id(item, "gpu")
        if (
            sum(
                1
                for selected_item in selected
                if part_id(selected_item, "cpu") == cpu_id
            )
            >= max_same_core_part
        ):
            continue
        if (
            sum(
                1
                for selected_item in selected
                if part_id(selected_item, "gpu") == gpu_id
            )
            >= max_same_core_part
        ):
            continue
        if is_diverse_enough(item, selected):
            selected.append(item)
            if len(selected) >= top_k:
                return selected

    # 预算或品牌约束太窄时仍保证有结果，但尽量避免完全重复核心件。
    seen_signatures = {core_signature(item) for item in selected}
    for item in feasible:
        signature = core_signature(item)
        if signature in seen_signatures:
            continue
        selected.append(item)
        seen_signatures.add(signature)
        if len(selected) >= top_k:
            return selected

    for item in feasible:
        if item not in selected:
            selected.append(item)
            if len(selected) >= top_k:
                return selected
    return selected
