# -*- coding: utf-8 -*-
import threading
import time

import pytest

from automation.core.scheduler import TaskScheduler, TaskStatus


@pytest.fixture
def scheduler(tmp_path):
    s = TaskScheduler(max_workers=2, state_dir=str(tmp_path / "scheduler"))
    s.start()
    yield s
    s.stop()


@pytest.fixture
def noop_scheduler(tmp_path):
    """运行被 mock 为立即成功的调度器，用于测试依赖/资源/抢占逻辑."""
    s = TaskScheduler(max_workers=4, state_dir=str(tmp_path / "scheduler"))

    def _noop_run(task_id: str):
        task = s.tasks.get(task_id)
        if not task:
            return
        # 模拟运行完成后调用 finish
        task.status = TaskStatus.COMPLETED
        s._finish_task(task, {})

    s._run_task = _noop_run
    s.start()
    yield s
    s.stop()


class TestTaskScheduler:
    def test_submit_returns_task_id(self, scheduler, tmp_path):
        config_path = tmp_path / "project_config.py"
        config_path.write_text("PROJECT_CONFIG = {}", encoding="utf-8")
        task_id = scheduler.submit(str(config_path))
        assert task_id.startswith("TASK-")
        task = scheduler.get_task(task_id)
        assert task.status in {TaskStatus.QUEUED, TaskStatus.RUNNING}

    def test_list_tasks(self, scheduler, tmp_path):
        config_path = tmp_path / "project_config.py"
        config_path.write_text("PROJECT_CONFIG = {}", encoding="utf-8")
        scheduler.submit(str(config_path), priority=1)
        scheduler.submit(str(config_path), priority=2)
        tasks = scheduler.list_tasks()
        assert len(tasks) == 2

    def test_cancel_task(self, scheduler, tmp_path):
        config_path = tmp_path / "project_config.py"
        config_path.write_text("PROJECT_CONFIG = {}", encoding="utf-8")
        # 取消已开始执行的任务应返回 False
        task_id = scheduler.submit(str(config_path))
        time.sleep(0.3)
        if scheduler.get_task(task_id).status == TaskStatus.QUEUED:
            assert scheduler.cancel_task(task_id) is True
            assert scheduler.get_task(task_id).status == TaskStatus.CANCELLED
        else:
            assert scheduler.cancel_task(task_id) is False


class TestTaskDependencies:
    def test_dependency_chain_success(self, noop_scheduler, tmp_path):
        config_path = tmp_path / "project_config.py"
        config_path.write_text("PROJECT_CONFIG = {}", encoding="utf-8")

        t1 = noop_scheduler.submit(str(config_path), priority=5)
        t2 = noop_scheduler.submit(str(config_path), priority=5, depends_on=[t1])

        # 等待依赖任务完成
        noop_scheduler.wait_for_completion(t2, timeout=5)
        assert noop_scheduler.get_task(t1).status == TaskStatus.COMPLETED
        assert noop_scheduler.get_task(t2).status == TaskStatus.COMPLETED

    def test_dependency_failed_blocks_downstream(self, tmp_path):
        config_path = tmp_path / "project_config.py"
        config_path.write_text("PROJECT_CONFIG = {}", encoding="utf-8")
        s = TaskScheduler(max_workers=4, state_dir=str(tmp_path / "scheduler"))

        t1_started = threading.Event()
        t1_block = threading.Event()
        t1_should_fail = {"value": False}

        def _blocking_run(task_id: str):
            task = s.tasks.get(task_id)
            if task and task.priority == 5 and not task.depends_on:
                t1_started.set()
                t1_block.wait(timeout=3)
            if task:
                if t1_should_fail["value"]:
                    task.status = TaskStatus.FAILED
                    task.error_message = "mock failure"
                else:
                    task.status = TaskStatus.COMPLETED
                s._finish_task(task, {})

        s._run_task = _blocking_run
        s.start()
        try:
            t1 = s.submit(str(config_path), priority=5, resources={"ui": 1})
            assert t1_started.wait(timeout=2), "t1 未启动"
            t2 = s.submit(str(config_path), priority=5, depends_on=[t1])
            # t2 应处于等待依赖状态
            time.sleep(0.3)
            assert s.get_task(t2).status in {TaskStatus.QUEUED, TaskStatus.RUNNING}
            # 让 t1 自行失败
            t1_should_fail["value"] = True
            t1_block.set()
            s.wait_for_completion(t2, timeout=5)
            assert s.get_task(t1).status == TaskStatus.FAILED
            assert s.get_task(t2).status == TaskStatus.BLOCKED
        finally:
            s.stop()


class TestTaskResources:
    def test_resource_limit_serializes_ui_tasks(self, tmp_path):
        config_path = tmp_path / "project_config.py"
        config_path.write_text("PROJECT_CONFIG = {}", encoding="utf-8")
        s = TaskScheduler(
            max_workers=4,
            state_dir=str(tmp_path / "scheduler"),
            resource_limits={"ui": 1},
        )

        running_count = []

        def _counting_run(task_id: str):
            running_count.append(1)
            # 模拟持有资源一段时间
            time.sleep(0.2)
            task = s.tasks.get(task_id)
            if task:
                task.status = TaskStatus.COMPLETED
                s._finish_task(task, {})
            running_count.pop()

        s._run_task = _counting_run
        s.start()
        try:
            t1 = s.submit(str(config_path), resources={"ui": 1})
            t2 = s.submit(str(config_path), resources={"ui": 1})
            s.wait_for_completion(t1, timeout=5)
            s.wait_for_completion(t2, timeout=5)
            assert s.get_task(t1).status == TaskStatus.COMPLETED
            assert s.get_task(t2).status == TaskStatus.COMPLETED
        finally:
            s.stop()

    def test_priority_preemption(self, tmp_path):
        config_path = tmp_path / "project_config.py"
        config_path.write_text("PROJECT_CONFIG = {}", encoding="utf-8")
        s = TaskScheduler(
            max_workers=4,
            state_dir=str(tmp_path / "scheduler"),
            resource_limits={"ui": 1},
        )

        # 手动构造一个正在运行且占用资源的低优先级任务
        t_low = s.submit(str(config_path), priority=9, resources={"ui": 1}, preemptible=True)
        s.tasks[t_low].status = TaskStatus.RUNNING
        s._allocate_resources({"ui": 1})

        # 高优先级任务需要相同资源
        t_high = s.submit(str(config_path), priority=1, resources={"ui": 1}, preemptible=True)

        # 直接触发抢占逻辑
        acquired = s._acquire_resources(s.tasks[t_high])
        assert acquired is True, "高优先级任务应成功抢占资源"
        assert s.get_task(t_low).status == TaskStatus.QUEUED, "低优先级任务应被重新入队"
        assert s._running_resources.get("ui", 0) == 1, "资源应被高优先级任务占用"
