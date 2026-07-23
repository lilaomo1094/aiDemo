#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多任务调度器 + IM Bot 入口.

用法:
    # 启动调度器（仅本地多线程执行任务）
    python run_scheduler.py --config config/project_config.py

    # 启动调度器并开启 IM 机器人（支持飞书/企业微信 webhook）
    python run_scheduler.py --im-provider lark --im-config config/im_config.json

    # 提交单个任务
    python run_scheduler.py --submit config/project_config.py --priority 3
"""

import argparse
import json
import sys
import time
from pathlib import Path

script_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(script_dir))

from automation.core.config import load_config
from automation.core.im import IMBotService, create_im_provider
from automation.core.scheduler import TaskScheduler


def load_im_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def start_scheduler(args):
    scheduler = TaskScheduler(max_workers=args.max_workers, state_dir=args.state_dir)
    scheduler.start()
    print(f"调度器已启动，工作线程数: {args.max_workers}")

    bot = None
    if args.im_provider:
        im_config = load_im_config(args.im_config) if args.im_config else {"provider": args.im_provider, "mock": True}
        im_config.setdefault("provider", args.im_provider)
        bot = IMBotService(scheduler, im_config)
        print(f"IM Bot 已接入: {args.im_provider}")

    if args.submit:
        task_id = scheduler.submit(args.submit, priority=args.priority)
        print(f"已提交任务: {task_id}")
        if not args.im_provider:
            task = scheduler.wait_for_completion(task_id, timeout=args.timeout)
            print(f"任务完成，状态: {task.status.value if task else 'unknown'}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止调度器...")
        scheduler.stop()


def submit_only(args):
    scheduler = TaskScheduler(max_workers=args.max_workers, state_dir=args.state_dir)
    scheduler.start()
    task_id = scheduler.submit(args.submit, priority=args.priority)
    print(f"已提交任务: {task_id}")
    task = scheduler.wait_for_completion(task_id, timeout=args.timeout)
    print(f"任务完成，状态: {task.status.value if task else 'unknown'}")
    scheduler.stop()


def parse_cli():
    parser = argparse.ArgumentParser(description="proDemoA 多任务调度器")
    parser.add_argument("--max-workers", type=int, default=4, help="并发工作线程数")
    parser.add_argument("--state-dir", default="output/scheduler", help="任务状态持久化目录")
    parser.add_argument("--submit", help="提交单个测试任务配置文件")
    parser.add_argument("--priority", type=int, default=5, help="任务优先级（1-10，数字越小越优先）")
    parser.add_argument("--timeout", type=float, default=3600, help="等待任务完成超时时间（秒）")
    parser.add_argument("--im-provider", choices=["lark", "feishu", "wechat", "wecom"], help="IM 提供商")
    parser.add_argument("--im-config", help="IM 配置文件路径（JSON）")
    return parser.parse_args()


def main():
    args = parse_cli()
    if args.submit and not args.im_provider:
        submit_only(args)
    else:
        start_scheduler(args)


if __name__ == "__main__":
    main()
