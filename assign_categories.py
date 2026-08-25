# -*- coding: utf-8 -*-
"""Разовая миграция: проставляет поле category всем существующим
страницам базы знаний (не курса) по новой структуре, согласованной с
Ольгой 25.08.2026 (мировые практики Zendesk/Salesforce/Stravito —
категории по роли/задаче менеджера, не по типу контента)."""
import sys
sys.path.insert(0, r'D:\Проекты\sandow-wiki')

from dotenv import load_dotenv
load_dotenv()

import github_store

TITLE_TO_CATEGORY = {
    "Разбор звонка: клиентка с негативным опытом от бывшего тренера": "Разбор звонков",
    "Разбор звонка: бывший клиент «Кенгуру»": "Разбор звонков",
    "Инструкция: гостевой визит и разовое посещение": "Клиент и доступ в клуб",
    "Инструкция: вход в клуб, доступ, парковка": "Клиент и доступ в клуб",
    "Правила и политика клуба: гайд для менеджера": "Клиент и доступ в клуб",
    "Площади, зоны и оборудование клуба": "Продукт и цены",
    "Что входит в абонемент, что оплачивается отдельно": "Продукт и цены",
    "Групповые занятия — что это и входит ли в абонемент": "Продукт и цены",
    "Тарифы, рассрочка и рекурренты — быстрый справочник": "Продукт и цены",
    "Фитнес-эксперты клуба": "Тренеры",
    "Личный кабинет клиента: гайд для менеджера": "Личный кабинет",
}

pages = github_store.pages_store.load()
applied, missing = [], []
for slug, meta in pages.items():
    if meta.get("course_order") is not None:
        continue  # уроки курса категорий не получают
    title = meta.get("title", "")
    category = TITLE_TO_CATEGORY.get(title)
    if category:
        pages[slug]["category"] = category
        applied.append((title, category))
    else:
        missing.append(title)

for title, cat in applied:
    print(f"{title} -> {cat}")
if missing:
    print("\nБЕЗ КАТЕГОРИИ (не нашлось в словаре):")
    for t in missing:
        print(" -", t)

github_store.pages_store.save(pages, "вики: страницы распределены по разделам базы знаний")
print(f"\nПрименено: {len(applied)}, без категории: {len(missing)}")
