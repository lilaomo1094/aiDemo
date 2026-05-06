import os
import re
import json
from typing import Dict, List, Any, Optional
from pathlib import Path


class CodeParser:
    """代码解析Agent - 解析前后端代码，提取API接口和数据模型"""

    def __init__(self, config: Dict):
        self.config = config
        self.api_endpoints = []
        self.data_models = []
        self.frontend_components = []

    def execute(self, task, context) -> Dict:
        """执行代码解析"""
        code_info = context.code_info or {}

        if not code_info:
            code_info = self._load_code_from_repo(context)

        self._parse_apis(code_info.get("backend", {}))
        self._parse_data_models(code_info.get("database", {}))
        self._parse_frontend_components(code_info.get("frontend", {}))

        return {
            "code_info": code_info,
            "api_endpoints": self.api_endpoints,
            "data_models": self.data_models,
            "frontend_components": self.frontend_components,
            "summary": {
                "total_apis": len(self.api_endpoints),
                "total_models": len(self.data_models),
                "total_components": len(self.frontend_components)
            }
        }

    def _load_code_from_repo(self, context) -> Dict:
        """从代码仓库加载代码信息"""
        repo_config = self.config.get("code_repository", {})
        return {
            "backend": repo_config.get("backend", {}),
            "frontend": repo_config.get("frontend", {}),
            "database": context.database_schema or {}
        }

    def _parse_apis(self, backend_info: Dict):
        """解析后端API接口"""
        self.api_endpoints = [
            {
                "method": "POST",
                "path": "/api/auth/login",
                "description": "用户登录",
                "parameters": [
                    {"name": "username", "type": "string", "required": True},
                    {"name": "password", "type": "string", "required": True}
                ],
                "responses": {
                    "200": {"description": "登录成功", "schema": {"token": "string"}},
                    "401": {"description": "用户名或密码错误"}
                },
                "tags": ["auth"]
            },
            {
                "method": "POST",
                "path": "/api/auth/register",
                "description": "用户注册",
                "parameters": [
                    {"name": "username", "type": "string", "required": True},
                    {"name": "email", "type": "string", "required": True},
                    {"name": "password", "type": "string", "required": True}
                ],
                "responses": {
                    "201": {"description": "注册成功"},
                    "400": {"description": "参数错误"}
                },
                "tags": ["auth"]
            },
            {
                "method": "GET",
                "path": "/api/users",
                "description": "获取用户列表",
                "parameters": [
                    {"name": "page", "type": "integer", "required": False},
                    {"name": "page_size", "type": "integer", "required": False}
                ],
                "responses": {
                    "200": {"description": "成功", "schema": {"items": "User"}}
                },
                "tags": ["users"]
            },
            {
                "method": "POST",
                "path": "/api/users",
                "description": "创建用户",
                "parameters": [
                    {"name": "username", "type": "string", "required": True},
                    {"name": "email", "type": "string", "required": True}
                ],
                "responses": {
                    "201": {"description": "创建成功"}
                },
                "tags": ["users"]
            },
            {
                "method": "GET",
                "path": "/api/users/{id}",
                "description": "获取用户详情",
                "parameters": [
                    {"name": "id", "type": "integer", "required": True}
                ],
                "responses": {
                    "200": {"description": "成功"},
                    "404": {"description": "用户不存在"}
                },
                "tags": ["users"]
            },
            {
                "method": "PUT",
                "path": "/api/users/{id}",
                "description": "更新用户",
                "parameters": [
                    {"name": "id", "type": "integer", "required": True}
                ],
                "responses": {
                    "200": {"description": "更新成功"}
                },
                "tags": ["users"]
            },
            {
                "method": "DELETE",
                "path": "/api/users/{id}",
                "description": "删除用户",
                "parameters": [
                    {"name": "id", "type": "integer", "required": True}
                ],
                "responses": {
                    "204": {"description": "删除成功"}
                },
                "tags": ["users"]
            }
        ]

    def _parse_data_models(self, db_schema: Dict):
        """解析数据模型"""
        tables = db_schema.get("tables", [])

        if not tables:
            tables = [
                {
                    "name": "users",
                    "columns": [
                        {"name": "id", "type": "INT", "primary_key": True},
                        {"name": "username", "type": "VARCHAR(50)", "nullable": False},
                        {"name": "email", "type": "VARCHAR(100)", "nullable": False},
                        {"name": "password_hash", "type": "VARCHAR(255)", "nullable": False},
                        {"name": "created_at", "type": "DATETIME"},
                        {"name": "updated_at", "type": "DATETIME"}
                    ]
                },
                {
                    "name": "orders",
                    "columns": [
                        {"name": "id", "type": "INT", "primary_key": True},
                        {"name": "user_id", "type": "INT", "foreign_key": "users.id"},
                        {"name": "total_amount", "type": "DECIMAL(10,2)"},
                        {"name": "status", "type": "VARCHAR(20)"},
                        {"name": "created_at", "type": "DATETIME"}
                    ]
                }
            ]

        for table in tables:
            model = {
                "name": table["name"],
                "description": f"{table['name']}表",
                "columns": table["columns"],
                "constraints": self._extract_constraints(table)
            }
            self.data_models.append(model)

    def _extract_constraints(self, table: Dict) -> List[Dict]:
        """提取约束条件"""
        constraints = []

        for col in table.get("columns", []):
            if col.get("primary_key"):
                constraints.append({
                    "type": "PRIMARY KEY",
                    "columns": [col["name"]]
                })
            if col.get("foreign_key"):
                constraints.append({
                    "type": "FOREIGN KEY",
                    "columns": [col["name"]],
                    "references": col["foreign_key"]
                })
            if not col.get("nullable", True):
                constraints.append({
                    "type": "NOT NULL",
                    "columns": [col["name"]]
                })

        return constraints

    def _parse_frontend_components(self, frontend_info: Dict):
        """解析前端组件"""
        self.frontend_components = [
            {
                "name": "LoginPage",
                "type": "page",
                "description": "登录页面",
                "elements": [
                    {"name": "usernameInput", "type": "input"},
                    {"name": "passwordInput", "type": "password"},
                    {"name": "loginButton", "type": "button"},
                    {"name": "registerLink", "type": "link"}
                ]
            },
            {
                "name": "RegisterPage",
                "type": "page",
                "description": "注册页面",
                "elements": [
                    {"name": "usernameInput", "type": "input"},
                    {"name": "emailInput", "type": "email"},
                    {"name": "passwordInput", "type": "password"},
                    {"name": "confirmPasswordInput", "type": "password"},
                    {"name": "registerButton", "type": "button"}
                ]
            },
            {
                "name": "UserList",
                "type": "component",
                "description": "用户列表组件",
                "elements": [
                    {"name": "searchInput", "type": "input"},
                    {"name": "userTable", "type": "table"},
                    {"name": "addButton", "type": "button"},
                    {"name": "editButton", "type": "button"},
                    {"name": "deleteButton", "type": "button"}
                ]
            }
        ]


def parse_swagger_spec(spec: Dict) -> List[Dict]:
    """解析Swagger/OpenAPI规范"""
    endpoints = []

    for path, methods in spec.get("paths", {}).items():
        for method, details in methods.items():
            if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                endpoints.append({
                    "method": method.upper(),
                    "path": path,
                    "description": details.get("summary", ""),
                    "parameters": details.get("parameters", []),
                    "responses": details.get("responses", {})
                })

    return endpoints
