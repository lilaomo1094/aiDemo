# -*- coding: utf-8 -*-
"""Function Calling 编排器 Agent.

接收自然语言指令，通过大模型的 Function Calling 能力自动调度其他 Agent
完成需求分析、代码解析、用例生成、测试执行、缺陷发现、报告生成等任务。
"""

import json
from typing import Any, Dict, List, Optional

from automation.core.llm import AgentTools, LLMResponse
from automation.core.utils import compact_json
from automation.workflow.engine import WorkflowContext, WorkflowEngine

from .base import BaseAgent
from .code_parser import CodeParser
from .defect_detector import DefectDetector
from .report_generator import ReportGenerator
from .requirement_analyzer import RequirementAnalyzer
from .test_executor import TestExecutor
from .test_generator import TestGenerator


class FunctionCallingOrchestrator(BaseAgent):
    """基于 Function Calling 的任务编排器."""

    SYSTEM_PROMPT = """你是 aiAgent 全链路自动化测试平台的智能编排器。
你可以调用以下工具帮助用户完成测试任务：
- analyze_requirement: 分析需求文档
- parse_code: 解析代码仓库或 OpenAPI
- generate_test_cases: 生成测试用例
- execute_tests: 执行测试用例
- detect_defects: 分析并发现缺陷
- generate_report: 生成测试报告
- submit_test_task: 提交异步测试任务（适合 IM/邮件场景）
- query_task_status: 查询任务状态

请根据用户指令，按顺序调用合适的工具。每次可以调用一个或多个工具。
如果某一步依赖上一步结果，请等待上一步结果返回后再继续。"""

    MAX_ITERATIONS = 10

    def __init__(self, config, knowledge_store=None):
        super().__init__(config, knowledge_store)
        self.tools = AgentTools.all_tools()
        self.context: Optional[WorkflowContext] = None
        self._tool_results: List[Dict[str, Any]] = []

    def execute(self, task, context) -> Dict[str, Any]:
        """执行用户指令，返回最终执行结果.

        task 中应包含：
        - instruction: 用户自然语言指令（必填）
        - context/run_id: 可选，已有工作流上下文
        """
        instruction = task.input_data.get("instruction", "") if hasattr(task, "input_data") else task.get("instruction", "")
        if not instruction:
            return {"status": "error", "message": "缺少用户指令"}

        run_id = getattr(context, "run_id", "") if context else ""
        self.context = context or self._create_context(run_id)

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
        ]

        final_answer = ""
        for _ in range(self.MAX_ITERATIONS):
            if not self.llm:
                return self._fallback_run(instruction)

            resp = self.llm.chat(messages, tools=self.tools)

            if resp.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": resp.content or "",
                    "tool_calls": self._to_openai_tool_calls(resp.tool_calls),
                })
                for tc in resp.tool_calls:
                    result = self._execute_tool_call(tc)
                    self._tool_results.append(result)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id", ""),
                        "content": compact_json(result),
                    })
            else:
                final_answer = resp.content
                break

        return {
            "status": "completed",
            "instruction": instruction,
            "final_answer": final_answer,
            "tool_results": self._tool_results,
            "context": self.context.to_dict(),
        }

    def _create_context(self, run_id: str) -> WorkflowContext:
        project_info = {
            "project_name": "FunctionCalling 任务",
            "project_code": "FC-001",
            "test_type": "智能编排",
            "test_environment": "dev",
        }
        if hasattr(self.config, "project"):
            project_info.update(self.config.project.model_dump() if hasattr(self.config.project, "model_dump") else dict(self.config.project))
        return WorkflowContext(run_id=run_id or "FC-RUN", project_info=project_info)

    def _to_openai_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "id": tc.get("id", ""),
                "type": tc.get("type", "function"),
                "function": tc.get("function", {}),
            }
            for tc in tool_calls
        ]

    def _execute_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        func = tool_call.get("function", {})
        name = func.get("name", "")
        try:
            args = json.loads(func.get("arguments", "{}"))
        except Exception as e:
            return {"tool": name, "status": "error", "message": f"参数解析失败: {e}"}

        handlers = {
            "analyze_requirement": self._tool_analyze_requirement,
            "parse_code": self._tool_parse_code,
            "generate_test_cases": self._tool_generate_test_cases,
            "execute_tests": self._tool_execute_tests,
            "detect_defects": self._tool_detect_defects,
            "generate_report": self._tool_generate_report,
            "submit_test_task": self._tool_submit_test_task,
            "query_task_status": self._tool_query_task_status,
        }
        handler = handlers.get(name)
        if not handler:
            return {"tool": name, "status": "error", "message": f"未知工具: {name}"}

        try:
            return handler(args)
        except Exception as e:
            return {"tool": name, "status": "error", "message": str(e)}

    def _tool_analyze_requirement(self, args: Dict[str, Any]) -> Dict[str, Any]:
        doc = args.get("requirement_doc") or self.context.requirement_doc
        if not doc:
            # 尝试读取配置文件中的需求文档
            req_config = getattr(self.config, "requirement", None)
            if req_config:
                req_dict = req_config.model_dump() if hasattr(req_config, "model_dump") else dict(req_config)
                doc_path = req_dict.get("requirement_doc_path")
                if doc_path:
                    from pathlib import Path
                    path = Path(doc_path)
                    if path.exists():
                        doc = path.read_text(encoding="utf-8")
        if not doc:
            return {"tool": "analyze_requirement", "status": "skipped", "message": "无需求文档"}

        agent = RequirementAnalyzer(self.config, self.knowledge_store)
        from automation.workflow.engine import WorkflowTask
        task = WorkflowTask(task_id="fc_req", agent_type=None, name="需求分析", description="", input_data={"requirement_doc": doc})
        result = agent.execute(task, self.context)
        self.context.requirement_doc = doc
        if isinstance(result, dict) and "requirements" in result:
            self.context.metadata["requirements"] = result["requirements"]
        return {"tool": "analyze_requirement", "status": "ok", "result": result}

    def _tool_parse_code(self, args: Dict[str, Any]) -> Dict[str, Any]:
        repo_type = args.get("repo_type", "backend")
        source = args.get("source", "")
        agent = CodeParser(self.config, self.knowledge_store)
        from automation.workflow.engine import WorkflowTask
        task = WorkflowTask(
            task_id="fc_code",
            agent_type=None,
            name="代码解析",
            description="",
            input_data={"repo_type": repo_type, "source": source},
        )
        result = agent.execute(task, self.context)
        self.context.code_info.update(result.get("code_info", {}))
        return {"tool": "parse_code", "status": "ok", "result": result}

    def _tool_generate_test_cases(self, args: Dict[str, Any]) -> Dict[str, Any]:
        agent = TestGenerator(self.config, self.knowledge_store)
        from automation.workflow.engine import WorkflowTask
        task = WorkflowTask(
            task_id="fc_gen",
            agent_type=None,
            name="用例生成",
            description="",
            input_data=args,
        )
        result = agent.execute(task, self.context)
        if isinstance(result, dict) and "test_cases" in result:
            self.context.test_cases = result["test_cases"]
        return {"tool": "generate_test_cases", "status": "ok", "count": len(self.context.test_cases)}

    def _tool_execute_tests(self, args: Dict[str, Any]) -> Dict[str, Any]:
        agent = TestExecutor(self.config, self.knowledge_store)
        from automation.workflow.engine import WorkflowTask
        task = WorkflowTask(task_id="fc_exec", agent_type=None, name="测试执行", description="", input_data=args)
        result = agent.execute(task, self.context)
        if isinstance(result, dict) and "execution_results" in result:
            self.context.execution_results = result["execution_results"]
        return {"tool": "execute_tests", "status": "ok", "summary": result.get("summary", {})}

    def _tool_detect_defects(self, args: Dict[str, Any]) -> Dict[str, Any]:
        agent = DefectDetector(self.config, self.knowledge_store)
        from automation.workflow.engine import WorkflowTask
        task = WorkflowTask(task_id="fc_defect", agent_type=None, name="缺陷发现", description="", input_data=args)
        result = agent.execute(task, self.context)
        if isinstance(result, dict) and "defects" in result:
            self.context.defects = result["defects"]
        return {"tool": "detect_defects", "status": "ok", "count": len(self.context.defects)}

    def _tool_generate_report(self, args: Dict[str, Any]) -> Dict[str, Any]:
        agent = ReportGenerator(self.config, self.knowledge_store)
        from automation.workflow.engine import WorkflowTask
        task = WorkflowTask(task_id="fc_report", agent_type=None, name="报告生成", description="", input_data=args)
        result = agent.execute(task, self.context)
        return {"tool": "generate_report", "status": "ok", "result": result}

    def _tool_submit_test_task(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from automation.core.scheduler import TaskScheduler
        scheduler = TaskScheduler(max_workers=1)
        task_id = scheduler.submit(
            config_path=args["config_path"],
            priority=args.get("priority", 5),
        )
        return {"tool": "submit_test_task", "status": "ok", "task_id": task_id}

    def _tool_query_task_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from automation.core.scheduler import TaskScheduler
        scheduler = TaskScheduler(max_workers=1)
        task_id = args.get("task_id")
        status = scheduler.get_status(task_id) if task_id else scheduler.list_tasks()
        return {"tool": "query_task_status", "status": "ok", "result": status}

    def _fallback_run(self, instruction: str) -> Dict[str, Any]:
        """未配置 LLM 时的兜底：顺序执行完整工作流."""
        engine = WorkflowEngine(self.config, self.knowledge_store)
        result = engine.run(self.context)
        return {
            "status": "completed",
            "instruction": instruction,
            "final_answer": "未配置 LLM，已按默认工作流执行测试任务。",
            "tool_results": [],
            "workflow_result": result,
        }
