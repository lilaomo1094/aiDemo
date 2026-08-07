# -*- coding: utf-8 -*-
"""回归测试：DBSchemaCollector 修复项.

1. test_connection 必须用 text() 包装 SQL，否则 SQLAlchemy 2.0 抛
   ObjectNotExecutableError 并被 except 静默吞掉，导致连接测试永远返回 False。
2. collect() 中多外键表的 foreign_key 字段不能全部指向最后一个外键的引用
   (旧实现 ref 变量从内层循环泄漏)。
"""
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.sql.elements import TextClause

from automation.core.parser.db_schema_collector import DBSchemaCollector


class _FakeDbConfig:
    """最小化的数据库配置对象，供 DBSchemaCollector 使用."""

    def __init__(self, db_type="mysql", enabled=True):
        self.type = db_type
        self.enabled = enabled
        self.host = "db.example.com"
        self.port = 3306
        self.username = "u"
        self.password = "p"
        self.database = "testdb"


class TestTestConnection:
    def test_test_connection_uses_text_wrapped_sql(self):
        """回归测试：test_connection 应使用 text("SELECT 1") 而非裸字符串."""
        collector = DBSchemaCollector(_FakeDbConfig())

        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        with patch("automation.core.parser.db_schema_collector.create_engine", return_value=mock_engine):
            result = collector.test_connection()

        assert result is True, "健康连接应返回 True"
        # 关键断言：execute 收到的必须是 text("SELECT 1")，而不是裸字符串 "SELECT 1"
        assert mock_conn.execute.call_count == 1
        arg = mock_conn.execute.call_args[0][0]
        assert isinstance(arg, TextClause), \
            "必须用 sqlalchemy.text() 包装 SQL，否则 SQLAlchemy 2.0 会抛 ObjectNotExecutableError"
        assert str(arg) == "SELECT 1"

    def test_test_connection_returns_false_on_failure(self):
        collector = DBSchemaCollector(_FakeDbConfig())
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = RuntimeError("connect failed")
        with patch("automation.core.parser.db_schema_collector.create_engine", return_value=mock_engine):
            assert collector.test_connection() is False


class TestCollectForeignKeys:
    def test_multiple_foreign_keys_recorded_per_column(self):
        """回归测试：同一表多个外键列应各自记录正确的引用关系.

        旧实现把 ref 当作内层循环变量泄漏，导致所有外键列都被记录为
        指向最后一个外键的引用 (referred_table.referred_col)。
        """
        collector = DBSchemaCollector(_FakeDbConfig())

        mock_engine = MagicMock()
        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = ["orders"]
        mock_inspector.get_pk_constraint.return_value = {"constrained_columns": ["id"]}
        # orders 表有两个外键：user_id -> users.id, org_id -> orgs.id
        mock_inspector.get_foreign_keys.return_value = [
            {"constrained_columns": ["user_id"], "referred_table": "users", "referred_columns": ["id"]},
            {"constrained_columns": ["org_id"], "referred_table": "orgs", "referred_columns": ["id"]},
        ]
        mock_inspector.get_columns.return_value = [
            {"name": "id", "type": "INTEGER"},
            {"name": "user_id", "type": "INTEGER"},
            {"name": "org_id", "type": "INTEGER"},
        ]

        with patch("automation.core.parser.db_schema_collector.create_engine", return_value=mock_engine), \
             patch("automation.core.parser.db_schema_collector.inspect", return_value=mock_inspector):
            tables = collector.collect()

        assert len(tables) == 1
        cols = {c["name"]: c for c in tables[0]["columns"]}
        assert cols["user_id"]["foreign_key"] == "testdb.users.id", \
            f"user_id 应指向 users.id，实际: {cols['user_id']['foreign_key']}"
        assert cols["org_id"]["foreign_key"] == "testdb.orgs.id", \
            f"org_id 应指向 orgs.id，实际: {cols['org_id']['foreign_key']}"
        assert cols["id"]["foreign_key"] is None

    def test_table_without_foreign_keys(self):
        collector = DBSchemaCollector(_FakeDbConfig())
        mock_engine = MagicMock()
        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = ["t"]
        mock_inspector.get_pk_constraint.return_value = {"constrained_columns": ["id"]}
        mock_inspector.get_foreign_keys.return_value = []
        mock_inspector.get_columns.return_value = [{"name": "id", "type": "INTEGER"}]

        with patch("automation.core.parser.db_schema_collector.create_engine", return_value=mock_engine), \
             patch("automation.core.parser.db_schema_collector.inspect", return_value=mock_inspector):
            tables = collector.collect()

        # 无外键的表不应因 ref 未定义而抛 NameError
        assert tables[0]["columns"][0]["foreign_key"] is None
