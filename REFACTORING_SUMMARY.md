# Recommender 模块重构总结

## 重构概述

本次重构全面升级了推荐系统模块，引入了机器学习基础、灵活的配置模式和完善的兼容性检查。

## 新增文件结构

```
pc_configuration/apps/recommender/
├── models.py                    # 新增：数据模型（历史记录、用户偏好、特征缓存）
├── forms.py                     # 新增：Django 表单验证
├── core/
│   ├── config.py               # 新增：推荐策略配置管理
│   ├── engine.py               # 重构：推荐引擎核心
│   ├── selection.py            # 重构：配件选择策略
│   ├── compatibility.py        # 重构：兼容性检查（扩展）
│   └── filters.py              # 重构：配件过滤器
├── algorithms/                  # 新增：算法模块
│   ├── __init__.py
│   ├── scoring.py              # 多维度评分系统
│   ├── feature_engineering.py  # 特征工程
│   ├── content_based.py        # 基于内容的推荐
│   └── collaborative.py        # 协同过滤（预留接口）
├── utils/                       # 新增：工具函数
│   ├── __init__.py
│   ├── normalizer.py           # 数据标准化
│   └── logger.py               # 日志配置
└── templates/recommender/
    └── index.html               # 重构：增强前端展示
```

## 核心改进

### 1. 数据标准化 (utils/normalizer.py)
- 统一的功率、尺寸、速度等数据解析
- 支持多种格式的输入（如 "DDR4-3200", "3200MHz"）
- 容量单位自动转换（TB/GB/MB）

### 2. 多维度评分系统 (algorithms/scoring.py)
**修复的 Bug:**
- ✅ 正则表达式错误：`r"\\d+"` → `r"\d+"`

**新增评分维度:**
- 性能评分：基于硬件规格和架构代数
- 能效评分：性能/功耗比
- 性价比评分：性能/价格比
- 品牌溢价因子

**评分特点:**
- CPU: 考虑核心数、频率、架构、TDP
- GPU: 考虑显存、频率、架构
- 内存：考虑速度、容量、延迟
- 存储：区分 SSD/HDD/NVMe
- 电源：考虑能效等级、模块化
- 散热器：考虑尺寸、转速、噪音

### 3. 特征工程 (algorithms/feature_engineering.py)
为每个配件提取特征向量，用于机器学习：
- CPU: [核心数，频率，TDP, 架构代数，是否有集显]
- GPU: [显存，频率，架构代数，长度]
- 主板：[插槽类型，板型，最大内存，槽位数]
- 等等...

### 4. 灵活配置模式 (core/config.py)
**预算分配权重:**
```python
BUDGET_WEIGHTS = {
    "value": {"cpu": 0.25, "gpu": 0.30, ...},
    "balanced": {"cpu": 0.30, "gpu": 0.35, ...},
    "performance": {"cpu": 0.35, "gpu": 0.40, ...},
}
```

**优先级模式:**
- `auto`: 自动平衡
- `cpu`: CPU 优先（增加 CPU 预算权重）
- `gpu`: 显卡优先
- `storage`: 存储优先

**用途权重:**
- 游戏：GPU 权重 1.4，CPU 权重 0.85
- 办公：GPU 权重 0.5，CPU 权重 0.8
- 生产力：CPU 权重 1.3，内存权重 1.3

### 5. 推荐引擎增强 (core/engine.py)
**主要改进:**
- 动态预算分配（根据优先级调整）
- 加权评分选择（用途权重 * 性能评分）
- 推荐理由生成
- 详细的日志记录
- 异常处理和容错

**算法流程:**
1. 预筛选 Top 30 CPU/GPU
2. 计算其他配件最低成本
3. 寻找最佳 CPU+GPU 组合（考虑用途权重）
4. 动态分配剩余预算
5. 选择其他配件
6. 电源匹配（含 30% 冗余）
7. 兼容性检查
8. 生成推荐理由

