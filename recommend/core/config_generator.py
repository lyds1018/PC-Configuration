from recommend.compatibility.cpu_mb import check_cpu_mb
from recommend.compatibility.gpu_case import check_gpu_case
from recommend.compatibility.mb_case import check_mb_case
from recommend.compatibility.mb_ram import check_mb_ram
from recommend.compatibility.psu_check import check_power


def generate_configs(
    cpu_data,
    mb_data,
    ram_data,
    gpu_data,
    case_data,
    psu_data,
    ssd_data,
    score_weights,
    budgets,
    total_budget,
):
    """
    两阶段筛选生成兼容的配置组合
    第一阶段：根据各部分预算筛选出符合价格范围的配件
    第二阶段：使用兼容性检测器筛选可使用的组合
    """

    # 第一阶段：根据预算筛选低于价格上限的配件
    candidates = {
        "cpu": filter_by_budget(cpu_data, budgets.get("cpu", float("inf"))),
        "mainboard": filter_by_budget(mb_data, budgets.get("mainboard", float("inf"))),
        "ram": filter_by_budget(ram_data, budgets.get("ram", float("inf"))),
        "gpu": filter_by_budget(gpu_data, budgets.get("gpu", float("inf"))),
        "case": filter_by_budget(case_data, budgets.get("case", float("inf"))),
        "psu": filter_by_budget(psu_data, budgets.get("psu", float("inf"))),
        "ssd": filter_by_budget(ssd_data, budgets.get("ssd", float("inf"))),
    }

    # 预计算各部件性能归一化范围
    score_norm = build_score_norm(
        {
            "cpu": candidates["cpu"],
            "mainboard": candidates["mainboard"],
            "ram": candidates["ram"],
            "gpu": candidates["gpu"],
            "psu": candidates["psu"],
            "ssd": candidates["ssd"],
        }
    )

    # 第二阶段：分阶段剪枝 + 兼容性检测
    valid_configs = []

    cpu_list = candidates["cpu"].to_dict("records")
    mb_list = candidates["mainboard"].to_dict("records")
    ram_list = candidates["ram"].to_dict("records")
    gpu_list = candidates["gpu"].to_dict("records")
    case_list = candidates["case"].to_dict("records")
    psu_list = candidates["psu"].to_dict("records")
    ssd_list = candidates["ssd"].to_dict("records")

    for cpu in cpu_list:
        for mb in mb_list:
            config = {"cpu": cpu, "mainboard": mb}
            flag = check_cpu_mb(config)
            if not flag:
                continue

            price_cpu_mb = cpu.get("price", 0) + mb.get("price", 0)
            if price_cpu_mb > total_budget:
                continue

            for ram in ram_list:
                config["ram"] = ram
                flag = check_mb_ram(config)
                if not flag:
                    continue

                price_cpu_mb_ram = price_cpu_mb + ram.get("price", 0)
                if price_cpu_mb_ram > total_budget:
                    continue

                for gpu in gpu_list:
                    config["gpu"] = gpu
                    price_cpu_mb_ram_gpu = price_cpu_mb_ram + gpu.get("price", 0)
                    if price_cpu_mb_ram_gpu > total_budget:
                        continue

                    for case in case_list:
                        config["case"] = case
                        flag = check_mb_case(config)
                        if not flag:
                            continue
                        flag = check_gpu_case(config)
                        if not flag:
                            continue

                        price_cpu_mb_ram_gpu_case = price_cpu_mb_ram_gpu + case.get(
                            "price", 0
                        )
                        if price_cpu_mb_ram_gpu_case > total_budget:
                            continue

                        for psu in psu_list:
                            config["psu"] = psu
                            flag = check_power(config)
                            if not flag:
                                continue

                            price_partial = price_cpu_mb_ram_gpu_case + psu.get(
                                "price", 0
                            )
                            if price_partial > total_budget:
                                continue

                            for ssd in ssd_list:
                                config["ssd"] = ssd
                                total_price = price_partial + ssd.get("price", 0)
                                if total_price > total_budget:
                                    continue

                                # 计算性能得分
                                total_score = score_config(
                                    config, score_weights, score_norm
                                )

                                final_config = dict(config)
                                final_config["total_price"] = total_price
                                final_config["total_score"] = total_score
                                valid_configs.append(final_config)

    return valid_configs


def filter_by_budget(data, budget):
    return data[data["price"] <= budget]


# 计算每个部件性能评分的最小值和最大值
def build_score_norm(parts):
    score_norm = {}
    for name, df in parts.items():
        min_v = df["score"].min()
        max_v = df["score"].max()
        score_norm[name] = (min_v, max_v)
    return score_norm


# 将性能值归一化到0-1范围
def normalize_perf(value, min_v, max_v):
    return (value - min_v) / (max_v - min_v)


# 计算总得分: 基于各部件评分归一化后，加权求和
def score_config(config, weights, norm):
    total_score = 0
    for part, weight in weights.items():
        score = config[part].get("score", 0)
        min_v, max_v = norm.get(part, (0, 0))
        total_score += weight * normalize_perf(score, min_v, max_v)
    return total_score
