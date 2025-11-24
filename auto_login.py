import os
import json
import re
from pathlib import Path
from playwright.sync_api import Playwright, sync_playwright

import schedule
import time
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

# マトリクス表の読み込み
with open("matrix.json", "r") as f:
    MATRIX = json.load(f)

def get_matrix(code):
    row = code[0]
    col = int(code[1]) - 1
    return MATRIX[row][col]

def job():
    print("実行されました！", datetime.now())
    with sync_playwright() as playwright:
        run(playwright)
    exit()

schedule.every().monday.at("14:07").do(job)

def run(playwright: Playwright):
    USERNAME = os.getenv("TITECH_USERNAME")
    PASSWORD = os.getenv("TITECH_PASSWORD")
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    page.goto("https://portal.titech.ac.jp/")
    page.get_by_role("button", name="同意（マトリクス/OTP/ソフトトークン認証）").click()

    # ユーザーネーム
    page.locator("input[name='usr_name']").fill(USERNAME)

    # パスワード
    page.locator("input[name='usr_password']").fill(PASSWORD)
    page.get_by_role("button", name="OK").click()

    # Grid 認証
    page.get_by_role("combobox").select_option("GridAuthOption")
    page.get_by_role("button", name="OK").click()

    # 認証テーブルの行を取得
    labels_locator = page.locator("th").filter(has_text=re.compile(r"\[[A-Z],\s*\d+\]"))
    count = labels_locator.count()

    print(f"Found {count} matrix inputs.")

    for i in range(count):
        target_th = labels_locator.nth(i)
        label_text = target_th.inner_text().strip()

        match = re.search(r"\[([A-Z]),\s*([0-9]+)\]", label_text)

        if match:
            row_char = match.group(1)
            col_num = int(match.group(2))
            
            value = MATRIX[row_char][col_num-1]

            print(f"Filling {label_text} with {value}")

            input_box = target_th.locator("xpath=..").locator("input")
            input_box.fill(str(value))

    # OK ボタンをクリック
    page.get_by_role("button", name="OK").click()

    # 教務Webへ
    with page.expect_popup() as popup_info:
        page.get_by_role("link", name="教務Webシステム（Web system for S&F）").click()
    page1 = popup_info.value

    page1.get_by_role("link", name="施設予約", exact=True).click()

    # Cookieを取得
    cookies = context.cookies()

    # Cookieを保存
    cookie_json_path = Path("cookies.json")
    cookie_json_path.write_text(json.dumps(cookies, indent=2))

    print("Press Enter to close the browser...")
    input()

    # ページを閉じる
    context.close()
    # ブラウザを閉じる
    browser.close()

while True:
    schedule.run_pending()
    time.sleep(1)
