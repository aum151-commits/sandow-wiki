# -*- coding: utf-8 -*-
"""Проверка через реальный браузер (не curl — curl в этом окружении ломает
кириллицу в теле формы). Локальный запуск на 127.0.0.1:5000 с тестовыми
файлами хранилища (test_pages/test_users/test_progress.json).
"""
import sys
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
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


def login(page, username, password):
    page.goto(f"{BASE}/login", wait_until="networkidle")
    page.fill("#username", username)
    page.fill("#password", password)
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")


with sync_playwright() as p:
    browser = p.chromium.launch()

    # --- админ регистрируется, создаёт урок с тестом ---
    admin = browser.new_page(viewport={"width": 1280, "height": 800})
    register(admin, "Ольга Тест", "olga_test", "adminpass123", "test-admin-invite")
    check("админ зарегистрирован и залогинен", admin.url == f"{BASE}/")
    check("видна ссылка «Сотрудники» (только у админа)", admin.locator("text=Сотрудники").count() > 0)

    admin.goto(f"{BASE}/wiki/new", wait_until="networkidle")
    check("поле «номер урока» видно админу", admin.locator("#course_order").count() > 0)
    admin.fill("#title", "Тестовый урок про метраж")
    admin.fill("#course_order", "1")
    admin.click(".ql-editor")
    admin.keyboard.type("Проверочный текст урока: в клубе 2500 м².")
    admin.fill("#quiz_text", "Сколько метров в клубе?\n- 500\n- 2500 *\n- 100")
    admin.click("button[type=submit]")
    admin.wait_for_load_state("networkidle")
    check("урок создан, попали на /course/...", "/course/" in admin.url)
    lesson_url = admin.url
    check("текст урока отображается", admin.locator("text=Проверочный текст урока").count() > 0)
    check("вопрос теста отображается", admin.locator("text=Сколько метров в клубе").count() > 0)

    # неверный ответ
    admin.check("input[name=q0][value='0']")
    admin.click("button[type=submit]")
    admin.wait_for_load_state("networkidle")
    check("неверный ответ — тест не засчитан", admin.locator(".quiz-banner.fail").count() > 0)

    # верный ответ
    admin.uncheck("input[name=q0][value='0']")
    admin.check("input[name=q0][value='1']")
    admin.click("button[type=submit]")
    admin.wait_for_load_state("networkidle")
    check("верный ответ — тест засчитан", admin.locator(".quiz-banner.pass").count() > 0)

    admin.goto(f"{BASE}/course", wait_until="networkidle")
    mark_done = "✅"
    check("урок отмечен пройденным в списке", mark_done in admin.locator(".page-list").inner_text())

    admin.goto(f"{BASE}/course/progress", wait_until="networkidle")
    check("Ольга Тест видна в общем прогрессе", "Ольга Тест" in admin.inner_text("body"))

    # --- обычный сотрудник регистрируется ---
    member = browser.new_page(viewport={"width": 390, "height": 844})
    register(member, "Продажник Тест", "seller_test", "sellerpass123", "test-invite")
    check("сотрудник зарегистрирован", member.url == f"{BASE}/")
    check("у сотрудника НЕТ ссылки «Сотрудники» (не админ)", member.locator("text=Сотрудники").count() == 0)

    member.goto(f"{BASE}/wiki/new", wait_until="networkidle")
    check("у сотрудника НЕТ поля «номер урока» (не админ)", member.locator("#course_order").count() == 0)

    member.goto(lesson_url, wait_until="networkidle")
    check("сотрудник видит урок, созданный админом", member.locator("text=Проверочный текст урока").count() > 0)
    check("у сотрудника нет кнопки «Редактировать» урока", member.locator("text=Редактировать").count() == 0)

    # --- админ отключает доступ сотруднику ---
    admin.goto(f"{BASE}/admin/users", wait_until="networkidle")
    check("сотрудник виден в списке", admin.locator("text=Продажник Тест").count() > 0)
    admin.click("form[action*='seller_test'] button")
    admin.wait_for_load_state("networkidle")
    check("статус сменился на «доступ отключён»", "доступ отключён" in admin.inner_text("body"))

    # сотрудник пробует зайти повторно — должно быть отказано
    member2 = browser.new_page(viewport={"width": 1280, "height": 800})
    login(member2, "seller_test", "sellerpass123")
    check("отключённому сотруднику отказано во входе", "Доступ отключён" in member2.inner_text("body"))

    browser.close()

print()
if errors:
    print(f"ИТОГ: {len(errors)} проблем — {errors}")
    sys.exit(1)
print("ИТОГ: всё прошло без ошибок")
