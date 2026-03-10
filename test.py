import os
import pandas as pd

# 创建数据目录
os.makedirs("data", exist_ok=True)

# =========================
# CPU 数据
# =========================
cpu_data = [
    ["Ryzen 5 5600",6,12,"AM4",65,22000,850],
    ["Ryzen 5 7600",6,12,"AM5",65,28000,1600],
    ["Ryzen 7 7700X",8,16,"AM5",105,35000,2600],
    ["i5-12400F",6,12,"LGA1700",65,24000,1200],
    ["i5-13400F",10,16,"LGA1700",65,30000,1700]
]

cpu_columns = [
    "name","cores","threads","socket","tdp","score","price"
]

pd.DataFrame(cpu_data,columns=cpu_columns).to_csv(
    "data/processed/cpu.csv",index=False
)

# =========================
# GPU 数据
# =========================
gpu_data = [
    ["GTX1660 Super",6,140,230,14000,1600],
    ["RTX3060",12,170,242,17000,2400],
    ["RTX4060",8,115,240,18000,2600],
    ["RTX4070",12,200,300,26000,4500],
    ["RX7600",8,165,260,17000,2200],
    ["RX7800XT",16,263,320,30000,4800]
]

gpu_columns = [
    "name","vram","tdp","length","score","price"
]

pd.DataFrame(gpu_data,columns=gpu_columns).to_csv(
    "data/processed/gpu.csv",index=False
)

# =========================
# 主板数据
# =========================
mainboard_data = [
    ["B450","AM4","DDR4","ATX",5000,500],
    ["B550","AM4","DDR4","ATX",6000,700],
    ["B650","AM5","DDR5","ATX",7000,1200],
    ["B660","LGA1700","DDR4","ATX",6500,900],
    ["Z690","LGA1700","DDR5","ATX",8000,1600]
]

mainboard_columns = [
    "name","socket","ram_type","form_factor","score","price"
]

pd.DataFrame(mainboard_data,columns=mainboard_columns).to_csv(
    "data/processed/mainboard.csv",index=False
)

# =========================
# RAM 数据
# =========================
ram_data = [
    ["16GB DDR4",16,"DDR4",8000,300],
    ["32GB DDR4",32,"DDR4",9000,550],
    ["16GB DDR5",16,"DDR5",10000,450],
    ["32GB DDR5",32,"DDR5",11000,800]
]

ram_columns = [
    "name","capacity","type","score","price"
]

pd.DataFrame(ram_data,columns=ram_columns).to_csv(
    "data/processed/ram.csv",index=False
)

# =========================
# SSD 数据
# =========================
ssd_data = [
    ["512GB SATA",512,"SATA",4000,200],
    ["1TB SATA",1024,"SATA",4500,350],
    ["1TB NVMe",1024,"NVMe",7000,450],
    ["2TB NVMe",2048,"NVMe",9000,800]
]

ssd_columns = [
    "name","capacity","type","score","price"
]

pd.DataFrame(ssd_data,columns=ssd_columns).to_csv(
    "data/processed/ssd.csv",index=False
)

# =========================
# PSU 电源数据
# =========================
psu_data = [
    ["450W Bronze",450,"80+ Bronze",6000,280],
    ["550W Bronze",550,"80+ Bronze",6500,320],
    ["650W Gold",650,"80+ Gold",7500,450],
    ["750W Gold",750,"80+ Gold",8000,550],
    ["850W Gold",850,"80+ Gold",8500,700]
]

psu_columns = [
    "name","watt","efficiency","score","price"
]

pd.DataFrame(psu_data,columns=psu_columns).to_csv(
    "data/processed/psu.csv",index=False
)

# =========================
# 机箱数据
# =========================
case_data = [
    ["Mini Tower A","mATX",320,6000,200],
    ["Mini Tower B","mATX",340,6200,230],
    ["Mid Tower A","ATX",360,7000,350],
    ["Mid Tower B","ATX",400,7500,450],
    ["Full Tower","E-ATX",450,8000,650]
]

case_columns = [
    "name","form_factor","max_gpu_length","score","price"
]

pd.DataFrame(case_data,columns=case_columns).to_csv(
    "data/processed/case.csv",index=False
)

print("所有测试数据已生成到 data/processed/ 目录")