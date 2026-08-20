# -*- coding: utf-8 -*-
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
    check("по умолчанию тёмная (нет data-theme)", page.get_attribute("html", "data-theme") is None)
    page.screenshot(path=f"{OUT}/theme_dark_default.png")

    page.click("#themeToggle")
    page.wait_for_timeout(200)
    check("после клика data-theme=light", page.get_attribute("html", "data-theme") == "light")
    page.screenshot(path=f"{OUT}/theme_light.png")

    # регистрация, переход по страницам — тема должна сохраняться
    page.fill("#display_name", "Тест темы")
    page.fill("#username", "theme_toggle_check")
    page.fill("#password", "checkpass123")
    page.fill("#invite", "test-admin-invite")
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")
    check("после регистрации тема осталась светлой", page.get_attribute("html", "data-theme") == "light")

    page.goto(f"{BASE}/course", wait_until="networkidle")
    check("на другой странице (без перезагрузки JS) тема светлая", page.get_attribute("html", "data-theme") == "light")
    page.screenshot(path=f"{OUT}/theme_light_course.png", full_page=True)

    # перезагрузка страницы — должна остаться (localStorage)
    page.reload(wait_until="networkidle")
    check("после перезагрузки тема осталась светлой (localStorage)", page.get_attribute("html", "data-theme") == "light")

    # переключить обратно
    page.click("#themeToggle")
    page.wait_for_timeout(200)
    check("переключение обратно на тёмную работает", page.get_attribute("html", "data-theme") is None)

    browser.close()

print()
if errors:
    print(f"ИТОГ: {len(errors)} проблем — {errors}")
    sys.exit(1)
print("ИТОГ: всё прошло без ошибок")
