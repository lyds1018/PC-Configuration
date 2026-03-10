def check_cpu_mb(config):

    if config["cpu"]["socket"] != config["mainboard"]["socket"]:
        return False

    return True