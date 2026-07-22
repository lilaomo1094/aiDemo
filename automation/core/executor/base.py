# -*- coding: utf-8 -*-
"""测试执行器抽象基类."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict


class TestStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    ERROR = "error"


class TestExecutor(ABC):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def execute(self, test_case: Dict, context) -> Dict[str, Any]:
        """执行单个测试用例，返回执行结果字典."""
        pass

    def _make_result(self, status: TestStatus, message: str = "", **kwargs) -> Dict:
        result = {"status": status.value, "message": message}
        result.update(kwargs)
        return result
