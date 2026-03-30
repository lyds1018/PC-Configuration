from django import template

register = template.Library()

PART_LABELS = {
    "cpu": "CPU",
    "cooler": "CPU 散热器",
    "mb": "主板",
    "ram": "内存",
    "storage": "存储",
    "gpu": "显卡",
    "case": "机箱",
    "psu": "电源",
}


@register.filter
def part_label(value):
    key = str(value or "").strip().lower()
    return PART_LABELS.get(key, str(value or ""))
