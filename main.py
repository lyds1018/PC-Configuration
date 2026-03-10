import os
from recommend.core.data_loader import load_data
from recommend.core.budget_allocator import allocate_budget
from recommend.core.selector import select_best

data_path = "data/processed/"
budget = int(input("请输入预算: "))

budgets = allocate_budget(budget)

cpu_data = load_data(os.path.join(data_path, "cpu.csv"))
gpu_data = load_data(os.path.join(data_path, "gpu.csv"))

cpu = select_best(cpu_data, budgets["cpu"])
gpu = select_best(gpu_data, budgets["gpu"])

print("推荐配置")
print("CPU:", cpu["name"])
print("GPU:", gpu["name"])