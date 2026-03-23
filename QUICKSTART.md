# Recommender 重构 - 快速开始指南

## 部署步骤

### 1. 应用数据库迁移

```bash
cd d:/PC-Configuration
uv run python manage.py makemigrations recommender
uv run python manage.py migrate recommender
```

### 2. 收集静态文件（如果需要）

```bash
uv run python manage.py collectstatic
```

### 3. 测试运行

```bash
uv run python manage.py runserver
```

访问 `http://localhost:8000/recommender/` 查看推荐页面。

## 主要变更

### 新增功能

1. **优先级选择器**
   - 自动平衡
   - CPU 优先
   - 显卡优先
   - 存储优先

2. **推荐理由**
   - 每个方案都会显示推荐理由
   - 包括性能分析、能效评价等

3. **兼容性提示**
   - 发现兼容性问题时会显示警告
   - 帮助用户避免购买不兼容的配件

4. **表单验证**
   - 预算范围验证（1000-50000 元）
   - 输入合法性检查
   - 友好的错误提示

### API 变更

#### 原函数签名（保持不变，添加可选参数）
```python
def build_recommendation(
    profile: str,           # 'value', 'balanced', 'performance'
    usage: str,             # 'gaming', 'office', 'productivity'
    budget_min: float,
    budget_max: float,
    cpu_qs: QuerySet,
    gpu_qs: QuerySet,
    ram_qs: QuerySet,
    storage_qs: QuerySet,
    mb_qs: QuerySet,
    psu_qs: QuerySet,
    case_qs: QuerySet,
    cooler_qs: QuerySet,
    priority_mode: str = "auto",  # 新增
) -> Optional[Dict]
```

#### 返回结果增强
```python
{
    "profile": "均衡方案",
    "total": 8999.0,
    "estimated_watt": 550,
    "compatibility": {"ok": True, "issues": []},
    "items": {...},  # 配件字典
    "scores": {       # 新增：详细评分
        "cpu_score": 3500.5,
        "gpu_score": 4200.8,
        "cpu_efficiency": 75.3,
        "gpu_efficiency": 82.1,
        "cpu_value": 68.5,
        "gpu_value": 72.3,
    },
    "reasons": [      # 新增：推荐理由
        "显卡性能强劲，适合游戏需求（GPU 评分：4201）",
        "平衡性能和价格，适合大多数用户",
        "配件能效表现良好",
    ],
    "budget_weights": {  # 新增：预算分配权重
        "cpu": 0.30,
        "gpu": 0.35,
        ...
    }
}
```

## 配置选项

### 预算分配策略 (core/config.py)

可以自定义预算分配比例：

```python
BUDGET_WEIGHTS = {
    "value": {
        "cpu": 0.25,      # CPU 占 25%
        "gpu": 0.30,      # GPU 占 30%
        "mb": 0.12,       # 主板占 12%
        ...
    },
    # ... 其他方案
}
```

### 用途权重

可以自定义不同用途的评分权重：

```python
USAGE_WEIGHTS = {
    "gaming": {
        "cpu": 0.85,      # 游戏 CPU 权重
        "gpu": 1.40,      # 游戏 GPU 权重 +40%
        ...
    },
    ...
}
```

## 数据质量要求

确保 CSV 数据包含以下字段：

### CPU (cpu.csv)
- `name`: 产品名称
- `price`: 价格
- `core_count`: 核心数
- `core_clock`: 基准频率 (MHz)
- `boost_clock`: 加速频率 (MHz)
- `microarchitecture`: 微架构
- `tdp`: 热设计功耗 (W)
- `graphics`: 是否有集成显卡

### GPU (gpu.csv)
- `name`: 产品名称
- `price`: 价格
- `chipset`: 芯片组
- `memory`: 显存 (GB)
- `core_clock`: 核心频率 (MHz)
- `boost_clock`: 加速频率 (MHz)
- `length`: 长度 (mm)

