"""
proDemoA 全链路自动化测试平台
只需提供需求文档、数据库信息和代码仓库地址，即可自动完成全链路测试
"""

import json
import uuid
import os
from datetime import datetime
from pathlib import Path

from workflow.engine import WorkflowEngine, WorkflowContext, create_workflow
from agents.requirement_analyzer import RequirementAnalyzer
from agents.code_parser import CodeParser
from agents.test_generator import TestGenerator
from agents.test_executor import TestExecutor
from agents.defect_detector import DefectDetector
from agents.report_generator import ReportGenerator


class AutomationTestPlatform:
    """全链路自动化测试平台主类"""
    
    def __init__(self, config_path: str = "automation/config/config.json"):
        self.config = self._load_config(config_path)
        self.workflow = create_workflow(self.config)
        
    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def run(self, input_data: dict) -> dict:
        """
        运行全链路自动化测试
        
        Args:
            input_data: 输入数据，包含需求文档、数据库信息、代码仓库地址等
            
        Returns:
            dict: 测试结果，包含测试用例、缺陷清单、测试报告等
        """
        run_id = f"RUN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        
        print(f"\n{'='*60}")
        print(f"🚀 proDemoA 全链路自动化测试平台")
        print(f"{'='*60}")
        print(f"📋 运行ID: {run_id}")
        print(f"📅 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        project_info = {
            "run_id": run_id,
            "project_name": input_data.get("project_name", "未命名项目"),
            "project_code": input_data.get("project_code", ""),
            "test_type": input_data.get("test_type", "功能测试"),
            "test_environment": input_data.get("test_environment", "test"),
            "start_time": datetime.now().isoformat()
        }
        
        context = WorkflowContext(
            run_id=run_id,
            project_info=project_info,
            requirement_doc=input_data.get("requirement_doc", ""),
            database_schema=input_data.get("database_schema", {}),
            code_info=input_data.get("code_info", {})
        )
        
        results = self.workflow.run(context)
        
        print(f"\n{'='*60}")
        print(f"✅ 测试执行完成")
        print(f"{'='*60}")
        print(f"📊 总任务数: {results['summary']['total_tasks']}")
        print(f"✅ 完成: {results['summary']['completed']}")
        print(f"❌ 失败: {results['summary']['failed']}")
        print(f"⏱️  总耗时: {results['summary']['total_duration']:.2f}秒")
        print(f"📝 测试用例数: {results['summary']['test_cases_count']}")
        print(f"🐛 缺陷数: {results['summary']['defects_count']}")
        print(f"{'='*60}\n")
        
        output_info = {
            "run_id": run_id,
            "status": results['status'],
            "test_cases": context.test_cases,
            "defects": context.defects,
            "execution_results": context.execution_results,
            "report_path": context.metadata.get("report_path", "output/test_report.html"),
            "output_files": {
                "test_cases": "output/test_cases.csv",
                "defects": "output/defects.csv",
                "report": "output/test_report.html"
            },
            "summary": results['summary']
        }
        
        self._save_results(output_info)
        
        return output_info
    
    def _save_results(self, results: dict):
        """保存结果到文件"""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        results_file = f"output/results_{results['run_id']}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"📁 结果已保存到: {results_file}")


def run_automation_test(
    project_name: str,
    requirement_doc: str = "",
    database_schema: dict = None,
    code_info: dict = None,
    project_code: str = "",
    test_type: str = "功能测试",
    test_environment: str = "test"
) -> dict:
    """
    快速运行自动化测试的便捷函数
    
    Args:
        project_name: 项目名称
        requirement_doc: 需求文档内容
        database_schema: 数据库结构信息
        code_info: 代码仓库信息
        project_code: 项目代码
        test_type: 测试类型
        test_environment: 测试环境
        
    Returns:
        dict: 测试结果
    """
    platform = AutomationTestPlatform()
    
    input_data = {
        "project_name": project_name,
        "project_code": project_code,
        "test_type": test_type,
        "test_environment": test_environment,
        "requirement_doc": requirement_doc,
        "database_schema": database_schema or {},
        "code_info": code_info or {}
    }
    
    return platform.run(input_data)


def main():
    """主入口函数"""
    import sys
    
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║         proDemoA 全链路自动化测试平台                    ║
    ║                                                          ║
    ║  输入：需求文档 + 数据库信息 + 代码仓库地址               ║
    ║  输出：测试用例 + 缺陷清单 + 测试报告                    ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        if os.path.exists(input_file):
            with open(input_file, 'r', encoding='utf-8') as f:
                input_data = json.load(f)
        else:
            print(f"❌ 输入文件不存在: {input_file}")
            return
    else:
        input_data = {
            "project_name": "演示项目",
            "project_code": "DEMO-001",
            "test_type": "功能测试",
            "test_environment": "test"
        }
    
    platform = AutomationTestPlatform()
    results = platform.run(input_data)
    
    print("\n📊 测试结果摘要:")
    print(f"   - 测试用例总数: {results['summary']['test_cases_count']}")
    print(f"   - 缺陷总数: {results['summary']['defects_count']}")
    print(f"   - 报告路径: {results['report_path']}")


if __name__ == "__main__":
    main()
