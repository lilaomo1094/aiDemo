# -*- coding: utf-8 -*-
"""代码解析器抽象."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CodeParseResult:
    api_endpoints: List[Dict] = field(default_factory=list)
    data_models: List[Dict] = field(default_factory=list)
    frontend_components: List[Dict] = field(default_factory=list)
    raw_files: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class RepositoryParser(ABC):
    @abstractmethod
    def parse(self, repo_config) -> CodeParseResult:
        pass

    def _normalize_endpoint(self, method: str, path: str, details: Dict) -> Dict:
        parameters = details.get("parameters", [])
        request_body = details.get("requestBody", {})
        if request_body:
            content = request_body.get("content", {})
            for content_type, schema_ref in content.items():
                schema = schema_ref.get("schema", {})
                if schema.get("type") == "object" and "properties" in schema:
                    for name, prop in schema["properties"].items():
                        parameters.append({
                            "name": name,
                            "in": "body",
                            "type": prop.get("type", "string"),
                            "required": name in schema.get("required", []),
                        })
                break
        return {
            "method": method.upper(),
            "path": path,
            "summary": details.get("summary", ""),
            "description": details.get("description", ""),
            "parameters": parameters,
            "responses": details.get("responses", {}),
            "tags": details.get("tags", []),
            "operation_id": details.get("operationId", ""),
        }
