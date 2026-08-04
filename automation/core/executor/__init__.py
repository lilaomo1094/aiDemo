"""可插拔测试执行器."""
from .api_executor import APIExecutor
from .base import TestExecutor, TestResult, TestStatus
from .factory import create_executor, register_executor
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

try:
    from .exploratory_ui_executor import ExploratoryUIExecutor
except ImportError:
    ExploratoryUIExecutor = None  # type: ignore

try:
    from .page_analyzer import PageAnalyzer, PageState
except ImportError:
    PageAnalyzer = None  # type: ignore
    PageState = None  # type: ignore

try:
    from .selector_healer import SelectorHealer, HealedSelector
except ImportError:
    SelectorHealer = None  # type: ignore
    HealedSelector = None  # type: ignore

__all__ = [
    "TestExecutor",
    "TestResult",
    "TestStatus",
    "APIExecutor",
    "DBExecutor",
    "IntegrationExecutor",
    "UIExecutor",
    "ExploratoryUIExecutor",
    "PageAnalyzer",
    "PageState",
    "SelectorHealer",
    "HealedSelector",
    "create_executor",
    "register_executor",
]
