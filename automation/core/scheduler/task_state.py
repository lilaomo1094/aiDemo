# -*- coding: utf-8 -*-
"""任务状态管理."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class TaskStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


@dataclass
class TaskState:
    task_id: str
    run_id: str
    config_path: str
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 5  # 1-10，数字越小优先级越高
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    tracker_data: Dict[str, Any] = field(default_factory=dict)
    callback_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "run_id": self.run_id,
            "config_path": self.config_path,
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error_message": self.error_message,
            "tracker_data": self.tracker_data,
            "callback_info": self.callback_info,
        }
