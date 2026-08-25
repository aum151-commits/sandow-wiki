# -*- coding: utf-8 -*-
"""Удаляет пустой дубль-аккаунт Елизаветы liza13 (0 уроков пройдено,
создан 2026-08-25T07:30:05, на 46 секунд раньше рабочего). Настоящий
аккаунт — rilizzyy (16 уроков пройдено, все тесты сданы). Просьба
Ольги 25.08.2026: «удалить задвоенный аккаунт, на котором 0%»."""
import sys
sys.path.insert(0, r'D:\Проекты\sandow-wiki')

from dotenv import load_dotenv
load_dotenv()

import github_store

DUPLICATE = "liza13"

users = github_store.users_store.load()
progress = github_store.progress_store.load()

assert DUPLICATE in users, f"{DUPLICATE} не найден в users"
assert not progress.get(DUPLICATE), f"у {DUPLICATE} есть прогресс, останавливаюсь для безопасности"

del users[DUPLICATE]
github_store.users_store.save(users, f"профиль: удалён пустой дубль-аккаунт {DUPLICATE} (0% прогресса)")
print(f"Удалён: {DUPLICATE}")
