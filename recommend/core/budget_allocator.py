def allocate_budget(total_budget):

    ratio = {
        "cpu":0.2,
        "gpu":0.4,
        "motherboard":0.1,
        "ram":0.1,
        "ssd":0.1
    }

    budgets = {}

    for part in ratio:
        budgets[part] = total_budget * ratio[part]

    return budgets