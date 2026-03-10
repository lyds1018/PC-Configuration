def check_mb_case(config):

    form_factor_rank = {
        "ITX": 1,
        "mATX": 2,
        "ATX": 3,
        "E-ATX": 4
    }

    mb_size = config["mainboard"]["form_factor"]
    case_size = config["case"]["form_factor"]

    if form_factor_rank[case_size] < form_factor_rank[mb_size]:
        return False

    return True