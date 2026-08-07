# -*- coding: utf-8 -*-
"""UI 执行器单元测试."""

from unittest.mock import MagicMock

import pytest

from automation.core.config import PlatformConfig
from automation.core.executor import UIExecutor
from automation.core.network import NetworkProfile


@pytest.fixture
def ui_config():
    config = PlatformConfig()
    config.extra["ui_base_url"] = "http://test.local"
    return config


def test_ui_executor_uses_chromium_by_default(ui_config):
    executor = UIExecutor(ui_config)
    mock_playwright = MagicMock()
    executor._launch_browser(mock_playwright, {"headless": True})
    mock_playwright.chromium.launch.assert_called_once_with(headless=True)


def test_ui_executor_uses_firefox(ui_config):
    ui_config.network = {"type": "public", "browser_type": "firefox"}
    executor = UIExecutor(ui_config)
    mock_playwright = MagicMock()
    executor._launch_browser(mock_playwright, {"headless": True})
    mock_playwright.firefox.launch.assert_called_once_with(headless=True)


def test_ui_executor_uses_webkit(ui_config):
    ui_config.network = {"type": "public", "browser_type": "safari"}
    executor = UIExecutor(ui_config)
    mock_playwright = MagicMock()
    executor._launch_browser(mock_playwright, {"headless": True})
    mock_playwright.webkit.launch.assert_called_once_with(headless=True)


def test_ui_executor_local_browser_detection(ui_config):
    ui_config.network = {"type": "public", "browser_type": "edge"}
    executor = UIExecutor(ui_config)
    assert executor._use_local_browser() is True


def test_ui_executor_missing_url_returns_blocked(ui_config):
    ui_config.extra.pop("ui_base_url", None)
    executor = UIExecutor(ui_config)
    result = executor.execute({"name": "test"}, None)
    assert result["status"] == "blocked"


def test_ui_executor_safe_close_ignores_exceptions():
    failing = MagicMock()
    failing.close.side_effect = RuntimeError("close failed")
    executor = UIExecutor(PlatformConfig())
    # 不应抛出异常
    executor._safe_close(failing, failing, failing)
    assert failing.close.call_count == 3


def test_install_browsers_passes_timeout_to_subprocess(monkeypatch):
    """回归测试：_install_browsers 必须给 subprocess.run 设置 timeout.

    旧实现调用 playwright install chromium 时不带 timeout，在网络卡顿/代理劫持
    时会无限阻塞，挂死整个 UI 执行器。
    """
    captured = {}
    import subprocess

    def fake_run(cmd, **kwargs):
        captured.update(kwargs)
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    executor = UIExecutor(PlatformConfig())
    assert executor._install_browsers() is True
    assert captured.get("timeout") is not None, "subprocess.run 必须设置 timeout 避免无限阻塞"
    assert captured["timeout"] > 0
