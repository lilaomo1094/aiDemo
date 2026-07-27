# -*- coding: utf-8 -*-
"""统一配置管理.

支持从 Python 模块、JSON、YAML 加载配置，使用 Pydantic 做校验与默认值填充。
"""

import importlib.util
import json
import os
import re
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


class TestAccountConfig(BaseModel):
    """测试账号配置，用于生成 UI/API 测试数据."""

    name: str = Field(default="default", description="账号标识名")
    username: str = ""
    password: str = ""
    phone: str = ""
    email: str = ""
    role: str = "user"
    extra: Dict[str, Any] = Field(default_factory=dict)


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
    fallback_model: Optional[str] = None
    api_key: str = ""
    base_url: Optional[str] = None
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4000, ge=1)
    timeout: int = Field(default=120, ge=1)
    retry_times: int = Field(default=3, ge=0, le=10)
    retry_backoff: float = Field(default=1.0, ge=0.0)

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


class NetworkConfig(BaseModel):
    """网络环境配置：区分公网、内网、VPN 等场景."""

    type: str = "public"  # public | private | vpn
    browser_mode: str = "headless"  # headed | headless
    browser_type: str = "chromium"  # chromium | edge | chrome
    proxy: Optional[str] = None
    bypass_hosts: List[str] = Field(default_factory=list)
    record_video: bool = False
    record_har: bool = False
    capture_console: bool = True
    capture_network: bool = False
    slow_mo: int = 0
    local_browser_path: Optional[str] = None

    @field_validator("type")
    @classmethod
    def _validate_type(cls, v: str) -> str:
        allowed = {"public", "private", "vpn"}
        if v.lower() not in allowed:
            raise ValueError(f"不支持的网络类型: {v}，支持: {allowed}")
        return v.lower()

    @field_validator("browser_mode")
    @classmethod
    def _validate_browser_mode(cls, v: str) -> str:
        allowed = {"headed", "headless"}
        if v.lower() not in allowed:
            raise ValueError(f"不支持的浏览器模式: {v}，支持: {allowed}")
        return v.lower()

    @field_validator("browser_type")
    @classmethod
    def _validate_browser_type(cls, v: str) -> str:
        allowed = {"chromium", "edge", "chrome"}
        if v.lower() not in allowed:
            raise ValueError(f"不支持的浏览器类型: {v}，支持: {allowed}")
        return v.lower()


