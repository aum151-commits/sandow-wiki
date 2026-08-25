# -*- coding: utf-8 -*-
"""Загружает извлечённые скриншоты ЛК (lk_screenshots/) в публичный
репозиторий aum151-commits/sandow-assets (тот же CDN, что уже используется
для фото тренеров — github.io/sandow-assets), путь lk-guide/<file>.
Печатает готовые https-ссылки для вставки в HTML гайда."""
import base64
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ["GITHUB_TOKEN_WORKFLOW"]
REPO = "aum151-commits/sandow-assets"
API = f"https://api.github.com/repos/{REPO}/contents"
HEAD = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github+json"}

SRC_DIR = r"D:\Проекты\sandow-wiki\lk_screenshots"

urls = {}
for fname in sorted(os.listdir(SRC_DIR)):
    local_path = os.path.join(SRC_DIR, fname)
    remote_path = f"lk-guide/{fname}"
    body = open(local_path, "rb").read()

    r = requests.get(f"{API}/{remote_path}", headers=HEAD, timeout=30)
    sha = r.json().get("sha") if r.status_code == 200 else None
    if sha and base64.b64decode(r.json()["content"]) == body:
        print(f"{fname}: уже актуален")
    else:
        payload = {
            "message": f"lk-guide: {fname}",
            "content": base64.b64encode(body).decode(),
            "committer": {"name": "Sandow Wiki", "email": "bot@sandowfitness.ru"},
        }
        if sha:
            payload["sha"] = sha
        r = requests.put(f"{API}/{remote_path}", headers=HEAD, json=payload, timeout=60)
        if r.status_code not in (200, 201):
            print(f"{fname}: ОШИБКА {r.status_code} {r.text[:200]}")
            sys.exit(1)
        print(f"{fname}: загружен")

    urls[fname] = f"https://aum151-commits.github.io/sandow-assets/{remote_path}"

print("\n--- ссылки ---")
for fname, url in urls.items():
    print(f"{fname} -> {url}")
