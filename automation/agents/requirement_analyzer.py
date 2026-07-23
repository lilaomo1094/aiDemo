# -*- coding: utf-8 -*-
"""需求分析 Agent：解析需求文档，提取测试要点与验收标准."""

import re
from typing import Dict, List

from automation.core.utils import truncate_text

from .base import BaseAgent


class RequirementAnalyzer(BaseAgent):
    SYSTEM_PROMPT = """你是一名资深测试分析师。请基于用户需求文档，提取结构化信息并以 JSON 输出。
输出格式：
{
  "requirements": [
    {"id": "REQ-001", "title": "", "description": "", "priority": "high|medium|low", "test_type": "functional|performance|security|compatibility"}
  ],
  "test_points": [
    {"req_id": "REQ-001", "test_point": "", "priority": "high|medium|low"}
  ],
  "acceptance_criteria": [
    {"req_id": "REQ-001", "criteria": ["", ""]}
  ]
}
只输出 JSON，不要额外解释。"""

    def execute(self, task, context) -> Dict:
        requirement_doc = context.requirement_doc or ""
        if not requirement_doc.strip():
            requirement_doc = self._sample_doc()

        fallback = self._rule_based_parse(requirement_doc)
        llm_result = self._call_llm_json(
            self._build_prompt(requirement_doc),
            system=self._build_system_prompt(self.SYSTEM_PROMPT, query=requirement_doc[:200]),
            fallback=fallback,
        )

        requirements = llm_result.get("requirements") or fallback.get("requirements", [])
        test_points = llm_result.get("test_points") or fallback.get("test_points", [])
        acceptance_criteria = llm_result.get("acceptance_criteria") or fallback.get("acceptance_criteria", [])

        return {
            "requirement_doc": requirement_doc,
            "requirements": requirements,
            "test_points": test_points,
            "acceptance_criteria": acceptance_criteria,
            "summary": {
                "total_requirements": len(requirements),
                "total_test_points": len(test_points),
                "total_criteria": len(acceptance_criteria),
            },
        }

    def _build_prompt(self, doc: str) -> str:
        # 压缩上下文，避免超长需求文档导致 token 爆炸
        max_tokens = self.config.llm.max_tokens if hasattr(self.config, "llm") else 4000
        # 保留约 1/3 的 token 预算给需求文档
        truncated = truncate_text(doc, max_tokens=max_tokens // 3)
        return f"""请分析以下需求文档并提取结构化信息：\n\n{truncated}\n"""

    def _rule_based_parse(self, doc: str) -> Dict:
        requirements = []
        lines = doc.split("\n")
        current = None
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = re.match(r".*\(REQ-(\d+)\).*", line)
            if match:
                if current:
                    requirements.append(current)
                current = {
                    "id": f"REQ-{match.group(1)}",
                    "title": line.replace(f"(REQ-{match.group(1)})", "").strip(" -：:"),
                    "description": "",
                    "priority": "medium",
                    "test_type": "functional",
                }
            elif current and line.startswith("-"):
                current["description"] += line.lstrip("- ").strip() + " "
        if current:
            requirements.append(current)

        if not requirements:
            requirements = self._sample_requirements()

        test_points = []
        acceptance_criteria = []
        for req in requirements:
            for point in self._points_by_priority(req.get("priority", "medium")):
                test_points.append({"req_id": req["id"], "test_point": point, "priority": req.get("priority", "medium")})
            acceptance_criteria.append({
                "req_id": req["id"],
                "criteria": [
                    f"{req['title']} 功能正常工作",
                    f"{req['title']} 错误提示信息正确",
                    f"{req['title']} 响应时间满足要求",
                ],
            })
        return {"requirements": requirements, "test_points": test_points, "acceptance_criteria": acceptance_criteria}

    def _points_by_priority(self, priority: str) -> List[str]:
        mapping = {
            "high": ["功能正确性", "边界条件", "异常处理", "安全性"],
            "medium": ["性能", "可用性", "兼容性"],
            "low": ["可维护性", "可扩展性"],
        }
        return mapping.get(priority, mapping["medium"])

    def _sample_doc(self) -> str:
        return "# 示例需求\n## 1. 用户登录 (REQ-001)\n用户可以通过用户名密码登录系统"

    def _sample_requirements(self) -> List[Dict]:
        return [
            {"id": "REQ-001", "title": "用户登录", "description": "用户可以通过用户名密码登录系统", "priority": "high", "test_type": "functional"},
            {"id": "REQ-002", "title": "用户注册", "description": "新用户可以注册账号", "priority": "high", "test_type": "functional"},
            {"id": "REQ-003", "title": "数据查询", "description": "用户可以查询业务数据", "priority": "medium", "test_type": "functional"},
        ]
