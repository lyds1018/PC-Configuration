"""Recommender 应用的数据模型"""

from django.contrib.auth.models import User
from django.db import models


class RecommendationHistory(models.Model):
    """推荐历史记录"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    # 用户输入参数
    budget_min = models.FloatField(verbose_name="最低预算")
    budget_max = models.FloatField(verbose_name="最高预算")
    usage = models.CharField(max_length=20, verbose_name="用途")
    cpu_brand = models.CharField(max_length=10, verbose_name="CPU 品牌")
    gpu_brand = models.CharField(max_length=10, verbose_name="显卡品牌")
    priority_mode = models.CharField(
        max_length=20, default="auto", verbose_name="优先级模式"
    )

    # 推荐结果摘要
    selected_profile = models.CharField(max_length=20, verbose_name="选择的方案")
    total_price = models.FloatField(verbose_name="总价")
    estimated_wattage = models.FloatField(verbose_name="预计功耗")

    class Meta:
        db_table = "recommender_history"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.selected_profile} - ￥{self.total_price}"


class UserPreference(models.Model):
    """用户偏好设置"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="用户")

    # 品牌偏好
    preferred_cpu_brand = models.CharField(
        max_length=10, blank=True, verbose_name="偏好 CPU 品牌"
    )
    preferred_gpu_brand = models.CharField(
        max_length=10, blank=True, verbose_name="偏好显卡品牌"
    )

    # 性能偏好
    performance_priority = models.CharField(
        max_length=20,
        default="balanced",
        choices=[
            ("cpu", "CPU 优先"),
            ("gpu", "显卡优先"),
            ("balanced", "平衡"),
            ("storage", "存储优先"),
        ],
        verbose_name="性能优先级",
    )

    # 其他偏好
    prefer_rgb = models.BooleanField(default=False, verbose_name="偏好 RGB")
    prefer_silent = models.BooleanField(default=False, verbose_name="偏好静音")
    min_efficiency = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ("bronze", "铜牌及以上"),
            ("gold", "金牌及以上"),
            ("platinum", "白金牌及以上"),
        ],
        verbose_name="最低能效等级",
    )

    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "recommender_user_preference"

    def __str__(self):
        return f"{self.user.username} 的偏好设置"


class ComponentFeature(models.Model):
    """配件特征缓存 - 用于加速推荐计算"""

    COMPONENT_TYPES = [
        ("cpu", "CPU"),
        ("gpu", "显卡"),
        ("mb", "主板"),
        ("ram", "内存"),
        ("storage", "存储"),
        ("psu", "电源"),
        ("case", "机箱"),
        ("cooler", "散热器"),
    ]

    component_type = models.CharField(
        max_length=20, choices=COMPONENT_TYPES, verbose_name="配件类型"
    )
    component_id = models.IntegerField(verbose_name="配件 ID")

    # 特征向量（JSON 格式存储）
    features = models.JSONField(default=dict, verbose_name="特征向量")

    # 预计算的评分
    gaming_score = models.FloatField(default=0.0, verbose_name="游戏评分")
    office_score = models.FloatField(default=0.0, verbose_name="办公评分")
    productivity_score = models.FloatField(default=0.0, verbose_name="生产力评分")

    # 能效评分
    efficiency_score = models.FloatField(default=0.0, verbose_name="能效评分")

    # 性价比评分
    value_score = models.FloatField(default=0.0, verbose_name="性价比评分")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "recommender_component_feature"
        unique_together = ["component_type", "component_id"]
        indexes = [
            models.Index(fields=["component_type"]),
            models.Index(fields=["gaming_score"]),
            models.Index(fields=["value_score"]),
        ]

    def __str__(self):
        return f"{self.get_component_type_display()} #{self.component_id}"
