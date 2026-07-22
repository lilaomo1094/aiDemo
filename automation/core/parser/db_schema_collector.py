# -*- coding: utf-8 -*-
"""真实数据库 Schema 采集器."""

from typing import Dict, List

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine


class DBSchemaCollector:
    """连接数据库并采集表结构、列、主键、外键、索引."""

    def __init__(self, db_config):
        self.config = db_config

    def collect(self) -> List[Dict]:
        if not self.config.enabled:
            return []

        engine = self._create_engine()
        try:
            inspector = inspect(engine)
            tables = []
            for table_name in inspector.get_table_names():
                columns = []
                pks = {c["name"] for c in inspector.get_pk_constraint(table_name).get("constrained_columns", [])}
                fks = []
                for fk in inspector.get_foreign_keys(table_name):
                    for i, col in enumerate(fk.get("constrained_columns", [])):
                        ref_cols = fk.get("referred_columns", [])
                        ref = f"{fk['referred_table']}.{ref_cols[i] if i < len(ref_cols) else ''}"
                        fks.append(col)

                for col in inspector.get_columns(table_name):
                    columns.append({
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col.get("nullable", True),
                        "default": col.get("default", None),
                        "primary_key": col["name"] in pks,
                        "foreign_key": f"{self.config.database}.{ref}" if col["name"] in fks else None,
                    })

                tables.append({
                    "name": table_name,
                    "description": "",
                    "columns": columns,
                })
            return tables
        finally:
            engine.dispose()

    def _create_engine(self) -> Engine:
        cfg = self.config
        if cfg.type == "mysql":
            driver = "pymysql"
            url = f"mysql+{driver}://{cfg.username}:{cfg.password}@{cfg.host}:{cfg.port}/{cfg.database}"
        elif cfg.type == "postgresql":
            driver = "psycopg2"
            url = f"postgresql+{driver}://{cfg.username}:{cfg.password}@{cfg.host}:{cfg.port}/{cfg.database}"
        elif cfg.type == "sqlite":
            url = f"sqlite:///{cfg.database}"
        else:
            raise ValueError(f"暂不支持通过 SQLAlchemy 连接的数据库类型: {cfg.type}")
        return create_engine(url, connect_args={"connect_timeout": 10} if cfg.type != "sqlite" else {})

    def test_connection(self) -> bool:
        if not self.config.enabled:
            return False
        engine = self._create_engine()
        try:
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception:
            return False
        finally:
            engine.dispose()
