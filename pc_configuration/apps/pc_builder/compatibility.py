def parse_module_spec(value):
    text = str(value).strip()
    parts = [p.strip() for p in text.replace(";", ",").split(",")]
    return [p for p in parts if p]


def check_cpu_mb(cpu, mb):
    issues = []

    cpu_socket = cpu.get("socket")
    mb_socket = mb.get("socket")

    if str(cpu_socket).strip().upper() != str(mb_socket).strip().upper():
        issues.append(f"CPU插槽{cpu_socket}与主板插槽{mb_socket}不兼容。")

    return issues


def _parse_ram_modules(modules_value):
    # 形如 "2,16" -> (2, 16) 表示2条，每条16GB
    text = str(modules_value).replace(" ", "")
    count_str, size_str = text.split(",", 1)
    return int(count_str), float(size_str)


def check_mb_ram(mb, ram):
    issues = []

    slots = mb.get("memory_slots")
    max_mem = mb.get("max_memory")
    modules = ram.get("modules")

    count, size = _parse_ram_modules(modules)
    if count > int(slots):
        issues.append(f"内存条数{count}超过主板槽位{slots}。")

    total_mem = count * size
    if float(total_mem) > float(max_mem):
        issues.append(f"内存总容量{total_mem}GB超过主板最大容量{max_mem}GB。")

    return issues


def check_case_mb(case, mb):
    issues = []

    case_type = case.get("type")
    mb_form = mb.get("form_factor")

    case_type = str(case_type).strip().upper()
    mb_form = str(mb_form).strip().upper()

    order = ["MINI ITX", "MICRO ATX", "M-ATX", "ATX", "E-ATX"]
    alias = {"M-ATX": "MICRO ATX", "MATX": "MICRO ATX", "ITX": "MINI ITX"}

    mb_form = alias.get(mb_form, mb_form)
    case_type = alias.get(case_type, case_type)

    if order.index(mb_form) > order.index(case_type):
        issues.append(f"主板规格{mb_form}无法安装到机箱规格{case_type}。")

    return issues


def check_power_budget(cpu, gpu, psu, ram=None, ssd=None):
    issues = []

    psu_watt = psu.get("wattage")
    psu_watt = float(psu_watt)

    cpu_power = cpu.get("power") or cpu.get("tdp")
    cpu_power = float(cpu_power)

    boost_clock = gpu.get("boost_clock")
    clock_mhz = float(boost_clock)
    gpu_power = 0.16 * clock_mhz + 50

    total = cpu_power + gpu_power

    if total * 1.3 > psu_watt:
        issues.append(
            f"电源{psu_watt}W不足以覆盖预计功耗{total:.1f}W的30%冗余。"
        )

    return issues


def check_case_storage(case, storage, storage_count=1):
    issues = []

    storage_type = storage.get("type")
    internal_bays = case.get("internal_35_bays")

    storage_type_str = str(storage_type).strip()
    is_hdd = storage_type_str.replace(".", "", 1).isdigit()

    if is_hdd and float(internal_bays) < float(storage_count):
        issues.append("机箱硬盘位数量不足。")

    return issues


def run_checks(parts):
    issues = []

    cpu = parts.get("cpu", {})
    mb = parts.get("mb", {})
    ram = parts.get("ram", {})
    case = parts.get("case", {})
    psu = parts.get("psu", {})
    gpu = parts.get("gpu", {})
    storage = parts.get("ssd", {})
    storage_count = parts.get("storage_count", 1)

    issues += check_cpu_mb(cpu, mb)

    issues += check_mb_ram(mb, ram)

    issues += check_case_mb(case, mb)

    issues += check_power_budget(cpu, gpu, psu, ram=ram, ssd=parts.get("ssd"))

    issues += check_case_storage(case, storage, storage_count=storage_count)

    return {"ok": len(issues) == 0, "issues": issues}
