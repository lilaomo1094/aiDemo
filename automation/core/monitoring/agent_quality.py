# -*- coding: utf-8 -*-
"""Agent 调用质量管理器.

在每个 Agent 调用前后进行输入校验、输出校验与质量评分，
为工作流引擎提供质量门禁能力，避免低质量输出污染下游 Agent.

强化能力：
- 上下文体积追踪（detect context bloat）
- 质量报告持久化（JSON 落盘，供仪表板可视化）
- 质量重试建议（基于评分与失败类型决定是否重试）
- Agent 调用统计（按 Agent 聚合成功率/平均评分/耗时）
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


def _estimate_size(obj: Any) -> int:
    """粗略估算对象序列化后的字节数，用于上下文体积追踪."""
    if obj is None:
        return 0
    try:
        if isinstance(obj, (str, bytes)):
            return len(obj)
        if isinstance(obj, dict):
            return sum(_estimate_size(k) + _estimate_size(v) for k, v in obj.items())
        if isinstance(obj, (list, tuple, set)):
            return sum(_estimate_size(i) for i in obj)
        # 自定义对象（如 WorkflowContext）：按属性字典估算
        if hasattr(obj, "__dict__"):
            return _estimate_size(vars(obj))
        return len(str(obj))
    except Exception:
        return 0


@dataclass
class QualityReport:
    """单次 Agent 调用的质量报告."""
    agent_name: str
    passed: bool
    input_issues: List[str] = field(default_factory=list)
    output_issues: List[str] = field(default_factory=list)
    score: float = 1.0
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    # 强化字段：上下文体积与执行耗时
    context_bytes: int = 0
    output_bytes: int = 0
    duration_seconds: float = 0.0
    attempt: int = 1
    stage: str = "output"  # input | output

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "passed": self.passed,
            "input_issues": self.input_issues,
            "output_issues": self.output_issues,
            "score": self.score,
            "warnings": self.warnings,
            "timestamp": self.timestamp,
            "context_bytes": self.context_bytes,
            "output_bytes": self.output_bytes,
            "duration_seconds": self.duration_seconds,
            "attempt": self.attempt,
            "stage": self.stage,
        }


# ------------------------------------------------------------------ #
# 输入 / 输出契约定义
# ------------------------------------------------------------------ #
AGENT_INPUT_CONTRACTS: Dict[str, Dict[str, Any]] = {
    "RequirementAnalyzer": {
        "required_context_fields": ["requirement_doc"],
        "allow_empty": {"requirement_doc": True},  # 空时使用示例文档
    },
    "CodeParser": {
        "required_context_fields": ["metadata"],
        "allow_empty": {"metadata": True},
    },
    "TestGenerator": {
        "required_context_fields": ["metadata", "code_info"],
        "allow_empty": {"code_info": True},
    },
    "TestExecutor": {
        "required_context_fields": ["test_cases"],
        "allow_empty": {"test_cases": False},
    },
    "DefectDetector": {
        "required_context_fields": ["execution_results"],
        "allow_empty": {"execution_results": True},
    },
    "ReportGenerator": {
        "required_context_fields": ["test_cases", "execution_results", "defects"],
        "allow_empty": {"test_cases": True, "execution_results": True, "defects": True},
    },
}

AGENT_OUTPUT_CONTRACTS: Dict[str, Dict[str, Any]] = {
    "RequirementAnalyzer": {
        "required_keys": ["requirements", "test_points", "acceptance_criteria", "summary"],
        "min_counts": {},
    },
    "CodeParser": {
        "required_keys": ["code_info"],
        "min_counts": {},
    },
    "TestGenerator": {
        "required_keys": ["test_cases", "summary"],
        "min_counts": {"test_cases": 0},
    },
    "TestExecutor": {
        "required_keys": ["execution_results", "summary"],
        "min_counts": {"execution_results": 0},
    },
    "DefectDetector": {
        "required_keys": ["defects", "summary"],
        "min_counts": {"defects": 0},
    },
    "ReportGenerator": {
        "required_keys": ["report_path", "output_files"],
        "min_counts": {},
    },
}


class AgentCallQualityManager:
    """Agent 调用质量管理器：输入校验 → 执行 → 输出校验 → 质量评分."""

    # 上下文体积阈值（字节），超过则告警冗余
    CONTEXT_BLOAT_THRESHOLD = 512 * 1024  # 512KB

    def __init__(self, strict_mode: bool = False, max_retries: int = 1):
        self.strict_mode = strict_mode
        self.max_retries = max_retries
        self.reports: List[QualityReport] = []
        # 按 Agent 聚合的调用计数（用于重试上限判断）
        self._agent_call_counts: Dict[str, int] = {}

    def validate_input(self, agent_name: str, context: Any) -> QualityReport:
        """在 Agent 执行前校验上下文输入，并追踪上下文体积."""
        contract = AGENT_INPUT_CONTRACTS.get(agent_name, {})
        issues: List[str] = []
        warnings: List[str] = []

        # 上下文体积追踪
        context_bytes = _estimate_size(context)

        for field_name in contract.get("required_context_fields", []):
            value = getattr(context, field_name, None) if context else None
            if value is None:
                issues.append(f"缺少必需上下文字段: {field_name}")
            elif not value and not contract.get("allow_empty", {}).get(field_name, True):
                issues.append(f"上下文字段为空且不允许: {field_name}")
            elif not value:
                warnings.append(f"上下文字段为空(已允许): {field_name}")

        # 上下文体积告警
        if context_bytes > self.CONTEXT_BLOAT_THRESHOLD:
            warnings.append(
                f"上下文体积过大: {context_bytes} 字节 > {self.CONTEXT_BLOAT_THRESHOLD}，建议精简"
            )

        report = QualityReport(
            agent_name=agent_name,
            passed=len(issues) == 0,
            input_issues=issues,
            warnings=warnings,
            score=0.0 if issues else 1.0,
            context_bytes=context_bytes,
            stage="input",
        )
        self.reports.append(report)
        return report

    def validate_output(
        self,
        agent_name: str,
        output: Any,
        duration_seconds: float = 0.0,
        attempt: int = 1,
    ) -> QualityReport:
        """在 Agent 执行后校验输出，并追踪输出体积与耗时."""
        contract = AGENT_OUTPUT_CONTRACTS.get(agent_name, {})
        issues: List[str] = []
        warnings: List[str] = []

        output_bytes = _estimate_size(output)

        if not isinstance(output, dict):
            issues.append(f"输出不是 dict 类型: {type(output)}")
            report = QualityReport(
                agent_name=agent_name,
                passed=False,
                output_issues=issues,
                score=0.0,
                output_bytes=output_bytes,
                duration_seconds=duration_seconds,
                attempt=attempt,
                stage="output",
            )
            self.reports.append(report)
            return report

        for key in contract.get("required_keys", []):
            if key not in output:
                issues.append(f"输出缺少必需字段: {key}")

        for key, min_count in contract.get("min_counts", {}).items():
            value = output.get(key)
            if isinstance(value, list) and len(value) < min_count:
                issues.append(f"输出字段 {key} 数量不足: {len(value)} < {min_count}")

        # 质量评分
        score = 1.0
        if issues:
            score = max(0.0, 1.0 - 0.2 * len(issues))

        # 额外质量检查
        if agent_name == "TestGenerator":
            test_cases = output.get("test_cases", [])
            if test_cases:
                no_action = sum(1 for tc in test_cases if not tc.get("action") and not tc.get("test_data"))
                if no_action > 0:
                    warnings.append(f"{no_action} 个用例缺少 action/test_data")
                    score = min(score, 0.8)

        if agent_name == "DefectDetector":
            defects = output.get("defects", [])
            seen_ids = set()
            duplicates = 0
            for d in defects:
                did = d.get("id", "")
                if did in seen_ids:
                    duplicates += 1
                seen_ids.add(did)
            if duplicates > 0:
                issues.append(f"检测到 {duplicates} 个重复缺陷 ID")
                score = min(score, 0.7)

        report = QualityReport(
            agent_name=agent_name,
            passed=len(issues) == 0,
            output_issues=issues,
            warnings=warnings,
            score=score,
            output_bytes=output_bytes,
            duration_seconds=duration_seconds,
            attempt=attempt,
            stage="output",
        )
        self.reports.append(report)
        return report

    def should_block_downstream(self, report: QualityReport) -> bool:
        """根据质量报告决定是否阻断下游 Agent."""
        if self.strict_mode:
            return not report.passed
        # 非严格模式：仅输出校验失败且评分极低时阻断
        return report.score < 0.3

    def should_retry(self, report: QualityReport) -> bool:
        """根据质量报告决定是否重试 Agent 调用.

        重试条件：输出校验未通过但评分处于可恢复区间（0.3~0.7），
        且该 Agent 重试次数未超过上限。
        """
        if report.stage != "output":
            return False
        if report.passed:
            return False
        calls = self._agent_call_counts.get(report.agent_name, 0)
        if calls > self.max_retries:
            return False
        # 评分极低（<0.3）通常是结构性错误，重试无意义；直接阻断
        # 评分 0.3~0.7 之间属于可恢复质量问题（如重复 ID），值得重试
        return 0.3 <= report.score <= 0.7

    def record_attempt(self, agent_name: str):
        """记录一次 Agent 调用尝试（用于重试计数）."""
        self._agent_call_counts[agent_name] = self._agent_call_counts.get(agent_name, 0) + 1

    def reset_agent_attempts(self, agent_name: str):
        """重置某个 Agent 的重试计数."""
        self._agent_call_counts[agent_name] = 0

    def save_reports(self, path: str) -> str:
        """将质量报告持久化到 JSON 文件，供仪表板可视化."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        data = {
            "generated_at": datetime.now().isoformat(),
            "summary": self.get_summary(),
            "agent_stats": self.get_agent_call_stats(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        return path

    def get_agent_call_stats(self) -> Dict[str, Any]:
        """按 Agent 聚合调用统计：成功率、平均评分、平均耗时、平均上下文体积."""
        stats: Dict[str, Dict[str, Any]] = {}
        # 只统计 output 阶段的报告（每个 Agent 一次调用的最终结果）
        output_reports = [r for r in self.reports if r.stage == "output"]
        for r in output_reports:
            bucket = stats.setdefault(r.agent_name, {
                "total": 0, "passed": 0, "failed": 0,
                "scores": [], "durations": [], "context_bytes": [], "output_bytes": [],
            })
            bucket["total"] += 1
            if r.passed:
                bucket["passed"] += 1
            else:
                bucket["failed"] += 1
            bucket["scores"].append(r.score)
            bucket["durations"].append(r.duration_seconds)
            bucket["context_bytes"].append(r.context_bytes)
            bucket["output_bytes"].append(r.output_bytes)

        result = {}
        for name, b in stats.items():
            result[name] = {
                "total": b["total"],
                "passed": b["passed"],
                "failed": b["failed"],
                "pass_rate": round(b["passed"] / b["total"], 3) if b["total"] else 0.0,
                "avg_score": round(sum(b["scores"]) / len(b["scores"]), 3) if b["scores"] else 0.0,
                "avg_duration_seconds": round(sum(b["durations"]) / len(b["durations"]), 3) if b["durations"] else 0.0,
                "avg_context_bytes": round(sum(b["context_bytes"]) / len(b["context_bytes"])) if b["context_bytes"] else 0,
                "avg_output_bytes": round(sum(b["output_bytes"]) / len(b["output_bytes"])) if b["output_bytes"] else 0,
            }
        return result

    def get_summary(self) -> Dict[str, Any]:
        """获取所有 Agent 调用的质量摘要."""
        return {
            "total_calls": len(self.reports),
            "passed": sum(1 for r in self.reports if r.passed),
            "failed": sum(1 for r in self.reports if not r.passed),
            "avg_score": sum(r.score for r in self.reports) / len(self.reports) if self.reports else 0.0,
            "total_context_bytes": sum(r.context_bytes for r in self.reports),
            "total_output_bytes": sum(r.output_bytes for r in self.reports),
            "reports": [r.to_dict() for r in self.reports],
        }
