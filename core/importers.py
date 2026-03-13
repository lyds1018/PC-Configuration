from pathlib import Path
from typing import Dict, Iterable

import pandas as pd
from django.db import transaction

from .models import Component


BASE_DIR = Path(__file__).resolve().parents[1]
CSV_DIR = BASE_DIR / 'data' / 'csv'


def _to_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return float(value)
    return value


def import_csvs(csv_dir: Path = CSV_DIR) -> Dict[str, int]:
    results: Dict[str, int] = {}
    for csv_path in csv_dir.glob('*.csv'):
        category = csv_path.stem
        df = pd.read_csv(csv_path)
        count = 0
        with transaction.atomic():
            for _, row in df.iterrows():
                row_dict = {k: _to_value(v) for k, v in row.to_dict().items()}
                name = str(row_dict.pop('name', '')).strip()
                if not name:
                    continue
                price = row_dict.pop('price', None)
                brand = name.split(' ')[0] if name else ''
                component, _ = Component.objects.get_or_create(
                    category=category,
                    name=name,
                    defaults={
                        'price': price,
                        'brand': brand,
                        'specs': row_dict,
                    },
                )
                component.price = price
                component.brand = brand
                component.specs = row_dict
                component.save()
                count += 1
        results[category] = count
    return results