# -*- coding: utf-8 -*-
"""真实 API 测试执行器."""

import json
from typing import Any, Dict

import requests

from .base import TestExecutor, TestStatus


class APIExecutor(TestExecutor):
    def __init__(self, config):
        super().__init__(config)
        self.base_url = getattr(config, "api_base_url", None) or getattr(config, "extra", {}).get("api_base_url", "")
        self.timeout = getattr(config, "test", None).timeout if hasattr(config, "test") else 30

    def execute(self, test_case: Dict, context) -> Dict[str, Any]:
        step = test_case.get("action", {}) or test_case.get("test_data", {})
        method = (step.get("method") or test_case.get("method", "GET")).upper()
        path = step.get("path") or test_case.get("path", "/")
        url = self._build_url(path)
        headers = step.get("headers", {})
        data = step.get("data") or step.get("body", {})
        expected_status = step.get("expected_status")
        if expected_status is None:
            expected_status = test_case.get("expected_status")
        expected_status = int(expected_status) if expected_status is not None else None

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data if data and method != "GET" else None,
                params=data if data and method == "GET" else None,
                timeout=self.timeout,
            )
            actual_status = response.status_code
            try:
                resp_body = response.json()
            except Exception:
                resp_body = response.text

            if expected_status is not None and actual_status != expected_status:
                return self._make_result(
                    TestStatus.FAILED,
                    f"期望状态码 {expected_status}，实际 {actual_status}",
                    status_code=actual_status,
                    response=resp_body,
                )
            return self._make_result(
                TestStatus.PASSED,
                "API 调用成功",
                status_code=actual_status,
                response=resp_body,
            )
        except requests.RequestException as e:
            return self._make_result(TestStatus.ERROR, f"请求异常: {e}")

    def _build_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        base = self.base_url or ""
        return f"{base.rstrip('/')}/{path.lstrip('/')}"
