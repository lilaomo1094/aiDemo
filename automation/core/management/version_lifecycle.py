# -*- coding: utf-8 -*-
"""版本生命周期管理.

在 VersionManager 基础上扩展：阶段流转、基线、环境画像、资产索引、里程碑.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from automation.core.version import VersionManager


VERSION_STATUSES = ["draft", "testing", "released", "deprecated"]


@dataclass
class VersionBaseline:
    """版本基线：记录该版本锁定的需求、代码、环境信息."""

    version: str
    requirement_hash: str = ""
    code_ref: str = ""
    environment_profile: str = "public"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VersionAssetIndex:
    """版本资产索引."""

    version: str
    requirement_file: str = "requirement.md"
    config_file: Optional[str] = None
    test_cases: List[str] = field(default_factory=list)
    reports: List[str] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    videos: List[str] = field(default_factory=list)
    har_files: List[str] = field(default_factory=list)
    defects: List[str] = field(default_factory=list)
    results: List[str] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VersionLifecycleManager(VersionManager):
    """增强版版本管理器：支持生命周期、基线、资产索引."""

    BASELINE_FILE = "baseline.json"
    ASSETS_FILE = "assets.json"
    CONFIG_FILE = "config.json"

    def __init__(self, base_dir: Union[str, Path], current_version: Optional[str] = None):
        super().__init__(base_dir, current_version)

    def create_version(
        self,
        version: str,
        description: str = "",
        parent_version: Optional[str] = None,
        requirement_text: Optional[str] = None,
        requirement_file: str = "requirement.md",
        config_file: Optional[str] = None,
        status: str = "draft",
        environment_profile: str = "public",
    ):
        """创建版本并初始化基线与资产索引."""
        info = super().create_version(
            version=version,
            description=description,
            parent_version=parent_version,
            requirement_text=requirement_text,
            requirement_file=requirement_file,
            config_file=config_file,
            status=status,
        )
        self._write_baseline(
            VersionBaseline(
                version=info.version,
                environment_profile=environment_profile,
                notes="版本初始化",
            )
        )
        self._write_assets(
            VersionAssetIndex(version=info.version, requirement_file=requirement_file, config_file=self.CONFIG_FILE)
        )
        self.init_version_config(info.version, environment=environment_profile)
        return info

    def set_status(self, version: str, status: str) -> bool:
        """切换版本状态."""
        status = status.lower()
        if status not in VERSION_STATUSES:
            raise ValueError(f"不支持的状态: {status}，支持: {VERSION_STATUSES}")
        for v in self._manifest.get("versions", []):
            if v["version"] == version:
                v["status"] = status
                v["updated_at"] = datetime.now().isoformat()
                self._save_manifest()
                return True
        return False

    def promote(self, version: str, to_status: str, notes: str = "") -> bool:
        """推进版本到下一阶段，并记录基线."""
        if not self.set_status(version, to_status):
            return False
        baseline = self._read_baseline(version)
        if baseline:
            baseline.notes = notes or f"推进到 {to_status}"
            baseline.created_at = datetime.now().isoformat()
            self._write_baseline(baseline)
        return True

    def version_config_path(self, version: Optional[str] = None) -> Path:
        """返回版本专属配置文件路径（不存在也返回路径）."""
        return self.version_dir(version) / self.CONFIG_FILE

    def load_version_config(self, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """加载版本专属 JSON 配置."""
        path = self.version_config_path(version)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None

    def save_version_config(self, version: str, config: Dict[str, Any]):
        """保存版本专属 JSON 配置."""
        path = self.version_config_path(version)
        path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        self._update_asset_config(version, self.CONFIG_FILE)

    def init_version_config(self, version: str, environment: str = "dev") -> Dict[str, Any]:
        """初始化版本专属配置模板."""
        config = {
            "version": version,
            "description": "",
            "environment": environment,
            "sources": {
                "swagger": {
                    "enabled": False,
                    "url": "",
                    "file_path": "",
                    "format": "openapi",
                },
                "frontend_repo": {
                    "enabled": False,
                    "type": "github",
                    "url": "",
                    "branch": "main",
                    "language": "react",
                    "test_framework": "jest",
                    "api_spec": "",
                    "local_path": "",
                },
                "backend_repo": {
                    "enabled": False,
                    "type": "github",
                    "url": "",
                    "branch": "main",
                    "language": "python",
                    "test_framework": "pytest",
                    "api_spec": "",
                    "local_path": "",
                },
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        self.save_version_config(version, config)
        return config

    def get_version_sources(self, version: Optional[str] = None) -> Dict[str, Any]:
        """获取版本的输入源配置（Swagger、前后端仓库）."""
        cfg = self.load_version_config(version)
        if cfg:
            return cfg.get("sources", {})
        return {}

    def update_version_sources(self, version: str, sources: Dict[str, Any]):
        """更新版本的输入源配置."""
        cfg = self.load_version_config(version) or self.init_version_config(version)
        cfg["sources"] = sources
        cfg["updated_at"] = datetime.now().isoformat()
        self.save_version_config(version, cfg)

    def ensure_version_config(self, version: Optional[str] = None, environment: str = "dev") -> Dict[str, Any]:
        """确保版本配置文件存在，不存在则初始化."""
        version = version or self.current_version
        cfg = self.load_version_config(version)
        if cfg is None:
            cfg = self.init_version_config(version, environment)
        return cfg

    def update_assets(self, version: str, asset_type: str, file_path: Union[str, Path]):
        """更新版本资产索引."""
        assets = self._read_assets(version)
        rel_path = str(Path(file_path).relative_to(self.version_dir(version)))
        mapping = {
            "test_cases": "test_cases",
            "report": "reports",
            "screenshot": "screenshots",
            "video": "videos",
            "har": "har_files",
            "defect": "defects",
            "result": "results",
            "config": "config_file",
        }
        key = mapping.get(asset_type)
        if not key:
            return
        if key == "config_file":
            assets.config_file = rel_path
        else:
            lst = getattr(assets, key)
            if rel_path not in lst:
                lst.append(rel_path)
        assets.updated_at = datetime.now().isoformat()
        self._write_assets(assets)

    def get_assets(self, version: Optional[str] = None) -> VersionAssetIndex:
        """获取版本资产索引."""
        return self._read_assets(version)

    def get_baseline(self, version: Optional[str] = None) -> Optional[VersionBaseline]:
        """获取版本基线."""
        return self._read_baseline(version)

    def _read_baseline(self, version: Optional[str] = None) -> Optional[VersionBaseline]:
        path = self.version_dir(version) / self.BASELINE_FILE
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return VersionBaseline(**data)
            except Exception:
                pass
        return None

    def _write_baseline(self, baseline: VersionBaseline):
        path = self.version_dir(baseline.version) / self.BASELINE_FILE
        path.write_text(json.dumps(baseline.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def _read_assets(self, version: Optional[str] = None) -> VersionAssetIndex:
        version = version or self.current_version or "default"
        path = self.version_dir(version) / self.ASSETS_FILE
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return VersionAssetIndex(**data)
            except Exception:
                pass
        return VersionAssetIndex(version=version)

    def _write_assets(self, assets: VersionAssetIndex):
        path = self.version_dir(assets.version) / self.ASSETS_FILE
        path.write_text(json.dumps(assets.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def _update_asset_config(self, version: str, config_file: str):
        assets = self._read_assets(version)
        assets.config_file = config_file
        assets.updated_at = datetime.now().isoformat()
        self._write_assets(assets)
