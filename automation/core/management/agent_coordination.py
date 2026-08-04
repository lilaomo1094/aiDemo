# -*- coding: utf-8 -*-
"""多 Agent 协作编排.

角色：
- 需求分析师：解析需求，提取验收标准
- 高级测试工程师：设计并执行测试
- 质量 QA：缺陷发现与报告质量把关
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from automation.agents.defect_detector import DefectDetector
from automation.agents.report_generator import ReportGenerator
from automation.agents.requirement_analyzer import RequirementAnalyzer
from automation.agents.test_executor import TestExecutor
from automation.agents.test_generator import TestGenerator
from automation.workflow.engine import WorkflowContext, WorkflowTask


@dataclass
class AgentResult:
    role: str
    agent_name: str
    status: str  # success | failed | skipped
    output: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    started_at: str = ""
    finished_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "agent_name": self.agent_name,
            "status": self.status,
            "output": self.output,
            "message": self.message,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


class AgentCoordinator:
    """协调需求分析师、高级测试工程师、质量 QA 三个角色."""

    ROLE_REQUIREMENT_ANALYST = "需求分析师"
    ROLE_SENIOR_TEST_ENGINEER = "高级测试工程师"
    ROLE_QUALITY_QA = "质量 QA"

    def __init__(self, config, knowledge_store=None):
        self.config = config
        self.knowledge_store = knowledge_store
        self._listeners: List[Callable] = []
        self._results: List[AgentResult] = []

    def register_listener(self, listener: Callable):
        self._listeners.append(listener)

    def _emit(self, event: str, data: Dict[str, Any]):
        for listener in self._listeners:
            try:
                listener(event, data)
            except Exception as e:
                print(f"Agent 协调监听器错误: {e}")

    def run(self, context: WorkflowContext) -> Dict[str, Any]:
        """执行完整的三角色协作链."""
        self._results = []

        # 1. 需求分析师
        req_result = self._run_agent(
            role=self.ROLE_REQUIREMENT_ANALYST,
            agent_name="RequirementAnalyzer",
            agent=RequirementAnalyzer(self.config, self.knowledge_store),
            task=WorkflowTask(
                task_id="req_analysis",
                agent_type=None,
                name="需求分析",
                description="解析需求文档，提取测试要点与验收标准",
                input_data={},
            ),
            context=context,
        )
        if req_result.status == "success":
            context.metadata["requirements"] = req_result.output.get("requirements", [])
            context.metadata["test_points"] = req_result.output.get("test_points", [])
            context.metadata["acceptance_criteria"] = req_result.output.get("acceptance_criteria", [])

        # 2. 高级测试工程师：生成用例
        gen_result = self._run_agent(
            role=self.ROLE_SENIOR_TEST_ENGINEER,
            agent_name="TestGenerator",
            agent=TestGenerator(self.config, self.knowledge_store),
            task=WorkflowTask(
                task_id="test_generation",
                agent_type=None,
                name="测试用例生成",
                description="基于需求设计测试用例",
                input_data={},
            ),
            context=context,
        )
        if gen_result.status == "success" and "test_cases" in gen_result.output:
            context.test_cases = gen_result.output["test_cases"]

        # 3. 高级测试工程师：执行测试
        exec_result = self._run_agent(
            role=self.ROLE_SENIOR_TEST_ENGINEER,
            agent_name="TestExecutor",
            agent=TestExecutor(self.config, self.knowledge_store),
            task=WorkflowTask(
                task_id="test_execution",
                agent_type=None,
                name="测试执行",
                description="执行测试用例并收集结果",
                input_data={},
            ),
            context=context,
        )
        if exec_result.status == "success" and "execution_results" in exec_result.output:
            context.execution_results = exec_result.output["execution_results"]

        # 4. 质量 QA：缺陷发现
        defect_result = self._run_agent(
            role=self.ROLE_QUALITY_QA,
            agent_name="DefectDetector",
            agent=DefectDetector(self.config, self.knowledge_store),
            task=WorkflowTask(
                task_id="defect_detection",
                agent_type=None,
                name="缺陷发现",
                description="分析执行结果识别缺陷",
                input_data={},
            ),
            context=context,
        )
        if defect_result.status == "success" and "defects" in defect_result.output:
            context.defects = defect_result.output["defects"]

        # 5. 质量 QA：报告生成
        report_result = self._run_agent(
            role=self.ROLE_QUALITY_QA,
            agent_name="ReportGenerator",
            agent=ReportGenerator(self.config, self.knowledge_store),
            task=WorkflowTask(
                task_id="report_generation",
                agent_type=None,
                name="报告生成",
                description="生成测试报告与缺陷清单",
                input_data={},
            ),
            context=context,
        )
        if report_result.status == "success":
            context.metadata["report_result"] = report_result.output
            if "output_files" in report_result.output:
                context.metadata.setdefault("output_files", {}).update(report_result.output["output_files"])
            if "report_path" in report_result.output:
                context.metadata["report_path"] = report_result.output["report_path"]

        return {
            "status": "completed" if all(r.status == "success" for r in self._results) else "partial",
            "agent_results": [r.to_dict() for r in self._results],
            "summary": self._summary(),
        }

    def _run_agent(
        self,
        role: str,
        agent_name: str,
        agent: Any,
        task: WorkflowTask,
        context: WorkflowContext,
    ) -> AgentResult:
        started = datetime.now().isoformat()
        self._emit("agent_started", {"role": role, "agent": agent_name})
        try:
            output = agent.execute(task, context)
            result = AgentResult(
                role=role,
                agent_name=agent_name,
                status="success",
                output=output if isinstance(output, dict) else {"result": output},
                started_at=started,
                finished_at=datetime.now().isoformat(),
            )
        except Exception as e:
            result = AgentResult(
                role=role,
                agent_name=agent_name,
                status="failed",
                message=str(e),
                started_at=started,
                finished_at=datetime.now().isoformat(),
            )
        self._results.append(result)
        self._emit("agent_finished", result.to_dict())
        return result

    def _summary(self) -> Dict[str, Any]:
        total = len(self._results)
        success = sum(1 for r in self._results if r.status == "success")
        failed = sum(1 for r in self._results if r.status == "failed")
        return {
            "total_agents": total,
            "success": success,
            "failed": failed,
            "roles": [r.role for r in self._results],
        }
