# -*- coding: utf-8 -*-
"""企业微信 / 微信 Provider.

当前为骨架实现：支持企业微信 Webhook 机器人发送文本/文件消息；
接收消息通过回调 URL 解析。
"""

import json
from typing import Any, Dict

import requests

from .base import IMMessage, IMProvider


class WeChatProvider(IMProvider):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.webhook_url = config.get("webhook_url", "")
        self.corp_id = config.get("corp_id", "")
        self.corp_secret = config.get("corp_secret", "")
        self.agent_id = config.get("agent_id", "")
        # 企业微信回调 Token，用于校验 msg_signature。
        # 配置后才会启用签名校验；未配置时保持明文模式兼容。
        self.token = config.get("token", "")
        self.mock = config.get("mock", False)

    def send_text(self, receiver: str, content: str, **kwargs) -> bool:
        """通过企业微信群机器人 Webhook 发送文本消息.

        receiver 在此模式下被忽略，使用 config 中的 webhook_url。
        """
        if self.mock:
            print(f"[WeChat Mock] send: {content[:200]}")
            return True

        url = kwargs.get("webhook_url") or self.webhook_url
        if not url:
            print("[WeChat] 缺少 webhook_url")
            return False

        payload = {"msgtype": "text", "text": {"content": content}}
        mentioned = kwargs.get("mentioned_list")
        if mentioned:
            payload["text"]["mentioned_list"] = mentioned

        try:
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if data.get("errcode") != 0:
                print(f"[WeChat] send_text failed: {data}")
                return False
            return True
        except Exception as e:
            print(f"[WeChat] send_text failed: {e}")
            return False

    def send_file(self, receiver: str, file_path: str, **kwargs) -> bool:
        """通过企业微信机器人发送文件（需先上传获取 media_id）."""
        if self.mock:
            print(f"[WeChat Mock] send file: {file_path}")
            return True

        url = kwargs.get("webhook_url") or self.webhook_url
        if not url:
            print("[WeChat] 缺少 webhook_url")
            return False

        # 企业微信机器人文件消息需要先调用 upload_media 接口
        # 简化实现：直接返回失败，提示使用 media_id
        print("[WeChat] send_file 需先调用 upload_media 获取 media_id")
        return False

    def parse_webhook_payload(self, payload: Dict[str, Any]) -> IMMessage:
        """解析企业微信回调消息.

        支持格式：
        { "MsgType": "text", "Content": "...", "FromUserName": "...", "ChatId": "..." }
        """
        msg_type = payload.get("MsgType", "text")
        content = ""
        if msg_type == "text":
            content = payload.get("Content", "")
        elif msg_type == "event":
            content = payload.get("EventKey", "")

        return IMMessage(
            message_id=payload.get("MsgId", ""),
            sender_id=payload.get("FromUserName", ""),
            sender_name=payload.get("FromUserName", ""),
            content=content,
            channel=payload.get("ChatId", ""),
            raw=payload,
        )

    def verify_webhook(self, body: bytes, headers: Dict[str, str]) -> bool:
        """校验企业微信事件回调签名 (msg_signature).

        企业微信把 msg_signature / timestamp / nonce 放在 URL query 中。
        WebhookServer 会把 query 参数合并进 headers（前缀 ``qs:``）以便这里读取。
        未配置 token 时放行（兼容明文模式）；配置 token 后必须校验。
        """
        if not self.token:
            return True

        import hashlib
        import hmac

        msg_signature = headers.get("qs:msg_signature") or ""
        timestamp = headers.get("qs:timestamp") or ""
        nonce = headers.get("qs:nonce") or ""
        if not msg_signature:
            return False
        # 企业微信签名算法：sha1(sort([token, timestamp, nonce, body]))
        expected = hashlib.sha1(
            "".join(sorted([self.token, timestamp, nonce, body.decode("utf-8", errors="replace")])).encode("utf-8")
        ).hexdigest()
        return hmac.compare_digest(expected, msg_signature)

    def verify_echostr(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> bool:
        """校验企业微信 URL 验证请求的 msg_signature.

        企业微信注册回调时会以 GET 形式发送 msg_signature/timestamp/nonce/echostr，
        服务端必须用 sha1(sort([token, timestamp, nonce, echostr])) 校验通过后才能回显。
        未配置 token 时放行（兼容明文模式）。
        """
        if not self.token:
            return True
        if not msg_signature:
            return False
        import hashlib
        import hmac

        expected = hashlib.sha1(
            "".join(sorted([self.token, timestamp, nonce, echostr])).encode("utf-8")
        ).hexdigest()
        return hmac.compare_digest(expected, msg_signature)
