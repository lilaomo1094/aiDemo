# -*- coding: utf-8 -*-
"""执行环境画像与策略.

根据公网/内网/VPN 环境，自动调整浏览器模式、录制策略、代理、慢速模式等.
"""

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from automation.core.config import NetworkConfig, PlatformConfig


@dataclass
class ExecutionProfile:
    """环境执行画像."""

    network_type: str = "public"  # public | private | vpn
    browser_mode: str = "headless"
    browser_type: str = "chromium"
    local_browser_path: Optional[str] = None
    record_video: bool = False
    record_har: bool = False
    capture_console: bool = True
    capture_network: bool = False
    slow_mo: int = 0
    proxy: Optional[str] = None
    bypass_hosts: list = field(default_factory=list)
    execution_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "network_type": self.network_type,
            "browser_mode": self.browser_mode,
            "browser_type": self.browser_type,
            "local_browser_path": self.local_browser_path,
            "record_video": self.record_video,
            "record_har": self.record_har,
            "capture_console": self.capture_console,
            "capture_network": self.capture_network,
            "slow_mo": self.slow_mo,
            "proxy": self.proxy,
            "bypass_hosts": self.bypass_hosts,
            "execution_notes": self.execution_notes,
        }


class EnvironmentProfileManager:
    """根据环境类型生成执行策略，并检测本地浏览器可用性."""

    DEFAULT_PROFILES = {
        "public": {
            "browser_mode": "headless",
            "record_video": False,
            "record_har": False,
            "capture_console": True,
            "capture_network": False,
            "slow_mo": 0,
        },
        "private": {
            "browser_mode": "headed",
            "record_video": True,
            "record_har": True,
            "capture_console": True,
            "capture_network": True,
            "slow_mo": 500,
        },
        "vpn": {
            "browser_mode": "headed",
            "record_video": True,
            "record_har": True,
            "capture_console": True,
            "capture_network": True,
            "slow_mo": 800,
        },
    }

    def __init__(self, config: PlatformConfig):
        self.config = config
        self.network: NetworkConfig = getattr(config, "network", NetworkConfig())

    def build_profile(self, override_type: Optional[str] = None) -> ExecutionProfile:
        """生成当前环境的执行画像."""
        network_type = (override_type or self.network.type or "public").lower()
        profile_defaults = self.DEFAULT_PROFILES.get(network_type, self.DEFAULT_PROFILES["public"])

        profile = ExecutionProfile(
            network_type=network_type,
            browser_mode=self.network.browser_mode or profile_defaults["browser_mode"],
            browser_type=self.network.browser_type or "chromium",
            local_browser_path=self.network.local_browser_path,
            record_video=self.network.record_video if self.network.record_video else profile_defaults["record_video"],
            record_har=self.network.record_har if self.network.record_har else profile_defaults["record_har"],
            capture_console=self.network.capture_console,
            capture_network=self.network.capture_network if self.network.capture_network else profile_defaults["capture_network"],
            slow_mo=self.network.slow_mo if self.network.slow_mo else profile_defaults["slow_mo"],
            proxy=self.network.proxy,
            bypass_hosts=list(self.network.bypass_hosts or []),
        )

        # 内网场景必须能监控本地浏览器：若指定 local_browser_path 不存在，尝试自动发现
        if network_type in {"private", "vpn"}:
            profile = self._ensure_local_browser(profile)
            profile.execution_notes = "内网执行：启用本地浏览器可视化监控"
        else:
            profile.execution_notes = "公网执行：默认 headless 模式"

        return profile

    def apply_to_config(self, profile: ExecutionProfile):
        """将画像应用到 PlatformConfig."""
        self.network.type = profile.network_type
        self.network.browser_mode = profile.browser_mode
        self.network.browser_type = profile.browser_type
        self.network.local_browser_path = profile.local_browser_path
        self.network.record_video = profile.record_video
        self.network.record_har = profile.record_har
        self.network.capture_console = profile.capture_console
        self.network.capture_network = profile.capture_network
        self.network.slow_mo = profile.slow_mo
        self.network.proxy = profile.proxy
        self.network.bypass_hosts = profile.bypass_hosts

    def detect_local_browser(self, browser_type: str = "edge") -> Optional[str]:
        """探测本地浏览器可执行文件路径."""
        candidates = self._browser_candidates(browser_type)
        for candidate in candidates:
            path = shutil.which(candidate)
            if path:
                return path
            if Path(candidate).exists():
                return str(Path(candidate).resolve())
        return None

    def _ensure_local_browser(self, profile: ExecutionProfile) -> ExecutionProfile:
        if profile.local_browser_path and Path(profile.local_browser_path).exists():
            return profile
        detected = self.detect_local_browser(profile.browser_type)
        if detected:
            profile.local_browser_path = detected
            profile.browser_mode = "headed"
        else:
            profile.execution_notes += "；未检测到本地浏览器，将使用 Playwright 内置 Chromium"
        return profile

    def _browser_candidates(self, browser_type: str):
        browser_type = (browser_type or "edge").lower()
        if browser_type == "edge":
            return ["msedge", "microsoft-edge", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
        if browser_type == "chrome":
            return ["chrome", "google-chrome", r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]
        return [browser_type]
