# -*- coding: utf-8 -*-
"""Проставляет «перепроверить факты до» на страницы, которые меняются
чаще остальных (тарифы, состав тренеров, расписание, оборудование) —
без этого поля они рисковали висеть годами без переверки, как и
случилось с ценами на сайте vs курсе."""
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
load_dotenv()

import github_store

REVIEW_BY = (datetime.now(timezone.utc).date() + timedelta(days=30)).isoformat()

SLUGS = ["3f753b60", "a072be91", "6cdc54f9", "eb2fdcc4"]

pages = github_store.pages_store.load()
for slug in SLUGS:
    if slug in pages:
        pages[slug]["review_by"] = REVIEW_BY
        print(f"{slug}: {pages[slug]['title']} -> перепроверить до {REVIEW_BY}")
    else:
        print(f"ВНИМАНИЕ: {slug} не найден")

github_store.pages_store.save(pages, "вики: проставлены даты перепроверки для изменчивых страниц")
print("Сохранено.")
