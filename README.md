# proDemoA 全链路自动化测试平台

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Version-1.0.0-orange.svg" alt="Version">
</p>

## 📋 项目简介

proDemoA 是一个基于AI Agent的全链路自动化测试平台，通过联动多个AI专家Agent，实现从需求文档到测试报告的全流程自动化。测试人员仅需修改配置文件即可开始测试工作。

## 🏗️ 项目架构

```
proDemoA/
├── config/                          # ⭐ 配置文件目录（测试人员仅需修改这里）
│   ├── project_config.py            # 项目配置文件
│   └── requirement.md              # 需求文档模板
│
├── automation/                      # 自动化测试核心引擎
│   ├── agents/                      # 6个AI Agent实现
│   │   ├── requirement_analyzer.py  # 需求分析Agent
│   │   ├── code_parser.py          # 代码解析Agent
│   │   ├── test_generator.py       # 测试用例生成Agent
│   │   ├── test_executor.py        # 测试执行Agent
│   │   ├── defect_detector.py      # 缺陷发现Agent
│   │   └── report_generator.py     # 报告生成Agent
│   │
│   ├── workflow/
│   │   └── engine.py               # 工作流引擎（任务调度）
│   │
│   └── config/
│       └── config.json             # 框架配置
│
├── agents/                          # AI专家库（43个）
│   ├── testing/                    # 测试Agent (9个)
│   ├── engineering/                 # 工程Agent (34个)
│   ├── index.json                  # Agent索引
│   └── README.md                   # Agent说明
│
├── tests/                           # 单元测试（框架自身测试）
│   ├── unit/                       # 单元测试
│   ├── integration/                # 集成测试
│   ├── e2e/                       # 端到端测试
│   ├── performance/                # 性能测试
│   ├── security/                   # 安全测试
│   └── ai_specific/               # AI专项测试
│
├── output/                          # 测试输出目录
│   ├── test_cases.csv              # 测试用例清单
│   ├── defects.csv                 # 缺陷清单
│   ├── test_report.html            # HTML测试报告
│   └── results.json                # 完整结果JSON
│
├── run_automation.py                # ⭐ 主入口脚本
├── conftest.py                     # Pytest配置
├── pytest.ini                      # Pytest设置
└── requirements-test.txt            # 测试依赖
```

## 📁 目录说明

### 1️⃣ config/ - 配置目录（重点）

| 文件 | 说明 | 用途 |
|------|------|------|
| `project_config.py` | 项目配置文件 | 测试人员修改此文件即可运行测试 |
| `requirement.md` | 需求文档模板 | 可直接编辑或替换为自己的需求文档 |

**配置内容**：
- 项目基本信息（名称、代码）
- 需求文档（支持文件读取或直接填写）
- 数据库连接信息
- 代码仓库地址
- 测试类型和覆盖率目标

### 2️⃣ automation/ - 自动化测试核心

| 目录 | 说明 |
|------|------|
| `agents/` | 6个AI Agent实现，负责需求分析、代码解析、测试生成、执行、缺陷发现、报告生成 |
| `workflow/` | 工作流引擎，负责任务调度和流程控制 |

### 3️⃣ agents/ - AI专家库

| 目录 | 数量 | 说明 |
|------|------|------|
| `testing/` | 9个 | 测试专用Agent（API测试、性能测试、无障碍测试等） |
| `engineering/` | 34个 | 工程类Agent（前端开发、后端架构、安全工程等） |

### 4️⃣ tests/ - 单元测试

| 目录 | 说明 |
|------|------|
| `unit/` | 单元测试（AI模型、服务层、工具函数） |
| `integration/` | 集成测试（API、数据库、AI Pipeline） |
| `e2e/` | 端到端测试 |
| `performance/` | 性能测试 |
| `security/` | 安全测试 |
| `ai_specific/` | AI专项测试 |

### 5️⃣ output/ - 测试输出

| 文件 | 说明 |
|------|------|
| `test_cases.csv` | 测试用例清单（可导入测试管理工具） |
| `defects.csv` | 缺陷清单（可导入缺陷管理工具） |
| `test_report.html` | HTML格式测试报告 |
| `results.json` | 完整测试结果JSON |

## 🚀 快速开始

### 步骤1：修改配置文件

打开 `config/project_config.py`，根据实际项目填写配置：

```python
PROJECT_CONFIG = {
    # 1. 项目基本信息
    "project_name": "我的项目",
    "project_code": "PRJ-001",
    "test_type": "功能测试",
    
    # 2. 需求文档
    "requirement_doc_path": "config/requirement.md",
    
    # 3. 数据库配置（可选）
    "database": {
        "enabled": True,
        "type": "mysql",
        "host": "localhost",
        "port": 3306,
        "database": "myapp_db",
        "tables": [...]
    },
    
    # 4. 代码仓库（可选）
    "frontend_repo": {...},
    "backend_repo": {...},
}
```

### 步骤2：运行测试

```bash
# 运行自动化测试
python run_automation.py
```

### 步骤3：查看结果

测试完成后，在 `output/` 目录查看：
- `test_cases.csv` - 测试用例
- `defects.csv` - 缺陷清单
- `test_report.html` - HTML报告

## 🔄 工作流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                         输入（配置）                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ 需求文档      │  │ 数据库结构    │  │ 代码仓库地址          │   │
│  │ config/      │  │ config/       │  │ config/              │   │
│  │ requirement.md│  │ project_config│  │ project_config.py    │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘   │
└─────────┼─────────────────┼────────────────────┼────────────────┘
          │                 │                      │
          ▼                 ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      自动化测试流程                                  │
