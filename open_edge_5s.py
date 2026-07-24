#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""使用本地 Edge 浏览器打开指定页面并保持 5 秒.

用法:
    python open_edge_5s.py [URL]

示例:
    python open_edge_5s.py
    python open_edge_5s.py https://merchant-dev.nexuscube.cn/#/login
"""

import argparse
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


DEFAULT_URL = "https://merchant-dev.nexuscube.cn/#/login"
OUTPUT_DIR = Path("output")


def main():
    parser = argparse.ArgumentParser(description="使用 Edge 浏览器打开页面并保持 5 秒")
    parser.add_argument(
        "url",
        nargs="?",
        default=DEFAULT_URL,
        help=f"目标 URL（默认: {DEFAULT_URL}）",
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(exist_ok=True)

    print(f"使用 Edge 打开: {args.url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel="msedge")
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        page = context.new_page()
        page.goto(args.url, timeout=30000, wait_until="domcontentloaded")

        page.wait_for_timeout(1000)
        screenshot_path = OUTPUT_DIR / "edge_opened.png"
        page.screenshot(path=str(screenshot_path), full_page=True)

        print(f"页面标题: {page.title()}")
        print(f"当前 URL: {page.url}")
        print(f"截图保存: {screenshot_path}")
        print("保持 5 秒...")
        time.sleep(5)

        browser.close()
    print("浏览器已关闭")


if __name__ == "__main__":
    main()
