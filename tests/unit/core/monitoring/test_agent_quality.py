# -*- coding: utf-8 -*-
"""AgentCallQualityManager 单元测试."""

import pytest

from automation.core.monitoring.agent_quality import (
    AGENT_INPUT_CONTRACTS,
    AGENT_OUTPUT_CONTRACTS,
    AgentCallQualityManager,
    QualityReport,
)
from automation.workflow.engine import AgentType, WorkflowContext


@pytest.fixture
def ctx():
    return WorkflowContext(run_id="test-run", project_info={"name": "demo"})


@pytest.fixture
def qm():
    return AgentCallQualityManager()


class TestInputValidation:
    def test_valid_input_passes(self, qm, ctx):
        ctx.requirement_doc = "用户登录功能需求"
        report = qm.validate_input("RequirementAnalyzer", ctx)
        assert report.passed
        assert report.score == 1.0

    def test_empty_allowed_field_warns_but_passes(self, qm, ctx):
        ctx.requirement_doc = ""
        report = qm.validate_input("RequirementAnalyzer", ctx)
        assert report.passed
        assert len(report.warnings) == 1

    def test_empty_disallowed_field_fails(self, qm, ctx):
        ctx.test_cases = []
        report = qm.validate_input("TestExecutor", ctx)
        assert not report.passed
        assert any("test_cases" in issue for issue in report.input_issues)

    def test_none_context_fails(self, qm):
        report = qm.validate_input("RequirementAnalyzer", None)
        assert not report.passed


class TestOutputValidation:
    def test_valid_output_passes(self, qm):
        output = {
            "requirements": [{"id": "REQ-1"}],
            "test_points": ["登录验证"],
            "acceptance_criteria": ["登录成功"],
            "summary": {"total": 1},
        }
        report = qm.validate_output("RequirementAnalyzer", output)
        assert report.passed

    def test_missing_required_key_fails(self, qm):
        output = {"requirements": []}
        report = qm.validate_output("RequirementAnalyzer", output)
        assert not report.passed
        assert any("test_points" in issue for issue in report.output_issues)

    def test_non_dict_output_fails(self, qm):
        report = qm.validate_output("RequirementAnalyzer", "not a dict")
        assert not report.passed
        assert report.score == 0.0

    def test_test_generator_missing_action_warns(self, qm):
        output = {
            "test_cases": [{"id": "TC-1", "name": "test"}],
            "summary": {"total": 1},
        }
        report = qm.validate_output("TestGenerator", output)
        assert report.passed  # 警告但不阻断
        assert report.score <= 0.8
        assert any("action" in w for w in report.warnings)

    def test_defect_detector_duplicate_ids_fail(self, qm):
        output = {
            "defects": [
                {"id": "DEF-001", "title": "bug1"},
                {"id": "DEF-001", "title": "bug2"},
            ],
            "summary": {"total": 2},
        }
        report = qm.validate_output("DefectDetector", output)
        assert not report.passed
        assert any("重复" in issue for issue in report.output_issues)


class TestBlockDownstream:
    def test_strict_mode_blocks_on_any_failure(self):
        qm = AgentCallQualityManager(strict_mode=True)
        report = QualityReport(agent_name="X", passed=False, score=0.9)
        assert qm.should_block_downstream(report)

    def test_non_strict_blocks_only_low_score(self, qm):
        high = QualityReport(agent_name="X", passed=False, score=0.5)
        low = QualityReport(agent_name="X", passed=False, score=0.1)
        assert not qm.should_block_downstream(high)
        assert qm.should_block_downstream(low)


class TestSummary:
    def test_summary_aggregates_reports(self, qm, ctx):
        ctx.requirement_doc = "需求"
        qm.validate_input("RequirementAnalyzer", ctx)
        qm.validate_output("RequirementAnalyzer", {
            "requirements": [], "test_points": [],
            "acceptance_criteria": [], "summary": {},
        })
        summary = qm.get_summary()
        assert summary["total_calls"] == 2
        assert summary["passed"] == 2
        assert summary["avg_score"] == 1.0


class TestContextSnapshot:
    def test_snapshot_and_restore(self, ctx):
        ctx.test_cases = [{"id": "TC-1"}]
        snap = ctx.snapshot()
        ctx.test_cases.append({"id": "TC-2"})
        assert len(ctx.test_cases) == 2
        ctx.restore(snap)
        assert len(ctx.test_cases) == 1

    def test_get_relevant_context_filters_fields(self, ctx):
        ctx.test_cases = [{"id": "TC-1"}]
        ctx.execution_results = [{"test_id": "TC-1", "status": "passed"}]
        ctx.defects = [{"id": "DEF-1"}]
        relevant = ctx.get_relevant_context(AgentType.TEST_EXECUTOR)
        assert "test_cases" in relevant
        assert "defects" not in relevant


