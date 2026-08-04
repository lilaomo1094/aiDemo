# -*- coding: utf-8 -*-
from automation.core.im.bot_service import IntentParser


class TestIntentParser:
    def setup_method(self):
        self.parser = IntentParser(
            project_aliases={"电商项目": "config/ecommerce.py", "登录": "config/login.py"},
            default_config_path="config/default.py",
        )

    def test_parse_run_with_alias(self):
        intent, params = self.parser.parse("测试一下电商项目，优先级3")
        assert intent == "run"
        assert params["target"] == "config/ecommerce.py"
        assert params["priority"] == 3

    def test_parse_run_with_path(self):
        intent, params = self.parser.parse("帮我执行 config/demo.py")
        assert intent == "run"
        assert params["target"] == "config/demo.py"

    def test_parse_run_default(self):
        intent, params = self.parser.parse("跑一下")
        assert intent == "run"
        assert params["target"] == "config/default.py"
        assert params["priority"] == 5

    def test_parse_slash_run(self):
        intent, params = self.parser.parse("/run config/demo.py 2")
        assert intent == "run"
        assert params["target"] == "config/demo.py"
        assert params["priority"] == 2

    def test_parse_status(self):
        intent, params = self.parser.parse("查一下 TASK-abc12345 的状态")
        assert intent == "status"
        assert params["task_id"] == "TASK-abc12345"

    def test_parse_cancel(self):
        intent, params = self.parser.parse("取消 TASK-abc12345")
        assert intent == "cancel"
        assert params["task_id"] == "TASK-abc12345"

    def test_parse_help(self):
        intent, params = self.parser.parse("/help")
        assert intent == "help"

    def test_parse_unknown(self):
        intent, params = self.parser.parse("hello world")
        assert intent == "unknown"
