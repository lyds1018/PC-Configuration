"""推荐模块工具函数与常量"""

import math
from dataclasses import dataclass
from typing import Dict, List, Mapping

from compatibility import run_checks

# 组合枚举常量
MAX_CANDIDATES = 8000
OUTPUT_CANDIDATES = 12

# 应用场景常量
WORKLOAD_GAME = "game"
WORKLOAD_OFFICE = "office"
WORKLOAD_PRODUCTIVITY = "productivity"
WORKLOAD_ALIASES = {
    "game": WORKLOAD_GAME,
    "office": WORKLOAD_OFFICE,
    "productivity": WORKLOAD_PRODUCTIVITY,
    "游戏": WORKLOAD_GAME,
    "办公": WORKLOAD_OFFICE,
    "生产力": WORKLOAD_PRODUCTIVITY,
}

# 配件子权重
SUB_WEIGHTS = {
    WORKLOAD_GAME: {
        "cpu": {
            "single_score": 0.35,
            "multi_score": 0.15,
            "bb": 0.25,
            "ct": 0.10,
            "tdp": 0.15,
        },
        "gpu": {
            "gaming_score": 0.50,
            "compute_score": 0.10,
            "cm": 0.20,
            "vram_size": 0.10,
            "tdp": 0.10,
        },
        "ram": {"capacity": 0.50, "fl": 0.50},
        "storage": {"capacity": 0.20, "cache_size": 0.10, "sp": 0.50, "rand": 0.20},
    },
    WORKLOAD_OFFICE: {
        "cpu": {
            "single_score": 0.30,
            "multi_score": 0.25,
            "bb": 0.20,
            "ct": 0.15,
            "tdp": 0.10,
        },
        "gpu": {
            "gaming_score": 0.10,
            "compute_score": 0.20,
            "cm": 0.20,
            "vram_size": 0.20,
            "tdp": 0.30,
        },
        "ram": {"capacity": 0.60, "fl": 0.40},
        "storage": {"capacity": 0.30, "cache_size": 0.10, "sp": 0.30, "rand": 0.30},
    },
    WORKLOAD_PRODUCTIVITY: {
        "cpu": {
            "single_score": 0.15,
            "multi_score": 0.40,
            "bb": 0.10,
            "ct": 0.25,
            "tdp": 0.10,
        },
        "gpu": {
            "gaming_score": 0.10,
            "compute_score": 0.45,
            "cm": 0.15,
            "vram_size": 0.20,
            "tdp": 0.10,
        },
        "ram": {"capacity": 0.70, "fl": 0.30},
        "storage": {"capacity": 0.25, "cache_size": 0.15, "sp": 0.25, "rand": 0.35},
    },
}

# 配件权重
TOTAL_WEIGHTS = {
    WORKLOAD_GAME: {"cpu": 0.25, "gpu": 0.50, "ram": 0.15, "storage": 0.10},
    WORKLOAD_OFFICE: {"cpu": 0.40, "gpu": 0.10, "ram": 0.30, "storage": 0.20},
    WORKLOAD_PRODUCTIVITY: {"cpu": 0.35, "gpu": 0.30, "ram": 0.20, "storage": 0.15},
}

# 页面渲染常量
CPU_BRAND_OPTIONS = ["AMD", "Intel"]
GPU_CHIP_BRAND_OPTIONS = ["AMD", "NVIDIA"]
EMPTY_REASON = "—"

# 智能体配置常量
MODEL = "deepseek-v4-flash"
BASE_URL = "https://api.deepseek.com"
TEMPERATURE = 0.8
THINKING_TYPE = "disabled"
API_KEY_ENV_VAR = "DEEPSEEK_API_KEY"
AGENT_TIMEOUT_SECONDS = 15.0


