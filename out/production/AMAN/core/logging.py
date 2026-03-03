"""
日志配置模块

提供统一的日志配置，支持：
- 开发模式：输出详细 DEBUG 日志
- 生产模式：输出 INFO 级别日志
- 日志文件：输出到 ~/Library/Logs/LocalBrisk/app.log
- 按天滚动，保留近7日日志
"""

import os
import sys
import logging
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime


# 日志目录
LOG_DIR = Path.home() / "Library" / "Logs" / "LocalBrisk"
LOG_FILE = LOG_DIR / "app.log"

# 日志格式
DETAILED_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)-40s | "
    "%(filename)s:%(lineno)d | %(funcName)s | %(message)s"
)
SIMPLE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

# 是否为开发模式
_is_dev_mode = os.environ.get("LOCALBRISK_DEV_MODE", "").lower() in ("1", "true", "yes")


def is_dev_mode() -> bool:
    """检查是否为开发模式"""
    return _is_dev_mode


def setup_logging(
    dev_mode: bool = None,
    log_level: str = None,
    log_to_console: bool = True,
    log_to_file: bool = True,
    backup_count: int = 7,  # 保留7天日志
) -> None:
    """设置日志配置
    
    Args:
        dev_mode: 是否为开发模式（None 则使用环境变量判断）
        log_level: 日志级别（None 则根据模式自动选择）
        log_to_console: 是否输出到控制台
        log_to_file: 是否输出到文件
        backup_count: 保留的日志文件数量（天数）
    """
    global _is_dev_mode
    
    # 确定模式
    if dev_mode is not None:
        _is_dev_mode = dev_mode
    
    # 确定日志级别
    if log_level:
        level = getattr(logging, log_level.upper(), logging.INFO)
    else:
        level = logging.DEBUG if _is_dev_mode else logging.INFO
    
    # 选择格式
    log_format = DETAILED_FORMAT if _is_dev_mode else SIMPLE_FORMAT
    
    # 创建日志目录
    if log_to_file:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 创建格式化器
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
    
    # 控制台处理器
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # 文件处理器 - 按天滚动
    if log_to_file:
        file_handler = TimedRotatingFileHandler(
            LOG_FILE,
            when="midnight",     # 每天午夜滚动
            interval=1,          # 间隔1天
            backupCount=backup_count,  # 保留7天
            encoding="utf-8",
        )
        # 设置滚动后的文件名后缀格式
        file_handler.suffix = "%Y-%m-%d"
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # 设置第三方库日志级别（减少噪音）
    _configure_third_party_loggers(_is_dev_mode)
    
    # 输出启动信息
    mode_str = "DEV" if _is_dev_mode else "PROD"
    logging.info(f"="*60)
    logging.info(f"LocalBrisk 日志系统初始化 | 模式: {mode_str} | 级别: {logging.getLevelName(level)}")
    logging.info(f"日志文件: {LOG_FILE} (按天滚动，保留{backup_count}天)")
    logging.info(f"="*60)


def _configure_third_party_loggers(dev_mode: bool):
    """配置第三方库的日志级别"""
    third_party_loggers = [
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "httpx",
        "httpcore",
        "openai",
        "langchain",
        "langchain_core",
        "langgraph",
    ]
    
    # 开发模式下，第三方库使用 INFO 级别
    # 生产模式下，使用 WARNING 级别
    third_party_level = logging.INFO if dev_mode else logging.WARNING
    
    for logger_name in third_party_loggers:
        logging.getLogger(logger_name).setLevel(third_party_level)


def get_logger(name: str) -> logging.Logger:
    """获取日志记录器
    
    Args:
        name: 日志记录器名称（通常使用 __name__）
        
    Returns:
        配置好的日志记录器
    """
    return logging.getLogger(name)


class LogContext:
    """日志上下文管理器
    
    用于在日志中添加上下文信息，方便追踪请求链路
    
    Usage:
        with LogContext(agent_name="my_agent", execution_id="123"):
            logger.info("Processing...")
    """
    
    _context: dict = {}
    
    def __init__(self, **kwargs):
        self.new_context = kwargs
        self.old_context = {}
    
    def __enter__(self):
        self.old_context = LogContext._context.copy()
        LogContext._context.update(self.new_context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        LogContext._context = self.old_context
        return False
    
    @classmethod
    def get(cls, key: str, default=None):
        """获取上下文值"""
        return cls._context.get(key, default)
    
    @classmethod
    def get_all(cls) -> dict:
        """获取所有上下文"""
        return cls._context.copy()
    
    @classmethod
    def format_context(cls) -> str:
        """格式化上下文为字符串"""
        if not cls._context:
            return ""
        return " | " + " | ".join(f"{k}={v}" for k, v in cls._context.items())


# 方便的日志函数（带上下文）
def log_with_context(logger: logging.Logger, level: int, message: str, **kwargs):
    """带上下文的日志输出"""
    context_str = LogContext.format_context()
    if kwargs:
        extra_str = " | " + " | ".join(f"{k}={v}" for k, v in kwargs.items())
    else:
        extra_str = ""
    logger.log(level, f"{message}{context_str}{extra_str}")
