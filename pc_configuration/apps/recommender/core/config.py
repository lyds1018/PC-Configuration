"""
推荐配置管理

集中管理推荐策略、预算分配、用途权重等配置
"""

from typing import Dict

# ============================================
# 预算分配策略
# ============================================
BUDGET_WEIGHTS = {
    # 性价比方案：更注重价格控制
    "value": {
        "cpu": 0.25,
        "gpu": 0.30,
        "mb": 0.12,
        "ram": 0.10,
        "storage": 0.08,
        "psu": 0.07,
        "case": 0.05,
        "cooler": 0.03,
    },
    # 均衡方案：各方面平衡
    "balanced": {
        "cpu": 0.30,
        "gpu": 0.35,
        "mb": 0.10,
        "ram": 0.08,
        "storage": 0.07,
        "psu": 0.06,
        "case": 0.04,
        "cooler": 0.03,
    },
    # 性能方案：追求极致性能
    "performance": {
        "cpu": 0.35,
        "gpu": 0.40,
        "mb": 0.08,
        "ram": 0.06,
        "storage": 0.05,
        "psu": 0.04,
        "case": 0.02,
        "cooler": 0.02,
    },
}


# ============================================
# 用途权重配置
# ============================================
USAGE_WEIGHTS = {
    # 游戏用途：GPU 优先
    "gaming": {
        "cpu": 0.85,
        "gpu": 1.40,
        "ram": 1.00,
        "storage": 0.80,
        "mb": 0.90,
        "psu": 1.00,
        "case": 0.85,
        "cooler": 0.90,
    },
    # 办公用途：够用就好
    "office": {
        "cpu": 0.80,
        "gpu": 0.50,
        "ram": 0.90,
        "storage": 1.00,
        "mb": 0.80,
        "psu": 0.70,
        "case": 0.70,
        "cooler": 0.80,
    },
    # 生产力用途：多核 CPU 和大内存
    "productivity": {
        "cpu": 1.30,
        "gpu": 1.10,
        "ram": 1.30,
        "storage": 1.20,
        "mb": 1.00,
        "psu": 1.10,
        "case": 0.90,
        "cooler": 1.10,
    },
}


# ============================================
# 优先级模式配置
# ============================================
PRIORITY_WEIGHTS = {
    # 自动平衡
    "auto": {
        "cpu": 1.0,
        "gpu": 1.0,
        "ram": 1.0,
        "storage": 1.0,
    },
    # CPU 优先
    "cpu": {
        "cpu": 1.3,
        "gpu": 0.9,
        "ram": 1.0,
        "storage": 0.9,
    },
    # 显卡优先
    "gpu": {
        "cpu": 0.9,
        "gpu": 1.3,
        "ram": 1.0,
        "storage": 0.9,
    },
    # 存储优先
    "storage": {
        "cpu": 0.95,
        "gpu": 0.95,
        "ram": 1.1,
        "storage": 1.3,
    },
}


# ============================================
# 兼容性检查配置
# ============================================
COMPATIBILITY_CONFIG = {
    # PSU 冗余系数
    "psu_safety_margin": 1.3,
    # 机箱兼容容差（mm）
    "case_tolerance_mm": 5,
    # 散热器高度安全余量（mm）
    "cooler_height_margin": 2,
    # 最小 PSU 瓦数
    "min_psu_wattage": 400,
    # 最大 PSU 瓦数（普通家用）
    "max_psu_wattage": 1600,
}


# ============================================
# 评分阈值配置
# ============================================
SCORE_THRESHOLDS = {
    # 最低综合评分（低于此值不推荐）
    "min_component_score": 30.0,
    # 性价比最低评分
    "min_value_score": 40.0,
    # 能效最低评分
    "min_efficiency_score": 50.0,
}


# ============================================
# 品牌偏好配置
# ============================================
BRAND_TIERS = {
    "cpu": {
        "tier1": ["Intel", "AMD"],
        "tier2": [],
    },
    "gpu": {
        "tier1": ["NVIDIA", "AMD"],
        "tier2": ["ASUS", "MSI", "Gigabyte", "Sapphire"],
    },
    "mb": {
        "tier1": ["ASUS", "MSI", "Gigabyte", "ASRock"],
        "tier2": [],
    },
    "ram": {
        "tier1": ["Corsair", "G.Skill", "Kingston", "Crucial"],
        "tier2": ["TEAMGROUP", "Patriot", "Silicon Power"],
    },
    "psu": {
        "tier1": ["Corsair", "Seasonic", "be quiet!", "EVGA"],
        "tier2": ["MSI", "Cooler Master", "Thermaltake", "Montech"],
    },
}


def get_budget_weights(profile: str, priority_mode: str = "auto") -> Dict[str, float]:
    """
    获取预算分配权重

    Args:
        profile: 方案类型 ('value', 'balanced', 'performance')
        priority_mode: 优先级模式 ('auto', 'cpu', 'gpu', 'storage')

    Returns:
        预算权重字典
    """
    base_weights = BUDGET_WEIGHTS.get(profile, BUDGET_WEIGHTS["balanced"])
    priority_multipliers = PRIORITY_WEIGHTS.get(priority_mode, PRIORITY_WEIGHTS["auto"])

    # 应用优先级乘数
    adjusted_weights = {}
    for key, weight in base_weights.items():
        multiplier = priority_multipliers.get(key, 1.0)
        adjusted_weights[key] = weight * multiplier

    # 归一化，确保总和为 1
    total = sum(adjusted_weights.values())
    if total > 0:
        for key in adjusted_weights:
            adjusted_weights[key] /= total

    return adjusted_weights


def get_usage_weights(usage: str) -> Dict[str, float]:
    """
    获取用途权重

    Args:
        usage: 用途 ('gaming', 'office', 'productivity')

    Returns:
        用途权重字典
    """
    return USAGE_WEIGHTS.get(usage, USAGE_WEIGHTS["office"])


def validate_profile(profile: str) -> bool:
    """验证方案类型是否有效"""
    return profile in BUDGET_WEIGHTS.keys()


def validate_usage(usage: str) -> bool:
    """验证用途是否有效"""
    return usage in USAGE_WEIGHTS.keys()


def validate_priority_mode(mode: str) -> bool:
    """验证优先级模式是否有效"""
    return mode in PRIORITY_WEIGHTS.keys()
