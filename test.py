import pandas as pd

# -----------------------
# CPU 数据
# -----------------------
cpu_data = [
    ["Ryzen 5 5600", 6, 12, 22000, 850, "AM4"],
    ["Ryzen 5 7600", 6, 12, 28000, 1600, "AM5"],
    ["Ryzen 7 7700X", 8, 16, 35000, 2600, "AM5"],
    ["i5-12400F", 6, 12, 24000, 1200, "LGA1700"],
    ["i5-13400F", 10, 16, 30000, 1700, "LGA1700"],
]

cpu_columns = ["name", "cores", "threads", "score", "price", "socket"]
pd.DataFrame(cpu_data, columns=cpu_columns).to_csv("data/processed/cpu.csv", index=False)

# -----------------------
# GPU 数据
# -----------------------
gpu_data = [
    ["GTX 1660 Super", 6, 14000, 1600],
    ["RTX 3060", 12, 17000, 2400],
    ["RTX 4060", 8, 18000, 2600],
    ["RTX 4070", 12, 26000, 4500],
    ["RX 7600", 8, 17000, 2200],
    ["RX 7800XT", 16, 30000, 4800],
]

gpu_columns = ["name", "vram", "score", "price"]
pd.DataFrame(gpu_data, columns=gpu_columns).to_csv("data/processed/gpu.csv", index=False)

# -----------------------
# RAM 数据
# -----------------------
ram_data = [
    ["16GB DDR4", 16, "DDR4", 8000, 300],
    ["32GB DDR4", 32, "DDR4", 9000, 550],
    ["16GB DDR5", 16, "DDR5", 10000, 450],
    ["32GB DDR5", 32, "DDR5", 11000, 800],
]

ram_columns = ["name", "capacity", "type", "score", "price"]
pd.DataFrame(ram_data, columns=ram_columns).to_csv("data/processed/ram.csv", index=False)

# -----------------------
# SSD 数据
# -----------------------
ssd_data = [
    ["512GB SATA", 512, "SATA", 4000, 200],
    ["1TB SATA", 1024, "SATA", 4500, 350],
    ["1TB NVMe", 1024, "NVMe", 7000, 450],
    ["2TB NVMe", 2048, "NVMe", 9000, 800],
]

ssd_columns = ["name", "capacity", "type", "score", "price"]
pd.DataFrame(ssd_data, columns=ssd_columns).to_csv("data/processed/ssd.csv", index=False)

# -----------------------
# 主板数据
# -----------------------
motherboard_data = [
    ["B450", "AM4", "DDR4", 5000, 500],
    ["B550", "AM4", "DDR4", 6000, 700],
    ["B650", "AM5", "DDR5", 7000, 1200],
    ["B660", "LGA1700", "DDR4", 6500, 900],
    ["Z690", "LGA1700", "DDR5", 8000, 1600],
]

motherboard_columns = ["name", "socket", "ram_type", "score", "price"]
pd.DataFrame(motherboard_data, columns=motherboard_columns).to_csv("data/processed/motherboard.csv", index=False)

print("测试数据 CSV 文件生成完成！")