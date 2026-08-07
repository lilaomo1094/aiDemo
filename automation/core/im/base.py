# -*- coding: utf-8 -*-
"""IM Provider 抽象基类."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class IMMessage:
    message_id: str
    sender_id: str
    sender_name: str = ""
    content: str = ""
    channel: str = ""  # chat_id / group_id
    message_type: str = "text"  # text / voice / image / file
    audio_url: str = ""  # 语音消息下载地址
    raw: Any = None

    def is_command(self) -> bool:
        return self.content.strip().startswith("/") or "执行测试" in self.content or "run" in self.content.lower()

    def get_command(self) -> str:
        text = self.content.strip()
        if text.startswith("/"):
            return text[1:].split()[0].lower()
        return ""


class IMProvider(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def send_text(self, receiver: str, content: str, **kwargs) -> bool:
        """发送文本消息."""
        pass

    @abstractmethod
    def send_file(self, receiver: str, file_path: str, **kwargs) -> bool:
        """发送文件."""
        pass

    def parse_webhook_payload(self, payload: Dict[str, Any]) -> IMMessage:
        """解析 Webhook 回调中的消息."""
        raise NotImplementedError()

    def verify_webhook(self, body: bytes, headers: Dict[str, str]) -> bool:
        """验证 Webhook 签名.

        Args:
            body: 原始请求体字节（签名需基于原始字节计算，不能基于解析后的对象）。
            headers: 请求头字典（大小写不敏感查找由调用方处理）。

        默认实现：未配置密钥时放行（保持向后兼容）；配置了密钥的子类必须实现
        真实的签名校验，否则存在管理员身份伪造 / 任意消息注入风险。
        """
        return True
