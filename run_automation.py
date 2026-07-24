#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""智测 全链路自动化测试平台 - 主入口.

用法:
    python run_automation.py [--config config/project_config.py] [--version v1.0.0]
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

script_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(script_dir))

from automation.core.config import (
    OutputConfig,
    PlatformConfig,
    load_config,
    merge_with_framework_config,
)
from automation.core.monitoring import ProgressReporter
from automation.core.output import OutputFormatter
from automation.core.rag import AgentKnowledgeStore
from automation.core.version import VersionManager
from automation.workflow.engine import WorkflowContext, create_workflow


def load_project_config(path: str) -> PlatformConfig:
    project = load_config(path)
    return merge_with_framework_config(project)


def load_knowledge_store(enabled: bool = True):
    """可选加载 Agent 专家知识库."""
    if not enabled:
        return None
    try:
        store = AgentKnowledgeStore()
        count = store.load()
        print(f"📚 已加载 {count} 个专家知识文档到 RAG 库")
        return store
    except Exception as e:
        print(f"⚠️  加载知识库失败: {e}")
        return None


class AutomationTestPlatform:
    """智测 全链路自动化测试平台主类."""

    def __init__(self, config_path: str = "config/project_config.py", use_knowledge: bool = True):
        self.config_path = config_path
        self.config = load_project_config(config_path)
        self.knowledge_store = load_knowledge_store(use_knowledge)
        self.version_manager: Optional[VersionManager] = None

    def _resolve_version(self, version: Optional[str]) -> Optional[str]:
        """确定本次运行使用的版本号."""
        if version:
            return version
        if self.config.version.enabled and self.config.version.current_version:
            return self.config.version.current_version
        return None

    def _prepare_version_environment(self, version: Optional[str]) -> Optional[str]:
        """初始化版本管理器并返回实际使用的版本号."""
        version = self._resolve_version(version)
        if not version and not self.config.version.enabled:
            return None

        self.version_manager = VersionManager(
            self.config.base_dir / self.config.version.base_dir,
            current_version=version,
        )
        resolved = version or self.version_manager.current_version
        if resolved and resolved not in self.version_manager.list_versions():
            if self.config.version.auto_create:
                print(f"🆕 自动创建新版本: {resolved}")
                self.version_manager.create_version(resolved, description=f"创建于 {datetime.now().isoformat()}")
            else:
                raise FileNotFoundError(f"版本不存在且未开启自动创建: {resolved}")
        if resolved:
            self.version_manager.set_current(resolved)
        return resolved

    def _load_requirement_doc(self, version: Optional[str]) -> str:
        """加载需求文档：优先版本目录，回退全局配置."""
        if self.version_manager and version:
            req_path = self.version_manager.requirement_path(version)
            if req_path.exists():
                return req_path.read_text(encoding="utf-8")
            print(f"⚠️  版本需求文档不存在，回退到全局配置: {req_path}")
        return self.config.requirement.load_text(self.config.base_dir)

    def _build_versioned_output_config(self, version: Optional[str]) -> OutputConfig:
        """构建版本化输出路径配置."""
        if not self.version_manager or not version:
            return self.config.output

        output_dir = self.version_manager.output_dir(version)
        output_dir.mkdir(parents=True, exist_ok=True)
        return OutputConfig(
            test_cases_file=str(output_dir / "test_cases.csv"),
            defects_file=str(output_dir / "defects.csv"),
            report_file=str(output_dir / "test_report.html"),
            results_file=str(output_dir / "results.json"),
            test_cases_excel=str(output_dir / "test_cases.xlsx"),
            defects_excel=str(output_dir / "defects.xlsx"),
        )

    def prepare_input_data(self, version: Optional[str] = None) -> Dict:
        return {
            "project_name": self.config.project.name,
            "project_code": self.config.project.code,
            "test_type": self.config.project.test_type,
            "test_environment": self.config.project.environment,
            "requirement_doc": self._load_requirement_doc(version),
            "database_schema": self.config.database.model_dump() if self.config.database else {},
            "code_info": {},
            "version": version,
        }

    def run(self, version: Optional[str] = None, input_data: Optional[Dict] = None) -> Dict:
        active_version = self._prepare_version_environment(version)
        if active_version:
            print(f"📌 当前版本: {active_version}")

        if input_data is None:
            input_data = self.prepare_input_data(active_version)

        # 使用版本化输出配置运行工作流
        original_output = self.config.output
        self.config.output = self._build_versioned_output_config(active_version)

        run_id = f"RUN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        project_info = {
            "run_id": run_id,
            "project_name": input_data.get("project_name", "未命名项目"),
            "project_code": input_data.get("project_code", ""),
            "test_type": input_data.get("test_type", "功能测试"),
            "test_environment": input_data.get("test_environment", "test"),
            "version": active_version,
            "start_time": datetime.now().isoformat(),
        }

        self._print_start(project_info, run_id, active_version)

        try:
            progress = ProgressReporter(total_steps=6, enable_terminal=True)
            workflow = create_workflow(
                self.config,
                knowledge_store=self.knowledge_store,
                max_workers=getattr(getattr(self.config, "workflow", None), "max_workers", 4),
                progress_reporter=progress,
            )
            context = WorkflowContext(
                run_id=run_id,
                project_info=project_info,
                requirement_doc=input_data.get("requirement_doc", ""),
                database_schema=input_data.get("database_schema", {}),
                code_info=input_data.get("code_info", {}),
                metadata={"version": active_version} if active_version else {},
            )

            results = workflow.run(context)
            self._print_summary(results)

            output_info = {
                "run_id": run_id,
                "version": active_version,
                "status": results["status"],
                "test_cases": context.test_cases,
                "defects": context.defects,
                "execution_results": context.execution_results,
                "report_path": context.metadata.get("report_path", self.config.output.report_file),
                "output_files": context.metadata.get("output_files", {}),
                "summary": results["summary"],
            }

            self._save_results(output_info)
            self._print_output_files(output_info)
            return output_info
        finally:
            self.config.output = original_output

    def _print_start(self, project_info: Dict, run_id: str, version: Optional[str]):
        print(f"\n{'=' * 60}")
        print("🚀 智测 全链路自动化测试平台")
        print(f"{'=' * 60}")
        print(f"📋 项目名称: {project_info['project_name']}")
        print(f"📋 项目代码: {project_info['project_code']}")
        print(f"📋 测试类型: {project_info['test_type']}")
        if version:
            print(f"🏷️  版本: {version}")
        print(f"📋 运行ID: {run_id}")
        print(f"📅 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 60}\n")

    def _print_summary(self, results: dict):
        summary = results["summary"]
        print(f"\n{'=' * 60}")
        print("✅ 测试执行完成")
        print(f"{'=' * 60}")
        print(f"📊 总任务数: {summary['total_tasks']}")
        print(f"✅ 完成: {summary['completed']}")
        print(f"❌ 失败: {summary['failed']}")
        print(f"⏱️  总耗时: {summary['total_duration']:.2f}秒")
        print(f"📝 测试用例数: {summary['test_cases_count']}")
        print(f"🐛 缺陷数: {summary['defects_count']}")

        milestones = summary.get("milestones")
        if milestones:
            print(f"\n🎯 里程碑进度: {milestones['completed']}/{milestones['total_milestones']} 完成")
            print(f"⚠️  未关闭风险: {milestones['open_risks']} 个")
            if milestones.get("critical_risks"):
                print("🔴 存在严重风险，建议立即处理")

        risks = summary.get("risks", {}).get("risks", [])
        open_risks = [r for r in risks if r.get("status") == "open"]
        if open_risks:
            print("\n📋 当前已知风险:")
            for risk in open_risks[:5]:
                icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
                    risk.get("level"), "⚪"
                )
                print(f"   {icon} [{risk.get('level').upper()}] {risk.get('description')}")
                if risk.get("mitigation"):
                    print(f"      缓解措施: {risk.get('mitigation')}")

        print(f"{'=' * 60}\n")

    def _save_results(self, results: dict):
        formatter = OutputFormatter(self.config.base_dir)
        formatter.save_json(results, self.config.output.results_file)
        print("📁 结果已保存")

    def _print_output_files(self, results: dict):
        print("📄 输出文件:")
        for name, path in results.get("output_files", {}).items():
            full_path = self.config.base_dir / path
            if full_path.exists():
                size = full_path.stat().st_size
                print(f"   - {name}: {path} ({size} bytes)")


