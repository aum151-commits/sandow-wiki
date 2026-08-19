# -*- coding: utf-8 -*-
"""Изолированная проверка: что реально происходит при клике на кнопку
вставки видео в редакторе Quill — открывает диалог или свою тултип-панель.
"""
from playwright.sync_api import sync_playwright

BASE = "https://sandow-wiki.onrender.com"
PASSWORD = "Sandow2026wiki"
OUT = r"C:\Users\sando\AppData\Local\Temp\claude\D---------\99486629-1b8f-4996-b4f7-26013e825d51\scratchpad"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    dialogs = []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

    page.goto(f"{BASE}/login", wait_until="networkidle")
    page.fill("#name", "Проверка")
    page.fill("#password", PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")
    page.goto(f"{BASE}/wiki/new", wait_until="networkidle")
    page.wait_for_selector(".ql-editor")
    page.click("button.ql-video")
    page.wait_for_timeout(500)
    page.screenshot(path=f"{OUT}/wiki_video_button_click.png")
    print("dialogs fired:", dialogs)
    print("tooltip visible:", page.locator(".ql-tooltip").count())
    html = page.locator(".ql-tooltip").first.inner_html() if page.locator(".ql-tooltip").count() else None
    print("tooltip html:", html)
    browser.close()
