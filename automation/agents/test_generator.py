import uuid
from typing import Dict, List, Any
from datetime import datetime


class TestGenerator:
    """测试用例生成Agent - 基于需求和代码生成测试用例"""

    def __init__(self, config: Dict):
        self.config = config
        self.test_cases = []

    def execute(self, task, context) -> Dict:
        """执行测试用例生成"""
        requirements = context.metadata.get("requirements", [])
        api_endpoints = []
        data_models = []

        if hasattr(context, 'code_info'):
            code_info = context.code_info or {}
            api_endpoints = code_info.get("api_endpoints", [])
            data_models = code_info.get("data_models", [])

        if not api_endpoints:
            api_endpoints = [
                {"method": "POST", "path": "/api/auth/login"},
                {"method": "POST", "path": "/api/auth/register"},
                {"method": "GET", "path": "/api/users"},
                {"method": "POST", "path": "/api/users"},
                {"method": "GET", "path": "/api/users/{id}"},
                {"method": "PUT", "path": "/api/users/{id}"},
                {"method": "DELETE", "path": "/api/users/{id}"}
            ]

        self._generate_api_test_cases(api_endpoints)
        self._generate_db_test_cases(data_models)
        self._generate_ui_test_cases()
        self._generate_integration_test_cases()

        return {
            "test_cases": self.test_cases,
            "summary": {
                "total_cases": len(self.test_cases),
                "by_type": self._count_by_type()
            }
        }

    def _generate_api_test_cases(self, endpoints: List[Dict]):
        """生成API测试用例"""
        test_type_map = {
            "POST": ["正常", "参数为空", "参数错误", "权限验证"],
            "GET": ["正常", "无数据", "权限验证", "分页"],
            "PUT": ["正常", "不存在", "参数错误", "权限验证"],
            "DELETE": ["正常", "不存在", "权限验证"]
        }

        for endpoint in endpoints:
            method = endpoint.get("method", "GET")
            path = endpoint.get("path", "")
            test_types = test_type_map.get(method, ["正常"])

            for test_type in test_types:
                test_case = {
                    "id": f"TC-API-{len(self.test_cases) + 1:03d}",
                    "type": "API",
                    "module": self._extract_module(path),
                    "name": f"{method} {path} - {test_type}",
                    "description": f"API接口 {method} {path} 的{test_type}测试",
                    "priority": "high" if "权限" in test_type or "正常" in test_type else "medium",
                    "preconditions": self._get_api_preconditions(method, path),
                    "test_steps": self._generate_api_steps(method, path, test_type),
                    "expected_result": self._get_api_expected_result(method, test_type),
                    "test_data": self._generate_test_data(method, path),
                    "tags": [method, self._extract_module(path), test_type]
                }
                self.test_cases.append(test_case)

    def _generate_db_test_cases(self, models: List[Dict]):
        """生成数据库测试用例"""
        for model in models:
            table_name = model.get("name", "")

            test_case = {
                "id": f"TC-DB-{len(self.test_cases) + 1:03d}",
                "type": "Database",
                "module": table_name,
                "name": f"{table_name} 表数据完整性测试",
                "description": f"验证{table_name}表的数据完整性、约束和关系",
                "priority": "high",
                "preconditions": ["数据库连接正常"],
                "test_steps": [
                    f"验证{table_name}表主键约束",
                    f"验证{table_name}表外键约束",
                    f"验证{table_name}表非空约束",
                    f"验证{table_name}表数据唯一性",
                    f"验证{table_name}表与其他表的数据关系"
                ],
                "expected_result": "所有约束条件正常工作，数据关系正确",
                "test_data": {"table": table_name},
                "tags": ["database", table_name, "constraint"]
            }
            self.test_cases.append(test_case)

    def _generate_ui_test_cases(self):
        """生成UI测试用例"""
        ui_tests = [
            {
                "page": "登录页",
                "elements": ["用户名输入框", "密码输入框", "登录按钮", "注册链接"],
                "tests": ["正常登录", "错误密码", "空用户名", "空密码", "SQL注入"]
            },
            {
                "page": "注册页",
                "elements": ["用户名输入框", "邮箱输入框", "密码输入框", "注册按钮"],
                "tests": ["正常注册", "邮箱格式错误", "密码太短", "用户名重复"]
            },
            {
                "page": "用户列表页",
                "elements": ["搜索框", "用户表格", "新增按钮", "编辑按钮", "删除按钮"],
                "tests": ["搜索功能", "分页功能", "新增用户", "编辑用户", "删除用户"]
            }
        ]

        for ui_test in ui_tests:
            for test in ui_test["tests"]:
                test_case = {
                    "id": f"TC-UI-{len(self.test_cases) + 1:03d}",
                    "type": "UI",
                    "module": ui_test["page"],
                    "name": f"{ui_test['page']} - {test}",
                    "description": f"{ui_test['page']}的{test}场景",
                    "priority": "high" if "正常" in test else "medium",
                    "preconditions": ["浏览器已打开", "页面已加载"],
                    "test_steps": self._generate_ui_steps(ui_test["page"], test),
                    "expected_result": f"{test}成功，页面显示正确",
                    "test_data": {},
                    "tags": ["ui", ui_test["page"], test]
                }
                self.test_cases.append(test_case)

    def _generate_integration_test_cases(self):
        """生成集成测试用例"""
        integration_tests = [
            {
                "name": "用户注册登录流程",
                "steps": ["注册新用户", "登录系统", "验证登录状态"],
                "priority": "high"
            },
            {
                "name": "用户CRUD完整流程",
                "steps": ["创建用户", "查询用户", "更新用户", "删除用户", "验证删除"],
                "priority": "high"
            },
            {
                "name": "数据权限隔离",
                "steps": ["用户A创建数据", "用户B尝试访问", "验证权限隔离"],
                "priority": "medium"
            }
        ]

        for test in integration_tests:
            test_case = {
                "id": f"TC-INT-{len(self.test_cases) + 1:03d}",
                "type": "Integration",
                "module": "业务流程",
                "name": test["name"],
                "description": f"集成测试：{test['name']}",
                "priority": test["priority"],
                "preconditions": ["系统正常运行", "数据库连接正常"],
                "test_steps": test["steps"],
                "expected_result": "所有步骤执行成功",
                "test_data": {},
                "tags": ["integration", "workflow"]
            }
            self.test_cases.append(test_case)

    def _extract_module(self, path: str) -> str:
        """从路径提取模块名"""
        parts = path.split("/")
        return parts[2] if len(parts) > 2 else "common"

    def _get_api_preconditions(self, method: str, path: str) -> List[str]:
        """获取API前置条件"""
        preconditions = ["API服务正常运行"]
        if method in ["PUT", "DELETE"]:
            preconditions.append("测试数据已创建")
        if "/auth" not in path:
            preconditions.append("用户已登录")
        return preconditions

    def _generate_api_steps(self, method: str, path: str, test_type: str) -> List[str]:
        """生成API测试步骤"""
        steps = [f"准备测试数据（根据需要）"]
        
        if "正常" in test_type:
            steps.append(f"发送 {method} 请求到 {path}")
        elif "为空" in test_type:
            steps.append(f"发送 {method} 请求到 {path}，参数为空")
        elif "错误" in test_type:
            steps.append(f"发送 {method} 请求到 {path}，使用错误参数")
        elif "权限" in test_type:
            steps.append(f"发送 {method} 请求到 {path}，无认证信息")
        elif "不存在" in test_type:
            steps.append(f"发送 {method} 请求到 {path}，使用不存在的ID")
        elif "分页" in test_type:
            steps.append(f"发送 GET 请求到 {path}?page=1&page_size=10")
        
        steps.append("验证响应状态码")
        steps.append("验证响应数据格式")
        steps.append("验证业务逻辑正确性")
        
        return steps

    def _get_api_expected_result(self, method: str, test_type: str) -> str:
        """获取API预期结果"""
        if "正常" in test_type:
            return "返回200/201，响应数据正确"
        elif "为空" in test_type:
            return "返回400，提示参数不能为空"
        elif "错误" in test_type:
            return "返回400，提示参数错误"
        elif "权限" in test_type:
            return "返回401，未授权访问"
        elif "不存在" in test_type:
            return "返回404，资源不存在"
        elif "分页" in test_type:
            return "返回200，分页数据正确"
        return "按预期返回相应状态码"

    def _generate_test_data(self, method: str, path: str) -> Dict:
        """生成测试数据"""
        if "login" in path:
            return {"username": "testuser", "password": "Test123456"}
        elif "register" in path:
            return {"username": f"testuser{uuid.uuid4().hex[:8]}", "email": f"test{uuid.uuid4().hex[:8]}@example.com", "password": "Test123456"}
        elif "users" in path:
            return {"username": "newuser", "email": f"new{uuid.uuid4().hex[:8]}@example.com"}
        return {}

    def _generate_ui_steps(self, page: str, test: str) -> List[str]:
        """生成UI测试步骤"""
        return ["打开浏览器", f"访问{page}", f"执行{test}操作", "验证结果"]

    def _count_by_type(self) -> Dict:
        """按类型统计"""
        counts = {}
        for tc in self.test_cases:
            tc_type = tc.get("type", "Unknown")
            counts[tc_type] = counts.get(tc_type, 0) + 1
        return counts
