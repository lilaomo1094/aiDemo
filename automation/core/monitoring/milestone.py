# -*- coding: utf-8 -*-
"""测试任务关键节点里程碑管理."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .risk import RiskManager
from .tracker import NodeStatus, TaskNode, TaskTracker


@dataclass
class Milestone:
    """测试执行过程中的一个里程碑节点."""

    node_id: str
    name: str
    status: NodeStatus = NodeStatus.PENDING
    planned_start: Optional[datetime] = None
    planned_end: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    progress_percentage: float = 0.0
    risks: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "status": self.status.value,
            "planned_start": self.planned_start.isoformat() if self.planned_start else None,
            "planned_end": self.planned_end.isoformat() if self.planned_end else None,
            "actual_start": self.actual_start.isoformat() if self.actual_start else None,
            "actual_end": self.actual_end.isoformat() if self.actual_end else None,
            "progress_percentage": self.progress_percentage,
            "risks": self.risks,
            "metadata": self.metadata,
        }


class MilestoneManager:
    """将 TaskTracker 的关键节点升级为里程碑，并绑定风险."""

    def __init__(self, run_id: str, risk_manager: Optional[RiskManager] = None):
        self.run_id = run_id
        self.tracker = TaskTracker(run_id)
        self.risk_manager = risk_manager or RiskManager()
        self.milestones: Dict[str, Milestone] = {}
        for node_id in self.tracker.NODES:
            node = self.tracker.nodes[node_id]
            self.milestones[node_id] = Milestone(node_id=node_id, name=node.name)

    def start(self, node_id: str, input_summary: str = ""):
        self.tracker.start_node(node_id, input_summary)
        ms = self.milestones.get(node_id)
        if ms:
            ms.status = NodeStatus.RUNNING
            ms.actual_start = datetime.now()
            ms.progress_percentage = 25.0

    def update_progress(self, node_id: str, percentage: float):
        ms = self.milestones.get(node_id)
        if ms and ms.status == NodeStatus.RUNNING:
            ms.progress_percentage = max(0.0, min(100.0, percentage))

    def finish(self, node_id: str, status: NodeStatus, output_summary: str = "", error: str = ""):
        self.tracker.finish_node(node_id, status, output_summary, error)
        ms = self.milestones.get(node_id)
        if ms:
            ms.status = status
            ms.actual_end = datetime.now()
            ms.progress_percentage = 100.0 if status in (NodeStatus.PASSED, NodeStatus.FAILED) else 0.0
            if error:
                level = self._level_from_status(status)
                self.risk_manager.add(
                    f"RISK-{node_id.upper()}-ERR",
                    node_id,
                    "执行",
                    level,
                    f"里程碑 '{ms.name}' 执行异常: {error}",
                    "查看详细日志并修复阻塞条件",
                )

    @staticmethod
    def _level_from_status(status: NodeStatus):
        from .risk import RiskLevel
        mapping = {
            NodeStatus.FAILED: RiskLevel.HIGH,
            NodeStatus.BLOCKED: RiskLevel.CRITICAL,
            NodeStatus.SKIPPED: RiskLevel.MEDIUM,
        }
        return mapping.get(status, RiskLevel.LOW)

    def evaluate_risks(self, node_id: str, context: Any, config: Optional[Any] = None):
        risks = self.risk_manager.evaluate_milestone(node_id, context, config)
        ms = self.milestones.get(node_id)
        if ms:
            ms.risks = [r.to_dict() for r in risks]
        return risks

    def get_open_risks(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self.risk_manager.list_open()]

    def summary(self) -> Dict[str, Any]:
        total = len(self.milestones)
        completed = sum(1 for m in self.milestones.values() if m.status == NodeStatus.PASSED)
        failed = sum(1 for m in self.milestones.values() if m.status == NodeStatus.FAILED)
        running = sum(1 for m in self.milestones.values() if m.status == NodeStatus.RUNNING)
        return {
            "run_id": self.run_id,
            "total_milestones": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "open_risks": len(self.risk_manager.list_open()),
            "critical_risks": self.risk_manager.has_critical(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "summary": self.summary(),
            "milestones": {k: v.to_dict() for k, v in self.milestones.items()},
            "risks": self.risk_manager.to_dict(),
        }
