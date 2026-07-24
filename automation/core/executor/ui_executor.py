# -*- coding: utf-8 -*-
"""UI 测试执行器（基于 Playwright，可选安装）."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .base import TestExecutor, TestStatus


class UIExecutor(TestExecutor):
    def __init__(self, config):
        super().__init__(config)
        self.base_url = getattr(config, "extra", {}).get("ui_base_url", "")
        self.screenshot_enabled = getattr(config, "extra", {}).get("ui_auto_screenshot", True)

    def _find_chromium_executable(self) -> str:
        """查找 Playwright 下载的 Chromium 可执行文件路径."""
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

    def _resolve_screenshot_dir(self, context, test_case: Dict) -> Path:
        """确定截图保存目录：优先版本化输出目录，回退 output/screenshots."""
        run_id = getattr(context, "run_id", "unknown")
        test_id = test_case.get("id", "unknown")
        base_dir = getattr(self.config, "base_dir", Path.cwd())
        output_dir = base_dir / "output"
        # 若配置中有版本化报告路径，则放在同版本目录下
        report_file = getattr(getattr(self.config, "output", None), "report_file", None)
        if report_file:
            report_path = Path(report_file)
            if report_path.parent.exists():
                output_dir = report_path.parent
        screenshot_dir = output_dir / "screenshots" / run_id / test_id
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        return screenshot_dir

    def _take_screenshot(self, page, screenshot_dir: Path, name: str) -> str:
        """截图并返回相对路径."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{name}_{timestamp}.png"
        full_path = screenshot_dir / filename
        page.screenshot(path=str(full_path))
        base_dir = getattr(self.config, "base_dir", Path.cwd())
        try:
            rel_path = str(full_path.relative_to(base_dir))
        except ValueError:
            rel_path = str(full_path)
        return rel_path

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

        # 是否启用关键场景截图：test_case 显式指定，或全局开启
        capture = action.get("capture_screenshots", self.screenshot_enabled)
        is_critical = test_case.get("critical", False) or "登录" in test_case.get("name", "")
        if is_critical:
            capture = True

        # 若未找到浏览器，尝试自动安装一次
        executable_path = self._find_chromium_executable()
        if not executable_path:
            self._install_browsers()
            executable_path = self._find_chromium_executable()

        launch_kwargs = {"headless": True}
        if executable_path:
            launch_kwargs["executable_path"] = executable_path

        screenshots: List[str] = []
        screenshot_dir = self._resolve_screenshot_dir(context, test_case)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(**launch_kwargs)
                page = browser.new_page()
                page.goto(url, timeout=30000, wait_until="domcontentloaded")

                if capture:
                    screenshots.append(self._take_screenshot(page, screenshot_dir, "01_opened"))

                results = []
                for idx, step in enumerate(steps, start=2):
                    op = step.get("op")
                    selector = step.get("selector", "")
                    value = step.get("value", "")
                    timeout = step.get("timeout", 10000)
                    step_name = step.get("name", f"step_{idx}_{op}")
                    try:
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
                    except Exception as step_err:
                        results.append({"op": op, "selector": selector, "status": "failed", "error": str(step_err)})
                        if capture:
                            screenshots.append(self._take_screenshot(page, screenshot_dir, f"{idx:02d}_{step_name}_failed"))
                        browser.close()
                        return self._make_result(
                            TestStatus.FAILED,
                            f"步骤 {step_name} 失败: {step_err}",
                            steps=results,
                            screenshots=screenshots,
                        )

                    # 关键步骤完成后截图
                    if capture and step.get("capture_after", False):
                        screenshots.append(self._take_screenshot(page, screenshot_dir, f"{idx:02d}_{step_name}"))

                # 用例整体成功完成后截图
                if capture:
                    screenshots.append(self._take_screenshot(page, screenshot_dir, f"{len(steps)+2:02d}_success"))

                # 支持用例级别显式指定最终截图
                explicit_screenshot = action.get("screenshot")
                if explicit_screenshot:
                    page.screenshot(path=str(screenshot_dir / explicit_screenshot))

                browser.close()
                return self._make_result(
                    TestStatus.PASSED,
                    "UI 测试通过",
                    steps=results,
                    screenshots=screenshots,
                )
        except Exception as e:
            err_msg = str(e)
            if "ERR_CONNECTION_CLOSED" in err_msg or "ERR_CONNECTION_REFUSED" in err_msg:
                err_msg = f"无法访问目标地址 {url}，请检查网络连通性或域名解析"
            elif "executable" in err_msg.lower() or "browser" in err_msg.lower():
                err_msg = f"本地浏览器未正确安装: {err_msg}，请执行 'playwright install chromium'"
            return self._make_result(
                TestStatus.ERROR,
                f"UI 测试失败: {err_msg}",
                screenshots=screenshots,
            )
