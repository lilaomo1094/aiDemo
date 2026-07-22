# -*- coding: utf-8 -*-
"""测试执行器工厂."""

from .api_executor import APIExecutor
from .base import TestExecutor
from .db_executor import DBExecutor
from .integration_executor import IntegrationExecutor
from .ui_executor import UIExecutor

_REGISTRY = {
    "api": APIExecutor,
    "database": DBExecutor,
    "db": DBExecutor,
    "ui": UIExecutor,
    "integration": IntegrationExecutor,
    "e2e": IntegrationExecutor,
}


def create_executor(test_type: str, config) -> TestExecutor:
    executor_cls = _REGISTRY.get(test_type.lower())
    if executor_cls is None:
        raise ValueError(f"未知的测试类型: {test_type}，支持: {list(_REGISTRY.keys())}")
    return executor_cls(config)


def register_executor(name: str, executor_cls):
    _REGISTRY[name.lower()] = executor_cls
