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
            ("core_count", "核心数"),
            ("core_clock", "基础频率(GHz)"),
            ("boost_clock", "加速频率(GHz)"),
            ("microarchitecture", "架构"),
            ("tdp", "TDP(W)"),
            ("graphics", "核显"),
            ("price", "价格(￥)"),
        ],
        "search_fields": ["name", "microarchitecture"],
    },
    "gpu": {
        "title": "显卡",
        "model": Gpu,
        "columns": [
            ("name", "型号"),
            ("chipset", "芯片"),
            ("memory", "显存(GB)"),
            ("core_clock", "核心频率(MHz)"),
            ("boost_clock", "加速频率(MHz)"),
            ("length", "长度(mm)"),
            ("price", "价格(￥)"),
        ],
        "search_fields": ["name", "chipset"],
    },
    "mb": {
        "title": "主板",
        "model": Mb,
        "columns": [
            ("name", "型号"),
            ("socket", "接口"),
            ("form_factor", "板型"),
            ("max_memory", "最大内存(GB)"),
            ("memory_slots", "内存槽"),
            ("price", "价格(￥)"),
        ],
        "search_fields": ["name", "socket", "form_factor"],
    },
    "ram": {
        "title": "内存",
        "model": Ram,
        "columns": [
            ("name", "型号"),
            ("speed", "频率"),
            ("modules", "模块"),
            ("first_word_latency", "首字延迟"),
            ("cas_latency", "CL"),
            ("price", "价格(￥)"),
        ],
        "search_fields": ["name", "speed", "modules"],
    },
    "psu": {
        "title": "电源",
        "model": Psu,
        "columns": [
            ("name", "型号"),
            ("type", "类型"),
            ("efficiency", "认证"),
            ("wattage", "功率(W)"),
            ("modular", "模组化"),
            ("price", "价格(￥)"),
        ],
        "search_fields": ["name", "type", "efficiency", "modular"],
    },
    "case": {
        "title": "机箱",
        "model": Case,
        "columns": [
            ("name", "型号"),
            ("type", "类型"),
            ("external_volume", "体积(L)"),
            ("internal_35_bays", "3.5寸仓位"),
            ("price", "价格(￥)"),
        ],
        "search_fields": ["name", "type"],
    },
    "storage": {
        "title": "存储",
        "model": Storage,
        "columns": [
            ("name", "型号"),
            ("capacity", "容量(GB)"),
            ("type", "类型"),
            ("cache", "缓存(MB)"),
            ("form_factor", "规格"),
            ("interface", "接口"),
            ("price", "价格(￥)"),
        ],
        "search_fields": ["name", "type", "form_factor", "interface"],
    },
    "cooler": {
        "title": "散热器",
        "model": CpuCooler,
        "columns": [
            ("name", "型号"),
            ("rpm", "转速"),
            ("noise_level", "噪音"),
            ("size", "尺寸(mm)"),
            ("price", "价格(￥)"),
        ],
        "search_fields": ["name", "rpm", "noise_level"],
    },
}
