"""日志配置"""

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """
    获取配置好的 logger

    Args:
        name: logger 名称，通常使用 __name__

    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)

    # 如果没有处理器，添加一个
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # 控制台处理器
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)

        # 格式化器
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger
