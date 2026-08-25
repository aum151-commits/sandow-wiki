# -*- coding: utf-8 -*-
"""Убирает Олега (управляющего, зарегистрирован дважды — oleg95 и oleg95!)
из таблицы «Прогресс команды»: он руководитель, не сотрудник ОП на
обучении, попадать в отчёт не должен — та же логика, что и для
Ольги (роль admin исключена в самом коде app.py). Просьба Ольги
25.08.2026."""
import sys
sys.path.insert(0, r'D:\Проекты\sandow-wiki')

from dotenv import load_dotenv
load_dotenv()

import github_store

TARGETS = ["oleg95", "oleg95!"]

users = github_store.users_store.load()
changed = []
for u in TARGETS:
    if u in users:
        users[u]["exclude_from_progress"] = True
        changed.append(u)

github_store.users_store.save(users, "профиль: Олег (управляющий) исключён из «Прогресс команды»")
print("Исключены:", changed)
