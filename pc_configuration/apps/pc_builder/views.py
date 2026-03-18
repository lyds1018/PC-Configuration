from django.shortcuts import render

from .models import Case, Cpu, CpuCooler, Gpu, Mb, Psu, Ram, Storage


def build_pc(request):
    parts = {
        "cpus": Cpu.objects.all().order_by("price"),
        "gpus": Gpu.objects.all().order_by("price"),
        "mbs": Mb.objects.all().order_by("price"),
        "rams": Ram.objects.all().order_by("price"),
        "psus": Psu.objects.all().order_by("price"),
        "cases": Case.objects.all().order_by("price"),
        "storages": Storage.objects.all().order_by("price"),
        "coolers": CpuCooler.objects.all().order_by("price"),
    }

    selected = {}
    total_price = 0.0
    if request.method == "POST":
        mapping = {
            "cpu_id": Cpu,
            "gpu_id": Gpu,
            "mb_id": Mb,
            "ram_id": Ram,
            "psu_id": Psu,
            "case_id": Case,
            "storage_id": Storage,
            "cooler_id": CpuCooler,
        }
        for field, model in mapping.items():
            item_id = request.POST.get(field)
            if item_id:
                item = model.objects.get(id=item_id)
                selected[field] = item
                total_price += float(item.price or 0)

    return render(
        request,
        "pc_builder/builder.html",
        {"parts": parts, "selected": selected, "total_price": total_price},
    )
