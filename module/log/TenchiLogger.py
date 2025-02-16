import logging
import platform
import traceback
from datetime import datetime
import colorlog
import os
import sys
import psutil



class TenchiFilter(logging.Filter):
    """
    多关键词过滤器
    """

    def __init__(self, keywords):
        super().__init__()
        self.keywords = keywords

    def filter(self, record):
        # 如果消息中包含任意一个指定的关键词，则返回False
        return not any(keyword in record.getMessage() for keyword in self.keywords)


def _format_args(*args, **kwargs):
    """
    炫酷复杂的格式化方法
    """
    parts = []

    # 处理位置参数
    for arg in args:
        if isinstance(arg, (dict, list, tuple, set)):
            # 特殊处理容器类型
            parts.append(repr(arg))
        else:
            parts.append(str(arg))

    # 处理关键字参数
    if kwargs:
        kwargs_str = [f"{k}={repr(v)}" for k, v in kwargs.items()]
        parts.extend(kwargs_str)

    # 可以添加自定义的分隔符
    return ' | '.join(parts)


class TenchiLogger(logging.Logger):
    """
    logger类，输出和保存日志信息、报错信息
    """

    def __init__(self, name):
        super().__init__(name)

        # 设置最低级别
        self.setLevel(logging.DEBUG)

        # 设置保存路径
        log_path = "log\\log.log"
        error_path = "log\\error.log"

        # 创建过滤器，过滤关键词
        keywords = ["property", "widget", "push", "layout"]
        tenchi_filter = TenchiFilter(keywords)

        # 确保日志目录存在
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        # 创建控制台处理器（带颜色）
        console_handler = colorlog.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.addFilter(tenchi_filter)

        # 创建普通日志文件处理器
        file_handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.addFilter(tenchi_filter)

        # 创建错误日志文件处理器
        error_handler = logging.FileHandler(error_path, mode='w', encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.addFilter(tenchi_filter)

        # 控制台格式器（带颜色）
        console_formatter = colorlog.ColoredFormatter(
            fmt='%(log_color)s[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )

        # 文件格式器（不带颜色）
        file_formatter = logging.Formatter(
            fmt='[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 设置处理器的格式器
        console_handler.setFormatter(console_formatter)
        file_handler.setFormatter(file_formatter)
        error_handler.setFormatter(file_formatter)

        # 添加处理器到日志器
        self.addHandler(console_handler)
        self.addHandler(file_handler)
        self.addHandler(error_handler)

    def tenchi_exception_handler(self, exc_type, exc_value, exc_traceback):
        """
        自定义异常处理方法，还会为调试打印出一些系统信息
        :param exc_type: 异常类型
        :param exc_value: 异常值
        :param exc_traceback: 异常追踪信息
        """

        # 获取完整的错误追踪信息
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))

        # 收集系统信息
        system_info = {
            'Python版本': sys.version,
            '操作系统': platform.platform(),
            '系统类型': platform.system(),
            '系统架构': platform.machine(),
            'CPU信息': platform.processor(),
            'CPU核心数': psutil.cpu_count(),
            'CPU使用率': f"{psutil.cpu_percent()}%",
            '总内存': f"{round(psutil.virtual_memory().total / (1024.0 * 1024.0 * 1024.0), 2)} GB",
            '可用内存': f"{round(psutil.virtual_memory().available / (1024.0 * 1024.0 * 1024.0), 2)} GB",
            '内存使用率': f"{psutil.virtual_memory().percent}%",
            '当前工作目录': os.getcwd(),
            'Python路径': sys.executable,
        }

        # 添加时间戳和分隔线
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted_error = (
            f"\n{'=' * 50}\n"
            f"时间戳: {timestamp}\n\n"
            f"系统信息:\n"
            f"{'-' * 30}\n"
            f"{chr(10).join(f'{k}: {v}' for k, v in system_info.items())}\n\n"
            f"错误信息:\n"
            f"{'-' * 30}\n"
            f"类型: {exc_type.__name__}\n"
            f"描述: {str(exc_value)}\n"
            f"追踪信息:\n{error_msg}"
            f"{'=' * 50}\n"
        )

        # 记录错误信息
        self.error(f"意外错误:\n{formatted_error}")

    def debug(self, *args, **kwargs):
        """重写debug方法"""
        message = _format_args(*args, **kwargs)
        super().debug(message)

    def info(self, *args, **kwargs):
        """重写info方法"""
        message = _format_args(*args, **kwargs)
        super().info(message)

    def warning(self, *args, **kwargs):
        """重写warning方法"""
        message = _format_args(*args, **kwargs)
        super().warning(message)

    def error(self, *args, **kwargs):
        """重写error方法"""
        message = _format_args(*args, **kwargs)
        super().error(message)

    def critical(self, *args, **kwargs):
        """重写critical方法"""
        message = _format_args(*args, **kwargs)
        super().critical(message)

    @staticmethod
    def get_logger(name='TenchiLogger'):
        """
        获取logger实例的静态方法
        """
        return TenchiLogger(name)


# 检查是否存在log文件夹，如果没有就创建
if getattr(sys, 'frozen', False):
    if not os.path.exists("log"):
        os.makedirs("log")
# 实例化为全局变量
logger = TenchiLogger("TenchiLogger")
