# -*- coding: utf-8 -*-
import time

import pytest

from automation.core.scheduler import TaskScheduler, TaskStatus


@pytest.fixture
def scheduler(tmp_path):
    s = TaskScheduler(max_workers=2, state_dir=str(tmp_path / "scheduler"))
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
