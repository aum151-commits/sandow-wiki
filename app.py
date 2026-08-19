# -*- coding: utf-8 -*-
"""«Сандов Фитнес» — один сайт, один логин: обучение (уроки по порядку
с личным прогрессом) и база знаний (свободная вики). Контент хранится
в приватном GitHub-репозитории (github_store.py), сама программа данных
не хранит — можно спокойно пересоздавать сервис.
"""

import os
import uuid
from datetime import datetime, timezone

import bleach
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, abort, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import github_store

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]

INVITE_CODE = os.environ["INVITE_CODE"]
ADMIN_INVITE_CODE = os.environ["ADMIN_INVITE_CODE"]

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


def new_slug() -> str:
    return uuid.uuid4().hex[:8]


def require_login():
    if not session.get("user"):
        return redirect(url_for("login", next=request.path))
    return None


def require_admin():
    guard = require_login()
    if guard:
        return guard
    users = github_store.users_store.load()
    if users.get(session["user"], {}).get("role") != "admin":
        abort(403)
    return None


def is_admin(username) -> bool:
    if not username:
        return False
    users = github_store.users_store.load()
    return users.get(username, {}).get("role") == "admin"


@app.context_processor
def inject_user():
    return {"current_user": session.get("user"), "current_user_is_admin": is_admin(session.get("user"))}


# ---------- простой формат теста: "- вариант *" — правильный ----------

def parse_quiz(raw: str):
    if not raw or not raw.strip():
        return None
    questions = []
    current = None
    for line in raw.splitlines():
        line = line.rstrip()
        if not line.strip():
            continue
        if line.lstrip().startswith("-"):
            if current is None:
                continue
            text = line.lstrip()[1:].strip()
            correct = text.endswith("*")
            if correct:
                text = text[:-1].strip()
            current["options"].append(text)
            if correct:
                current["correct"].append(len(current["options"]) - 1)
        else:
            current = {"question": line.strip(), "options": [], "correct": []}
            questions.append(current)
    questions = [q for q in questions if q["options"] and q["correct"]]
    return questions or None


def quiz_to_text(quiz) -> str:
    if not quiz:
        return ""
    lines = []
    for q in quiz:
        lines.append(q["question"])
        for i, opt in enumerate(q["options"]):
            mark = " *" if i in q["correct"] else ""
            lines.append(f"- {opt}{mark}")
        lines.append("")
    return "\n".join(lines).strip()


@app.get("/health")
def health():
    return "ok"


