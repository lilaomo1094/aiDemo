# -*- coding: utf-8 -*-
# ============================================================
# 智测 全链路自动化测试平台 - 项目配置文件
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
        # 密码支持 ${DATABASE_PASSWORD} 占位符，或直接写死（不推荐）
        "password": "${DATABASE_PASSWORD}",
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

    # ========== 测试账号（用于 UI/API 用例生成） ==========
    # 密码支持 ${TEST_PASSWORD} 占位符或环境变量自动回退
    "test_accounts": [
        {
            "name": "default",
            "username": "testuser",
            "password": "${TEST_PASSWORD}",
            "phone": "13411985758",
            "email": "test@example.com",
            "role": "user",
        },
        {
            "name": "admin",
            "username": "admin",
            "password": "${TEST_PASSWORD}",
            "phone": "13411985759",
            "email": "admin@example.com",
            "role": "admin",
        },
    ],

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
        # 主模型失败时自动切换的兜底模型，为空则关闭降级
        "fallback_model": "gpt-4o-mini",
        # 建议通过环境变量 OPENAI_API_KEY 注入，避免写死在配置文件
        "api_key": "",
        "base_url": "https://api.openai.com/v1",
        "temperature": 0.2,
        "max_tokens": 4000,
        "timeout": 120,
        # LLM 调用重试策略
        "retry_times": 3,
        "retry_backoff": 1.0,
    },

    # ========== 语音识别配置（可选） ==========
    # 启用后支持通过语音下达测试任务，IM 机器人与 run_voice_task.py 会调用 ASR
    "voice": {
        "enabled": False,
        "provider": "openai_whisper",  # 目前仅支持 openai_whisper
        # 支持 ${VOICE_API_KEY}，为空时自动回退到 OPENAI_API_KEY
        "api_key": "${VOICE_API_KEY}",
        "base_url": "https://api.openai.com/v1",
        "model": "whisper-1",
        "language": "zh",
        "timeout": 60,
    },

    # ========== Function Calling 智能编排（可选） ==========
    # 启用后 IM 机器人收到自然语言指令时，会通过大模型 Function Calling 自动编排 Agent
    "function_calling": {
        "enabled": False,
        "max_iterations": 10,
    },

    # ========== 版本迭代管理（可选） ==========
    # 启用后，每个版本拥有独立的需求文档与输出目录
    # 运行: python run_automation.py --version v0.7.30
    # 创建: python run_automation.py --create-version v0.7.30 --requirement config/requirement.md
    # 对比: python run_automation.py --compare v0.7.30 v0.8.0
    "version": {
        "enabled": True,
        "base_dir": "versions",
        "current_version": "v0.7.30",
        "auto_create": True,  # 指定 --version 且版本不存在时自动创建
    },

    # ========== IM 机器人配置（可选） ==========
    "im": {
        "provider": "lark",
        "enabled": False,
        "app_id": "",
        # 支持 ${IM_APP_SECRET}
        "app_secret": "${IM_APP_SECRET}",
        "default_config_path": "config/project_config.py",
        "project_aliases": {},
        "admin_users": [],
        "voice": {
            "enabled": False,
            "provider": "openai_whisper",
            # 支持 ${VOICE_API_KEY}，为空时自动回退到 OPENAI_API_KEY
            "api_key": "${VOICE_API_KEY}",
            "model": "whisper-1",
            "language": "zh",
        },
        "function_calling": False,
    },

    # ========== 网络环境配置 ==========
    # type: public(公网) | private(公司内网) | vpn(VPN接入内网)
    # browser_mode: headed(有界面，便于内网本地监控) | headless(无头，适用于CI/公网)
    # browser_type: chromium(Playwright下载的Chromium) | edge(本地Edge) | chrome(本地Chrome)
    "network": {
        "type": "public",
        "browser_mode": "headless",
        "browser_type": "edge",
        # 代理配置示例："http://proxy.company.com:8080"
        "proxy": None,
        "bypass_hosts": [],
        # 内网场景建议开启视频录制与 HAR，便于回溯
        "record_video": False,
        "record_har": False,
        "capture_console": True,
        "capture_network": False,
        # 内网监控时放慢操作节奏（毫秒）
        "slow_mo": 0,
        # 指定本地浏览器路径（如 Chrome/Edge 可执行文件），优先级高于 browser_type
        "local_browser_path": None,
    },

    # ========== 扩展配置 ==========
    "extra": {
        # API 基础地址，用于真实 API 测试执行
        "api_base_url": "http://localhost:8000",
        # UI 基础地址（示例）
        "ui_base_url": "http://localhost:8080",
    },
}


