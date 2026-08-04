# -*- coding: utf-8 -*-
"""Function Calling 工具定义：将 Agent 能力暴露为大模型可调用的工具."""

from typing import Any, Dict, List

from .base import ToolDefinition


class AgentTools:
    """智测 可调用工具集合."""

    @classmethod
    def all_tools(cls) -> List[ToolDefinition]:
        return [
            cls.analyze_requirement(),
            cls.parse_code(),
            cls.generate_test_cases(),
            cls.execute_tests(),
            cls.explore_ui(),
            cls.detect_defects(),
            cls.generate_report(),
            cls.submit_test_task(),
            cls.query_task_status(),
        ]

    @classmethod
    def analyze_requirement(cls) -> ToolDefinition:
        return ToolDefinition(
            name="analyze_requirement",
            description="分析需求文档，提取测试要点、验收标准和功能模块。",
            parameters={
                "requirement_doc": {
                    "type": "string",
                    "description": "需求文档内容或文件路径，为空则使用配置中的需求文档。",
                },
                "focus_modules": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "需要重点关注的模块列表，为空则自动识别。",
                },
            },
            required=[],
        )

    @classmethod
    def parse_code(cls) -> ToolDefinition:
        return ToolDefinition(
            name="parse_code",
            description="解析前后端代码仓库或 OpenAPI 规范，提取 API 接口、数据模型和前端组件。",
            parameters={
                "repo_type": {
                    "type": "string",
                    "enum": ["frontend", "backend", "openapi"],
                    "description": "代码类型。",
                },
                "source": {
                    "type": "string",
                    "description": "Git URL、本地路径或 OpenAPI 文件路径。",
                },
            },
            required=["repo_type", "source"],
        )

    @classmethod
    def generate_test_cases(cls) -> ToolDefinition:
        return ToolDefinition(
            name="generate_test_cases",
            description="基于需求分析结果和代码解析结果生成测试用例。",
            parameters={
                "test_types": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["api", "ui", "db", "integration", "e2e"]},
                    "description": "需要生成的测试类型。",
                },
                "priority_filter": {
                    "type": "string",
                    "enum": ["all", "high", "medium", "low"],
                    "description": "用例优先级过滤。",
                },
            },
            required=[],
        )

    @classmethod
    def execute_tests(cls) -> ToolDefinition:
        return ToolDefinition(
            name="execute_tests",
            description="执行已生成的测试用例，支持按类型或 ID 过滤。",
            parameters={
                "test_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "指定执行的用例 ID 列表，为空则执行全部。",
                },
                "test_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "按类型过滤执行。",
                },
            },
            required=[],
        )

    @classmethod
    def detect_defects(cls) -> ToolDefinition:
        return ToolDefinition(
            name="detect_defects",
            description="分析测试执行结果，识别缺陷并生成缺陷报告。",
            parameters={
                "execution_results": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "测试执行结果列表，为空则使用上下文中最近的结果。",
                },
            },
            required=[],
        )

    @classmethod
    def generate_report(cls) -> ToolDefinition:
        return ToolDefinition(
            name="generate_report",
            description="生成最终测试报告（HTML/CSV/Excel/JSON）。",
            parameters={
                "formats": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["html", "csv", "excel", "json"]},
                    "description": "报告格式。",
                },
            },
            required=[],
        )

    @classmethod
    def submit_test_task(cls) -> ToolDefinition:
        return ToolDefinition(
            name="submit_test_task",
            description="向任务调度器提交一个异步测试任务，适用于 IM/邮件等异步场景。",
            parameters={
                "config_path": {
                    "type": "string",
                    "description": "测试配置文件路径。",
                },
                "priority": {
                    "type": "integer",
                    "description": "任务优先级 1-10，数字越小越优先。",
                },
            },
            required=["config_path"],
        )

    @classmethod
    def explore_ui(cls) -> ToolDefinition:
        return ToolDefinition(
            name="explore_ui",
            description=(
                "对 Web UI 页面进行 AI 驱动的探索式测试。"
                "只需用自然语言描述测试目标（如'测试登录功能是否正常'），"
                "Agent 会自动打开页面、分析 DOM 结构、通过 LLM(Vision) 观察页面截图决策下一步操作，"
                "执行交互并报告结果。支持：功能验证、回归测试、冒烟测试、UI 可用性检查。"
                "当用户请求动态 UI 测试、自然语言 UI 测试时优先使用此工具。"
            ),
            parameters={
                "goal": {
                    "type": "string",
                    "description": "测试目标，用自然语言描述。"
                    "如：'使用 admin/admin123 登录，验证能否进入管理后台首页'",
                },
                "start_url": {
                    "type": "string",
                    "description": "起始页面 URL，如 https://example.com/login",
                },
                "max_steps": {
                    "type": "integer",
                    "description": "最大探索步数，默认 20",
                },
                "expected_outcome": {
                    "type": "string",
                    "description": "期望的测试结果描述，如：'跳转到首页，显示欢迎信息'",
                },
            },
            required=["goal"],
        )

    @classmethod
    def query_task_status(cls) -> ToolDefinition:
        return ToolDefinition(
            name="query_task_status",
            description="查询调度器中任务的状态。",
            parameters={
                "task_id": {
                    "type": "string",
                    "description": "任务 ID，为空则返回最近任务状态。",
                },
            },
            required=[],
        )
