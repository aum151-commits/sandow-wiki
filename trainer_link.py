# -*- coding: utf-8 -*-
"""Запрос лучшего балла сотрудника из голосового ИИ-тренажёра
(отдельный сервис sandow-voice-trainer на Render) — для статуса
«допущен к звонкам». Тренажёр не привязывает сессии к логину, поэтому
сверяем по имени, которое сотрудник сам указывает в профиле вики
(должно совпадать с тем, что он вводит в тренажёре).
"""
import os
from urllib.parse import urlsplit, urlunsplit, quote

import requests

TRAINER_URL = os.environ.get("TRAINER_URL", "https://sandow-voice-trainer.onrender.com")
TRAINER_USER = os.environ.get("TRAINER_USER", "")
TRAINER_PASSWORD = os.environ.get("TRAINER_PASSWORD", "")
TIMEOUT = 45  # бесплатный тариф Render засыпает, первый запрос может будить сервис


def _link_with_credentials(url: str, user: str, password: str) -> str:
    """Ссылка со встроенным логином/паролем (user:pass@host) — переход
    по клику проходит Basic Auth тренажёра сразу, без второго окна входа."""
    if not user:
        return url
    parts = urlsplit(url)
    netloc = f"{quote(user)}:{quote(password)}@{parts.netloc}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


TRAINER_LINK_URL = _link_with_credentials(TRAINER_URL, TRAINER_USER, TRAINER_PASSWORD)


def best_score(manager_name: str):
    """Возвращает (score_ratio 0..1, число попыток) или None, если не
    удалось получить данные (тренажёр недоступен, имя не найдено и т.п.)."""
    if not manager_name or not TRAINER_USER:
        return None
    try:
        r = requests.get(
            f"{TRAINER_URL}/api/trainings",
            params={"manager_name": manager_name, "exact": "1"},
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


def recent_trainings(manager_name: str, limit: int = 5):
    """Последние завершённые попытки с деталями (балл, сильные/слабые
    стороны, рекомендация судьи, следующее упражнение) для страницы
    прогресса. Список идёт одним запросом, детали — по одному запросу на
    попытку (эндпоинт тренажёра не отдаёт их пачкой), поэтому лимит
    небольшой: бесплатный Render может спать, каждый запрос до TIMEOUT сек.
    Возвращает [] если у сотрудника ещё нет завершённых попыток, None —
    если тренажёр недоступен или имя не привязано."""
    if not manager_name or not TRAINER_USER:
        return None
    try:
        r = requests.get(
            f"{TRAINER_URL}/api/trainings",
            params={"manager_name": manager_name, "exact": "1"},
            auth=(TRAINER_USER, TRAINER_PASSWORD),
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        sessions = r.json()
    except (requests.RequestException, ValueError):
        return None
    if not isinstance(sessions, list):
        return None

    finished = [s for s in sessions if s.get("finished_at") and s.get("max_score")]
    finished.sort(key=lambda s: s.get("started_at") or "", reverse=True)
    out = []
    for s in finished[:limit]:
        summary = {}
        try:
            dr = requests.get(
                f"{TRAINER_URL}/api/trainings/{s['id']}",
                auth=(TRAINER_USER, TRAINER_PASSWORD),
                timeout=TIMEOUT,
            )
            if dr.ok:
                summary = (dr.json() or {}).get("summary") or {}
        except requests.RequestException:
            pass  # без деталей — всё равно покажем хотя бы балл
        out.append({
            "started_at": s.get("started_at"),
            "script_type": s.get("script_type"),
            "outcome": s.get("outcome"),
            "score": s.get("score"),
            "max_score": s.get("max_score"),
            "grade": s.get("grade"),
            "strengths": summary.get("strengths") or [],
            "weaknesses": summary.get("weaknesses") or [],
            "recommendation": summary.get("recommendation") or "",
            "next_drill": summary.get("next_drill") or "",
        })
    return out
