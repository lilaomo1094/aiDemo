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

        for test_case in test_cases:
            result = self._execute_single(test_case, context)
            execution_results.append(result)
            # 失败重试
            if result["status"] in {TestStatus.FAILED.value, TestStatus.ERROR.value}:
                retry_times = self.config.test.retry_times if hasattr(self.config, "test") else 0
                for _ in range(retry_times):
                    retry = self._execute_single(test_case, context)
                    if retry["status"] not in {TestStatus.FAILED.value, TestStatus.ERROR.value}:
                        execution_results[-1] = retry
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

    def _execute_single(self, test_case: Dict, context) -> Dict:
        test_id = test_case.get("id", "UNKNOWN")
        test_type = test_case.get("type", "API")
        execution = {
            "test_id": test_id,
            "test_name": test_case.get("name", ""),
            "test_type": test_type,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "duration": 0.0,
            "status": TestStatus.PASSED.value,
            "status_code": None,
            "response": None,
            "error_message": "",
            "screenshots": [],
            "logs": [],
        }
        start = time.time()
        try:
            executor = create_executor(test_type, self.config)
            result = executor.execute(test_case, context)
            execution["status"] = result.get("status", TestStatus.PASSED.value)
            execution["status_code"] = result.get("status_code")
            execution["response"] = result.get("response", result.get("rows", result.get("steps", {})))
            execution["error_message"] = result.get("message", "")
            execution["screenshots"] = result.get("screenshots", []) or execution.get("screenshots", [])
            execution["console_logs"] = result.get("console_logs", [])
            execution["video_path"] = result.get("video_path", "")
            execution["har_path"] = result.get("har_path", "")
            execution["browser_mode"] = result.get("browser_mode", "")
            execution["network_type"] = result.get("network_type", "")
        except Exception as e:
            execution["status"] = TestStatus.ERROR.value
            execution["error_message"] = str(e)
        finally:
            execution["duration"] = round(time.time() - start, 3)
            execution["end_time"] = datetime.now().isoformat()
        return execution

    def _calculate_pass_rate(self, results: List[Dict]) -> float:
        return calculate_pass_rate(results, passed_status=TestStatus.PASSED.value)
