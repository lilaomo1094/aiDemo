# -*- coding: utf-8 -*-
"""版本迭代管理.

按版本组织需求文档与测试输出，支持版本清单维护、版本对比与快速切换.
"""

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


_VERSION_RE = re.compile(r"^v?\d+\.\d+(\.\d+)?(-[\w\-.]+)?$")


@dataclass
class VersionInfo:
    """单个版本元信息."""

    version: str
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    requirement_file: str = "requirement.md"
    config_file: Optional[str] = None
    output_dir: str = "output"
    parent_version: Optional[str] = None
    status: str = "draft"  # draft / testing / released / deprecated

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VersionManager:
    """管理 versions/ 目录下的多版本输入输出."""

    MANIFEST_NAME = "manifest.json"

    def __init__(self, base_dir: Union[str, Path], current_version: Optional[str] = None):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.base_dir / self.MANIFEST_NAME
        self._manifest: Dict[str, Any] = {"versions": []}
        self._load_manifest()
        self.current_version = current_version or self._manifest.get("current_version")

    def _load_manifest(self):
        if self.manifest_path.exists():
            try:
                self._manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            except Exception:
                self._manifest = {"versions": []}
        else:
            self._manifest = {"versions": []}

    def _save_manifest(self):
        self.manifest_path.write_text(
            json.dumps(self._manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_versions(self) -> List[str]:
        """返回所有已注册版本号."""
        return [v["version"] for v in self._manifest.get("versions", [])]

    def get_version_info(self, version: Optional[str] = None) -> Optional[VersionInfo]:
        """获取指定版本信息，默认取当前版本."""
        version = version or self.current_version
        if not version:
            return None
        for v in self._manifest.get("versions", []):
            if v["version"] == version:
                return VersionInfo(**v)
        return None

    def version_dir(self, version: Optional[str] = None) -> Path:
        """返回版本目录."""
        version = version or self.current_version or "default"
        return self.base_dir / version

    def requirement_path(self, version: Optional[str] = None) -> Path:
        """返回版本需求文档路径."""
        info = self.get_version_info(version)
        file_name = info.requirement_file if info else "requirement.md"
        return self.version_dir(version) / file_name

    def output_dir(self, version: Optional[str] = None) -> Path:
        """返回版本输出目录."""
        info = self.get_version_info(version)
        subdir = info.output_dir if info else "output"
        return self.version_dir(version) / subdir

    def config_path(self, version: Optional[str] = None) -> Optional[Path]:
        """返回版本专属配置文件路径，若不存在则返回 None."""
        info = self.get_version_info(version)
        if info and info.config_file:
            path = self.version_dir(version) / info.config_file
            if path.exists():
                return path
        return None

    def create_version(
        self,
        version: str,
        description: str = "",
        parent_version: Optional[str] = None,
        requirement_text: Optional[str] = None,
        requirement_file: str = "requirement.md",
        config_file: Optional[str] = None,
        status: str = "draft",
    ) -> VersionInfo:
        """创建新版本目录与清单."""
        version = self._normalize_version(version)
        if not _VERSION_RE.match(version):
            raise ValueError(f"版本号格式不正确: {version}，建议使用 v1.0.0 形式")

        if version in self.list_versions():
            raise ValueError(f"版本已存在: {version}")

        vdir = self.version_dir(version)
        vdir.mkdir(parents=True, exist_ok=True)
        (vdir / "output").mkdir(exist_ok=True)

        if requirement_text is not None:
            req_path = vdir / requirement_file
            req_path.write_text(requirement_text, encoding="utf-8")

        info = VersionInfo(
            version=version,
            description=description,
            requirement_file=requirement_file,
            config_file=config_file,
            output_dir="output",
            parent_version=parent_version,
            status=status,
        )
        self._manifest["versions"].append(info.to_dict())
        self._manifest["current_version"] = version
        self.current_version = version
        self._save_manifest()
        return info

    def set_current(self, version: str) -> bool:
        """切换当前版本."""
        version = self._normalize_version(version)
        if version not in self.list_versions():
            return False
        self._manifest["current_version"] = version
        self.current_version = version
        self._save_manifest()
        return True

    def compare_versions(self, from_version: str, to_version: str) -> Dict[str, Any]:
        """对比两个版本的需求文档与输出统计."""
        from_info = self.get_version_info(from_version)
        to_info = self.get_version_info(to_version)
        if not from_info or not to_info:
            raise ValueError("对比的版本不存在")

        from_req = self._read_requirement(from_version)
        to_req = self._read_requirement(to_version)

        from_results = self._read_results(from_version)
        to_results = self._read_results(to_version)

        return {
            "from_version": from_version,
            "to_version": to_version,
            "requirement_changed": from_req != to_req,
            "requirement_diff": {
                "from_length": len(from_req),
                "to_length": len(to_req),
            },
            "test_cases": {
                "from": len(from_results.get("test_cases", [])),
                "to": len(to_results.get("test_cases", [])),
            },
            "defects": {
                "from": len(from_results.get("defects", [])),
                "to": len(to_results.get("defects", [])),
            },
        }

    def _read_requirement(self, version: str) -> str:
        path = self.requirement_path(version)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _read_results(self, version: str) -> Dict[str, Any]:
        path = self.output_dir(version) / "results.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    @staticmethod
    def _normalize_version(version: str) -> str:
        version = version.strip().lower()
        if not version.startswith("v") and version[0].isdigit():
            version = f"v{version}"
        return version
