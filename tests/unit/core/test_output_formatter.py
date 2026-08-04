# -*- coding: utf-8 -*-
"""输出格式化单元测试."""

import csv
import json
from pathlib import Path

import pytest

from automation.core.output import OutputFormatter


@pytest.fixture
def formatter(tmp_path: Path):
    return OutputFormatter(tmp_path)


def test_save_json(formatter: OutputFormatter, tmp_path: Path):
    path = formatter.save_json({"key": "value"}, "result.json")
    assert Path(path).exists()
    assert json.loads(Path(path).read_text(encoding="utf-8")) == {"key": "value"}


def test_save_csv(formatter: OutputFormatter, tmp_path: Path):
    rows = [{"id": "1", "name": "tc1"}, {"id": "2", "name": "tc2"}]
    path = formatter.save_csv(rows, "cases.csv")
    assert Path(path).exists()
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        assert [r["id"] for r in reader] == ["1", "2"]


def test_save_excel(formatter: OutputFormatter, tmp_path: Path):
    rows = [{"id": "1", "name": "tc1"}]
    path = formatter.save_excel(rows, "cases.xlsx", "用例")
    assert Path(path).exists()


def test_save_html_report(formatter: OutputFormatter, tmp_path: Path):
    class FakeContext:
        project_info = {"project_name": "Test"}
        test_cases = [{"id": "1", "name": "tc1"}]
        execution_results = [{"test_id": "1", "test_name": "tc1", "status": "passed", "duration": 0.1}]
        defects = []
        metadata = {}

    path = formatter.save_html_report(FakeContext(), "report.html")
    content = Path(path).read_text(encoding="utf-8")
    assert "Test" in content
    assert "通过" in content
