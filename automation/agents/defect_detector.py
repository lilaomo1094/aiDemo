# -*- coding: utf-8 -*-
"""缺陷发现 Agent：基于执行结果识别缺陷并分类."""

from collections import Counter
from datetime import datetime
from typing import Dict, List

from automation.core.utils import calculate_pass_rate, compact_json, count_by, extract_module_from_path, truncate_list

from .base import BaseAgent


class DefectDetector(BaseAgent):
    SYSTEM_PROMPT = """你是一名缺陷分析专家。请根据失败的测试执行结果，分析根本原因并输出 JSON 数组。
每个缺陷字段：
{
  "title": "缺陷标题",
  "description": "缺陷描述",
  "severity": "critical|high|medium|low",
  "type": "functional|authentication|authorization|validation|performance|systemic",
  "module": "所属模块",
  "priority": "P1|P2|P3|P4",
  "root_cause": "根本原因分析",
  "suggested_fix": "修复建议"
}
只输出 JSON 数组，不要额外解释。"""

    def execute(self, task, context) -> Dict:
        execution_results = getattr(context, "execution_results", []) or []
        defects = []

        # 基于 LLM 分析失败结果（压缩上下文避免 token 爆炸）
        failed_results = [r for r in execution_results if r.get("status") in {"failed", "error"}]
        if self.llm and failed_results:
            llm_defects = self._analyze_with_llm(failed_results)
            for d in llm_defects:
                d.setdefault("id", f"DEF-{len(defects) + 1:03d}")
                d.setdefault("test_id", "N/A")
                d.setdefault("test_name", "多个失败用例聚合")
                d.setdefault("status", "new")
                d.setdefault("created_at", datetime.now().isoformat())
                defects.extend(llm_defects)

        # 兜底规则生成
        if not defects:
            defects = self._rule_based_detect(execution_results)

        # 系统性缺陷检测
        defects.extend(self._detect_systemic_issues(defects))

        return {
            "defects": defects,
            "summary": {
                "total_defects": len(defects),
                "by_severity": count_by(defects, "severity"),
                "by_type": count_by(defects, "type"),
                "by_module": count_by(defects, "module"),
                "pass_rate": calculate_pass_rate(execution_results),
            },
        }

    def _analyze_with_llm(self, failed_results: List[Dict]) -> List[Dict]:
        # 只保留关键字段，避免长响应导致 token 过多
        compact_results = truncate_list(
            failed_results,
            max_tokens=1500,
            keep_fields=["test_id", "test_name", "test_type", "status", "error_message", "status_code"],
        )
        prompt = "请分析以下失败的测试执行结果，识别缺陷并给出根因与修复建议：\n\n" + compact_json(compact_results)
        system = self._build_system_prompt(self.SYSTEM_PROMPT, query="缺陷分析 测试失败")
        return self._call_llm_json(prompt, system=system, fallback=[])

    def _rule_based_detect(self, execution_results: List[Dict]) -> List[Dict]:
        defects = []
        for result in execution_results:
            if result.get("status") not in {"failed", "error"}:
                continue
            test_name = result.get("test_name", "")
            test_id = result.get("test_id", "")
            defects.append({
                "id": f"DEF-{len(defects) + 1:03d}",
                "test_id": test_id,
                "test_name": test_name,
                "title": f"测试失败: {test_name}",
                "description": f"执行结果: {result.get('error_message', '未知错误')}",
                "severity": self._determine_severity(test_name),
                "status": "new",
                "type": self._determine_type(test_name),
                "module": extract_module_from_path(test_name),
                "priority": self._determine_priority(test_name),
                "steps_to_reproduce": [
                    "1. 准备测试环境",
                    f"2. 执行测试用例 {test_id}",
                    "3. 观察测试结果",
                ],
                "actual_result": result.get("error_message", "测试失败"),
                "expected_result": "按需求正常工作",
                "root_cause": "",
                "suggested_fix": "",
                "created_at": datetime.now().isoformat(),
                "tags": [],
            })
        return defects

    def _detect_systemic_issues(self, defects: List[Dict]) -> List[Dict]:
        if len(defects) <= 3:
            return []
        modules = [d.get("module", "common") for d in defects]
        counter = Counter(modules)
        systemic = []
        for module, count in counter.items():
            if count > 3:
                systemic.append({
                    "id": f"DEF-SYS-{len(systemic) + 1:03d}",
                    "test_id": "N/A",
                    "test_name": f"{module} 模块系统性缺陷",
                    "title": f"{module} 模块存在系统性缺陷",
                    "description": f"检测到 {module} 模块存在 {count} 个相关缺陷，可能存在系统性问题",
                    "severity": "high",
                    "status": "new",
                    "type": "systemic",
                    "module": module,
                    "priority": "P2",
                    "steps_to_reproduce": [f"执行 {module} 相关测试", "观察多个测试失败", "分析失败模式"],
                    "actual_result": "多个测试失败",
                    "expected_result": "所有测试通过",
                    "root_cause": "需要进一步分析",
                    "suggested_fix": "建议进行代码审查",
                    "created_at": datetime.now().isoformat(),
                    "tags": ["systemic", module],
                })
        return systemic

    def _determine_severity(self, test_name: str) -> str:
        lower = test_name.lower()
        if "payment" in lower or "delete" in lower:
            return "critical"
        if "auth" in lower or "login" in lower or "register" in lower:
            return "high"
        if "update" in lower or "edit" in lower:
            return "medium"
        return "low"

    def _determine_type(self, test_name: str) -> str:
        lower = test_name.lower()
        if "permission" in lower or "access" in lower:
            return "authorization"
        if "auth" in lower or "login" in lower or "register" in lower:
            return "authentication"
        if "validation" in lower or "invalid" in lower:
            return "validation"
        if "performance" in lower or "timeout" in lower:
            return "performance"
        return "functional"

    def _determine_priority(self, test_name: str) -> str:
        mapping = {"critical": "P1", "high": "P2", "medium": "P3", "low": "P4"}
        return mapping.get(self._determine_severity(test_name), "P3")
