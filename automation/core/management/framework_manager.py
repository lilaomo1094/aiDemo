# -*- coding: utf-8 -*-
"""测试自动化管理框架总入口.

整合版本生命周期、任务生命周期、Agent 协作、环境画像、资产管理.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from automation.core.config import CodeRepositoryConfig, PlatformConfig
from automation.core.management.agent_coordination import AgentCoordinator
from automation.core.management.asset_manager import AssetManager
from automation.core.management.environment_profile import EnvironmentProfileManager
from automation.core.management.task_lifecycle import TaskLifecycleManager
from automation.core.management.version_lifecycle import VersionLifecycleManager
from automation.core.monitoring import MilestoneManager, NodeStatus, ProgressReporter, RiskManager
from automation.core.output import OutputFormatter
from automation.core.rag import AgentKnowledgeStore
from automation.workflow.engine import WorkflowContext


class TestAutomationManager:
    """智测 测试自动化管理框架总入口."""

    def __init__(self, config: PlatformConfig, knowledge_store=None):
        self.config = config
        self.knowledge_store = knowledge_store
        version_config = getattr(config, "version", None)
        base_dir = config.base_dir / (version_config.base_dir if version_config else "versions")
        current_version = version_config.current_version if version_config else None
        self.version_manager = VersionLifecycleManager(base_dir, current_version=current_version)
        self.asset_manager = AssetManager(self.version_manager)
        test_config = getattr(config, "test", None)
        self.task_manager = TaskLifecycleManager(
            state_dir=str(config.base_dir / "output" / "task_lifecycle"),
            max_workers=test_config.max_workers if test_config else 4,
        )
        self.env_manager = EnvironmentProfileManager(config)

    def prepare_version(
        self,
        version: Optional[str] = None,
        auto_create: bool = True,
        environment_type: Optional[str] = None,
    ) -> str:
        """准备版本环境：自动创建、切换当前版本、应用环境画像."""
        target = version or self.version_manager.current_version
        if not target:
            target = "v0.7.30"

        target = self.version_manager._normalize_version(target)

        if target not in self.version_manager.list_versions():
            if auto_create:
                print(f"🆕 自动创建版本: {target}")
                self.version_manager.create_version(
                    target,
                    description=f"创建于 {datetime.now().isoformat()}",
                    environment_profile=environment_type or self.config.network.type,
                )
            else:
                raise FileNotFoundError(f"版本不存在: {target}")

        self.version_manager.set_current(target)

        # 应用环境画像
        profile = self.env_manager.build_profile(override_type=environment_type)
        self.env_manager.apply_to_config(profile)

        # 应用版本级 Swagger / 代码仓库配置
        self._apply_version_sources(target)

        return target

    def _apply_version_sources(self, version: str):
        """将版本级 sources 配置合并到当前 config，供 Agent 使用."""
        cfg = self.version_manager.ensure_version_config(version, environment=self.config.environment)
        sources = cfg.get("sources", {})

        # Swagger -> 代码解析的 API Spec
        swagger = sources.get("swagger", {})
        if swagger.get("enabled"):
            spec_source = swagger.get("file_path") or swagger.get("url") or ""
            if spec_source:
                print(f"📘 版本级 Swagger: {spec_source}")
                # 如果 backend_repo 未启用，则构造一个启用的 backend_repo 用于解析
                if not self.config.backend_repo.enabled:
                    self.config.backend_repo = CodeRepositoryConfig(
                        enabled=True,
                        type="openapi",
                        api_spec=spec_source,
                    )
                else:
                    self.config.backend_repo.api_spec = spec_source or self.config.backend_repo.api_spec

        # 版本级前后端仓库覆盖项目级配置
        for key in ["frontend_repo", "backend_repo"]:
            repo = sources.get(key, {})
            if repo.get("enabled"):
                print(f"📦 版本级 {key}: {repo.get('url') or repo.get('local_path')}")
                model = CodeRepositoryConfig(
                    enabled=True,
                    type=repo.get("type", "github"),
                    url=repo.get("url", ""),
                    branch=repo.get("branch", "main"),
                    language=repo.get("language", ""),
                    test_framework=repo.get("test_framework", ""),
                    api_spec=repo.get("api_spec", ""),
                    local_path=repo.get("local_path", ""),
                )
                setattr(self.config, key, model)

    def run_version(
        self,
        version: Optional[str] = None,
        environment_type: Optional[str] = None,
        progress_reporter: Optional[ProgressReporter] = None,
    ) -> Dict[str, Any]:
        """执行一次完整版本测试（三 Agent 协作）."""
        active_version = self.prepare_version(version, environment_type=environment_type)
        run_id = self._generate_run_id()

        print(f"\n{'=' * 60}")
        print("🚀 智测 测试自动化管理框架")
        print(f"{'=' * 60}")
        print(f"📌 版本: {active_version}")
        print(f"🌐 网络环境: {self.config.network.type}")
        print(f"🖥️  浏览器模式: {self.config.network.browser_mode}")
        print(f"📋 运行ID: {run_id}")
        print(f"{'=' * 60}\n")

        # 加载需求
        req_doc = self.version_manager.requirement_path(active_version).read_text(encoding="utf-8")

        # 里程碑
        milestone_manager = MilestoneManager(run_id)
        milestone_manager.start("config_validated", "校验配置与版本环境")
        validation_context = SimpleNamespace(requirement_doc=req_doc, config=self.config)
        milestone_manager.evaluate_risks("config_validated", validation_context, self.config)
        cfg_status = NodeStatus.BLOCKED if milestone_manager.risk_manager.has_critical() else NodeStatus.PASSED
        milestone_manager.finish("config_validated", status=cfg_status)
        if cfg_status == NodeStatus.BLOCKED:
            return {
                "run_id": run_id,
                "version": active_version,
                "status": "blocked",
                "errors": ["配置校验存在严重风险，已阻断执行"],
                "milestones": milestone_manager.to_dict(),
            }

        project_info = {
            "run_id": run_id,
            "project_name": self.config.project.name,
            "project_code": self.config.project.code,
            "test_type": self.config.project.test_type,
            "test_environment": self.config.project.environment,
            "version": active_version,
            "start_time": datetime.now().isoformat(),
        }

        context = WorkflowContext(
            run_id=run_id,
            project_info=project_info,
            requirement_doc=req_doc,
            metadata={"version": active_version, "environment_type": self.config.network.type},
        )

        # 三角色 Agent 协作
        coordinator = AgentCoordinator(self.config, self.knowledge_store)
        if progress_reporter:
            coordinator.register_listener(lambda event, data: self._on_agent_event(progress_reporter, event, data))
        coordination_result = coordinator.run(context)

        # 保存结果到版本输出目录
        output_dir = self.version_manager.output_dir(active_version)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_files = self._save_run_outputs(context, output_dir, run_id)

        # 转换为绝对路径以更新资产索引
        abs_output_files = {k: str(self.config.base_dir / v) for k, v in output_files.items()}
        self.asset_manager.collect_run_output(active_version, abs_output_files, run_id)

        # 更新基线
        baseline = self.version_manager.get_baseline(active_version)
        if baseline:
            baseline.requirement_hash = self.asset_manager.get_requirement_hash(active_version)
            self.version_manager._write_baseline(baseline)

        result = {
            "run_id": run_id,
            "version": active_version,
            "status": coordination_result["status"],
            "environment": self.config.network.type,
            "agent_results": coordination_result["agent_results"],
            "summary": {
                **coordination_result["summary"],
                "test_cases_count": len(context.test_cases),
                "execution_results_count": len(context.execution_results),
                "defects_count": len(context.defects),
            },
            "output_files": output_files,
            "milestones": milestone_manager.to_dict(),
        }

        # 保存运行记录
        record_path = output_dir / f"run_{run_id}.json"
        record_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        self.task_manager.save_run_record(run_id, result)

        self._print_result(result)
        return result

    def submit_task(
        self,
        config_path: str,
        version: Optional[str] = None,
        priority: int = 5,
        environment_type: Optional[str] = None,
    ) -> str:
        """提交异步测试任务."""
        active_version = None
        if version:
            active_version = self.prepare_version(version, environment_type=environment_type)
        return self.task_manager.submit(
            config_path=config_path,
            version=active_version,
            priority=priority,
            network_type=environment_type or self.config.network.type,
        )

    def list_versions(self) -> List[Dict[str, Any]]:
        """列出所有版本及状态."""
        versions = []
        for v in self.version_manager.list_versions():
            info = self.version_manager.get_version_info(v)
            baseline = self.version_manager.get_baseline(v)
            versions.append({
                "version": v,
                "status": info.status if info else "unknown",
                "created_at": info.created_at if info else "",
                "baseline": baseline.to_dict() if baseline else None,
            })
        return versions

    def promote_version(self, version: str, to_status: str, notes: str = "") -> bool:
        """推进版本状态."""
        return self.version_manager.promote(version, to_status, notes)

    def compare_versions(self, from_version: str, to_version: str) -> Dict[str, Any]:
        """对比两个版本."""
        return self.version_manager.compare_versions(from_version, to_version)

    def get_version_assets(self, version: Optional[str] = None) -> Dict[str, Any]:
        """获取版本资产报告."""
        return self.asset_manager.generate_asset_report(version)

    def list_tasks(
        self,
        status: Optional[str] = None,
        version: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """列出任务."""
        tasks = self.task_manager.list_tasks(status=status, version=version, limit=limit)
        return [t.to_dict() for t in tasks]

    def get_task_summary(self) -> Dict[str, Any]:
        return self.task_manager.get_summary()

    def cancel_task(self, task_id: str) -> bool:
        return self.task_manager.cancel(task_id)

    def retry_task(self, task_id: str) -> Optional[str]:
        return self.task_manager.retry(task_id)

    def _generate_run_id(self) -> str:
        return f"RUN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"

    def _save_run_outputs(self, context: WorkflowContext, output_dir: Path, run_id: str) -> Dict[str, str]:
        formatter = OutputFormatter(self.config.base_dir)
        files = {}

        test_case_rows = self._format_test_cases(context.test_cases)
        if test_case_rows:
            files["test_cases_csv"] = formatter.save_csv(test_case_rows, str(output_dir / "test_cases.csv"))
            files["test_cases_excel"] = formatter.save_excel(test_case_rows, str(output_dir / "test_cases.xlsx"), "测试用例")

        defect_rows = self._format_defects(context.defects)
        if defect_rows:
            files["defects_csv"] = formatter.save_csv(defect_rows, str(output_dir / "defects.csv"))
            files["defects_excel"] = formatter.save_excel(defect_rows, str(output_dir / "defects.xlsx"), "缺陷")

        report_path = formatter.save_html_report(context, str(output_dir / "test_report.html"))
        files["report"] = report_path

        results_path = output_dir / "results.json"
        results_path.write_text(json.dumps({
            "run_id": run_id,
            "test_cases": context.test_cases,
            "execution_results": context.execution_results,
            "defects": context.defects,
            "metadata": context.metadata,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        files["results"] = str(results_path.relative_to(self.config.base_dir))

        return files

    def _format_test_cases(self, test_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows = []
        for tc in test_cases:
            rows.append({
                "用例ID": tc.get("id", ""),
                "用例名称": tc.get("name", ""),
                "用例类型": tc.get("type", ""),
                "所属模块": tc.get("module", ""),
                "优先级": tc.get("priority", ""),
                "前置条件": "; ".join(tc.get("preconditions", [])),
                "测试步骤": "; ".join(tc.get("test_steps", [])),
                "预期结果": tc.get("expected_result", ""),
                "测试数据": json.dumps(tc.get("action", tc.get("test_data", {})), ensure_ascii=False),
                "标签": ", ".join(tc.get("tags", [])),
            })
        return rows

    def _format_defects(self, defects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows = []
        for d in defects:
            rows.append({
                "缺陷ID": d.get("id", ""),
                "缺陷标题": d.get("title", ""),
                "严重程度": d.get("severity", ""),
                "优先级": d.get("priority", ""),
                "缺陷状态": d.get("status", ""),
                "缺陷类型": d.get("type", ""),
                "所属模块": d.get("module", ""),
                "关联用例": d.get("test_id", ""),
                "描述": d.get("description", ""),
                "复现步骤": "; ".join(d.get("steps_to_reproduce", [])),
                "实际结果": d.get("actual_result", ""),
                "预期结果": d.get("expected_result", ""),
                "根本原因": d.get("root_cause", ""),
                "建议修复": d.get("suggested_fix", ""),
                "创建时间": d.get("created_at", ""),
                "标签": ", ".join(d.get("tags", [])),
            })
        return rows

    def _on_agent_event(self, reporter: ProgressReporter, event: str, data: Dict[str, Any]):
        if event == "agent_started":
            reporter.update(message=f"🤖 [{data.get('role')}] {data.get('agent')} 开始工作")
        elif event == "agent_finished":
            status = "✅" if data.get("status") == "success" else "❌"
            reporter.update(message=f"{status} [{data.get('role')}] {data.get('agent_name')} 完成")

    def _print_result(self, result: Dict[str, Any]):
        print(f"\n{'=' * 60}")
        print("📊 测试执行完成")
        print(f"{'=' * 60}")
        summary = result["summary"]
        print(f"🤖 参与 Agent: {summary['total_agents']} 个")
        print(f"✅ 成功: {summary['success']} | ❌ 失败: {summary['failed']}")
        print(f"📝 生成用例: {summary['test_cases_count']} 条")
        print(f"🔍 执行结果: {summary['execution_results_count']} 条")
        print(f"🐛 发现缺陷: {summary['defects_count']} 个")
        print("\n📄 输出文件:")
        for name, path in result["output_files"].items():
            print(f"   - {name}: {path}")
        print(f"{'=' * 60}\n")
