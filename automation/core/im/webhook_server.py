# -*- coding: utf-8 -*-
"""IM Webhook HTTP 服务.

基于 Python 标准库 http.server，无需额外依赖即可接收飞书/企业微信事件推送。

支持：
- 飞书开放平台事件推送（含 challenge 校验）
- 企业微信回调（含 echostr 校验，简化实现）
- 通用 /webhook/<provider> 端点
"""

import json
import threading
import urllib.parse
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Dict


# 限制单个 webhook 请求体大小，避免恶意 Content-Length 触发内存/连接耗尽 DoS
_MAX_BODY_BYTES = 1 * 1024 * 1024


class WebhookHandler(BaseHTTPRequestHandler):
    """处理 IM Webhook 请求."""

    bot_service = None
    provider_type = "lark"

    def log_message(self, format, *args):
        # 简化日志，避免默认输出过多
        print(f"[Webhook] {self.address_string()} - {format % args}")

    def _send_json(self, status_code: int, data: Dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, status_code: int, text: str):
        body = text.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        raw = self.headers.get("Content-Length", "0")
        try:
            content_length = int(raw)
        except (TypeError, ValueError):
            # 非法 Content-Length 会让 do_POST 直接抛 ValueError 而断开连接，
            # 显式返回 400 更友好，也避免日志被异常栈淹没。
            raise _MalformedRequest(f"invalid Content-Length: {raw!r}")
        if content_length < 0 or content_length > _MAX_BODY_BYTES:
            raise _MalformedRequest(
                f"Content-Length out of range (0..{_MAX_BODY_BYTES}): {content_length}"
            )
        return self.rfile.read(content_length)

    def _verify_signature(self, body: bytes, query_params: Dict[str, str]) -> bool:
        """调用 provider.verify_webhook 校验请求签名.

        把 query 参数以 ``qs:<key>`` 形式合并进 headers 字典，
        以便企业微信 provider 读取 msg_signature/timestamp/nonce。
        """
        if self.bot_service is None:
            return False
        headers: Dict[str, str] = {}
        for key in self.headers.keys():
            headers[key] = self.headers.get(key, "")
        for k, v in query_params.items():
            headers[f"qs:{k}"] = v
        try:
            return self.bot_service.provider.verify_webhook(body, headers)
        except Exception as e:
            print(f"[Webhook] signature verification raised: {e}")
            return False

    def _handle_payload(self, payload: Dict, handler: Callable[[Dict], Dict]) -> None:
        if self.bot_service is None:
            self._send_json(500, {"error": "bot service not configured"})
            return
        try:
            result = handler(payload)
            self._send_json(200, result)
        except Exception as e:
            print(f"[Webhook] handle payload error: {e}")
            self._send_json(500, {"error": str(e)})

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        flat = {k: v[0] for k, v in params.items() if v}

        if parsed.path == "/webhook/wechat":
            # 企业微信 URL 校验：必须用 token 校验 msg_signature 通过后才能回显 echostr，
            # 否则任意请求都能让本服务回显 echostr，等同于绕过回调注册鉴权。
            echostr = flat.get("echostr", "")
            if echostr:
                provider = self.bot_service.provider if self.bot_service else None
                if provider is None:
                    self._send_json(500, {"error": "bot service not configured"})
                    return
                try:
                    ok = provider.verify_echostr(
                        flat.get("msg_signature", ""),
                        flat.get("timestamp", ""),
                        flat.get("nonce", ""),
                        echostr,
                    )
                except Exception as e:
                    print(f"[Webhook] wechat echostr verification raised: {e}")
                    ok = False
                if not ok:
                    self._send_text(403, "invalid signature")
                    return
                self._send_text(200, echostr)
                return

        self._send_json(404, {"error": "not found"})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query_params = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items() if v}
        try:
            body = self._read_body()
        except _MalformedRequest as e:
            self._send_json(400, {"error": str(e)})
            return

        if path == "/webhook/lark" or path == "/webhook/feishu":
            self._handle_lark(body, query_params)
        elif path == "/webhook/wechat":
            self._handle_wechat(body, query_params)
        elif path == "/webhook/generic":
            self._handle_generic(body, query_params)
        else:
            self._send_json(404, {"error": "unknown webhook endpoint"})

    def _handle_lark(self, body: bytes, query_params: Dict[str, str]):
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception as e:
            self._send_json(400, {"error": f"invalid json: {e}"})
            return

        # 飞书 challenge 校验（challenge 请求也需要签名校验，避免伪造 challenge 探测）
        if payload.get("type") == "url_verification":
            if not self._verify_signature(body, query_params):
                self._send_json(401, {"error": "invalid signature"})
                return
            self._send_json(200, {"challenge": payload.get("challenge", "")})
            return

        if not self._verify_signature(body, query_params):
            self._send_json(401, {"error": "invalid signature"})
            return
        self._handle_payload(payload, self.bot_service.handle_webhook_payload)

    def _handle_wechat(self, body: bytes, query_params: Dict[str, str]):
        if not self._verify_signature(body, query_params):
            self._send_json(401, {"error": "invalid signature"})
            return
        try:
            root = ET.fromstring(body.decode("utf-8"))
            payload = {child.tag: child.text or "" for child in root}
        except Exception as e:
            self._send_json(400, {"error": f"invalid xml: {e}"})
            return

        self._handle_payload(payload, self.bot_service.handle_webhook_payload)

    def _handle_generic(self, body: bytes, query_params: Dict[str, str]):
        # 通用 webhook 端点：基类 verify_webhook 默认放行，保留向后兼容。
        if not self._verify_signature(body, query_params):
            self._send_json(401, {"error": "invalid signature"})
            return
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception as e:
            self._send_json(400, {"error": f"invalid json: {e}"})
            return

        self._handle_payload(payload, self.bot_service.handle_webhook_payload)


class _MalformedRequest(Exception):
    """请求格式非法（如 Content-Length 非数字/越界），用于在 do_POST 中返回 400."""


class WebhookServer:
    """IM Webhook 服务封装."""

    def __init__(self, bot_service, host: str = "0.0.0.0", port: int = 8000):
        self.bot_service = bot_service
        self.host = host
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        WebhookHandler.bot_service = self.bot_service
        WebhookHandler.provider_type = self.bot_service.provider_type
        self.server = HTTPServer((self.host, self.port), WebhookHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        print(f"[WebhookServer] started at http://{self.host}:{self.port}")
        print(f"  飞书 endpoint: http://{self.host}:{self.port}/webhook/lark")
        print(f"  企业微信 endpoint: http://{self.host}:{self.port}/webhook/wechat")

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            print("[WebhookServer] stopped")
