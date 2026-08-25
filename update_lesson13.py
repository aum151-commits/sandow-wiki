# -*- coding: utf-8 -*-
"""Обновляет Занятие 1.3 «Наши ценности и преимущества» — усиленная
версия, одобрена Ольгой 25.08.2026 (черновик на согласование +
поправка про BODY MANIA: «не один бой, а много»)."""
import sys
sys.path.insert(0, r'D:\Проекты\sandow-wiki')

from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

import github_store

SLUG = "d479363f"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")

new_html = open(r"D:\Проекты\sandow-wiki\_lesson13_new.html", encoding="utf-8").read().strip()

pages = github_store.pages_store.load()
assert SLUG in pages, "урок 1.3 не найден"
pages[SLUG]["html"] = new_html
pages[SLUG]["updated_at"] = NOW
pages[SLUG]["updated_by"] = "усилен УТП: оборудование, бойцовский клуб, медийность (одобрено Ольгой 25.08.2026)"
github_store.pages_store.save(pages, "курс: усилен урок 1.3 — конкретные бренды, бойцовский клуб, медийность")
print("Готово:", pages[SLUG]["title"])