# 推荐请求参数类
@dataclass
class RecommendationRequest:
    budget_min: float = 0.0
    budget_max: float = 0.0
    workload: str = WORKLOAD_GAME
    cpu_brand: str = ""
    gpu_chip_brand: str = ""
    gpu_card_brand: str = ""
    free_text: str = ""
    top_k: int = 3


# 边界类
@dataclass(frozen=True)
class MinMax:
    min_value: float
    max_value: float


# 整机边界类
@dataclass(frozen=True)
class ALLBounds:
    cpu: Dict[str, MinMax]  # 多字段边界
    gpu: Dict[str, MinMax]
    ram: Dict[str, MinMax]
    storage: Dict[str, MinMax]
    cpu_ee: MinMax
    gpu_ee: MinMax


def to_int(value, default=0):
    """转整数，失败时返回0。"""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def to_float(value, default=0.0):
    """转浮点数，失败时返回0.0。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_log(value: float) -> float:
    """转对数，输入非正数时返回0.0。"""
    if value <= 0:
        return 0.0
    return math.log(value)


def linear_norm(value: float, bounds: MinMax) -> float:
    """线性归一化"""
    denom = bounds.max_value - bounds.min_value
    if denom <= 0:
        return 0.0
    return (value - bounds.min_value) / denom


def positive_log_norm(value: float, bounds: MinMax) -> float:
    """对数归一化"""
    span = bounds.max_value - bounds.min_value
    if span <= 0:
        return 0.0
    numerator = to_log(value - bounds.min_value + 1.0)
    denominator = to_log(span + 1.0)
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def normalize_brand(value: str) -> str:
    """品牌名称转统一格式"""
    text = (value or "").strip()
    if not text:
        return ""
    upper = text.upper()
    if upper in {"INTEL", "英特尔"}:
        return "英特尔"
    if upper in {"AMD"}:
        return "AMD"
    if upper in {"NVIDIA", "英伟达"}:
        return "NVIDIA"
    return text


def normalize_budget_range(params: RecommendationRequest) -> tuple[float, float]:
    """确保预算范围有效。"""
    budget_min = max(0.0, to_float(params.budget_min, 0.0))
    budget_max = max(0.0, to_float(params.budget_max, 0.0))
    if budget_min > budget_max:
        budget_min, budget_max = budget_max, budget_min
    return budget_min, budget_max


def part_price(part) -> float:
    """读取单个配件价格，失败时返回0.0。"""
    return to_float(getattr(part, "price", 0.0), 0.0)


def sum_price(parts: List[object]) -> float:
    """计算配件列表总价。"""
    return sum(part_price(p) for p in parts if p is not None)


def min_price(parts: Mapping[str, List[object]], key: str) -> float:
    """计算配件列表中指定类别的最低价。"""
    values = [part_price(item) for item in parts.get(key, [])]
    return min(values) if values else 0.0


def max_price(parts: Mapping[str, List[object]], key: str) -> float:
    """计算配件列表中指定类别的最高价。"""
    values = [part_price(item) for item in parts.get(key, [])]
    return max(values) if values else 0.0


def scale_0_100(value: float) -> float:
    """将 0-1 映射到 0-100。"""
    return max(0.0, min(100.0, value * 100.0))


def to_score_dict(obj) -> Dict[str, float]:
    """将配件对象的性能字段转换为统一的评分字典。"""
    fields = [
        "single_score",
        "multi_score",
        "base_clock",
        "boost_clock",
        "core_count",
        "thread_count",
        "tdp",
        "gaming_score",
        "compute_score",
        "core_clock",
        "memory_clock",
        "vram_size",
        "capacity",
        "frequency",
        "latency",
        "cache_size",
        "read_speed",
        "write_speed",
        "random_read_iops",
        "random_write_iops",
    ]

    return {field: to_float(getattr(obj, field, 0.0), 0.0) for field in fields}


def is_compatible(parts: Mapping[str, object]) -> bool:
    """调用兼容性检查，返回是否通过。"""
    return run_checks(dict(parts)).get("ok", False)
