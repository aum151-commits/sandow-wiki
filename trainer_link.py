# -*- coding: utf-8 -*-
"""Запрос лучшего балла сотрудника из голосового ИИ-тренажёра
(отдельный сервис sandow-voice-trainer на Render) — для статуса
«допущен к звонкам». Тренажёр не привязывает сессии к логину, поэтому
сверяем по имени, которое сотрудник сам указывает в профиле вики
(должно совпадать с тем, что он вводит в тренажёре).
"""
import os

import requests

TRAINER_URL = os.environ.get("TRAINER_URL", "https://sandow-voice-trainer.onrender.com")
TRAINER_USER = os.environ.get("TRAINER_USER", "")
TRAINER_PASSWORD = os.environ.get("TRAINER_PASSWORD", "")
TIMEOUT = 45  # бесплатный тариф Render засыпает, первый запрос может будить сервис


def best_score(manager_name: str):
    """Возвращает (score_ratio 0..1, число попыток) или None, если не
    удалось получить данные (тренажёр недоступен, имя не найдено и т.п.)."""
    if not manager_name or not TRAINER_USER:
        return None
    try:
        r = requests.get(
            f"{TRAINER_URL}/api/trainings",
            params={"manager_name": manager_name},
            auth=(TRAINER_USER, TRAINER_PASSWORD),
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        sessions = r.json()
    except (requests.RequestException, ValueError):
        return None
    if not isinstance(sessions, list) or not sessions:
        return None
    ratios = [
        s["score"] / s["max_score"]
        for s in sessions
        if s.get("max_score") and s.get("score") is not None
    ]
    if not ratios:
        return None
    return max(ratios), len(sessions)
