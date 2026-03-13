from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .compat import check_candidate, check_compatibility
from .models import Component


BUILD_SESSION_KEY = 'build_selection'


def _get_selected_map(request):
    selected_ids = request.session.get(BUILD_SESSION_KEY, {})
    if not selected_ids:
        return {}
    components = Component.objects.filter(id__in=selected_ids.values())
    return {component.category: component for component in components}


def _set_selected(request, category: str, component_id: int):
    selected_ids = request.session.get(BUILD_SESSION_KEY, {})
    selected_ids[category] = component_id
    request.session[BUILD_SESSION_KEY] = selected_ids


def _remove_selected(request, category: str):
    selected_ids = request.session.get(BUILD_SESSION_KEY, {})
    if category in selected_ids:
        selected_ids.pop(category)
        request.session[BUILD_SESSION_KEY] = selected_ids


def home(request):
    categories = (
        Component.objects.values_list('category', flat=True)
        .distinct()
        .order_by('category')
    )
    return render(request, 'core/home.html', {'categories': categories})


@login_required
def builder_home(request):
    selected = _get_selected_map(request)
    issues = check_compatibility(selected)
    total_price = sum((c.price_or_zero for c in selected.values()))
    categories = (
        Component.objects.values_list('category', flat=True)
        .distinct()
        .order_by('category')
    )
    return render(
        request,
        'core/builder.html',
        {
            'selected': selected,
            'issues': issues,
            'total_price': total_price,
            'categories': categories,
        },
    )


@login_required
def category_list(request, category: str):
    query = request.GET.get('q', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()

    components = Component.objects.filter(category=category)
    if query:
        components = components.filter(Q(name__icontains=query) | Q(brand__icontains=query))
    if min_price:
        components = components.filter(price__gte=min_price)
    if max_price:
        components = components.filter(price__lte=max_price)

    selected = _get_selected_map(request)
    results = []
    for component in components:
        issues = check_candidate(selected, category, component)
        results.append({'component': component, 'issues': issues})

    return render(
        request,
        'core/category_list.html',
        {
            'category': category,
            'results': results,
            'selected': selected,
            'query': query,
            'min_price': min_price,
            'max_price': max_price,
        },
    )


@login_required
def add_to_builder(request, component_id: int):
    component = get_object_or_404(Component, id=component_id)
    _set_selected(request, component.category, component.id)
    return redirect('builder')


@login_required
def remove_from_builder(request, category: str):
    _remove_selected(request, category)
    return redirect('builder')


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('builder')
    else:
        form = UserCreationForm()
    return render(request, 'core/register.html', {'form': form})