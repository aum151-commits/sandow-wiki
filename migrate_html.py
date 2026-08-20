# -*- coding: utf-8 -*-
"""Второй перенос курса — из data/course_html (реальный HTML из Skillspace,
таблицы/заголовки сохранены) вместо плоского текста data/course. Также
проставляет module по номеру перед точкой в "Занятие N.M" (1 → «Модуль 1.
Компания, продукты и цены» и т.д., по структуре из памяти проекта).

Запуск (из sandow-wiki, тот же venv, что и app.py — нужен bleach):
    .venv/Scripts/python.exe migrate_html.py
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import bleach
from dotenv import load_dotenv

load_dotenv()

import github_store

SRC_DIR = Path(r"D:\Проекты\call-analysis\voice-trainer\data\course_html")

MODULE_NAMES = {
    1: "Модуль 1. Компания, продукты и цены",
    2: "Модуль 2. Техника продаж",
    3: "Модуль 3. Скрипты звонков",
    4: "Модуль 4. Ролевая игра и тест",
}

ALLOWED_TAGS = [
    "p", "br", "strong", "em", "u", "s", "span",
    "h1", "h2", "h3", "ul", "ol", "li", "a", "img",
    "blockquote", "pre", "code", "iframe", "audio", "source", "hr",
    "table", "thead", "tbody", "tr", "th", "td",
]
ALLOWED_ATTRS = {
    "*": ["class", "style"],
    "a": ["href", "target", "rel"],
    "img": ["src", "alt"],
    "iframe": ["src", "width", "height", "frameborder", "allow", "allowfullscreen"],
    "audio": ["controls", "src"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
    "source": ["src", "type"],
}

EMPTY_LEADING_P = re.compile(
    r'^\s*<p[^>]*class="is-empty"[^>]*>\s*(<br[^>]*>)?\s*</p>\s*', re.IGNORECASE
)


def clean(raw_html: str) -> str:
    html = EMPTY_LEADING_P.sub("", raw_html)
    html = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS,
                         protocols=["http", "https"], strip=True)
    # пустые концевые <p><br></p>
    html = re.sub(r'<p>\s*(<br[^>]*>)?\s*</p>\s*$', "", html.strip())
    return html.strip()


def module_for(title: str):
    m = re.match(r"Занятие\s+(\d+)\.", title)
    if not m:
        return None
    return MODULE_NAMES.get(int(m.group(1)))


def main():
    index = json.loads((SRC_DIR / "index.json").read_text(encoding="utf-8"))
    assert len(index) == 18, f"ожидал 18 занятий, нашёл {len(index)}"

    pages = github_store.pages_store.load()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for item in index:
        title = re.sub(r"^Занятие\s*", "Занятие ", item["title"].strip())
        raw = (SRC_DIR / item["file"]).read_text(encoding="utf-8")
        body_html = clean(raw)

        existing = next((s for s, m in pages.items() if m.get("title") == title), None)
        slug = existing or __import__("uuid").uuid4().hex[:8]

        pages[slug] = {
            "title": title,
            "html": body_html,
            "course_order": item["order"],
            "module": module_for(title),
            "plan_day": pages.get(slug, {}).get("plan_day") if existing else None,
            "quiz": pages.get(slug, {}).get("quiz") if existing else None,
            "tags": pages.get(slug, {}).get("tags", []) if existing else [],
            "updated_at": now,
            "updated_by": "перенос из Skillspace (HTML, с таблицами)",
        }
        print(f"[{item['order']}/18] {title} -> {slug} "
              f"({'обновлено' if existing else 'новое'}, {len(body_html)} байт, "
              f"модуль: {module_for(title)})")

    github_store.pages_store.save(pages, "вики: перенос занятий курса из Skillspace (HTML со структурой)")
    print("\nГотово.")


if __name__ == "__main__":
    main()
