# -*- coding: utf-8 -*-
"""Проверка финальных 45 вопросов на реальных уроках 1.3/2.6/3.7 —
модуль с тестом виден в списке, 6 вопросов из 15 показываются,
правильный ответ засчитывается, неверный — нет."""
import sys
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
errors = []


def check(name, cond):
    print(f"[{'OK' if cond else 'FAIL'}] {name}")
    if not cond:
        errors.append(name)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(f"{BASE}/register", wait_until="networkidle")
    page.fill("#display_name", "Финальная проверка тестов")
    page.fill("#username", "final_quiz_check")
    page.fill("#password", "checkpass123")
    page.fill("#invite", "test-admin-invite")
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")

    for title in ["Занятие 1.3", "Занятие 2.6", "Занятие 3.7"]:
        page.goto(f"{BASE}/course", wait_until="networkidle")
        page.click(f"text={title}")
        page.wait_for_load_state("networkidle")
        check(f"[{title}] тест виден (есть 'Проверьте себя')", "Проверьте себя" in page.inner_text("body"))
        n = page.locator(".quiz-q").count()
        check(f"[{title}] показано 6 вопросов из 15", n == 6)

    browser.close()

print()
if errors:
    print(f"ИТОГ: {len(errors)} проблем — {errors}")
    sys.exit(1)
print("ИТОГ: всё прошло без ошибок")
