# -*- coding: utf-8 -*-
"""Хранилище страниц вики в приватном GitHub-репозитории через Contents API.

Все страницы лежат одним JSON-файлом в отдельном приватном репозитории
(не в этом, публичном, репозитории с кодом приложения). Локального клона
нет — читаем/пишем строго через API, как gh_push_file.py в других
автоматизациях проекта.
"""

import base64
import json
import os
import time

import requests

TOKEN = os.environ["GITHUB_TOKEN_WORKFLOW"]
REPO = os.environ.get("WIKI_REPO", "aum151-commits/sandow-automation")
PATH = os.environ.get("WIKI_PATH", "wiki-content/pages.json")
API = f"https://api.github.com/repos/{REPO}/contents/{PATH}"
HEAD = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github+json"}

CACHE_TTL = 20  # секунд
_cache = {"data": None, "sha": None, "ts": 0.0}


def _fetch():
    r = requests.get(API, headers=HEAD, timeout=30)
    if r.status_code == 404:
        return {}, None
    r.raise_for_status()
    j = r.json()
    content = base64.b64decode(j["content"]).decode("utf-8")
    return json.loads(content), j["sha"]


def load(force=False):
    now = time.time()
    if force or _cache["data"] is None or now - _cache["ts"] > CACHE_TTL:
        data, sha = _fetch()
        _cache.update(data=data, sha=sha, ts=now)
    return _cache["data"]


def save(pages: dict, message: str):
    body = json.dumps(pages, ensure_ascii=False, indent=2)
    payload = {
        "message": message,
        "content": base64.b64encode(body.encode("utf-8")).decode(),
        "committer": {"name": "Sandow Wiki", "email": "bot@sandowfitness.ru"},
    }
    if _cache["sha"]:
        payload["sha"] = _cache["sha"]

    r = requests.put(API, headers=HEAD, json=payload, timeout=60)
    if r.status_code == 409:
        # кто-то успел сохранить страницу параллельно — перечитать и повторить один раз
        load(force=True)
        payload["sha"] = _cache["sha"]
        r = requests.put(API, headers=HEAD, json=payload, timeout=60)
    r.raise_for_status()
    j = r.json()
    _cache.update(data=pages, sha=j["content"]["sha"], ts=time.time())
    return pages
