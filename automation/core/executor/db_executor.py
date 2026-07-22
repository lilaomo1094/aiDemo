# -*- coding: utf-8 -*-
"""真实数据库测试执行器."""

from typing import Any, Dict

from sqlalchemy import create_engine, text

from .base import TestExecutor, TestStatus


class DBExecutor(TestExecutor):
    def __init__(self, config):
        super().__init__(config)
        self.db_config = getattr(config, "database", None)

    def execute(self, test_case: Dict, context) -> Dict[str, Any]:
        if not self.db_config or not self.db_config.enabled:
            return self._make_result(TestStatus.SKIPPED, "数据库未启用")

        action = test_case.get("action", {}) or test_case.get("test_data", {})
        sql = action.get("sql") or test_case.get("sql", "")
        if not sql:
            return self._make_result(TestStatus.SKIPPED, "未提供 SQL")

        engine = self._create_engine()
        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql))
                rows = [dict(row._mapping) for row in result.mappings()]
                return self._make_result(
                    TestStatus.PASSED,
                    "数据库执行成功",
                    rows=rows,
                    row_count=len(rows),
                )
        except Exception as e:
            return self._make_result(TestStatus.ERROR, f"数据库执行失败: {e}")
        finally:
            engine.dispose()

    def _create_engine(self):
        cfg = self.db_config
        if cfg.type == "mysql":
            url = f"mysql+pymysql://{cfg.username}:{cfg.password}@{cfg.host}:{cfg.port}/{cfg.database}"
        elif cfg.type == "postgresql":
            url = f"postgresql+psycopg2://{cfg.username}:{cfg.password}@{cfg.host}:{cfg.port}/{cfg.database}"
        elif cfg.type == "sqlite":
            url = f"sqlite:///{cfg.database}"
        else:
            raise ValueError(f"不支持的数据库类型: {cfg.type}")
        return create_engine(url, connect_args={"connect_timeout": 10} if cfg.type != "sqlite" else {})
