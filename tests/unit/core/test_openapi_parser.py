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


def test_openapi_parser_ref_resolution(tmp_path: Path):
    spec = {
        "openapi": "3.0.0",
        "servers": [{"url": "/api"}],
        "paths": {
            "/users/{id}": {
                "get": {
                    "operationId": "getUser",
                    "parameters": [{"$ref": "#/components/parameters/UserId"}],
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            },
                        }
                    },
                }
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
                    "required": ["id"],
                }
            },
            "parameters": {
                "UserId": {
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                }
            },
        },
    }
    spec_path = tmp_path / "openapi_ref.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    parser = OpenAPIParser()
    result = parser.parse(type("C", (), {"api_spec": str(spec_path)}))

    assert len(result.api_endpoints) == 1
    ep = result.api_endpoints[0]
    param = ep["parameters"][0]
    assert param["name"] == "id"
    assert param["in"] == "path"
    assert param["type"] == "integer"
    assert param["required"] is True

    resp_schema = ep["responses"]["200"]["schema"]
    assert resp_schema["type"] == "object"
    assert "id" in resp_schema["properties"]


def test_openapi_parser_swagger2_parameter(tmp_path: Path):
    spec = {
        "swagger": "2.0",
        "basePath": "/api/v2",
        "paths": {
            "/orders": {
                "get": {
                    "operationId": "listOrders",
                    "parameters": [
                        {"name": "status", "in": "query", "type": "string", "required": False}
                    ],
                    "responses": {"200": {"description": "OK", "schema": {"type": "array"}}},
                }
            }
        },
    }
    spec_path = tmp_path / "swagger2.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    parser = OpenAPIParser()
    result = parser.parse(type("C", (), {"api_spec": str(spec_path)}))

    ep = result.api_endpoints[0]
    assert ep["path"] == "/api/v2/orders"
    param = ep["parameters"][0]
    assert param["type"] == "string"
    assert param["in"] == "query"


def test_openapi_parser_allof_and_enum(tmp_path: Path):
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/pets": {
                "post": {
                    "operationId": "createPet",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "allOf": [
                                        {"$ref": "#/components/schemas/PetBase"},
                                        {
                                            "type": "object",
                                            "properties": {"status": {"type": "string", "enum": ["active", "inactive"]}},
                                        },
                                    ]
                                }
                            }
                        }
                    },
                    "responses": {"201": {"description": "Created"}},
                }
            }
        },
        "components": {
            "schemas": {
                "PetBase": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                }
            }
        },
    }
    spec_path = tmp_path / "allof.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    parser = OpenAPIParser()
    result = parser.parse(type("C", (), {"api_spec": str(spec_path)}))

    ep = result.api_endpoints[0]
    names = {p["name"] for p in ep["parameters"]}
    assert names == {"name", "status"}
    status_param = next(p for p in ep["parameters"] if p["name"] == "status")
    assert status_param["type"] == "string"


def test_openapi_parser_invalid_and_circular_refs(tmp_path: Path):
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/bad": {
                "get": {
                    "operationId": "badRefs",
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Missing"}
                                }
                            },
                        }
                    },
                }
            },
            "/loop": {
                "get": {
                    "operationId": "loopRefs",
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/A"}
                                }
                            },
                        }
                    },
                }
            },
        },
        "components": {
            "schemas": {
                "A": {
                    "type": "object",
                    "properties": {"b": {"$ref": "#/components/schemas/B"}},
                },
                "B": {
                    "type": "object",
                    "properties": {"a": {"$ref": "#/components/schemas/A"}},
                },
            }
        },
    }
    spec_path = tmp_path / "bad_refs.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    parser = OpenAPIParser()
    result = parser.parse(type("C", (), {"api_spec": str(spec_path)}))

    assert len(result.api_endpoints) == 2
    bad_schema = result.api_endpoints[0]["responses"]["200"]["schema"]
    assert "未找到引用" in bad_schema.get("description", "")

    loop_schema = result.api_endpoints[1]["responses"]["200"]["schema"]
    assert loop_schema["type"] == "object"
