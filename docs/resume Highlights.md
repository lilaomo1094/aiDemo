# 智测（Zhice）自动化测试框架 —— 简历亮点萃取

> 本文件从项目整体架构、核心能力与工程实践中提炼出适合写入个人简历的内容，可直接复制到简历的「项目经历」或「技术能力」板块。

---

## 一、项目概述

**智测** 是一款面向 AI 驱动的测试自动化管理框架，旨在实现从需求解析、用例生成、测试执行到缺陷发现与报告生成的全链路自动化。框架以"版本"为核心组织测试资产，支持多 Agent 协作、多环境隔离、多类型测试执行与并发任务调度，适用于需要持续集成与质量保障的软件项目。

---

## 二、核心能力矩阵

| 能力域 | 已实现功能 |
|--------|-----------|
| **版本化资产管理** | 按版本（如 v0.7.30）隔离需求、配置、代码仓库、接口文档、测试报告；支持版本生命周期状态流转（draft/testing/released/deprecated）。 |
| **多 Agent 协作** | 需求分析师、高级测试工程师、质量 QA 三角色协同：解析需求 → 生成用例 → 执行测试 → 缺陷检测 → 报告生成。 |
| **多类型测试执行** | 支持 API（requests）、UI（Playwright，含 Edge/Chrome/Firefox/Safari/WebKit）、数据库（SQLAlchemy）、集成测试。 |
| **并发任务调度** | 基于优先级队列 + 线程池的任务调度器；支持任务依赖链、资源槽位限制、优先级抢占、状态持久化。 |
| **环境隔离** | dev/test/staging/prod 环境画像 + 版本级环境覆盖（数据库、网络、API/UI 地址）。 |
| **接口文档驱动** | OpenAPI/Swagger 2.0/3.0 解析，支持 `$ref` 展开、复杂 schema、响应提取，反向生成接口与 UI 自动化脚本。 |
| **质量监控** | 里程碑管理、风险扫描、卡控点（Checkpoint）、任务追踪、Hook 事件机制。 |
| **报告与可视化** | 生成静态 HTML 仪表板，聚合任务状态、里程碑、风险与版本资产；支持轻量 HTTP 服务预览。 |
| **LLM 集成** | 支持 OpenAI、Anthropic、Ollama 等模型，用于需求分析、用例生成、缺陷检测，并具备规则兜底能力。 |
| **IM 集成** | 飞书 / 企业微信机器人通知、Webhook 回调。 |

---

## 三、技术亮点（适合简历）

### 1. 架构设计
- 采用**分层架构**：核心层（config/executor/parser/scheduler）+ 管理层（version/task/framework）+ Agent 层 + 工作流层，职责清晰、可扩展。
- 设计**版本化配置体系**：通过 `config/environments/` + `versions/<version>/config.json` 实现项目级与版本级环境参数隔离，支持一键切换测试环境。
- 实现**插件化执行器工厂**：`create_executor(test_type, config)` 统一创建 API/UI/DB/Integration 执行器，新增测试类型无需改动核心调度逻辑。

### 2. 并发与资源调度
- 设计并实现**多线程任务调度器**，支持：
  - 优先级队列与并发执行；
  - `depends_on` 任务依赖链，依赖失败自动阻断下游；
  - 资源槽位限制（如 UI 浏览器并发数）与**优先级抢占**；
  - 任务状态持久化到本地 JSON，支持断点恢复与实时监控。
- 引入 `resources_acquired` 标志位，解决抢占场景下资源重复释放导致的记账异常，提升并发稳定性。

### 3. 自动化测试工程
- 构建 **Playwright -based UI 自动化执行器**，支持本地浏览器（Edge/Chrome）与 Playwright 内置浏览器（Chromium/Firefox/WebKit），具备截图、视频、HAR、控制台日志等证据采集能力。
- 实现 **OpenAPI/Swagger 解析器**，支持 `$ref` 递归展开、循环引用检测、Swagger 2.0 / OpenAPI 3.0 参数标准化，为接口自动化脚本生成提供结构化输入。
- 设计 **多 Agent 协作工作流**：RequirementAnalyzer → TestGenerator → TestExecutor → DefectDetector → ReportGenerator，通过 `WorkflowContext` 传递上下文，支持事件监听与里程碑跟踪。

### 4. 工程实践
- **测试驱动开发**：项目包含 127 个自动化测试（单元 / 集成 / E2E / 性能 / 安全 / AI 专项），全量通过。
- **配置即代码**：使用 Pydantic 进行配置校验，支持环境变量与 JSON/ Python 配置文件混合加载。
- **风险与质量卡控**：通过 Checkpoint、Milestone、Risk 模块在关键节点进行配置校验与风险扫描。
- **可观测性**：Hook 事件机制 + 任务状态持久化 + HTML 仪表板，实现测试执行全链路可视化。

---

## 四、可直接写入简历的描述

### 版本 A：侧重架构与调度（推荐）

> 独立负责智测（Zhice）AI 测试自动化框架的设计与迭代，构建以"版本"为核心的测试资产管理平台。主导实现多线程任务调度器，支持优先级队列、任务依赖链、资源槽位限制与优先级抢占；设计插件化执行器工厂，统一调度 API/UI/数据库/集成测试；基于 Playwright 实现跨浏览器 UI 自动化，集成 OpenAPI/Swagger 解析实现接口文档驱动的脚本生成。通过 Pydantic 配置校验、127 个自动化测试与 HTML 仪表板保障框架质量与可观测性。

### 版本 B：侧重多 Agent 与 AI 测试

> 设计并实现智测（Zhice）多 Agent 协作测试框架，串联需求分析、用例生成、测试执行、缺陷检测与报告生成五个角色。集成 OpenAI/Anthropic/Ollama 等 LLM 进行需求解析与用例设计，同时保留规则兜底保证稳定性；基于 WorkflowContext 实现上下文共享与事件驱动监控；支持 OpenAPI/Swagger 解析与 Playwright UI 自动化，输出结构化测试报告与缺陷清单。

### 版本 C：简洁版（1-2 行）

> 负责智测 AI 测试自动化框架研发，实现版本化资产管理、多 Agent 协作工作流、并发任务调度与 API/UI/DB 多类型测试执行，支撑项目全链路质量保障。

---

## 五、技术关键词

可根据简历 ATS 筛选需要选取：

`Python` · `Pydantic` · `Playwright` · `pytest` · `requests` · `SQLAlchemy` · `ThreadPoolExecutor` · `PriorityQueue` · `OpenAPI` · `Swagger` · `LLM` · `OpenAI` · `Anthropic` · `Ollama` · `RAG` · `Agent` · `Workflow` · `CI/CD` · `测试自动化` · `并发调度` · `资源隔离` · `版本管理` · `可观测性`

---

## 六、可量化的成果

- 框架覆盖 **API / UI / 数据库 / 集成** 四类测试执行。
- 任务调度器支持 **优先级抢占 + 资源槽位限制**，避免 UI 浏览器资源冲突。
- OpenAPI 解析器支持 **Swagger 2.0 / OpenAPI 3.0** 与 `$ref` 复杂引用展开。
- 项目自身具备 **127 个自动化测试**，覆盖单元、集成、E2E、性能、安全、AI 专项。
- 支持 **多环境配置隔离**（dev/test/staging/prod）与版本级参数覆盖。

---

*文档生成时间：2026-07-27*
