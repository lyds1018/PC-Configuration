from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .compatibility import run_checks
from .models import Case, Cpu, CpuCooler, Gpu, Mb, Psu, Ram, Storage


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


@login_required
def build_pc(request):
    categories = [
        {"key": "cpu", "label": "CPU"},
        {"key": "cooler", "label": "CPU 散热器"},
        {"key": "mb", "label": "主板"},
        {"key": "ram", "label": "内存"},
        {"key": "storage", "label": "存储"},
        {"key": "gpu", "label": "显卡"},
        {"key": "case", "label": "机箱"},
        {"key": "psu", "label": "电源"},
    ]
    selected_ids = request.session.get("pc_builder_selection", {})
    selected = {}
    total_price = 0.0
    estimated_wattage = None
    for item in categories:
        key = item["key"]
        item_id = selected_ids.get(key)
        if not item_id:
            continue
        model = PARTS_CONFIG.get(key, {}).get("model")
        if not model:
            continue
        try:
            obj = model.objects.get(id=item_id)
        except model.DoesNotExist:
            continue
        selected[key] = obj
        total_price += float(getattr(obj, "price", 0) or 0)

    parts = {
        "cpu": {},
        "mb": {},
        "ram": {},
        "case": {},
        "psu": {},
        "gpu": {},
        "ssd": {},
        "storage_count": 1,
    }
    if selected.get("cpu"):
        parts["cpu"] = {"tdp": selected["cpu"].tdp}
    if selected.get("mb"):
        parts["mb"] = {
            "socket": selected["mb"].socket,
            "form_factor": selected["mb"].form_factor,
            "max_memory": selected["mb"].max_memory,
            "memory_slots": selected["mb"].memory_slots,
        }
    if selected.get("ram"):
        parts["ram"] = {"modules": selected["ram"].modules}
    if selected.get("case"):
        parts["case"] = {
            "type": selected["case"].type,
            "internal_35_bays": selected["case"].internal_35_bays,
        }
    if selected.get("psu"):
        parts["psu"] = {"wattage": selected["psu"].wattage}
    if selected.get("gpu"):
        parts["gpu"] = {"boost_clock": selected["gpu"].boost_clock}
    if selected.get("storage"):
        parts["ssd"] = {"type": selected["storage"].type}

    can_check = all(
        selected.get(key)
        for key in ("cpu", "mb", "ram", "case", "psu", "gpu", "storage")
    )
    compatibility = run_checks(parts) if can_check else {"ok": True, "issues": []}

    if selected.get("cpu") and selected.get("gpu"):
        cpu_power = float(selected["cpu"].tdp or 0)
        gpu_clock = float(selected["gpu"].boost_clock or 0)
        estimated_wattage = cpu_power + (0.16 * gpu_clock + 50 if gpu_clock else 0)

    return render(
        request,
        "pc_builder/builder.html",
        {
            "categories": categories,
            "selected": selected,
            "total_price": total_price,
            "compatibility": compatibility,
            "can_check": can_check,
            "estimated_wattage": estimated_wattage,
        },
    )


@login_required
def select_part(request, part_type, pk):
    config = PARTS_CONFIG.get(part_type)
    if not config:
        return redirect("build_pc")
    model = config["model"]
    get_object_or_404(model, id=pk)
    selected = request.session.get("pc_builder_selection", {})
    selected[part_type] = pk
    request.session["pc_builder_selection"] = selected
    return redirect("build_pc")


@login_required
def part_list(request, part_type):
    config = PARTS_CONFIG.get(part_type)
    if not config:
        return render(
            request,
            "pc_builder/part_list.html",
            {"invalid": True, "title": "配件"},
        )

    q = (request.GET.get("q") or "").strip()
    sort = (request.GET.get("sort") or "price").strip()
    direction = (request.GET.get("dir") or "asc").strip().lower()

    columns = [{"key": key, "label": label} for key, label in config["columns"]]
    allowed_sort_fields = [col["key"] for col in columns]
    if sort not in allowed_sort_fields:
        sort = "price" if "price" in allowed_sort_fields else allowed_sort_fields[0]
    if direction not in {"asc", "desc"}:
        direction = "asc"

    queryset = config["model"].objects.all()
    if q:
        search_fields = config.get("search_fields") or ["name"]
        query = Q()
        for field in search_fields:
            query |= Q(**{f"{field}__icontains": q})
        queryset = queryset.filter(query)

    order_by = f"-{sort}" if direction == "desc" else sort
    queryset = queryset.order_by(order_by)

    selected_ids = request.session.get("pc_builder_selection", {})
    context = {
        "title": config["title"],
        "part_type": part_type,
        "columns": columns,
        "items": queryset,
        "q": q,
        "sort": sort,
        "dir": direction,
        "selected_id": selected_ids.get(part_type),
    }
    return render(request, "pc_builder/part_list.html", context)
