# -*- coding: utf-8 -*-
import pytest

from automation.core.im import IMMessage, IMBotService
from automation.core.scheduler import TaskScheduler


@pytest.fixture
def scheduler(tmp_path):
    s = TaskScheduler(max_workers=1, state_dir=str(tmp_path / "scheduler"))
    s.start()
    yield s
    s.stop()


@pytest.fixture
def bot(scheduler):
    config = {"provider": "lark", "mock": True, "default_config_path": "config/project_config.py"}
    return IMBotService(scheduler, config)


class TestIMBotService:
    def test_handle_help(self, bot):
        msg = IMMessage(message_id="1", sender_id="u1", content="/help")
        reply = bot.handle_message(msg)
        assert "可用命令" in reply

    def test_handle_unknown_command(self, bot):
        msg = IMMessage(message_id="2", sender_id="u1", content="/foo")
        reply = bot.handle_message(msg)
        assert "未知命令" in reply

    def test_handle_non_command(self, bot):
        msg = IMMessage(message_id="3", sender_id="u1", content="hello")
        reply = bot.handle_message(msg)
        assert "未识别为指令" in reply

    def test_handle_status_empty(self, bot):
        msg = IMMessage(message_id="4", sender_id="u1", content="/status")
        reply = bot.handle_message(msg)
        assert "当前没有任务" in reply
