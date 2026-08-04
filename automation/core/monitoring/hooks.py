# -*- coding: utf-8 -*-
"""事件钩子机制：支持Webhook、日志、IM通知等."""

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List

import requests


@dataclass
class EventHook:
    """单个钩子定义."""

    name: str
    event_filter: List[str]  # 监听的事件列表，如 ["node_started", "task_completed"]
    handler: Callable[[str, Dict], None]


class HookManager:
    """管理任务执行过程中的事件钩子."""

    def __init__(self):
        self.hooks: List[EventHook] = []

    def register(self, hook: EventHook):
        self.hooks.append(hook)

    def emit(self, event: str, data: Dict[str, Any]):
        for hook in self.hooks:
            if event in hook.event_filter or "*" in hook.event_filter:
                try:
                    hook.handler(event, data)
                except Exception as e:
                    print(f"Hook {hook.name} error: {e}")

    def register_webhook(self, url: str, events: List[str] = None):
        """注册 Webhook 钩子."""
        events = events or ["*"]

        def handler(event: str, data: Dict):
            payload = {"event": event, "data": data, "timestamp": __import__("datetime").datetime.now().isoformat()}
            requests.post(url, json=payload, timeout=10)

        self.register(EventHook(name=f"webhook:{url}", event_filter=events, handler=handler))

    def register_logger(self, logger_fn: Callable = None):
        """注册日志钩子."""
        def handler(event: str, data: Dict):
            fn = logger_fn or print
            fn(f"[EVENT] {event}: {json.dumps(data, ensure_ascii=False, default=str)}")

        self.register(EventHook(name="logger", event_filter=["*"], handler=handler))