class TestContextSizeTracking:
    """强化能力：上下文体积追踪."""

    def test_context_bytes_recorded_for_non_empty_context(self, qm, ctx):
        ctx.requirement_doc = "用户登录模块需求文档" * 20
        report = qm.validate_input("RequirementAnalyzer", ctx)
        assert report.context_bytes > 0

    def test_context_bloat_warning_when_oversized(self):
        qm = AgentCallQualityManager()
        qm.CONTEXT_BLOAT_THRESHOLD = 100  # 调低阈值便于测试
        ctx = WorkflowContext(run_id="t", project_info={"name": "d"})
        ctx.requirement_doc = "x" * 200
        report = qm.validate_input("RequirementAnalyzer", ctx)
        assert any("体积过大" in w for w in report.warnings)

    def test_output_bytes_recorded(self, qm):
        output = {
            "requirements": [{"id": "REQ-1"}],
            "test_points": ["登录验证"],
            "acceptance_criteria": ["登录成功"],
            "summary": {"total": 1},
        }
        report = qm.validate_output("RequirementAnalyzer", output)
        assert report.output_bytes > 0
        assert report.stage == "output"

    def test_duration_and_attempt_recorded(self, qm):
        output = {
            "requirements": [], "test_points": [],
            "acceptance_criteria": [], "summary": {},
        }
        report = qm.validate_output("RequirementAnalyzer", output, duration_seconds=2.5, attempt=2)
        assert report.duration_seconds == 2.5
        assert report.attempt == 2


class TestRetryLogic:
    """强化能力：质量可恢复时重试."""

    def test_should_retry_for_recoverable_score(self):
        qm = AgentCallQualityManager(max_retries=1)
        qm.record_attempt("DefectDetector")
        # 评分 0.7（重复 ID 场景）属于可恢复区间
        report = QualityReport(
            agent_name="DefectDetector", passed=False, score=0.7, stage="output"
        )
        assert qm.should_retry(report)

    def test_should_not_retry_for_critical_score(self):
        qm = AgentCallQualityManager(max_retries=1)
        qm.record_attempt("X")
        report = QualityReport(agent_name="X", passed=False, score=0.1, stage="output")
        assert not qm.should_retry(report)

    def test_should_not_retry_when_max_exceeded(self):
        qm = AgentCallQualityManager(max_retries=1)
        qm.record_attempt("X")
        qm.record_attempt("X")  # 已 2 次，超过上限
        report = QualityReport(agent_name="X", passed=False, score=0.5, stage="output")
        assert not qm.should_retry(report)

    def test_should_not_retry_passed_report(self):
        qm = AgentCallQualityManager()
        report = QualityReport(agent_name="X", passed=True, score=1.0, stage="output")
        assert not qm.should_retry(report)

    def test_should_not_retry_input_stage(self):
        qm = AgentCallQualityManager()
        report = QualityReport(agent_name="X", passed=False, score=0.5, stage="input")
        assert not qm.should_retry(report)

    def test_reset_agent_attempts(self):
        qm = AgentCallQualityManager(max_retries=1)
        qm.record_attempt("X")
        qm.record_attempt("X")
        qm.reset_agent_attempts("X")
        assert qm._agent_call_counts["X"] == 0


class TestPersistenceAndStats:
    """强化能力：质量报告持久化与 Agent 调用统计."""

    def test_save_reports_writes_json(self, qm, ctx, tmp_path):
        ctx.requirement_doc = "需求"
        qm.validate_input("RequirementAnalyzer", ctx)
        qm.validate_output("RequirementAnalyzer", {
            "requirements": [], "test_points": [],
            "acceptance_criteria": [], "summary": {},
        })
        path = tmp_path / "quality.json"
        result = qm.save_reports(str(path))
        assert result == str(path)
        assert path.exists()
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "summary" in data
        assert "agent_stats" in data
        assert "generated_at" in data

    def test_agent_call_stats_aggregates_per_agent(self, qm, ctx):
        ctx.requirement_doc = "需求"
        qm.validate_input("RequirementAnalyzer", ctx)
        qm.validate_output("RequirementAnalyzer", {
            "requirements": [], "test_points": [],
            "acceptance_criteria": [], "summary": {},
        })
        # 一次失败的 DefectDetector 输出
        qm.validate_output("DefectDetector", {
            "defects": [{"id": "D1"}, {"id": "D1"}], "summary": {},
        })
        stats = qm.get_agent_call_stats()
        assert "RequirementAnalyzer" in stats
        assert stats["RequirementAnalyzer"]["total"] == 1
        assert stats["RequirementAnalyzer"]["passed"] == 1
        assert "DefectDetector" in stats
        assert stats["DefectDetector"]["failed"] == 1
        assert stats["DefectDetector"]["pass_rate"] == 0.0

    def test_summary_includes_byte_totals(self, qm, ctx):
        ctx.requirement_doc = "需求文档内容"
        qm.validate_input("RequirementAnalyzer", ctx)
        summary = qm.get_summary()
        assert "total_context_bytes" in summary
        assert "total_output_bytes" in summary
        assert summary["total_context_bytes"] > 0
