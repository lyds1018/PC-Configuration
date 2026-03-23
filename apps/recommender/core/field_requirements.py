"""
推荐系统与兼容系统字段契约。

用于统一数据清洗与数据库字段规划。
"""

REQUIRED_FIELDS = {
    "cpu": [
        "name",
        "price",
        "core_count",
        "core_clock",
        "boost_clock",
        "microarchitecture",
        "tdp",
        "graphics",
        "socket",
        "threads",
        "l3_cache_mb",
    ],
    "gpu": [
        "name",
        "price",
        "chipset",
        "memory",
        "core_clock",
        "boost_clock",
        "length",
        "tdp",
        "chip_vendor",
    ],
    "mb": [
        "name",
        "price",
        "socket",
        "form_factor",
        "max_memory",
        "memory_slots",
        "ddr_generation",
        "m2_slots",
    ],
    "ram": [
        "name",
        "price",
        "speed",
        "modules",
        "first_word_latency",
        "cas_latency",
        "total_capacity_gb",
        "ddr_generation",
    ],
    "storage": [
        "name",
        "price",
        "capacity",
        "type",
        "cache",
        "form_factor",
        "interface",
        "storage_class",
        "is_nvme",
        "tbw",
    ],
    "psu": [
        "name",
        "price",
        "type",
        "efficiency",
        "wattage",
        "modular",
        "efficiency_score",
        "atx_version",
    ],
    "case": [
        "name",
        "price",
        "type",
        "external_volume",
        "internal_35_bays",
        "max_gpu_length",
        "max_cooler_height",
    ],
    "cpu_cooler": [
        "name",
        "price",
        "rpm",
        "noise_level",
        "size",
        "cooler_type",
        "tdp_capacity",
        "socket_support",
    ],
}


RECOMMENDED_FIELDS = {
    "cpu": ["brand", "brand_en", "socket_hint"],
    "gpu": ["brand", "brand_en", "gpu_vendor", "length_class"],
    "mb": ["brand", "brand_en"],
    "ram": ["brand", "brand_en", "module_count", "module_size_gb"],
    "storage": ["brand", "brand_en"],
    "psu": ["brand", "brand_en"],
    "case": ["brand", "brand_en"],
    "cpu_cooler": ["brand", "brand_en"],
}


def get_required_fields(component_type: str):
    return REQUIRED_FIELDS.get(component_type, [])


def get_recommended_fields(component_type: str):
    return RECOMMENDED_FIELDS.get(component_type, [])