class EnvironmentConfig(BaseModel):
    """环境级配置：可被不同项目复用，按 dev/test/staging/prod 隔离."""

    name: str = Field(default="dev", description="环境名称")
    description: str = ""
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    test_accounts: List[TestAccountConfig] = Field(default_factory=list)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    extra: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class PlatformConfig(BaseModel):
    project: ProjectInfo = Field(default_factory=ProjectInfo)
    requirement: RequirementConfig = Field(default_factory=RequirementConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    frontend_repo: CodeRepositoryConfig = Field(default_factory=CodeRepositoryConfig)
    backend_repo: CodeRepositoryConfig = Field(default_factory=CodeRepositoryConfig)
    test: TestConfig = Field(default_factory=TestConfig)
    test_accounts: List[TestAccountConfig] = Field(default_factory=list)
    output: OutputConfig = Field(default_factory=OutputConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    function_calling: FunctionCallingConfig = Field(default_factory=FunctionCallingConfig)
    version: VersionConfig = Field(default_factory=VersionConfig)
    im: IMConfig = Field(default_factory=IMConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    extra: Dict[str, Any] = Field(default_factory=dict)
    # 环境配置：可引用 environments/ 目录下的公共环境配置
    environment: str = Field(default="dev", description="当前使用的环境配置名")
    environments_dir: str = Field(default="config/environments", description="环境配置库目录")

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

    # database / repos / test / test_accounts / output / llm
    for section in ["database", "frontend_repo", "backend_repo", "test", "test_accounts", "output", "llm"]:
        if section in raw:
            normalized[section] = raw[section]

    # extra
    normalized["extra"] = raw.get("extra", {})
    return normalized


_ENV_PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _resolve_env_placeholders(value: Any) -> Any:
    """递归解析字符串中的 ${ENV_VAR} 占位符为环境变量值."""
    if isinstance(value, str):
        if _ENV_PLACEHOLDER.fullmatch(value):
            var_name = _ENV_PLACEHOLDER.match(value).group(1)
            resolved = os.environ.get(var_name, "")
            return resolved
        return _ENV_PLACEHOLDER.sub(lambda m: os.environ.get(m.group(1), ""), value)
    if isinstance(value, dict):
        return {k: _resolve_env_placeholders(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_placeholders(v) for v in value]
    return value


def _apply_secret_fallbacks(raw: Dict[str, Any]) -> Dict[str, Any]:
    """当敏感字段为空时，自动尝试从标准环境变量读取."""
    llm = raw.get("llm", {})
    provider = (llm.get("provider") or "openai").lower()
    if not llm.get("api_key"):
        env_var = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "azure_openai": "AZURE_OPENAI_API_KEY",
            "ollama": "OLLAMA_API_KEY",
        }.get(provider, "LLM_API_KEY")
        llm["api_key"] = os.environ.get(env_var, "")

    db = raw.get("database", {})
    if not db.get("password"):
        db["password"] = os.environ.get("DATABASE_PASSWORD", "")

    for acc in raw.get("test_accounts", []):
        if isinstance(acc, dict) and not acc.get("password"):
            acc["password"] = os.environ.get("TEST_PASSWORD", "")

    voice = raw.get("voice", {})
    if not voice.get("api_key"):
        voice["api_key"] = os.environ.get("VOICE_API_KEY") or os.environ.get("OPENAI_API_KEY", "")

    im = raw.get("im", {})
    if not im.get("app_secret"):
        im["app_secret"] = os.environ.get("IM_APP_SECRET", "")
    im_voice = im.get("voice", {})
    if not im_voice.get("api_key"):
        im_voice["api_key"] = os.environ.get("VOICE_API_KEY") or os.environ.get("OPENAI_API_KEY", "")

    return raw


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
    normalized = _resolve_env_placeholders(normalized)
    normalized = _apply_secret_fallbacks(normalized)
    return PlatformConfig(**normalized)


def load_environment_config(
    env_name: str,
    environments_dir: Union[str, Path] = "config/environments",
    base_dir: Optional[Union[str, Path]] = None,
) -> EnvironmentConfig:
    """加载指定环境的公共配置."""
    if base_dir:
        env_dir = Path(base_dir) / environments_dir
    else:
        env_dir = Path(environments_dir)
    env_path = env_dir / f"{env_name}.json"
    if not env_path.exists():
        raise FileNotFoundError(f"环境配置不存在: {env_path}")
    raw = load_json_config(env_path)
    return EnvironmentConfig(**raw)


def merge_environment_config(
    project_config: PlatformConfig,
    env_name: Optional[str] = None,
) -> PlatformConfig:
    """将公共环境配置合并到项目配置，项目配置优先级更高.

    合并规则：对 database/network/extra/test_accounts 进行深合并，
    项目配置中为空/默认值的字段由环境配置填充。
    """
    env_name = env_name or project_config.environment
    if not env_name:
        return project_config
    try:
        env_config = load_environment_config(env_name, project_config.environments_dir, project_config.base_dir)
    except FileNotFoundError:
        return project_config

    project_dump = project_config.model_dump(by_alias=True)
    env_dump = env_config.model_dump(by_alias=True)

    for section in ["database", "network", "extra"]:
        project_section = project_dump.get(section) or {}
        env_section = env_dump.get(section) or {}
        project_dump[section] = _deep_merge(project_section, env_section)

    project_accounts = project_dump.get("test_accounts") or []
    env_accounts = env_dump.get("test_accounts") or []
    if not project_accounts:
        project_dump["test_accounts"] = env_accounts

    # 同步当前环境名
    project_dump["environment"] = env_name
    return PlatformConfig(**project_dump)


def _deep_merge(project_value: Any, env_value: Any) -> Any:
    """深合并：项目值为空时采用环境值；字典递归合并；列表非空时保留项目值."""
    if isinstance(project_value, dict) and isinstance(env_value, dict):
        merged = dict(env_value)
        for key, value in project_value.items():
            merged[key] = _deep_merge(value, env_value.get(key))
        return merged
    if isinstance(project_value, list):
        return project_value if project_value else env_value
    if project_value is None:
        return env_value
    if isinstance(project_value, str):
        return project_value if project_value.strip() != "" else env_value
    if isinstance(project_value, bool):
        return project_value
    return project_value


def _has_user_value(value: Any) -> bool:
    """判断配置项是否包含用户自定义值."""
    if value is None:
        return False
    if isinstance(value, dict):
        return any(_has_user_value(v) for v in value.values())
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, bool):
        return value
    return True


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
