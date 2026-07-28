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
