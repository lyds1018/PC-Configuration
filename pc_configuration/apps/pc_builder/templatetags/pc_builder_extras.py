import builtins

from django import template

register = template.Library()


@register.filter
def getattr(obj, name):
    return builtins.getattr(obj, name, "")


@register.filter
def get_item(mapping, key):
    if mapping is None:
        return None
    return mapping.get(key)