│                                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐           │
│  │ 需求分析      │──▶│ 代码解析      │──▶│ 测试用例生成 │           │
│  │ Agent        │   │ Agent        │   │ Agent        │           │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘           │
│         │                  │                  │                    │
│         │                  │                  ▼                    │
│         │                  │         ┌──────────────┐             │
│         │                  │────────▶│ 测试执行      │             │
│         │                  │         │ Agent        │             │
│         │                  │         └──────┬───────┘             │
│         │                  │                │                      │
│         │                  │                ▼                      │
│         │                  │        ┌──────────────┐             │
│         │                  └────────▶│ 缺陷发现      │             │
│         │                           │ Agent        │             │
│         │                           └──────┬───────┘             │
│         │                                  │                      │
│         │                                  ▼                      │
│         │                         ┌──────────────┐             │
│         └────────────────────────▶│ 报告生成      │             │
│                                   │ Agent        │             │
│                                   └──────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         输出                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ 测试用例      │  │ 缺陷清单      │  │ 测试报告             │   │
│  │ test_cases  │  │ defects.csv  │  │ test_report.html    │   │
│  │ .csv        │  │              │  │                      │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## 📊 输出说明

### test_cases.csv - 测试用例

| 字段 | 说明 |
|------|------|
| 用例ID | 唯一标识 |
| 用例名称 | 测试用例名称 |
| 用例类型 | API/UI/Database/Integration |
| 所属模块 | 所属业务模块 |
| 优先级 | high/medium/low |
| 前置条件 | 测试前置条件 |
| 测试步骤 | 详细测试步骤 |
| 预期结果 | 预期测试结果 |
| 测试数据 | 使用的测试数据 |

### defects.csv - 缺陷清单

| 字段 | 说明 |
|------|------|
| 缺陷ID | 唯一标识 |
| 缺陷标题 | 缺陷概要 |
| 严重程度 | critical/high/medium/low |
| 优先级 | P1/P2/P3/P4 |
| 缺陷状态 | new/confirmed/in_progress/resolved/closed |
| 缺陷类型 | functional/performance/security |
| 所属模块 | 所属模块 |
| 复现步骤 | 复现步骤 |
| 建议修复 | 修复建议 |

## ⚙️ 配置项详解

### project_config.py 完整配置

```python
PROJECT_CONFIG = {
    # ========== 项目基本信息 ==========
    "project_name": "项目名称",
    "project_code": "项目代码",
    "test_type": "功能测试/性能测试/安全测试/全面测试",
    "test_environment": "dev/test/staging",

    # ========== 需求文档 ==========
    "requirement_doc_path": "config/requirement.md",  # 从文件读取
    # 或
    "requirement_doc": "直接填写需求内容...",

    # ========== 数据库配置 ==========
    "database": {
        "enabled": True,
        "type": "mysql/postgresql/oracle/sqlserver",
        "host": "localhost",
        "port": 3306,
        "database": "db_name",
        "username": "user",
        "password": "password",
        "tables": [...]  # 表结构定义
    },

    # ========== 代码仓库 ==========
    "frontend_repo": {
        "enabled": True/False,
        "type": "github/gitlab/gitee",
        "url": "仓库地址",
        "branch": "分支",
        "language": "react/vue/angular",
        "test_framework": "jest/playwright/cypress"
    },
    
    "backend_repo": {
        "enabled": True/False,
        "type": "github/gitlab/gitee",
        "url": "仓库地址",
        "branch": "分支",
        "language": "python/java/node",
        "test_framework": "pytest/junit/mocha",
        "api_spec": "swagger/openapi/graphql"
    },

    # ========== 测试配置 ==========
    "test_config": {
        "coverage_target": 80,    # 覆盖率目标%
        "test_types": ["unit","integration","api","ui","e2e"],
        "retry_failed": True,
        "retry_times": 2
    }
}
```

## 🔧 运行单元测试

框架自身包含72个单元测试，可验证框架功能：

```bash
# 运行所有单元测试
pytest

# 运行特定类型
pytest tests/unit/
pytest tests/ai_specific/

# 生成HTML报告
pytest --html=reports/report.html
```

## 🤖 AI专家库

本项目整合了来自 [agency-agents-zh](https://github.com/jnMetaCode/agency-agents-zh) 的43个AI专家Agent：

### 测试Agent (9个)
- API测试工程师
- 性能基准测试工程师
- 测试结果分析师
- 无障碍审计师
- 证据收集器
- 工具评估师
- 工作流优化师
- 现实检查员
- 嵌入式QA工程师

### 工程Agent (34个)
- 前端开发者、后端架构师、AI工程师
- 代码审查员、安全工程师、DevOps自动化
- SRE、数据工程师、数据库优化师
- 等等...

## 📝 注意事项

1. **配置文件是核心** - 测试人员只需修改 `config/project_config.py`
2. **需求文档支持** - 支持Markdown格式，也支持直接填写
3. **数据库可选** - 可以仅配置需求文档进行测试
4. **代码仓库可选** - 可以仅配置需求文档和数据库信息
5. **输出格式** - CSV格式便于导入测试管理工具

## 📄 许可证

MIT License

---

<p align="center">🚀 使用proDemoA，让测试工作更高效！</p>
