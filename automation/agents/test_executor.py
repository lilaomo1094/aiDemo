# -*- coding: utf-8 -*-
"""测试执行 Agent：调用可插拔执行器运行测试用例."""

import time
from datetime import datetime
from typing import Any, Dict, List

from automation.core.executor import TestStatus, create_executor
from automation.core.utils import calculate_pass_rate

from .base import BaseAgent


class TestExecutor(BaseAgent):
    def execute(self, task, context) -> Dict:
        test_cases = getattr(context, "test_cases", []) or []
        execution_results = []
        executor_cache: Dict[str, Any] = {}

        for test_case in test_cases:
            try:
                result = self._execute_single(test_case, context, executor_cache)
                execution_results.append(result)
            except Exception as e:
                # 单个用例的不可预期异常不应阻断后续用例
                execution_results.append(self._error_execution(test_case, e))
                continue

            # 失败重试
            if result["status"] in {TestStatus.FAILED.value, TestStatus.ERROR.value}:
                retry_times = self.config.test.retry_times if hasattr(self.config, "test") else 0
                for _ in range(retry_times):
                    retry = self._execute_single(test_case, context, executor_cache)
                    execution_results[-1] = retry
                    if retry["status"] not in {TestStatus.FAILED.value, TestStatus.ERROR.value}:
                        break

        return {
            "execution_results": execution_results,
            "summary": {
                "total": len(execution_results),
                "passed": sum(1 for r in execution_results if r["status"] == TestStatus.PASSED.value),
                "failed": sum(1 for r in execution_results if r["status"] == TestStatus.FAILED.value),
                "blocked": sum(1 for r in execution_results if r["status"] == TestStatus.BLOCKED.value),
                "skipped": sum(1 for r in execution_results if r["status"] == TestStatus.SKIPPED.value),
                "error": sum(1 for r in execution_results if r["status"] == TestStatus.ERROR.value),
                "pass_rate": self._calculate_pass_rate(execution_results),
            },
        }

    def _execute_single(self, test_case: Dict, context, executor_cache: Dict[str, Any]) -> Dict:
        test_id = test_case.get("id", "UNKNOWN")
        test_type = test_case.get("type", "API")
        execution = self._init_execution(test_case)
        start = time.time()
        try:
            executor = executor_cache.get(test_type)
            if executor is None:
                executor = create_executor(test_type, self.config)
                executor_cache[test_type] = executor
            result = executor.execute(test_case, context)
            self._apply_result(execution, result)
        except Exception as e:
            execution["status"] = TestStatus.ERROR.value
            execution["error_message"] = str(e)
        finally:
            execution["duration"] = round(time.time() - start, 3)
            execution["end_time"] = datetime.now().isoformat()
        return execution

    def _init_execution(self, test_case: Dict) -> Dict:
        return {
            "test_id": test_case.get("id", "UNKNOWN"),
            "test_name": test_case.get("name", ""),
            "test_type": test_case.get("type", "API"),
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "duration": 0.0,
            "status": TestStatus.PASSED.value,
            "status_code": None,
            "response": None,
            "error_message": "",
            "screenshots": [],
            "logs": [],
            "console_logs": [],
            "video_path": "",
            "har_path": "",
            "browser_mode": "",
            "network_type": "",
        }

    def _apply_result(self, execution: Dict, result: Dict):
        execution["status"] = result.get("status", TestStatus.PASSED.value)
        execution["status_code"] = result.get("status_code")
        execution["response"] = result.get("response", result.get("rows", result.get("steps", {})))
        execution["error_message"] = result.get("message", "")
        execution["screenshots"] = result.get("screenshots", []) or []
        execution["console_logs"] = result.get("console_logs", [])
        execution["video_path"] = result.get("video_path", "")
        execution["har_path"] = result.get("har_path", "")
        execution["browser_mode"] = result.get("browser_mode", "")
        execution["network_type"] = result.get("network_type", "")

    def _error_execution(self, test_case: Dict, error: Exception) -> Dict:
        execution = self._init_execution(test_case)
        execution["status"] = TestStatus.ERROR.value
        execution["error_message"] = f"执行框架异常: {error}"
        execution["duration"] = 0.0
        execution["end_time"] = datetime.now().isoformat()
        return execution

    def _calculate_pass_rate(self, results: List[Dict]) -> float:
        return calculate_pass_rate(results, passed_status=TestStatus.PASSED.value)
