# -*- coding: utf-8 -*-
"""Web 报告仪表板生成器.

提供：
- 聚合调度器任务状态、里程碑、风险
- 读取版本清单与资产
- 生成静态 HTML 报告
- 启动轻量 HTTP 服务预览
"""

import json
import os
import threading
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, List, Optional


class DashboardGenerator:
    """基于本地状态文件生成智测 Web 仪表板."""

    def __init__(
        self,
        state_dir: str = "output/scheduler",
        version_manifest: str = "versions/manifest.json",
        output_dir: str = "output/dashboard",
    ):
        self.state_dir = Path(state_dir)
        self.version_manifest = Path(version_manifest)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self) -> Path:
        """生成 HTML 报告并返回路径."""
        tasks = self._load_tasks()
        versions = self._load_versions()
        summary = self._build_summary(tasks)
        html = self._render_html(tasks, versions, summary)
        index_path = self.output_dir / "index.html"
        index_path.write_text(html, encoding="utf-8")
        return index_path

    def _load_tasks(self) -> List[Dict[str, Any]]:
        tasks = []
        if not self.state_dir.exists():
            return tasks
        for path in sorted(self.state_dir.glob("TASK-*.json"), reverse=True):
            try:
                tasks.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        return tasks

    def _load_versions(self) -> List[Dict[str, Any]]:
        if not self.version_manifest.exists():
            return []
        try:
            manifest = json.loads(self.version_manifest.read_text(encoding="utf-8"))
            return manifest.get("versions", [])
        except Exception:
            return []

    def _build_summary(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(tasks)
        by_status: Dict[str, int] = {}
        for t in tasks:
            by_status[t.get("status", "unknown")] = by_status.get(t.get("status", "unknown"), 0) + 1
        return {
            "total": total,
            "completed": by_status.get("completed", 0),
            "failed": by_status.get("failed", 0),
            "blocked": by_status.get("blocked", 0),
            "running": by_status.get("running", 0),
            "queued": by_status.get("queued", 0),
            "cancelled": by_status.get("cancelled", 0),
        }

    def _render_html(
        self, tasks: List[Dict[str, Any]], versions: List[Dict[str, Any]], summary: Dict[str, Any]
    ) -> str:
        title = "智测自动化测试仪表板"
        generated_at = datetime.now().isoformat()

        rows = []
        for t in tasks[:50]:
            tracker = t.get("tracker_data", {}) or {}
            nodes = tracker.get("nodes", {})
            milestones = ", ".join(
                name for name, node in nodes.items() if node.get("status") == "passed"
            )[:80]
            rows.append(
                "<tr>"
                f"<td>{t.get('task_id', '')}</td>"
                f"<td><span class='status {t.get('status', '')}'>{t.get('status', '')}</span></td>"
                f"<td>{t.get('priority', '')}</td>"
                f"<td>{t.get('config_path', '')}</td>"
                f"<td>{t.get('started_at', '') or '-'}</td>"
                f"<td>{t.get('completed_at', '') or '-'}</td>"
                f"<td>{t.get('error_message', '') or '-'}</td>"
                f"<td title='{milestones}'>{milestones or '-'}...</td>"
                "</tr>"
            )

        version_rows = []
        for v in versions:
            version_rows.append(
                "<tr>"
                f"<td>{v.get('version', '')}</td>"
                f"<td>{v.get('status', '')}</td>"
                f"<td>{v.get('created_at', '')}</td>"
                f"<td>{v.get('description', '') or '-'}</td>"
                "</tr>"
            )

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ --bg: #f5f7fa; --card: #fff; --text: #1f2937; --muted: #6b7280; --primary: #2563eb; --success: #16a34a; --danger: #dc2626; --warning: #d97706; }}
body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background: var(--bg); color: var(--text); }}
header {{ background: var(--card); border-bottom: 1px solid #e5e7eb; padding: 1.5rem 2rem; display: flex; justify-content: space-between; align-items: center; }}
h1 {{ margin: 0; font-size: 1.5rem; }}
.generated {{ color: var(--muted); font-size: 0.875rem; }}
.container {{ padding: 2rem; max-width: 1400px; margin: 0 auto; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
.card {{ background: var(--card); border-radius: 0.75rem; padding: 1.25rem; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
.card .label {{ color: var(--muted); font-size: 0.875rem; }}
.card .value {{ font-size: 1.75rem; font-weight: 700; margin-top: 0.25rem; }}
.section {{ background: var(--card); border-radius: 0.75rem; padding: 1.25rem; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
.section h2 {{ margin-top: 0; font-size: 1.125rem; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; }}
th, td {{ text-align: left; padding: 0.625rem; border-bottom: 1px solid #f3f4f6; }}
th {{ color: var(--muted); font-weight: 600; }}
tr:hover {{ background: #f9fafb; }}
.status {{ display: inline-block; padding: 0.125rem 0.5rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }}
.status.completed {{ background: #dcfce7; color: var(--success); }}
.status.failed {{ background: #fee2e2; color: var(--danger); }}
.status.blocked {{ background: #fef3c7; color: var(--warning); }}
.status.running {{ background: #dbeafe; color: var(--primary); }}
.status.queued, .status.pending {{ background: #f3f4f6; color: var(--muted); }}
.status.cancelled {{ background: #e5e7eb; color: #374151; }}
.empty {{ color: var(--muted); padding: 2rem; text-align: center; }}
</style>
</head>
<body>
<header>
<h1>智测自动化测试仪表板</h1>
<span class="generated">生成时间: {generated_at}</span>
</header>
<div class="container">
  <div class="cards">
    <div class="card"><div class="label">总任务</div><div class="value">{summary['total']}</div></div>
    <div class="card"><div class="label">已完成</div><div class="value" style="color:var(--success)">{summary['completed']}</div></div>
    <div class="card"><div class="label">失败</div><div class="value" style="color:var(--danger)">{summary['failed']}</div></div>
    <div class="card"><div class="label">阻塞</div><div class="value" style="color:var(--warning)">{summary['blocked']}</div></div>
    <div class="card"><div class="label">运行中</div><div class="value" style="color:var(--primary)">{summary['running']}</div></div>
    <div class="card"><div class="label">队列中</div><div class="value">{summary['queued']}</div></div>
  </div>

  <div class="section">
    <h2>最近任务</h2>
    <table>
      <thead>
        <tr><th>任务 ID</th><th>状态</th><th>优先级</th><th>配置</th><th>开始时间</th><th>完成时间</th><th>错误信息</th><th>里程碑</th></tr>
      </thead>
      <tbody>
        {''.join(rows) if rows else '<tr><td colspan="8" class="empty">暂无任务</td></tr>'}
      </tbody>
    </table>
  </div>

  <div class="section">
    <h2>版本资产</h2>
    <table>
      <thead>
        <tr><th>版本</th><th>状态</th><th>创建时间</th><th>描述</th></tr>
      </thead>
      <tbody>
        {''.join(version_rows) if version_rows else '<tr><td colspan="4" class="empty">暂无版本</td></tr>'}
      </tbody>
    </table>
  </div>
</div>
</body>
</html>"""

    def serve(self, port: int = 8080, bind: str = "127.0.0.1") -> threading.Thread:
        """启动轻量 HTTP 服务预览报告，返回服务线程."""
        self.generate()
        os.chdir(self.output_dir)
        server = HTTPServer((bind, port), SimpleHTTPRequestHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return thread


def main():
    import argparse

    parser = argparse.ArgumentParser(description="智测 Web 仪表板")
    parser.add_argument("--generate", action="store_true", help="生成静态报告")
    parser.add_argument("--serve", action="store_true", help="启动 HTTP 服务")
    parser.add_argument("--port", type=int, default=8080, help="HTTP 端口")
    parser.add_argument("--state-dir", default="output/scheduler", help="任务状态目录")
    parser.add_argument("--output-dir", default="output/dashboard", help="报告输出目录")
    args = parser.parse_args()

    dashboard = DashboardGenerator(state_dir=args.state_dir, output_dir=args.output_dir)
    if args.serve:
        dashboard.serve(port=args.port)
        print(f"仪表板已启动: http://127.0.0.1:{args.port}/")
        try:
            while True:
                pass
        except KeyboardInterrupt:
            print("\n关闭服务")
    else:
        path = dashboard.generate()
        print(f"仪表板已生成: {path}")


if __name__ == "__main__":
    main()
