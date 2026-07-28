# -*- coding: utf-8 -*-
"""Web 仪表板单元测试."""

import json

from automation.reporting import DashboardGenerator


def test_dashboard_generates_html(tmp_path):
    state_dir = tmp_path / "scheduler"
    state_dir.mkdir()
    (state_dir / "TASK-12345678.json").write_text(
        json.dumps(
            {
                "task_id": "TASK-12345678",
                "status": "completed",
                "priority": 1,
                "config_path": "config/project_config.py",
                "tracker_data": {"nodes": {"requirement_analyzed": {"status": "passed"}}},
            }
        ),
        encoding="utf-8",
    )

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({"versions": [{"version": "v0.7.30", "status": "draft"}]}),
        encoding="utf-8",
    )

    output_dir = tmp_path / "dashboard"
    dashboard = DashboardGenerator(
        state_dir=str(state_dir),
        version_manifest=str(manifest_path),
        output_dir=str(output_dir),
    )
    path = dashboard.generate()
    assert path.exists()
    html = path.read_text(encoding="utf-8")
    assert "智测自动化测试仪表板" in html
    assert "TASK-12345678" in html
    assert "v0.7.30" in html


def test_dashboard_empty_state(tmp_path):
    output_dir = tmp_path / "dashboard"
    dashboard = DashboardGenerator(
        state_dir=str(tmp_path / "empty_scheduler"),
        version_manifest=str(tmp_path / "no_manifest.json"),
        output_dir=str(output_dir),
    )
    path = dashboard.generate()
    html = path.read_text(encoding="utf-8")
    assert "暂无任务" in html
    assert "暂无版本" in html
