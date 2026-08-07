# -*- coding: utf-8 -*-
"""真实数据库 Schema 采集器."""

from typing import Dict, List

from sqlalchemy import create_engine, inspect, text
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
                # SQLAlchemy Inspector.get_pk_constraint 返回的 constrained_columns
                # 是列名字符串列表（不是列字典），直接用 set 即可。旧实现写成
                # c["name"] 会在任何真实数据库上抛 "string indices must be integers".
                pks = set(inspector.get_pk_constraint(table_name).get("constrained_columns", []))
                # 记录每个外键列对应的引用（col_name -> referred_table.referred_col）。
                # 之前的实现把 ref 当作循环变量泄漏出内层循环，导致同一表内多个外键列
                # 全部被记录为指向最后一个外键的引用。
                fk_refs: Dict[str, str] = {}
                for fk in inspector.get_foreign_keys(table_name):
                    ref_cols = fk.get("referred_columns", [])
                    for i, col in enumerate(fk.get("constrained_columns", [])):
                        ref_col = ref_cols[i] if i < len(ref_cols) else ""
                        fk_refs[col] = f"{fk['referred_table']}.{ref_col}"

                for col in inspector.get_columns(table_name):
                    ref = fk_refs.get(col["name"])
                    columns.append({
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col.get("nullable", True),
                        "default": col.get("default", None),
                        "primary_key": col["name"] in pks,
                        "foreign_key": f"{self.config.database}.{ref}" if ref else None,
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
                # SQLAlchemy 2.0 的 Connection.execute 不再接受裸字符串，
                # 必须用 text() 包装，否则抛 ObjectNotExecutableError 并被
                # 下面的 except 静默吞掉，导致 test_connection 永远返回 False。
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
        finally:
            engine.dispose()
