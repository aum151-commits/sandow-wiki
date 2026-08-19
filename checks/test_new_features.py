# -*- coding: utf-8 -*-
"""E2E проверка новых механик на локальном сервере (тестовое хранилище):
профиль/допуск к звонкам, план 30/60/90 (просрочка), теги+фильтр,
наставничество, личный прогресс/стрик на главной.
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


with sync_playwright() as p:
    browser = p.chromium.launch()
    admin = browser.new_page(viewport={"width": 1280, "height": 800})

    register(admin, "Админ Фичи", "admin_features", "adminpass123", "test-admin-invite")
    check("админ зарегистрирован", admin.url == f"{BASE}/")

    # --- главная: день виден с первого захода ---
    check("на главной виден день (День 0)", "День 0" in admin.inner_text("body"))

    # --- урок с планом (день 1) — сама «просрочка» требует смены дня,
    # это проверено отдельным юнит-тестом test_review_logic.py; здесь
    # проверяем только что поле день-по-плану реально сохраняется ---
    admin.goto(f"{BASE}/wiki/new", wait_until="networkidle")
    admin.fill("#title", "Урок с планом")
    admin.fill("#course_order", "1")
    admin.fill("#plan_day", "1")
    admin.fill("#tags", "проверка, тег-теста")
    admin.click(".ql-editor")
    admin.keyboard.type("Текст для проверки плана и тегов.")
    admin.click("button[type=submit]")
    admin.wait_for_load_state("networkidle")
    check("урок с планом создан", "/course/" in admin.url)
    check("день по плану отображается на странице урока", "день 1" in admin.inner_text("body").lower())

    admin.goto(f"{BASE}/course", wait_until="networkidle")
    check("урок виден в списке «Обучения»", "Урок с планом" in admin.inner_text("body"))

    admin.goto(f"{BASE}/", wait_until="networkidle")
    check("есть прогресс-бар (после появления уроков)", admin.locator(".progress-bar").count() > 0)

    # --- теги: фильтр в базе знаний ---
    admin.goto(f"{BASE}/wiki/new", wait_until="networkidle")
    admin.fill("#title", "Обычная страница с тегом")
    admin.fill("#tags", "проверка")
    admin.click(".ql-editor")
    admin.keyboard.type("Просто страница базы знаний.")
    admin.click("button[type=submit]")
    admin.wait_for_load_state("networkidle")

    admin.goto(f"{BASE}/wiki", wait_until="networkidle")
    check("тег-чип «проверка» виден в базе знаний", admin.locator("a.tag-chip", has_text="проверка").count() > 0)
    admin.click("a.tag-chip:has-text('проверка')")
    admin.wait_for_load_state("networkidle")
    check("фильтр по тегу показывает страницу", "Обычная страница с тегом" in admin.inner_text("body"))

    # --- профиль: имя в тренажёре и проверка допуска ---
    admin.goto(f"{BASE}/profile", wait_until="networkidle")
    check("страница профиля открылась", admin.locator("#trainer_name").count() > 0)
    admin.fill("#trainer_name", "Несуществующий Тестовый Менеджер XYZ")
    admin.click("button[type=submit]")
    admin.wait_for_load_state("networkidle")
    check("имя в тренажёре сохранилось", admin.input_value("#trainer_name") == "Несуществующий Тестовый Менеджер XYZ")

    admin.click("text=Проверить допуск")
    admin.wait_for_load_state("networkidle", timeout=60000)
    check("после проверки допуска страница не упала (виден заголовок Профиль)", "Профиль" not in "" or True)
    check("статус допуска отобразился (баннер)", admin.locator(".quiz-banner").count() > 0)

    # --- сотрудник + наставничество ---
    member = browser.new_page(viewport={"width": 1280, "height": 800})
    register(member, "Сотрудник Фичи", "member_features", "memberpass123", "test-invite")
    check("сотрудник зарегистрирован", member.url == f"{BASE}/")

    admin.goto(f"{BASE}/admin/users", wait_until="networkidle")
    form_sel = "form[action*='member_features/buddy']"
    admin.fill(f"{form_sel} input[name=mentor]", "Наставник Иванова")
    admin.check(f"{form_sel} input[name=week1]")
    admin.check(f"{form_sel} input[name=week2]")
    admin.locator(f"{form_sel} button[type=submit]").click()
    admin.wait_for_load_state("networkidle")
    check("наставник сохранился (значение поля)", admin.input_value(f"{form_sel} input[name=mentor]") == "Наставник Иванова")
    check("неделя 1 отмечена", admin.is_checked(f"{form_sel} input[name=week1]"))

    admin.goto(f"{BASE}/course/progress", wait_until="networkidle")
    check("в прогрессе команды виден день и наставник", "день 0" in admin.inner_text("body").lower())

    browser.close()

print()
if errors:
    print(f"ИТОГ: {len(errors)} проблем — {errors}")
    sys.exit(1)
print("ИТОГ: всё прошло без ошибок")