# ---------- аккаунты ----------

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        invite = request.form.get("invite", "")
        username = request.form.get("username", "").strip().lower()
        display_name = request.form.get("display_name", "").strip()
        password = request.form.get("password", "")
        users = github_store.users_store.load()
        if invite not in (INVITE_CODE, ADMIN_INVITE_CODE):
            error = "Неверный код приглашения — уточните у Ольги"
        elif not username or not password or not display_name:
            error = "Заполните все поля"
        elif username in users:
            error = "Такой логин уже занят, выберите другой"
        elif len(password) < 6:
            error = "Пароль слишком короткий (минимум 6 символов)"
        else:
            users[username] = {
                "display_name": display_name,
                "password_hash": generate_password_hash(password),
                "role": "admin" if invite == ADMIN_INVITE_CODE else "member",
                "active": True,
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            github_store.users_store.save(users, f"вики: регистрация «{username}»")
            session["user"] = username
            return redirect(url_for("home"))
    return render_template("register.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        users = github_store.users_store.load()
        account = users.get(username)
        if account and not account.get("active", True):
            error = "Доступ отключён администратором"
        elif account and check_password_hash(account["password_hash"], password):
            session["user"] = username
            return redirect(request.args.get("next") or url_for("home"))
        else:
            error = "Неверный логин или пароль"
    return render_template("login.html", error=error)


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def display_name(username: str) -> str:
    if not username:
        return "коллега"
    users = github_store.users_store.load()
    return users.get(username, {}).get("display_name", username)


# ---------- админ: доступ сотрудников ----------

@app.get("/admin/users")
def admin_users():
    guard = require_admin()
    if guard:
        return guard
    users = github_store.users_store.load()
    rows = sorted(
        [{"username": u, **a} for u, a in users.items()],
        key=lambda a: a.get("display_name", a["username"]).lower(),
    )
    return render_template("admin_users.html", rows=rows)


@app.post("/admin/users/<username>/toggle")
def admin_toggle_user(username):
    guard = require_admin()
    if guard:
        return guard
    if username == session.get("user"):
        abort(400)  # нельзя отключить самого себя
    users = github_store.users_store.load()
    if username not in users:
        abort(404)
    users[username]["active"] = not users[username].get("active", True)
    state = "включён" if users[username]["active"] else "отключён"
    github_store.users_store.save(users, f"админ: доступ «{username}» {state}")
    return redirect(url_for("admin_users"))


# ---------- главная ----------

@app.get("/")
def home():
    guard = require_login()
    if guard:
        return guard
    pages = github_store.pages_store.load()
    lessons = [p for p in pages.values() if p.get("course_order") is not None]
    progress = github_store.progress_store.load().get(session["user"], {})
    done = sum(1 for p in pages if pages[p].get("course_order") is not None and p in progress)
    return render_template("home.html", lessons_total=len(lessons), lessons_done=done)


# ---------- обучение ----------

@app.get("/course")
def course_list():
    guard = require_login()
    if guard:
        return guard
    pages = github_store.pages_store.load()
    progress = github_store.progress_store.load().get(session["user"], {})
    lessons = [
        {"slug": slug, "done": slug in progress, **meta}
        for slug, meta in pages.items()
        if meta.get("course_order") is not None
    ]
    lessons.sort(key=lambda it: it["course_order"])
    return render_template("course_list.html", lessons=lessons)


@app.get("/course/<slug>")
def course_view(slug):
    guard = require_login()
    if guard:
        return guard
    pages = github_store.pages_store.load()
    page = pages.get(slug)
    if not page or page.get("course_order") is None:
        abort(404)
    lessons = sorted(
        [{"slug": s, **m} for s, m in pages.items() if m.get("course_order") is not None],
        key=lambda it: it["course_order"],
    )
    idx = next(i for i, it in enumerate(lessons) if it["slug"] == slug)
    prev_lesson = lessons[idx - 1] if idx > 0 else None
    next_lesson = lessons[idx + 1] if idx + 1 < len(lessons) else None
    progress = github_store.progress_store.load().get(session["user"], {})
    quiz = page.get("quiz")
    quiz_for_view = [{"question": q["question"], "options": q["options"]} for q in quiz] if quiz else None
    return render_template(
        "course_view.html", page=page, slug=slug,
        prev_lesson=prev_lesson, next_lesson=next_lesson,
        done=slug in progress, entry=progress.get(slug), quiz=quiz_for_view,
    )


@app.post("/course/<slug>/complete")
def course_complete(slug):
    guard = require_login()
    if guard:
        return guard
    pages = github_store.pages_store.load()
    if slug not in pages or pages[slug].get("course_order") is None:
        abort(404)
    if pages[slug].get("quiz"):
        abort(400)  # у урока есть тест — засчитывается только через него
    progress = github_store.progress_store.load()
    user_progress = progress.setdefault(session["user"], {})
    if request.form.get("undo") == "1":
        user_progress.pop(slug, None)
        msg = f"прогресс: {session['user']} снял отметку с «{pages[slug]['title']}»"
    else:
        user_progress[slug] = {"completed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "score": None}
        msg = f"прогресс: {session['user']} прошёл «{pages[slug]['title']}»"
    github_store.progress_store.save(progress, msg)
    return redirect(url_for("course_view", slug=slug))


@app.post("/course/<slug>/quiz")
def course_quiz_submit(slug):
    guard = require_login()
    if guard:
        return guard
    pages = github_store.pages_store.load()
    page = pages.get(slug)
    quiz = page.get("quiz") if page else None
    if not page or page.get("course_order") is None or not quiz:
        abort(404)

    total = len(quiz)
    correct_count = 0
    results = []
    for i, q in enumerate(quiz):
        picked = {int(v) for v in request.form.getlist(f"q{i}")}
        is_correct = picked == set(q["correct"])
        correct_count += int(is_correct)
        results.append({"question": q["question"], "options": q["options"],
                         "correct": q["correct"], "picked": picked, "is_correct": is_correct})

    passed = correct_count == total
    if passed:
        progress = github_store.progress_store.load()
        user_progress = progress.setdefault(session["user"], {})
        user_progress[slug] = {
            "completed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "score": f"{correct_count}/{total}",
        }
        github_store.progress_store.save(
            progress, f"прогресс: {session['user']} сдал тест «{page['title']}» ({correct_count}/{total})")

    lessons = sorted(
        [{"slug": s, **m} for s, m in pages.items() if m.get("course_order") is not None],
        key=lambda it: it["course_order"],
    )
    idx = next(i for i, it in enumerate(lessons) if it["slug"] == slug)
    prev_lesson = lessons[idx - 1] if idx > 0 else None
    next_lesson = lessons[idx + 1] if idx + 1 < len(lessons) else None
    progress_now = github_store.progress_store.load().get(session["user"], {})
    return render_template(
        "course_view.html", page=page, slug=slug,
        prev_lesson=prev_lesson, next_lesson=next_lesson,
        done=slug in progress_now, entry=progress_now.get(slug),
        quiz_result={"passed": passed, "correct": correct_count, "total": total, "results": results},
        quiz=[{"question": q["question"], "options": q["options"]} for q in quiz],
    )


@app.get("/course/progress")
def course_progress_overview():
    """Общая таблица прогресса — видно всем, у кого есть логин (внутренняя команда)."""
    guard = require_login()
    if guard:
        return guard
    pages = github_store.pages_store.load()
    lessons = sorted(
        [{"slug": s, **m} for s, m in pages.items() if m.get("course_order") is not None],
        key=lambda it: it["course_order"],
    )
    users = github_store.users_store.load()
    progress = github_store.progress_store.load()
    rows = []
    for username, account in sorted(users.items(), key=lambda kv: kv[1].get("display_name", kv[0])):
        done = sum(1 for lesson in lessons if lesson["slug"] in progress.get(username, {}))
        rows.append({"name": account.get("display_name", username), "done": done})
    return render_template("course_progress.html", rows=rows, total=len(lessons))


# ---------- вики (база знаний, не входит в курс) ----------

@app.get("/wiki")
def wiki_list():
    guard = require_login()
    if guard:
        return guard
    pages = github_store.pages_store.load()
    q = request.args.get("q", "").strip().lower()
    items = [
        {"slug": slug, **meta}
        for slug, meta in pages.items()
        if meta.get("course_order") is None
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
    return render_template("wiki_edit.html", page=None, slug=None, quiz_text="")


@app.post("/wiki/new")
def wiki_new():
    course_order = request.form.get("course_order", "").strip()
    guard = require_admin() if course_order else require_login()
    if guard:
        return guard
    title = request.form.get("title", "").strip() or "Без названия"
    html = sanitize(request.form.get("html", ""))
    quiz = parse_quiz(request.form.get("quiz_text", ""))
    pages = github_store.pages_store.load()
    slug = new_slug()
    while slug in pages:
        slug = new_slug()
    pages[slug] = {
        "title": title,
        "html": html,
        "course_order": int(course_order) if course_order else None,
        "quiz": quiz,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "updated_by": display_name(session.get("user")),
    }
    github_store.pages_store.save(pages, f"вики: новая страница «{title}»")
    dest = "course_view" if pages[slug]["course_order"] is not None else "wiki_view"
    return redirect(url_for(dest, slug=slug))


@app.get("/wiki/<slug>")
def wiki_view(slug):
    guard = require_login()
    if guard:
        return guard
    pages = github_store.pages_store.load()
    page = pages.get(slug)
    if not page or page.get("course_order") is not None:
        abort(404)
    return render_template("wiki_view.html", page=page, slug=slug)


@app.get("/wiki/<slug>/edit")
def wiki_edit_form(slug):
    pages = github_store.pages_store.load()
    page = pages.get(slug)
    is_lesson = bool(page and page.get("course_order") is not None)
    guard = require_admin() if is_lesson else require_login()
    if guard:
        return guard
    if not page:
        abort(404)
    return render_template("wiki_edit.html", page=page, slug=slug, quiz_text=quiz_to_text(page.get("quiz")))


@app.post("/wiki/<slug>/edit")
def wiki_edit(slug):
    pages = github_store.pages_store.load()
    course_order = request.form.get("course_order", "").strip()
    was_lesson = slug in pages and pages[slug].get("course_order") is not None
    guard = require_admin() if (course_order or was_lesson) else require_login()
    if guard:
        return guard
    if slug not in pages:
        abort(404)
    title = request.form.get("title", "").strip() or "Без названия"
    html = sanitize(request.form.get("html", ""))
    quiz = parse_quiz(request.form.get("quiz_text", ""))
    pages[slug] = {
        "title": title,
        "html": html,
        "course_order": int(course_order) if course_order else None,
        "quiz": quiz,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "updated_by": display_name(session.get("user")),
    }
    github_store.pages_store.save(pages, f"вики: правка «{title}»")
    dest = "course_view" if pages[slug]["course_order"] is not None else "wiki_view"
    return redirect(url_for(dest, slug=slug))


@app.post("/wiki/<slug>/delete")
def wiki_delete(slug):
    pages = github_store.pages_store.load()
    is_lesson = slug in pages and pages[slug].get("course_order") is not None
    guard = require_admin() if is_lesson else require_login()
    if guard:
        return guard
    if slug in pages:
        title = pages[slug]["title"]
        was_lesson = pages[slug].get("course_order") is not None
        del pages[slug]
        github_store.pages_store.save(pages, f"вики: удалена страница «{title}»")
    else:
        was_lesson = False
    return redirect(url_for("course_list") if was_lesson else url_for("wiki_list"))


@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True, port=5000)
