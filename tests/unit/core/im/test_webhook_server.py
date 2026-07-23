# -*- coding: utf-8 -*-
import json
import threading
import time
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