### 其他配件
参考 `data/csv/processed/` 目录中的现有格式。

## 故障排除

### 问题：推荐结果为空

**可能原因:**
1. 预算过低（低于 1000 元）
2. 品牌限制过严
3. 数据质量问题

**解决方法:**
- 提高预算范围
- 放宽品牌限制
- 检查 CSV 数据完整性

### 问题：兼容性警告过多

**可能原因:**
- 某些配件缺少关键属性
- 数据格式不一致

**解决方法:**
- 检查并补充缺失数据
- 统一数据格式

### 问题：响应时间过长

**可能原因:**
- 候选集过大
- 数据库查询未优化

**解决方法:**
- 使用数据库索引
- 实现特征缓存（ComponentFeature 模型）
- 添加 select_related/prefetch_related

## 扩展开发

### 添加新的评分维度

在 `algorithms/scoring.py` 中添加：

```python
def new_score(component) -> float:
    """新的评分维度"""
    # 实现评分逻辑
    return score
```

### 添加新的兼容性检查

在 `core/compatibility.py` 中添加：

```python
def check_new_compatibility(parts: Dict) -> List[str]:
    """新的兼容性检查"""
    issues = []
    # 实现检查逻辑
    return issues
```

然后在 `check_compatibility()` 中调用。

### 添加新的推荐策略

在 `core/config.py` 中添加：

```python
NEW_PROFILE_WEIGHTS = {
    "new_profile": {
        "cpu": 0.40,
        "gpu": 0.35,
        ...
    },
}
```

## 性能优化建议

1. **启用特征缓存**
   ```python
   # 预计算配件特征
   from recommender.algorithms.feature_engineering import extract_cpu_features
   
   for cpu in Cpu.objects.all():
       features = extract_cpu_features(cpu)
       ComponentFeature.objects.create(
           component_type="cpu",
           component_id=cpu.id,
           features=features,
           ...
       )
   ```

2. **数据库查询优化**
   ```python
   # 使用 select_related 减少查询次数
   cpu_qs = Cpu.objects.select_related().all()
   ```

3. **添加索引**
   ```python
   # 在 models.py 中为常用查询字段添加索引
   class Meta:
       indexes = [
           models.Index(fields=['price']),
           models.Index(fields=['core_count']),
       ]
   ```

## 监控和维护

### 日志记录

系统会自动记录：
- 推荐请求参数
- 生成的方案数量
- 兼容性检查结果
- 错误和异常

查看日志：
```bash
# Django 开发服务器日志
tail -f logs/django.log
```

### 推荐效果追踪

使用 `RecommendationHistory` 模型：
```python
from recommender.models import RecommendationHistory

# 查看最近的推荐
history = RecommendationHistory.objects.all()[:10]

# 统计最受欢迎的方案
from django.db.models import Count
stats = RecommendationHistory.objects.values('selected_profile').annotate(count=Count('id'))
```

## 常见问题 FAQ

**Q: 为什么有些方案没有生成？**
A: 可能是因为预算不足、兼容性问题或数据缺失。检查日志获取详细原因。

**Q: 如何调整推荐算法？**
A: 修改 `algorithms/scoring.py` 中的评分函数或 `core/config.py` 中的权重配置。

**Q: 支持自定义用途吗？**
A: 是的，在 `core/config.py` 的 `USAGE_WEIGHTS` 中添加新的用途配置即可。

**Q: 如何添加新的配件类型？**
A: 
1. 在 `pc_builder/models.py` 中添加模型
2. 在 `algorithms/feature_engineering.py` 中添加特征提取
3. 在 `algorithms/scoring.py` 中添加评分函数
4. 更新推荐引擎和模板

## 联系和支持

如有问题或建议，请参考：
- 完整文档：`REFACTORING_SUMMARY.md`
- 源代码注释
- Django 官方文档

---

**版本**: 2.0  
**更新日期**: 2026-03-23  
**维护者**: PC Configuration Team
