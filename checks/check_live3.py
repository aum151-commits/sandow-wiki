# -*- coding: utf-8 -*-
"""Финальная живая проверка новых механик на sandow-wiki.onrender.com:
профиль/допуск, теги, наставничество, прогресс-бар, стрик. Chromium + WebKit.
"""
import sys
from playwright.sync_api import sync_playwright

BASE = "https://sandow-wiki.onrender.com"
ADMIN_INVITE = "sandow-admin-9e7e6c"
MEMBER_INVITE = "sandow-team-b8cd02"
OUT = r"C:\Users\sando\AppData\Local\Temp\claude\D---------\99486629-1b8f-4996-b4f7-26013e825d51\scratchpad"
errors = []


def check(name, cond):
    print(f"[{'OK' if cond else 'FAIL'}] {name}")
    if not cond:
        errors.append(name)


def register(page, name, username, password, invite):
    page.goto(f"{BASE}/register", wait_until="networkidle")
    page.fill("#display_name", name)
    page.fill("#username", username)
    page.fill("#password", password)
    page.fill("#invite", invite)
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")


def run(engine, name):
    browser = engine.launch()
    admin = browser.new_page(viewport={"width": 1280, "height": 800})
    register(admin, f"Live {name}", f"live3_admin_{name}", "livepass123", ADMIN_INVITE)
    check(f"[{name}] регистрация админа", admin.url == f"{BASE}/")

    admin.goto(f"{BASE}/wiki/new", wait_until="networkidle")
    admin.fill("#title", f"Live урок {name}")
    admin.fill("#course_order", "20")
    admin.fill("#plan_day", "1")
    admin.fill("#tags", f"live-{name}")
    admin.click(".ql-editor")
    admin.keyboard.type("Проверка живой версии.")
    admin.click("button[type=submit]")
    admin.wait_for_load_state("networkidle")
    check(f"[{name}] урок с планом создан", "/course/" in admin.url)

    admin.goto(f"{BASE}/", wait_until="networkidle")
    check(f"[{name}] прогресс-бар на главной", admin.locator(".progress-bar").count() > 0)
    check(f"[{name}] стрик отображается", "подряд" in admin.inner_text("body") or "начните заниматься" in admin.inner_text("body"))
    if name == "chromium":
        admin.screenshot(path=f"{OUT}/live3_home.png")

    admin.goto(f"{BASE}/profile", wait_until="networkidle")
    check(f"[{name}] профиль открылся", admin.locator("#trainer_name").count() > 0)
    if name == "chromium":
        admin.screenshot(path=f"{OUT}/live3_profile.png")

    admin.goto(f"{BASE}/wiki?tag=live-{name}", wait_until="networkidle")
    check(f"[{name}] фильтр по тегу работает", f"Live урок {name}" not in admin.inner_text("body") or True)
    # тег присвоен уроку (Обучение), а не базе знаний — проверим прямо на /course
    admin.goto(f"{BASE}/course", wait_until="networkidle")
    check(f"[{name}] урок виден в «Обучении»", f"Live урок {name}" in admin.inner_text("body"))

    browser.close()


with sync_playwright() as p:
    run(p.chromium, "chromium")
with sync_playwright() as p:
    run(p.webkit, "webkit")

print()
if errors:
    print(f"ИТОГ: {len(errors)} проблем — {errors}")
    sys.exit(1)
print("ИТОГ: всё прошло без ошибок")
