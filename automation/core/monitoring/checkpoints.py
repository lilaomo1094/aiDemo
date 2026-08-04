# -*- coding: utf-8 -*-
"""验收卡控点管理."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class GateStatus(Enum):
    PASSED = "passed"
    BLOCKED = "blocked"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class CheckpointResult:
    checkpoint_id: str
    name: str
    status: GateStatus
    message: str
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
        }


class CheckpointManager:
    """管理测试任务各节点的验收卡控规则."""

    def __init__(self, config):
        self.config = config
        self.rules = self._build_default_rules()
        self.custom_rules: Dict[str, List[Callable]] = {}

    def _build_default_rules(self) -> Dict[str, List[Callable]]:
        return {
            "config_validated": [self._check_config_completeness],
            "test_cases_generated": [self._check_test_case_quantity, self._check_test_case_quality],
            "test_cases_reviewed": [self._check_manual_approval],
            "tests_executed": [self._check_pass_rate],
            "defects_detected": [self._check_critical_defects],
        }

    def evaluate(self, node_id: str, context) -> List[CheckpointResult]:
        rules = self.rules.get(node_id, []) + self.custom_rules.get(node_id, [])
        results = []
        for rule in rules:
            results.append(rule(context))
        return results

    def register_rule(self, node_id: str, rule: Callable):
        self.custom_rules.setdefault(node_id, []).append(rule)

    # ============= 默认卡控规则 =============

    def _check_config_completeness(self, context) -> CheckpointResult:
        config = getattr(context, "config", None)
        errors = []
        if not config:
            errors.append("配置对象为空")
        else:
            if not config.project.name:
                errors.append("项目名称未配置")
            if not config.project.code:
                errors.append("项目代码未配置")
            if not config.requirement.load_text(config.base_dir):
                errors.append("需求文档为空")
        status = GateStatus.BLOCKED if errors else GateStatus.PASSED
        return CheckpointResult(
            checkpoint_id="config_completeness",
            name="配置完整性检查",
            status=status,
            message="; ".join(errors) if errors else "配置完整",
            details={"errors": errors},
        )

    def _check_test_case_quantity(self, context) -> CheckpointResult:
        test_cases = getattr(context, "test_cases", []) or []
        min_cases = getattr(self.config, "extra", {}).get("min_test_cases", 1)
        if len(test_cases) >= min_cases:
            return CheckpointResult(
                checkpoint_id="test_case_quantity",
                name="用例数量检查",
                status=GateStatus.PASSED,
                message=f"生成用例 {len(test_cases)} 个，满足最低要求 {min_cases}",
                details={"count": len(test_cases), "min_required": min_cases},
            )
        return CheckpointResult(
            checkpoint_id="test_case_quantity",
            name="用例数量检查",
            status=GateStatus.BLOCKED,
            message=f"生成用例 {len(test_cases)} 个，低于最低要求 {min_cases}",
            details={"count": len(test_cases), "min_required": min_cases},
        )

    def _check_test_case_quality(self, context) -> CheckpointResult:
        test_cases = getattr(context, "test_cases", []) or []
        threshold = getattr(self.config, "extra", {}).get("test_case_quality_threshold", 0.5)
        low_quality = [tc for tc in test_cases if tc.get("_quality_score", 0.5) < threshold]
        if not low_quality:
            return CheckpointResult(
                checkpoint_id="test_case_quality",
                name="用例质量检查",
                status=GateStatus.PASSED,
                message="所有用例质量分达标",
                details={"low_quality_count": 0},
            )
        return CheckpointResult(
            checkpoint_id="test_case_quality",
            name="用例质量检查",
            status=GateStatus.WARNING,
            message=f"发现 {len(low_quality)} 个低质量用例",
            details={"low_quality_count": len(low_quality)},
        )

    def _check_manual_approval(self, context) -> CheckpointResult:
        # 默认自动通过；在IM交互场景下可改为等待人工确认
        auto_approve = getattr(self.config, "extra", {}).get("auto_approve_test_cases", True)
        status = GateStatus.PASSED if auto_approve else GateStatus.BLOCKED
        return CheckpointResult(
            checkpoint_id="manual_approval",
            name="用例人工评审",
            status=status,
            message="已自动通过" if auto_approve else "等待人工确认",
            details={"auto_approve": auto_approve},
        )

    def _check_pass_rate(self, context) -> CheckpointResult:
        results = getattr(context, "execution_results", []) or []
        if not results:
            return CheckpointResult(
                checkpoint_id="pass_rate",
                name="执行通过率检查",
                status=GateStatus.BLOCKED,
                message="无执行结果",
                details={"pass_rate": 0.0},
            )
        passed = sum(1 for r in results if r.get("status") == "passed")
        rate = passed / len(results)
        target = getattr(self.config, "test", None)
        target_rate = target.coverage_target / 100 if target else 0.8
        status = GateStatus.PASSED if rate >= target_rate else GateStatus.WARNING
        return CheckpointResult(
            checkpoint_id="pass_rate",
            name="执行通过率检查",
            status=status,
            message=f"通过率 {rate:.2%}，目标 {target_rate:.2%}",
            details={"pass_rate": rate, "target": target_rate},
        )

    def _check_critical_defects(self, context) -> CheckpointResult:
        defects = getattr(context, "defects", []) or []
        critical = [d for d in defects if d.get("severity") in {"critical", "high"}]
        if not critical:
            return CheckpointResult(
                checkpoint_id="critical_defects",
                name="严重缺陷检查",
                status=GateStatus.PASSED,
                message="未发现严重缺陷",
                details={"critical_count": 0},
            )
        return CheckpointResult(
            checkpoint_id="critical_defects",
            name="严重缺陷检查",
            status=GateStatus.WARNING,
            message=f"发现 {len(critical)} 个严重/高危缺陷，建议人工复核",
            details={"critical_count": len(critical)},
        )
