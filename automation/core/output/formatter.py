# -*- coding: utf-8 -*-
"""统一输出格式化：CSV、JSON、HTML、Excel."""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from jinja2 import Template
except ImportError:
    Template = None


class OutputFormatter:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def save_json(self, data: Dict, path: str) -> str:
        full = self.base_dir / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(full)

    def save_csv(self, rows: List[Dict], path: str) -> str:
        full = self.base_dir / path
        full.parent.mkdir(parents=True, exist_ok=True)
        with open(full, "w", newline="", encoding="utf-8-sig") as f:
            if not rows:
                return str(full)
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return str(full)

    def save_excel(self, rows: List[Dict], path: str, sheet_name: str = "Sheet1") -> str:
        full = self.base_dir / path
        full.parent.mkdir(parents=True, exist_ok=True)
        try:
            from openpyxl import Workbook
        except ImportError:
            return ""
        wb = Workbook()
        ws = wb.active
        ws.title = sheet_name
        if rows:
            headers = list(rows[0].keys())
            ws.append(headers)
            for row in rows:
                ws.append([row.get(h, "") for h in headers])
        wb.save(full)
        return str(full)

    def save_html_report(self, context, path: str) -> str:
        full = self.base_dir / path
        full.parent.mkdir(parents=True, exist_ok=True)
        html = self._render_html(context)
        full.write_text(html, encoding="utf-8")
        return str(full)

    def _render_html(self, context) -> str:
        execution_results = getattr(context, "execution_results", []) or []
        passed = sum(1 for r in execution_results if r.get("status") == "passed")
        failed = sum(1 for r in execution_results if r.get("status") in {"failed", "error"})
        total = len(execution_results) or 1
        pass_rate = round(passed / total * 100, 2)

        test_cases = getattr(context, "test_cases", []) or []
        defects = getattr(context, "defects", []) or []
        project = getattr(context, "project_info", {})

        if Template is None:
            return self._render_simple_html(project, test_cases, passed, failed, pass_rate, defects, execution_results)

        template = Template("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>测试报告 - {{ project.get('project_name', '项目') }}</title>
    <style>
        body { font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
        .summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }
        .card { padding: 20px; border-radius: 8px; text-align: center; }
        .card.total { background: #e3f2fd; } .card.pass { background: #e8f5e9; }
        .card.fail { background: #ffebee; } .card.rate { background: #fff3e0; }
        .card .number { font-size: 36px; font-weight: bold; margin: 10px 0; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #4CAF50; color: #fff; }
        tr:hover { background: #f5f5f5; }
        .severity-critical, .severity-high { color: #d32f2f; font-weight: bold; }
        .severity-medium { color: #f57c00; } .severity-low { color: #388e3c; }
        .status-passed { color: #388e3c; } .status-failed, .status-error { color: #d32f2f; }
        .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #888; }
    </style>
</head>
<body>
    <div class="container">
        <h1>测试报告</h1>
        <p><strong>项目：</strong>{{ project.get('project_name', 'N/A') }} ({{ project.get('project_code', '') }})</p>
        <p><strong>测试类型：</strong>{{ project.get('test_type', '全面测试') }}</p>
        <p><strong>生成时间：</strong>{{ now }}</p>

        <h2>测试概览</h2>
        <div class="summary">
            <div class="card total"><div>总用例数</div><div class="number">{{ test_cases|length }}</div></div>
            <div class="card pass"><div>通过</div><div class="number">{{ passed }}</div></div>
            <div class="card fail"><div>失败</div><div class="number">{{ failed }}</div></div>
            <div class="card rate"><div>通过率</div><div class="number">{{ pass_rate }}%</div></div>
        </div>

        <h2>缺陷清单</h2>
        <table>
            <tr><th>ID</th><th>标题</th><th>严重</th><th>优先级</th><th>模块</th><th>类型</th></tr>
            {% for d in defects %}
            <tr>
                <td>{{ d.get('id', '') }}</td>
                <td>{{ d.get('title', '') }}</td>
                <td class="severity-{{ d.get('severity', 'low') }}">{{ d.get('severity', '') }}</td>
                <td>{{ d.get('priority', '') }}</td>
                <td>{{ d.get('module', '') }}</td>
                <td>{{ d.get('type', '') }}</td>
            </tr>
            {% else %}
            <tr><td colspan="6">暂无缺陷</td></tr>
            {% endfor %}
        </table>

        <h2>执行详情</h2>
        <table>
            <tr><th>ID</th><th>名称</th><th>类型</th><th>状态</th><th>耗时</th><th>信息</th></tr>
            {% for r in execution_results %}
            <tr>
                <td>{{ r.get('test_id', '') }}</td>
                <td>{{ r.get('test_name', '') }}</td>
                <td>{{ r.get('test_type', '') }}</td>
                <td class="status-{{ r.get('status', '') }}">{{ r.get('status', '') }}</td>
                <td>{{ r.get('duration', 0) }}s</td>
                <td>{{ r.get('error_message', '') }}</td>
            </tr>
            {% endfor %}
        </table>

        <div class="footer">
            <p>智测 全链路自动化测试平台</p>
        </div>
    </div>
</body>
</html>""")
        return template.render(
            project=project,
            now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            test_cases=test_cases,
            passed=passed,
            failed=failed,
            pass_rate=pass_rate,
            defects=defects,
            execution_results=execution_results,
        )

    def _render_simple_html(self, project, test_cases, passed, failed, pass_rate, defects, execution_results) -> str:
        """jinja2 缺失时的极简 HTML 报告."""
        rows = []
        for r in execution_results:
            rows.append(
                f"<tr><td>{r.get('test_id', '')}</td><td>{r.get('test_name', '')}</td>"
                f"<td>{r.get('status', '')}</td><td>{r.get('duration', 0)}s</td></tr>"
            )
        return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>测试报告</title></head>
<body>
<h1>测试报告 - {project.get('project_name', '项目')}</h1>
<p>总用例: {len(test_cases)} | 通过: {passed} | 失败: {failed} | 通过率: {pass_rate}%</p>
<h2>执行详情</h2>
<table border="1"><tr><th>ID</th><th>名称</th><th>状态</th><th>耗时</th></tr>
{''.join(rows)}
</table>
</body></html>"""
