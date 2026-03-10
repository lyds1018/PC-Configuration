def get_score_weights(build_type):
    # 不同用途的性能分数权重模型
    WEIGHT_MODEL = {
        "gaming": {
            "gpu": 0.45,
            "cpu": 0.25,
            "ram": 0.10,
            "ssd": 0.08,
            "mainboard": 0.07,
            "psu": 0.05,
        },
        "workstation": {
            "cpu": 0.35,
            "gpu": 0.25,
            "ram": 0.18,
            "ssd": 0.10,
            "mainboard": 0.07,
            "psu": 0.05,
        },
        "office": {
            "cpu": 0.30,
            "ram": 0.22,
            "ssd": 0.18,
            "gpu": 0.10,
            "mainboard": 0.12,
            "psu": 0.08,
        },
    }

    return WEIGHT_MODEL[build_type]
