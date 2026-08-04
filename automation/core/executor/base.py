# -*- coding: utf-8 -*-
"""测试执行器抽象基类."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class TestStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestResult:
    """测试执行结果."""
    status: TestStatus
    message: str = ""
    steps: List[Dict] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    console_logs: List[Dict] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "message": self.message,
            "steps": self.steps,
            "screenshots": self.screenshots,
            "console_logs": self.console_logs,
            "details": self.details,
        }


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
