# -*- coding: utf-8 -*-
"""Финализирует урок 1.1 (вариант Б истории Сандова, короткий блок
преимуществ без пересечения с 1.3) и добавляет мостик в начало 1.3,
чтобы уроки перетекали друг в друга. Одобрено Ольгой 26.08.2026."""
import sys
sys.path.insert(0, r'D:\Проекты\sandow-wiki')

from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

import github_store

NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")

pages = github_store.pages_store.load()

lesson11 = open(r"D:\Проекты\sandow-wiki\_lesson11_final.html", encoding="utf-8").read().strip()
pages["acdb13a7"]["html"] = lesson11
pages["acdb13a7"]["updated_at"] = NOW
pages["acdb13a7"]["updated_by"] = "усилен: короткая история Сандова + яркие факты, без дублей с 1.3 (одобрено Ольгой 26.08.2026)"

lesson13 = open(r"D:\Проекты\sandow-wiki\_lesson13_bridge.html", encoding="utf-8").read().strip()
pages["d479363f"]["html"] = lesson13
pages["d479363f"]["updated_at"] = NOW
pages["d479363f"]["updated_by"] = "добавлен мостик от 1.1 (одобрено Ольгой 26.08.2026)"

github_store.pages_store.save(pages, "курс: уроки 1.1 и 1.3 согласованы между собой, добавлены переходы")
print("Готово: 1.1 и 1.3 обновлены")
