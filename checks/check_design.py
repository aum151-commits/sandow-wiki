# -*- coding: utf-8 -*-
"""Визуальная проверка нового дизайна (паспорт стиля) — реальный контент,
несколько экранов и движков."""
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
OUT = r"C:\Users\sando\AppData\Local\Temp\claude\D---------\99486629-1b8f-4996-b4f7-26013e825d51\scratchpad"


def register(page, name, username, password, invite):
    page.goto(f"{BASE}/register", wait_until="networkidle")
    page.fill("#display_name", name)
    page.fill("#username", username)
    page.fill("#password", password)
    page.fill("#invite", invite)
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")


def shots(engine, name, viewports, full_page=True):
    browser = engine.launch()
    for vw, vh, tag in viewports:
        page = browser.new_page(viewport={"width": vw, "height": vh})
        register(page, f"Дизайн {name}", f"design2_{name}_{vw}", "checkpass123", "test-admin-invite")
        page.screenshot(path=f"{OUT}/design_{name}_{tag}_login_home.png", full_page=full_page)
        page.goto(f"{BASE}/course", wait_until="networkidle")
        page.screenshot(path=f"{OUT}/design_{name}_{tag}_course_list.png", full_page=full_page)
        page.click("text=Занятие 1.2")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=f"{OUT}/design_{name}_{tag}_lesson.png", full_page=full_page)
        page.close()
    browser.close()


with sync_playwright() as p:
    shots(p.chromium, "chromium", [(1280, 1400, "desktop"), (390, 1400, "mobile")])
with sync_playwright() as p:
    # full_page=True снимает битые скриншоты в WebKit на этой машине (несовпадение
    # DPR) — сама вёрстка в порядке (подтверждено scrollWidth==clientWidth и обычным
    # viewport-скриншотом), поэтому здесь используем viewport-скриншот.
    shots(p.webkit, "webkit", [(390, 844, "mobile")], full_page=False)

print("Готово, скриншоты в", OUT)
