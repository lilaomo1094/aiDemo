# -*- coding: utf-8 -*-
"""测试执行器单元测试."""

import pytest
import responses

from automation.core.config import PlatformConfig
from automation.core.executor import APIExecutor, IntegrationExecutor, TestStatus, create_executor


def test_create_executor():
    config = PlatformConfig()
    executor = create_executor("api", config)
    assert isinstance(executor, APIExecutor)
    with pytest.raises(ValueError):
        create_executor("unknown", config)


@responses.activate
def test_api_executor_success():
    config = PlatformConfig()
    config.extra["api_base_url"] = "http://test.local"
    responses.add(responses.GET, "http://test.local/users", json={"data": []}, status=200)

    executor = APIExecutor(config)
    result = executor.execute(
        {"action": {"method": "GET", "path": "/users", "expected_status": 200}}, None
    )
    assert result["status"] == TestStatus.PASSED.value
    assert result["status_code"] == 200


@responses.activate
def test_api_executor_status_mismatch():
    config = PlatformConfig()
    config.extra["api_base_url"] = "http://test.local"
    responses.add(responses.POST, "http://test.local/users", json={}, status=400)

    executor = APIExecutor(config)
    result = executor.execute(
        {"action": {"method": "POST", "path": "/users", "data": {}, "expected_status": 201}}, None
    )
    assert result["status"] == TestStatus.FAILED.value


def test_integration_executor_no_steps():
    config = PlatformConfig()
    executor = IntegrationExecutor(config)
    result = executor.execute({"type": "integration"}, None)
    assert result["status"] == TestStatus.SKIPPED.value
