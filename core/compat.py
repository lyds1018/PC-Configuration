from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from .models import Component


@dataclass
class CompatibilityIssue:
    message: str


def _to_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            return int(value)
        text = str(value).replace(',', '').strip()
        if text == '':
            return None
        return int(float(text))
    except (ValueError, TypeError):
        return None


def _norm(text: Optional[str]) -> str:
    return (text or '').strip().lower()


def _memory_modules(modules: Optional[str]) -> Optional[tuple[int, int]]:
    if not modules:
        return None
    try:
        parts = [p.strip() for p in str(modules).split(',')]
        if len(parts) != 2:
            return None
        return int(parts[0]), int(parts[1])
    except (ValueError, TypeError):
        return None


def check_compatibility(selected: Dict[str, Component]) -> List[CompatibilityIssue]:
    issues: List[CompatibilityIssue] = []

    cpu = selected.get('cpu')
    motherboard = selected.get('motherboard')
    memory = selected.get('memory')
    pc_case = selected.get('case')
    psu = selected.get('power-supply')
    video_card = selected.get('video-card')

    if cpu and motherboard:
        cpu_socket = cpu.specs.get('socket')
        board_socket = motherboard.specs.get('socket')
        if cpu_socket and board_socket and _norm(cpu_socket) != _norm(board_socket):
            issues.append(
                CompatibilityIssue(
                    f"CPU 与主板不兼容：{cpu_socket} vs {board_socket}。"
                )
            )

    if memory and motherboard:
        modules = _memory_modules(memory.specs.get('modules'))
        max_memory = _to_int(motherboard.specs.get('max_memory'))
        slots = _to_int(motherboard.specs.get('memory_slots'))
        if modules and max_memory:
            count, size = modules
            total = count * size
            if total > max_memory:
                issues.append(
                    CompatibilityIssue(
                        f"内存容量超过主板上限：{total}GB > {max_memory}GB。"
                    )
                )
            if slots and count > slots:
                issues.append(
                    CompatibilityIssue(
                        f"内存条数量超过主板插槽：{count} > {slots}。"
                    )
                )

    if pc_case and motherboard:
        case_type = pc_case.specs.get('type')
        form_factor = motherboard.specs.get('form_factor')
        if case_type and form_factor:
            if _norm(form_factor) not in _norm(case_type):
                issues.append(
                    CompatibilityIssue(
                        f"机箱规格可能不支持主板：{case_type} vs {form_factor}。"
                    )
                )

    if psu and (cpu or video_card):
        cpu_tdp = _to_int(cpu.specs.get('tdp')) if cpu else None
        gpu_tdp = _to_int(video_card.specs.get('tdp')) if video_card else None
        estimated = 0
        if cpu_tdp:
            estimated += cpu_tdp
        if gpu_tdp:
            estimated += gpu_tdp
        estimated += 50

        wattage = _to_int(psu.specs.get('wattage'))
        if wattage and estimated:
            required = int(estimated * 1.3)
            if wattage < required:
                issues.append(
                    CompatibilityIssue(
                        f"电源功率可能不足：建议 >= {required}W，当前 {wattage}W。"
                    )
                )

    return issues


def check_candidate(selected: Dict[str, Component], category: str, candidate: Component) -> List[CompatibilityIssue]:
    snapshot = dict(selected)
    snapshot[category] = candidate
    return check_compatibility(snapshot)