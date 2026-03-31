"""
Logging configuration module.

Provides unified logging configuration with support for:
- Development mode: detailed DEBUG logs
- Production mode: INFO level logs
- Log file: output to ~/Library/Logs/LocalBrisk/app.log
- Daily rotation, retaining the last 7 days
"""

import os
import sys
import logging
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime


# Log directory
LOG_DIR = Path.home() / "Library" / "Logs" / "LocalBrisk"
LOG_FILE = LOG_DIR / "app.log"

# Log formats
DETAILED_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)-40s | "
    "%(filename)s:%(lineno)d | %(funcName)s | %(message)s"
)
SIMPLE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

# Whether in development mode
_is_dev_mode = os.environ.get("LOCALBRISK_DEV_MODE", "").lower() in ("1", "true", "yes")


def is_dev_mode() -> bool:
    """Check if running in development mode."""
    return _is_dev_mode


def setup_logging(
    dev_mode: bool = None,
    log_level: str = None,
    log_to_console: bool = True,
    log_to_file: bool = True,
    backup_count: int = 7,  # Retain 7 days of logs
) -> None:
    """Configure logging.
    
    Args:
        dev_mode: Whether in development mode (None uses environment variable)
        log_level: Log level (None auto-selects based on mode)
        log_to_console: Whether to output to console
        log_to_file: Whether to output to file
        backup_count: Number of log files to retain (days)
    """
    global _is_dev_mode
    
    # Determine mode
    if dev_mode is not None:
        _is_dev_mode = dev_mode
    
    # Determine log level
    if log_level:
        level = getattr(logging, log_level.upper(), logging.INFO)
    else:
        level = logging.DEBUG if _is_dev_mode else logging.INFO
    
    # Select format
    log_format = DETAILED_FORMAT if _is_dev_mode else SIMPLE_FORMAT
    
    # Create log directory
    if log_to_file:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler - daily rotation
    if log_to_file:
        file_handler = TimedRotatingFileHandler(
            LOG_FILE,
            when="midnight",     # Rotate at midnight
            interval=1,          # Every 1 day
            backupCount=backup_count,  # Retain 7 days
            encoding="utf-8",
        )
        # Set rotated file name suffix format
        file_handler.suffix = "%Y-%m-%d"
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set third-party library log levels (reduce noise)
    _configure_third_party_loggers(_is_dev_mode)
    
    # Output startup info
    mode_str = "DEV" if _is_dev_mode else "PROD"
    logging.info(f"="*60)
    logging.info(f"LocalBrisk logging initialized | mode: {mode_str} | level: {logging.getLevelName(level)}")
    logging.info(f"Log file: {LOG_FILE} (daily rotation, {backup_count}-day retention)")
    logging.info(f"="*60)


def _configure_third_party_loggers(dev_mode: bool):
    """Configure log levels for third-party libraries."""
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
    
    # Dev mode: third-party libs use INFO level
    # Prod mode: use WARNING level
    third_party_level = logging.INFO if dev_mode else logging.WARNING
    
    for logger_name in third_party_loggers:
        logging.getLogger(logger_name).setLevel(third_party_level)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class LogContext:
    """Log context manager.
    
    Adds contextual information to log entries for request tracing.
    
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
        """Get a context value."""
        return cls._context.get(key, default)
    
    @classmethod
    def get_all(cls) -> dict:
        """Get all context values."""
        return cls._context.copy()
    
    @classmethod
    def format_context(cls) -> str:
        """Format context as a string."""
        if not cls._context:
            return ""
        return " | " + " | ".join(f"{k}={v}" for k, v in cls._context.items())


# Convenience logging function (with context)
def log_with_context(logger: logging.Logger, level: int, message: str, **kwargs):
    """Log a message with context."""
    context_str = LogContext.format_context()
    if kwargs:
        extra_str = " | " + " | ".join(f"{k}={v}" for k, v in kwargs.items())
    else:
        extra_str = ""
    logger.log(level, f"{message}{context_str}{extra_str}")
