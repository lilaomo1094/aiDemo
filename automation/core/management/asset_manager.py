# -*- coding: utf-8 -*-
"""测试资产管理.

汇总版本级测试资产：需求、用例、报告、截图、视频、HAR、缺陷、结果.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from automation.core.management.version_lifecycle import VersionLifecycleManager


class AssetManager:
    """测试资产管理器."""

    def __init__(self, version_manager: VersionLifecycleManager):
        self.version_manager = version_manager

    def index_version_assets(self, version: Optional[str] = None) -> Dict[str, Any]:
        """扫描版本目录，重建资产索引."""
        version = version or self.version_manager.current_version
        vdir = self.version_manager.version_dir(version)
        output_dir = self.version_manager.output_dir(version)

        assets = {
            "version": version,
            "requirement_file": str(self.version_manager.requirement_path(version).relative_to(vdir.parent)),
            "config_file": None,
            "swagger": self._collect_files(vdir, ["*.json", "*.yaml", "*.yml"], filter_name="swagger"),
            "frontend_repo": self._collect_files(vdir, ["*"], filter_name="frontend_repo"),
            "backend_repo": self._collect_files(vdir, ["*"], filter_name="backend_repo"),
            "test_cases": self._collect_files(output_dir, ["*test_cases*"]),
            "reports": self._collect_files(output_dir, ["*report*"]),
            "screenshots": self._collect_files(output_dir, ["*.png", "*.jpg", "*.jpeg", "*.webp"]),
            "videos": self._collect_files(output_dir, ["*.webm", "*.mp4"]),
            "har_files": self._collect_files(output_dir, ["*.har"]),
            "defects": self._collect_files(output_dir, ["*defect*"]),
            "results": self._collect_files(output_dir, ["results.json"]),
            "updated_at": datetime.now().isoformat(),
        }

        config_path = self.version_manager.version_config_path(version)
        if config_path.exists():
            config_rel = str(config_path.relative_to(vdir))
            assets["config_file"] = config_rel
            self.version_manager._update_asset_config(version, config_rel)
            try:
                cfg = json.loads(config_path.read_text(encoding="utf-8"))
                sources = cfg.get("sources", {})
                for key in ["swagger", "frontend_repo", "backend_repo"]:
                    src = sources.get(key, {})
                    if src.get("enabled"):
                        assets[key] = {
                            "enabled": True,
                            "url": src.get("url", ""),
                            "file_path": src.get("file_path", ""),
                            "local_path": src.get("local_path", ""),
                            "branch": src.get("branch", ""),
                        }
            except Exception:
                pass

        self._sync_to_lifecycle(version, assets)
        return assets

    def collect_run_output(self, version: str, output_files: Dict[str, str], run_id: str):
        """将一次运行产出注册到版本资产索引."""
        for name, path in output_files.items():
            asset_type = self._classify_asset(name)
            if asset_type:
                self.version_manager.update_assets(version, asset_type, path)
        self.index_version_assets(version)

    def get_requirement_hash(self, version: Optional[str] = None) -> str:
        """计算版本需求文档的哈希，用于基线校验."""
        req_path = self.version_manager.requirement_path(version)
        if not req_path.exists():
            return ""
        content = req_path.read_bytes()
        return hashlib.sha256(content).hexdigest()[:16]

    def generate_asset_report(self, version: Optional[str] = None) -> Dict[str, Any]:
        """生成资产统计报告."""
        version = version or self.version_manager.current_version
        assets = self.index_version_assets(version)
        return {
            "version": version,
            "status": self.version_manager.get_version_info(version).status if self.version_manager.get_version_info(version) else "unknown",
            "asset_summary": {
                "test_cases": len(assets.get("test_cases", [])),
                "reports": len(assets.get("reports", [])),
                "screenshots": len(assets.get("screenshots", [])),
                "videos": len(assets.get("videos", [])),
                "har_files": len(assets.get("har_files", [])),
                "defects": len(assets.get("defects", [])),
                "results": len(assets.get("results", [])),
            },
            "requirement_hash": self.get_requirement_hash(version),
            "baseline": self.version_manager.get_baseline(version).to_dict() if self.version_manager.get_baseline(version) else None,
            "assets": assets,
        }

    def _collect_files(self, directory: Path, patterns: List[str], filter_name: str = "") -> List[str]:
        results = []
        if not directory.exists():
            return results
        seen = set()
        for pattern in patterns:
            for path in directory.glob(pattern):
                if path.is_dir():
                    continue
                rel = str(path.relative_to(directory.parent))
                if rel in seen:
                    continue
                seen.add(rel)
                if filter_name == "swagger":
                    lower = path.name.lower()
                    if "swagger" in lower or "openapi" in lower or path.suffix in {".yaml", ".yml"}:
                        results.append(rel)
                elif filter_name in {"frontend_repo", "backend_repo"}:
                    # 代码仓库资产通常放在版本目录下的 repos/ 子目录
                    if f"repos/{filter_name}" in rel or rel.startswith(f"{directory.name}/repos/{filter_name}"):
                        results.append(rel)
                else:
                    results.append(rel)
        return sorted(results)

    def _classify_asset(self, name: str) -> Optional[str]:
        lower = name.lower()
        if "test_cases" in lower:
            return "test_cases"
        if "defect" in lower:
            return "defect"
        if "report" in lower:
            return "report"
        if "screenshot" in lower:
            return "screenshot"
        if "video" in lower:
            return "video"
        if "har" in lower:
            return "har"
        if "result" in lower:
            return "result"
        return None

    def _sync_to_lifecycle(self, version: str, assets: Dict[str, Any]):
        """同步扫描结果到 VersionLifecycleManager 的资产索引."""
        info = self.version_manager.get_version_info(version)
        if info is None:
            return
        output_dir = self.version_manager.output_dir(version)
        for key in ["test_cases", "reports", "screenshots", "videos", "har_files", "defects", "results"]:
            for rel_path in assets.get(key, []):
                self.version_manager.update_assets(version, key.rstrip("_files"), output_dir.parent / rel_path)
