from .models import Case, Cpu, CpuCooler, Gpu, Mb, Psu, Ram, Storage

SELECTION_SESSION_KEY = "pc_builder_selection"

BUILD_CATEGORIES = [
    {"key": "cpu", "label": "CPU"},
    {"key": "cooler", "label": "CPU 散热器"},
    {"key": "mb", "label": "主板"},
    {"key": "ram", "label": "内存"},
    {"key": "storage", "label": "存储"},
    {"key": "gpu", "label": "显卡"},
    {"key": "case", "label": "机箱"},
    {"key": "psu", "label": "电源"},
]

COMPATIBILITY_REQUIRED_KEYS = ("cpu", "mb", "ram", "case", "psu", "gpu", "storage")

PARTS_CONFIG = {
    "cpu": {
        "title": "CPU",
        "model": Cpu,
        "columns": [
            ("name", "型号"),
            ("socket", "接口"),
            ("core_count", "核心数"),
            ("thread_count", "线程数"),
            ("base_clock", "基础频率(GHz)"),
            ("boost_clock", "睿频(GHz)"),
            ("tdp", "TDP(W)"),
            ("price", "价格(￥)"),
        ],
        "search_fields": ["name", "brand", "socket"],
    },
    "gpu": {
        "title": "显卡",
        "model": Gpu,
        "columns": [
            ("name", "型号"),
            ("chip_brand", "芯片品牌"),
            ("card_brand", "显卡品牌"),
            ("vram_size", "显存(GB)"),
            ("length", "长度(mm)"),
            ("tdp", "TDP(W)"),
            ("gaming_score", "游戏性能"),
            ("compute_score", "计算性能"),
            ("price", "价格(￥)"),
        ],
        "search_fields": ["name", "chip_brand", "card_brand"],
    },
    "mb": {
        "title": "主板",
        "model": Mb,
        "columns": [
            ("name", "型号"),
            ("socket", "接口"),
            ("form", "板型"),
            ("memory_type", "内存类型"),
            ("memory_frequency", "内存频率"),
            ("memory_slots", "内存槽"),
            ("m2_slots", "M.2"),
            ("sata_ports", "SATA"),
            ("price", "价格(￥)"),
        ],
        "search_fields": ["name", "brand", "socket", "form"],
    },
    "ram": {
        "title": "内存",
        "model": Ram,
        "columns": [
            ("name", "型号"),
            ("type", "代际"),
            ("capacity", "容量(GB)"),
            ("frequency", "频率(MHz)"),
            ("latency", "时序(CL)"),
            ("price", "价格(￥)"),
        ],
        "search_fields": ["name", "brand", "type"],
    },
    "psu": {
        "title": "电源",
        "model": Psu,
        "columns": [
            ("name", "型号"),
            ("form", "规格"),
            ("efficiency", "认证"),
            ("wattage", "功率(W)"),
            ("price", "价格(￥)"),
        ],
        "search_fields": ["name", "brand", "form", "efficiency"],
    },
    "case": {
        "title": "机箱",
        "model": Case,
        "columns": [
            ("name", "型号"),
            ("form", "板型支持"),
            ("gpu_length", "显卡限长(mm)"),
            ("air_height", "风冷限高(mm)"),
            ("psu_form", "电源规格"),
            ("storage_2_5", "2.5寸位"),
            ("storage_3_5", "3.5寸位"),
            ("price", "价格(￥)"),
        ],
        "search_fields": ["name", "brand", "form", "psu_form"],
    },
    "storage": {
        "title": "存储",
        "model": Storage,
        "columns": [
            ("name", "型号"),
            ("type", "类型"),
            ("capacity", "容量(GB)"),
            ("read_speed", "读取(MB/s)"),
            ("write_speed", "写入(MB/s)"),
            ("price", "价格(￥)"),
        ],
        "search_fields": ["name", "brand", "type"],
    },
    "cooler": {
        "title": "散热器",
        "model": CpuCooler,
        "columns": [
            ("name", "型号"),
            ("type", "类型"),
            ("air_height", "风冷高度(mm)"),
            ("water_size", "冷排规格"),
            ("noise_level", "噪音(dB)"),
            ("price", "价格(￥)"),
        ],
        "search_fields": ["name", "brand", "type"],
    },
}
