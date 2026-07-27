# -*- coding: utf-8 -*-
"""测试任务生命周期管理.

对 TaskScheduler 进行高层封装：提交、取消、重试、状态机、批量查询.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from automation.core.scheduler import TaskScheduler, TaskState, TaskStatus


class TaskLifecycleManager:
    """测试任务生命周期管理器."""

    def __init__(self, state_dir: str = "output/task_lifecycle", max_workers: int = 4):
        self.scheduler = TaskScheduler(max_workers=max_workers, state_dir=state_dir)
        self._lifecycle_dir = Path(state_dir)
        self._lifecycle_dir.mkdir(parents=True, exist_ok=True)
        self._listeners: List[Callable] = []

    def register_listener(self, listener: Callable):
        self._listeners.append(listener)

    def _emit(self, event: str, data: Dict[str, Any]):
        for listener in self._listeners:
            try:
                listener(event, data)
            except Exception as e:
                print(f"任务生命周期监听器错误: {e}")

    def submit(
        self,
        config_path: str,
        version: Optional[str] = None,
        priority: int = 5,
        network_type: Optional[str] = None,
        callback_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        """提交一个测试任务."""
        callback = callback_info or {}
        if version:
            callback["version"] = version
        if network_type:
            callback["network_type"] = network_type

        task_id = self.scheduler.submit(config_path=config_path, priority=priority, callback_info=callback)
        self._emit("task_submitted", {"task_id": task_id, "version": version, "priority": priority})
        return task_id

    def start_scheduler(self):
        """启动后台调度."""
        self.scheduler.start()

    def stop_scheduler(self):
        """停止后台调度."""
        self.scheduler.stop()

    def cancel(self, task_id: str) -> bool:
        """取消待执行或队列中的任务."""
        result = self.scheduler.cancel_task(task_id)
        if result:
            self._emit("task_cancelled", {"task_id": task_id})
        return result

    def retry(self, task_id: str) -> Optional[str]:
        """重试失败/取消的任务，生成新任务 ID."""
        task = self.scheduler.get_task(task_id)
        if not task:
            return None
        if task.status not in {TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.BLOCKED}:
            return None
        new_id = self.scheduler.submit(
            config_path=task.config_path,
            priority=max(1, task.priority - 1),
            callback_info=task.callback_info,
        )
        self._emit("task_retried", {"old_task_id": task_id, "new_task_id": new_id})
        return new_id

    def get_task(self, task_id: str) -> Optional[TaskState]:
        return self.scheduler.get_task(task_id)

    def list_tasks(
        self,
        status: Optional[str] = None,
        version: Optional[str] = None,
        limit: int = 100,
    ) -> List[TaskState]:
        """按状态或版本过滤任务."""
        tasks = self.scheduler.list_tasks()
        if status:
            tasks = [t for t in tasks if t.status.value == status.lower()]
        if version:
            tasks = [t for t in tasks if t.callback_info.get("version") == version]
        return tasks[:limit]

    def get_summary(self) -> Dict[str, Any]:
        """任务统计摘要."""
        tasks = self.scheduler.list_tasks()
        by_status: Dict[str, int] = {}
        for t in tasks:
            key = t.status.value
            by_status[key] = by_status.get(key, 0) + 1
        return {
            "total": len(tasks),
            "by_status": by_status,
            "running": sum(1 for t in tasks if t.status == TaskStatus.RUNNING),
            "completed": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
            "failed": sum(1 for t in tasks if t.status == TaskStatus.FAILED),
        }

    def wait_for_completion(self, task_id: str, timeout: Optional[float] = None) -> Optional[TaskState]:
        return self.scheduler.wait_for_completion(task_id, timeout=timeout)

    def save_run_record(self, task_id: str, record: Dict[str, Any]):
        """保存任务运行记录到生命周期目录."""
        path = self._lifecycle_dir / f"{task_id}.json"
        record["saved_at"] = datetime.now().isoformat()
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
