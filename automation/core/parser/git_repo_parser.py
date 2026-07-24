# -*- coding: utf-8 -*-
"""Git 仓库解析器：克隆/拉取仓库并扫描 API 规范、源码结构."""

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List

try:
    from git import Repo
except ImportError:
    Repo = None

from .base import CodeParseResult, RepositoryParser
from .openapi_parser import OpenAPIParser


class GitRepositoryParser(RepositoryParser):
    def __init__(self, timeout: int = 120, work_dir: str = None):
        self.timeout = timeout
        self.work_dir = work_dir or tempfile.gettempdir()

    def parse(self, repo_config) -> CodeParseResult:
        local_path = self._ensure_local(repo_config)
        if not local_path or not Path(local_path).exists():
            return CodeParseResult(errors=["无法获取仓库本地路径"])

        result = CodeParseResult(raw_files=self._scan_files(local_path))

        # 优先解析 OpenAPI 规范
        spec_path = self._find_openapi_spec(local_path, repo_config)
        if spec_path:
            openapi = OpenAPIParser(timeout=self.timeout)
            openapi_result = openapi.parse(type("C", (), {"api_spec": str(spec_path)}))
            result.api_endpoints = openapi_result.api_endpoints
            result.data_models = openapi_result.data_models
            result.errors.extend(openapi_result.errors)

        # 简单扫描前端组件（React/Vue）
        if repo_config.language.lower() in {"react", "vue", "angular"}:
            result.frontend_components = self._scan_frontend_components(local_path, repo_config.language.lower())

        return result

    def _ensure_local(self, repo_config) -> str:
        if repo_config.local_path and Path(repo_config.local_path).exists():
            return repo_config.local_path

        if not repo_config.url:
            return ""

        if Repo is None:
            return ""

        repo_name = repo_config.url.rstrip("/").split("/")[-1].replace(".git", "")
        target = Path(self.work_dir) / f"aiAgent_repo_{repo_name}"

        if target.exists():
            try:
                repo = Repo(str(target))
                repo.remotes.origin.pull(repo_config.branch, timeout=self.timeout)
                return str(target)
            except Exception:
                shutil.rmtree(target, ignore_errors=True)

        Repo.clone_from(
            repo_config.url,
            str(target),
            branch=repo_config.branch,
            depth=1,
            timeout=self.timeout,
        )
        return str(target)

    def _find_openapi_spec(self, local_path: str, repo_config) -> Path:
        candidates = []
        if repo_config.api_spec:
            candidates.append(Path(local_path) / repo_config.api_spec)
        candidates.extend([
            Path(local_path) / "openapi.yaml",
            Path(local_path) / "openapi.yml",
            Path(local_path) / "openapi.json",
            Path(local_path) / "swagger.yaml",
            Path(local_path) / "swagger.yml",
            Path(local_path) / "swagger.json",
        ])
        for c in candidates:
            if c.exists():
                return c
        # 递归查找第一层
        for root, dirs, files in os.walk(local_path):
            if ".git" in root:
                continue
            for f in files:
                if f in {"openapi.yaml", "openapi.yml", "openapi.json", "swagger.yaml", "swagger.yml", "swagger.json"}:
                    return Path(root) / f
        return None

    def _scan_files(self, local_path: str) -> List[str]:
        files = []
        for root, _, filenames in os.walk(local_path):
            if ".git" in root:
                continue
            for f in filenames:
                files.append(str(Path(root) / f))
        return files[:500]

    def _scan_frontend_components(self, local_path: str, language: str) -> List[Dict]:
        components = []
        if language == "react":
            ext = ".jsx"
            alt = ".tsx"
        elif language == "vue":
            ext = ".vue"
            alt = None
        else:
            ext = ".html"
            alt = None

        for root, _, filenames in os.walk(local_path):
            if "node_modules" in root or ".git" in root:
                continue
            for f in filenames:
                if f.endswith(ext) or (alt and f.endswith(alt)):
                    rel = Path(root).relative_to(local_path)
                    components.append({
                        "name": f,
                        "path": str(rel / f),
                        "type": "component",
                    })
                    if len(components) >= 50:
                        return components
        return components