def main():
    parser = argparse.ArgumentParser(description="智测 全链路自动化测试平台")
    parser.add_argument("--config", default="config/project_config.py", help="配置文件路径")
    parser.add_argument("--version", default=None, help="指定版本号，例如 v1.0.0")
    parser.add_argument("--create-version", default=None, help="仅创建新版本并写入需求文档（需配合 --requirement）")
    parser.add_argument("--requirement", default=None, help="创建版本时使用的外部需求文档路径")
    parser.add_argument("--compare", nargs=2, metavar=("FROM", "TO"), help="对比两个版本，例如 --compare v1.0.0 v1.1.0")
    args = parser.parse_args()

    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║         智测 全链路自动化测试平台                        ║
    ║                                                          ║
    ║  配置: config/project_config.py                          ║
    ║  运行: python run_automation.py --version v1.0.0        ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    try:
        platform = AutomationTestPlatform(config_path=args.config)

        if args.compare:
            vm = VersionManager(
                platform.config.base_dir / platform.config.version.base_dir,
                current_version=platform.config.version.current_version or None,
            )
            diff = vm.compare_versions(args.compare[0], args.compare[1])
            print(json.dumps(diff, ensure_ascii=False, indent=2))
            return

        if args.create_version:
            vm = VersionManager(
                platform.config.base_dir / platform.config.version.base_dir,
                current_version=platform.config.version.current_version or None,
            )
            req_text = ""
            if args.requirement and Path(args.requirement).exists():
                req_text = Path(args.requirement).read_text(encoding="utf-8")
            vm.create_version(args.create_version, requirement_text=req_text)
            print(f"✅ 已创建版本 {args.create_version}")
            print(f"📁 版本目录: {vm.version_dir(args.create_version)}")
            return

        results = platform.run(version=args.version)

        print("\n" + "=" * 60)
        print("📊 测试结果摘要")
        print("=" * 60)
        print(f"   测试用例总数: {results['summary']['test_cases_count']}")
        print(f"   缺陷总数: {results['summary']['defects_count']}")
        if results.get("version"):
            print(f"   版本: {results['version']}")

    except FileNotFoundError as e:
        print(f"\n❌ 错误: {e}")
        print("\n请确保配置文件存在: config/project_config.py")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 执行错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
