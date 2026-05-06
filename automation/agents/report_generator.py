import os
import json
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path


class ReportGenerator:
    """测试报告生成Agent - 生成测试报告和缺陷清单"""

    def __init__(self, config: Dict):
        self.config = config
        self.report_path = ""

    def execute(self, task, context) -> Dict:
        """执行报告生成"""
        test_cases = context.test_cases or []
        execution_results = context.execution_results or []
        defects = context.defects or []

        self._generate_test_case_output(test_cases)
        self._generate_defect_output(defects)
        report_path = self._generate_html_report(context)

        return {
            "report_path": report_path,
            "test_cases_count": len(test_cases),
            "defects_count": len(defects),
            "summary": {
                "total_test_cases": len(test_cases),
                "total_defects": len(defects),
                "pass_rate": self._calculate_pass_rate(execution_results)
            }
        }

    def _generate_test_case_output(self, test_cases: List[Dict]):
        """生成测试用例输出"""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        test_case_data = []
        for tc in test_cases:
            test_case_data.append({
                "用例ID": tc.get("id", ""),
                "用例名称": tc.get("name", ""),
                "用例类型": tc.get("type", ""),
                "所属模块": tc.get("module", ""),
                "优先级": tc.get("priority", ""),
                "前置条件": "; ".join(tc.get("preconditions", [])),
                "测试步骤": "; ".join(tc.get("test_steps", [])),
                "预期结果": tc.get("expected_result", ""),
                "测试数据": json.dumps(tc.get("test_data", {}), ensure_ascii=False),
                "标签": ", ".join(tc.get("tags", []))
            })

        with open("output/test_cases.csv", "w", encoding="utf-8-sig") as f:
            if test_case_data:
                headers = list(test_case_data[0].keys())
                f.write(",".join(headers) + "\n")
                for row in test_case_data:
                    values = [str(row.get(h, "")) for h in headers]
                    f.write(",".join(values) + "\n")

    def _generate_defect_output(self, defects: List[Dict]):
        """生成缺陷清单输出"""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        defect_data = []
        for defect in defects:
            defect_data.append({
                "缺陷ID": defect.get("id", ""),
                "缺陷标题": defect.get("title", ""),
                "严重程度": defect.get("severity", ""),
                "优先级": defect.get("priority", ""),
                "缺陷状态": defect.get("status", ""),
                "缺陷类型": defect.get("type", ""),
                "所属模块": defect.get("module", ""),
                "关联用例": defect.get("test_id", ""),
                "描述": defect.get("description", ""),
                "复现步骤": "; ".join(defect.get("steps_to_reproduce", [])),
                "实际结果": defect.get("actual_result", ""),
                "预期结果": defect.get("expected_result", ""),
                "根本原因": defect.get("root_cause", ""),
                "建议修复": defect.get("suggested_fix", ""),
                "创建时间": defect.get("created_at", ""),
                "标签": ", ".join(defect.get("tags", []))
            })

        with open("output/defects.csv", "w", encoding="utf-8-sig") as f:
            if defect_data:
                headers = list(defect_data[0].keys())
                f.write(",".join(headers) + "\n")
                for row in defect_data:
                    values = [str(row.get(h, "")) for h in headers]
                    f.write(",".join(values) + "\n")

    def _generate_html_report(self, context) -> str:
        """生成HTML测试报告"""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        report_path = "output/test_report.html"
        
        pass_rate = self._calculate_pass_rate(context.execution_results)
        
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试报告 - {context.project_info.get('project_name', '项目')}</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin: 20px 0;
        }}
        .summary-card {{
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .summary-card.total {{
            background-color: #e3f2fd;
        }}
        .summary-card.pass {{
            background-color: #e8f5e9;
        }}
        .summary-card.fail {{
            background-color: #ffebee;
        }}
        .summary-card.rate {{
            background-color: #fff3e0;
        }}
        .summary-card .number {{
            font-size: 36px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .summary-card.total .number {{
            color: #1976d2;
        }}
        .summary-card.pass .number {{
            color: #388e3c;
        }}
        .summary-card.fail .number {{
            color: #d32f2f;
        }}
        .summary-card.rate .number {{
            color: #f57c00;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .severity-critical {{
            color: #d32f2f;
            font-weight: bold;
        }}
        .severity-high {{
            color: #f57c00;
            font-weight: bold;
        }}
        .severity-medium {{
            color: #fbc02d;
        }}
        .severity-low {{
            color: #388e3c;
        }}
        .status-passed {{
            color: #388e3c;
        }}
        .status-failed {{
            color: #d32f2f;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #888;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 测试报告</h1>
        <p><strong>项目名称：</strong>{context.project_info.get('project_name', 'N/A')}</p>
        <p><strong>项目代码：</strong>{context.project_info.get('project_code', 'N/A')}</p>
        <p><strong>测试类型：</strong>{context.project_info.get('test_type', '全面测试')}</p>
        <p><strong>生成时间：</strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>📊 测试概览</h2>
        <div class="summary">
            <div class="summary-card total">
                <div>总用例数</div>
                <div class="number">{len(context.test_cases)}</div>
            </div>
            <div class="summary-card pass">
                <div>通过数</div>
                <div class="number">{sum(1 for r in context.execution_results if r.get('status') == 'passed')}</div>
            </div>
            <div class="summary-card fail">
                <div>失败数</div>
                <div class="number">{len(context.defects)}</div>
            </div>
            <div class="summary-card rate">
                <div>通过率</div>
                <div class="number">{pass_rate}%</div>
            </div>
        </div>
        
        <h2>📋 测试用例统计</h2>
        <table>
            <tr>
                <th>类型</th>
                <th>数量</th>
                <th>占比</th>
            </tr>
            {self._generate_type_statistics(context.test_cases)}
        </table>
        
        <h2>🐛 缺陷清单</h2>
        <table>
            <tr>
                <th>ID</th>
                <th>标题</th>
                <th>严重程度</th>
                <th>优先级</th>
                <th>模块</th>
                <th>类型</th>
            </tr>
            {self._generate_defect_table(context.defects)}
        </table>
        
        <h2>📈 缺陷统计</h2>
        <div class="summary">
            <div class="summary-card total">
                <div>缺陷总数</div>
                <div class="number">{len(context.defects)}</div>
            </div>
            {self._generate_defect_summary(context.defects)}
        </div>
        
        <div class="footer">
            <p>报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>proDemoA 全链路自动化测试平台</p>
        </div>
    </div>
</body>
</html>"""

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        self.report_path = report_path
        return report_path

    def _calculate_pass_rate(self, execution_results: List[Dict]) -> float:
        """计算通过率"""
        if not execution_results:
            return 0.0
        passed = sum(1 for r in execution_results if r.get("status") == "passed")
        return round(passed / len(execution_results) * 100, 2)

    def _generate_type_statistics(self, test_cases: List[Dict]) -> str:
        """生成类型统计"""
        type_counts = {}
        for tc in test_cases:
            tc_type = tc.get("type", "Unknown")
            type_counts[tc_type] = type_counts.get(tc_type, 0) + 1

        total = len(test_cases) or 1
        html = ""
        for tc_type, count in type_counts.items():
            percentage = round(count / total * 100, 2)
            html += f"""
            <tr>
                <td>{tc_type}</td>
                <td>{count}</td>
                <td>{percentage}%</td>
            </tr>"""
        return html

    def _generate_defect_table(self, defects: List[Dict]) -> str:
        """生成缺陷表格"""
        if not defects:
            return "<tr><td colspan='6'>暂无缺陷</td></tr>"

        html = ""
        for defect in defects[:20]:
            severity = defect.get("severity", "low")
            html += f"""
            <tr>
                <td>{defect.get('id', '')}</td>
                <td>{defect.get('title', '')}</td>
                <td class='severity-{severity}'>{defect.get('severity', '')}</td>
                <td>{defect.get('priority', '')}</td>
                <td>{defect.get('module', '')}</td>
                <td>{defect.get('type', '')}</td>
            </tr>"""
        return html

    def _generate_defect_summary(self, defects: List[Dict]) -> str:
        """生成缺陷摘要"""
        severity_counts = {}
        for defect in defects:
            severity = defect.get("severity", "low")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        html = ""
        for severity in ["critical", "high", "medium", "low"]:
            count = severity_counts.get(severity, 0)
            html += f"""
            <div class="summary-card {'fail' if severity in ['critical', 'high'] else 'rate'}">
                <div>{severity.capitalize()}</div>
                <div class="number">{count}</div>
            </div>"""
        return html
