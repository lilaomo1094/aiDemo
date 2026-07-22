# -*- coding: utf-8 -*-
"""OpenAPI / Swagger 规范解析器."""

import json
from pathlib import Path
from typing import Dict, List, Union
from urllib.parse import urlparse

import requests
import yaml

from .base import CodeParseResult, RepositoryParser


class OpenAPIParser(RepositoryParser):
    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def parse(self, repo_config) -> CodeParseResult:
        spec_path = repo_config.api_spec or ""
        if not spec_path:
            return CodeParseResult(errors=["未配置 api_spec"])

        try:
            spec = self._load_spec(spec_path)
        except Exception as e:
            return CodeParseResult(errors=[f"加载 OpenAPI 规范失败: {e}"])

        endpoints = self._parse_paths(spec)
        models = self._parse_schemas(spec)
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

    def _parse_schemas(self, spec: Dict) -> List[Dict]:
        models = []
        defs = {}
        if "components" in spec and "schemas" in spec["components"]:
            defs = spec["components"]["schemas"]
        elif "definitions" in spec:
            defs = spec["definitions"]

        for name, schema in defs.items():
            columns = []
            required = set(schema.get("required", []))
            properties = schema.get("properties", {})
            for prop_name, prop in properties.items():
                columns.append({
                    "name": prop_name,
                    "type": prop.get("type", "string"),
                    "required": prop_name in required,
                    "description": prop.get("description", ""),
                })
            models.append({
                "name": name,
                "description": schema.get("description", ""),
                "columns": columns,
            })
        return models
