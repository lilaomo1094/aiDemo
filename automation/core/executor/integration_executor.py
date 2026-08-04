# -*- coding: utf-8 -*-
"""集成测试执行器：按步骤编排多个子操作."""

from typing import Any, Dict, List

from .api_executor import APIExecutor
from .base import TestExecutor, TestStatus

try:
    from .db_executor import DBExecutor
except ImportError:
    DBExecutor = None


class IntegrationExecutor(TestExecutor):
    def __init__(self, config):
        super().__init__(config)
        self.api = APIExecutor(config)
        self.db = DBExecutor(config) if DBExecutor else None

    def execute(self, test_case: Dict, context) -> Dict[str, Any]:
        action = test_case.get("action", {}) or test_case.get("test_data", {})
        steps = action.get("steps") or test_case.get("steps", [])
        if not steps:
            return self._make_result(TestStatus.SKIPPED, "集成用例未配置步骤")

        results: List[Dict] = []
        variables = {}
        for idx, step in enumerate(steps):
            step_type = step.get("type", "api")
            step = self._resolve_variables(step, variables)
            if step_type == "api":
                result = self.api.execute(step, context)
                self._extract_variables(result.get("response", {}), step.get("extract", {}), variables)
            elif step_type == "db":
                if self.db is None:
                    result = self._make_result(TestStatus.ERROR, "数据库执行器不可用，请安装 sqlalchemy")
                else:
                    result = self.db.execute(step, context)
                    self._extract_variables(result.get("rows", []), step.get("extract", {}), variables)
            else:
                result = self._make_result(TestStatus.SKIPPED, f"不支持的步骤类型: {step_type}")
            results.append({"step": idx + 1, "type": step_type, **result})
            if result["status"] in {TestStatus.FAILED.value, TestStatus.ERROR.value}:
                return self._make_result(
                    TestStatus.FAILED,
                    f"第 {idx + 1} 步失败: {result.get('message', '')}",
                    steps=results,
                    variables=variables,
                )

        return self._make_result(TestStatus.PASSED, "集成流程通过", steps=results, variables=variables)

    def _resolve_variables(self, step: Dict, variables: Dict) -> Dict:
        import copy
        step = copy.deepcopy(step)
        for key, value in step.items():
            if isinstance(value, str):
                for var_name, var_value in variables.items():
                    step[key] = value.replace(f"{{{{{var_name}}}}}", str(var_value))
            elif isinstance(value, dict):
                step[key] = self._resolve_variables(value, variables)
            elif isinstance(value, list):
                step[key] = [self._resolve_variables(item, variables) if isinstance(item, dict) else item for item in value]
        return step

    def _extract_variables(self, source: Any, extract: Dict, variables: Dict):
        for name, path in extract.items():
            if isinstance(path, str):
                value = source
                for part in path.split("."):
                    if isinstance(value, dict):
                        value = value.get(part)
                    elif isinstance(value, list) and part.isdigit():
                        value = value[int(part)] if int(part) < len(value) else None
                    else:
                        value = None
                    if value is None:
                        break
                variables[name] = value
