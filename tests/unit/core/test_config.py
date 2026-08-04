# -*- coding: utf-8 -*-
"""配置模块单元测试."""

import json
import tempfile
from pathlib import Path

import pytest

from automation.core.config import (
    DatabaseConfig,
    LLMConfig,
    OutputConfig,
    PlatformConfig,
    ProjectInfo,
    load_config,
    load_json_config,
)


def test_project_info_defaults():
    info = ProjectInfo()
    assert info.name == "未命名项目"
    assert info.environment == "test"


def test_database_config_validation():
    db = DatabaseConfig(type="MySQL")
    assert db.type == "mysql"
    with pytest.raises(ValueError):
        DatabaseConfig(type="mongodb")


def test_llm_config_validation():
    llm = LLMConfig(provider="OpenAI", model="gpt-4o")
    assert llm.provider == "openai"
    with pytest.raises(ValueError):
        LLMConfig(provider="unknown")


def test_load_json_config(tmp_path: Path):
    data = {"project": {"project_name": "Test"}, "database": {"enabled": False}}
    config_path = tmp_path / "test.json"
    config_path.write_text(json.dumps(data), encoding="utf-8")
    config = load_json_config(config_path)
    assert config["project"]["project_name"] == "Test"


def test_load_config_nested(tmp_path: Path):
    data = {
        "project": {"project_name": "Nested"},
        "database": {"enabled": True, "type": "sqlite", "database": ":memory:"},
        "llm": {"provider": "ollama", "model": "llama3"},
    }
    config_path = tmp_path / "nested.json"
    config_path.write_text(json.dumps(data), encoding="utf-8")
    config = load_config(config_path)
    assert isinstance(config, PlatformConfig)
    assert config.project.name == "Nested"
    assert config.database.enabled is True
    assert config.llm.provider == "ollama"


def test_load_config_legacy_flat(tmp_path: Path):
    data = {
        "project_name": "Legacy",
        "project_code": "LEG-001",
        "database": {"enabled": False},
    }
    config_path = tmp_path / "legacy.json"
    config_path.write_text(json.dumps(data), encoding="utf-8")
    config = load_config(config_path)
    assert config.project.name == "Legacy"
    assert config.project.code == "LEG-001"


def test_output_config_post_validate():
    config = PlatformConfig(output={"results_file": "output/results.yaml"})
    assert config.output.results_file == "output/results.json"
