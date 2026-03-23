"""
配件评分系统

提供多维度的配件评分：
- 性能评分：基于硬件规格
- 能效评分：基于性能与功耗比
- 性价比评分：基于性能与价格比
"""

import re
from typing import Optional, Union

from ..utils.normalizer import (
    normalize_gpu_memory,
)


def price(value: Union[str, float, int, None]) -> float:
    """
    标准化价格处理

    Args:
        value: 价格值

    Returns:
        浮点数价格，无效输入返回 0.0
    """
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def cpu_brand(name: Optional[str]) -> str:
    """
    识别 CPU 品牌

    Args:
        name: CPU 名称

    Returns:
        'intel', 'amd', 或 'other'
    """
    if not name:
        return "other"

    text = name.lower()
    if "intel" in text:
        return "intel"
    if "amd" in text or "ryzen" in text:
        return "amd"
    return "other"


def gpu_brand(name: Optional[str]) -> str:
    """
    识别 GPU 品牌

    Args:
        name: GPU 名称

    Returns:
        'nvidia', 'amd', 或 'other'
    """
    if not name:
        return "other"

    text = name.lower()
    if "nvidia" in text or "geforce" in text or "rtx" in text or "gtx" in text:
        return "nvidia"
    if "amd" in text or "radeon" in text or "rx " in text:
        return "amd"
    return "other"


def cpu_score(cpu, usage: str = "gaming") -> float:
    """
    CPU 综合评分

    考虑因素：
    - 核心数量
    - 时钟频率
    - 架构代数
    - TDP（能效）
    - 用途权重

    Args:
        cpu: CPU 对象
        usage: 用途 ('gaming', 'office', 'productivity')

    Returns:
        CPU 综合评分
    """
    if not cpu:
        return 0.0

    # 基础分：核心数 * 2 + 基准频率
    core_count = float(cpu.core_count or 0)
    threads = float(getattr(cpu, "threads", 0) or 0)
    l3_cache_mb = float(getattr(cpu, "l3_cache_mb", 0) or 0)
    base_clock = float(cpu.core_clock or 0)
    boost_clock = float(cpu.boost_clock or 0)
    tdp = float(cpu.tdp or 0)

    # 平均频率权重
    avg_clock = (base_clock + boost_clock) / 2

    # 基础性能分
    base = core_count * 2.5 + avg_clock * 1.2
    if threads > 0:
        base += threads * 0.25
    if l3_cache_mb > 0:
        base += min(l3_cache_mb, 96) * 0.08

    # 架构加成（简化版，根据微架构名称判断）
    arch_bonus = 1.0
    if hasattr(cpu, "microarchitecture"):
        arch = str(cpu.microarchitecture or "").lower()
        if "zen 5" in arch or "arrow lake" in arch or "raptor lake" in arch:
            arch_bonus = 1.3
        elif "zen 4" in arch or "raptor" in arch:
            arch_bonus = 1.2
        elif "zen 3" in arch or "rocket" in arch:
            arch_bonus = 1.1
        elif "zen 2" in arch or "comet" in arch:
            arch_bonus = 1.0
        else:
            arch_bonus = 0.9

    base *= arch_bonus

    # 用途加权
    if usage == "gaming":
        # 游戏更看重单核性能（提升频率权重）
        score = base + boost_clock * 1.8
    elif usage == "office":
        # 办公场景降低功耗敏感度
        score = base * 0.85
    elif usage == "productivity":
        # 生产力更看重多核性能
        score = base * 1.3 + core_count * 1.5
    else:
        score = base

    # 能效惩罚（过高的 TDP 会降低评分）
    if tdp > 150:
        score *= 0.9
    elif tdp > 100:
        score *= 0.95

    return score


