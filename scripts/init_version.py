#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""版本初始化脚本.

建立新版本目录并自动生成所有配置模板：
- versions/{version}/config.json      版本级环境、Swagger、代码仓库配置
- versions/{version}/requirement.md   需求文档占位（需手动替换）
- versions/{version}/README.md        参数填写说明

用法:
    # 交互式
    python scripts/init_version.py

    # 命令行
    python scripts/init_version.py --version v0.8.0 --environment test \
        --swagger-file "versions/v0.8.0/swagger.yaml" \
        --backend-url "https://github.com/example/backend" \
        --frontend-url "https://github.com/example/frontend" \
        --api-base-url "http://test-api.company.com" \
        --ui-base-url "http://test-ui.company.com"
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# 支持从仓库根目录和 scripts 目录运行
script_dir = Path(__file__).parent.resolve()
repo_root = script_dir.parent
sys.path.insert(0, str(repo_root))

from automation.core.config import load_config, merge_environment_config, merge_with_framework_config
from automation.core.management import VersionLifecycleManager


def prompt(question: str, default: str = "") -> str:
    """交互式询问，非交互环境直接返回默认值."""
    try:
        if sys.stdin.isatty():
            value = input(f"{question} [{default}]: ").strip()
            return value if value else default
    except EOFError:
        pass
    return default


