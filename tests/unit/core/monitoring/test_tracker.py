# -*- coding: utf-8 -*-
from automation.core.monitoring import TaskTracker
from automation.core.monitoring.tracker import NodeStatus


class TestTaskTracker:
    def test_nodes_initialized(self):
        tracker = TaskTracker("RUN-001")
        assert "task_submitted" in tracker.nodes
        assert "config_validated" in tracker.nodes
        assert len(tracker.nodes) == 12

    def test_start_and_finish_node(self):
        tracker = TaskTracker("RUN-001")
        tracker.start_node("config_validated", "input")
        assert tracker.get_node("config_validated").status == NodeStatus.RUNNING
        tracker.finish_node("config_validated", NodeStatus.PASSED, "output")
        assert tracker.get_node("config_validated").status == NodeStatus.PASSED
        assert not tracker.is_blocked()

    def test_is_blocked(self):
        tracker = TaskTracker("RUN-001")
        tracker.finish_node("config_validated", NodeStatus.BLOCKED, error="fail")
        assert tracker.is_blocked() is True
