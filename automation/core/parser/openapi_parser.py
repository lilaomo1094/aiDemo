# -*- coding: utf-8 -*-
"""OpenAPI / Swagger 规范解析器.

支持特性：
- Swagger 2.0 / OpenAPI 3.0 混合解析
- 文档内 ``$ref`` 引用递归展开
- 参数与响应 schema 标准化
- 复杂对象/数组/枚举类型提取
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import requests
import yaml

from .base import CodeParseResult, RepositoryParser


class OpenAPIParser(RepositoryParser):
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._spec: Dict[str, Any] = {}

    def parse(self, repo_config) -> CodeParseResult:
        spec_path = repo_config.api_spec or ""
        if not spec_path:
            return CodeParseResult(errors=["未配置 api_spec"])

        try:
            self._spec = self._load_spec(spec_path)
        except Exception as e:
            return CodeParseResult(errors=[f"加载 OpenAPI 规范失败: {e}"])

        endpoints = self._parse_paths(self._spec)
        models = self._parse_schemas(self._spec)
        return CodeParseResult(api_endpoints=endpoints, data_models=models)

    def _load_spec(self, spec_path: str) -> Dict:
        parsed = urlparse(spec_path)
        if parsed.scheme in {"http", "https"}:
            response = requests.get(spec_path, timeout=self.timeout)
            response.raise_for_status()
            text = response.text
        else:
            text = Path(spec_path).read_text(encoding="utf-8")

        if text.strip().startswith("{"):
            return json.loads(text)
        return yaml.safe_load(text) or {}

    # ------------------------------------------------------------------ #
    # $ref 解析
    # ------------------------------------------------------------------ #
    def _resolve_ref(self, ref: str) -> Any:
        if not ref.startswith("#/"):
            return {}
        parts = ref.split("/")[1:]
        node = self._spec
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                return {}
            node = node[part]
        return node

    def _resolve_schema(self, schema: Any, depth: int = 0) -> Dict[str, Any]:
        """递归展开 schema，返回标准化描述."""
        if depth > 20:
            return {"type": "object", "description": "嵌套过深"}
        if not isinstance(schema, dict):
            return {"type": "object"}

        if "$ref" in schema:
            schema = {**self._resolve_ref(schema["$ref"]), **{k: v for k, v in schema.items() if k != "$ref"}}

        schema_type = schema.get("type", "object")
        result: Dict[str, Any] = {
            "type": schema_type,
            "description": schema.get("description", ""),
            "enum": schema.get("enum", []),
        }

        if schema_type == "array" and "items" in schema:
            result["items"] = self._resolve_schema(schema["items"], depth + 1)

        if "properties" in schema:
            props = {}
            required = set(schema.get("required", []))
            for name, prop in schema["properties"].items():
                props[name] = self._resolve_schema(prop, depth + 1)
                props[name]["required"] = name in required
            result["properties"] = props

        if "allOf" in schema:
            merged = {"type": "object", "properties": {}, "required": []}
            for sub in schema["allOf"]:
                resolved = self._resolve_schema(sub, depth + 1)
                merged["properties"].update(resolved.get("properties", {}))
            result.update(merged)

        return result

    def _get_param_type(self, param: Dict) -> str:
        """兼容 Swagger 2.0 与 OpenAPI 3.0 的参数类型."""
        if "schema" in param:
            return self._resolve_schema(param["schema"]).get("type", "string")
        return param.get("type", "string")

    # ------------------------------------------------------------------ #
    # 路径与端点解析
    # ------------------------------------------------------------------ #
    def _parse_paths(self, spec: Dict) -> List[Dict]:
        endpoints = []
        paths = spec.get("paths", {})
        base_path = spec.get("basePath", "")
        servers = spec.get("servers", [])
        if servers and not base_path:
            base_path = servers[0].get("url", "")

        for path, methods in paths.items():
            full_path = base_path + path
            for method, details in methods.items():
                if method.upper() not in {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}:
                    continue
                endpoints.append(self._normalize_endpoint(method, full_path, details))
        return endpoints

    def _normalize_endpoint(self, method: str, path: str, details: Dict) -> Dict:
        parameters = []

        # 路径级与方法级参数
        for param in details.get("parameters", []):
            parameters.append(self._normalize_parameter(param))

        # requestBody -> body 参数
        request_body = details.get("requestBody") or {}
        if request_body:
            content = request_body.get("content", {})
            for content_type, schema_ref in content.items():
                schema = self._resolve_schema(schema_ref.get("schema", {}))
                for name, prop in schema.get("properties", {}).items():
                    parameters.append({
                        "name": name,
                        "in": "body",
                        "type": prop.get("type", "string"),
                        "required": prop.get("required", False),
                        "description": prop.get("description", ""),
                        "content_type": content_type,
                    })
                break

        # 响应 schema
        responses = {}
        for code, resp in (details.get("responses", {}) or {}).items():
            normalized: Dict[str, Any] = {
                "description": resp.get("description", ""),
            }
            resp_content = resp.get("content", {})
            for content_type, schema_ref in resp_content.items():
                normalized["content_type"] = content_type
                normalized["schema"] = self._resolve_schema(schema_ref.get("schema", {}))
                break
            if "schema" in resp:
                normalized["schema"] = self._resolve_schema(resp["schema"])
            responses[str(code)] = normalized

        return {
            "method": method.upper(),
            "path": path,
            "summary": details.get("summary", ""),
            "description": details.get("description", ""),
            "parameters": parameters,
            "responses": responses,
            "tags": details.get("tags", []),
            "operation_id": details.get("operationId", ""),
        }

    def _normalize_parameter(self, param: Dict) -> Dict:
        if "$ref" in param:
            param = self._resolve_ref(param["$ref"])
        return {
            "name": param.get("name", ""),
            "in": param.get("in", "query"),
            "type": self._get_param_type(param),
            "required": param.get("required", False),
            "description": param.get("description", ""),
        }

    # ------------------------------------------------------------------ #
    # Schema / Model 解析
    # ------------------------------------------------------------------ #
    def _parse_schemas(self, spec: Dict) -> List[Dict]:
        models = []
        defs = {}
        if "components" in spec and "schemas" in spec["components"]:
            defs = spec["components"]["schemas"]
        elif "definitions" in spec:
            defs = spec["definitions"]

        for name, schema in defs.items():
            resolved = self._resolve_schema(schema)
            columns = []
            for prop_name, prop in resolved.get("properties", {}).items():
                columns.append({
                    "name": prop_name,
                    "type": prop.get("type", "string"),
                    "required": prop.get("required", False),
                    "description": prop.get("description", ""),
                })
            models.append({
                "name": name,
                "description": resolved.get("description", ""),
                "columns": columns,
            })
        return models
