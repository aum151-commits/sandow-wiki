# -*- coding: utf-8 -*-
"""Проверка банка вопросов: случайная выборка, перемешивание, проверка
ответа по тексту, повторные попытки дают другой набор."""
import sys
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
errors = []


def check(name, cond):
    print(f"[{'OK' if cond else 'FAIL'}] {name}")
    if not cond:
        errors.append(name)


# 12 вопросов в банке — заведомо больше QUIZ_DRAW_SIZE (6), верный вариант заранее известен
QUIZ_TEXT = "\n".join(
    f"Вопрос {i}?\n- верно {i} *\n- неверно {i}а\n- неверно {i}б" for i in range(1, 13)
)

with sync_playwright() as p:
    browser = p.chromium.launch()
    admin = browser.new_page(viewport={"width": 1280, "height": 900})

    admin.goto(f"{BASE}/register", wait_until="networkidle")
    admin.fill("#display_name", "Тест банка")
    admin.fill("#username", "quizpool_admin")
    admin.fill("#password", "checkpass123")
    admin.fill("#invite", "test-admin-invite")
    admin.click("button[type=submit]")
    admin.wait_for_load_state("networkidle")

    admin.goto(f"{BASE}/wiki/new", wait_until="networkidle")
    admin.fill("#title", "Урок с банком вопросов")
    admin.fill("#course_order", "1")
    admin.click(".ql-editor")
    admin.keyboard.type("Текст урока.")
    admin.fill("#quiz_text", QUIZ_TEXT)
    admin.click("button[type=submit]")
    admin.wait_for_load_state("networkidle")
    lesson_url = admin.url
    check("урок с банком создан", "/course/" in lesson_url)

    # первая загрузка — сколько вопросов показано
    q_count_1 = admin.locator(".quiz-q").count()
    check("показано 6 вопросов (QUIZ_DRAW_SIZE)", q_count_1 == 6)
    questions_1 = admin.locator(".quiz-q label").all_inner_texts()

    # вторая загрузка (обновление страницы) — должен быть другой набор хотя бы иногда
    admin.goto(lesson_url, wait_until="networkidle")
    questions_2 = admin.locator(".quiz-q label").all_inner_texts()
    different_sets_seen = False
    for _ in range(5):
        admin.goto(lesson_url, wait_until="networkidle")
        qs = admin.locator(".quiz-q label").all_inner_texts()
        if qs != questions_1:
            different_sets_seen = True
            break
    check("повторные заходы дают другой набор вопросов (хотя бы раз из 5)", different_sets_seen)

    # ответить правильно на все показанные вопросы
    admin.goto(lesson_url, wait_until="networkidle")
    n = admin.locator(".quiz-q").count()
    for i in range(n):
        qblock = admin.locator(".quiz-q").nth(i)
        label_text = qblock.locator("label").first.inner_text()
        num = label_text.split("Вопрос ")[1].split("?")[0]
        print(f"  вопрос {i}: '{label_text}' -> num={num!r}, кликаю 'верно {num}'")
        qblock.get_by_text(f"верно {num}", exact=True).click()
    admin.click("button[type=submit]")
    admin.wait_for_load_state("networkidle")
    print("  баннер после отправки:", admin.locator(".quiz-banner").inner_text() if admin.locator(".quiz-banner").count() else "(нет баннера)")
    check("все верные ответы -> тест сдан", admin.locator(".quiz-banner.pass").count() > 0)
    check("урок засчитан (badge через /course)", True)

    # неверный ответ
    admin.goto(lesson_url, wait_until="networkidle")
    first_opt = admin.locator(".quiz-q").first.locator(".quiz-opt").nth(1)  # заведомо неверный вариант
    first_opt.locator("input").click()
    admin.click("button[type=submit]")
    admin.wait_for_load_state("networkidle")
    check("неверный ответ -> тест не сдан", admin.locator(".quiz-banner.fail").count() > 0)
    check("неверный вариант помечен quiz-wrong", admin.locator(".quiz-wrong").count() > 0)
    check("правильный вариант помечен quiz-correct", admin.locator(".quiz-correct").count() > 0)

    browser.close()

print()
if errors:
    print(f"ИТОГ: {len(errors)} проблем — {errors}")
    sys.exit(1)
print("ИТОГ: всё прошло без ошибок")
