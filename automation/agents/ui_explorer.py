# -*- coding: utf-8 -*-
"""UI 探索 Agent：将探索式 UI 测试能力暴露为 Function Calling 工具.

作为工作流中的一个独立 Agent，接收自然语言测试指令，驱动
ExploratoryUIExecutor 执行 AI 探索式 UI 测试。

可以被 Orchestrator 通过 function calling 调用，实现
"explore_ui" 工具，让用户直接用自然语言发起 UI 探索测试。
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from automation.core.executor.exploratory_ui_executor import (
    ExploratoryConfig,
    ExploratoryUIExecutor,
)

from .base import BaseAgent

logger = logging.getLogger(__name__)


class UIExplorerAgent(BaseAgent):
    """UI 探索 Agent.

    接收自然语言测试指令，动态探索 UI 页面并返回结果。

    可被 Orchestrator 的 function calling 机制调用：
    - Tool name: explore_ui
    - 输入: goal, start_url, max_steps, etc.
    - 输出: 探索结果（步骤记录、截图、错误等）
    """

    def execute(self, task, context) -> Dict[str, Any]:
        """执行 UI 探索任务.

        task.input_data 应包含:
            - goal (str): 测试目标描述
            - start_url (str): 起始页面 URL
            - max_steps (int): 最大探索步数
            - expected_outcome (str): 预期结果
            - test_id (str): 测试 ID
        """
        input_data = task.input_data if hasattr(task, "input_data") else (task or {})

        goal = input_data.get("goal", input_data.get("description", ""))
        if not goal:
            return {
                "status": "error",
                "message": "缺少测试目标 (goal)",
                "exploration": None,
            }

        start_url = input_data.get("start_url", input_data.get("url", ""))
        max_steps = input_data.get("max_steps", 20)
        expected_outcome = input_data.get("expected_outcome", "")
        test_id = input_data.get("test_id", f"EXP-{datetime.now().strftime('%Y%m%d%H%M%S')}")

        # 创建探索式执行器
        try:
            executor = ExploratoryUIExecutor(self.config)
        except Exception as e:
            return {
                "status": "error",
                "message": f"初始化探索执行器失败: {e}",
            }

        # 执行
        try:
            test_case = {
                "id": test_id,
                "type": "exploratory_ui",
                "goal": goal,
                "start_url": start_url,
                "max_steps": max_steps,
                "expected_outcome": expected_outcome,
            }

            result = executor.execute(test_case, context)

            return {
                "status": result.status.value,
                "goal": goal,
                "message": result.message,
                "test_id": test_id,
                "exploration": {
                    "total_steps": result.details.get("total_steps", 0),
                    "duration": result.details.get("duration", 0),
                    "goal_achieved": result.details.get("goal_achieved", False),
                    "errors": result.details.get("errors", []),
                    "conclusion": result.details.get("conclusion", ""),
                    "steps": self._summarize_steps(result.steps),
                },
                "screenshots": result.screenshots,
                "console_logs": result.console_logs,
            }

        except Exception as e:
            logger.exception(f"UI 探索执行异常: {e}")
            return {
                "status": "error",
                "message": f"探索执行失败: {e}",
                "test_id": test_id,
            }

    def _summarize_steps(self, steps: List[Dict]) -> List[Dict]:
        """压缩步骤记录，移除大字段."""
        summary = []
        for s in (steps or []):
            summary.append({
                "step": s.get("step", "?"),
                "action": s.get("action", "?"),
                "selector": (s.get("selector", "") or "")[:80],
                "value": s.get("value", ""),
                "success": s.get("success", True),
                "reasoning": (s.get("reasoning", "") or "")[:120],
            })
        return summary


# ──────────────── Function Calling 工具定义 ────────────────

EXPLORE_UI_TOOL = {
    "name": "explore_ui",
    "description": (
        "对 Web UI 页面进行 AI 驱动的探索式测试。"
        "你只需描述测试目标（如'测试登录功能是否正常'），"
        "Agent 会自动打开页面、分析元素、执行操作并报告结果。"
        "适用于：功能验证、回归测试、冒烟测试、UI 可用性检查。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "goal": {
                "type": "string",
                "description": "测试目标，用自然语言描述要测试什么功能，例如："
                "'使用 admin/admin123 登录，验证能否进入管理后台首页'",
            },
            "start_url": {
                "type": "string",
                "description": "起始页面 URL，如 https://example.com/login",
            },
            "max_steps": {
                "type": "integer",
                "description": "最大探索步数，默认 20",
                "default": 20,
            },
            "expected_outcome": {
                "type": "string",
                "description": "期望的测试结果，例如：'跳转到首页，显示欢迎信息'",
            },
        },
        "required": ["goal"],
    },
}
