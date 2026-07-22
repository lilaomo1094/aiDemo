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
├── config/                          # ⭐ 项目配置（测试人员仅需修改这里）
│   ├── project_config.py            # 项目配置文件
│   └── requirement.md              # 需求文档模板
│
├── automation/                      # 自动化测试核心引擎
│   ├── agents/                      # 6个AI Agent实现
│   │   ├── base.py                  # Agent 抽象基类
│   │   ├── requirement_analyzer.py  # 需求分析Agent
│   │   ├── code_parser.py          # 代码解析Agent
│   │   ├── test_generator.py       # 测试用例生成Agent
│   │   ├── test_executor.py        # 测试执行Agent
│   │   ├── defect_detector.py      # 缺陷发现Agent
│   │   └── report_generator.py     # 报告生成Agent
│   │
│   ├── core/                        # 框架核心能力（可插拔）
│   │   ├── config.py               # 统一配置管理（Pydantic 校验）
│   │   ├── llm/                    # LLM Provider 抽象层
│   │   │   ├── base.py
│   │   │   ├── openai_provider.py
│   │   │   ├── anthropic_provider.py
│   │   │   ├── ollama_provider.py
│   │   │   └── factory.py
│   │   ├── parser/                 # 代码/API/数据库解析器
│   │   │   ├── base.py
│   │   │   ├── openapi_parser.py   # OpenAPI/Swagger 解析
│   │   │   ├── git_repo_parser.py  # Git 仓库克隆与扫描
│   │   │   └── db_schema_collector.py  # 真实数据库 Schema 采集
│   │   ├── executor/               # 可插拔测试执行器
│   │   │   ├── base.py
│   │   │   ├── api_executor.py     # 真实 HTTP 请求
│   │   │   ├── db_executor.py      # 真实 SQL 执行
│   │   │   ├── ui_executor.py      # Playwright UI 测试
│   │   │   ├── integration_executor.py  # 多步骤编排
│   │   │   └── factory.py
│   │   └── output/                 # 统一输出格式化
│   │       └── formatter.py        # CSV/JSON/HTML/Excel
│   │
│   ├── workflow/
│   │   └── engine.py               # 工作流引擎（DAG 任务调度）
│   │
│   └── config/
│       └── config.json             # 框架默认配置
│
├── agents/                          # AI专家库（43个）
│   ├── testing/                    # 测试Agent (9个)
│   ├── engineering/                 # 工程Agent (34个)
│   ├── index.json                  # Agent索引
│   └── README.md                   # Agent说明
│
├── tests/                           # 单元测试（框架自身测试）
│   ├── unit/                       # 单元测试
│   │   └── core/                  # 核心模块测试
│   ├── integration/                # 集成测试
│   ├── e2e/                       # 端到端测试
│   ├── performance/                # 性能测试
│   ├── security/                   # 安全测试
│   └── ai_specific/               # AI专项测试
│
├── output/                          # 测试输出目录
│   ├── test_cases.csv              # 测试用例清单
│   ├── test_cases.xlsx             # 测试用例 Excel
│   ├── defects.csv                 # 缺陷清单
│   ├── defects.xlsx                # 缺陷 Excel
│   ├── test_report.html            # HTML测试报告
│   └── results.json                # 完整结果JSON
│
├── run_automation.py                # ⭐ 主入口脚本
├── conftest.py                     # Pytest配置
├── pytest.ini                      # Pytest设置
├── requirements.txt                 # 运行依赖
└── requirements-test.txt            # 测试依赖
```

## 📁 目录说明

### 1️⃣ config/ - 配置目录（重点）

| 文件 | 说明 | 用途 |
|------|------|------|
| `project_config.py` | 项目配置文件 | 测试人员修改此文件即可运行测试 |
| `requirement.md` | 需求文档模板 | 可直接编辑或替换为自己的需求文档 |

**配置内容**：
- 项目基本信息（名称、代码、测试类型、环境）
- 需求文档（支持文件读取或直接填写）
- 数据库连接信息（真实连接自动采集 Schema）
- 前后端代码仓库地址（Git 克隆/OpenAPI 解析）
- LLM 模型配置（OpenAI/Anthropic/Ollama/自定义）
- 测试类型、重试、超时、覆盖率目标
- 输出文件路径

### 2️⃣ automation/ - 自动化测试核心

| 目录 | 说明 |
|------|------|
| `agents/` | 6个AI Agent实现，负责需求分析、代码解析、测试生成、执行、缺陷发现、报告生成 |
| `core/` | 框架核心能力：统一配置、LLM Provider、代码/API/DB 解析器、可插拔执行器、输出格式化 |
| `workflow/` | 工作流引擎，负责 DAG 任务调度和流程控制 |

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
| `test_cases.xlsx` | 测试用例 Excel |
| `defects.csv` | 缺陷清单（可导入缺陷管理工具） |
| `defects.xlsx` | 缺陷 Excel |
| `test_report.html` | HTML格式测试报告 |
| `results.json` | 完整测试结果JSON |

## 🚀 快速开始

### 步骤1：修改配置文件

打开 `config/project_config.py`，根据实际项目填写配置：

```python
PROJECT_CONFIG = {
    # 1. 项目基本信息
    "project": {
        "project_name": "我的项目",
        "project_code": "PRJ-001",
        "test_type": "功能测试",
        "test_environment": "test",
    },

    # 2. 需求文档
    "requirement": {"requirement_doc_path": "config/requirement.md"},

    # 3. 数据库配置（真实连接，可选）
    "database": {
        "enabled": True,
        "type": "mysql",
        "host": "localhost",
        "port": 3306,
        "database": "myapp_db",
        "username": "root",
        "password": "password",
        "tables": [...]
    },

    # 4. 代码仓库（真实 Git 克隆或本地路径，可选）
    "frontend_repo": {
        "enabled": True,
        "type": "github",
        "url": "https://github.com/example/frontend",
        "branch": "main",
        "language": "react",
    },
    "backend_repo": {
        "enabled": True,
        "type": "local",
        "local_path": "/path/to/backend",
        "api_spec": "openapi.yaml",
        "language": "python",
    },

    # 5. LLM 配置（可选，配置后启用 AI 驱动）
    "llm": {
        "provider": "openai",
        "model": "gpt-4o",
        "api_key": "sk-...",
        "base_url": "https://api.openai.com/v1",
    },

    # 6. 测试执行配置
    "test": {"retry_failed": True, "retry_times": 2, "timeout": 30},

    # 7. 扩展配置
    "extra": {
        "api_base_url": "http://localhost:8000",
        "ui_base_url": "http://localhost:3000",
    },
}
```

### 步骤2：运行测试

```bash
# 运行自动化测试
python run_automation.py
```

### 步骤3：查看结果

测试完成后，在 `output/` 目录查看：
- `test_cases.csv` / `test_cases.xlsx` - 测试用例
- `defects.csv` / `defects.xlsx` - 缺陷清单
- `test_report.html` - HTML报告
- `results.json` - 完整结果 JSON

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
    "project": {
        "project_name": "项目名称",
        "project_code": "项目代码",
        "test_type": "功能测试/性能测试/安全测试/全面测试",
        "test_environment": "dev/test/staging",
    },

    # ========== 需求文档 ==========
    "requirement": {
        "requirement_doc_path": "config/requirement.md",  # 从文件读取
        # 或
        "requirement_doc": "直接填写需求内容...",
    },

    # ========== 数据库配置（真实连接） ==========
    "database": {
        "enabled": False,
        "type": "mysql/postgresql/sqlite",
        "host": "localhost",
        "port": 3306,
        "database": "db_name",
        "username": "user",
        "password": "password",
        "tables": [...]  # 表结构定义（连接失败时兜底）
    },

    # ========== 代码仓库 ==========
    "frontend_repo": {
        "enabled": False,
        "type": "github/gitlab/gitee/local",
        "url": "仓库地址",
        "branch": "main",
        "language": "react/vue/angular",
        "test_framework": "jest/playwright/cypress",
        "local_path": "",      # local 类型时使用本地路径
        "api_spec": "",        # 本地或远程 OpenAPI 规范路径
    },
    "backend_repo": {
        "enabled": False,
        "type": "github/gitlab/gitee/local",
        "url": "仓库地址",
        "branch": "main",
        "language": "python/java/node",
        "test_framework": "pytest/junit/mocha",
        "local_path": "",
        "api_spec": "openapi.yaml",
    },

    # ========== LLM 配置 ==========
    "llm": {
        "provider": "openai",           # openai/anthropic/azure_openai/ollama/custom
        "model": "gpt-4o",
        "api_key": "sk-...",
        "base_url": "https://api.openai.com/v1",
        "temperature": 0.2,
        "max_tokens": 4000,
        "timeout": 120,
    },

    # ========== 测试配置 ==========
    "test": {
        "coverage_target": 80,          # 覆盖率目标%
        "test_types": ["unit","integration","api","ui","e2e"],
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

    # ========== 扩展配置 ==========
    "extra": {
        "api_base_url": "http://localhost:8000",
        "ui_base_url": "http://localhost:3000",
    },
}
```