def gpu_score(gpu, usage: str = "gaming") -> float:
    """
    GPU 综合评分

    考虑因素：
    - 显存容量
    - 时钟频率
    - 架构
    - 用途权重

    Args:
        gpu: GPU 对象
        usage: 用途 ('gaming', 'office', 'productivity')

    Returns:
        GPU 综合评分
    """
    if not gpu:
        return 0.0

    # 提取规格
    memory = normalize_gpu_memory(gpu.memory)
    base_clock = float(gpu.core_clock or 0)
    boost_clock = float(gpu.boost_clock or 0)
    tdp = float(getattr(gpu, "tdp", 0) or 0)

    # 基础分：显存 * 60 + 频率
    base = memory * 60 + boost_clock * 0.8

    # 架构识别（通过 chipset 名称）
    arch_bonus = 1.0
    if hasattr(gpu, "chipset"):
        chipset = str(gpu.chipset or "").lower()
        # NVIDIA
        if "rtx 50" in chipset:
            arch_bonus = 1.4
        elif "rtx 40" in chipset:
            arch_bonus = 1.2
        elif "rtx 30" in chipset:
            arch_bonus = 1.0
        # AMD
        elif "rx 90" in chipset:
            arch_bonus = 1.3
        elif "rx 70" in chipset:
            arch_bonus = 1.1
        elif "rx 60" in chipset:
            arch_bonus = 1.0

    base *= arch_bonus

    # 用途加权
    if usage == "gaming":
        score = base * 1.4
    elif usage == "office":
        score = base * 0.5  # 办公对显卡要求低
    elif usage == "productivity":
        # 生产力应用（渲染、视频编辑）需要大显存
        score = base * 1.2 + memory * 30
    else:
        score = base

    # 同代产品中，过高功耗会有小幅惩罚
    if tdp > 300:
        score *= 0.93
    elif tdp > 250:
        score *= 0.96

    return score


def ram_score(ram) -> float:
    """
    内存综合评分

    考虑因素：
    - 速度（MT/s）
    - 容量
    - 延迟
    - 价格

    Args:
        ram: 内存对象

    Returns:
        内存综合评分
    """
    if not ram:
        return 0.0

    # 解析速度
    speed_text = str(ram.speed or "")
    numbers = re.findall(r"\d+", speed_text)
    speed = float(numbers[0]) if numbers else 0.0

    # 解析容量（从 modules 字段）
    total_capacity = float(getattr(ram, "total_capacity_gb", 0) or 0)
    if total_capacity <= 0:
        modules_text = str(ram.modules or "")
        module_parts = modules_text.split(",")
        if len(module_parts) >= 2:
            try:
                module_count = int(module_parts[0].strip())
                module_size = float(module_parts[1].strip())
                total_capacity = module_count * module_size
            except (ValueError, IndexError):
                total_capacity = 0.0
        else:
            total_capacity = 0.0

    # CAS 延迟（越低越好）
    cas_latency = float(ram.cas_latency or 0)

    # 基础分：速度 + 容量 * 系数
    base = speed + total_capacity * 15

    # 延迟惩罚
    if cas_latency > 0:
        base *= (40 / cas_latency) ** 0.3  # CL40 为基准

    # 价格因素（性价比）
    ram_price = price(ram.price)
    if ram_price > 0:
        base *= (1 + 50 / ram_price) ** 0.2

    return base


def storage_score(storage) -> float:
    """
    存储设备综合评分

    考虑因素：
    - 容量
    - 类型（SSD vs HDD）
    - 接口速度
    - 价格

    Args:
        storage: 存储设备对象

    Returns:
        存储设备综合评分
    """
    if not storage:
        return 0.0

    capacity = float(storage.capacity or 0)
    storage_type = str(storage.type or "").upper()
    interface = str(storage.interface or "").upper()
    storage_class = str(getattr(storage, "storage_class", "") or "").upper()
    ram_price = price(storage.price)

    # 类型系数
    type_multiplier = 1.0
    if "SSD" in storage_type or "M.2" in storage_type or "NVME" in storage_type:
        type_multiplier = 1.5
    elif "HDD" in storage_type:
        type_multiplier = 0.8

    if "NVME SSD" in storage_class:
        type_multiplier = max(type_multiplier, 1.6)
    elif "SATA SSD" in storage_class:
        type_multiplier = max(type_multiplier, 1.35)

    # 接口系数
    interface_bonus = 0.0
    if "NVME" in interface or "PCIE" in interface:
        interface_bonus = 50
    elif "SATA" in interface:
        interface_bonus = 20

    # 基础分：容量 * 类型系数 + 接口加成
    base = capacity * type_multiplier + interface_bonus

    # 价格因素
    if ram_price > 0:
        base *= (1 + 100 / ram_price) ** 0.15

    return base


