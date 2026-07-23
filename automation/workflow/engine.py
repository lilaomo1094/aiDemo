# -*- coding: utf-8 -*-
"""工作流引擎：负责任务调度与上下文管理."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentType(Enum):
    REQUIREMENT_ANALYZER = "requirement_analyzer"
    CODE_PARSER = "code_parser"
    TEST_GENERATOR = "test_generator"
    TEST_EXECUTOR = "test_executor"
    DEFECT_DETECTOR = "defect_detector"
    REPORT_GENERATOR = "report_generator"


@dataclass
class WorkflowTask:
    task_id: str
    agent_type: AgentType
    name: str
    description: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    input_data: Dict = field(default_factory=dict)
    output_data: Dict = field(default_factory=dict)
    error_message: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)

    def duration(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


@dataclass
class WorkflowContext:
    run_id: str
    project_info: Dict
    requirement_doc: str = ""
    database_schema: Dict = field(default_factory=dict)
    code_info: Dict = field(default_factory=dict)
    test_cases: List[Dict] = field(default_factory=list)
    execution_results: List[Dict] = field(default_factory=list)
    defects: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "run_id": self.run_id,
            "project_info": self.project_info,
            "requirement_doc": self.requirement_doc[:500] + "..." if len(self.requirement_doc) > 500 else self.requirement_doc,
            "database_schema": self.database_schema,
            "test_cases_count": len(self.test_cases),
            "execution_results_count": len(self.execution_results),
            "defects_count": len(self.defects),
            "metadata": self.metadata,
        }


class WorkflowEngine:
    def __init__(self, config: Any, knowledge_store=None):
        self.config = config
        self.knowledge_store = knowledge_store
        self.tasks: Dict[str, WorkflowTask] = {}
        self.context: Optional[WorkflowContext] = None
        self.listeners: List[Callable] = []
        # 延迟初始化 agent 工厂，避免重复 import
        self._agent_factory_cache = None

    def register_listener(self, listener: Callable):
        self.listeners.append(listener)

    def notify(self, event: str, data: Dict):
        for listener in self.listeners:
            try:
                listener(event, data)
            except Exception as e:
                print(f"Listener error: {e}")

    def create_tasks(self) -> List[WorkflowTask]:
        tasks = [
            WorkflowTask(
                task_id="task_requirement",
                agent_type=AgentType.REQUIREMENT_ANALYZER,
                name="需求分析",
                description="解析需求文档，提取测试要点和验收标准",
            ),
            WorkflowTask(
                task_id="task_code_parse",
                agent_type=AgentType.CODE_PARSER,
                name="代码解析",
                description="解析前后端代码，提取 API 接口和数据模型",
                dependencies=["task_requirement"],
            ),
            WorkflowTask(
                task_id="task_test_generate",
                agent_type=AgentType.TEST_GENERATOR,
                name="测试用例生成",
                description="基于需求和代码生成测试用例",
                dependencies=["task_code_parse"],
            ),
            WorkflowTask(
                task_id="task_test_execute",
                agent_type=AgentType.TEST_EXECUTOR,
                name="测试执行",
                description="执行测试用例，收集执行结果",
                dependencies=["task_test_generate"],
            ),
            WorkflowTask(
                task_id="task_defect_detect",
                agent_type=AgentType.DEFECT_DETECTOR,
                name="缺陷发现",
                description="分析执行结果，识别缺陷",
                dependencies=["task_test_execute"],
            ),
            WorkflowTask(
                task_id="task_report",
                agent_type=AgentType.REPORT_GENERATOR,
                name="报告生成",
                description="生成测试报告和缺陷清单",
                dependencies=["task_defect_detect"],
            ),
        ]
        for task in tasks:
            self.tasks[task.task_id] = task
        return tasks

    def can_execute(self, task: WorkflowTask) -> bool:
        if task.status != WorkflowStatus.PENDING:
            return False
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task.status != WorkflowStatus.COMPLETED:
                return False
        return True

    def get_executable_tasks(self) -> List[WorkflowTask]:
        return [task for task in self.tasks.values() if self.can_execute(task)]

    def run(self, context: WorkflowContext) -> Dict:
        self.context = context
        self.create_tasks()
        results = {
            "run_id": context.run_id,
            "status": WorkflowStatus.COMPLETED.value,
            "tasks": [],
            "summary": {},
            "errors": [],
        }
        max_iterations = len(self.tasks) * 2
        iteration = 0
        while iteration < max_iterations:
            executable = self.get_executable_tasks()
            if not executable:
                remaining = [t for t in self.tasks.values() if t.status == WorkflowStatus.PENDING]
                if remaining:
                    results["status"] = WorkflowStatus.FAILED.value
                    results["errors"].append(f"无法执行任务: {remaining[0].task_id}")
                    for task in remaining:
                        task.status = WorkflowStatus.FAILED
                        task.error_message = "依赖任务失败"
                break
            for task in executable:
                self._execute_task(task)
                results["tasks"].append({
                    "task_id": task.task_id,
                    "name": task.name,
                    "status": task.status.value,
                    "duration": task.duration(),
                    "error": task.error_message,
                })
                if task.status == WorkflowStatus.FAILED:
                    results["status"] = WorkflowStatus.FAILED.value
                    results["errors"].append(f"任务 {task.name} 失败: {task.error_message}")
            iteration += 1
            if all(t.status == WorkflowStatus.COMPLETED for t in self.tasks.values()):
                break
        results["summary"] = self._generate_summary()
        return results

    def _execute_task(self, task: WorkflowTask):
        task.status = WorkflowStatus.RUNNING
        task.start_time = datetime.now()
        self.notify("task_started", {"task": task.name, "task_id": task.task_id})
        try:
            agent_output = self._run_agent(task)
            task.output_data = agent_output
            task.status = WorkflowStatus.COMPLETED
            self._update_context(task)
            self.notify("task_completed", {"task": task.name, "task_id": task.task_id, "output": agent_output})
        except Exception as e:
            task.status = WorkflowStatus.FAILED
            task.error_message = str(e)
            task.end_time = datetime.now()
            self.notify("task_failed", {"task": task.name, "task_id": task.task_id, "error": str(e)})

    def _get_agent_factory(self):
        if self._agent_factory_cache is None:
            from automation.agents.requirement_analyzer import RequirementAnalyzer
            from automation.agents.code_parser import CodeParser
            from automation.agents.test_generator import TestGenerator
            from automation.agents.test_executor import TestExecutor
            from automation.agents.defect_detector import DefectDetector
            from automation.agents.report_generator import ReportGenerator

            self._agent_factory_cache = {
                AgentType.REQUIREMENT_ANALYZER: RequirementAnalyzer,
                AgentType.CODE_PARSER: CodeParser,
                AgentType.TEST_GENERATOR: TestGenerator,
                AgentType.TEST_EXECUTOR: TestExecutor,
                AgentType.DEFECT_DETECTOR: DefectDetector,
                AgentType.REPORT_GENERATOR: ReportGenerator,
            }
        return self._agent_factory_cache

    def _run_agent(self, task: WorkflowTask) -> Dict:
        factory = self._get_agent_factory()
        agent_cls = factory.get(task.agent_type)
        if not agent_cls:
            raise ValueError(f"Unknown agent type: {task.agent_type}")
        agent = agent_cls(self.config, knowledge_store=self.knowledge_store)
        return agent.execute(task, self.context)

    def _update_context(self, task: WorkflowTask):
        if task.agent_type == AgentType.REQUIREMENT_ANALYZER:
            self.context.metadata["requirements"] = task.output_data.get("requirements", [])
            self.context.metadata["test_points"] = task.output_data.get("test_points", [])
            self.context.metadata["acceptance_criteria"] = task.output_data.get("acceptance_criteria", [])
        elif task.agent_type == AgentType.CODE_PARSER:
            self.context.code_info = task.output_data.get("code_info", {})
            self.context.database_schema = task.output_data.get("code_info", {}).get("database", {})
        elif task.agent_type == AgentType.TEST_GENERATOR:
            self.context.test_cases = task.output_data.get("test_cases", [])
        elif task.agent_type == AgentType.TEST_EXECUTOR:
            self.context.execution_results = task.output_data.get("execution_results", [])
        elif task.agent_type == AgentType.DEFECT_DETECTOR:
            self.context.defects = task.output_data.get("defects", [])
        elif task.agent_type == AgentType.REPORT_GENERATOR:
            self.context.metadata["report_path"] = task.output_data.get("report_path", "")
            self.context.metadata["output_files"] = task.output_data.get("output_files", {})

    def _generate_summary(self) -> Dict:
        completed = sum(1 for t in self.tasks.values() if t.status == WorkflowStatus.COMPLETED)
        failed = sum(1 for t in self.tasks.values() if t.status == WorkflowStatus.FAILED)
        total_duration = sum(t.duration() for t in self.tasks.values())
        return {
            "total_tasks": len(self.tasks),
            "completed": completed,
            "failed": failed,
            "total_duration": total_duration,
            "test_cases_count": len(self.context.test_cases) if self.context else 0,
            "defects_count": len(self.context.defects) if self.context else 0,
        }


def create_workflow(config, knowledge_store=None) -> WorkflowEngine:
    return WorkflowEngine(config, knowledge_store=knowledge_store)
