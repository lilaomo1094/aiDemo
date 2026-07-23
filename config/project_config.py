# -*- coding: utf-8 -*-
# ============================================================
# aiAgent 全链路自动化测试平台 - 项目配置文件
# ============================================================
# 使用说明：
# 1. 测试人员只需修改本文件中的项目信息
# 2. 运行命令: python run_automation.py
# 3. 无需修改任何代码
# ============================================================

PROJECT_CONFIG = {
    # ========== 项目基本信息 ==========
    "project": {
        "project_name": "商户端登录功能",
        "project_code": "LOGIN-001",
        "test_type": "UI 功能测试",
        "test_environment": "dev",
    },

    # ========== 需求文档配置 ==========
    # 方式一：从文件读取（推荐）
    "requirement": {
        "requirement_doc_path": "config/requirement.md",
        # "requirement_doc": "直接填写需求内容...",
    },

    # ========== 数据库配置 ==========
    "database": {
        "enabled": False,
        "type": "mysql",
        "host": "localhost",
        "port": 3306,
        "database": "ums_db",
        "username": "test_user",
        "password": "test_password",
        "tables": [
            {
                "name": "users",
                "description": "用户表",
                "columns": [
                    {"name": "id", "type": "INT", "primary_key": True},
                    {"name": "username", "type": "VARCHAR(50)", "nullable": False},
                    {"name": "email", "type": "VARCHAR(100)", "nullable": False},
                    {"name": "password_hash", "type": "VARCHAR(255)", "nullable": False},
                    {"name": "role", "type": "VARCHAR(20)", "default": "user"},
                    {"name": "created_at", "type": "DATETIME"},
                    {"name": "updated_at", "type": "DATETIME"},
                ],
            },
            {
                "name": "sessions",
                "description": "会话表",
                "columns": [
                    {"name": "id", "type": "INT", "primary_key": True},
                    {"name": "user_id", "type": "INT", "foreign_key": "users.id"},
                    {"name": "token", "type": "VARCHAR(255)", "nullable": False},
                    {"name": "expires_at", "type": "DATETIME"},
                    {"name": "created_at", "type": "DATETIME"},
                ],
            },
        ],
    },

    # ========== 前端代码仓库配置 ==========
    "frontend_repo": {
        "enabled": False,
        "type": "github",
        "url": "https://github.com/example/frontend",
        "branch": "develop",
        "language": "react",
        "test_framework": "jest",
        "api_spec": "",
        "local_path": "",
    },

    # ========== 后端代码仓库配置 ==========
    "backend_repo": {
        "enabled": False,
        "type": "github",
        "url": "https://github.com/example/backend",
        "branch": "develop",
        "language": "python",
        "test_framework": "pytest",
        "api_spec": "",
        "local_path": "",
    },

    # ========== 测试配置 ==========
    "test": {
        "coverage_target": 80,
        "test_types": ["unit", "integration", "api", "ui", "e2e"],
        "retry_failed": True,
        "retry_times": 2,
        "timeout": 30,
        "parallel": False,
        "max_workers": 4,
    },

    # ========== 输出配置 ==========
    "output": {
        "test_cases_file": "output/test_cases.csv",
        "defects_file": "output/defects.csv",
        "report_file": "output/test_report.html",
        "results_file": "output/results.json",
        "test_cases_excel": "output/test_cases.xlsx",
        "defects_excel": "output/defects.xlsx",
    },

    # ========== LLM 配置（可选） ==========
    # 配置后将启用 AI 驱动的需求分析、用例生成、缺陷分析
    "llm": {
        "provider": "openai",
        "model": "gpt-4o",
        "api_key": "",
        "base_url": "https://api.openai.com/v1",
        "temperature": 0.2,
        "max_tokens": 4000,
        "timeout": 120,
    },

    # ========== 扩展配置 ==========
    "extra": {
        # API 基础地址，用于真实 API 测试执行
        "api_base_url": "http://localhost:8000",
        # UI 基础地址
        "ui_base_url": "https://merchant-dev.nexuscube.cn",
    },
}


