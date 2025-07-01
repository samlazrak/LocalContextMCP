"""
Structured logging configuration for MCP Server.
Supports both JSON and text formats with proper error handling.
"""

import logging
import logging.handlers
import sys
import json
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path

import structlog
from structlog.stdlib import LoggerFactory


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "getMessage"
            }:
                log_data[key] = value
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_data, default=str, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """Enhanced text formatter with colors for development."""
    
    # Color codes for different log levels
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors and sys.stderr.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as colored text."""
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Get color for level
        level_color = ""
        reset_color = ""
        if self.use_colors:
            level_color = self.COLORS.get(record.levelname, "")
            reset_color = self.RESET
        
        # Build log message
        message = (
            f"{timestamp} | "
            f"{level_color}{record.levelname:8}{reset_color} | "
            f"{record.name:20} | "
            f"{record.funcName}:{record.lineno} | "
            f"{record.getMessage()}"
        )
        
        # Add exception info if present
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"
        
        return message


def setup_logging(
    level: str = "INFO",
    format_type: str = "json",
    file_path: Optional[str] = None,
    file_max_size: int = 100 * 1024 * 1024,
    file_backup_count: int = 5,
    use_colors: bool = True
) -> None:
    """
    Set up structured logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type ("json" or "text")
        file_path: Path to log file (optional)
        file_max_size: Maximum file size in bytes
        file_backup_count: Number of backup files to keep
        use_colors: Whether to use colors in text format
    """
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    if format_type.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter(use_colors=use_colors)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if file_path:
        # Ensure directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=file_max_size,
            backupCount=file_backup_count,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set up specific logger levels for common noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


class LogContext:
    """Context manager for adding structured logging context."""
    
    def __init__(self, logger: structlog.stdlib.BoundLogger, **kwargs):
        self.logger = logger
        self.context = kwargs
        self.old_context = None
    
    def __enter__(self):
        self.old_context = self.logger._context.copy()
        self.logger = self.logger.bind(**self.context)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.logger.error(
                "Exception occurred in log context",
                exception_type=exc_type.__name__,
                exception_message=str(exc_val)
            )


def log_function_call(logger: structlog.stdlib.BoundLogger):
    """Decorator to log function calls with parameters and execution time."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            
            # Log function entry
            logger.debug(
                f"Calling function {func.__name__}",
                function=func.__name__,
                args=args,
                kwargs=kwargs
            )
            
            try:
                result = func(*args, **kwargs)
                
                # Log successful completion
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.debug(
                    f"Function {func.__name__} completed",
                    function=func.__name__,
                    duration_seconds=duration,
                    success=True
                )
                
                return result
                
            except Exception as e:
                # Log exception
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.error(
                    f"Function {func.__name__} failed",
                    function=func.__name__,
                    duration_seconds=duration,
                    exception=str(e),
                    success=False
                )
                raise
        
        return wrapper
    return decorator


def log_async_function_call(logger: structlog.stdlib.BoundLogger):
    """Decorator to log async function calls with parameters and execution time."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            
            # Log function entry
            logger.debug(
                f"Calling async function {func.__name__}",
                function=func.__name__,
                args=args,
                kwargs=kwargs
            )
            
            try:
                result = await func(*args, **kwargs)
                
                # Log successful completion
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.debug(
                    f"Async function {func.__name__} completed",
                    function=func.__name__,
                    duration_seconds=duration,
                    success=True
                )
                
                return result
                
            except Exception as e:
                # Log exception
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.error(
                    f"Async function {func.__name__} failed",
                    function=func.__name__,
                    duration_seconds=duration,
                    exception=str(e),
                    success=False
                )
                raise
        
        return wrapper
    return decorator