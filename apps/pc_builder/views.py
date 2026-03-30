from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .services import (
    build_builder_context,
    build_part_list_context,
    select_part as select_part_service,
)


@login_required
def build_pc(request):
    return render(request, "pc_builder/builder.html", build_builder_context(request))


@login_required
def select_part(request, part_type, pk):
    ok = select_part_service(request, part_type, pk)
    if not ok:
        return redirect("pc_builder:build_pc")
    return redirect("pc_builder:build_pc")


@login_required
def part_list(request, part_type):
    return render(
        request,
        "pc_builder/part_list.html",
        build_part_list_context(request, part_type),
    )



