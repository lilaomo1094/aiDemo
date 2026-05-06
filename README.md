# AI Full-Stack Testing Framework

## 框架概述

proDemoA AI全栈测试框架是一个专为AI应用设计的全面测试解决方案，支持从单元测试到端到端测试的全方位质量保障。

## 框架架构

```
├── tests/                     # 测试代码
│   ├── unit/                  # 单元测试
│   ├── integration/           # 集成测试
│   ├── e2e/                  # 端到端测试
│   ├── performance/           # 性能测试
│   ├── security/             # 安全测试
│   └── ai_specific/          # AI专项测试
├── agents/                    # AI智能体 (43个)
│   ├── testing/              # 测试Agent (9个)
│   ├── engineering/          # 工程Agent (34个)
│   ├── index.json            # Agent索引
│   └── README.md             # Agent说明
├── fixtures/                  # 测试数据fixtures
├── helpers/                   # 测试辅助工具
├── config/                    # 测试配置
├── reports/                   # 测试报告
├── conftest.py               # Pytest配置
├── pytest.ini                 # Pytest设置
└── requirements-test.txt     # 测试依赖
```

## AI智能体 (Agents)

本项目整合了来自 [agency-agents-zh](https://github.com/jnMetaCode/agency-agents-zh) 的43个AI智能体，用于辅助测试工作。

### 测试Agent (9个)

| Agent | 说明 |
|-------|------|
| API测试工程师 | RESTful API接口测试 |
| 性能基准测试工程师 | 性能基准测试与优化 |
| 测试结果分析师 | 测试结果分析与报告 |
| 无障碍审计师 | Web无障碍标准合规性测试 |
| 证据收集器 | 测试过程证据收集与记录 |
| 工具评估师 | 测试工具评估与选型 |
| 工作流优化师 | 测试流程优化 |
| 现实检查员 | AI输出真实性验证 |
| 嵌入式QA工程师 | 嵌入式系统QA |

### 工程Agent (34个)

包括：前端开发者、后端架构师、AI工程师、代码审查员、安全工程师、DevOps自动化、SRE等。

详细Agent列表请查看 [agents/index.json](agents/index.json)

### 使用方式

1. 在AI IDE中读取 `agents/testing/` 或 `agents/engineering/` 下的 `.md` 文件
2. 使用Agent的提示词进行测试辅助工作
3. 可通过 `agents/index.json` 快速查找所需Agent

## 核心特性

### 1. 单元测试 (Unit Tests)
- AI模型功能验证
- 服务层逻辑测试
- 工具函数测试

### 2. 集成测试 (Integration Tests)
- API接口测试
- 数据库交互测试
- AI Pipeline流程测试

### 3. 端到端测试 (E2E Tests)
- Web应用全流程测试
- API完整链路测试

### 4. 性能测试 (Performance Tests)
- 负载测试
- 压力测试
- 响应时间测试

### 5. 安全测试 (Security Tests)
- 身份认证测试
- 漏洞扫描
- 数据安全测试

### 6. AI专项测试 (AI-Specific Tests)
- 模型评估测试
- Prompt有效性测试
- 输出准确性测试

## 技术栈

- **测试框架**: pytest
- **HTTP客户端**: requests / httpx
- **异步测试**: pytest-asyncio
- **Mock**: unittest.mock / pytest-mock
- **性能测试**: locust / pytest-benchmark
- **安全测试**: pytest-security
- **报告生成**: pytest-html / allure

## 快速开始

### 安装依赖
```bash
pip install -r requirements-test.txt
```

### 运行所有测试
```bash
pytest
```

### 运行特定类型测试
```bash
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
pytest tests/performance/
pytest tests/security/
pytest tests/ai_specific/
```

### 生成测试报告
```bash
pytest --html=reports/report.html
```

## 测试规范

### 命名规范
- 测试文件: `test_<模块名>.py`
- 测试类: `Test<功能名>`
- 测试函数: `test_<功能描述>`

### 断言规范
- 使用清晰的断言消息
- 包含预期值和实际值
- 失败时提供调试信息

### Fixture使用
- 共享fixture定义在conftest.py
- 特定fixture按模块存放
- 使用明确的fixture作用域

## AI模型测试特别说明

### 模型评估指标
- 准确率 (Accuracy)
- 精确率 (Precision)
- 召回率 (Recall)
- F1分数 (F1-Score)
- 响应时间 (Response Time)

### Prompt测试策略
- 边界条件测试
- 多样性测试
- 安全性测试
- 性能基准测试

## 持续集成

框架支持与CI/CD集成:
- GitHub Actions
- GitLab CI
- Jenkins

## 许可证

MIT License
