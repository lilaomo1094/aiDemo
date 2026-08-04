# -*- coding: utf-8 -*-
"""IM Bot 服务：接收外部消息指令，调用任务调度器并推送结果.

支持命令：
- /run <config_path|项目别名> [priority] [--env env]   提交测试任务
- /status [task_id]                                    查询任务状态
- /list                                                列出所有任务
- /cancel <task_id>                                    取消任务
- /help                                                帮助信息

也支持自然语言：
- "测试一下电商项目，优先级3"
- "跑一下登录模块的功能测试"
- "帮我执行 config/ecommerce.py"
"""

import re
import shlex
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from automation.core.scheduler import TaskScheduler
from automation.core.voice import create_asr_provider

from .base import IMMessage
from .factory import create_im_provider


@dataclass
class _EventHook:
    name: str
    event_filter: List[str] = field(default_factory=list)
    handler: Callable = field(default=lambda *args, **kwargs: None)


class IntentParser:
    """轻量自然语言意图解析器."""

    RUN_KEYWORDS = ["测试", "跑", "执行", "运行", "测一下", "跑一下", "执行一下", "运行一下"]
    STATUS_KEYWORDS = ["状态", "进度", "怎么样了", "查一下"]
    CANCEL_KEYWORDS = ["取消", "停止", "终止"]
    LIST_KEYWORDS = ["列表", "所有任务", "任务列表"]
    HELP_KEYWORDS = ["帮助", "怎么用", "help"]

    def __init__(self, project_aliases: Dict[str, str], default_config_path: str):
        self.project_aliases = project_aliases
        self.default_config_path = default_config_path

    def parse(self, content: str) -> Tuple[str, Dict[str, Any]]:
        """解析消息，返回 (intent, params)."""
        text = content.strip()

        # 1. 优先处理 / 命令
        if text.startswith("/"):
            return self._parse_slash(text)

        # 2. 自然语言意图识别
        if any(kw in text for kw in self.RUN_KEYWORDS):
            return "run", self._extract_run_params(text)
        if any(kw in text for kw in self.STATUS_KEYWORDS):
            task_id = self._extract_task_id(text)
            return "status", {"task_id": task_id}
        if any(kw in text for kw in self.CANCEL_KEYWORDS):
            task_id = self._extract_task_id(text)
            return "cancel", {"task_id": task_id}
        if any(kw in text for kw in self.LIST_KEYWORDS):
            return "list", {}
        if any(kw in text for kw in self.HELP_KEYWORDS):
            return "help", {}

        return "unknown", {}

    def _parse_slash(self, text: str) -> Tuple[str, Dict[str, Any]]:
        text = text[1:].strip()
        try:
            parts = shlex.split(text)
        except ValueError:
            parts = text.split()
        if not parts:
            return "help", {}

        command = parts[0].lower()
        args = parts[1:]

        if command in ("run", "执行测试"):
            return "run", self._parse_run_args(args)
        if command == "status":
            return "status", {"task_id": args[0] if args else None}
        if command == "list":
            return "list", {}
        if command == "cancel":
            return "cancel", {"task_id": args[0] if args else None}
        if command == "help":
            return "help", {}

        return "unknown", {"command": command}

    def _parse_run_args(self, args: List[str]) -> Dict[str, Any]:
        params = {"target": None, "priority": 5, "env": None}
        if args:
            params["target"] = args[0]
        i = 1
        while i < len(args):
            arg = args[i]
            if arg in ("--priority", "-p"):
                i += 1
                if i < len(args):
                    try:
                        params["priority"] = int(args[i])
                    except ValueError:
                        pass
            elif arg in ("--env", "-e"):
                i += 1
                if i < len(args):
                    params["env"] = args[i]
            elif arg.isdigit() and params["priority"] == 5:
                params["priority"] = int(arg)
            i += 1
        return params

    def _extract_run_params(self, text: str) -> Dict[str, Any]:
        params = {"target": None, "priority": 5, "env": None}

        # 优先级
        priority_match = re.search(r"优先级\s*(\d+)", text)
        if not priority_match:
            priority_match = re.search(r"priority\s*(\d+)", text, re.IGNORECASE)
        if priority_match:
            params["priority"] = int(priority_match.group(1))

        # 环境
        env_match = re.search(r"环境\s*([a-zA-Z0-9_\-]+)", text)
        if not env_match:
            env_match = re.search(r"--env\s+([a-zA-Z0-9_\-]+)", text)
        if env_match:
            params["env"] = env_match.group(1)

        # 目标：项目别名 或 配置文件路径
        target = self._extract_target(text)
        params["target"] = target
        return params

    def _extract_target(self, text: str) -> Optional[str]:
        # 直接包含 config/ 或 .py 的路径
        path_match = re.search(r"[\w\-/]+\.py", text)
        if path_match:
            return path_match.group(0)

        # 项目别名匹配（取最长匹配）
        matched_alias = None
        for alias in sorted(self.project_aliases.keys(), key=len, reverse=True):
            if alias in text:
                matched_alias = alias
                break
        if matched_alias:
            return self.project_aliases[matched_alias]

        return self.default_config_path

    def _extract_task_id(self, text: str) -> Optional[str]:
        match = re.search(r"TASK-[a-f0-9]+", text, re.IGNORECASE)
        return match.group(0) if match else None


