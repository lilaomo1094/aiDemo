# -*- coding: utf-8 -*-
"""IM Bot 服务：接收外部消息指令，调用任务调度器并推送结果.

支持命令：
- /run <config_path> [priority]   提交测试任务
- /status [task_id]               查询任务状态
- /list                           列出所有任务
- /cancel <task_id>               取消任务
- /help                           帮助信息
"""

import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from automation.core.scheduler import TaskScheduler

from .base import IMMessage
from .factory import create_im_provider


class IMBotService:
    """IM 机器人服务，桥接 IM 消息与任务调度器."""

    def __init__(self, scheduler: TaskScheduler, im_config: Dict[str, Any]):
        self.scheduler = scheduler
        self.im_config = im_config
        self.provider_type = im_config.get("provider", "lark")
        self.provider = create_im_provider(self.provider_type, im_config)
        self.default_config_path = im_config.get("default_config_path", "config/project_config.py")
        self.admin_users = set(im_config.get("admin_users", []))
        self._lock = threading.Lock()
        self._register_hooks()

    def _register_hooks(self):
        """注册任务完成/失败回调，向 IM 推送结果."""
        def im_notifier(event: str, data: Dict):
            if event not in ("task_completed", "task_failed"):
                return
            task = data.get("task", {})
            callback = task.get("callback_info", {})
            receiver = callback.get("im_receiver")
            if not receiver:
                return

            report_path = self._find_report_path(task)
            summary = self._format_task_summary(task)
            self.provider.send_text(receiver, summary)
            if report_path and Path(report_path).exists():
                self.provider.send_file(receiver, str(report_path))

        self.scheduler.hook_manager.register(
            type("EventHook", (), {
                "name": "im_notifier",
                "event_filter": ["task_completed", "task_failed"],
                "handler": im_notifier,
            })()
        )

    def _find_report_path(self, task: Dict) -> Optional[str]:
        tracker = task.get("tracker_data", {})
        nodes = tracker.get("nodes", {})
        report_node = nodes.get("report_generated", {})
        output = report_node.get("output_summary", "")
        # 简单匹配 report_path
        match = re.search(r'"report_path":\s*"([^"]+)"', output)
        if match:
            return match.group(1)
        result = task.get("result", {})
        return result.get("report_path")

    def _format_task_summary(self, task: Dict) -> str:
        status = task.get("status", "unknown")
        task_id = task.get("task_id", "")
        run_id = task.get("run_id", "")
        error = task.get("error_message", "")
        lines = [
            f"【测试任务通知】",
            f"任务ID: {task_id}",
            f"运行ID: {run_id}",
            f"状态: {status}",
        ]
        tracker = task.get("tracker_data", {})
        nodes = tracker.get("nodes", {})
        for node_id, node in nodes.items():
            if node.get("status") in ("passed", "blocked", "failed"):
                lines.append(f"- {node.get('name', node_id)}: {node.get('status')}")
        if error:
            lines.append(f"错误: {error}")
        return "\n".join(lines)

    def handle_message(self, message: IMMessage) -> str:
        """处理单条 IM 消息，返回回复文本."""
        if not message.is_command():
            return "未识别为指令，发送 /help 查看可用命令。"

        command = message.get_command()
        args = self._parse_args(message.content)

        if command in ("run", "执行测试"):
            return self._cmd_run(message, args)
        elif command == "status":
            return self._cmd_status(args)
        elif command == "list":
            return self._cmd_list()
        elif command == "cancel":
            return self._cmd_cancel(message, args)
        elif command == "help":
            return self._cmd_help()
        else:
            return f"未知命令: {command}，发送 /help 查看帮助。"

    def _parse_args(self, content: str) -> List[str]:
        text = content.strip()
        if text.startswith("/"):
            text = text[1:]
        # 去掉中文指令前缀
        for prefix in ["执行测试", "运行测试"]:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
        parts = text.split()
        # 第一个词是命令本身，仅保留后续参数
        return parts[1:] if parts else []

    def _cmd_run(self, message: IMMessage, args: List[str]) -> str:
        if self.admin_users and message.sender_id not in self.admin_users:
            return "您没有权限提交测试任务。"

        config_path = args[0] if args else self.default_config_path
        priority = 5
        if len(args) >= 2:
            try:
                priority = int(args[1])
            except ValueError:
                pass

        if not Path(config_path).exists():
            return f"配置文件不存在: {config_path}"

        callback_info = {
            "im_channel": self.provider_type,
            "im_receiver": message.sender_id,
        }
        task_id = self.scheduler.submit(config_path, priority=priority, callback_info=callback_info)
        return f"已提交测试任务\n任务ID: {task_id}\n配置: {config_path}\n优先级: {priority}"

    def _cmd_status(self, args: List[str]) -> str:
        if not args:
            tasks = self.scheduler.list_tasks()
            if not tasks:
                return "当前没有任务。"
            lines = ["任务状态列表:"]
            for task in tasks[-10:]:
                lines.append(f"- {task.task_id}: {task.status.value} (优先级 {task.priority})")
            return "\n".join(lines)

        task_id = args[0]
        task = self.scheduler.get_task(task_id)
        if not task:
            return f"未找到任务: {task_id}"
        return self._format_task_summary(task.to_dict())

    def _cmd_list(self) -> str:
        return self._cmd_status([])

    def _cmd_cancel(self, message: IMMessage, args: List[str]) -> str:
        if self.admin_users and message.sender_id not in self.admin_users:
            return "您没有权限取消任务。"
        if not args:
            return "用法: /cancel <task_id>"
        task_id = args[0]
        if self.scheduler.cancel_task(task_id):
            return f"已取消任务: {task_id}"
        return f"取消失败，任务不存在或已不在队列中: {task_id}"

    def _cmd_help(self) -> str:
        return (
            "可用命令:\n"
            "/run <config_path> [priority] - 提交测试任务\n"
            "/status [task_id]             - 查询任务状态\n"
            "/list                         - 列出所有任务\n"
            "/cancel <task_id>             - 取消任务\n"
            "/help                         - 帮助"
        )

    def handle_webhook_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理 IM Webhook 回调 payload."""
        message = self.provider.parse_webhook_payload(payload)
        reply = self.handle_message(message)
        if message.sender_id:
            self.provider.send_text(message.sender_id, reply)
        return {"message": reply, "command": message.get_command()}
