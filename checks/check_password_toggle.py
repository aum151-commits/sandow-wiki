# -*- coding: utf-8 -*-
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
    page = browser.new_page(viewport={"width": 390, "height": 844})

    page.goto(f"{BASE}/register", wait_until="networkidle")
    check("autocapitalize=off на пароле (регистрация)",
          page.get_attribute("#password", "autocapitalize") == "off")
    page.fill("#display_name", "Тест пароля")
    page.fill("#username", "pw_toggle_test")
    page.fill("#password", "SecretPass1")
    check("тип поля password до нажатия", page.get_attribute("#password", "type") == "password")
    page.click("#togglePassword")
    check("тип поля text после нажатия «Показать»", page.get_attribute("#password", "type") == "text")
    check("значение видно и совпадает", page.input_value("#password") == "SecretPass1")
    page.click("#togglePassword")
    check("снова password после «Скрыть»", page.get_attribute("#password", "type") == "password")
    page.fill("#invite", "test-invite")
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")
    check("регистрация прошла", page.url == f"{BASE}/")

    page.goto(f"{BASE}/logout", wait_until="networkidle")
    page.goto(f"{BASE}/login", wait_until="networkidle")
    check("autocapitalize=off на пароле (логин)",
          page.get_attribute("#password", "autocapitalize") == "off")
    page.fill("#username", "pw_toggle_test")
    page.fill("#password", "SecretPass1")
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")
    check("логин с тем же паролем сработал", page.url == f"{BASE}/")

    browser.close()

print()
if errors:
    print(f"ИТОГ: {len(errors)} проблем — {errors}")
    sys.exit(1)
print("ИТОГ: всё прошло без ошибок")
