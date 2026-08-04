# -*- coding: utf-8 -*-
"""代码解析 Agent：解析前后端代码、API 规范、数据库结构."""

from typing import Dict, List

from automation.core.parser import DBSchemaCollector, GitRepositoryParser, OpenAPIParser

from .base import BaseAgent


class CodeParser(BaseAgent):
    def execute(self, task, context) -> Dict:
        code_info = {"backend": {}, "frontend": {}, "database": {}, "errors": []}

        # 后端仓库解析
        backend = self.config.backend_repo if hasattr(self.config, "backend_repo") else None
        if backend and backend.enabled:
            parser = self._select_parser(backend)
            result = parser.parse(backend)
            code_info["backend"] = {
                "api_endpoints": result.api_endpoints,
                "data_models": result.data_models,
                "raw_files": result.raw_files[:20],
                "errors": result.errors,
            }
            code_info["errors"].extend(result.errors)

        # 前端仓库解析
        frontend = self.config.frontend_repo if hasattr(self.config, "frontend_repo") else None
        if frontend and frontend.enabled:
            parser = self._select_parser(frontend)
            result = parser.parse(frontend)
            code_info["frontend"] = {
                "components": result.frontend_components,
                "raw_files": result.raw_files[:20],
                "errors": result.errors,
            }
            code_info["errors"].extend(result.errors)

        # 数据库 Schema 采集
        db = self.config.database if hasattr(self.config, "database") else None
        if db and db.enabled:
            try:
                collector = DBSchemaCollector(db)
                tables = collector.collect()
                code_info["database"] = {"tables": tables, "source": "live"}
            except Exception as e:
                code_info["database"] = {"tables": [t.model_dump() for t in db.tables], "source": "config"}
                code_info["errors"].append(f"数据库连接失败，使用配置中的表结构: {e}")
        else:
            code_info["database"] = {"tables": [], "source": "none"}

        return {
            "code_info": code_info,
            "api_endpoints": code_info["backend"].get("api_endpoints", []),
            "data_models": code_info["backend"].get("data_models", []) or code_info["database"].get("tables", []),
            "frontend_components": code_info["frontend"].get("components", []),
            "summary": {
                "total_apis": len(code_info["backend"].get("api_endpoints", [])),
                "total_models": len(code_info["backend"].get("data_models", [])) or len(code_info["database"].get("tables", [])),
                "total_components": len(code_info["frontend"].get("components", [])),
                "errors": code_info["errors"],
            },
        }

    def _select_parser(self, repo_config):
        if repo_config.api_spec:
            return OpenAPIParser(timeout=self.config.test.timeout if hasattr(self.config, "test") else 30)
        if repo_config.type in {"github", "gitlab", "gitee", "local"} or repo_config.local_path:
            return GitRepositoryParser(timeout=self.config.test.timeout * 4 if hasattr(self.config, "test") else 120)
        return OpenAPIParser()
