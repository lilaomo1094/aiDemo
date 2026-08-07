# -*- coding: utf-8 -*-
"""飞书 Lark Provider.

发送消息优先使用飞书 Skill（lark-im）；未授权时降级为日志输出。
接收消息通过 Webhook 回调解析。
"""

from typing import Any, Dict

from .base import IMMessage, IMProvider


class LarkProvider(IMProvider):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.app_id = config.get("app_id", "")
        self.app_secret = config.get("app_secret", "")
        self.encrypt_key = config.get("encrypt_key", "")
        self.mock = config.get("mock", False)

    def send_text(self, receiver: str, content: str, **kwargs) -> bool:
        if self.mock:
            print(f"[Lark Mock] send to {receiver}: {content[:200]}")
            return True
        try:
            # 使用 lark-im skill 发送文本消息
            from automation.core.im.skills import send_lark_text
            return send_lark_text(receiver, content, **kwargs)
        except Exception as e:
            print(f"[Lark] send_text failed: {e}, fallback to log")
            print(f"[Lark Fallback] to={receiver}: {content[:200]}")
            return False

    def send_file(self, receiver: str, file_path: str, **kwargs) -> bool:
        if self.mock:
            print(f"[Lark Mock] send file to {receiver}: {file_path}")
            return True
        try:
            from automation.core.im.skills import send_lark_file
            return send_lark_file(receiver, file_path, **kwargs)
        except Exception as e:
            print(f"[Lark] send_file failed: {e}, fallback to log")
            return False

    def parse_webhook_payload(self, payload: Dict[str, Any]) -> IMMessage:
        """解析飞书事件回调 payload.

        支持两种格式：
        1. 开放平台事件推送：{ "event": { "message": { ... } } }
        2. 自定义机器人 webhook：{ "chat_id": "...", "open_id": "...", "text": "..." }
        """
        event = payload.get("event", payload)
        message = event.get("message", {})
        sender = event.get("sender", {}).get("sender_id", {}).get("open_id", "") or event.get("open_id", "")
        chat_id = message.get("chat_id", "") or event.get("chat_id", "")
        msg_type = message.get("msg_type", "text")

        content = ""
        if msg_type == "text":
            raw_content = message.get("content", "{}")
            if isinstance(raw_content, str):
                import json
                try:
                    content = json.loads(raw_content).get("text", "")
                except Exception:
                    content = raw_content
            elif isinstance(raw_content, dict):
                content = raw_content.get("text", "")
        elif msg_type == "post":
            content = "[post message]"

        return IMMessage(
            message_id=message.get("message_id", event.get("message_id", "")),
            sender_id=sender,
            sender_name=event.get("sender", {}).get("sender_id", {}).get("open_id", ""),
            content=content,
            channel=chat_id,
            raw=payload,
        )

    def verify_webhook(self, body: bytes, headers: Dict[str, str]) -> bool:
        """校验飞书事件回调签名 (X-Lark-Signature).

        未配置 encrypt_key 时放行（兼容明文模式与既有测试）。
        配置了 encrypt_key 时必须校验，否则任何能访问端口的请求都可伪造
        sender_id 冒充 admin_users 触发 /run / /cancel 等高危命令。
        """
        if not self.encrypt_key:
            return True

        import hashlib
        import hmac

        signature = (
            headers.get("X-Lark-Signature")
            or headers.get("x-lark-signature")
            or ""
        )
        if not signature:
            return False
        timestamp = (
            headers.get("X-Lark-Request-Timestamp")
            or headers.get("x-lark-request-timestamp")
            or ""
        )
        nonce = (
            headers.get("X-Lark-Request-Nonce")
            or headers.get("x-lark-request-nonce")
            or ""
        )
        # 飞书 v1 签名算法：sha256(timestamp + nonce + encrypt_key + body)
        signed = f"{timestamp}{nonce}{self.encrypt_key}".encode("utf-8") + body
        expected = hashlib.sha256(signed).hexdigest()
        return hmac.compare_digest(expected, signature)
