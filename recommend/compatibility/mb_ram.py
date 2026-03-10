def check_mb_ram(config):

    if config["mainboard"]["ram_type"] != config["ram"]["type"]:
        return False

    return True