# -*- coding: utf-8 -*-
"""Хранилище JSON-файлов в приватном GitHub-репозитории через Contents API.

Три независимых файла в одном приватном репозитории (не в этом, публичном,
репозитории с кодом приложения): страницы вики/уроков, аккаунты, прогресс
по урокам. Локального клона нет — читаем/пишем строго через API, как
gh_push_file.py в других автоматизациях проекта.
"""

import base64
import json
import os
import time

import requests

TOKEN = os.environ["GITHUB_TOKEN_WORKFLOW"]
REPO = os.environ.get("WIKI_REPO", "aum151-commits/sandow-automation")
API_BASE = f"https://api.github.com/repos/{REPO}/contents"
HEAD = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github+json"}
CACHE_TTL = 20  # секунд


class JsonFileStore:
    def __init__(self, path: str, default):
        self.path = path
        self.default = default
        self._cache = {"data": None, "sha": None, "ts": 0.0}

    @property
    def _api(self):
        return f"{API_BASE}/{self.path}"

    def _fetch(self):
        r = requests.get(self._api, headers=HEAD, timeout=30)
        if r.status_code == 404:
            return json.loads(json.dumps(self.default)), None
        r.raise_for_status()
        j = r.json()
        content = base64.b64decode(j["content"]).decode("utf-8")
        return json.loads(content), j["sha"]

    def load(self, force=False):
        now = time.time()
        if force or self._cache["data"] is None or now - self._cache["ts"] > CACHE_TTL:
            data, sha = self._fetch()
            self._cache.update(data=data, sha=sha, ts=now)
        return self._cache["data"]

    def save(self, data, message: str):
        body = json.dumps(data, ensure_ascii=False, indent=2)
        payload = {
            "message": message,
            "content": base64.b64encode(body.encode("utf-8")).decode(),
            "committer": {"name": "Sandow Wiki", "email": "bot@sandowfitness.ru"},
        }
        if self._cache["sha"]:
            payload["sha"] = self._cache["sha"]

        r = requests.put(self._api, headers=HEAD, json=payload, timeout=60)
        if r.status_code == 409:
            # кто-то успел сохранить параллельно — перечитать и повторить один раз
            self.load(force=True)
            payload["sha"] = self._cache["sha"]
            r = requests.put(self._api, headers=HEAD, json=payload, timeout=60)
        r.raise_for_status()
        j = r.json()
        self._cache.update(data=data, sha=j["content"]["sha"], ts=time.time())
        return data


def history(path: str, contains: str = None, limit: int = 15):
    """Список последних коммитов, затронувших файл — грубая, но бесплатная
    история правок: своей версии diff/rollback не пишем, git уже это умеет.
    contains — фильтр по подстроке в сообщении коммита (например, названию
    страницы), т.к. все страницы живут в одном общем JSON-файле."""
    r = requests.get(
        f"https://api.github.com/repos/{REPO}/commits",
        headers=HEAD, params={"path": path, "per_page": 100}, timeout=30,
    )
    r.raise_for_status()
    commits = r.json()
    out = []
    for c in commits:
        msg = c["commit"]["message"]
        if contains and contains not in msg:
            continue
        out.append({
            "message": msg,
            "date": c["commit"]["author"]["date"],
            "author": c["commit"]["author"]["name"],
        })
        if len(out) >= limit:
            break
    return out


WIKI_PATH = os.environ.get("WIKI_PATH", "wiki-content/pages.json")
USERS_PATH = os.environ.get("WIKI_USERS_PATH", "wiki-content/users.json")
PROGRESS_PATH = os.environ.get("WIKI_PROGRESS_PATH", "wiki-content/progress.json")
# Отдельно от progress.json: там прогресс хранится {slug: entry} и на нём
# завязана due_for_review() — примешивать туда что-то не по схеме лесона
# (например список попыток) её ломает. Попытки тестов — свой файл.
ATTEMPTS_PATH = os.environ.get("WIKI_ATTEMPTS_PATH", "wiki-content/attempts.json")
# Глобальные настройки платформы (не привязаны к конкретному пользователю
# или странице) — например видимость целых разделов для сотрудников,
# пока раздел не готов к запуску.
SETTINGS_PATH = os.environ.get("WIKI_SETTINGS_PATH", "wiki-content/settings.json")
pages_store = JsonFileStore(WIKI_PATH, default={})
users_store = JsonFileStore(USERS_PATH, default={})
progress_store = JsonFileStore(PROGRESS_PATH, default={})
attempts_store = JsonFileStore(ATTEMPTS_PATH, default={})
settings_store = JsonFileStore(SETTINGS_PATH, default={})
