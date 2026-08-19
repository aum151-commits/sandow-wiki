# -*- coding: utf-8 -*-
"""Реальная проверка живого sandow-wiki.onrender.com в браузере (Playwright).
Логин, стартовая страница, создание вики-страницы с видео/аудио-вставкой,
просмотр, поиск, мобильный вьюпорт. Скриншоты в scratch/.
"""
import sys
from playwright.sync_api import sync_playwright

BASE = "https://sandow-wiki.onrender.com"
PASSWORD = "Sandow2026wiki"
OUT = r"C:\Users\sando\AppData\Local\Temp\claude\D---------\99486629-1b8f-4996-b4f7-26013e825d51\scratchpad"

errors = []


def check(name, cond):
    status = "OK" if cond else "FAIL"
    print(f"[{status}] {name}")
    if not cond:
        errors.append(name)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # --- десктоп ---
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"{BASE}/login", wait_until="networkidle")
        page.fill("#name", "Проверка")
        page.fill("#password", PASSWORD)
        page.click("button[type=submit]")
        page.wait_for_load_state("networkidle")
        check("после логина попали на главную", page.url == f"{BASE}/")
        check("плитка «Обучение» видна", page.locator("text=Обучение").count() > 0)
        check("плитка «База знаний» видна", page.locator("text=База знаний").count() > 0)
        page.screenshot(path=f"{OUT}/wiki_home_desktop.png")

        page.click("text=База знаний")
        page.wait_for_load_state("networkidle")
        check("открылся список вики", "/wiki" in page.url)
        page.screenshot(path=f"{OUT}/wiki_list_desktop.png")

        page.click("text=+ Новая страница")
        page.wait_for_load_state("networkidle")
        page.fill("#title", "Проверка публикации")
        page.wait_for_selector(".ql-editor")
        page.click(".ql-editor")
        page.keyboard.type("Это тестовая страница со ссылкой на видео.")
        # кнопка видео открывает собственную панель Quill (не системный prompt)
        page.click("button.ql-video")
        page.wait_for_selector(".ql-tooltip input[type=text]")
        check("подсказка вставки видео на русском",
              "видео" in (page.locator(".ql-tooltip").first.inner_text() or "").lower())
        page.fill(".ql-tooltip input[type=text]", "https://www.youtube.com/embed/dQw4w9WgXcQ")
        page.click(".ql-tooltip a.ql-action")
        page.wait_for_timeout(300)
        check("видео вставилось (iframe в редакторе)", page.locator("#editor iframe").count() > 0)

        # аудио — своя кнопка, использует настоящий window.prompt()
        page.once("dialog", lambda d: d.accept("https://example.com/test.mp3"))
        page.click("#audioBtn")
        page.wait_for_timeout(300)
        check("аудио вставилось (audio в редакторе)", page.locator("#editor audio").count() > 0)

        page.click("button[type=submit]")
        page.wait_for_load_state("networkidle")
        check("страница сохранилась и открылась просмотр", "/wiki/" in page.url and "/edit" not in page.url)
        check("видео отображается на странице просмотра", page.locator(".content-html iframe").count() > 0)
        check("аудио отображается на странице просмотра", page.locator(".content-html audio").count() > 0)
        check("текст страницы виден", page.locator("text=Это тестовая страница").count() > 0)
        page.screenshot(path=f"{OUT}/wiki_view_desktop.png")
        view_url = page.url

        # поиск
        page.goto(f"{BASE}/wiki?q=Проверка", wait_until="networkidle")
        check("поиск находит созданную страницу", page.locator("text=Проверка публикации").count() > 0)

        # удаляем тестовую страницу
        page.goto(view_url, wait_until="networkidle")
        page.once("dialog", lambda d: d.accept())
        page.click("text=Удалить")
        page.wait_for_load_state("networkidle")
        check("после удаления вернулись в список", "/wiki" in page.url and page.url.count("/wiki/") == 0)

        page.close()

        # --- мобильный вьюпорт (iPhone-размер) ---
        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(f"{BASE}/login", wait_until="networkidle")
        mobile.fill("#name", "Проверка")
        mobile.fill("#password", PASSWORD)
        mobile.click("button[type=submit]")
        mobile.wait_for_load_state("networkidle")
        mobile.screenshot(path=f"{OUT}/wiki_home_mobile.png")
        check("на мобильном плитки не съехали (обе видны)",
              mobile.locator("text=Обучение").count() > 0 and mobile.locator("text=База знаний").count() > 0)
        mobile.click("text=База знаний")
        mobile.wait_for_load_state("networkidle")
        mobile.screenshot(path=f"{OUT}/wiki_list_mobile.png")
        mobile.close()

        browser.close()

    print()
    if errors:
        print(f"ИТОГ: {len(errors)} проблем — {errors}")
        sys.exit(1)
    print("ИТОГ: всё прошло без ошибок")


if __name__ == "__main__":
    run()
