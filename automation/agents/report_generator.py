# -*- coding: utf-8 -*-
"""报告生成 Agent：输出 CSV/JSON/HTML/Excel 多格式报告."""

import json
from typing import Dict, List

from automation.core.output import OutputFormatter
from automation.core.utils import calculate_pass_rate

from .base import BaseAgent


class ReportGenerator(BaseAgent):
    def execute(self, task, context) -> Dict:
        formatter = OutputFormatter(self.config.base_dir)
        test_cases = getattr(context, "test_cases", []) or []
        execution_results = getattr(context, "execution_results", []) or []
        defects = getattr(context, "defects", []) or []

        test_case_rows = self._format_test_cases(test_cases)
        defect_rows = self._format_defects(defects)

        output = self.config.output if hasattr(self.config, "output") else None
        if output is None:
            from automation.core.config import OutputConfig
            output = OutputConfig()

        files = {}
        if test_case_rows:
            files["test_cases_csv"] = formatter.save_csv(test_case_rows, output.test_cases_file)
            if output.test_cases_excel:
                files["test_cases_excel"] = formatter.save_excel(test_case_rows, output.test_cases_excel, "测试用例")
        if defect_rows:
            files["defects_csv"] = formatter.save_csv(defect_rows, output.defects_file)
            if output.defects_excel:
                files["defects_excel"] = formatter.save_excel(defect_rows, output.defects_excel, "缺陷")

        report_path = formatter.save_html_report(context, output.report_file)
        files["report"] = report_path

        return {
            "report_path": report_path,
            "output_files": files,
            "test_cases_count": len(test_cases),
            "defects_count": len(defects),
            "summary": {
                "total_test_cases": len(test_cases),
                "total_defects": len(defects),
                "pass_rate": self._calculate_pass_rate(execution_results),
            },
        }

    def _format_test_cases(self, test_cases: List[Dict]) -> List[Dict]:
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

    def _format_defects(self, defects: List[Dict]) -> List[Dict]:
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

    def _calculate_pass_rate(self, execution_results: List[Dict]) -> float:
        return calculate_pass_rate(execution_results, passed_status="passed")
