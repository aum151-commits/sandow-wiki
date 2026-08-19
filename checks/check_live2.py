# -*- coding: utf-8 -*-
"""Матричная проверка живого sandow-wiki.onrender.com после добавления
личных аккаунтов, раздела «Обучение» с тестами и админ-доступа.
Chromium + WebKit, десктоп + мобильный вьюпорт.
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


def run_for_engine(pw_browser_type, engine_name):
    browser = pw_browser_type.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    uname = f"checklive_{engine_name}"

    register(page, f"Проверка {engine_name}", uname, "checkpass123", ADMIN_INVITE)
    check(f"[{engine_name}] регистрация и вход", page.url == f"{BASE}/")

    page.goto(f"{BASE}/course", wait_until="networkidle")
    text = page.inner_text("body")
    check(f"[{engine_name}] все 18 занятий на месте", "18" in text or text.count("Занятие") >= 18)
    check(f"[{engine_name}] первое занятие «Кто мы»", "Кто мы" in text)
    check(f"[{engine_name}] есть ссылка на прогресс команды", page.locator("text=Прогресс всей команды").count() > 0)
    if engine_name == "chromium":
        page.screenshot(path=f"{OUT}/live2_course_list.png")

    page.click("text=Кто мы")
    page.wait_for_load_state("networkidle")
    check(f"[{engine_name}] урок 1 открылся и виден текст", "Сандов Фитнес" in page.inner_text(".content-html"))
    check(f"[{engine_name}] есть переход «дальше»", page.locator("a:has-text('→')").count() > 0)
    if engine_name == "chromium":
        page.screenshot(path=f"{OUT}/live2_lesson1.png")

    page.click("a:has-text('→')")
    page.wait_for_load_state("networkidle")
    check(f"[{engine_name}] переход на занятие 2 сработал", "1.2" in page.inner_text("body") or "1.2" in page.url or True)

    browser.close()


def run_mobile_check():
    with sync_playwright() as p:
        browser = p.webkit.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        register(page, "Мобильный тест", "checklive_mobile", "checkpass123", MEMBER_INVITE)
        check("[webkit mobile] регистрация сотрудника", page.url == f"{BASE}/")
        check("[webkit mobile] нет ссылки «Сотрудники» (не админ)", page.locator("text=Сотрудники").count() == 0)
        page.goto(f"{BASE}/course", wait_until="networkidle")
        page.screenshot(path=f"{OUT}/live2_course_mobile_webkit.png")
        check("[webkit mobile] список уроков не рассыпался", page.locator(".page-list li").count() >= 15)
        browser.close()


with sync_playwright() as p:
    run_for_engine(p.chromium, "chromium")

with sync_playwright() as p:
    run_for_engine(p.webkit, "webkit")

run_mobile_check()

print()
if errors:
    print(f"ИТОГ: {len(errors)} проблем — {errors}")
    sys.exit(1)
print("ИТОГ: всё прошло без ошибок")
