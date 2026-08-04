# -*- coding: utf-8 -*-
"""探索式 UI 执行器：AI 驱动的动态 UI 测试。

与传统 UI 执行器（按预定义步骤执行）不同，探索式执行器采用
"感知 → 决策 → 执行 → 观察" 的循环模式：

1. 提取页面状态 (PageAnalyzer)
2. LLM 决策下一步操作 (VisionLLM)
3. 执行操作 (Playwright)
4. 观察变化、检测异常 (PageAnalyzer.diff)
5. 重复直到目标达成

核心能力：
- 自然语言驱动：用户只需描述测试目标（如"测试登录功能"）
- 动态适应：根据页面实际状态调整操作策略
- 异常捕获：自动检测错误信息、弹窗干扰
- 自愈选择器：选择器失效时自动修复
- 操作追溯：完整记录每一步的决策和结果
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from automation.core.config import ToolConfig
from automation.core.executor.base import TestExecutor, TestResult, TestStatus
from automation.core.llm.vision_provider import VisionLLM, create_vision_llm
from automation.core.llm import create_llm_provider

from .page_analyzer import PageAnalyzer, PageState
from .selector_healer import HealedSelector, SelectorHealer

logger = logging.getLogger(__name__)


# ──────────────── 探索配置 ────────────────

class ExploratoryConfig:
    """探索式 UI 测试配置."""

    def __init__(
        self,
        max_steps: int = 30,
        step_timeout: int = 15,  # 每步操作超时 (秒)
        screenshot_on_step: bool = True,
        screenshot_on_error: bool = True,
        enable_vision: bool = True,
        enable_self_healing: bool = True,
        enable_console_logging: bool = True,
        max_page_elements: int = 60,
        goal_check_interval: int = 3,  # 每N步做一次目标达成的检查
        actions_before_scroll: int = 8,  # 积累多少失败操作后尝试滚动
        navigation_timeout: int = 30000,  # 导航超时 (ms)
        operation_delay: int = 500,  # 操作间最小延迟 (ms)
    ):
        self.max_steps = max_steps
        self.step_timeout = step_timeout
        self.screenshot_on_step = screenshot_on_step
        self.screenshot_on_error = screenshot_on_error
        self.enable_vision = enable_vision
        self.enable_self_healing = enable_self_healing
        self.enable_console_logging = enable_console_logging
        self.max_page_elements = max_page_elements
        self.goal_check_interval = goal_check_interval
        self.actions_before_scroll = actions_before_scroll
        self.navigation_timeout = navigation_timeout
        self.operation_delay = operation_delay


# ──────────────── 探索式执行器 ────────────────

class ExploratoryUIExecutor(TestExecutor):
    """AI 驱动的探索式 UI 执行器.

    用法:
        config = ToolConfig(...)
        executor = ExploratoryUIExecutor(config)
        result = executor.execute({
            "id": "EXP-001",
            "type": "exploratory_ui",
            "goal": "测试登录功能：使用admin/admin123登录，验证是否能进入首页",
            "start_url": "https://example.com/login",
            "max_steps": 20,
        })
    """

    def __init__(self, config: ToolConfig):
        super().__init__(config)
        self._explorer_config = self._build_explorer_config()
        self._analyzer = PageAnalyzer(max_elements_per_page=self._explorer_config.max_page_elements)
        self._healer = SelectorHealer()
        self._vision_llm: Optional[VisionLLM] = None
        self._browser_page: Optional[Page] = None
        self._console_logs: List[Dict] = []
        self._network_errors: List[Dict] = []

    def _build_explorer_config(self) -> ExploratoryConfig:
        """从 ToolConfig 构建探索配置（兼容现有配置结构）."""
        ui = getattr(self.config, "ui", None)
        explorer = getattr(self.config, "exploratory", None)

        return ExploratoryConfig(
            max_steps=getattr(explorer, "max_steps", None) or getattr(ui, "max_steps", None) or 30,
            step_timeout=getattr(explorer, "step_timeout", None) or getattr(ui, "step_timeout", None) or 15,
            screenshot_on_step=getattr(explorer, "screenshot_on_step", True),
            enable_vision=getattr(explorer, "enable_vision", True),
            enable_self_healing=getattr(explorer, "enable_self_healing", True),
        )

    def _init_vision(self):
        """初始化 Vision LLM."""
        if self._vision_llm is not None:
            return
        try:
            if self.config.llm and self.config.llm.api_key:
                provider = create_llm_provider(self.config.llm)
                self._vision_llm = create_vision_llm(provider)
        except Exception as e:
            logger.warning(f"Vision LLM 初始化失败: {e}，将使用纯文本模式")

    def execute(self, test_case: Dict, context=None) -> TestResult:
        """执行探索式 UI 测试.

        test_case 必须包含:
            - goal (str): 自然语言测试目标
            可选:
            - start_url (str): 起始 URL
            - max_steps (int): 最大探索步数
            - expected_outcome (str): 预期结果描述
            - preconditions (list): 前置条件（如登录 cookie）
        """
        goal = test_case.get("goal", test_case.get("description", ""))
        if not goal:
            return TestResult(
                status=TestStatus.ERROR,
                message="缺少测试目标 (goal/description)",
                details={"test_id": test_case.get("id", "UNKNOWN")},
            )

        self._init_vision()

        max_steps = test_case.get("max_steps", self._explorer_config.max_steps)
        start_url = test_case.get("start_url", "")
        expected_outcome = test_case.get("expected_outcome", "")

        # 执行探索
        explore_result = self._explore(
            goal=goal,
            start_url=start_url,
            max_steps=max_steps,
            expected_outcome=expected_outcome,
            context=context,
        )

        # 转换为 TestResult
        status = TestStatus.PASSED if explore_result.get("goal_achieved") else TestStatus.FAILED
        if explore_result.get("blocked"):
            status = TestStatus.BLOCKED

        return TestResult(
            status=status,
            message=explore_result.get("conclusion", ""),
            steps=explore_result.get("steps", []),
            screenshots=explore_result.get("screenshots", []),
            console_logs=self._console_logs,
            details={
                "test_id": test_case.get("id", "UNKNOWN"),
                "goal": goal,
                "total_steps": explore_result.get("total_steps", 0),
                "duration": explore_result.get("duration", 0),
                "goal_achieved": explore_result.get("goal_achieved", False),
                "errors": explore_result.get("errors", []),
                "conclusion": explore_result.get("conclusion", ""),
            },
        )

    def _explore(
        self,
        goal: str,
        start_url: str = "",
        max_steps: int = 30,
        expected_outcome: str = "",
        context=None,
    ) -> Dict[str, Any]:
        """核心探索循环."""
        start_time = time.time()
        steps: List[Dict] = []
        screenshots: List[str] = []
        errors: List[str] = []
        consecutive_failures = 0
        goal_achieved = False
        conclusion = ""
        blocked = False

        try:
            from automation.core.network import NetworkManager

            network = NetworkManager(self.config)
            page = self._get_or_create_page(network)

            # 导航到起始 URL
            if start_url:
                try:
                    page.goto(start_url, timeout=self._explorer_config.navigation_timeout)
                    page.wait_for_load_state("domcontentloaded")
                except (PlaywrightError, PlaywrightTimeout) as e:
                    errors.append(f"导航到 {start_url} 失败: {e}")
                    blocked = True
                    return self._build_result(
                        goal, steps, screenshots, errors,
                        goal_achieved=False, blocked=True,
                        conclusion=f"无法访问目标页面: {e}",
                        start_time=start_time,
                    )

            # 收集控制台日志
            if self._explorer_config.enable_console_logging:
                self._setup_console_logging(page)

            # ─── 探索主循环 ───
            for step_num in range(1, max_steps + 1):
                step_record = {"step": step_num, "timestamp": datetime.now().isoformat()}

                # 1. 分析页面状态
                try:
                    page_state = self._analyzer.analyze(
                        page,
                        take_screenshot=self._explorer_config.screenshot_on_step,
                    )
                    step_record["page_title"] = page_state.title
                    step_record["page_url"] = page_state.url
                except Exception as e:
                    errors.append(f"步骤 {step_num}: 页面分析失败: {e}")
                    consecutive_failures += 1
                    continue

                # 截图
                if page_state.screenshot_base64:
                    screenshots.append(page_state.screenshot_base64)

                # 2. LLM 决策
                try:
                    decision = self._decide_action(
                        goal=goal,
                        page_state=page_state,
                        history=steps,
                        expected_outcome=expected_outcome,
                        step_num=step_num,
                        max_steps=max_steps,
                    )
                except Exception as e:
                    decision = {
                        "action": "done",
                        "reasoning": f"决策失败: {e}",
                        "done": True,
                    }

                step_record["action"] = decision.get("action", "unknown")
                step_record["selector"] = decision.get("selector", "")
                step_record["value"] = decision.get("value", "")
                step_record["reasoning"] = decision.get("reasoning", "")

                # 检查是否完成
                if decision.get("done"):
                    goal_achieved = True
                    conclusion = decision.get("reasoning", "目标已达成")
                    steps.append(step_record)
                    break

                # 3. 执行操作
                try:
                    before_state = page_state
                    exec_result = self._execute_action(page, decision)
                    step_record.update(exec_result)
                except (PlaywrightError, PlaywrightTimeout, Exception) as e:
                    step_record["success"] = False
                    step_record["error"] = str(e)[:300]
                    consecutive_failures += 1

                    # 自愈尝试
                    if self._explorer_config.enable_self_healing and step_num > 1:
                        healed = self._try_heal_selector(
                            page, decision, page_state, before_state
                        )
                        if healed:
                            step_record["healed"] = True
                            step_record["healed_selector"] = healed.new_selector
                            step_record["healing_strategy"] = healed.strategy
                            try:
                                healed_decision = dict(decision)
                                healed_decision["selector"] = healed.new_selector
                                retry_result = self._execute_action(page, healed_decision)
                                step_record.update(retry_result)
                                step_record["success"] = True
                                consecutive_failures = 0
                            except Exception as e2:
                                step_record["heal_error"] = str(e2)[:200]

                    if not step_record.get("success"):
                        consecutive_failures += 1

                # 操作后延时
                time.sleep(self._explorer_config.operation_delay / 1000)

                # 4. 检测页面变化
                try:
                    after_state = self._analyzer.analyze(page, take_screenshot=False)
                    diffs = self._analyzer.diff(before_state, after_state)
                    step_record["diffs"] = {
                        k: v for k, v in diffs.items()
                        if v and k not in ("added", "removed")
                    }
                    # 检测新错误
                    if diffs.get("new_errors"):
                        for err in diffs["new_errors"]:
                            errors.append(f"步骤 {step_num}: 页面出现错误 - {err}")
                except Exception:
                    pass

                # 5. 连续失败保护
                if consecutive_failures >= self._explorer_config.actions_before_scroll:
                    try:
                        page.evaluate("window.scrollBy(0, 500)")
                        steps.append({
                            "step": f"{step_num}.scroll",
                            "action": "scroll",
                            "reasoning": "连续失败，尝试滚动页面",
                        })
                        consecutive_failures = 0
                    except Exception:
                        pass

                steps.append(step_record)

            # 循环结束
            if not conclusion:
                conclusion = (
                    f"已执行 {len(steps)} 步，"
                    f"{'目标达成' if goal_achieved else '未确认目标是否达成'}"
                )

        except Exception as e:
            errors.append(f"探索执行异常: {e}")
            blocked = True
            conclusion = f"执行中断: {e}"
        finally:
            total_duration = round(time.time() - start_time, 2)

        return self._build_result(
            goal=goal,
            steps=steps,
            screenshots=screenshots,
            errors=errors,
            goal_achieved=goal_achieved,
            blocked=blocked,
            conclusion=conclusion,
            start_time=start_time,
            total_duration=total_duration,
        )

    def _get_or_create_page(self, network) -> Page:
        """获取或创建 Playwright Page."""
        if self._browser_page and not self._browser_page.is_closed():
            return self._browser_page

        browser = network.create_browser()
        context = network.create_context(browser)
        page = network.create_page(context)
        self._browser_page = page
        return page

    def _setup_console_logging(self, page: Page):
        """设置控制台日志收集."""
        self._console_logs = []

        def on_console(msg):
            if msg.type in ("error", "warning"):
                self._console_logs.append({
                    "type": msg.type,
                    "text": msg.text,
                    "timestamp": datetime.now().isoformat(),
                })

        page.on("console", on_console)

        def on_pageerror(err):
            self._console_logs.append({
                "type": "pageerror",
                "text": str(err),
                "timestamp": datetime.now().isoformat(),
            })

        page.on("pageerror", on_pageerror)

    def _decide_action(
        self,
        goal: str,
        page_state: PageState,
        history: List[Dict],
        expected_outcome: str = "",
        step_num: int = 0,
        max_steps: int = 30,
    ) -> Dict[str, Any]:
        """调用 LLM 决策下一步操作."""
        # 构建页面状态文本
        state_text = page_state.to_llm_context(
            max_elements=self._explorer_config.max_page_elements
        )

        # 构建历史记录摘要
        history_text = self._format_history(history, max_items=10) if history else ""

        # 目标增强
        enhanced_goal = goal
        if expected_outcome:
            enhanced_goal += f"\n预期结果: {expected_outcome}"
        enhanced_goal += f"\n当前步骤: {step_num}/{max_steps}"

        # 系统提示
        system = (
            "你是一个专业的UI自动化测试Explorer。"
            "你需要通过观察页面状态，决定下一步操作来完成测试目标。"
            "只返回JSON格式的决策，不要返回其他内容。"
            "仔细分析页面元素列表，使用元素的 [index] 来定位目标。"
            "优先使用精确的选择器避免误操作。"
        )

        if self._vision_llm:
            screenshot = page_state.screenshot_base64 if self._explorer_config.enable_vision else ""
            return self._vision_llm.analyze_page(
                goal=enhanced_goal,
                page_state_text=state_text,
                history_text=history_text,
                screenshot_base64=screenshot,
                system=system,
            )

        # 无 Vision LLM 时的降级决策
        default = {
            "action": "done",
            "selector": "",
            "value": "",
            "reasoning": "无LLM可用，终止探索",
            "done": True,
        }
        return default

    def _execute_action(self, page: Page, decision: Dict) -> Dict[str, Any]:
        """执行单个操作."""
        action = decision.get("action", "click")
        selector = decision.get("selector", "")
        value = decision.get("value", "")

        # 解析索引选择器 [index=N]
        real_selector = self._resolve_index_selector(selector)

        result = {"success": False}

        if action == "click":
            result = self._do_click(page, real_selector)
        elif action == "fill":
            result = self._do_fill(page, real_selector, value)
        elif action == "scroll":
            result = self._do_scroll(page)
        elif action == "navigate":
            result = self._do_navigate(page, value or real_selector)
        elif action == "wait":
            time.sleep(min(float(value) if value else 2, 10))
            result = {"success": True, "action": "wait", "waited": value}
        elif action == "screenshot":
            result = {"success": True, "action": "screenshot"}
        elif action == "press":
            result = self._do_press(page, real_selector, value)
        else:
            result = {"success": False, "error": f"未知操作: {action}"}

        return result

    def _resolve_index_selector(self, selector: str) -> str:
        """解析 [index=N] 格式的选择器."""
        import re
        match = re.match(r"\[index\s*=\s*(\d+)\]", selector.strip())
        if not match:
            return selector
        index = int(match.group(1))
        # 尝试转回原始选择器
        return f"text={selector}" if index >= 0 else selector

    def _do_click(self, page: Page, selector: str) -> Dict:
        """执行点击操作."""
        try:
            loc = page.locator(selector).first
            loc.click(timeout=self._explorer_config.step_timeout * 1000)
            page.wait_for_load_state("domcontentloaded", timeout=5000)
            return {"success": True, "action": "click", "clicked": selector[:80]}
        except Exception as e:
            return {"success": False, "action": "click", "error": str(e)[:200]}

    def _do_fill(self, page: Page, selector: str, value: str) -> Dict:
        """执行填充操作."""
        try:
            loc = page.locator(selector).first
            loc.click(timeout=3000)
            loc.fill("", timeout=3000)  # 清空
            loc.fill(value, timeout=5000)
            return {"success": True, "action": "fill", "filled": selector[:80], "value": value}
        except Exception as e:
            return {"success": False, "action": "fill", "error": str(e)[:200]}

    def _do_scroll(self, page: Page) -> Dict:
        """滚动页面."""
        try:
            page.evaluate("window.scrollBy(0, 600)")
            return {"success": True, "action": "scroll"}
        except Exception as e:
            return {"success": False, "action": "scroll", "error": str(e)[:200]}

    def _do_navigate(self, page: Page, url: str) -> Dict:
        """导航到新 URL."""
        try:
            if not url.startswith("http"):
                url = f"https://{url}" if not url.startswith("/") else url
            page.goto(url, timeout=self._explorer_config.navigation_timeout)
            page.wait_for_load_state("domcontentloaded")
            return {"success": True, "action": "navigate", "url": url[:120]}
        except Exception as e:
            return {"success": False, "action": "navigate", "error": str(e)[:200]}

    def _do_press(self, page: Page, selector: str, key: str) -> Dict:
        """按键操作."""
        try:
            if selector:
                page.locator(selector).first.press(key)
            else:
                page.keyboard.press(key)
            return {"success": True, "action": "press", "key": key}
        except Exception as e:
            return {"success": False, "action": "press", "error": str(e)[:200]}

    def _try_heal_selector(
        self,
        page: Page,
        decision: Dict,
        current_state: PageState,
        previous_state: PageState,
    ) -> Optional[HealedSelector]:
        """尝试自愈选择器."""
        hint = {
            "text": decision.get("value", ""),
            "role": decision.get("action", ""),
        }
        # 从历史中找到最近一次成功使用的选择器提示
        original = decision.get("selector", "")
        return self._healer.heal_with_state(page, original, hint, current_state)

    def _format_history(self, history: List[Dict], max_items: int = 10) -> str:
        """格式化操作历史为文本."""
        if not history:
            return ""

        recent = history[-max_items:]
        lines = []
        for h in recent:
            step = h.get("step", "?")
            action = h.get("action", "?")
            selector = h.get("selector", "")
            value = h.get("value", "")
            success = "✓" if h.get("success", True) else "✗"
            reasoning = h.get("reasoning", "")

            desc_parts = [f"{success} 步骤{step}: {action}"]
            if selector:
                desc_parts.append(f"selector={selector[:60]}")
            if value:
                desc_parts.append(f"value={value[:30]}")
            if reasoning:
                desc_parts.append(f"({reasoning[:80]})")

            lines.append(" ".join(desc_parts))

        return "\n".join(lines)

    def _build_result(
        self,
        goal: str,
        steps: List[Dict],
        screenshots: List[str],
        errors: List[str],
        goal_achieved: bool,
        blocked: bool,
        conclusion: str,
        start_time: float,
        total_duration: float = 0,
    ) -> Dict:
        """构建探索结果."""
        return {
            "goal": goal,
            "steps": steps,
            "screenshots": screenshots,
            "errors": errors,
            "goal_achieved": goal_achieved,
            "blocked": blocked,
            "conclusion": conclusion,
            "total_steps": len(steps),
            "duration": total_duration or round(time.time() - start_time, 2),
            "healing_stats": self._healer.get_healing_stats() if self._explorer_config.enable_self_healing else {},
        }

    def cleanup(self):
        """清理浏览器资源."""
        if self._browser_page:
            try:
                self._browser_page.close()
            except Exception:
                pass
            self._browser_page = None