## 🔌 可插拔扩展

### 自定义 LLM Provider

```python
from automation.core.llm import LLMProvider, LLMResponse, register_provider

class MyProvider(LLMProvider):
    def chat(self, messages, **kwargs):
        return LLMResponse(content="...", model="my-model")

register_provider("my", MyProvider)
```

### 自定义测试执行器

```python
from automation.core.executor import TestExecutor, TestStatus, register_executor

class MyExecutor(TestExecutor):
    def execute(self, test_case, context):
        return self._make_result(TestStatus.PASSED, "ok")

register_executor("my", MyExecutor)
```

## 🔧 运行单元测试

框架自身包含 80+ 单元/集成测试，可验证框架功能：

```bash
# 安装依赖
pip install -r requirements.txt

# 运行所有测试
pytest

# 运行核心模块测试
pytest tests/unit/core/

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

1. **配置文件是核心** - 测试人员只需修改 `config/project_config.py`，无需改动代码
2. **需求文档支持** - 支持 Markdown 格式，也支持直接填写；LLM 未配置时走规则化兜底
3. **数据库可选** - 开启 `database.enabled=True` 后会真实连接并采集 Schema，失败时使用配置兜底
4. **代码仓库可选** - 支持 Git 克隆、本地路径、OpenAPI/Swagger 规范解析
5. **LLM 可选** - 配置 LLM 后 Agent 会使用 AI 生成需求、用例、缺陷分析；未配置时自动生成规则化结果
6. **真实执行** - API/DB/UI/Integration 执行器会真实调用目标系统，请在测试环境使用
7. **输出格式** - CSV/Excel 便于导入测试管理工具，HTML 报告便于人工查看

## 📄 许可证

MIT License

---

<p align="center">🚀 使用proDemoA，让测试工作更高效！</p>
