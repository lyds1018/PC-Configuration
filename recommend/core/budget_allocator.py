def allocate_budget(total_budget, build_type):
    # 不同用途的配件预算上限
    BUDGET_MODEL = {
        "gaming": {
            "gpu": 0.45,
            "cpu": 0.25,
            "mainboard": 0.18,
            "ram": 0.15,
            "ssd": 0.15,
            "psu": 0.12,
            "case": 0.10,
        },
        "workstation": {
            "gpu": 0.40,
            "cpu": 0.35,
            "mainboard": 0.18,
            "ram": 0.20,
            "ssd": 0.18,
            "psu": 0.12,
            "case": 0.08,
        },
        "office": {
            "cpu": 0.40,
            "mainboard": 0.20,
            "ram": 0.25,
            "ssd": 0.25,
            "psu": 0.15,
            "case": 0.10,
        },
    }

    budgets = {}

    for part in BUDGET_MODEL[build_type]:
        budgets[part] = total_budget * BUDGET_MODEL[build_type][part]

    return budgets
