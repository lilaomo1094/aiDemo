# -*- coding: utf-8 -*-
"""网络环境管理：支持公网、内网、VPN 等不同网络场景下的测试执行."""

import os
import shutil
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class NetworkType(str, Enum):
    PUBLIC = "public"    # 公网环境
    PRIVATE = "private"  # 公司内网
    VPN = "vpn"          # 通过 VPN 接入内网


class BrowserMode(str, Enum):
    HEADED = "headed"      # 有界面浏览器，便于本地监控
    HEADLESS = "headless"  # 无头浏览器，适用于 CI/公网


class NetworkProfile:
    """单次测试使用的网络环境配置."""

    def __init__(
        self,
        network_type: NetworkType = NetworkType.PUBLIC,
        browser_mode: BrowserMode = BrowserMode.HEADLESS,
        proxy: Optional[str] = None,
        bypass_hosts: Optional[List[str]] = None,
        record_video: bool = False,
        record_har: bool = False,
        capture_console: bool = True,
        capture_network: bool = False,
        slow_mo: int = 0,
        local_browser_path: Optional[str] = None,
    ):
        self.network_type = network_type
        self.browser_mode = browser_mode
        self.proxy = proxy
        self.bypass_hosts = bypass_hosts or []
        self.record_video = record_video
        self.record_har = record_har
        self.capture_console = capture_console
        self.capture_network = capture_network
        self.slow_mo = slow_mo
        self.local_browser_path = local_browser_path

    @property
    def is_private(self) -> bool:
        return self.network_type in {NetworkType.PRIVATE, NetworkType.VPN}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "network_type": self.network_type.value,
            "browser_mode": self.browser_mode.value,
            "proxy": self.proxy,
            "bypass_hosts": self.bypass_hosts,
            "record_video": self.record_video,
            "record_har": self.record_har,
            "capture_console": self.capture_console,
            "capture_network": self.capture_network,
            "slow_mo": self.slow_mo,
            "local_browser_path": self.local_browser_path,
        }


class NetworkManager:
    """根据配置构造 Playwright / Selenium 等浏览器启动参数."""

    def __init__(self, config):
        raw = getattr(config, "network", None)
        if raw is None:
            raw = {}
        elif hasattr(raw, "model_dump"):
            raw = raw.model_dump()
        self.config = raw
        self.profile = self._build_profile()

    def _build_profile(self) -> NetworkProfile:
        network_type = NetworkType(self.config.get("type", "public").lower())
        browser_mode = BrowserMode(self.config.get("browser_mode", "headless").lower())

        # 内网场景默认开启本地监控能力
        is_private = network_type in {NetworkType.PRIVATE, NetworkType.VPN}
        record_video = self.config.get("record_video", is_private)
        record_har = self.config.get("record_har", is_private)
        capture_console = self.config.get("capture_console", True)
        capture_network = self.config.get("capture_network", is_private)
        slow_mo = self.config.get("slow_mo", 300 if is_private else 0)

        # 内网默认使用有界面浏览器以便监控；无图形环境时会自动回退
        if is_private and browser_mode == BrowserMode.HEADLESS:
            browser_mode = BrowserMode.HEADED

        return NetworkProfile(
            network_type=network_type,
            browser_mode=browser_mode,
            proxy=self.config.get("proxy") or None,
            bypass_hosts=self.config.get("bypass_hosts", []),
            record_video=record_video,
            record_har=record_har,
            capture_console=capture_console,
            capture_network=capture_network,
            slow_mo=slow_mo,
            local_browser_path=self.config.get("local_browser_path") or None,
        )

    def resolve_browser_launch_kwargs(self, executable_path: str = "") -> Tuple[Dict[str, Any], bool]:
        """返回 (playwright launch kwargs, 是否实际使用 headed)."""
        headless = self.profile.browser_mode == BrowserMode.HEADLESS
        args = ["--disable-blink-features=AutomationControlled"]
        actually_headed = not headless

        # Linux 无图形环境时， headed 浏览器无法直接启动，自动回退到 headless
        # 同时保留视频录制作为本地监控手段
        if actually_headed and os.name == "posix" and not os.environ.get("DISPLAY"):
            actually_headed = False
            headless = True

        kwargs = {
            "headless": headless,
            "args": args,
            "slow_mo": self.profile.slow_mo,
        }
        if executable_path:
            kwargs["executable_path"] = executable_path
        elif self.profile.local_browser_path:
            kwargs["executable_path"] = self.profile.local_browser_path

        return kwargs, actually_headed

    def resolve_browser_context_kwargs(self, video_dir: Optional[Path] = None) -> Dict[str, Any]:
        """返回 playwright browser.new_context 参数."""
        kwargs: Dict[str, Any] = {
            "viewport": {"width": 1366, "height": 768},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
        }

        if self.profile.proxy:
            kwargs["proxy"] = {"server": self.profile.proxy}
            if self.profile.bypass_hosts:
                kwargs["proxy"]["bypass"] = ",".join(self.profile.bypass_hosts)

        if self.profile.record_video and video_dir:
            kwargs["record_video_dir"] = str(video_dir)
            kwargs["record_video_size"] = {"width": 1280, "height": 720}

        return kwargs

    def should_wrap_with_xvfb(self) -> bool:
        """Linux 无 DISPLAY 且需要 headed 时，需要 xvfb-run 包装."""
        if os.name != "posix":
            return False
        if self.profile.browser_mode != BrowserMode.HEADED:
            return False
        return not os.environ.get("DISPLAY") and shutil.which("xvfb-run") is not None


class XvfbRunner:
    """在 Linux 无图形环境下使用 xvfb 运行需要 headed 浏览器的命令."""

    @staticmethod
    def wrap(command: List[str]) -> List[str]:
        if shutil.which("xvfb-run"):
            return ["xvfb-run", "--auto-servernum", "--server-args=-screen 0 1366x768x24"] + command
        return command
