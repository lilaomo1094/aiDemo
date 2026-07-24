# -*- coding: utf-8 -*-
"""统一配置管理.

支持从 Python 模块、JSON、YAML 加载配置，使用 Pydantic 做校验与默认值填充。
"""

import importlib.util
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

from pydantic import BaseModel, Field, field_validator, model_validator


class ProjectInfo(BaseModel):
    name: str = Field(default="未命名项目", alias="project_name")
    code: str = Field(default="", alias="project_code")
    test_type: str = Field(default="功能测试")
    environment: str = Field(default="test", alias="test_environment")

    model_config = {"populate_by_name": True}


class RequirementConfig(BaseModel):
    doc_path: Optional[str] = Field(default=None, alias="requirement_doc_path")
    doc: Optional[str] = Field(default=None, alias="requirement_doc")

    model_config = {"populate_by_name": True}

    def load_text(self, base_dir: Union[str, Path]) -> str:
        if self.doc:
            return self.doc
        if self.doc_path:
            path = Path(base_dir) / self.doc_path
            if path.exists():
                return path.read_text(encoding="utf-8")
        return ""


class DatabaseColumn(BaseModel):
    name: str
    type: str = "VARCHAR(255)"
    primary_key: bool = False
    nullable: bool = True
    foreign_key: Optional[str] = None
    default: Optional[Any] = None


class DatabaseTable(BaseModel):
    name: str
    description: Optional[str] = None
    columns: List[DatabaseColumn] = Field(default_factory=list)


class DatabaseConfig(BaseModel):
    enabled: bool = False
    type: str = "mysql"
    host: str = "localhost"
    port: int = 3306
    database: str = ""
    username: str = ""
    password: str = ""
    tables: List[DatabaseTable] = Field(default_factory=list)

    @field_validator("type")
    @classmethod
    def _validate_type(cls, v: str) -> str:
        allowed = {"mysql", "postgresql", "oracle", "sqlserver", "sqlite"}
        if v.lower() not in allowed:
            raise ValueError(f"不支持的数据库类型: {v}，支持: {allowed}")
        return v.lower()


class CodeRepositoryConfig(BaseModel):
    enabled: bool = False
    type: str = "github"
    url: str = ""
    branch: str = "main"
    language: str = ""
    test_framework: str = ""
    api_spec: Optional[str] = Field(default=None, alias="api_spec")
    local_path: Optional[str] = None

    @field_validator("type")
    @classmethod
    def _validate_type(cls, v: str) -> str:
        allowed = {"github", "gitlab", "gitee", "local"}
        if v.lower() not in allowed:
            raise ValueError(f"不支持的仓库类型: {v}，支持: {allowed}")
        return v.lower()


class TestConfig(BaseModel):
    coverage_target: int = Field(default=80, ge=0, le=100)
    test_types: List[str] = Field(default_factory=lambda: ["unit", "integration", "api", "ui", "e2e"])
    retry_failed: bool = True
    retry_times: int = Field(default=2, ge=0)
    timeout: int = Field(default=30, ge=1)
    parallel: bool = False
    max_workers: int = Field(default=4, ge=1)


class OutputConfig(BaseModel):
    test_cases_file: str = "output/test_cases.csv"
    defects_file: str = "output/defects.csv"
    report_file: str = "output/test_report.html"
    results_file: str = "output/results.json"
    test_cases_excel: Optional[str] = "output/test_cases.xlsx"
    defects_excel: Optional[str] = "output/defects.xlsx"


class LLMConfig(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4o"
    api_key: str = ""
    base_url: Optional[str] = None
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4000, ge=1)
    timeout: int = Field(default=120, ge=1)

    @field_validator("provider")
    @classmethod
    def _validate_provider(cls, v: str) -> str:
        allowed = {"openai", "anthropic", "azure_openai", "ollama", "custom"}
        if v.lower() not in allowed:
            raise ValueError(f"不支持的 LLM 提供者: {v}，支持: {allowed}")
        return v.lower()


class VoiceConfig(BaseModel):
    enabled: bool = False
    provider: str = "openai_whisper"
    api_key: str = ""
    base_url: Optional[str] = None
    model: str = "whisper-1"
    language: str = "zh"
    timeout: int = Field(default=60, ge=1)

    @field_validator("provider")
    @classmethod
    def _validate_provider(cls, v: str) -> str:
        allowed = {"openai_whisper"}
        if v.lower() not in allowed:
            raise ValueError(f"不支持的 ASR 提供者: {v}，支持: {allowed}")
        return v.lower()


class FunctionCallingConfig(BaseModel):
    enabled: bool = False
    max_iterations: int = Field(default=10, ge=1, le=50)


