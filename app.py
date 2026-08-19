# -*- coding: utf-8 -*-
"""База знаний «Сандов Фитнес» — простая вики с общей стартовой страницей,
которая ведёт также на курсы Stepik. Контент хранится в приватном
GitHub-репозитории (github_store.py), сама программа данных не хранит —
можно спокойно пересоздавать сервис.
"""

import os
import re
import uuid
from datetime import datetime, timezone

import bleach
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, abort, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

import github_store

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]

STEPIK_URL = os.environ.get("STEPIK_URL", "")
WIKI_PASSWORD_HASH = os.environ["WIKI_PASSWORD_HASH"]

ALLOWED_TAGS = [
    "p", "br", "strong", "em", "u", "s", "span", "div",
    "h1", "h2", "h3", "ul", "ol", "li", "a", "img",
    "blockquote", "pre", "code", "iframe", "audio", "source", "hr",
]
ALLOWED_ATTRS = {
    "*": ["class", "style"],
    "a": ["href", "target", "rel"],
    "img": ["src", "alt"],
    "iframe": ["src", "width", "height", "frameborder", "allow", "allowfullscreen"],
    "audio": ["controls", "src"],
    "source": ["src", "type"],
}
ALLOWED_PROTOCOLS = ["http", "https"]


def sanitize(html: str) -> str:
    return bleach.clean(
        html or "",
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )


def plain_text(html: str) -> str:
    return bleach.clean(html or "", tags=[], strip=True)


def slugify() -> str:
    return uuid.uuid4().hex[:8]


def require_login():
    if not session.get("ok"):
        return redirect(url_for("login", next=request.path))
    return None


@app.get("/health")
def health():
    return "ok"


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        pwd = request.form.get("password", "")
        if check_password_hash(WIKI_PASSWORD_HASH, pwd):
            session["ok"] = True
            session["user"] = request.form.get("name", "").strip() or "коллега"
            return redirect(request.args.get("next") or url_for("home"))
        error = "Неверный пароль"
    return render_template("login.html", error=error)


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/")
def home():
    guard = require_login()
    if guard:
        return guard
    return render_template("home.html", stepik_url=STEPIK_URL)


@app.get("/wiki")
def wiki_list():
    guard = require_login()
    if guard:
        return guard
    pages = github_store.load()
    q = request.args.get("q", "").strip().lower()
    items = [
        {"slug": slug, **meta}
        for slug, meta in pages.items()
    ]
    if q:
        items = [
            it for it in items
            if q in it["title"].lower() or q in plain_text(it["html"]).lower()
        ]
    items.sort(key=lambda it: it["title"].lower())
    return render_template("wiki_list.html", items=items, q=request.args.get("q", ""))


@app.get("/wiki/new")
def wiki_new_form():
    guard = require_login()
    if guard:
        return guard
    return render_template("wiki_edit.html", page=None, slug=None)


@app.post("/wiki/new")
def wiki_new():
    guard = require_login()
    if guard:
        return guard
    title = request.form.get("title", "").strip() or "Без названия"
    html = sanitize(request.form.get("html", ""))
    pages = github_store.load()
    slug = slugify()
    while slug in pages:
        slug = slugify()
    pages[slug] = {
        "title": title,
        "html": html,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "updated_by": session.get("user", "коллега"),
    }
    github_store.save(pages, f"вики: новая страница «{title}»")
    return redirect(url_for("wiki_view", slug=slug))


@app.get("/wiki/<slug>")
def wiki_view(slug):
    guard = require_login()
    if guard:
        return guard
    pages = github_store.load()
    page = pages.get(slug)
    if not page:
        abort(404)
    return render_template("wiki_view.html", page=page, slug=slug)


@app.get("/wiki/<slug>/edit")
def wiki_edit_form(slug):
    guard = require_login()
    if guard:
        return guard
    pages = github_store.load()
    page = pages.get(slug)
    if not page:
        abort(404)
    return render_template("wiki_edit.html", page=page, slug=slug)


@app.post("/wiki/<slug>/edit")
def wiki_edit(slug):
    guard = require_login()
    if guard:
        return guard
    pages = github_store.load()
    if slug not in pages:
        abort(404)
    title = request.form.get("title", "").strip() or "Без названия"
    html = sanitize(request.form.get("html", ""))
    pages[slug] = {
        "title": title,
        "html": html,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "updated_by": session.get("user", "коллега"),
    }
    github_store.save(pages, f"вики: правка «{title}»")
    return redirect(url_for("wiki_view", slug=slug))


@app.post("/wiki/<slug>/delete")
def wiki_delete(slug):
    guard = require_login()
    if guard:
        return guard
    pages = github_store.load()
    if slug in pages:
        title = pages[slug]["title"]
        del pages[slug]
        github_store.save(pages, f"вики: удалена страница «{title}»")
    return redirect(url_for("wiki_list"))


@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True, port=5000)
