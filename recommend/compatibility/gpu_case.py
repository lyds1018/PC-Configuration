def check_gpu_case(config):

    gpu_length = config["gpu"]["length"]
    max_length = config["case"]["max_gpu_length"]

    if gpu_length > max_length:
        return False

    return True