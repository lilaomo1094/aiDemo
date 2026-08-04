# -*- coding: utf-8 -*-
import pytest

from automation.core.im import IMMessage, create_im_provider
from automation.core.im.lark_provider import LarkProvider
from automation.core.im.wechat_provider import WeChatProvider


class TestIMMessage:
    def test_is_command_with_slash(self):
        msg = IMMessage(message_id="1", sender_id="u1", content="/run config.py")
        assert msg.is_command() is True
        assert msg.get_command() == "run"

    def test_is_command_with_chinese(self):
        msg = IMMessage(message_id="2", sender_id="u1", content="执行测试 config.py")
        assert msg.is_command() is True
        assert msg.get_command() == ""

    def test_is_not_command(self):
        msg = IMMessage(message_id="3", sender_id="u1", content="hello")
        assert msg.is_command() is False


class TestLarkProvider:
    def test_parse_open_platform_event(self):
        provider = LarkProvider({"mock": True})
        payload = {
            "event": {
                "message": {
                    "message_id": "m1",
                    "chat_id": "c1",
                    "msg_type": "text",
                    "content": '{"text": "/run config.py"}',
                },
                "sender": {"sender_id": {"open_id": "u1"}},
            }
        }
        msg = provider.parse_webhook_payload(payload)
        assert msg.message_id == "m1"
        assert msg.sender_id == "u1"
        assert msg.channel == "c1"
        assert msg.content == "/run config.py"

    def test_send_text_mock(self):
        provider = LarkProvider({"mock": True})
        assert provider.send_text("u1", "hello") is True


class TestWeChatProvider:
    def test_parse_webhook_payload(self):
        provider = WeChatProvider({"mock": True})
        payload = {
            "MsgType": "text",
            "MsgId": "m1",
            "FromUserName": "u1",
            "ChatId": "c1",
            "Content": "/status task-1",
        }
        msg = provider.parse_webhook_payload(payload)
        assert msg.message_id == "m1"
        assert msg.sender_id == "u1"
        assert msg.content == "/status task-1"


class TestFactory:
    def test_create_lark(self):
        provider = create_im_provider("lark", {"mock": True})
        assert isinstance(provider, LarkProvider)

    def test_create_wechat(self):
        provider = create_im_provider("wechat", {"mock": True})
        assert isinstance(provider, WeChatProvider)

    def test_create_unsupported(self):
        with pytest.raises(ValueError):
            create_im_provider("unknown", {})
