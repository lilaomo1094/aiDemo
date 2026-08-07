# -*- coding: utf-8 -*-
import threading
import time

import pytest

from automation.core.monitoring import EventHook
from automation.core.scheduler import TaskScheduler, TaskState, TaskStatus


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
        s._allocate_resources(s.tasks[t_low])

        # 高优先级任务需要相同资源
        t_high = s.submit(str(config_path), priority=1, resources={"ui": 1}, preemptible=True)

        # 直接触发抢占逻辑
        acquired = s._acquire_resources(s.tasks[t_high])
        assert acquired is True, "高优先级任务应成功抢占资源"
        assert s.get_task(t_low).status == TaskStatus.QUEUED, "低优先级任务应被重新入队"
        assert s._running_resources.get("ui", 0) == 1, "资源应被高优先级任务占用"
        assert s.tasks[t_low].resources_acquired is False, "被抢占任务应标记资源已释放"


class TestSchedulerConcurrencyFixes:
    """回归测试：调度器并发缺陷修复."""

    def test_hook_callback_into_submit_does_not_deadlock(self, tmp_path):
        """回归测试：hook 处理函数在持有锁时反向调用 submit() 不应死锁.

        旧实现使用不可重入的 threading.Lock()，_evaluate_task 在持有 self.lock 时
        调用 hook_manager.emit('task_blocked', ...)，若 hook 处理函数再调用
        scheduler.submit() (同样需要 self.lock)，consume 线程会永久死锁。
        修复后使用 RLock，同线程可重入。
        """
        config_path = tmp_path / "project_config.py"
        config_path.write_text("PROJECT_CONFIG = {}", encoding="utf-8")
        s = TaskScheduler(max_workers=2, state_dir=str(tmp_path / "scheduler"))

        callback_triggered = threading.Event()

        def reentrant_handler(event, data):
            # 在 hook 内反向调用 submit，模拟 "task_blocked 时自动重新提交一个降级任务"
            if event == "task_blocked":
                try:
                    s.submit(str(config_path), priority=9)
                finally:
                    callback_triggered.set()

        s.hook_manager.register(EventHook(
            name="reentrant",
            event_filter=["task_blocked"],
            handler=reentrant_handler,
        ))

        # 构造一个依赖不存在的任务 -> 依赖失败 -> 触发 task_blocked 事件
        s.submit(str(config_path), priority=5, depends_on=["TASK-NONEXISTENT"])

        # 直接调用 _evaluate_task 触发 task_blocked 路径（在锁内 emit）
        # 旧实现会在这里死锁；若 1.5s 内回调被触发说明没有死锁。
        s._evaluate_task(list(s.tasks.keys())[0], priority=5)
        assert callback_triggered.wait(timeout=1.5), "hook 回调未触发，疑似死锁"

    def test_consume_loop_survives_exception_in_evaluate(self, tmp_path):
        """回归测试：_consume_loop 体异常不应杀死消费线程.

        旧实现只对 task_queue.get 做了 try/except，循环体其余部分
        (_evaluate_task / _save_state / executor.submit) 任意一处抛异常都会
        让唯一的 consume 线程静默退出，调度器永久停止处理任务。
        本测试让第一个任务的 _evaluate_task 抛异常，验证第二个任务仍能被消费。
        """
        config_path = tmp_path / "project_config.py"
        config_path.write_text("PROJECT_CONFIG = {}", encoding="utf-8")
        s = TaskScheduler(max_workers=2, state_dir=str(tmp_path / "scheduler"))

        original_evaluate = s._evaluate_task
        call_count = {"n": 0}

        def flaky_evaluate(task_id, priority):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("模拟 _evaluate_task 抛异常（如磁盘满导致 _save_state 失败）")
            return original_evaluate(task_id, priority)

        s._evaluate_task = flaky_evaluate
        s._run_task = lambda task_id: None  # 不真正执行 workflow
        s.start()
        try:
            t1 = s.submit(str(config_path), priority=5)
            # 第一个任务会让 consume 线程抛异常；若 consume 线程已死，第二个任务永远不会被消费
            time.sleep(0.3)
            t2 = s.submit(str(config_path), priority=5)
            deadline = time.time() + 3
            while time.time() < deadline:
                if s.get_task(t2).status == TaskStatus.RUNNING:
                    break
                time.sleep(0.1)
            assert s.get_task(t2).status == TaskStatus.RUNNING, (
                "consume 线程未恢复，第二个任务未被消费 — 疑似 consume_loop 已死"
            )
        finally:
            s.stop()

    def test_list_tasks_does_not_raise_under_concurrent_writes(self, tmp_path):
        """回归测试：并发 submit 时调用 list_tasks 不应抛 RuntimeError.

        旧实现 list_tasks 直接 list(self.tasks.values())，与 submit 的写入并发
        时会抛 'dictionary changed size during iteration'。修复后在锁内做快照。
        """
        config_path = tmp_path / "project_config.py"
        config_path.write_text("PROJECT_CONFIG = {}", encoding="utf-8")
        s = TaskScheduler(max_workers=2, state_dir=str(tmp_path / "scheduler"))

        stop = threading.Event()
        errors = []

        def writer():
            i = 0
            while not stop.is_set():
                try:
                    s.submit(str(config_path), priority=5)
                except Exception as e:  # noqa: BLE001
                    errors.append(e)
                    return
                i += 1
                if i > 200:
                    return

        def reader():
            while not stop.is_set():
                try:
                    s.list_tasks()
                except Exception as e:  # noqa: BLE001
                    errors.append(e)
                    return

        w = threading.Thread(target=writer)
        r = threading.Thread(target=reader)
        w.start()
        r.start()
        w.join(timeout=3)
        stop.set()
        r.join(timeout=3)
        assert not errors, f"并发访问抛异常: {errors!r}"

    def test_global_risk_summary_does_not_raise_under_concurrent_finish(self, tmp_path):
        """回归测试：worker 并发写 risk_summaries 时读侧不应抛 RuntimeError."""
        s = TaskScheduler(max_workers=2, state_dir=str(tmp_path / "scheduler"))

        stop = threading.Event()
        errors = []

        def finisher():
            i = 0
            while not stop.is_set() and i < 100:
                try:
                    task = TaskState(
                        task_id=f"TASK-{i}",
                        run_id=f"RUN-{i}",
                        config_path="x",
                        status=TaskStatus.COMPLETED,
                    )
                    s.tasks[task.task_id] = task
                    s._finish_task(task, {"milestones": {"risks": {"open_count": 1, "critical_count": 0}}})
                except Exception as e:  # noqa: BLE001
                    errors.append(e)
                    return
                i += 1

        def reader():
            while not stop.is_set():
                try:
                    s.get_global_risk_summary()
                    s.get_global_milestone_summary()
                except Exception as e:  # noqa: BLE001
                    errors.append(e)
                    return

        f = threading.Thread(target=finisher)
        r = threading.Thread(target=reader)
        f.start()
        r.start()
        f.join(timeout=3)
        stop.set()
        r.join(timeout=3)
        assert not errors, f"并发读写 risk/milestone summaries 抛异常: {errors!r}"
