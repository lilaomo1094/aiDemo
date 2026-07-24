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

    def _install_browsers(self) -> bool:
        """尝试自动安装 Playwright Chromium 浏览器."""
        try:
            import subprocess
            subprocess.run(
                ["playwright", "install", "chromium"],
                check=True,
                capture_output=True,
                text=True,
            )
            return True
        except Exception:
            return False

    def execute(self, test_case: Dict, context) -> Dict[str, Any]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return self._make_result(TestStatus.SKIPPED, "未安装 playwright，跳过 UI 测试")

        action = test_case.get("action", {}) or test_case.get("test_data", {})
        url = action.get("url") or test_case.get("url", self.base_url)
        steps = action.get("steps") or test_case.get("steps", [])
        if not url:
            return self._make_result(TestStatus.BLOCKED, "未配置 UI 测试目标 URL")

        # 若未找到浏览器，尝试自动安装一次
        executable_path = self._find_chromium_executable()
        if not executable_path:
            self._install_browsers()
            executable_path = self._find_chromium_executable()

        launch_kwargs = {"headless": True}
        if executable_path:
            launch_kwargs["executable_path"] = executable_path

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(**launch_kwargs)
                page = browser.new_page()
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                results = []
                screenshot_path = action.get("screenshot")
                for step in steps:
                    op = step.get("op")
                    selector = step.get("selector", "")
                    value = step.get("value", "")
                    timeout = step.get("timeout", 10000)
                    if op == "fill":
                        page.fill(selector, value)
                    elif op == "click":
                        page.click(selector)
                    elif op == "select":
                        page.select_option(selector, value)
                    elif op == "wait":
                        page.wait_for_selector(selector, timeout=timeout)
                    elif op == "assert_text":
                        page.wait_for_selector(selector, timeout=timeout)
                        text = page.inner_text(selector)
                        assert value in text, f"未找到期望文本: {value}"
                    elif op == "assert_visible":
                        page.wait_for_selector(selector, state="visible", timeout=timeout)
                    else:
                        results.append({"op": op, "selector": selector, "status": "unknown"})
                        continue
                    results.append({"op": op, "selector": selector, "status": "ok"})
                if screenshot_path:
                    page.screenshot(path=screenshot_path)
                browser.close()
                return self._make_result(TestStatus.PASSED, "UI 测试通过", steps=results)
        except Exception as e:
            err_msg = str(e)
            if "ERR_CONNECTION_CLOSED" in err_msg or "ERR_CONNECTION_REFUSED" in err_msg:
                err_msg = f"无法访问目标地址 {url}，请检查网络连通性或域名解析"
            elif "executable" in err_msg.lower() or "browser" in err_msg.lower():
                err_msg = f"本地浏览器未正确安装: {err_msg}，请执行 'playwright install chromium'"
            return self._make_result(TestStatus.ERROR, f"UI 测试失败: {err_msg}")
