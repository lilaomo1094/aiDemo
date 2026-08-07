# -*- coding: utf-8 -*-
import hashlib
import json
import socket
import threading
import time
import urllib.error
import urllib.request

import pytest

from automation.core.im import IMBotService, WebhookServer
from automation.core.scheduler import TaskScheduler


@pytest.fixture
def webhook_server(tmp_path):
    scheduler = TaskScheduler(max_workers=1, state_dir=str(tmp_path / "scheduler"))
    scheduler.start()
    im_config = {"provider": "lark", "mock": True, "admin_users": ["cli_user"]}
    bot = IMBotService(scheduler, im_config)
    server = WebhookServer(bot, host="127.0.0.1", port=0)
    server.start()
    actual_port = server.server.server_address[1]
    time.sleep(0.2)
    yield server, actual_port
    server.stop()
    scheduler.stop()


@pytest.fixture
def encrypted_webhook_server(tmp_path):
    """配置了 encrypt_key 的 webhook 服务，用于测试签名校验."""
    scheduler = TaskScheduler(max_workers=1, state_dir=str(tmp_path / "scheduler"))
    scheduler.start()
    im_config = {
        "provider": "lark",
        "mock": True,
        "admin_users": ["cli_user"],
        "encrypt_key": "test-encrypt-key-123",
    }
    bot = IMBotService(scheduler, im_config)
    server = WebhookServer(bot, host="127.0.0.1", port=0)
    server.start()
    actual_port = server.server.server_address[1]
    time.sleep(0.2)
    yield server, actual_port, im_config["encrypt_key"]
    server.stop()
    scheduler.stop()


def _lark_signature(body: bytes, timestamp: str, nonce: str, encrypt_key: str) -> str:
    """复现飞书 X-Lark-Signature v1 算法：sha256(timestamp + nonce + encrypt_key + body)."""
    signed = f"{timestamp}{nonce}{encrypt_key}".encode("utf-8") + body
    return hashlib.sha256(signed).hexdigest()


class TestWebhookServer:
    def test_lark_url_verification(self, webhook_server):
        server, port = webhook_server
        payload = json.dumps({"type": "url_verification", "challenge": "abc123"}).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/webhook/lark",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        assert data["challenge"] == "abc123"

    def test_lark_message_webhook(self, webhook_server):
        server, port = webhook_server
        payload = {
            "event": {
                "message": {
                    "message_id": "m1",
                    "chat_id": "c1",
                    "msg_type": "text",
                    "content": '{"text": "/help"}',
                },
                "sender": {"sender_id": {"open_id": "cli_user"}},
            }
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/webhook/lark",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        assert "message" in result
        assert "可用命令" in result["message"]


class TestWebhookSignatureVerification:
    """回归测试：配置 encrypt_key 后必须校验签名，避免 admin 身份伪造."""

    def test_unsigned_request_rejected_when_encrypt_key_configured(self, encrypted_webhook_server):
        _server, port, _key = encrypted_webhook_server
        payload = json.dumps({
            "event": {
                "message": {
                    "message_id": "m1",
                    "chat_id": "c1",
                    "msg_type": "text",
                    "content": '{"text": "/help"}',
                },
                "sender": {"sender_id": {"open_id": "cli_user"}},
            }
        }).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/webhook/lark",
            data=payload,
            headers={"Content-Type": "application/json"},  # 故意不带 X-Lark-Signature
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req, timeout=5)
        assert exc.value.code == 401, "未签名请求应被拒绝（防止伪造 sender_id 冒充 admin）"

    def test_correctly_signed_request_accepted(self, encrypted_webhook_server):
        _server, port, encrypt_key = encrypted_webhook_server
        payload = json.dumps({
            "event": {
                "message": {
                    "message_id": "m1",
                    "chat_id": "c1",
                    "msg_type": "text",
                    "content": '{"text": "/help"}',
                },
                "sender": {"sender_id": {"open_id": "cli_user"}},
            }
        }).encode("utf-8")
        timestamp = "1700000000"
        nonce = "abc"
        signature = _lark_signature(payload, timestamp, nonce, encrypt_key)
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/webhook/lark",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Lark-Signature": signature,
                "X-Lark-Request-Timestamp": timestamp,
                "X-Lark-Request-Nonce": nonce,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        assert "message" in result
        assert "可用命令" in result["message"]

    def test_tampered_signature_rejected(self, encrypted_webhook_server):
        _server, port, _encrypt_key = encrypted_webhook_server
        payload = json.dumps({
            "event": {
                "message": {"message_id": "m1", "chat_id": "c1", "msg_type": "text",
                            "content": '{"text": "/help"}'},
                "sender": {"sender_id": {"open_id": "cli_user"}},
            }
        }).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/webhook/lark",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Lark-Signature": "deadbeef" * 8,  # 错误签名
                "X-Lark-Request-Timestamp": "1700000000",
                "X-Lark-Request-Nonce": "abc",
            },
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req, timeout=5)
        assert exc.value.code == 401

    def test_oversized_content_length_rejected(self, webhook_server):
        """回归测试：超大 Content-Length 应直接 400，避免 rfile.read 阻塞导致内存/连接耗尽."""
        _server, port = webhook_server
        # 用原始 socket 发送精确的恶意请求，避免 urllib 改写 Content-Length
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(("127.0.0.1", port))
        sock.sendall(
            b"POST /webhook/lark HTTP/1.1\r\n"
            b"Host: 127.0.0.1\r\n"
            b"Content-Length: 99999999\r\n"
            b"\r\n"
        )
        resp = sock.recv(4096)
        sock.close()
        assert b" 400 " in resp.split(b"\r\n")[0], "超大 Content-Length 应返回 400"

    def test_invalid_content_length_rejected(self, webhook_server):
        """回归测试：非数字 Content-Length 应返回 400 而非断开连接."""
        _server, port = webhook_server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(("127.0.0.1", port))
        sock.sendall(
            b"POST /webhook/lark HTTP/1.1\r\n"
            b"Host: 127.0.0.1\r\n"
            b"Content-Length: abc\r\n"
            b"\r\n"
        )
        resp = sock.recv(4096)
        sock.close()
        assert b" 400 " in resp.split(b"\r\n")[0], "非数字 Content-Length 应返回 400"
