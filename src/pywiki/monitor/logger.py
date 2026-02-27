"""
Wiki 日志系统
"""

import functools
import logging
import traceback
from datetime import datetime
from enum import Enum
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar, ParamSpec

P = ParamSpec("P")
R = TypeVar("R")


def get_default_log_dir() -> Path:
    """获取默认日志目录"""
    log_dir = Path.home() / ".pywiki" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_default_log_file() -> Path:
    """获取默认日志文件路径"""
    return get_default_log_dir() / "pywiki.log"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class WikiLogger:
    """Wiki 日志记录器"""

    _instance: Optional["WikiLogger"] = None

    def __new__(
        cls,
        name: str = "pywiki",
        log_file: Optional[Path] = None,
        level: LogLevel = LogLevel.INFO,
    ) -> "WikiLogger":
        if cls._instance is not None:
            return cls._instance
        return super().__new__(cls)

    def __init__(
        self,
        name: str = "pywiki",
        log_file: Optional[Path] = None,
        level: LogLevel = LogLevel.INFO,
    ):
        if hasattr(self, "_initialized") and self._initialized:
            return

        self.name = name
        self.log_file = log_file or get_default_log_file()
        self.level = level
        self._initialized = True

        self._logger = logging.getLogger(name)
        self._logger.setLevel(getattr(logging, level.value))

        if not self._logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self) -> None:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)

        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = TimedRotatingFileHandler(
                self.log_file,
                when="midnight",
                interval=1,
                backupCount=7,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

    def debug(self, message: str) -> None:
        self._logger.debug(message)

    def info(self, message: str) -> None:
        self._logger.info(message)

    def warning(self, message: str) -> None:
        self._logger.warning(message)

    def error(self, message: str) -> None:
        self._logger.error(message)

    def critical(self, message: str) -> None:
        self._logger.critical(message)

    def exception(self, message: str) -> None:
        self._logger.exception(message)

    def log_generation_start(self, project_name: str) -> None:
        self.info(f"开始生成 Wiki: {project_name}")

    def log_generation_complete(
        self,
        project_name: str,
        duration: float,
        files_processed: int,
    ) -> None:
        self.info(
            f"Wiki 生成完成: {project_name} - "
            f"耗时: {duration:.2f}s, 处理文件: {files_processed}"
        )

    def log_generation_error(self, project_name: str, error: str) -> None:
        self.error(f"Wiki 生成失败: {project_name} - {error}")

    def log_file_processed(self, file_path: str, success: bool) -> None:
        if success:
            self.debug(f"文件处理成功: {file_path}")
        else:
            self.warning(f"文件处理失败: {file_path}")

    def log_diagram_generated(self, diagram_type: str, output_path: str) -> None:
        self.info(f"图表生成: {diagram_type} -> {output_path}")

    def log_sync_start(self, project_name: str) -> None:
        self.info(f"开始同步 Git: {project_name}")

    def log_sync_complete(self, project_name: str, commits: int) -> None:
        self.info(f"Git 同步完成: {project_name} - 提交数: {commits}")

    def log_exception(self, context: str, exc: Optional[Exception] = None) -> None:
        """记录异常详情，包含完整堆栈跟踪"""
        if exc:
            self.error(f"{context}: {type(exc).__name__}: {exc}")
            self.debug(f"堆栈跟踪:\n{traceback.format_exc()}")
        else:
            self.error(f"{context}")
            self.debug(f"堆栈跟踪:\n{traceback.format_exc()}")

    def log_api_call(self, api_name: str, params: dict[str, Any] | None = None) -> None:
        """记录 API 调用"""
        params_str = f" - 参数: {params}" if params else ""
        self.debug(f"API 调用: {api_name}{params_str}")

    def log_api_response(self, api_name: str, success: bool, duration_ms: float | None = None) -> None:
        """记录 API 响应"""
        duration_str = f" ({duration_ms:.0f}ms)" if duration_ms else ""
        if success:
            self.debug(f"API 响应: {api_name} - 成功{duration_str}")
        else:
            self.warning(f"API 响应: {api_name} - 失败{duration_str}")


def log_exceptions(
    logger_instance: Optional[WikiLogger] = None,
    reraise: bool = True,
    default_return: Any = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """异常日志装饰器
    
    Args:
        logger_instance: 日志记录器实例，默认使用全局 logger
        reraise: 是否重新抛出异常
        default_return: 发生异常时的默认返回值
    
    Example:
        @log_exceptions()
        def risky_function():
            ...
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            log = logger_instance or logger
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log.log_exception(f"函数 {func.__name__} 执行失败", e)
                if reraise:
                    raise
                return default_return
        return wrapper
    return decorator


def log_async_exceptions(
    logger_instance: Optional[WikiLogger] = None,
    reraise: bool = True,
    default_return: Any = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """异步函数异常日志装饰器"""
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            log = logger_instance or logger
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                log.log_exception(f"异步函数 {func.__name__} 执行失败", e)
                if reraise:
                    raise
                return default_return
        return wrapper
    return decorator


def get_logger(name: str = "pywiki", log_file: Optional[Path] = None) -> WikiLogger:
    """获取日志记录器
    
    Args:
        name: 日志记录器名称
        log_file: 日志文件路径
    
    Returns:
        WikiLogger 实例
    """
    return WikiLogger(name=name, log_file=log_file)


logger = WikiLogger()
