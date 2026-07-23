"""可插拔测试执行器."""
from .api_executor import APIExecutor
from .base import TestExecutor, TestStatus
from .factory import create_executor
from .integration_executor import IntegrationExecutor

try:
    from .db_executor import DBExecutor
except ImportError:
    # 未安装 sqlalchemy 时提供占位类
    class DBExecutor:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise ImportError("数据库执行器需要安装 sqlalchemy")

try:
    from .ui_executor import UIExecutor
except ImportError:
    UIExecutor = None  # type: ignore

__all__ = [
    "TestExecutor",
    "TestStatus",
    "APIExecutor",
    "DBExecutor",
    "IntegrationExecutor",
    "UIExecutor",
    "create_executor",
]