class IMBotService:
    """IM 机器人服务，桥接 IM 消息与任务调度器."""

    def __init__(self, scheduler: TaskScheduler, im_config):
        self.scheduler = scheduler
        # 兼容 Pydantic 模型与字典配置
        if hasattr(im_config, "model_dump"):
            self.im_config = im_config.model_dump()
        else:
            self.im_config = dict(im_config)
        self.provider_type = self.im_config.get("provider", "lark")
        self.provider = create_im_provider(self.provider_type, self.im_config)
        self.default_config_path = self.im_config.get("default_config_path", "config/project_config.py")
        self.project_aliases = self.im_config.get("project_aliases", {})
        self.admin_users = set(self.im_config.get("admin_users", []))
        self.intent_parser = IntentParser(self.project_aliases, self.default_config_path)
        self._lock = threading.Lock()

        # 语音识别（可选）
        voice_config = self.im_config.get("voice") or {}
        self.asr = create_asr_provider(voice_config) if voice_config.get("enabled") else None

        # Function Calling 智能编排（可选）
        self.function_calling_enabled = self.im_config.get("function_calling", False)

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
            _EventHook(
                name="im_notifier",
                event_filter=["task_completed", "task_failed"],
                handler=im_notifier,
            )
        )

    def _find_report_path(self, task: Dict) -> Optional[str]:
        tracker = task.get("tracker_data", {})
        nodes = tracker.get("nodes", {})
        report_node = nodes.get("report_generated", {})
        output = report_node.get("output_summary", "")
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
        """处理单条 IM 消息，返回回复文本.

        支持语音消息：先通过 ASR 转文本，再进行意图解析或 Function Calling 编排。
        """
        # 1. 语音消息转文本
        if message.message_type == "voice" and message.audio_url and self.asr:
            transcribed = self._transcribe_audio(message.audio_url)
            if not transcribed:
                return "语音消息识别失败，请重试或发送文字。"
            message.content = transcribed

        # 2. Function Calling 智能编排（处理自然语言复杂指令）
        if self.function_calling_enabled and not message.content.strip().startswith("/"):
            return self._cmd_orchestrate(message)

        # 3. 原有意图解析流程
        intent, params = self.intent_parser.parse(message.content)

        if intent == "run":
            return self._cmd_run(message, params)
        elif intent == "status":
            return self._cmd_status(params.get("task_id"))
        elif intent == "list":
            return self._cmd_list()
        elif intent == "cancel":
            return self._cmd_cancel(message, params.get("task_id"))
        elif intent == "help":
            return self._cmd_help()
        elif intent == "unknown":
            if message.content.strip().startswith("/"):
                return f"未知命令: {params.get('command', '')}，发送 /help 查看帮助。"
            return "未识别为指令，发送 /help 查看可用命令。"
        else:
            return "未识别为指令，发送 /help 查看可用命令。"

    def _transcribe_audio(self, audio_url: str) -> str:
        """下载音频并通过 ASR 识别为文本."""
        import tempfile

        import requests

        try:
            resp = requests.get(audio_url, timeout=60)
            resp.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp.write(resp.content)
                tmp_path = tmp.name
            result = self.asr.transcribe(tmp_path)
            Path(tmp_path).unlink(missing_ok=True)
            return result.text
        except Exception as e:
            print(f"语音转文字失败: {e}")
            return ""

    def _cmd_orchestrate(self, message: IMMessage) -> str:
        """使用 Function Calling 编排器处理自然语言指令."""
        from automation.agents.orchestrator import FunctionCallingOrchestrator
        from automation.core.config import load_config
        from automation.workflow.engine import WorkflowTask

        config = load_config(self.default_config_path)
        orchestrator = FunctionCallingOrchestrator(config)
        task = WorkflowTask(
            task_id="fc-im",
            agent_type=None,
            name="智能编排",
            description=message.content,
            input_data={"instruction": message.content},
        )
        result = orchestrator.execute(task, None)
        return result.get("final_answer") or f"已执行 {len(result.get('tool_results', []))} 个工具调用"

    def _resolve_config_path(self, target: Optional[str]) -> str:
        if not target:
            return self.default_config_path
        if Path(target).exists():
            return target
        if target in self.project_aliases:
            return self.project_aliases[target]
        alias_path = self.project_aliases.get(target)
        if alias_path and Path(alias_path).exists():
            return alias_path
        return self.default_config_path

    def _cmd_run(self, message: IMMessage, params: Dict[str, Any]) -> str:
        if self.admin_users and message.sender_id not in self.admin_users:
            return "您没有权限提交测试任务。"

        target = params.get("target")
        config_path = self._resolve_config_path(target)
        priority = params.get("priority", 5)
        env = params.get("env")

        if not Path(config_path).exists():
            return f"配置文件不存在: {config_path}"

        callback_info = {
            "im_channel": self.provider_type,
            "im_receiver": message.sender_id,
        }
        task_id = self.scheduler.submit(config_path, priority=priority, callback_info=callback_info)
        reply = f"已提交测试任务\n任务ID: {task_id}\n配置: {config_path}\n优先级: {priority}"
        if env:
            reply += f"\n环境: {env}"
        return reply

    def _cmd_status(self, task_id: Optional[str]) -> str:
        if not task_id:
            tasks = self.scheduler.list_tasks()
            if not tasks:
                return "当前没有任务。"
            lines = ["任务状态列表:"]
            for task in tasks[-10:]:
                lines.append(f"- {task.task_id}: {task.status.value} (优先级 {task.priority})")
            return "\n".join(lines)

        task = self.scheduler.get_task(task_id)
        if not task:
            return f"未找到任务: {task_id}"
        return self._format_task_summary(task.to_dict())

    def _cmd_list(self) -> str:
        return self._cmd_status(None)

    def _cmd_cancel(self, message: IMMessage, task_id: Optional[str]) -> str:
        if self.admin_users and message.sender_id not in self.admin_users:
            return "您没有权限取消任务。"
        if not task_id:
            return "用法: /cancel <task_id>"
        if self.scheduler.cancel_task(task_id):
            return f"已取消任务: {task_id}"
        return f"取消失败，任务不存在或已不在队列中: {task_id}"

    def _cmd_help(self) -> str:
        aliases = "\n".join(f"  {k}: {v}" for k, v in self.project_aliases.items()) or "  （暂无）"
        return (
            "可用命令:\n"
            "/run <项目别名|配置路径> [priority] [--env env]\n"
            "/status [task_id]             - 查询任务状态\n"
            "/list                         - 列出所有任务\n"
            "/cancel <task_id>             - 取消任务\n"
            "/help                         - 帮助\n\n"
            "也支持自然语言，例如:\n"
            "  测试一下电商项目，优先级3\n"
            "  跑一下登录模块\n\n"
            "已配置的项目别名:\n" + aliases
        )

    def handle_webhook_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理 IM Webhook 回调 payload."""
        message = self.provider.parse_webhook_payload(payload)
        reply = self.handle_message(message)
        if message.sender_id:
            self.provider.send_text(message.sender_id, reply)
        return {"message": reply, "intent": "run" if "已提交测试任务" in reply else "other"}
