#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""aiAgent 全链路自动化测试平台 - 主入口.

用法:
    python run_automation.py [--config config/project_config.py]
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

script_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(script_dir))

from automation.core.config import PlatformConfig, load_config, merge_with_framework_config
from automation.core.output import OutputFormatter
from automation.core.rag import AgentKnowledgeStore
from automation.workflow.engine import WorkflowContext, create_workflow


def load_project_config(path: str) -> PlatformConfig:
    project = load_config(path)
    return merge_with_framework_config(project)


def prepare_input_data(config: PlatformConfig) -> dict:
    return {
        "project_name": config.project.name,
        "project_code": config.project.code,
        "test_type": config.project.test_type,
        "test_environment": config.project.environment,
        "requirement_doc": config.requirement.load_text(config.base_dir),
        "database_schema": config.database.model_dump() if config.database else {},
        "code_info": {},
    }


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
    """全链路自动化测试平台主类."""

    def __init__(self, config_path: str = "config/project_config.py", use_knowledge: bool = True):
        self.config = load_project_config(config_path)
        self.knowledge_store = load_knowledge_store(use_knowledge)
        self.workflow = create_workflow(self.config, knowledge_store=self.knowledge_store)
        self.output_dir = self.config.base_dir / "output"
        self.output_dir.mkdir(exist_ok=True)

    def run(self, input_data: dict = None) -> dict:
        if input_data is None:
            input_data = prepare_input_data(self.config)

        run_id = f"RUN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        project_info = {
            "run_id": run_id,
            "project_name": input_data.get("project_name", "未命名项目"),
            "project_code": input_data.get("project_code", ""),
            "test_type": input_data.get("test_type", "功能测试"),
            "test_environment": input_data.get("test_environment", "test"),
            "start_time": datetime.now().isoformat(),
        }

        self._print_start(project_info, run_id)

        context = WorkflowContext(
            run_id=run_id,
            project_info=project_info,
            requirement_doc=input_data.get("requirement_doc", ""),
            database_schema=input_data.get("database_schema", {}),
            code_info=input_data.get("code_info", {}),
        )

        results = self.workflow.run(context)
        self._print_summary(results)

        output_info = {
            "run_id": run_id,
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

    def _print_start(self, project_info: dict, run_id: str):
        print(f"\n{'=' * 60}")
        print("🚀 aiAgent 全链路自动化测试平台")
        print(f"{'=' * 60}")
        print(f"📋 项目名称: {project_info['project_name']}")
        print(f"📋 项目代码: {project_info['project_code']}")
        print(f"📋 测试类型: {project_info['test_type']}")
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
    parser = argparse.ArgumentParser(description="aiAgent 全链路自动化测试平台")
    parser.add_argument("--config", default="config/project_config.py", help="配置文件路径")
    args = parser.parse_args()

    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║         aiAgent 全链路自动化测试平台                   ║
    ║                                                          ║
    ║  配置: config/project_config.py                          ║
    ║  运行: python run_automation.py                         ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    try:
        platform = AutomationTestPlatform(config_path=args.config)
        results = platform.run()

        print("\n" + "=" * 60)
        print("📊 测试结果摘要")
        print("=" * 60)
        print(f"   测试用例总数: {results['summary']['test_cases_count']}")
        print(f"   缺陷总数: {results['summary']['defects_count']}")

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
