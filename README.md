# AI Full-Stack Testing Framework

## 框架概述

proDemoA AI全栈测试框架是一个专为AI应用设计的全面测试解决方案，支持从单元测试到端到端测试的全方位质量保障。

## 框架架构

```
├── tests/
│   ├── unit/                  # 单元测试
│   │   ├── models/            # AI模型单元测试
│   │   ├── services/          # 服务层单元测试
│   │   └── utils/              # 工具函数测试
│   ├── integration/           # 集成测试
│   │   ├── api/                # API集成测试
│   │   ├── database/           # 数据库集成测试
│   │   └── ai_pipeline/        # AI流程集成测试
│   ├── e2e/                   # 端到端测试
│   │   ├── web/                # Web端E2E测试
│   │   └── api/                # API端E2E测试
│   ├── performance/            # 性能测试
│   │   ├── load/               # 负载测试
│   │   └── stress/             # 压力测试
│   ├── security/               # 安全测试
│   │   ├── auth/               # 认证测试
│   │   └── vulnerability/       # 漏洞扫描
│   └── ai_specific/            # AI专项测试
│       ├── model_evaluation/   # 模型评估测试
│       ├── prompt/             # Prompt测试
│       └── accuracy/           # 准确性测试
├── fixtures/                  # 测试数据fixtures
├── helpers/                    # 测试辅助工具
├── config/                     # 测试配置
├── reports/                    # 测试报告
├── conftest.py                # Pytest配置
├── pytest.ini                  # Pytest设置
└── requirements-test.txt      # 测试依赖
```

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
