#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""merchant-dev.nexuscube.cn 登录演示脚本.

用法:
    python demo_merchant_login.py

环境要求:
    - 安装 playwright: pip install playwright
    - 安装浏览器: playwright install chromium
    - 当前网络可访问 https://merchant-dev.nexuscube.cn
"""

from pathlib import Path

from playwright.sync_api import sync_playwright


URL = "https://merchant-dev.nexuscube.cn/#/login"
ACCOUNT = "13411985758"
PASSWORD = "888888"
OUTPUT_DIR = Path("output")


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        print(f"1. 打开登录页: {URL}")
        page.goto(URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        page.screenshot(path=str(OUTPUT_DIR / "merchant_step1_open.png"), full_page=True)
        print(f"   标题: {page.title()}")
        print(f"   URL: {page.url}")

        print("2. 查找账号/密码输入框")
        phone_input = page.locator("input[type=tel], input[name=mobile], input[placeholder*=手机], input[placeholder*=账号]").first
        pwd_input = page.locator("input[type=password]").first

        if phone_input.count() == 0 or pwd_input.count() == 0:
            print("   未定位到输入框，尝试通用 input 策略")
            inputs = page.query_selector_all("input")
            for inp in inputs:
                input_type = inp.get_attribute("type") or ""
                placeholder = inp.get_attribute("placeholder") or ""
                if input_type == "tel" or "手机" in placeholder or "账号" in placeholder:
                    phone_input = inp
                elif input_type == "password" or "密码" in placeholder:
                    pwd_input = inp

        print(f"3. 输入账号: {ACCOUNT}")
        phone_input.fill(ACCOUNT)
        page.wait_for_timeout(500)

        print("4. 输入密码")
        pwd_input.fill(PASSWORD)
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUTPUT_DIR / "merchant_step2_filled.png"), full_page=True)

        print("5. 点击登录")
        login_btn = page.locator("button:has-text('登录'), button[type=submit], .login-btn").first
        if login_btn.count() > 0:
            login_btn.click()
        else:
            pwd_input.press("Enter")

        page.wait_for_timeout(5000)
        page.screenshot(path=str(OUTPUT_DIR / "merchant_step3_logged_in.png"), full_page=True)
        print(f"   登录后标题: {page.title()}")
        print(f"   登录后URL: {page.url}")

        browser.close()
    print("6. 演示完成，截图保存在 output/ 目录")


if __name__ == "__main__":
    main()
