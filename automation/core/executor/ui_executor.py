# -*- coding: utf-8 -*-
"""UI 测试执行器（基于 Playwright，可选安装）."""

from typing import Any, Dict

from .base import TestExecutor, TestStatus


class UIExecutor(TestExecutor):
    def __init__(self, config):
        super().__init__(config)
        self.base_url = getattr(config, "extra", {}).get("ui_base_url", "")

    def _find_chromium_executable(self) -> str:
        """查找 Playwright 下载的 Chromium 可执行文件路径."""
        from pathlib import Path
        cache_root = Path.home() / ".cache" / "ms-playwright"
        for name in sorted(cache_root.iterdir() if cache_root.exists() else [], reverse=True):
            candidate = name / "chrome-linux64" / "chrome"
            if candidate.exists():
                return str(candidate)
        return ""

    def execute(self, test_case: Dict, context) -> Dict[str, Any]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return self._make_result(TestStatus.SKIPPED, "未安装 playwright，跳过 UI 测试")

        action = test_case.get("action", {}) or test_case.get("test_data", {})
        url = action.get("url") or test_case.get("url", self.base_url)
        steps = action.get("steps") or test_case.get("steps", [])

        try:
            with sync_playwright() as p:
                executable_path = self._find_chromium_executable()
                browser = p.chromium.launch(headless=True, executable_path=executable_path)
                page = browser.new_page()
                page.goto(url)
                results = []
                for step in steps:
                    op = step.get("op")
                    selector = step.get("selector", "")
                    value = step.get("value", "")
                    if op == "fill":
                        page.fill(selector, value)
                    elif op == "click":
                        page.click(selector)
                    elif op == "assert_text":
                        page.wait_for_selector(selector, timeout=10000)
                        text = page.inner_text(selector)
                        assert value in text, f"未找到期望文本: {value}"
                    results.append({"op": op, "selector": selector, "status": "ok"})
                browser.close()
                return self._make_result(TestStatus.PASSED, "UI 测试通过", steps=results)
        except Exception as e:
            return self._make_result(TestStatus.ERROR, f"UI 测试失败: {e}")
