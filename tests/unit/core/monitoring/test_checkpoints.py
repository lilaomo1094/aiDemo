# -*- coding: utf-8 -*-
from automation.core.config import PlatformConfig
from automation.core.monitoring import CheckpointManager, GateStatus


class DummyContext:
    def __init__(self, config=None, test_cases=None, execution_results=None, defects=None):
        self.config = config
        self.test_cases = test_cases or []
        self.execution_results = execution_results or []
        self.defects = defects or []


class TestCheckpointManager:
    def test_config_completeness_passed(self):
        config = PlatformConfig(project={"project_name": "test", "project_code": "T1"}, requirement={"requirement_doc": "doc"})
        mgr = CheckpointManager(config)
        ctx = DummyContext(config=config)
        results = mgr.evaluate("config_validated", ctx)
        assert results[0].status == GateStatus.PASSED

    def test_test_case_quantity_blocked(self):
        config = PlatformConfig(extra={"min_test_cases": 3})
        mgr = CheckpointManager(config)
        ctx = DummyContext(test_cases=[{"id": "1"}])
        results = mgr.evaluate("test_cases_generated", ctx)
        quantity = [r for r in results if r.checkpoint_id == "test_case_quantity"][0]
        assert quantity.status == GateStatus.BLOCKED

    def test_pass_rate_warning(self):
        config = PlatformConfig(test={"coverage_target": 80})
        mgr = CheckpointManager(config)
        ctx = DummyContext(execution_results=[{"status": "passed"}, {"status": "failed"}])
        results = mgr.evaluate("tests_executed", ctx)
        pass_rate = [r for r in results if r.checkpoint_id == "pass_rate"][0]
        assert pass_rate.status == GateStatus.WARNING
