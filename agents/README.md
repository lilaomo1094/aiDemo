# AI Agent 索引

本项目整合了来自 [agency-agents-zh](https://github.com/jnMetaCode/agency-agents-zh) 的AI智能体，用于辅助测试工作。

## 目录结构

```
agents/
├── testing/          # 测试专用Agent (9个)
├── engineering/      # 工程类Agent (34个)
└── index.json        # Agent索引文件
```

## 测试Agent列表 (9个)

| Agent名称 | 文件 | 说明 |
|----------|------|------|
| 无障碍审计师 | testing-accessibility-auditor.md | Web/应用无障碍测试 |
| API测试工程师 | testing-api-tester.md | API接口测试 |
| 嵌入式QA工程师 | testing-embedded-qa-engineer.md | 嵌入式系统QA |
| 证据收集器 | testing-evidence-collector.md | 测试证据收集 |
| 性能基准测试工程师 | testing-performance-benchmarker.md | 性能测试 |
| 现实检查员 | testing-reality-checker.md | 真实性验证 |
| 测试结果分析师 | testing-test-results-analyzer.md | 测试结果分析 |
| 工具评估师 | testing-tool-evaluator.md | 测试工具评估 |
| 工作流优化师 | testing-workflow-optimizer.md | 测试流程优化 |

## 工程类Agent列表 (34个)

### 开发类
| Agent名称 | 说明 |
|----------|------|
| 前端开发者 | React/Vue开发 |
| 后端架构师 | API设计/数据库架构 |
| AI工程师 | 机器学习/模型部署 |
| 移动应用开发者 | iOS/Android开发 |
| 高级开发者 | Laravel/高端CSS |

### 运维类
| Agent名称 | 说明 |
|----------|------|
| DevOps自动化 | CI/CD/基础设施自动化 |
| SRE | 站点可靠性工程 |
| 故障响应指挥官 | 应急响应 |
| 自主优化架构师 | 自适应系统 |

### 质量类
| Agent名称 | 说明 |
|----------|------|
| 代码审查员 | 代码审查/安全审计 |
| 安全工程师 | 威胁建模/漏洞评估 |
| 数据库优化师 | 性能调优 |
| 技术文档工程师 | API文档 |

### 专项类
| Agent名称 | 说明 |
|----------|------|
| 快速原型师 | POC/MVP开发 |
| 数据工程师 | ETL/数据管线 |
| Git工作流大师 | 分支策略 |
| 软件架构师 | 系统设计 |

## 使用方式

这些Agent可通过以下方式使用：

1. **Claude Code / GitHub Copilot**: 直接读取Agent的.md文件获取提示词
2. **Cursor**: 导入Agent配置
3. **其他AI IDE**: 参考Agent的描述和流程

## 来源

- 原仓库: [jnMetaCode/agency-agents-zh](https://github.com/jnMetaCode/agency-agents-zh)
- 许可证: MIT
- 版本: 186个Agent (本项目包含43个)

## 更新日志

- 2026-05-06: 初始导入 (testing 9个 + engineering 34个)
