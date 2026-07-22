# -*- coding: utf-8 -*-
"""测试用例生成 Agent：基于需求、代码、数据库生成结构化用例."""

import json
import uuid
from typing import Dict, List

from .base import BaseAgent


class TestGenerator(BaseAgent):
    SYSTEM_PROMPT = """你是一名资深测试用例设计专家。请根据输入的需求、API 规范和数据库结构生成测试用例，并以 JSON 数组输出。
每个用例字段：
{
  "id": "TC-API-001",
  "type": "API|Database|UI|Integration",
  "module": "模块名",
  "name": "用例名称",
  "description": "用例描述",
  "priority": "high|medium|low",
  "preconditions": ["前置条件"],
  "test_steps": ["步骤1", "步骤2"],
  "expected_result": "预期结果",
  "expected_status": 200,
  "action": {"method": "POST", "path": "/api/xxx", "data": {}, "headers": {}, "expected_status": 200, "sql": "", "steps": [], "url": ""},
  "tags": ["api", "auth"]
}
注意：
1. 为每个 API 生成正例和反例（参数为空、参数错误、权限不足、资源不存在）。
2. 为数据库表生成约束完整性用例。
3. 如果前端组件信息存在，补充 UI 用例。
4. 只输出 JSON 数组，不要额外解释。"""

    def execute(self, task, context) -> Dict:
        requirements = context.metadata.get("requirements", [])
        api_endpoints = []
        data_models = []
        frontend_components = []

        code_info = getattr(context, "code_info", {}) or {}
        backend = code_info.get("backend", {})
        database = code_info.get("database", {})
        frontend = code_info.get("frontend", {})

        api_endpoints = backend.get("api_endpoints", [])
        data_models = backend.get("data_models", []) or database.get("tables", [])
        frontend_components = frontend.get("components", [])

        # 如果存在 LLM，优先使用 LLM 生成
        if self.llm:
            test_cases = self._generate_with_llm(
                requirements, api_endpoints, data_models, frontend_components
            )
        else:
            test_cases = []

        # 兜底规则生成
        if not test_cases:
            test_cases = self._generate_rule_based(
                requirements, api_endpoints, data_models, frontend_components
            )

        return {
            "test_cases": test_cases,
            "summary": {
                "total_cases": len(test_cases),
                "by_type": self._count_by_type(test_cases),
            },
        }

    def _generate_with_llm(
        self,
        requirements: List[Dict],
        api_endpoints: List[Dict],
        data_models: List[Dict],
        frontend_components: List[Dict],
    ) -> List[Dict]:
        prompt = self._build_prompt(requirements, api_endpoints, data_models, frontend_components)
        result = self._call_llm_json(prompt, system=self.SYSTEM_PROMPT, fallback=[])
        if not isinstance(result, list):
            return []
        for idx, tc in enumerate(result):
            if "id" not in tc:
                tc["id"] = f"TC-{tc.get('type', 'GEN')}-{idx + 1:03d}"
        return result

    def _build_prompt(
        self,
        requirements: List[Dict],
        api_endpoints: List[Dict],
        data_models: List[Dict],
        frontend_components: List[Dict],
    ) -> str:
        return f"""请根据以下信息生成测试用例：

## 需求列表
{json.dumps(requirements, ensure_ascii=False, indent=2)}

## API 接口
{json.dumps(api_endpoints, ensure_ascii=False, indent=2)}

## 数据模型
{json.dumps(data_models, ensure_ascii=False, indent=2)}

## 前端组件
{json.dumps(frontend_components, ensure_ascii=False, indent=2)}
"""

    def _generate_rule_based(
        self,
        requirements: List[Dict],
        api_endpoints: List[Dict],
        data_models: List[Dict],
        frontend_components: List[Dict],
    ) -> List[Dict]:
        test_cases = []
        endpoints = api_endpoints or [
            {"method": "POST", "path": "/api/auth/login"},
            {"method": "POST", "path": "/api/auth/register"},
            {"method": "GET", "path": "/api/users"},
            {"method": "POST", "path": "/api/users"},
            {"method": "GET", "path": "/api/users/{{id}}"},
            {"method": "PUT", "path": "/api/users/{{id}}"},
            {"method": "DELETE", "path": "/api/users/{{id}}"},
        ]

        test_type_map = {
            "POST": ["正常", "参数为空", "参数错误", "权限验证"],
            "GET": ["正常", "无数据", "权限验证", "分页"],
            "PUT": ["正常", "不存在", "参数错误", "权限验证"],
            "DELETE": ["正常", "不存在", "权限验证"],
        }

        for endpoint in endpoints:
            method = endpoint.get("method", "GET")
            path = endpoint.get("path", "")
            for test_type in test_type_map.get(method, ["正常"]):
                tc_id = f"TC-API-{len(test_cases) + 1:03d}"
                priority = "high" if "权限" in test_type or "正常" in test_type else "medium"
                expected_status = self._expected_status(method, test_type)
                test_cases.append({
                    "id": tc_id,
                    "type": "API",
                    "module": self._extract_module(path),
                    "name": f"{method} {path} - {test_type}",
                    "description": f"API 接口 {method} {path} 的{test_type}测试",
                    "priority": priority,
                    "preconditions": self._api_preconditions(method, path),
                    "test_steps": self._api_steps(method, path, test_type),
                    "expected_result": self._api_expected_result(method, test_type),
                    "expected_status": expected_status,
                    "action": {
                        "method": method,
                        "path": path,
                        "data": self._api_data(method, path, test_type),
                        "headers": {},
                        "expected_status": expected_status,
                    },
                    "tags": [method, self._extract_module(path), test_type],
                })

        for model in data_models:
            table = model.get("name", "")
            test_cases.append({
                "id": f"TC-DB-{len(test_cases) + 1:03d}",
                "type": "Database",
                "module": table,
                "name": f"{table} 表数据完整性测试",
                "description": f"验证 {table} 表的数据完整性、约束和关系",
                "priority": "high",
                "preconditions": ["数据库连接正常"],
                "test_steps": [
                    f"验证 {table} 表主键约束",
                    f"验证 {table} 表外键约束",
                    f"验证 {table} 表非空约束",
                ],
                "expected_result": "所有约束条件正常工作",
                "action": {"sql": f"SELECT * FROM {table} LIMIT 1"},
                "tags": ["database", table, "constraint"],
            })

        return test_cases

    def _extract_module(self, path: str) -> str:
        parts = path.split("/")
        return parts[2] if len(parts) > 2 else "common"

    def _api_preconditions(self, method: str, path: str) -> List[str]:
        pre = ["API 服务正常运行"]
        if method in {"PUT", "DELETE"}:
            pre.append("测试数据已创建")
        if "/auth" not in path:
            pre.append("用户已登录")
        return pre

    def _api_steps(self, method: str, path: str, test_type: str) -> List[str]:
        steps = ["准备测试数据"]
        if "正常" in test_type:
            steps.append(f"发送 {method} 请求到 {path}")
        elif "为空" in test_type:
            steps.append(f"发送 {method} 请求到 {path}，参数为空")
        elif "错误" in test_type:
            steps.append(f"发送 {method} 请求到 {path}，使用错误参数")
        elif "权限" in test_type:
            steps.append(f"发送 {method} 请求到 {path}，无认证信息")
        elif "不存在" in test_type:
            steps.append(f"发送 {method} 请求到 {path}，使用不存在的 ID")
        elif "分页" in test_type:
            steps.append(f"发送 GET 请求到 {path}?page=1&page_size=10")
        steps.extend(["验证响应状态码", "验证响应数据格式", "验证业务逻辑"])
        return steps

    def _api_expected_result(self, method: str, test_type: str) -> str:
        mapping = {
            "正常": "返回 200/201，数据正确",
            "为空": "返回 400，提示参数错误",
            "错误": "返回 400，提示参数错误",
            "权限": "返回 401，未授权",
            "不存在": "返回 404，资源不存在",
            "分页": "返回 200，分页数据正确",
        }
        return mapping.get(test_type, "按预期返回")

    def _expected_status(self, method: str, test_type: str) -> int:
        mapping = {
            "正常": 200 if method != "POST" else 201,
            "为空": 400,
            "错误": 400,
            "权限": 401,
            "不存在": 404,
            "分页": 200,
        }
        return mapping.get(test_type, 200)

    def _api_data(self, method: str, path: str, test_type: str) -> Dict:
        if "为空" in test_type:
            return {}
        if "错误" in test_type:
            return {"invalid": "value"}
        if "权限" in test_type:
            return {}
        if "不存在" in test_type:
            return {"id": 999999}
        if "login" in path:
            return {"username": "testuser", "password": "Test123456"}
        if "register" in path:
            return {"username": f"testuser{uuid.uuid4().hex[:8]}", "email": f"test{uuid.uuid4().hex[:8]}@example.com", "password": "Test123456"}
        if "users" in path:
            if method == "POST":
                return {"username": "newuser", "email": f"new{uuid.uuid4().hex[:8]}@example.com"}
            return {"page": 1, "page_size": 10}
        return {}

    def _count_by_type(self, test_cases: List[Dict]) -> Dict:
        counts = {}
        for tc in test_cases:
            t = tc.get("type", "Unknown")
            counts[t] = counts.get(t, 0) + 1
        return counts
