from pathlib import Path
from typing import Dict

import pandas as pd
from django.db import transaction

from .models import Component


BASE_DIR = Path(__file__).resolve().parents[1]
CSV_DIR = BASE_DIR / 'data' / 'csv'
CORE_CATEGORIES = {
    'cpu',
    'motherboard',
    'memory',
    'video-card',
    'internal-hard-drive',
    'power-supply',
    'case',
    'cpu-cooler',
}


def _to_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return float(value)
    return value


def _derive_memory_specs(row_dict: Dict[str, object]) -> None:
    speed = row_dict.get('speed')
    if not speed:
        return

    text = str(speed).upper().replace('DDR', '').strip()
    # Handle formats like "5,6000" (DDR5-6000)
    if ',' in text:
        parts = [p.strip() for p in text.split(',') if p.strip()]
        if parts and parts[0].isdigit():
            gen = int(parts[0])
            if gen in (3, 4, 5):
                row_dict.setdefault('memory_type', f'DDR{gen}')
        if len(parts) >= 2 and parts[1].isdigit():
            row_dict.setdefault('memory_speed_mhz', int(parts[1]))
        return

    # Handle plain numeric speeds like 3200 / 5600
    if text.isdigit():
        mhz = int(text)
        row_dict.setdefault('memory_speed_mhz', mhz)
        if mhz >= 4800:
            row_dict.setdefault('memory_type', 'DDR5')
        elif mhz >= 2133:
            row_dict.setdefault('memory_type', 'DDR4')
        else:
            row_dict.setdefault('memory_type', 'DDR3')


def import_csvs(csv_dir: Path = CSV_DIR) -> Dict[str, int]:
    results: Dict[str, int] = {}
    for csv_path in csv_dir.glob('*.csv'):
        category = csv_path.stem
        if category not in CORE_CATEGORIES:
            continue
        df = pd.read_csv(csv_path)
        count = 0
        with transaction.atomic():
            for _, row in df.iterrows():
                row_dict = {k: _to_value(v) for k, v in row.to_dict().items()}
                name = str(row_dict.pop('name', '')).strip()
                if not name:
                    continue
                price = row_dict.pop('price', None)
                if category == 'memory':
                    _derive_memory_specs(row_dict)
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