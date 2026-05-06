import re
import json
from typing import Dict, List, Any
from datetime import datetime


class RequirementAnalyzer:
    """需求分析Agent - 解析需求文档，提取测试要点"""

    def __init__(self, config: Dict):
        self.config = config
        self.requirements = []
        self.test_points = []
        self.acceptance_criteria = []

    def execute(self, task, context) -> Dict:
        """执行需求分析"""
        requirement_doc = context.requirement_doc or self._load_requirement_doc(context)

        self._parse_requirement(requirement_doc)
        self._extract_test_points()
        self._extract_acceptance_criteria()

        return {
            "requirement_doc": requirement_doc,
            "requirements": self.requirements,
            "test_points": self.test_points,
            "acceptance_criteria": self.acceptance_criteria,
            "summary": {
                "total_requirements": len(self.requirements),
                "total_test_points": len(self.test_points),
                "total_criteria": len(self.acceptance_criteria)
            }
        }

    def _load_requirement_doc(self, context) -> str:
        """从上下文加载需求文档"""
        return context.project_info.get("requirement_doc", "")

    def _parse_requirement(self, doc: str):
        """解析需求文档"""
        if not doc:
            self.requirements = self._generate_sample_requirements()
            return

        lines = doc.split('\n')
        current_req = None

        for line in lines:
            line = line.strip()

            if line.startswith('#') or line.startswith('##'):
                continue

            req_match = re.match(r'(?:REQ|需求|功能)[-：:\s]*(\d+)', line, re.IGNORECASE)
            if req_match:
                if current_req:
                    self.requirements.append(current_req)
                current_req = {
                    "id": f"REQ-{req_match.group(1)}",
                    "title": line,
                    "description": "",
                    "priority": "medium",
                    "test_type": "functional"
                }
            elif current_req and line:
                current_req["description"] += line + " "

        if current_req:
            self.requirements.append(current_req)

    def _generate_sample_requirements(self) -> List[Dict]:
        """生成示例需求"""
        return [
            {
                "id": "REQ-001",
                "title": "用户登录功能",
                "description": "用户可以通过用户名密码登录系统",
                "priority": "high",
                "test_type": "functional"
            },
            {
                "id": "REQ-002", 
                "title": "用户注册功能",
                "description": "新用户可以注册账号",
                "priority": "high",
                "test_type": "functional"
            },
            {
                "id": "REQ-003",
                "title": "数据查询功能",
                "description": "用户可以查询业务数据",
                "priority": "medium",
                "test_type": "functional"
            }
        ]

    def _extract_test_points(self):
        """提取测试要点"""
        test_point_mapping = {
            "high": ["功能正确性", "边界条件", "异常处理", "安全性"],
            "medium": ["性能", "可用性", "兼容性"],
            "low": ["可维护性", "可扩展性"]
        }

        for req in self.requirements:
            priority = req.get("priority", "medium")
            points = test_point_mapping.get(priority, test_point_mapping["medium"])

            for point in points:
                self.test_points.append({
                    "req_id": req["id"],
                    "test_point": point,
                    "priority": priority
                })

    def _extract_acceptance_criteria(self):
        """提取验收标准"""
        for req in self.requirements:
            self.acceptance_criteria.append({
                "req_id": req["id"],
                "criteria": [
                    f"{req['title']}功能正常工作",
                    f"{req['title']}错误提示信息正确",
                    f"{req['title']}响应时间满足要求"
                ]
            })

    def _call_llm(self, prompt: str) -> str:
        """调用LLM接口（预留）"""
        return ""


def extract_requirements_from_markdown(markdown_text: str) -> List[Dict]:
    """从Markdown提取需求"""
    analyzer = RequirementAnalyzer({})
    analyzer._parse_requirement(markdown_text)
    return analyzer.requirements


def extract_requirements_from_docx(docx_path: str) -> List[Dict]:
    """从Word文档提取需求"""
    return []


def extract_requirements_from_pdf(pdf_path: str) -> List[Dict]:
    """从PDF提取需求"""
    return []
