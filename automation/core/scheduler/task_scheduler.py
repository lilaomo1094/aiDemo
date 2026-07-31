# -*- coding: utf-8 -*-
"""多任务并发调度器.

支持能力：
- 优先级队列
- 任务依赖链（depends_on）
- 资源槽位限制（resources / resource_limits）
- 优先级抢占（preemptible）
"""

import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from queue import PriorityQueue
from typing import Any, Callable, Dict, List, Optional

from automation.core.config import PlatformConfig, load_config, merge_with_framework_config
from automation.core.monitoring import CheckpointManager, GateStatus, HookManager, TaskTracker
from automation.core.monitoring.tracker import NodeStatus
from automation.workflow.engine import WorkflowContext, WorkflowStatus, create_workflow

from .task_state import TaskState, TaskStatus


class TaskScheduler:
    """支持多线程并发执行多个测试任务的调度器."""

    def __init__(
        self,
        max_workers: int = 4,
        state_dir: str = "output/scheduler",
        resource_limits: Optional[Dict[str, int]] = None,
    ):
        self.max_workers = max_workers
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.tasks: Dict[str, TaskState] = {}
        self.task_queue: PriorityQueue = PriorityQueue()
        self.lock = threading.Lock()
        self.executor: Optional[ThreadPoolExecutor] = None
        self.hook_manager = HookManager()
        self._shutdown = False

        # 资源槽位管理
        self.resource_limits: Dict[str, int] = resource_limits or {}
        self._running_resources: Dict[str, int] = {}
        self._resource_lock = threading.Lock()

        # 里程碑与风险聚合
        self.milestone_summaries: Dict[str, Dict[str, Any]] = {}
        self.risk_summaries: Dict[str, Dict[str, Any]] = {}

    def submit(
        self,
        config_path: str,
        priority: int = 5,
        callback_info: Optional[Dict] = None,
        depends_on: Optional[List[str]] = None,
        resources: Optional[Dict[str, int]] = None,
        preemptible: bool = True,
    ) -> str:
        """提交一个测试任务到队列."""
        task_id = f"TASK-{uuid.uuid4().hex[:8]}"
        run_id = f"RUN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        task = TaskState(
            task_id=task_id,
            run_id=run_id,
            config_path=config_path,
            status=TaskStatus.QUEUED,
            priority=priority,
            callback_info=callback_info or {},
            depends_on=depends_on or [],
            resources=resources or {},
            preemptible=preemptible,
        )
        with self.lock:
            self.tasks[task_id] = task
        # PriorityQueue 按 priority 排序，数字越小越优先
        self.task_queue.put((priority, datetime.now().isoformat(), task_id))
        self.hook_manager.emit("task_submitted", task.to_dict())
        self._save_state(task)
        return task_id

    def start(self):
        """启动调度器，持续消费任务队列."""
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="aiAgent-worker-")
        self._shutdown = False
        threading.Thread(target=self._consume_loop, daemon=True).start()

    def stop(self):
        """停止调度器."""
        self._shutdown = True
        if self.executor:
            self.executor.shutdown(wait=True)

    def _consume_loop(self):
        while not self._shutdown:
            try:
                priority, _, task_id = self.task_queue.get(timeout=1)
            except Exception:
                continue

            action, task = self._evaluate_task(task_id, priority)
            if action == "sleep":
                time.sleep(0.1)
                continue
            if action == "continue":
                continue
            if action == "skip":
                continue

            # action == "run"
            self._save_state(task)
            self.hook_manager.emit("task_started", task.to_dict())
            self.executor.submit(self._run_task, task_id)

    def _evaluate_task(self, task_id: str, priority: int):
        with self.lock:
            task = self.tasks.get(task_id)
            if not task or task.status not in {TaskStatus.QUEUED, TaskStatus.PENDING}:
                return "skip", None

            # 依赖检查
            dep_status = self._check_dependencies(task)
            if dep_status == "waiting":
                self.task_queue.put((priority, datetime.now().isoformat(), task_id))
                return "sleep", task
            if dep_status == "failed":
                task.status = TaskStatus.BLOCKED
                task.error_message = "依赖任务失败"
                self._save_state(task)
                self.hook_manager.emit("task_blocked", task.to_dict())
                return "continue", task

            # 资源检查与抢占
            if not self._acquire_resources(task):
                self.task_queue.put((priority, datetime.now().isoformat(), task_id))
                return "sleep", task

            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now().isoformat()
            return "run", task

    def _check_dependencies(self, task: TaskState) -> str:
        """返回 'satisfied' | 'waiting' | 'failed'."""
        if not task.depends_on:
            return "satisfied"
        for dep_id in task.depends_on:
            dep = self.tasks.get(dep_id)
            if not dep:
                return "failed"
            if dep.status == TaskStatus.FAILED or dep.status == TaskStatus.BLOCKED or dep.status == TaskStatus.CANCELLED:
                return "failed"
            if dep.status != TaskStatus.COMPLETED:
                return "waiting"
        return "satisfied"

    def _acquire_resources(self, task: TaskState) -> bool:
        """尝试为任务获取资源，不足时尝试抢占低优先级任务."""
        if not task.resources:
            return True
        with self._resource_lock:
            # 检查是否直接满足
            if self._can_fit_resources(task.resources):
                self._allocate_resources(task)
                return True

            # 尝试抢占可抢占的低优先级运行中任务
            if self._preempt_resources_for(task):
                return True
        return False

    def _can_fit_resources(self, resources: Dict[str, int]) -> bool:
        for name, amount in resources.items():
            limit = self.resource_limits.get(name)
            if limit is None:
                # 未配置限制的资源默认不限制
                continue
            if self._running_resources.get(name, 0) + amount > limit:
                return False
        return True

    def _allocate_resources(self, task: TaskState):
        """为任务分配资源并标记已获取."""
        for name, amount in task.resources.items():
            self._running_resources[name] = self._running_resources.get(name, 0) + amount
        task.resources_acquired = True

    def _release_resources(self, task: TaskState):
        """释放任务占用的资源，幂等且线程安全."""
        if not task.resources_acquired:
            return
        with self._resource_lock:
            for name, amount in task.resources.items():
                current = self._running_resources.get(name, 0) - amount
                self._running_resources[name] = max(0, current)
            task.resources_acquired = False

    def _preempt_resources_for(self, task: TaskState) -> bool:
        """为当前任务抢占低优先级可抢占任务的资源.

        注意：本方法必须在 ``_resource_lock`` 内调用，因此直接操作
        ``_running_resources``，不再重复加锁。
        """
        candidates = [
            t for t in self.tasks.values()
            if t.status == TaskStatus.RUNNING
            and t.preemptible
            and t.priority > task.priority
            and t.task_id != task.task_id
        ]
        # 按优先级从低到高排序
        candidates.sort(key=lambda t: (-t.priority, t.started_at or ""))

        for victim in candidates:
            # 释放被抢占任务的资源（ bookkeeping 层面）
            for name, amount in victim.resources.items():
                current = self._running_resources.get(name, 0) - amount
                self._running_resources[name] = max(0, current)
            victim.resources_acquired = False

            # 标记被抢占任务重新入队
            victim.status = TaskStatus.QUEUED
            victim.started_at = None
            self.task_queue.put((victim.priority, datetime.now().isoformat(), victim.task_id))
            self.hook_manager.emit("task_preempted", victim.to_dict())

            if self._can_fit_resources(task.resources):
                self._allocate_resources(task)
                return True

        return False

    def _run_task(self, task_id: str):
        task = self.tasks.get(task_id)
        if not task:
            return
        try:
            config = load_config(task.config_path)
            config = merge_with_framework_config(config)
            config.extra["run_id"] = task.run_id
            config.extra["callback_info"] = task.callback_info

            tracker = TaskTracker(task.run_id)
            checkpoint_manager = CheckpointManager(config)
            workflow = create_workflow(config)

            # 注册监控事件
            def workflow_listener(event, data):
                self._on_workflow_event(task, tracker, checkpoint_manager, event, data)
            workflow.register_listener(workflow_listener)

            # 加载输入数据
            from run_automation import prepare_input_data
            input_data = prepare_input_data(config)

            tracker.start_node("task_submitted", f"config={task.config_path}")
            tracker.finish_node("task_submitted", NodeStatus.PASSED)

            tracker.start_node("config_validated", task.config_path)
            cp_results = checkpoint_manager.evaluate("config_validated", type("C", (), {"config": config})())
            for r in cp_results:
                tracker.add_checkpoint_result("config_validated", r.to_dict())
            if any(r.status == GateStatus.BLOCKED for r in cp_results):
                tracker.finish_node("config_validated", NodeStatus.BLOCKED, error="配置校验未通过")
                task.status = TaskStatus.BLOCKED
                task.error_message = "配置校验未通过"
                self._finish_task(task, {})
                return
            tracker.finish_node("config_validated", NodeStatus.PASSED)

            context = WorkflowContext(
                run_id=task.run_id,
                project_info=input_data,
                requirement_doc=input_data.get("requirement_doc", ""),
                database_schema=input_data.get("database_schema", {}),
                code_info=input_data.get("code_info", {}),
            )
            context.config = config

            result = workflow.run(context)

            # 最终状态
            if result["status"] == WorkflowStatus.COMPLETED.value:
                task.status = TaskStatus.COMPLETED
            else:
                task.status = TaskStatus.FAILED
                task.error_message = "; ".join(result.get("errors", []))

            task.result = result
            task.tracker_data = tracker.to_dict()
            self._finish_task(task, result)

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            self._finish_task(task, {})

    def _on_workflow_event(self, task: TaskState, tracker: TaskTracker, checkpoint_manager: CheckpointManager, event: str, data: Dict):
        node_mapping = {
            "task_started": None,
            "task_completed": None,
            "task_failed": None,
        }
        # 根据 workflow task 名称映射到监控节点
        task_name = data.get("task", "")
        task_id_map = {
            "需求分析": "requirement_analyzed",
            "代码解析": "code_parsed",
            "测试用例生成": "test_cases_generated",
            "测试执行": "tests_executed",
            "缺陷发现": "defects_detected",
            "报告生成": "report_generated",
            "训练数据生成": "training_data_generated",
        }
        node_id = task_id_map.get(task_name)
        if not node_id:
            return

        if event == "task_started":
            tracker.start_node(node_id, task_name)
        elif event == "task_completed":
            output = data.get("output", {})
            summary = ""
            if isinstance(output, dict):
                if "summary" in output:
                    summary = json.dumps(output["summary"], ensure_ascii=False)
                else:
                    summary = json.dumps({k: v for k, v in output.items() if k != "test_cases" and k != "execution_results" and k != "defects"}, ensure_ascii=False, default=str)[:200]
            tracker.finish_node(node_id, NodeStatus.PASSED, output_summary=summary)

            # 在该节点执行卡控
            cp_results = checkpoint_manager.evaluate(node_id, data.get("context"))
            for r in cp_results:
                tracker.add_checkpoint_result(node_id, r.to_dict())
        elif event == "task_failed":
            tracker.finish_node(node_id, NodeStatus.FAILED, error=data.get("error", ""))

    def _finish_task(self, task: TaskState, result: Dict):
        task.completed_at = datetime.now().isoformat()
        self._release_resources(task)

        # 聚合里程碑与风险到调度器全局视图
        milestones = result.get("milestones") if isinstance(result, dict) else None
        if milestones:
            self.milestone_summaries[task.run_id] = milestones
            risks = milestones.get("risks")
            if risks:
                self.risk_summaries[task.run_id] = risks

        self._save_state(task)
        self.hook_manager.emit("task_completed" if task.status == TaskStatus.COMPLETED else "task_failed", task.to_dict())

        # 回调通知
        if task.callback_info.get("im_channel"):
            self.hook_manager.emit("im_notification", {
                "channel": task.callback_info["im_channel"],
                "task": task.to_dict(),
            })

    def _save_state(self, task: TaskState):
        path = self.state_dir / f"{task.task_id}.json"
        path.write_text(json.dumps(task.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def get_task(self, task_id: str) -> Optional[TaskState]:
        return self.tasks.get(task_id)

    def list_tasks(self) -> List[TaskState]:
        return list(self.tasks.values())

    def cancel_task(self, task_id: str) -> bool:
        with self.lock:
            task = self.tasks.get(task_id)
            if task and task.status in {TaskStatus.PENDING, TaskStatus.QUEUED}:
                task.status = TaskStatus.CANCELLED
                self._release_resources(task)
                self._save_state(task)
                return True
        return False

    def get_global_risk_summary(self) -> Dict[str, Any]:
        """返回调度器内所有任务的风险聚合摘要."""
        total_open = 0
        total_critical = 0
        for summary in self.risk_summaries.values():
            total_open += summary.get("open_count", 0)
            total_critical += summary.get("critical_count", 0)
        return {
            "tasks_with_risks": len(self.risk_summaries),
            "total_open_risks": total_open,
            "total_critical_risks": total_critical,
            "risk_details": self.risk_summaries,
        }

    def get_global_milestone_summary(self) -> Dict[str, Any]:
        """返回所有任务的里程碑聚合摘要."""
        completed = 0
        failed = 0
        running = 0
        total = 0
        for ms in self.milestone_summaries.values():
            summary = ms.get("summary", {})
            completed += summary.get("completed", 0)
            failed += summary.get("failed", 0)
            running += summary.get("running", 0)
            total += summary.get("total_milestones", 0)
        return {
            "tasks": len(self.milestone_summaries),
            "total_milestones": total,
            "completed": completed,
            "failed": failed,
            "running": running,
        }

    def wait_for_completion(self, task_id: str, timeout: Optional[float] = None) -> Optional[TaskState]:
        import time
        start = time.time()
        while True:
            task = self.tasks.get(task_id)
            if task and task.status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.BLOCKED, TaskStatus.CANCELLED}:
                return task
            if timeout and (time.time() - start) > timeout:
                return task
            time.sleep(0.5)