def build_version_config(
    version: str,
    environment: str = "dev",
    swagger_url: str = "",
    swagger_file: str = "",
    frontend_url: str = "",
    frontend_local_path: str = "",
    backend_url: str = "",
    backend_local_path: str = "",
    api_base_url: str = "",
    ui_base_url: str = "",
    db_host: str = "",
    db_database: str = "",
    description: str = "",
) -> dict:
    """构建版本专属配置."""
    return {
        "version": version,
        "description": description or f"版本 {version} 测试配置",
        "environment": environment,
        "sources": {
            "swagger": {
                "enabled": bool(swagger_url or swagger_file),
                "url": swagger_url,
                "file_path": swagger_file,
                "format": "openapi",
            },
            "frontend_repo": {
                "enabled": bool(frontend_url or frontend_local_path),
                "type": "github" if frontend_url else "local",
                "url": frontend_url,
                "branch": "main",
                "language": "react",
                "test_framework": "jest",
                "api_spec": "",
                "local_path": frontend_local_path,
            },
            "backend_repo": {
                "enabled": bool(backend_url or backend_local_path),
                "type": "github" if backend_url else "local",
                "url": backend_url,
                "branch": "main",
                "language": "python",
                "test_framework": "pytest",
                "api_spec": "",
                "local_path": backend_local_path,
            },
        },
        "environment_overrides": {
            "database": {
                "enabled": bool(db_host),
                "type": "mysql",
                "host": db_host,
                "port": 3306,
                "database": db_database,
                "username": "test_user",
                "password": "${DATABASE_PASSWORD}",
                "tables": [],
            },
            "network": {
                "type": "public",
                "browser_mode": "headless",
                "browser_type": "chromium",
                "proxy": None,
                "bypass_hosts": [],
                "record_video": False,
                "record_har": False,
                "capture_console": True,
                "capture_network": False,
                "slow_mo": 0,
                "local_browser_path": None,
            },
            "extra": {
                "api_base_url": api_base_url,
                "ui_base_url": ui_base_url,
            },
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


def write_readme(version_dir: Path):
    """写入版本填写说明."""
    readme = version_dir / "README.md"
    content = f"""# 版本 {version_dir.name} 配置说明

本目录由 `scripts/init_version.py` 自动生成。

## 需要您手动补充的内容

1. **需求文档**
   - 替换 `requirement.md` 为您的 Word 需求转译后的 Markdown 文件
   - 也可将多个 Word 文档转义后放在 `requirements/` 目录并合并

2. **版本配置 `config.json`**
   - 在 `sources.swagger` 中填写 Swagger / OpenAPI 文件路径或 URL
   - 在 `sources.frontend_repo` / `sources.backend_repo` 中填写代码仓库地址或本地路径
   - 在 `environment_overrides` 中覆盖数据库、网络、API/UI 地址

3. **接口文档**
   - 推荐将 Swagger 文件（`.json` / `.yaml`）放入本版本目录
   - 修改 `config.json → sources.swagger.file_path` 指向该文件

## 执行测试

```bash
python run_automation.py --environment {version_dir.name} --version {version_dir.name} --manage run-version
```

或完整运行：

```bash
python run_automation.py --environment {version_dir.name} --version {version_dir.name}
```
"""
    readme.write_text(content, encoding="utf-8")


def init_version(
    version: str,
    base_dir: str = "versions",
    environment: str = "dev",
    config_path: str = "config/project_config.py",
    **kwargs,
) -> Path:
    """初始化一个版本目录."""
    project_config = merge_with_framework_config(load_config(config_path))
    project_config = merge_environment_config(project_config, environment)

    vm = VersionLifecycleManager(base_dir, current_version=version)

    if version in vm.list_versions():
        print(f"⚠️  版本 {version} 已存在，仅更新配置模板")
    else:
        print(f"🆕 创建版本: {version}")
        vm.create_version(
            version,
            description=kwargs.get("description", ""),
            environment_profile=environment,
        )

    vdir = vm.version_dir(version)

    # 写入版本配置
    version_config = build_version_config(version, environment, **kwargs)
    vm.save_version_config(version, version_config)

    # 写入需求占位
    req_path = vm.requirement_path(version)
    if not req_path.exists() or req_path.stat().st_size == 0:
        req_path.write_text(
            f"# {version} 需求文档\n\n请将此文件替换为 Word 需求转译后的 Markdown 内容。\n",
            encoding="utf-8",
        )

    # 写入说明文档
    write_readme(vdir)

    print(f"✅ 版本 {version} 初始化完成")
    print(f"📁 版本目录: {vdir}")
    print("📄 请修改以下文件后执行测试:")
    print(f"   - {vdir / 'config.json'}")
    print(f"   - {vdir / 'requirement.md'}")
    return vdir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="智测 版本初始化脚本")
    parser.add_argument("--version", required=True, help="版本号，例如 v0.8.0")
    parser.add_argument("--environment", default="dev", choices=["dev", "test", "staging", "prod"], help="默认环境")
    parser.add_argument("--base-dir", default="versions", help="版本库根目录")
    parser.add_argument("--config", default="config/project_config.py", help="项目配置文件路径")
    parser.add_argument("--swagger-url", default="", help="Swagger URL")
    parser.add_argument("--swagger-file", default="", help="Swagger 本地文件路径")
    parser.add_argument("--frontend-url", default="", help="前端仓库 Git 地址")
    parser.add_argument("--frontend-local-path", default="", help="前端仓库本地路径")
    parser.add_argument("--backend-url", default="", help="后端仓库 Git 地址")
    parser.add_argument("--backend-local-path", default="", help="后端仓库本地路径")
    parser.add_argument("--api-base-url", default="", help="API 基础地址")
    parser.add_argument("--ui-base-url", default="", help="UI 基础地址")
    parser.add_argument("--db-host", default="", help="数据库主机")
    parser.add_argument("--db-database", default="", help="数据库名")
    parser.add_argument("--description", default="", help="版本描述")
    parser.add_argument("--interactive", action="store_true", help="交互式询问")
    return parser.parse_args()


def interactive_collect(args: argparse.Namespace) -> argparse.Namespace:
    """交互式收集参数."""
    args.version = prompt("版本号", args.version)
    args.environment = prompt("环境 (dev/test/staging/prod)", args.environment)
    args.swagger_file = prompt("Swagger 文件路径（可空）", args.swagger_file)
    args.swagger_url = prompt("Swagger URL（可空）", args.swagger_url)
    args.backend_url = prompt("后端仓库 Git 地址（可空）", args.backend_url)
    args.backend_local_path = prompt("后端仓库本地路径（可空）", args.backend_local_path)
    args.frontend_url = prompt("前端仓库 Git 地址（可空）", args.frontend_url)
    args.frontend_local_path = prompt("前端仓库本地路径（可空）", args.frontend_local_path)
    args.api_base_url = prompt("API 基础地址（可空）", args.api_base_url)
    args.ui_base_url = prompt("UI 基础地址（可空）", args.ui_base_url)
    args.db_host = prompt("数据库主机（可空）", args.db_host)
    args.db_database = prompt("数据库名（可空）", args.db_database)
    args.description = prompt("版本描述（可空）", args.description)
    return args


def main():
    args = parse_args()
    if args.interactive:
        args = interactive_collect(args)

    init_version(
        version=args.version,
        base_dir=args.base_dir,
        environment=args.environment,
        config_path=args.config,
        swagger_url=args.swagger_url,
        swagger_file=args.swagger_file,
        frontend_url=args.frontend_url,
        frontend_local_path=args.frontend_local_path,
        backend_url=args.backend_url,
        backend_local_path=args.backend_local_path,
        api_base_url=args.api_base_url,
        ui_base_url=args.ui_base_url,
        db_host=args.db_host,
        db_database=args.db_database,
        description=args.description,
    )


if __name__ == "__main__":
    main()
