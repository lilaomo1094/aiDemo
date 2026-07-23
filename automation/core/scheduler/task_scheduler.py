# -*- coding: utf-8 -*-
"""多任务并发调度器."""

import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
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

    def __init__(self, max_workers: int = 4, state_dir: str = "output/scheduler"):
        self.max_workers = max_workers
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.tasks: Dict[str, TaskState] = {}
        self.task_queue: PriorityQueue = PriorityQueue()
        self.lock = threading.Lock()
        self.executor: Optional[ThreadPoolExecutor] = None
        self.hook_manager = HookManager()
        self._shutdown = False

    def submit(self, config_path: str, priority: int = 5, callback_info: Dict = None) -> str:
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
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="proDemoA-worker-")
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
            with self.lock:
                task = self.tasks.get(task_id)
                if not task or task.status != TaskStatus.QUEUED:
                    continue
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now().isoformat()
            self._save_state(task)
            self.hook_manager.emit("task_started", task.to_dict())
            self.executor.submit(self._run_task, task_id)

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
                self._save_state(task)
                return True
        return False

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
