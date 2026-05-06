#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
proDemoA 全链路自动化测试平台 - 主入口

使用方法:
    python run_automation.py

测试人员只需修改 config/project_config.py 文件即可开始测试
"""

import json
import uuid
import os
import sys
from datetime import datetime
from pathlib import Path

# 确保可以导入automation模块
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
sys.path.insert(0, os.path.join(script_dir, 'automation'))

from workflow.engine import WorkflowEngine, WorkflowContext, create_workflow


def load_project_config():
    """加载项目配置文件"""
    config_file = os.path.join(script_dir, 'config', 'project_config.py')
    
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"配置文件不存在: {config_file}")
    
    import importlib.util
    spec = importlib.util.spec_from_file_location("project_config", config_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    return module.PROJECT_CONFIG


def load_requirement_doc(config):
    """加载需求文档"""
    # 优先从文件读取
    if config.get("requirement_doc_path"):
        doc_path = os.path.join(script_dir, config["requirement_doc_path"])
        if os.path.exists(doc_path):
            with open(doc_path, 'r', encoding='utf-8') as f:
                return f.read()
    
    # 其次使用直接填写的内容
    if config.get("requirement_doc"):
        return config["requirement_doc"]
    
    return ""


def prepare_input_data(config):
    """准备输入数据"""
    # 加载需求文档
    requirement_doc = load_requirement_doc(config)
    
    # 准备数据库结构
    database_schema = {}
    if config.get("database", {}).get("enabled"):
        db_config = config["database"]
        database_schema = {
            "type": db_config.get("type", "mysql"),
            "host": db_config.get("host", "localhost"),
            "port": db_config.get("port", 3306),
            "database": db_config.get("database", ""),
            "tables": db_config.get("tables", [])
        }
    
    # 准备代码仓库信息
    code_info = {"frontend": {}, "backend": {}}
    
    if config.get("frontend_repo", {}).get("enabled"):
        code_info["frontend"] = config["frontend_repo"]
    
    if config.get("backend_repo", {}).get("enabled"):
        code_info["backend"] = config["backend_repo"]
    
    return {
        "project_name": config.get("project_name", "未命名项目"),
        "project_code": config.get("project_code", ""),
        "test_type": config.get("test_type", "功能测试"),
        "test_environment": config.get("test_environment", "test"),
        "requirement_doc": requirement_doc,
        "database_schema": database_schema,
        "code_info": code_info
    }


def ensure_output_dir():
    """确保输出目录存在"""
    output_dir = Path(os.path.join(script_dir, 'output'))
    output_dir.mkdir(exist_ok=True)
    return output_dir


class AutomationTestPlatform:
    """全链路自动化测试平台主类"""
    
    def __init__(self):
        self.config = load_project_config()
        self.workflow = create_workflow(self.config)
        self.output_dir = ensure_output_dir()
        
    def run(self, input_data: dict = None) -> dict:
        """运行全链路自动化测试"""
        if input_data is None:
            input_data = prepare_input_data(self.config)
        
        run_id = f"RUN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        
        print(f"\n{'='*60}")
        print(f"🚀 proDemoA 全链路自动化测试平台")
        print(f"{'='*60}")
        print(f"📋 项目名称: {input_data.get('project_name', 'N/A')}")
        print(f"📋 项目代码: {input_data.get('project_code', 'N/A')}")
        print(f"📋 测试类型: {input_data.get('test_type', 'N/A')}")
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
        
        output_files = self.config.get("output", {})
        
        output_info = {
            "run_id": run_id,
            "status": results['status'],
            "test_cases": context.test_cases,
            "defects": context.defects,
            "execution_results": context.execution_results,
            "report_path": context.metadata.get("report_path", output_files.get("report_file", "output/test_report.html")),
            "output_files": {
                "test_cases": output_files.get("test_cases_file", "output/test_cases.csv"),
                "defects": output_files.get("defects_file", "output/defects.csv"),
                "report": output_files.get("report_file", "output/test_report.html")
            },
            "summary": results['summary']
        }
        
        self._save_results(output_info)
        self._print_output_files(output_info)
        
        return output_info
    
    def _save_results(self, results: dict):
        """保存结果到文件"""
        output_files = self.config.get("output", {})
        
        results_file = os.path.join(script_dir, output_files.get("results_file", "output/results.json"))
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"📁 结果已保存")
    
    def _print_output_files(self, results: dict):
        """打印输出文件信息"""
        print("📄 输出文件:")
        for name, path in results.get("output_files", {}).items():
            full_path = os.path.join(script_dir, path)
            if os.path.exists(full_path):
                size = os.path.getsize(full_path)
                print(f"   - {name}: {path} ({size} bytes)")


def main():
    """主入口函数"""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║         proDemoA 全链路自动化测试平台                    ║
    ║                                                          ║
    ║  配置: config/project_config.py                          ║
    ║  运行: python run_automation.py                         ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    try:
        platform = AutomationTestPlatform()
        results = platform.run()
        
        print("\n" + "="*60)
        print("📊 测试结果摘要")
        print("="*60)
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
