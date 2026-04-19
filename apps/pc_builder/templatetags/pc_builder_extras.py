import builtins

from django import template

register = template.Library()


# 自定义模板过滤器
# `getattr` 用于获取对象属性
@register.filter
def getattr(obj, name):
    return builtins.getattr(obj, name, "")


# `get_item` 用于获取字典项
@register.filter
def get_item(mapping, key):
    if mapping is None:
        return None
    return mapping.get(key)
