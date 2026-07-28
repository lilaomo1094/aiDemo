# -*- coding: utf-8 -*-
"""UI 测试执行器（基于 Playwright，支持内网/公网多环境）."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from automation.core.network import NetworkManager

from .base import TestExecutor, TestStatus


class UIExecutor(TestExecutor):
    def __init__(self, config):
        super().__init__(config)
        self.base_url = getattr(config, "extra", {}).get("ui_base_url", "")
        self.screenshot_enabled = getattr(config, "extra", {}).get("ui_auto_screenshot", True)
        self.network = NetworkManager(config)

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

    def _use_local_browser(self) -> bool:
        """判断是否使用本地已安装浏览器（Edge/Chrome）而非 Playwright 下载的 Chromium."""
        browser_type = self.network.profile.browser_type
        return browser_type in {"edge", "chrome"} and not self.network.profile.local_browser_path

    def _launch_browser(self, playwright, launch_kwargs: Dict):
        """根据 browser_type 启动对应浏览器（chromium/firefox/webkit）."""
        browser_type = self.network.profile.browser_type
        if browser_type in {"firefox", "mozilla", "gecko"}:
            return playwright.firefox.launch(**launch_kwargs)
        if browser_type in {"safari", "webkit", "apple"}:
            return playwright.webkit.launch(**launch_kwargs)
        return playwright.chromium.launch(**launch_kwargs)

    def _resolve_output_dir(self, context, test_case: Dict) -> Path:
        """确定本次用例的输出目录：优先版本化输出目录."""
        run_id = getattr(context, "run_id", "unknown")
        test_id = test_case.get("id", "unknown")
        base_dir = getattr(self.config, "base_dir", Path.cwd())
        output_dir = base_dir / "output"
        report_file = getattr(getattr(self.config, "output", None), "report_file", None)
        if report_file:
            report_path = Path(report_file)
            if report_path.parent.exists():
                output_dir = report_path.parent
        return output_dir / "ui_evidence" / run_id / test_id

    def _take_screenshot(self, page, output_dir: Path, name: str) -> str:
        """截图并返回相对路径."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{name}_{timestamp}.png"
        full_path = output_dir / filename
        page.screenshot(path=str(full_path))
        base_dir = getattr(self.config, "base_dir", Path.cwd())
        try:
            return str(full_path.relative_to(base_dir))
        except ValueError:
            return str(full_path)

    def _collect_console_logs(self, page) -> List[Dict[str, Any]]:
        """收集浏览器控制台日志."""
        if not self.network.profile.capture_console:
            return []
        logs = []
        for log in page.event_data.get("console", []) if hasattr(page, "event_data") else []:
            logs.append({"type": log.type, "text": log.text})
        return logs

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

        # 关键场景强制截图与监控
        capture = action.get("capture_screenshots", self.screenshot_enabled)
        is_critical = test_case.get("critical", False) or "登录" in test_case.get("name", "")
        if is_critical:
            capture = True
            # 登录类关键场景默认开启控制台与网络监控
            if not self.network.profile.capture_console:
                self.network.profile.capture_console = True

        # 若使用 Playwright Chromium 且未找到浏览器，尝试自动安装一次
        executable_path = ""
        if not self._use_local_browser():
            executable_path = self._find_chromium_executable()
            if not executable_path:
                self._install_browsers()
                executable_path = self._find_chromium_executable()

        output_dir = self._resolve_output_dir(context, test_case)
        output_dir.mkdir(parents=True, exist_ok=True)

        launch_kwargs, actually_headed = self.network.resolve_browser_launch_kwargs(executable_path)
        video_dir = output_dir / "video" if self.network.profile.record_video else None

        # HAR 录制文件路径提前准备好，避免重复创建 context
        har_file = None
        if self.network.profile.record_har:
            har_file = output_dir / f"trace_{datetime.now().strftime('%Y%m%d%H%M%S')}.har"

        context_kwargs = self.network.resolve_browser_context_kwargs(video_dir)
        if har_file:
            context_kwargs["record_har_path"] = str(har_file)

        screenshots: List[str] = []
        console_logs: List[Dict] = []
        har_path: str = ""
        video_path: str = ""

        try:
            with sync_playwright() as p:
                browser = self._launch_browser(p, launch_kwargs)
                ctx = browser.new_context(**context_kwargs)

                page = ctx.new_page()
                if self.network.profile.capture_console:
                    page.on("console", lambda msg: console_logs.append({"type": msg.type, "text": msg.text}))
                if self.network.profile.capture_network:
                    page.on("request", lambda req: console_logs.append({"type": "network", "text": f"{req.method} {req.url}"}))

                page.goto(url, timeout=30000, wait_until="domcontentloaded")

                if capture:
                    screenshots.append(self._take_screenshot(page, output_dir, "01_opened"))

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
                            screenshots.append(self._take_screenshot(page, output_dir, f"{idx:02d}_{step_name}_failed"))
                        ctx.close()
                        browser.close()
                        return self._make_result(
                            TestStatus.FAILED,
                            f"步骤 {step_name} 失败: {step_err}",
                            steps=results,
                            screenshots=screenshots,
                            console_logs=console_logs,
                        )

                    if capture and step.get("capture_after", False):
                        screenshots.append(self._take_screenshot(page, output_dir, f"{idx:02d}_{step_name}"))

                if capture:
                    screenshots.append(self._take_screenshot(page, output_dir, f"{len(steps)+2:02d}_success"))

                explicit_screenshot = action.get("screenshot")
                if explicit_screenshot:
                    page.screenshot(path=str(output_dir / explicit_screenshot))

                page.close()
                ctx.close()
                browser.close()

                if har_file and har_file.exists():
                    try:
                        har_path = str(har_file.relative_to(getattr(self.config, "base_dir", Path.cwd())))
                    except ValueError:
                        har_path = str(har_file)

                # 收集视频路径
                if video_dir and video_dir.exists():
                    videos = sorted(video_dir.glob("*.webm"))
                    if videos:
                        try:
                            video_path = str(videos[0].relative_to(getattr(self.config, "base_dir", Path.cwd())))
                        except ValueError:
                            video_path = str(videos[0])

                return self._make_result(
                    TestStatus.PASSED,
                    "UI 测试通过",
                    steps=results,
                    screenshots=screenshots,
                    console_logs=console_logs,
                    video_path=video_path,
                    har_path=har_path,
                    browser_mode="headed" if actually_headed else "headless",
                    network_type=self.network.profile.network_type.value,
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
                console_logs=console_logs,
                network_type=self.network.profile.network_type.value,
            )
