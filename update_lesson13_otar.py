# -*- coding: utf-8 -*-
"""Добавляет в урок 1.3 факт про Отара Кушанашвили (готовился к бою с
Джигурдой в нашем бойцовском клубе, подтверждено видео-досье
Сандов Фитнес/видео/otar-clip-источник.txt) — по просьбе Ольги 25.08.2026."""
import sys
sys.path.insert(0, r'D:\Проекты\sandow-wiki')

from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

import github_store

SLUG = "d479363f"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")

new_html = open(r"D:\Проекты\sandow-wiki\_lesson13_v2.html", encoding="utf-8").read().strip()

pages = github_store.pages_store.load()
pages[SLUG]["html"] = new_html
pages[SLUG]["updated_at"] = NOW
pages[SLUG]["updated_by"] = "добавлен факт про Отара Кушанашвили/Джигурду (одобрено Ольгой 25.08.2026)"
github_store.pages_store.save(pages, "курс: урок 1.3 — добавлен Отар Кушанашвили/Джигурда в раздел медийности")
print("Готово:", pages[SLUG]["title"])
