# -*- coding: utf-8 -*-
"""回归测试：VersionManager manifest 原子写与损坏保护.

旧实现 _save_manifest 直接 write_text (非原子)，写过程被中断 (OOM/断电/磁盘满)
会让 manifest.json 被截断为空；下一次 _load_manifest 又静默初始化为空 manifest，
任何后续 save 会用空对象覆盖已损坏文件，造成版本注册表整体数据丢失。
"""
import json
from pathlib import Path

import pytest

from automation.core.version import VersionManager


class TestManifestAtomicWrite:
    def test_save_produces_valid_manifest_without_temp_residue(self, tmp_path):
        mgr = VersionManager(base_dir=tmp_path)
        mgr.create_version("v1.0.0", description="first")
        manifest = tmp_path / VersionManager.MANIFEST_NAME
        assert manifest.exists()
        # 内容必须是合法 JSON 且包含刚创建的版本
        data = json.loads(manifest.read_text(encoding="utf-8"))
        assert any(v["version"] == "v1.0.0" for v in data["versions"])
        # 原子写不应残留临时文件
        residue = list(tmp_path.glob(".manifest-*.tmp"))
        assert residue == [], f"原子写不应残留临时文件: {residue}"

    def test_corrupt_manifest_preserved_on_load(self, tmp_path, capsys):
        """_load_manifest 遇到损坏文件时不应覆盖磁盘原文件（保留以便恢复）."""
        manifest = tmp_path / VersionManager.MANIFEST_NAME
        garbage = b"{ this is not valid json"
        manifest.write_bytes(garbage)

        VersionManager(base_dir=tmp_path)
        # 磁盘上的损坏文件应原样保留，未被覆盖
        assert manifest.read_bytes() == garbage, "损坏的 manifest 应保留原文件以便恢复"
        # 应打印告警
        captured = capsys.readouterr()
        assert "manifest 解析失败" in captured.out

    def test_save_failure_preserves_original_manifest(self, tmp_path, monkeypatch):
        """_save_manifest 在 os.replace 失败时不应损坏原 manifest，且清理临时文件."""
        mgr = VersionManager(base_dir=tmp_path)
        mgr.create_version("v1.0.0")
        manifest = tmp_path / VersionManager.MANIFEST_NAME
        original_content = manifest.read_text(encoding="utf-8")

        import os

        def _failing_replace(src, dst):
            raise RuntimeError("replace failed")

        monkeypatch.setattr(os, "replace", _failing_replace)

        with pytest.raises(RuntimeError):
            mgr.create_version("v2.0.0")

        # 原 manifest 内容应未被破坏
        assert manifest.read_text(encoding="utf-8") == original_content
        # 不应残留临时文件
        assert list(tmp_path.glob(".manifest-*.tmp")) == []
