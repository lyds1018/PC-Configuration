from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .servicer import (
    build_builder_context,
    build_part_list_context,
)
from .servicer import (
    select_part as select_part_service,
)


@login_required
def build_pc(request):
    """装机主页视图"""
    return render(request, "pc_builder/builder.html", build_builder_context(request))


@login_required
def select_part(request, part_type, pk):
    """选择配件，随后重定向回装机主页面"""
    select_part_service(request, part_type, pk)
    return redirect("pc_builder:build_pc")


@login_required
def part_list(request, part_type):
    """配件列表视图"""
    return render(
        request,
        "pc_builder/part_list.html",
        build_part_list_context(request, part_type),
    )
