# -*- coding: utf-8 -*-
"""测试执行过程已知风险管理."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskStatus(Enum):
    OPEN = "open"
    MITIGATED = "mitigated"
    ACCEPTED = "accepted"
    RESOLVED = "resolved"


@dataclass
class Risk:
    risk_id: str
    milestone_id: str
    category: str
    level: RiskLevel
    description: str
    mitigation: str = ""
    status: RiskStatus = RiskStatus.OPEN
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_id": self.risk_id,
            "milestone_id": self.milestone_id,
            "category": self.category,
            "level": self.level.value,
            "description": self.description,
            "mitigation": self.mitigation,
            "status": self.status.value,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @property
    def icon(self) -> str:
        return {
            RiskLevel.LOW: "🟢",
            RiskLevel.MEDIUM: "🟡",
            RiskLevel.HIGH: "🟠",
            RiskLevel.CRITICAL: "🔴",
        }.get(self.level, "⚪")


class RiskManager:
    """跟踪测试全链路的已知风险."""

    def __init__(self):
        self.risks: List[Risk] = []

    def add(
        self,
        risk_id: str,
        milestone_id: str,
        category: str,
        level: RiskLevel,
        description: str,
        mitigation: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Risk:
        risk = Risk(
            risk_id=risk_id,
            milestone_id=milestone_id,
            category=category,
            level=level,
            description=description,
            mitigation=mitigation,
            metadata=metadata or {},
        )
        self.risks.append(risk)
        return risk

    def list_by_milestone(self, milestone_id: str) -> List[Risk]:
        return [r for r in self.risks if r.milestone_id == milestone_id]

    def list_open(self) -> List[Risk]:
        return [r for r in self.risks if r.status == RiskStatus.OPEN]

    def has_critical(self) -> bool:
        return any(r.level == RiskLevel.CRITICAL and r.status == RiskStatus.OPEN for r in self.risks)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risks": [r.to_dict() for r in self.risks],
            "open_count": len(self.list_open()),
            "critical_count": sum(
                1 for r in self.risks if r.level == RiskLevel.CRITICAL and r.status == RiskStatus.OPEN
            ),
        }

    def evaluate_milestone(
        self, milestone_id: str, context: Any, config: Optional[Any] = None
    ) -> List[Risk]:
        """根据当前上下文评估某里程碑的已知风险."""
        found: List[Risk] = []
        test_cases = getattr(context, "test_cases", []) or []
        execution_results = getattr(context, "execution_results", []) or []
        defects = getattr(context, "defects", []) or []
        requirement_doc = getattr(context, "requirement_doc", "") or ""
        code_info = getattr(context, "code_info", {}) or {}
        cfg = config or getattr(context, "config", None)

        # 配置校验阶段
        if milestone_id == "config_validated":
            if not cfg or not getattr(cfg.project, "name", None):
                found.append(
                    self.add(
                        "RISK-CFG-001",
                        milestone_id,
                        "配置",
                        RiskLevel.HIGH,
                        "项目名称未配置，可能导致输出文件命名混乱",
                        "在 config/project_config.py 中完善 project.name",
                    )
                )
            if not requirement_doc.strip():
                found.append(
                    self.add(
                        "RISK-CFG-002",
                        milestone_id,
                        "输入",
                        RiskLevel.CRITICAL,
                        "需求文档为空，AI 无法生成有效用例",
                        "提供需求文档或使用 --requirement 指定文件",
                    )
                )

        # 需求分析阶段
        if milestone_id == "requirement_analyzed":
            reqs = getattr(context, "metadata", {}).get("requirements", []) or []
            if len(reqs) < 1:
                found.append(
                    self.add(
                        "RISK-REQ-001",
                        milestone_id,
                        "需求",
                        RiskLevel.HIGH,
                        "未从需求文档提取到有效测试要点",
                        "检查需求文档是否包含明确的验收标准",
                    )
                )
            if len(requirement_doc) < 50:
                found.append(
                    self.add(
                        "RISK-REQ-002",
                        milestone_id,
                        "需求",
                        RiskLevel.MEDIUM,
                        "需求文档过短，覆盖范围可能不足",
                        "补充更详细的需求说明和业务流程",
                    )
                )

        # 代码解析阶段
        if milestone_id == "code_parsed":
            if not code_info:
                found.append(
                    self.add(
                        "RISK-CODE-001",
                        milestone_id,
                        "代码",
                        RiskLevel.MEDIUM,
                        "未获取到代码信息，接口/数据模型覆盖可能不全",
                        "配置代码仓库路径或提供 API 文档",
                    )
                )

        # 用例生成阶段
        if milestone_id == "test_cases_generated":
            min_cases = cfg.extra.get("min_test_cases", 1) if cfg and hasattr(cfg, "extra") else 1
            if len(test_cases) < min_cases:
                found.append(
                    self.add(
                        "RISK-TC-001",
                        milestone_id,
                        "用例",
                        RiskLevel.HIGH,
                        f"生成用例数 {len(test_cases)} 低于最低要求 {min_cases}",
                        "优化需求描述或降低 min_test_cases 阈值",
                    )
                )
            low_quality = [tc for tc in test_cases if tc.get("_quality_score", 0.5) < 0.5]
            if low_quality:
                found.append(
                    self.add(
                        "RISK-TC-002",
                        milestone_id,
                        "用例",
                        RiskLevel.MEDIUM,
                        f"发现 {len(low_quality)} 个低质量用例",
                        "人工复核并补充前置条件与预期结果",
                    )
                )

        # 测试执行阶段
        if milestone_id == "tests_executed":
            if not execution_results:
                found.append(
                    self.add(
                        "RISK-EXEC-001",
                        milestone_id,
                        "执行",
                        RiskLevel.CRITICAL,
                        "无任何执行结果，可能环境不可达或执行器异常",
                        "检查测试环境连通性、浏览器驱动及账号配置",
                    )
                )
            else:
                failed = sum(1 for r in execution_results if r.get("status") != "passed")
                rate = failed / len(execution_results)
                if rate > 0.5:
                    found.append(
                        self.add(
                            "RISK-EXEC-002",
                            milestone_id,
                            "执行",
                            RiskLevel.HIGH,
                            f"失败率 {rate:.1%}，可能存在环境不稳定或被测系统变更",
                            "排查失败用例并确认环境版本",
                        )
                    )

        # 缺陷发现阶段
        if milestone_id == "defects_detected":
            critical = [d for d in defects if d.get("severity") in {"critical", "high"}]
            if critical:
                found.append(
                    self.add(
                        "RISK-DEF-001",
                        milestone_id,
                        "缺陷",
                        RiskLevel.HIGH,
                        f"发现 {len(critical)} 个严重/高危缺陷",
                        "建议人工复核并优先修复阻塞性问题",
                    )
                )

        # 报告生成阶段
        if milestone_id == "report_generated":
            report_path = getattr(context, "metadata", {}).get("report_path", "")
            if not report_path:
                found.append(
                    self.add(
                        "RISK-RPT-001",
                        milestone_id,
                        "报告",
                        RiskLevel.MEDIUM,
                        "未生成报告文件路径",
                        "检查输出目录权限与报告生成器配置",
                    )
                )

        return found
