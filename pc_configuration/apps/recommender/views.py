from dataclasses import dataclass
import re

from django.contrib.auth.decorators import login_required
from django.db.models import QuerySet
from django.shortcuts import render

from pc_builder.models import Case, Cpu, CpuCooler, Gpu, Mb, Psu, Ram, Storage
from pc_builder.compatibility import run_checks


@dataclass
class PartChoice:
    name: str
    price: float
    obj: object


def _price(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _cpu_brand(name):
    text = (name or "").lower()
    if "intel" in text:
        return "intel"
    if "amd" in text or "ryzen" in text:
        return "amd"
    return "other"


def _gpu_brand(name):
    text = (name or "").lower()
    if "nvidia" in text or "geforce" in text:
        return "nvidia"
    if "amd" in text or "radeon" in text:
        return "amd"
    return "other"


def _cpu_score(cpu, usage):
    base = (cpu.core_count or 0) * 2 + (cpu.boost_clock or 0)
    if usage == "gaming":
        return base + (cpu.boost_clock or 0) * 2
    if usage == "office":
        return base * 0.8
    return base * 1.2


def _gpu_score(gpu, usage):
    base = (gpu.boost_clock or 0) + (gpu.memory or 0) * 60
    if usage == "gaming":
        return base * 1.3
    if usage == "office":
        return base * 0.6
    return base * 1.1


def _ram_score(ram):
    text = str(ram.speed or "")
    numbers = re.findall(r"\\d+", text)
    speed = float(numbers[0]) if numbers else 0.0
    return speed + _price(ram.price) * 0.05


def _storage_score(storage):
    return (storage.capacity or 0) + _price(storage.price) * 0.02


def _pick_best_within(queryset, budget, score_fn):
    best = None
    best_score = -1
    for item in queryset:
        price = _price(item.price)
        if price <= budget and price > 0:
            score = score_fn(item)
            if score > best_score:
                best = item
                best_score = score
    if best:
        return best
    return queryset.order_by("price").first()


def _psu_for_wattage(queryset, min_watt):
    if min_watt <= 0:
        return queryset.order_by("price").first()
    candidate = (
        queryset.filter(wattage__gte=min_watt).order_by("price").first()
    )
    return candidate or queryset.order_by("-wattage").first()


def _make_parts_dict(selection):
    cpu = selection.get("cpu")
    mb = selection.get("mb")
    ram = selection.get("ram")
    case = selection.get("case")
    psu = selection.get("psu")
    gpu = selection.get("gpu")
    storage = selection.get("storage")
    return {
        "cpu": {"tdp": cpu.tdp} if cpu else {},
        "mb": {
            "socket": mb.socket,
            "form_factor": mb.form_factor,
            "max_memory": mb.max_memory,
            "memory_slots": mb.memory_slots,
        }
        if mb
        else {},
        "ram": {"modules": ram.modules} if ram else {},
        "case": {
            "type": case.type,
            "internal_35_bays": case.internal_35_bays,
        }
        if case
        else {},
        "psu": {"wattage": psu.wattage} if psu else {},
        "gpu": {"boost_clock": gpu.boost_clock} if gpu else {},
        "ssd": {"type": storage.type} if storage else {},
        "storage_count": 1,
    }


def _estimate_wattage(cpu, gpu):
    cpu_power = float(cpu.tdp or 0) if cpu else 0
    gpu_clock = float(gpu.boost_clock or 0) if gpu else 0
    gpu_power = 0.16 * gpu_clock + 50 if gpu_clock else 0
    return cpu_power + gpu_power


def _build_recommendation(
    profile,
    usage,
    budget_min,
    budget_max,
    cpu_qs,
    gpu_qs,
    ram_qs,
    storage_qs,
    mb_qs,
    psu_qs,
    case_qs,
    cooler_qs,
):
    target_budget = {
        "value": budget_min,
        "balanced": (budget_min + budget_max) / 2,
        "performance": budget_max,
    }[profile]

    cpu_candidates = sorted(
        list(cpu_qs),
        key=lambda c: _cpu_score(c, usage),
        reverse=True,
    )[:20]
    gpu_candidates = sorted(
        list(gpu_qs),
        key=lambda g: _gpu_score(g, usage),
        reverse=True,
    )[:20]

    other_min = sum(
        [
            _price(ram_qs.order_by("price").first().price),
            _price(storage_qs.order_by("price").first().price),
            _price(mb_qs.order_by("price").first().price),
            _price(case_qs.order_by("price").first().price),
            _price(cooler_qs.order_by("price").first().price),
        ]
    )

    best = None
    for cpu in cpu_candidates:
        for gpu in gpu_candidates:
            base = _price(cpu.price) + _price(gpu.price) + other_min
            if base > budget_max:
                continue
            score = _cpu_score(cpu, usage) * 0.55 + _gpu_score(gpu, usage) * 0.65
            if not best or score > best[0]:
                best = (score, cpu, gpu)

    if not best:
        return None

    _, cpu, gpu = best
    remaining = max(target_budget - _price(cpu.price) - _price(gpu.price), 0)

    ram = _pick_best_within(ram_qs, remaining * 0.25, _ram_score)
    storage = _pick_best_within(storage_qs, remaining * 0.25, _storage_score)
    mb = _pick_best_within(mb_qs, remaining * 0.2, lambda m: _price(m.price))
    case = _pick_best_within(case_qs, remaining * 0.15, lambda c: _price(c.price))
    cooler = _pick_best_within(
        cooler_qs, remaining * 0.1, lambda c: _price(c.price)
    )

    estimated_watt = _estimate_wattage(cpu, gpu)
    psu = _psu_for_wattage(psu_qs, estimated_watt * 1.3)

    selection = {
        "cpu": cpu,
        "gpu": gpu,
        "ram": ram,
        "storage": storage,
        "mb": mb,
        "psu": psu,
        "case": case,
        "cooler": cooler,
    }

    total = sum(_price(item.price) for item in selection.values() if item)
    if total < budget_min or total > budget_max:
        return None

    compatibility = run_checks(_make_parts_dict(selection))

    return {
        "profile": {
            "value": "性价比方案",
            "balanced": "均衡方案",
            "performance": "性能方案",
        }[profile],
        "total": total,
        "estimated_watt": estimated_watt,
        "compatibility": compatibility,
        "items": selection,
    }


def _filter_brand_cpu(qs: QuerySet, brand):
    if brand == "any":
        return qs
    return [c for c in qs if _cpu_brand(c.name) == brand]


def _filter_brand_gpu(qs: QuerySet, brand):
    if brand == "any":
        return qs
    return [g for g in qs if _gpu_brand(g.name) == brand]


@login_required
def recommend(request):
    context = {
        "results": [],
        "form": {
            "budget_min": "",
            "budget_max": "",
            "usage": "gaming",
            "cpu_brand": "any",
            "gpu_brand": "any",
        },
    }

    if request.method == "POST":
        try:
            budget_min = float(request.POST.get("budget_min") or 0)
            budget_max = float(request.POST.get("budget_max") or 0)
        except (TypeError, ValueError):
            budget_min = 0
            budget_max = 0

        usage = request.POST.get("usage") or "gaming"
        cpu_brand = request.POST.get("cpu_brand") or "any"
        gpu_brand = request.POST.get("gpu_brand") or "any"

        context["form"] = {
            "budget_min": budget_min,
            "budget_max": budget_max,
            "usage": usage,
            "cpu_brand": cpu_brand,
            "gpu_brand": gpu_brand,
        }

        if budget_min > budget_max:
            budget_min, budget_max = budget_max, budget_min

        cpu_qs = Cpu.objects.all()
        gpu_qs = Gpu.objects.all()
        ram_qs = Ram.objects.all()
        storage_qs = Storage.objects.all()
        mb_qs = Mb.objects.all()
        psu_qs = Psu.objects.all()
        case_qs = Case.objects.all()
        cooler_qs = CpuCooler.objects.all()

        cpu_list = _filter_brand_cpu(cpu_qs, cpu_brand)
        gpu_list = _filter_brand_gpu(gpu_qs, gpu_brand)

        results = []
        for profile in ("value", "balanced", "performance"):
            result = _build_recommendation(
                profile,
                usage,
                budget_min,
                budget_max,
                cpu_list,
                gpu_list,
                ram_qs,
                storage_qs,
                mb_qs,
                psu_qs,
                case_qs,
                cooler_qs,
            )
            if result:
                results.append(result)

        context["results"] = results

    return render(request, "recommender/index.html", context)
