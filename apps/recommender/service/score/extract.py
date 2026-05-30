from typing import Dict, Mapping
from ..utils import to_float, to_log


def cpu_features(cpu: Mapping[str, float]) -> Dict[str, float]:
    """提取 CPU 评分字段数据，并计算相关数据"""
    base_clock = to_float(cpu.get("base_clock"))
    boost_clock = to_float(cpu.get("boost_clock"))
    core_count = to_float(cpu.get("core_count"))
    thread_count = to_float(cpu.get("thread_count"))

    return {
        "single_score": to_float(cpu.get("single_score")),
        "multi_score": to_float(cpu.get("multi_score")),
        "bb": (base_clock + boost_clock) / 2.0,
        "ct": to_log(core_count * thread_count),
        "tdp": to_float(cpu.get("tdp")),
    }


def gpu_features(gpu: Mapping[str, float]) -> Dict[str, float]:
    """提取 GPU 评分字段数据，并计算相关数据"""
    core_clock = to_float(gpu.get("core_clock"))
    memory_clock = to_float(gpu.get("memory_clock"))
    return {
        "gaming_score": to_float(gpu.get("gaming_score")),
        "compute_score": to_float(gpu.get("compute_score")),
        "cm": (core_clock + memory_clock) / 2.0,
        "vram_size": to_float(gpu.get("vram_size")),
        "tdp": to_float(gpu.get("tdp")),
    }


def ram_features(ram: Mapping[str, float]) -> Dict[str, float]:
    """提取内存评分字段数据，并计算相关数据"""
    frequency = to_float(ram.get("frequency"))
    latency = to_float(ram.get("latency"), default=1.0)
    if latency <= 0:
        latency = 1.0

    return {
        "capacity": to_float(ram.get("capacity")),
        "fl": frequency / latency,
    }


def storage_features(storage: Mapping[str, float]) -> Dict[str, float]:
    """提取存储设备评分字段数据，并计算相关数据"""
    read_speed = to_float(storage.get("read_speed"))
    write_speed = to_float(storage.get("write_speed"))
    random_read_iops = to_float(storage.get("random_read_iops"))
    random_write_iops = to_float(storage.get("random_write_iops"))

    return {
        "capacity": to_float(storage.get("capacity")),
        "cache_size": to_float(storage.get("cache_size")),
        "sp": (read_speed + write_speed) / 2.0,
        "rand": (random_read_iops + random_write_iops) / 2.0,
    }