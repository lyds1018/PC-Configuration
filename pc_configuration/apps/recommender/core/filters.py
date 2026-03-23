"""
配件过滤器模块

提供品牌、价格范围等过滤功能
"""

from typing import List, Union

from django.db.models import QuerySet

from ..algorithms.scoring import cpu_brand as get_cpu_brand
from ..algorithms.scoring import gpu_brand as get_gpu_brand


def filter_cpu_brand(
    qs: Union[QuerySet, List],
    brand: str,
) -> Union[QuerySet, List]:
    """
    按品牌过滤 CPU

    Args:
        qs: CPU 查询集或列表
        brand: 品牌 ('any', 'intel', 'amd')

    Returns:
        过滤后的结果
    """
    if brand == "any":
        return qs

    # 如果是 QuerySet，使用 Django ORM
    if hasattr(qs, "filter"):
        # 由于品牌在名称中，需要手动过滤
        return [cpu for cpu in qs if get_cpu_brand(cpu.name) == brand]

    # 如果是列表，直接过滤
    return [cpu for cpu in qs if get_cpu_brand(cpu.name) == brand]


def filter_gpu_brand(
    qs: Union[QuerySet, List],
    brand: str,
) -> Union[QuerySet, List]:
    """
    按品牌过滤 GPU

    Args:
        qs: GPU 查询集或列表
        brand: 品牌 ('any', 'nvidia', 'amd')

    Returns:
        过滤后的结果
    """
    if brand == "any":
        return qs

    # 如果是 QuerySet
    if hasattr(qs, "filter"):
        return [gpu for gpu in qs if get_gpu_brand(gpu.name) == brand]

    # 如果是列表
    return [gpu for gpu in qs if get_gpu_brand(gpu.name) == brand]


def filter_by_price_range(
    qs: Union[QuerySet, List],
    min_price: float,
    max_price: float,
    price_field: str = "price",
) -> Union[QuerySet, List]:
    """
    按价格范围过滤

    Args:
        qs: 查询集或列表
        min_price: 最低价格
        max_price: 最高价格
        price_field: 价格字段名

    Returns:
        过滤后的结果
    """
    from ..algorithms.scoring import price as parse_price

    # 如果是 QuerySet，使用 ORM
    if hasattr(qs, "filter"):
        return qs.filter(
            **{f"{price_field}__gte": min_price, f"{price_field}__lte": max_price}
        )

    # 如果是列表，手动过滤
    return [
        item
        for item in qs
        if min_price <= parse_price(getattr(item, price_field, 0)) <= max_price
    ]
