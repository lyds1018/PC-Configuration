def check_power(config):

    cpu_tdp = config["cpu"]["tdp"]
    gpu_tdp = config["gpu"]["tdp"]
    psu_watt = config["psu"]["watt"]

    system_power = cpu_tdp + gpu_tdp + 150
    required_power = system_power * 1.3

    if psu_watt < required_power:
        return False

    return True