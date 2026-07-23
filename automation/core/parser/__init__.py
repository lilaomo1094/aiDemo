"""代码、API 规范、仓库解析器."""
from .base import CodeParseResult, RepositoryParser
from .git_repo_parser import GitRepositoryParser
from .openapi_parser import OpenAPIParser

try:
    from .db_schema_collector import DBSchemaCollector
except ImportError:
    # 未安装 sqlalchemy 时提供占位类，避免阻塞其他解析器导入
    class DBSchemaCollector:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise ImportError("数据库 Schema 采集需要安装 sqlalchemy")

__all__ = [
    "CodeParseResult",
    "RepositoryParser",
    "GitRepositoryParser",
    "OpenAPIParser",
    "DBSchemaCollector",
]
