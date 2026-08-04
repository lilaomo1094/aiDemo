# -*- coding: utf-8 -*-
"""实时进度报告器."""

import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ProgressEvent:
    total: int = 0
    completed: int = 0
    failed: int = 0
    running: int = 0
    current_task: str = ""
    percentage: float = 0.0
    elapsed_seconds: float = 0.0
    message: str = ""
    milestone: str = ""
    milestone_progress: float = 0.0
    risks: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProgressReporter:
    """在终端或回调中实时报告工作流执行进度与风险."""

    def __init__(
        self,
        total_steps: int = 0,
        output: Optional[Any] = None,
        enable_terminal: bool = True,
        callback: Optional[Callable[[ProgressEvent], None]] = None,
    ):
        self.total_steps = total_steps
        self.output = output or sys.stdout
        self.enable_terminal = enable_terminal
        self.callback = callback
        self.start_time = time.time()
        self._last_line_length = 0

    def update(
        self,
        completed: int = 0,
        failed: int = 0,
        running: int = 0,
        current_task: str = "",
        message: str = "",
        milestone: str = "",
        milestone_progress: float = 0.0,
        risks: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        event = ProgressEvent(
            total=self.total_steps,
            completed=completed,
            failed=failed,
            running=running,
            current_task=current_task,
            percentage=(completed / self.total_steps * 100) if self.total_steps > 0 else 0.0,
            elapsed_seconds=time.time() - self.start_time,
            message=message,
            milestone=milestone,
            milestone_progress=milestone_progress,
            risks=risks or [],
            metadata=metadata or {},
        )
        if self.callback:
            try:
                self.callback(event)
            except Exception:
                pass
        if self.enable_terminal:
            self._print_progress(event)

    def _print_progress(self, event: ProgressEvent):
        bar_length = 30
        filled = int(bar_length * event.percentage / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        line = (
            f"\r🚀 智测执行中 [{bar}] "
            f"{event.percentage:5.1f}% | "
            f"{event.completed}/{event.total} | "
            f"运行:{event.running} 失败:{event.failed} | "
            f"当前: {event.current_task or '等待中'} | "
            f"已用 {event.elapsed_seconds:.1f}s"
        )
        if event.milestone:
            ms_bar_length = 15
            ms_filled = int(ms_bar_length * event.milestone_progress / 100)
            ms_bar = "█" * ms_filled + "░" * (ms_bar_length - ms_filled)
            line += f" | 里程碑 [{ms_bar}] {event.milestone_progress:4.1f}% {event.milestone}"
        if event.message:
            line += f" | {event.message}"
        # 清除上一行多余字符
        if self._last_line_length and self._last_line_length > len(line):
            line += " " * (self._last_line_length - len(line))
        self._last_line_length = len(line)
        self.output.write(line)
        self.output.flush()

        # 风险信息另起一行展示，避免覆盖进度条
        if event.risks and self.enable_terminal:
            critical = [r for r in event.risks if r.get("level") == "critical"]
            high = [r for r in event.risks if r.get("level") == "high"]
            if critical or high:
                risk_line = "⚠️  当前风险:"
                for r in critical + high[:2]:
                    risk_line += f" [{r.get('level').upper()}] {r.get('description')};"
                self.output.write(f"\n{risk_line}\n")
                self._last_line_length = 0

    def finish(self, status: str = "完成", message: str = ""):
        if self.enable_terminal:
            self.output.write("\n")
            self.output.flush()
        event = ProgressEvent(
            total=self.total_steps,
            completed=self.total_steps,
            percentage=100.0,
            elapsed_seconds=time.time() - self.start_time,
            current_task=status,
            message=message,
        )
        if self.callback:
            try:
                self.callback(event)
            except Exception:
                pass
