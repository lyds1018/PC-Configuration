"""
特征工程模块

为每个配件提取特征向量，用于机器学习推荐算法
"""

from typing import Any, Dict, List

from ..utils.normalizer import (
    extract_clock_speed,
    normalize_form_factor,
    normalize_gpu_memory,
    normalize_power,
    normalize_ram_speed,
    normalize_size,
    normalize_socket,
    normalize_storage_capacity,
    parse_module_spec,
)


def extract_cpu_features(cpu) -> Dict[str, Any]:
    """
    提取 CPU 特征

    Args:
        cpu: CPU 对象

    Returns:
        特征字典
    """
    if not cpu:
        return {}

    # 基础规格
    core_count = float(cpu.core_count or 0)
    base_clock = extract_clock_speed(cpu.core_clock)
    boost_clock = extract_clock_speed(cpu.boost_clock)
    tdp = normalize_power(cpu.tdp)

    # 架构代数（简化版）
    arch = str(getattr(cpu, "microarchitecture", "") or "").lower()
    arch_gen = 0
    if "zen 5" in arch or "arrow lake" in arch:
        arch_gen = 5
    elif "zen 4" in arch or "raptor lake" in arch:
        arch_gen = 4
    elif "zen 3" in arch or "rocket lake" in arch:
        arch_gen = 3
    elif "zen 2" in arch or "comet lake" in arch:
        arch_gen = 2
    elif "zen" in arch:
        arch_gen = 1

    # 是否有集成显卡
    has_igpu = bool(getattr(cpu, "graphics", 0))

    return {
        "core_count": core_count,
        "base_clock_mhz": base_clock,
        "boost_clock_mhz": boost_clock,
        "tdp_watts": tdp,
        "architecture_gen": arch_gen,
        "has_integrated_graphics": has_igpu,
        "performance_index": core_count * 2 + boost_clock,  # 简单性能指数
    }


def extract_gpu_features(gpu) -> Dict[str, Any]:
    """
    提取 GPU 特征

    Args:
        gpu: GPU 对象

    Returns:
        特征字典
    """
    if not gpu:
        return {}

    memory = normalize_gpu_memory(gpu.memory)
    base_clock = extract_clock_speed(gpu.core_clock)
    boost_clock = extract_clock_speed(gpu.boost_clock)
    length = normalize_size(gpu.length)

    # 架构识别
    chipset = str(getattr(gpu, "chipset", "") or "").lower()
    arch_gen = 0
    if "rtx 50" in chipset:
        arch_gen = 5
    elif "rtx 40" in chipset:
        arch_gen = 4
    elif "rtx 30" in chipset:
        arch_gen = 3
    elif "rx 90" in chipset:
        arch_gen = 5
    elif "rx 70" in chipset:
        arch_gen = 4
    elif "rx 60" in chipset:
        arch_gen = 3

    return {
        "vram_gb": memory,
        "base_clock_mhz": base_clock,
        "boost_clock_mhz": boost_clock,
        "length_mm": length,
        "architecture_gen": arch_gen,
        "performance_index": memory * 60 + boost_clock,
    }


def extract_mb_features(mb) -> Dict[str, Any]:
    """
    提取主板特征

    Args:
        mb: 主板对象

    Returns:
        特征字典
    """
    if not mb:
        return {}

    socket = normalize_socket(getattr(mb, "socket", ""))
    form_factor = normalize_form_factor(getattr(mb, "form_factor", ""))
    max_memory = float(getattr(mb, "max_memory", 0) or 0)
    memory_slots = float(getattr(mb, "memory_slots", 0) or 0)

    # 板型数字化
    ff_map = {
        "MINI ITX": 1,
        "MICRO ATX": 2,
        "ATX": 3,
        "E-ATX": 4,
    }
    ff_score = ff_map.get(form_factor, 2)

    return {
        "socket": socket,
        "form_factor": form_factor,
        "form_factor_score": ff_score,
        "max_memory_gb": max_memory,
        "memory_slots": memory_slots,
        "expansion_score": ff_score * 10 + max_memory / 16,
    }


def extract_ram_features(ram) -> Dict[str, Any]:
    """
    提取内存特征

    Args:
        ram: 内存对象

    Returns:
        特征字典
    """
    if not ram:
        return {}

    speed = normalize_ram_speed(getattr(ram, "speed", ""))
    modules_str = getattr(ram, "modules", "")
    module_count, module_size = parse_module_spec(modules_str)
    total_capacity = module_count * module_size

    cas_latency = float(getattr(ram, "cas_latency", 0) or 0)

    return {
        "speed_mt_s": speed,
        "module_count": module_count,
        "module_size_gb": module_size,
        "total_capacity_gb": total_capacity,
        "cas_latency": cas_latency,
        "performance_index": speed + total_capacity * 10,
    }