class VersionConfig(BaseModel):
    enabled: bool = False
    base_dir: str = "versions"
    current_version: str = ""
    auto_create: bool = True  # 指定 --version 且不存在时自动创建


class IMVoiceConfig(BaseModel):
    enabled: bool = False
    provider: str = "openai_whisper"
    api_key: str = ""
    model: str = "whisper-1"
    language: str = "zh"


class IMConfig(BaseModel):
    provider: str = "lark"
    enabled: bool = False
    app_id: str = ""
    app_secret: str = ""
    default_config_path: str = "config/project_config.py"
    project_aliases: Dict[str, str] = Field(default_factory=dict)
    admin_users: List[str] = Field(default_factory=list)
    voice: IMVoiceConfig = Field(default_factory=IMVoiceConfig)
    function_calling: bool = False


class PlatformConfig(BaseModel):
    project: ProjectInfo = Field(default_factory=ProjectInfo)
    requirement: RequirementConfig = Field(default_factory=RequirementConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    frontend_repo: CodeRepositoryConfig = Field(default_factory=CodeRepositoryConfig)
    backend_repo: CodeRepositoryConfig = Field(default_factory=CodeRepositoryConfig)
    test: TestConfig = Field(default_factory=TestConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    function_calling: FunctionCallingConfig = Field(default_factory=FunctionCallingConfig)
    version: VersionConfig = Field(default_factory=VersionConfig)
    im: IMConfig = Field(default_factory=IMConfig)
    extra: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True, "validate_assignment": True}

    @model_validator(mode="after")
    def _post_validate(self):
        if not self.output.results_file.endswith(".json"):
            self.output.results_file = "output/results.json"
        return self

    @property
    def base_dir(self) -> Path:
        # 优先使用新环境变量，兼容旧变量名
        base_dir = os.environ.get("AIAGENT_BASE_DIR") or os.environ.get("PRODEMA_BASE_DIR")
        return Path(base_dir or Path.cwd()).resolve()

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True)


def load_py_config(path: Union[str, Path]) -> Dict[str, Any]:
    path = Path(path).resolve()
    spec = importlib.util.spec_from_file_location("project_config", path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(f"无法加载配置文件: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = getattr(module, "PROJECT_CONFIG", None)
    if config is None:
        raise ValueError(f"配置文件中未找到 PROJECT_CONFIG: {path}")
    return config


def load_json_config(path: Union[str, Path]) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_yaml_config(path: Union[str, Path]) -> Dict[str, Any]:
    if yaml is None:
        raise ImportError("读取 YAML 配置需要安装 PyYAML")
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def _normalize_legacy_config(raw: Dict[str, Any]) -> Dict[str, Any]:
    """兼容旧版扁平配置：将顶层字段迁移到嵌套结构."""
    if "project" in raw or "requirement" in raw:
        return raw

    normalized: Dict[str, Any] = {}

    # project
    project = {}
    for key in ["project_name", "project_code", "test_type", "test_environment"]:
        if key in raw:
            project[key] = raw[key]
    if project:
        normalized["project"] = project

    # requirement
    req = {}
    for key in ["requirement_doc_path", "requirement_doc"]:
        if key in raw:
            req[key] = raw[key]
    if req:
        normalized["requirement"] = req

    # database / repos / test / output / llm
    for section in ["database", "frontend_repo", "backend_repo", "test", "output", "llm"]:
        if section in raw:
            normalized[section] = raw[section]

    # extra
    normalized["extra"] = raw.get("extra", {})
    return normalized


def load_config(path: Union[str, Path]) -> PlatformConfig:
    path = Path(path).resolve()
    suffix = path.suffix.lower()
    if suffix in {".py"}:
        raw = load_py_config(path)
    elif suffix in {".json"}:
        raw = load_json_config(path)
    elif suffix in {".yaml", ".yml"}:
        raw = load_yaml_config(path)
    else:
        raise ValueError(f"不支持的配置文件格式: {suffix}")
    normalized = _normalize_legacy_config(raw)
    return PlatformConfig(**normalized)


def merge_with_framework_config(
    project_config: PlatformConfig,
    framework_config_path: Optional[Union[str, Path]] = None,
) -> PlatformConfig:
    """合并项目配置与框架默认配置，项目配置优先级更高."""
    if framework_config_path is None:
        framework_config_path = Path(__file__).parents[1] / "config" / "config.json"
    if Path(framework_config_path).exists():
        framework_raw = load_json_config(framework_config_path)
        framework = PlatformConfig(**framework_raw)
        merged = framework.model_dump(by_alias=True)
        merged.update(project_config.model_dump(by_alias=True, exclude_unset=True))
        return PlatformConfig(**merged)
    return project_config
