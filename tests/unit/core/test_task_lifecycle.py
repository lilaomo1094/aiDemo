# -*- coding: utf-8 -*-
"""回归测试：TaskLifecycleManager.retry 必须保留原任务的依赖与资源约束.

旧实现 retry 只转发 config_path/priority/callback_info，丢失 depends_on 与 resources，
导致重试任务会绕过依赖门控（在依赖未完成前先跑）和资源槽位限制（超过 resource_limits）。
"""
from unittest.mock import patch

import pytest

from automation.core.management import TaskLifecycleManager
from automation.core.scheduler import TaskStatus


@pytest.fixture
def lifecycle(tmp_path):
    return TaskLifecycleManager(state_dir=str(tmp_path / "lifecycle"), max_workers=2)


class TestRetry:
    def test_retry_forwards_depends_on_and_resources(self, lifecycle, tmp_path):
        config_path = tmp_path / "project_config.py"
        config_path.write_text("PROJECT_CONFIG = {}", encoding="utf-8")

        # 提交一个带依赖与资源约束的任务
        captured = {}

        original_submit = lifecycle.scheduler.submit

        def capture_submit(**kwargs):
            captured.update(kwargs)
            return original_submit(**kwargs)

        # 先构造一个 FAILED 任务作为重试源
        t1 = lifecycle.scheduler.submit(
            config_path=str(config_path),
            priority=5,
            depends_on=["TASK-PREREQ"],
            resources={"ui": 1},
            preemptible=False,
        )
        lifecycle.scheduler.tasks[t1].status = TaskStatus.FAILED

        with patch.object(lifecycle.scheduler, "submit", side_effect=capture_submit):
            new_id = lifecycle.retry(t1)

        assert new_id is not None, "retry 应返回新任务 ID"
        assert captured.get("depends_on") == ["TASK-PREREQ"], "重试任务必须保留 depends_on"
        assert captured.get("resources") == {"ui": 1}, "重试任务必须保留 resources"
        assert captured.get("preemptible") is False, "重试任务必须保留 preemptible"

    def test_retry_returns_none_for_running_task(self, lifecycle, tmp_path):
        config_path = tmp_path / "project_config.py"
        config_path.write_text("PROJECT_CONFIG = {}", encoding="utf-8")
        t1 = lifecycle.scheduler.submit(str(config_path), priority=5)
        lifecycle.scheduler.tasks[t1].status = TaskStatus.RUNNING
        assert lifecycle.retry(t1) is None
