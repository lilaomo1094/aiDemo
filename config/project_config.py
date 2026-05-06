# -*- coding: utf-8 -*-
# ============================================================
# proDemoA 全链路自动化测试平台 - 项目配置文件
# ============================================================
# 使用说明：
# 1. 测试人员只需修改本文件中的项目信息
# 2. 运行命令: python run_automation.py
# 3. 无需修改任何代码
# ============================================================

PROJECT_CONFIG = {
    # ========== 项目基本信息 ==========
    "project_name": "用户管理系统",           # 项目名称
    "project_code": "UMS-001",              # 项目代码
    "test_type": "全面测试",                 # 测试类型: 功能测试/性能测试/安全测试/全面测试
    "test_environment": "test",              # 测试环境: dev/test/staging

    # ========== 需求文档配置 ==========
    # 方式一：从文件读取（推荐）
    "requirement_doc_path": "config/requirement.md",
    
    # 方式二：直接填写需求内容（覆盖方式一）
    # "requirement_doc": "需求文档内容...",
    
    # 示例需求内容（如果上面两项都为空，将使用此内容）
    "requirement_doc": """
# 用户管理系统需求文档

## 功能需求

### 1. 用户登录 (REQ-001)
用户可以通过用户名密码登录系统
- 用户名密码正确返回token
- 用户名密码错误返回401

### 2. 用户注册 (REQ-002)
新用户可以注册账号
- 邮箱格式验证
- 密码强度验证
- 用户名唯一性检查

### 3. 用户管理 (REQ-003)
管理员可以管理用户
- 创建用户
- 查询用户列表
- 查询用户详情
- 更新用户信息
- 删除用户

## 非功能需求

### 性能要求
- 登录响应时间 < 200ms
- 查询响应时间 < 500ms

### 安全要求
- 密码加密存储
- 接口认证验证
- SQL注入防护

## 验收标准
1. 所有功能正常工作
2. 性能满足要求
3. 安全测试通过
""",

    # ========== 数据库配置 ==========
    "database": {
        "enabled": True,                    # 是否启用数据库解析
        "type": "mysql",                   # 数据库类型: mysql/postgresql/oracle/sqlserver
        "host": "localhost",                # 数据库地址
        "port": 3306,                      # 端口
        "database": "ums_db",               # 数据库名
        "username": "test_user",            # 用户名
        "password": "test_password",        # 密码
        
        # 表结构定义（如果无法连接数据库，可手动填写）
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
                    {"name": "updated_at", "type": "DATETIME"}
                ]
            },
            {
                "name": "sessions",
                "description": "会话表",
                "columns": [
                    {"name": "id", "type": "INT", "primary_key": True},
                    {"name": "user_id", "type": "INT", "foreign_key": "users.id"},
                    {"name": "token", "type": "VARCHAR(255)", "nullable": False},
                    {"name": "expires_at", "type": "DATETIME"},
                    {"name": "created_at", "type": "DATETIME"}
                ]
            }
        ]
    },

    # ========== 前端代码仓库配置 ==========
    "frontend_repo": {
        "enabled": False,                   # 是否启用前端仓库解析
        "type": "github",                  # 仓库类型: github/gitlab/gitee
        "url": "https://github.com/example/frontend",
        "branch": "develop",               # 分支
        "language": "react",               # 开发语言: react/vue/angular
        "test_framework": "jest"           # 测试框架: jest/playwright/cypress
    },

    # ========== 后端代码仓库配置 ==========
    "backend_repo": {
        "enabled": False,                  # 是否启用后端仓库解析
        "type": "github",                  # 仓库类型: github/gitlab/gitee
        "url": "https://github.com/example/backend",
        "branch": "develop",               # 分支
        "language": "python",              # 开发语言: python/java/node
        "test_framework": "pytest",        # 测试框架: pytest/junit/mocha
        "api_spec": "swagger"              # API规范: swagger/openapi/graphql
    },

    # ========== 测试配置 ==========
    "test_config": {
        "coverage_target": 80,             # 覆盖率目标 (%)
        "test_types": [                    # 需要生成的测试类型
            "unit",
            "integration", 
            "api",
            "ui",
            "e2e"
        ],
        "run_after_deploy": True,          # 部署后是否自动运行
        "notify_on_complete": True,        # 完成是否通知
        "retry_failed": True,              # 失败是否重试
        "retry_times": 2                  # 重试次数
    },

    # ========== 输出配置 ==========
    "output": {
        "test_cases_file": "output/test_cases.csv",
        "defects_file": "output/defects.csv",
        "report_file": "output/test_report.html",
        "results_file": "output/results.json"
    }
}


# ============================================================
# 快速配置示例 - 复制下方配置到上方覆盖即可使用
# ============================================================

# 示例1：最小配置（仅测试需求文档）
MINIMAL_CONFIG = {
    "project_name": "我的项目",
    "project_code": "PRJ-001",
    "requirement_doc": "# 需求文档\n## 功能1\n需求描述...",
    "database": {"enabled": False},
    "frontend_repo": {"enabled": False},
    "backend_repo": {"enabled": False}
}

# 示例2：完整配置
FULL_CONFIG = {
    "project_name": "用户管理系统",
    "project_code": "UMS-001",
    "test_type": "全面测试",
    "requirement_doc_path": "config/requirement.md",
    "database": {
        "enabled": True,
        "type": "mysql",
        "host": "192.168.1.100",
        "port": 3306,
        "database": "ums_prod",
        "username": "ums_user",
        "password": "ums_password",
        "tables": []
    },
    "frontend_repo": {
        "enabled": True,
        "type": "gitlab",
        "url": "https://gitlab.example.com/team/frontend",
        "branch": "release/v2.0",
        "language": "vue",
        "test_framework": "cypress"
    },
    "backend_repo": {
        "enabled": True,
        "type": "gitlab",
        "url": "https://gitlab.example.com/team/backend",
        "branch": "release/v2.0",
        "language": "java",
        "test_framework": "junit",
        "api_spec": "openapi"
    }
}