def extract_storage_features(storage) -> Dict[str, Any]:
    """
    提取存储设备特征

    Args:
        storage: 存储设备对象

    Returns:
        特征字典
    """
    if not storage:
        return {}

    capacity = normalize_storage_capacity(getattr(storage, "capacity", 0))
    storage_type = str(getattr(storage, "type", "") or "").upper()
    interface = str(getattr(storage, "interface", "") or "").upper()

    # 类型分类
    is_ssd = "SSD" in storage_type or "M.2" in storage_type or "NVME" in storage_type
    is_hdd = "HDD" in storage_type and not is_ssd
    is_nvme = "NVME" in interface or "PCIE" in interface

    # 速度等级（1-5）
    speed_tier = 1
    if is_nvme:
        speed_tier = 5
    elif is_ssd:
        speed_tier = 3
    elif is_hdd:
        speed_tier = 1

    return {
        "capacity_gb": capacity,
        "is_ssd": is_ssd,
        "is_hdd": is_hdd,
        "is_nvme": is_nvme,
        "speed_tier": speed_tier,
        "value_index": capacity * (1 if is_hdd else 1.5),
    }


def extract_psu_features(psu) -> Dict[str, Any]:
    """
    提取电源特征

    Args:
        psu: 电源对象

    Returns:
        特征字典
    """
    if not psu:
        return {}

    wattage = float(getattr(psu, "wattage", 0) or 0)
    efficiency = str(getattr(psu, "efficiency", "") or "").lower()
    modular = str(getattr(psu, "modular", "") or "").lower()

    # 能效等级数字化
    eff_map = {
        "titanium": 5,
        "platinum": 4,
        "gold": 3,
        "silver": 2,
        "bronze": 1,
    }
    eff_score = 0
    for key, value in eff_map.items():
        if key in efficiency:
            eff_score = value
            break

    # 模块化
    mod_score = 0
    if "full" in modular or "true" in modular:
        mod_score = 2
    elif "semi" in modular:
        mod_score = 1

    return {
        "wattage": wattage,
        "efficiency_score": eff_score,
        "modular_score": mod_score,
        "quality_index": wattage * eff_score * 0.1,
    }


def extract_case_features(case) -> Dict[str, Any]:
    """
    提取机箱特征

    Args:
        case: 机箱对象

    Returns:
        特征字典
    """
    if not case:
        return {}

    case_type = normalize_form_factor(getattr(case, "type", ""))
    bays = float(getattr(case, "internal_35_bays", 0) or 0)

    # 板型支持度
    ff_map = {
        "MINI ITX": 1,
        "MICRO ATX": 2,
        "ATX": 3,
        "E-ATX": 4,
    }
    ff_score = ff_map.get(case_type, 2)

    return {
        "form_factor": case_type,
        "form_factor_score": ff_score,
        "drive_bays": bays,
        "expansion_score": ff_score * 10 + bays * 5,
    }


def extract_cooler_features(cooler) -> Dict[str, Any]:
    """
    提取散热器特征

    Args:
        cooler: 散热器对象

    Returns:
        特征字典
    """
    if not cooler:
        return {}

    size = float(getattr(cooler, "size", 0) or 0)
    rpm_text = str(getattr(cooler, "rpm", "") or "")
    noise_text = str(getattr(cooler, "noise_level", "") or "")

    # RPM 提取
    import re

    rpm_numbers = re.findall(r"\d+", rpm_text)
    rpm = float(rpm_numbers[0]) if rpm_numbers else 0

    # 噪音提取
    noise_numbers = re.findall(r"[\d.]+", noise_text)
    noise_db = float(noise_numbers[0]) if noise_numbers else 0

    # 散热能力估算
    cooling_capacity = size * 15 + rpm * 0.05

    return {
        "size_mm": size,
        "max_rpm": rpm,
        "noise_db": noise_db,
        "cooling_capacity": cooling_capacity,
        "efficiency_index": cooling_capacity / (noise_db if noise_db > 0 else 30),
    }


def get_feature_vector(component, component_type: str) -> List[float]:
    """
    获取配件的特征向量（用于机器学习算法）

    Args:
        component: 配件对象
        component_type: 配件类型

    Returns:
        特征向量列表
    """
    extractors = {
        "cpu": extract_cpu_features,
        "gpu": extract_gpu_features,
        "mb": extract_mb_features,
        "ram": extract_ram_features,
        "storage": extract_storage_features,
        "psu": extract_psu_features,
        "case": extract_case_features,
        "cooler": extract_cooler_features,
    }

    extractor = extractors.get(component_type)
    if not extractor:
        return []

    features = extractor(component)

    # 转换为向量（取数值部分）
    vector = []
    for key in sorted(features.keys()):
        value = features[key]
        if isinstance(value, (int, float)):
            vector.append(float(value))
        elif isinstance(value, bool):
            vector.append(1.0 if value else 0.0)

    return vector
