"""
推荐系统表单模块

提供用户输入验证和表单处理
"""

from django import forms


class RecommendationForm(forms.Form):
    """推荐请求表单"""

    BUDGET_MIN = 1000.0
    BUDGET_MAX = 50000.0

    # 预算范围
    budget_min = forms.FloatField(
        min_value=0,
        max_value=BUDGET_MAX,
        required=True,
        label="最低预算（元）",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "placeholder": f"最小值 {BUDGET_MIN}",
                "min": 0,
                "step": 100,
            }
        ),
    )

    budget_max = forms.FloatField(
        min_value=0,
        max_value=BUDGET_MAX,
        required=True,
        label="最高预算（元）",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "placeholder": f"最大值 {BUDGET_MAX}",
                "min": 0,
                "step": 100,
            }
        ),
    )

    # 用途选择
    USAGE_CHOICES = [
        ("gaming", "游戏"),
        ("office", "办公"),
        ("productivity", "生产力"),
    ]

    usage = forms.ChoiceField(
        choices=USAGE_CHOICES,
        required=True,
        label="主要用途",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    # 品牌偏好
    CPU_BRAND_CHOICES = [
        ("any", "不限"),
        ("intel", "Intel"),
        ("amd", "AMD"),
    ]

    cpu_brand = forms.ChoiceField(
        choices=CPU_BRAND_CHOICES,
        required=False,
        label="CPU 品牌偏好",
        initial="any",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    GPU_BRAND_CHOICES = [
        ("any", "不限"),
        ("nvidia", "NVIDIA"),
        ("amd", "AMD"),
    ]

    gpu_brand = forms.ChoiceField(
        choices=GPU_BRAND_CHOICES,
        required=False,
        label="显卡品牌偏好",
        initial="any",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    # 优先级模式
    PRIORITY_CHOICES = [
        ("auto", "自动平衡"),
        ("cpu", "CPU 优先"),
        ("gpu", "显卡优先"),
        ("storage", "存储优先"),
    ]

    priority_mode = forms.ChoiceField(
        choices=PRIORITY_CHOICES,
        required=False,
        label="配置优先级",
        initial="auto",
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
    )

    def clean(self):
        """表单验证"""
        cleaned_data = super().clean()

        budget_min = cleaned_data.get("budget_min")
        budget_max = cleaned_data.get("budget_max")

        if budget_min is not None and budget_max is not None:
            # 确保最小值小于最大值
            if budget_min > budget_max:
                raise forms.ValidationError("最低预算不能高于最高预算")

            # 确保预算在合理范围内
            if budget_min < self.BUDGET_MIN:
                raise forms.ValidationError(f"最低预算不能低于￥{self.BUDGET_MIN}")

            if budget_max > self.BUDGET_MAX:
                raise forms.ValidationError(f"最高预算不能高于￥{self.BUDGET_MAX}")

        return cleaned_data
