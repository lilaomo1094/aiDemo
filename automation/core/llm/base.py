# -*- coding: utf-8 -*-
"""LLM Provider 抽象基类."""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

import requests


logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    content: str
    model: str = ""
    usage: Dict[str, int] = None
    raw: Any = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if self.usage is None:
            self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


class ToolDefinition:
    """Function Calling 工具定义."""

    def __init__(self, name: str, description: str, parameters: Dict[str, Any], required: List[str] = None):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.required = required or []

    def to_openai(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required,
                },
            },
        }


def with_llm_retry(
    max_retries: int = 3,
    backoff_seconds: float = 1.0,
    retry_status_codes: Tuple[int, ...] = (429, 502, 503, 504),
    retry_exceptions: Tuple[Type[Exception], ...] = (requests.Timeout, requests.ConnectionError),
):
    """LLM 调用重试装饰器.

    对网络超时、连接错误以及指定 HTTP 状态码进行指数退避重试。
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            retries = getattr(self.config, "retry_times", max_retries)
            backoff = getattr(self.config, "retry_backoff", backoff_seconds)
            last_exception: Optional[Exception] = None

            for attempt in range(retries + 1):
                try:
                    return func(self, *args, **kwargs)
                except requests.HTTPError as e:
                    resp = getattr(e, "response", None)
                    status_code = resp.status_code if resp is not None else 0
                    if status_code in retry_status_codes and attempt < retries:
                        sleep_time = backoff * (2 ** attempt)
                        logger.warning(
                            "LLM %s 返回 %s，第 %d 次重试，等待 %.2f 秒",
                            func.__name__, status_code, attempt + 1, sleep_time,
                        )
                        time.sleep(sleep_time)
                        continue
                    logger.error("LLM %s HTTP 错误 %s，不再重试", func.__name__, status_code)
                    raise
                except retry_exceptions as e:
                    last_exception = e
                    if attempt < retries:
                        sleep_time = backoff * (2 ** attempt)
                        logger.warning(
                            "LLM %s 异常 %s，第 %d 次重试，等待 %.2f 秒",
                            func.__name__, type(e).__name__, attempt + 1, sleep_time,
                        )
                        time.sleep(sleep_time)
                        continue
                    logger.error("LLM %s 异常 %s，已达最大重试次数", func.__name__, type(e).__name__)
                    raise last_exception

        return wrapper

    return decorator


class LLMProvider(ABC):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """传入消息列表，返回 LLMResponse."""
        pass

    def complete(self, prompt: str, system: Optional[str] = None, **kwargs) -> LLMResponse:
        """单轮 completion 快捷方法."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, **kwargs)

    def extract_json(self, text: str) -> str:
        """从 LLM 输出中提取 JSON 字符串（支持 markdown 代码块）."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text

    def _try_fallback_model(self, messages: List[Dict[str, str]], kwargs: Dict[str, Any], original_error: Exception) -> LLMResponse:
        """在主模型失败后尝试 fallback 模型."""
        fallback_model = getattr(self.config, "fallback_model", None)
        if not fallback_model or kwargs.get("model") == fallback_model:
            raise original_error
        logger.warning("主模型失败，尝试 fallback 模型: %s", fallback_model)
        kwargs = dict(kwargs)
        kwargs["model"] = fallback_model
        return self.chat(messages, **kwargs)
