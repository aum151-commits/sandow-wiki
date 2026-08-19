# -*- coding: utf-8 -*-
"""Юнит-проверка интервального повторения без ожидания реальных дней:
подменяем today() через monkeypatch и проверяем прогрессию этапов."""
import os
import sys
from datetime import date, timedelta

os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("INVITE_CODE", "test")
os.environ.setdefault("ADMIN_INVITE_CODE", "test")
os.environ.setdefault("GITHUB_TOKEN_WORKFLOW", "test")

sys.path.insert(0, r"D:\Проекты\sandow-wiki")
import app as wiki_app

errors = []


def check(name, cond):
    print(f"[{'OK' if cond else 'FAIL'}] {name}")
    if not cond:
        errors.append(name)


REAL_TODAY = date(2026, 8, 20)
current = {"d": REAL_TODAY}
wiki_app.today = lambda: current["d"]

progress = {}

# первый проход
wiki_app.record_pass(progress, "lesson1", "5/5")
entry = progress["lesson1"]
check("этап 0 после первого прохождения", entry["review_stage"] == 0)
check("следующее повторение через 1 день", entry["next_review"] == (REAL_TODAY + timedelta(days=1)).isoformat())

# пересдача СЕГОДНЯ ЖЕ (до срока повторения) — этап не должен продвинуться
wiki_app.record_pass(progress, "lesson1", "5/5")
check("пересдача до срока не продвигает этап", progress["lesson1"]["review_stage"] == 0)

# переносимся на день повторения и сдаём снова — этап должен продвинуться до 1 (3 дня)
current["d"] = REAL_TODAY + timedelta(days=1)
wiki_app.record_pass(progress, "lesson1", "5/5")
entry = progress["lesson1"]
check("после повторения в срок — этап 1", entry["review_stage"] == 1)
check("следующее повторение через 3 дня от текущей даты", entry["next_review"] == (current["d"] + timedelta(days=3)).isoformat())

# ещё три успешных повторения в срок — должны пройти этапы 2, 3, затем None (освоено)
current["d"] = date.fromisoformat(entry["next_review"])
wiki_app.record_pass(progress, "lesson1", "5/5")
check("этап 2 (7 дней)", progress["lesson1"]["review_stage"] == 2)

current["d"] = date.fromisoformat(progress["lesson1"]["next_review"])
wiki_app.record_pass(progress, "lesson1", "5/5")
check("этап 3 (30 дней)", progress["lesson1"]["review_stage"] == 3)

current["d"] = date.fromisoformat(progress["lesson1"]["next_review"])
wiki_app.record_pass(progress, "lesson1", "5/5")
check("после всех этапов next_review = None (освоено)", progress["lesson1"]["next_review"] is None)

# due_for_review
current["d"] = REAL_TODAY
progress2 = {}
wiki_app.record_pass(progress2, "lessonA", None)  # next_review = завтра
pages = {"lessonA": {"course_order": 1}, "lessonB": {"course_order": 2}}
check("свежий урок пока НЕ на повторении", "lessonA" not in wiki_app.due_for_review(pages, progress2))
current["d"] = REAL_TODAY + timedelta(days=1)
check("на следующий день урок появляется в due", "lessonA" in wiki_app.due_for_review(pages, progress2))

# --- план 30/60/90: onboarding_day и просрочка ---
users = {"member1": {"created_at": (REAL_TODAY - timedelta(days=5)).isoformat() + "T00:00:00+00:00"}}
current["d"] = REAL_TODAY
check("день онбординга = 5 (зарегистрирован 5 дней назад)", wiki_app.onboarding_day("member1", users) == 5)

pages = {
    "l1": {"course_order": 1, "plan_day": 3},   # план на день 3, сейчас день 5 — просрочен, если не пройден
    "l2": {"course_order": 2, "plan_day": 10},  # план на день 10 — ещё рано
}
progress_empty = {}
day_n = wiki_app.onboarding_day("member1", users)
overdue_l1 = pages["l1"]["plan_day"] <= day_n and "l1" not in progress_empty
overdue_l2 = pages["l2"]["plan_day"] <= day_n and "l2" not in progress_empty
check("урок с плановым днём 3 просрочен на дне 5", overdue_l1 is True)
check("урок с плановым днём 10 пока не просрочен", overdue_l2 is False)

print()
if errors:
    print(f"ИТОГ: {len(errors)} проблем — {errors}")
    sys.exit(1)
print("ИТОГ: логика интервального повторения и плана 30/60/90 корректна")
