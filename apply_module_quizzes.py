# -*- coding: utf-8 -*-
"""Прикрепляет согласованные тесты (module_quizzes.py) к последним урокам
модулей 1/2/3 — занятия 1.3, 2.6, 3.7."""
import os
import sys

os.environ.setdefault("SECRET_KEY", "x")
os.environ.setdefault("INVITE_CODE", "x")
os.environ.setdefault("ADMIN_INVITE_CODE", "x")

sys.path.insert(0, r"D:\Проекты\sandow-wiki")
from dotenv import load_dotenv
load_dotenv()

from app import parse_quiz
import github_store
from module_quizzes import MODULE_1_QUIZ, MODULE_2_QUIZ, MODULE_3_QUIZ

TARGETS = {
    "Занятие 1.3": MODULE_1_QUIZ,
    "Занятие 2.6": MODULE_2_QUIZ,
    "Занятие 3.7": MODULE_3_QUIZ,
}

pages = github_store.pages_store.load()
applied = []
for slug, meta in pages.items():
    title = meta.get("title", "")
    for prefix, quiz_text in TARGETS.items():
        if title.startswith(prefix):
            quiz = parse_quiz(quiz_text)
            assert quiz is not None and len(quiz) == 15, f"{title}: ожидал 15 вопросов, получил {len(quiz) if quiz else 0}"
            for q in quiz:
                assert len(q["correct"]) >= 1, f"{title}: у вопроса «{q['question'][:40]}» нет правильного ответа"
            pages[slug]["quiz"] = quiz
            applied.append((title, len(quiz)))

for title, n in applied:
    print(f"{title}: прикреплено {n} вопросов")

assert len(applied) == 3, f"ожидал прикрепить к 3 урокам, получилось {len(applied)}"

github_store.pages_store.save(pages, "вики: тесты по модулям 1/2/3 (согласовано с Ольгой 20.08.2026)")
print("\nСохранено.")
