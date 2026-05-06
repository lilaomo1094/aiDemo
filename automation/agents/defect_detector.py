import uuid
from typing import Dict, List, Any
from datetime import datetime
from enum import Enum


class DefectSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class DefectStatus(Enum):
    NEW = "new"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class DefectDetector:
    """缺陷发现Agent - 分析执行结果，识别缺陷"""

    def __init__(self, config: Dict):
        self.config = config
        self.defects = []

    def execute(self, task, context) -> Dict:
        """执行缺陷发现"""
        execution_results = context.execution_results or []
        
        if not execution_results:
            execution_results = self._generate_sample_results()

        self._analyze_results(execution_results)
        self._detect_defects(execution_results)
        self._classify_defects()

        return {
            "defects": self.defects,
            "summary": {
                "total_defects": len(self.defects),
                "by_severity": self._count_by_severity(),
                "by_type": self._count_by_type(),
                "by_module": self._count_by_module()
            }
        }

    def _generate_sample_results(self) -> List[Dict]:
        """生成示例执行结果"""
        return [
            {"test_id": "TC-API-001", "test_name": "POST /api/auth/login - 正常", "status": "passed", "duration": 0.123},
            {"test_id": "TC-API-002", "test_name": "POST /api/auth/register - 参数为空", "status": "failed", "duration": 0.087},
            {"test_id": "TC-API-003", "test_name": "GET /api/users - 正常", "status": "passed", "duration": 0.234},
            {"test_id": "TC-API-004", "test_name": "GET /api/users/{id} - 不存在", "status": "failed", "duration": 0.156},
            {"test_id": "TC-DB-001", "test_name": "users表数据完整性测试", "status": "passed", "duration": 0.456},
        ]

    def _analyze_results(self, results: List[Dict]):
        """分析执行结果"""
        for result in results:
            if result.get("status") == "failed":
                test_name = result.get("test_name", "")
                
                defect = {
                    "id": f"DEF-{len(self.defects) + 1:03d}",
                    "test_id": result.get("test_id", ""),
                    "test_name": test_name,
                    "title": self._generate_defect_title(test_name),
                    "description": self._generate_defect_description(result),
                    "severity": self._determine_severity(test_name),
                    "status": DefectStatus.NEW.value,
                    "type": self._determine_defect_type(test_name),
                    "module": self._extract_module(test_name),
                    "priority": self._determine_priority(test_name),
                    "steps_to_reproduce": self._generate_reproduction_steps(result),
                    "actual_result": result.get("error_message", "测试失败"),
                    "expected_result": "按需求正常工作",
                    "root_cause": "",
                    "suggested_fix": "",
                    "created_at": datetime.now().isoformat(),
                    "assignee": "",
                    "tags": []
                }
                
                self.defects.append(defect)

    def _detect_defects(self, results: List[Dict]):
        """检测缺陷模式"""
        failed_tests = [r for r in results if r.get("status") == "failed"]
        
        if len(failed_tests) > 3:
            common_module = self._find_common_module(failed_tests)
            if common_module:
                systemic_defect = {
                    "id": f"DEF-SYS-{len(self.defects) + 1:03d}",
                    "test_id": "N/A",
                    "test_name": f"{common_module}模块系统性缺陷",
                    "title": f"{common_module}模块存在系统性缺陷",
                    "description": f"检测到{common_module}模块存在多个相关缺陷，可能存在系统性问题",
                    "severity": DefectSeverity.HIGH.value,
                    "status": DefectStatus.NEW.value,
                    "type": "systemic",
                    "module": common_module,
                    "priority": "high",
                    "steps_to_reproduce": [
                        f"执行{common_module}相关测试",
                        "观察多个测试失败",
                        "分析失败模式"
                    ],
                    "actual_result": f"多个测试失败",
                    "expected_result": "所有测试通过",
                    "root_cause": "需要进一步分析",
                    "suggested_fix": "建议进行代码审查",
                    "created_at": datetime.now().isoformat(),
                    "assignee": "",
                    "tags": ["systemic", common_module]
                }
                self.defects.append(systemic_defect)

    def _classify_defects(self):
        """分类缺陷"""
        for defect in self.defects:
            test_name = defect.get("test_name", "").lower()
            
            if "auth" in test_name or "login" in test_name or "register" in test_name:
                defect["type"] = "authentication"
                defect["tags"].append("认证问题")
            
            elif "permission" in test_name or "access" in test_name:
                defect["type"] = "authorization"
                defect["tags"].append("权限问题")
            
            elif "validation" in test_name or "invalid" in test_name:
                defect["type"] = "validation"
                defect["tags"].append("验证问题")
            
            elif "performance" in test_name or "timeout" in test_name:
                defect["type"] = "performance"
                defect["tags"].append("性能问题")
            
            else:
                defect["type"] = "functional"
                defect["tags"].append("功能问题")

    def _generate_defect_title(self, test_name: str) -> str:
        """生成缺陷标题"""
        return f"测试失败: {test_name}"

    def _generate_defect_description(self, result: Dict) -> str:
        """生成缺陷描述"""
        return f"测试用例执行失败，错误信息: {result.get('error_message', '未知错误')}"

    def _determine_severity(self, test_name: str) -> str:
        """确定缺陷严重程度"""
        test_name_lower = test_name.lower()
        
        if "auth" in test_name_lower or "login" in test_name_lower or "register" in test_name_lower:
            return DefectSeverity.HIGH.value
        elif "delete" in test_name_lower or "payment" in test_name_lower:
            return DefectSeverity.CRITICAL.value
        elif "update" in test_name_lower or "edit" in test_name_lower:
            return DefectSeverity.MEDIUM.value
        else:
            return DefectSeverity.LOW.value

    def _determine_defect_type(self, test_name: str) -> str:
        """确定缺陷类型"""
        test_name_lower = test_name.lower()
        
        if "permission" in test_name_lower or "access" in test_name_lower:
            return "authorization"
        elif "auth" in test_name_lower or "login" in test_name_lower:
            return "authentication"
        elif "validation" in test_name_lower or "invalid" in test_name_lower:
            return "validation"
        elif "performance" in test_name_lower or "timeout" in test_name_lower:
            return "performance"
        else:
            return "functional"

    def _determine_priority(self, test_name: str) -> str:
        """确定缺陷优先级"""
        severity = self._determine_severity(test_name)
        
        priority_map = {
            DefectSeverity.CRITICAL.value: "P1",
            DefectSeverity.HIGH.value: "P2",
            DefectSeverity.MEDIUM.value: "P3",
            DefectSeverity.LOW.value: "P4",
            DefectSeverity.INFO.value: "P5"
        }
        
        return priority_map.get(severity, "P3")

    def _extract_module(self, test_name: str) -> str:
        """提取模块名"""
        parts = test_name.split()
        for part in parts:
            if part.startswith("/api/"):
                return part.replace("/api/", "").split("/")[0]
        return "common"

    def _generate_reproduction_steps(self, result: Dict) -> List[str]:
        """生成复现步骤"""
        return [
            "1. 准备测试环境",
            f"2. 执行测试用例 {result.get('test_id', '')}",
            "3. 观察测试结果",
            "4. 记录错误信息"
        ]

    def _find_common_module(self, failed_tests: List[Dict]) -> str:
        """查找共同模块"""
        modules = [self._extract_module(t.get("test_name", "")) for t in failed_tests]
        
        from collections import Counter
        module_counts = Counter(modules)
        
        if module_counts and module_counts.most_common(1)[0][1] > 1:
            return module_counts.most_common(1)[0][0]
        
        return ""

    def _count_by_severity(self) -> Dict:
        """按严重程度统计"""
        counts = {}
        for defect in self.defects:
            severity = defect.get("severity", "unknown")
            counts[severity] = counts.get(severity, 0) + 1
        return counts

    def _count_by_type(self) -> Dict:
        """按类型统计"""
        counts = {}
        for defect in self.defects:
            defect_type = defect.get("type", "unknown")
            counts[defect_type] = counts.get(defect_type, 0) + 1
        return counts

    def _count_by_module(self) -> Dict:
        """按模块统计"""
        counts = {}
        for defect in self.defects:
            module = defect.get("module", "unknown")
            counts[module] = counts.get(module, 0) + 1
        return counts
