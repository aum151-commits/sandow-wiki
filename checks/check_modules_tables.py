# -*- coding: utf-8 -*-
"""Визуальная проверка модулей и таблиц после переноса HTML-контента."""
import sys
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
OUT = r"C:\Users\sando\AppData\Local\Temp\claude\D---------\99486629-1b8f-4996-b4f7-26013e825d51\scratchpad"
errors = []


def check(name, cond):
    print(f"[{'OK' if cond else 'FAIL'}] {name}")
    if not cond:
        errors.append(name)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(f"{BASE}/register", wait_until="networkidle")
    page.fill("#display_name", "Проверка модулей")
    page.fill("#username", "modules_check")
    page.fill("#password", "checkpass123")
    page.fill("#invite", "test-admin-invite")
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")

    page.goto(f"{BASE}/course", wait_until="networkidle")
    body = page.inner_text("body")
    check("Модуль 1 виден", "Модуль 1" in body)
    check("Модуль 2 виден", "Модуль 2" in body)
    check("Модуль 3 виден", "Модуль 3" in body)
    check("Модуль 4 виден", "Модуль 4" in body)
    page.screenshot(path=f"{OUT}/modules_list.png", full_page=True)

    page.click("text=Занятие 1.2")
    page.wait_for_load_state("networkidle")
    check("таблица отрисована", page.locator(".content-html table").count() >= 3)
    check("цена Bronze видна", "3 900" in page.inner_text(".content-html"))
    check("заголовок h3 отрисован жирным блоком", page.locator(".content-html h3").count() > 0)
    page.screenshot(path=f"{OUT}/lesson_tables.png", full_page=True)

    # мобильный вид
    mobile = browser.new_page(viewport={"width": 390, "height": 844})
    mobile.goto(f"{BASE}/login", wait_until="networkidle")
    mobile.fill("#username", "modules_check")
    mobile.fill("#password", "checkpass123")
    mobile.click("button[type=submit]")
    mobile.wait_for_load_state("networkidle")
    mobile.goto(f"{BASE}/course/" + page.url.rsplit("/", 1)[-1], wait_until="networkidle")
    mobile.screenshot(path=f"{OUT}/lesson_tables_mobile.png", full_page=True)

    browser.close()

print()
if errors:
    print(f"ИТОГ: {len(errors)} проблем — {errors}")
    sys.exit(1)
print("ИТОГ: всё прошло без ошибок")
