# -*- coding: utf-8 -*-
"""IM Provider 工厂：根据配置创建对应的消息平台 Provider."""

from typing import Any, Dict

from .base import IMProvider
from .lark_provider import LarkProvider
from .wechat_provider import WeChatProvider


PROVIDER_REGISTRY: Dict[str, Any] = {
    "lark": LarkProvider,
    "feishu": LarkProvider,
    "wechat": WeChatProvider,
    "wecom": WeChatProvider,
}


def create_im_provider(provider_type: str, config: Dict[str, Any]) -> IMProvider:
    """创建 IM Provider.

    Args:
        provider_type: lark / feishu / wechat / wecom
        config: provider 配置字典

    Raises:
        ValueError: 不支持的 provider 类型
    """
    provider_type = provider_type.lower()
    cls = PROVIDER_REGISTRY.get(provider_type)
    if not cls:
        supported = ", ".join(PROVIDER_REGISTRY.keys())
        raise ValueError(f"不支持的 IM Provider: {provider_type}，支持: {supported}")
    return cls(config)


def register_im_provider(provider_type: str, cls: Any):
    """注册自定义 IM Provider."""
    PROVIDER_REGISTRY[provider_type.lower()] = cls
