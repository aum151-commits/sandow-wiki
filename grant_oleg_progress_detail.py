# -*- coding: utf-8 -*-
"""Даёт Олегу (управляющему) право видеть детали прогресса команды
(просрочки), не давая доступа к админке сайта (/admin/users) — это
разные права. Ольга (role=admin) уже видит всё по своей роли. Просьба
Ольги 25.08.2026: рядовые сотрудники не должны видеть чужие просрочки
(публичный флаг «отстаёт» демотивирует), а руководителям это нужно."""
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
        users[u]["see_progress_detail"] = True
        changed.append(u)

github_store.users_store.save(users, "профиль: Олег получил право видеть детали прогресса (просрочки)")
print("Обновлены:", changed)
