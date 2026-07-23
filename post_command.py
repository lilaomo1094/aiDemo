#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令发布入口：向本地 Webhook Server 或 IM Bot 发送测试指令.

用法:
    # 发送文字命令到本地 webhook server
    python post_command.py --text "测试一下电商项目，优先级3"

    # 发送 /run 命令
    python post_command.py --text "/run config/project_config.py 3"

    # 查询任务状态
    python post_command.py --text "/status TASK-xxxxxx"

    # 指定 webhook 地址
    python post_command.py --url http://localhost:8000/webhook/lark --text "跑一下登录模块"
"""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

script_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(script_dir))

from automation.core.im import IMBotService, create_im_provider
from automation.core.scheduler import TaskScheduler


def send_to_webhook(url: str, payload: dict) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_local(text: str, im_config_path: str):
    """本地直接调用 BotService（无需启动 HTTP 服务）."""
    with open(im_config_path, "r", encoding="utf-8") as f:
        im_config = json.load(f)

    scheduler = TaskScheduler(max_workers=1, state_dir="output/scheduler")
    scheduler.start()
    bot = IMBotService(scheduler, im_config)

    # 构造一个模拟的 IM 消息
    from automation.core.im import IMMessage

    message = IMMessage(message_id="CLI-001", sender_id="cli_user", content=text)
    reply = bot.handle_message(message)
    print("机器人回复:")
    print(reply)

    if "已提交测试任务" in reply:
        import re

        match = re.search(r"任务ID:\s*(TASK-[a-f0-9]+)", reply)
        if match:
            task_id = match.group(1)
            print(f"\n等待任务 {task_id} 完成...")
            task = scheduler.wait_for_completion(task_id, timeout=300)
            print(f"任务状态: {task.status.value if task else 'unknown'}")

    scheduler.stop()


def parse_cli():
    parser = argparse.ArgumentParser(description="proDemoA 命令发布入口")
    parser.add_argument("--text", required=True, help="要发送的指令文本")
    parser.add_argument("--url", default="http://localhost:8000/webhook/lark", help="Webhook 地址")
    parser.add_argument("--local", action="store_true", help="本地直接调用 BotService，不经过 HTTP")
    parser.add_argument("--im-config", default="config/im_config.json", help="IM 配置文件路径")
    return parser.parse_args()


def main():
    args = parse_cli()
    if args.local:
        run_local(args.text, args.im_config)
        return

    # 默认通过 HTTP 发送飞书格式 payload
    payload = {
        "event": {
            "message": {
                "message_id": "CLI-001",
                "chat_id": "cli_chat",
                "msg_type": "text",
                "content": json.dumps({"text": args.text}, ensure_ascii=False),
            },
            "sender": {"sender_id": {"open_id": "cli_user"}},
        }
    }
    result = send_to_webhook(args.url, payload)
    print("Webhook 响应:")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
