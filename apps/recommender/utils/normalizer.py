"""数据标准化工具模块"""

import re
from typing import Any, Optional


def normalize_power(value: Any) -> float:
    """
    标准化功率值（TDP、功耗等）

    Args:
        value: 功率值，可以是数字或字符串

    Returns:
        标准化的功率值（瓦特），如果无法解析则返回 0.0
    """
    if value is None:
        return 0.0

    try:
        # 如果是数字直接返回
        if isinstance(value, (int, float)):
            return float(value)

        # 如果是字符串，提取数字
        text = str(value).strip().upper()
        # 移除单位标记
        text = re.sub(r"\s*W\b", "", text)  # 移除 "W"
        text = re.sub(r"\s*TDP\b", "", text)  # 移除 "TDP"

        # 提取数值
        match = re.search(r"[\d.]+", text)
        if match:
            return float(match.group())
        return 0.0
    except (ValueError, TypeError):
        return 0.0


def normalize_size(value: Any, unit: str = "mm") -> float:
    """
    标准化尺寸值（长度、高度、宽度等）

    Args:
        value: 尺寸值
        unit: 目标单位，默认为 mm

    Returns:
        标准化的尺寸值，如果无法解析则返回 0.0
    """
    if value is None:
        return 0.0

    try:
        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip()
        # 提取数值
        match = re.search(r"[\d.]+", text)
        if match:
            return float(match.group())
        return 0.0
    except (ValueError, TypeError):
        return 0.0


def normalize_socket(socket: Optional[str]) -> str:
    """
    标准化 CPU 插槽名称

    Args:
        socket: 原始插槽名称

    Returns:
        标准化的插槽名称
    """
    if not socket:
        return ""

    text = str(socket).strip().upper()

    # 常见插槽映射
    socket_map = {
        "AM5": "AM5",
        "AM4": "AM4",
        "AM3": "AM3",
        "AM3+": "AM3+",
        "FM2+": "FM2+",
        "LGA1700": "LGA1700",
        "LGA1200": "LGA1200",
        "LGA1151": "LGA1151",
        "LGA1150": "LGA1150",
        "LGA2066": "LGA2066",
        "LGA2011": "LGA2011",
        "LGA2011-3": "LGA2011-3",
        "TR4": "TR4",
        "SP3": "SP3",
        "S1700": "S1700",  # Intel 新插槽
    }

    # 精确匹配
    if text in socket_map.values():
        return text

    # 模糊匹配
    for key, value in socket_map.items():
        if key in text or value in text:
            return value

    # 返回原始值（大写）
    return text


def normalize_form_factor(form_factor: Optional[str]) -> str:
    """
    标准化主板和机箱规格

    Args:
        form_factor: 原始规格名称

    Returns:
        标准化的规格名称
    """
    if not form_factor:
        return ""

    text = str(form_factor).strip().upper()

    # 规格映射
    ff_map = {
        "MINI ITX": "MINI ITX",
        "ITX": "MINI ITX",
        "MICRO ATX": "MICRO ATX",
        "M-ATX": "MICRO ATX",
        "MATX": "MICRO ATX",
        "ATX": "ATX",
        "E-ATX": "E-ATX",
        "EXTENDED ATX": "E-ATX",
    }

    # 查找匹配
    for key, value in ff_map.items():
        if key in text:
            return value

    return text


def normalize_ram_speed(speed: Any) -> int:
    """
    标准化内存速度（MT/s）

    Args:
        speed: 速度值，可能是 "DDR4-3200" 或 "3200MHz" 等格式

    Returns:
        标准化的速度值（MT/s）
    """
    if not speed:
        return 0

    text = str(speed).strip().upper()

    # 提取数字
    numbers = re.findall(r"\d+", text)
    if not numbers:
        return 0

    # 通常第一个或第二个数字是速度
    for num in numbers:
        value = int(num)
        # 合理的内存速度范围
        if 800 <= value <= 12800:
            return value

    return 0


def normalize_storage_capacity(capacity: Any) -> float:
    """
    标准化存储容量（GB）

    Args:
        capacity: 容量值，可能是 "1TB" 或 "500GB" 等格式

    Returns:
        标准化的容量值（GB）
    """
    if not capacity:
        return 0.0

    try:
        if isinstance(capacity, (int, float)):
            return float(capacity)

        text = str(capacity).strip().upper()

        # 提取数值和单位
        match = re.search(r"([\d.]+)\s*(TB|GB|MB)", text)
        if not match:
            # 尝试直接提取数字
            numbers = re.findall(r"[\d.]+", text)
            if numbers:
                return float(numbers[0])
            return 0.0

        value = float(match.group(1))
        unit = match.group(2)

        # 转换为 GB
        if unit == "TB":
            return value * 1024
        elif unit == "MB":
            return value / 1024
        else:
            return value
    except (ValueError, TypeError):
        return 0.0


def normalize_gpu_memory(memory: Any) -> float:
    """
    标准化显存容量（GB）

    Args:
        memory: 显存容量

    Returns:
        标准化的显存容量（GB）
    """
    if not memory:
        return 0.0

    try:
        if isinstance(memory, (int, float)):
            return float(memory)

        text = str(memory).strip().upper()
        # 提取数字
        match = re.search(r"([\d.]+)", text)
        if match:
            return float(match.group(1))
        return 0.0
    except (ValueError, TypeError):
        return 0.0


def parse_module_spec(value: Any) -> tuple:
    """
    解析内存模块规格

    Args:
        value: 规格字符串，如 "2,16" 表示 2 条 16GB

    Returns:
        (数量，单条容量) 元组
    """
    if not value:
        return (0, 0.0)

    try:
        text = str(value).replace(" ", "")
        parts = text.split(",")
        if len(parts) >= 2:
            count = int(parts[0])
            size = float(parts[1])
            return (count, size)
        return (0, 0.0)
    except (ValueError, TypeError):
        return (0, 0.0)


def extract_clock_speed(value: Any) -> float:
    """
    提取时钟频率（MHz）

    Args:
        value: 频率值，可能是 "3.5GHz" 或 "3500MHz" 等格式

    Returns:
        标准化的频率值（MHz）
    """
    if not value:
        return 0.0

    try:
        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip().upper()

        # 提取数字
        numbers = re.findall(r"[\d.]+", text)
        if not numbers:
            return 0.0

        value = float(numbers[0])

        # 判断单位
        if "GHZ" in text:
            return value * 1000  # GHz 转 MHz
        elif "MHZ" in text:
            return value
        else:
            # 假设是 MHz（对于现代 CPU/GPU）
            return value
    except (ValueError, TypeError):
        return 0.0
