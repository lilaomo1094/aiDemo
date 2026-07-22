# -*- coding: utf-8 -*-
"""OpenAPI 解析器单元测试."""

import json
from pathlib import Path

from automation.core.parser import OpenAPIParser


def test_openapi_parser_basic(tmp_path: Path):
    spec = {
        "openapi": "3.0.0",
        "servers": [{"url": "/api/v1"}],
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "operationId": "listUsers",
                    "parameters": [{"name": "page", "in": "query", "type": "integer"}],
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "summary": "Create user",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"name": {"type": "string"}},
                                    "required": ["name"],
                                }
                            }
                        }
                    },
                    "responses": {"201": {"description": "Created"}},
                },
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "description": "User model",
                    "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
                    "required": ["id", "name"],
                }
            }
        },
    }
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    parser = OpenAPIParser()
    result = parser.parse(type("C", (), {"api_spec": str(spec_path)}))

    assert len(result.api_endpoints) == 2
    get_ep = next(e for e in result.api_endpoints if e["method"] == "GET")
    assert get_ep["path"] == "/api/v1/users"
    assert get_ep["operation_id"] == "listUsers"

    post_ep = next(e for e in result.api_endpoints if e["method"] == "POST")
    body_params = [p for p in post_ep["parameters"] if p["in"] == "body"]
    assert len(body_params) == 1

    assert len(result.data_models) == 1
    assert result.data_models[0]["name"] == "User"


def test_openapi_parser_missing_spec():
    parser = OpenAPIParser()
    result = parser.parse(type("C", (), {"api_spec": ""}))
    assert result.errors == ["未配置 api_spec"]
