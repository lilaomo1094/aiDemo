# -*- coding: utf-8 -*-
"""任务执行节点追踪器."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"      # 节点通过验收
    BLOCKED = "blocked"    # 被卡控点拦截
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskNode:
    node_id: str
    name: str
    status: NodeStatus = NodeStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0
    input_summary: str = ""
    output_summary: str = ""
    error_message: str = ""
    checkpoint_results: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def start(self):
        self.status = NodeStatus.RUNNING
        self.start_time = datetime.now()

    def finish(self, status: NodeStatus, output_summary: str = "", error: str = ""):
        self.status = status
        self.end_time = datetime.now()
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
        self.output_summary = output_summary
        self.error_message = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "error_message": self.error_message,
            "checkpoint_results": self.checkpoint_results,
            "metadata": self.metadata,
        }


class TaskTracker:
    """追踪一次测试任务的所有关键节点."""

    NODES = [
        "task_submitted",
        "config_validated",
        "requirement_analyzed",
        "code_parsed",
        "test_cases_generated",
        "test_cases_reviewed",
        "tests_executed",
        "defects_detected",
        "report_generated",
        "training_data_generated",
        "result_notified",
        "task_completed",
    ]

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.nodes: Dict[str, TaskNode] = {}
        for node_id in self.NODES:
            self.nodes[node_id] = TaskNode(node_id=node_id, name=self._node_name(node_id))

    def _node_name(self, node_id: str) -> str:
        mapping = {
            "task_submitted": "任务提交",
            "config_validated": "配置校验",
            "requirement_analyzed": "需求分析",
            "code_parsed": "代码解析",
            "test_cases_generated": "用例生成",
            "test_cases_reviewed": "用例评审",
            "tests_executed": "测试执行",
            "defects_detected": "缺陷发现",
            "report_generated": "报告生成",
            "training_data_generated": "训练数据生成",
            "result_notified": "结果通知",
            "task_completed": "任务完成",
        }
        return mapping.get(node_id, node_id)

    def start_node(self, node_id: str, input_summary: str = ""):
        node = self.nodes.get(node_id)
        if node:
            node.input_summary = input_summary
            node.start()

    def finish_node(self, node_id: str, status: NodeStatus, output_summary: str = "", error: str = ""):
        node = self.nodes.get(node_id)
        if node:
            node.finish(status, output_summary, error)

    def add_checkpoint_result(self, node_id: str, result: Dict):
        node = self.nodes.get(node_id)
        if node:
            node.checkpoint_results.append(result)

    def get_node(self, node_id: str) -> Optional[TaskNode]:
        return self.nodes.get(node_id)

    def is_blocked(self) -> bool:
        return any(n.status == NodeStatus.BLOCKED for n in self.nodes.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "is_blocked": self.is_blocked(),
        }