def psu_score(psu) -> float:
    """
    电源综合评分

    考虑因素：
    - 瓦数
    - 能效等级
    - 模块化
    - 价格

    Args:
        psu: 电源对象

    Returns:
        电源综合评分
    """
    if not psu:
        return 0.0

    wattage = float(psu.wattage or 0)
    efficiency = str(psu.efficiency or "").lower()
    modular = str(psu.modular or "").lower()
    ram_price = price(psu.price)

    # 瓦数基础分
    base = wattage * 0.3

    # 能效等级加成
    eff_bonus = 0.0
    if "titanium" in efficiency:
        eff_bonus = 100
    elif "platinum" in efficiency:
        eff_bonus = 70
    elif "gold" in efficiency:
        eff_bonus = 50
    elif "silver" in efficiency:
        eff_bonus = 30
    elif "bronze" in efficiency:
        eff_bonus = 20

    base += eff_bonus

    # 模块化加成
    if "full" in modular or "true" in modular:
        base *= 1.15
    elif "semi" in modular:
        base *= 1.05

    # 价格因素（不过度追求低价）
    if ram_price > 0:
        base *= (1 + 200 / ram_price) ** 0.1

    return base


def case_score(case) -> float:
    """
    机箱综合评分

    考虑因素：
    - 兼容性（支持的板型）
    - 扩展性（硬盘位）
    - 散热设计
    - 价格

    Args:
        case: 机箱对象

    Returns:
        机箱综合评分
    """
    if not case:
        return 0.0

    case_type = str(case.type or "").upper()
    bays = float(case.internal_35_bays or 0)
    ram_price = price(case.price)

    # 板型支持度（ATX 为标准）
    type_base = 50.0
    if "E-ATX" in case_type:
        type_base = 80
    elif "ATX" in case_type:
        type_base = 60
    elif "MICRO" in case_type or "M-ATX" in case_type:
        type_base = 45
    elif "MINI" in case_type or "ITX" in case_type:
        type_base = 40

    # 扩展性加分
    expansion = bays * 10

    # 价格因素
    if ram_price > 0:
        bonus = (1 + 150 / ram_price) ** 0.15
    else:
        bonus = 1.0

    return (type_base + expansion) * bonus


def cooler_score(cooler) -> float:
    """
    散热器综合评分

    考虑因素：
    - 散热能力（尺寸、转速）
    - 噪音控制
    - 价格

    Args:
        cooler: 散热器对象

    Returns:
        散热器综合评分
    """
    if not cooler:
        return 0.0

    size = float(cooler.size or 0)
    rpm_text = str(cooler.rpm or "")
    noise_text = str(cooler.noise_level or "")
    ram_price = price(cooler.price)

    # 尺寸基础分（越大散热越好）
    base = size * 2.5

    # RPM 提取和加分
    rpm_numbers = re.findall(r"\d+", rpm_text)
    if rpm_numbers:
        rpm = float(rpm_numbers[0])
        base += rpm * 0.02

    # 噪音惩罚（如果知道噪音值）
    noise_numbers = re.findall(r"[\d.]+", noise_text)
    if noise_numbers:
        noise_db = float(noise_numbers[0])
        if noise_db > 30:
            base *= (35 / noise_db) ** 0.3

    # 价格因素
    if ram_price > 0:
        base *= (1 + 100 / ram_price) ** 0.12

    return base


def efficiency_score(component, component_type: str) -> float:
    """
    通用能效评分

    Args:
        component: 配件对象
        component_type: 配件类型 ('cpu', 'gpu', 'psu' 等)

    Returns:
        能效评分（0-100）
    """
    if not component:
        return 0.0

    if component_type == "cpu":
        perf = cpu_score(component, "balanced")
        power = float(component.tdp or 0)
    elif component_type == "gpu":
        perf = gpu_score(component, "balanced")
        # GPU 没有直接 TDP，估算
        boost = float(component.boost_clock or 0)
        power = 0.16 * boost + 50 if boost > 0 else 100
    elif component_type == "psu":
        # 电源的能效看转换效率
        eff = str(component.efficiency or "").lower()
        if "titanium" in eff:
            return 95.0
        elif "platinum" in eff:
            return 90.0
        elif "gold" in eff:
            return 85.0
        elif "silver" in eff:
            return 80.0
        elif "bronze" in eff:
            return 75.0
        else:
            return 70.0
    else:
        return 50.0

    if power <= 0:
        return 50.0

    # 性能/功耗比，归一化到 0-100
    ratio = perf / power
    return min(100.0, ratio * 2)


def value_score(component, base_score: float) -> float:
    """
    性价比评分

    Args:
        component: 配件对象
        base_score: 基础性能评分

    Returns:
        性价比评分（0-100）
    """
    if not component or base_score <= 0:
        return 0.0

    comp_price = price(component.price)
    if comp_price <= 0:
        return 0.0

    # 性能/价格比，归一化
    ratio = base_score / comp_price
    return min(100.0, ratio * 50)
