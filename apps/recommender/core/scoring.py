import re


def price(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def cpu_brand(name):
    text = (name or "").lower()
    if "intel" in text:
        return "intel"
    if "amd" in text or "ryzen" in text:
        return "amd"
    return "other"


def gpu_brand(name):
    text = (name or "").lower()
    if "nvidia" in text or "geforce" in text:
        return "nvidia"
    if "amd" in text or "radeon" in text:
        return "amd"
    return "other"


def cpu_score(cpu, usage):
    base = (cpu.core_count or 0) * 2 + (cpu.boost_clock or 0)
    if usage == "gaming":
        return base + (cpu.boost_clock or 0) * 2
    if usage == "office":
        return base * 0.8
    return base * 1.2


def gpu_score(gpu, usage):
    base = (gpu.boost_clock or 0) + (gpu.memory or 0) * 60
    if usage == "gaming":
        return base * 1.3
    if usage == "office":
        return base * 0.6
    return base * 1.1


def ram_score(ram):
    text = str(ram.speed or "")
    numbers = re.findall(r"\\d+", text)
    speed = float(numbers[0]) if numbers else 0.0
    return speed + price(ram.price) * 0.05


def storage_score(storage):
    return (storage.capacity or 0) + price(storage.price) * 0.02
