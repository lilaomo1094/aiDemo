# -*- coding: utf-8 -*-
# ============================================================
# 智测 全链路自动化测试平台 - 项目配置文件
# ============================================================
# 使用说明：
# 1. 本文件只保留项目专属信息（项目名称、需求、代码仓库、通用测试策略等）
# 2. 数据库、测试账号、网络、API/UI 地址等环境相关配置已迁移到
#    config/environments/{dev,test,staging,prod}.json
# 3. 运行命令:
#    - 默认 dev 环境:  python run_automation.py
#    - 指定 test 环境: python run_automation.py --environment test
#    - 指定版本:       python run_automation.py --environment test --version v0.7.30
# 4. 如需覆盖公共环境配置，可在本文件对应字段显式声明，项目配置优先级更高
# ============================================================

PROJECT_CONFIG = {
    # ========== 项目基本信息 ==========
    "project": {
        "project_name": "商户端登录功能",
        "project_code": "LOGIN-001",
        "test_type": "UI 功能测试",
        # 项目所归属的测试环境标签，仅用于报告展示
        "test_environment": "dev",
    },

    # ========== 需求文档配置 ==========
    # 方式一：从文件读取（推荐）
    "requirement": {
        "requirement_doc_path": "config/requirement.md",
        # "requirement_doc": "直接填写需求内容...",
    },

    # ========== 前端代码仓库配置（可选） ==========
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

    # ========== 后端代码仓库配置（可选） ==========
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

    # ========== 测试策略配置（可选） ==========
    # 环境相关连接信息（数据库、账号、网络、URL）请优先维护在
    # config/environments/*.json，此处保留通用测试策略即可。
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
    "llm": {
        "provider": "openai",
        "model": "gpt-4o",
        "fallback_model": "gpt-4o-mini",
        "api_key": "",
        "base_url": "https://api.openai.com/v1",
        "temperature": 0.2,
        "max_tokens": 4000,
        "timeout": 120,
        "retry_times": 3,
        "retry_backoff": 1.0,
    },

    # ========== 语音识别配置（可选） ==========
    "voice": {
        "enabled": False,
        "provider": "openai_whisper",
        "api_key": "${VOICE_API_KEY}",
        "base_url": "https://api.openai.com/v1",
        "model": "whisper-1",
        "language": "zh",
        "timeout": 60,
    },

    # ========== Function Calling 智能编排（可选） ==========
    "function_calling": {
        "enabled": False,
        "max_iterations": 10,
    },

    # ========== 版本迭代管理（可选） ==========
    "version": {
        "enabled": True,
        "base_dir": "versions",
        "current_version": "v0.7.30",
        "auto_create": True,
    },

    # ========== IM 机器人配置（可选） ==========
    "im": {
        "provider": "lark",
        "enabled": False,
        "app_id": "",
        "app_secret": "${IM_APP_SECRET}",
        "default_config_path": "config/project_config.py",
        "project_aliases": {},
        "admin_users": [],
        "voice": {
            "enabled": False,
            "provider": "openai_whisper",
            "api_key": "${VOICE_API_KEY}",
            "model": "whisper-1",
            "language": "zh",
        },
        "function_calling": False,
    },

    # ========== 环境配置引用 ==========
    # 指定使用 config/environments/ 下的哪个公共环境配置
    # 命令行 --environment 会覆盖此处
    "environment": "dev",
    "environments_dir": "config/environments",

    # ========== 项目级环境覆盖（可选） ==========
    # 若以下字段为空，则自动从 environment 对应的公共环境配置读取；
    # 若在此显式声明，则项目级配置优先级更高。
    # "database": { ... },
    # "test_accounts": [ ... ],
    # "network": { ... },
    # "extra": { "api_base_url": "", "ui_base_url": "" },
}
