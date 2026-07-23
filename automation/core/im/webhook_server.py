# -*- coding: utf-8 -*-
"""IM Webhook HTTP 服务.

基于 Python 标准库 http.server，无需额外依赖即可接收飞书/企业微信事件推送。

支持：
- 飞书开放平台事件推送（含 challenge 校验）
- 企业微信回调（含 echostr 校验，简化实现）
- 通用 /webhook/<provider> 端点
"""

import hashlib
import hmac
import json
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict

from .base import IMMessage
from .factory import create_im_provider


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
        content_length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(content_length)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/webhook/wechat":
            # 企业微信 URL 校验
            echostr = params.get("echostr", [""])[0]
            if echostr:
                self._send_text(200, echostr)
                return

        self._send_json(404, {"error": "not found"})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/webhook/lark" or path == "/webhook/feishu":
            self._handle_lark()
        elif path == "/webhook/wechat":
            self._handle_wechat()
        elif path == "/webhook/generic":
            self._handle_generic()
        else:
            self._send_json(404, {"error": "unknown webhook endpoint"})

    def _handle_lark(self):
        body = self._read_body()
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception as e:
            self._send_json(400, {"error": f"invalid json: {e}"})
            return

        # 飞书 challenge 校验
        if payload.get("type") == "url_verification":
            challenge = payload.get("challenge", "")
            self._send_json(200, {"challenge": challenge})
            return

        if self.bot_service is None:
            self._send_json(500, {"error": "bot service not configured"})
            return

        try:
            result = self.bot_service.handle_webhook_payload(payload)
            self._send_json(200, result)
        except Exception as e:
            print(f"[Webhook] handle lark payload error: {e}")
            self._send_json(500, {"error": str(e)})

    def _handle_wechat(self):
        body = self._read_body()
        try:
            import xml.etree.ElementTree as ET

            root = ET.fromstring(body.decode("utf-8"))
            payload = {child.tag: child.text or "" for child in root}
        except Exception as e:
            self._send_json(400, {"error": f"invalid xml: {e}"})
            return

        if self.bot_service is None:
            self._send_json(500, {"error": "bot service not configured"})
            return

        try:
            result = self.bot_service.handle_webhook_payload(payload)
            self._send_json(200, result)
        except Exception as e:
            print(f"[Webhook] handle wechat payload error: {e}")
            self._send_json(500, {"error": str(e)})

    def _handle_generic(self):
        body = self._read_body()
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception as e:
            self._send_json(400, {"error": f"invalid json: {e}"})
            return

        if self.bot_service is None:
            self._send_json(500, {"error": "bot service not configured"})
            return

        try:
            result = self.bot_service.handle_webhook_payload(payload)
            self._send_json(200, result)
        except Exception as e:
            self._send_json(500, {"error": str(e)})


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
        self.server.allow_reuse_address = True
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
