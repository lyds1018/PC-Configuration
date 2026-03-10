import os

from recommend.core.budget_allocator import allocate_budget
from recommend.core.score_weight import get_score_weights
from recommend.core.config_generator import generate_configs
from recommend.core.data_loader import load_data

data_path = "data/processed/"
total_budget = int(input("请输入预算: "))
build_type = input("请输入用途 (gaming/office/workstation): ")

budgets = allocate_budget(total_budget, build_type)
score_weights = get_score_weights(build_type)

cpu_data = load_data(os.path.join(data_path, "cpu.csv"))
gpu_data = load_data(os.path.join(data_path, "gpu.csv"))
ram_data = load_data(os.path.join(data_path, "ram.csv"))
mb_data = load_data(os.path.join(data_path, "mainboard.csv"))
ssd_data = load_data(os.path.join(data_path, "ssd.csv"))
psu_data = load_data(os.path.join(data_path, "psu.csv"))
case_data = load_data(os.path.join(data_path, "case.csv"))

configs = generate_configs(
    cpu_data,
    mb_data,
    ram_data,
    gpu_data,
    case_data,
    psu_data,
    ssd_data,
    score_weights,
    budgets,
    total_budget=total_budget,
)

# 输出前3个配置
for i, config in enumerate(configs[:3]):
    print(f"配置 {i+1}:")
    print(f"  CPU: {config['cpu']['name']} - ${config['cpu']['price']}")
    print(f"  主板: {config['mainboard']['name']} - ${config['mainboard']['price']}")
    print(f"  内存: {config['ram']['name']} - ${config['ram']['price']}")
    print(f"  显卡: {config['gpu']['name']} - ${config['gpu']['price']}")
    print(f"  存储: {config['ssd']['name']} - ${config['ssd']['price']}")
    print(f"  电源: {config['psu']['name']} - ${config['psu']['price']}")
    print(f"  机箱: {config['case']['name']} - ${config['case']['price']}")
    print(f"  总价: ${config['total_price']:.2f}")
    print(f"  综合评分: {config['total_score']:.4f}")
    print("-" * 40)