### 6. 扩展兼容性检查 (core/compatibility.py)
**新增检查项:**
- CPU-主板插槽扩展验证
- 显卡长度 vs 机箱限长
- 散热器尺寸 vs CPU TDP
- 存储接口兼容性
- 内存与散热器间隙（预留）

**原有检查保留:**
- CPU-主板插槽匹配
- 内存-主板兼容性
- 机箱 - 主板板型匹配
- 电源功率充足性
- 机箱硬盘位检查

### 7. 表单验证 (forms.py)
**新增字段:**
- `priority_mode`: 优先级选择
- 预算范围验证（1000-50000 元）
- 最小值不能大于最大值
- 完整的表单清理和错误提示

### 8. 数据模型 (models.py)
**新增模型:**
- `RecommendationHistory`: 记录每次推荐
- `UserPreference`: 存储用户偏好
- `ComponentFeature`: 配件特征缓存（用于加速）

### 9. 前端增强 (templates/index.html)
**新增展示:**
- ✅ 推荐理由列表
- ✅ 兼容性问题提示
- ✅ 优先级选择器
- ✅ 更强的视觉层次

## 技术亮点

### 代码质量
- ✅ 完整的类型注解
- ✅ 详细的文档字符串
- ✅ 模块化设计
- ✅ 单一职责原则
- ✅ 日志记录

### 性能优化
- 候选集剪枝（只考虑 Top 30）
- 预计算最低成本
- 早期跳过超出预算的组合
- QuerySet 优化（待实现 select_related）

### 可扩展性
- 插件化的评分函数
- 可配置的权重系统
- 预留机器学习接口
- 支持新的配件类型

## 向后兼容性

保持了与现有系统的兼容：
- 保留了原有的 `build_recommendation` 函数签名（添加可选参数）
- 兼容现有的 pc_builder.models
- 模板保持基本结构不变

## 使用示例

### 基础使用
```python
from recommender.core.engine import build_recommendation

result = build_recommendation(
    profile="balanced",
    usage="gaming",
    budget_min=5000,
    budget_max=8000,
    cpu_qs=Cpu.objects.all(),
    gpu_qs=Gpu.objects.all(),
    # ... 其他参数
    priority_mode="auto",
)
```

### 自定义优先级
```python
# CPU 优先的游戏配置
result = build_recommendation(
    profile="performance",
    usage="gaming",
    budget_min=8000,
    budget_max=12000,
    priority_mode="cpu",  # CPU 优先
    # ...
)
```

## 下一步工作

### Task 7: 测试
- [ ] 单元测试（scoring, compatibility, filters）
- [ ] 集成测试（完整推荐流程）
- [ ] 边界条件测试（极低/极高预算）
- [ ] 性能测试（响应时间 < 2 秒）

### Task 8: 部署
- [ ] 数据库迁移：`python manage.py migrate recommender`
- [ ] 特征数据预计算脚本
- [ ] 监控和日志配置
- [ ] 性能调优

### 未来扩展
- [ ] 协同过滤实现（需要用户数据积累）
- [ ] A/B 测试框架
- [ ] 推荐效果评估
- [ ] 实时特征更新
- [ ] 更多兼容性检查规则

## 已知问题

1. **数据质量问题**: 现有 CSV 数据可能存在噪声或不一致
   - 解决：数据清洗脚本（待开发）

2. **算法调优**: 评分权重需要实际测试调整
   - 解决：收集用户反馈，迭代优化

3. **缺失数据**: 部分配件缺少关键属性（如机箱 GPU 限长）
   - 解决：数据补充或使用估算值

## 总结

本次重构实现了：
- ✅ 全面的算法升级（多维度评分、特征工程）
- ✅ 灵活的配置模式（优先级、用途权重）
- ✅ 完善的兼容性检查（6+ 项验证）
- ✅ 清晰的代码结构（模块化、类型注解）
- ✅ 良好的用户体验（推荐理由、错误提示）

重构后的系统更加智能、灵活和可维护，为未来的机器学习升级奠定了坚实基础。
