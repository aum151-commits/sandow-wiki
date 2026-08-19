# -*- coding: utf-8 -*-
"""«Сандов Фитнес» — один сайт, один логин: обучение (уроки по порядку
с личным прогрессом) и база знаний (свободная вики). Контент хранится
в приватном GitHub-репозитории (github_store.py), сама программа данных
не хранит — можно спокойно пересоздавать сервис.
"""

import os
import uuid
from datetime import date, datetime, timedelta, timezone

import bleach
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, abort, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import github_store
import trainer_link

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]

INVITE_CODE = os.environ["INVITE_CODE"]
ADMIN_INVITE_CODE = os.environ["ADMIN_INVITE_CODE"]

REVIEW_INTERVALS = [1, 3, 7, 30]  # дни до следующего повторения теста
CERT_SCORE_THRESHOLD = float(os.environ.get("CERT_SCORE_THRESHOLD", "0.7"))

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


def today() -> date:
    return datetime.now(timezone.utc).date()


def record_pass(user_progress: dict, slug: str, score) -> None:
    """Отмечает урок пройденным и продвигает интервальное повторение
    (1 → 3 → 7 → 30 дней). Если урок сдают повторно ДО наступления даты
    следующего повторения — это просто пересдача, этап не продвигается."""
    entry = user_progress.get(slug)
    prev_next_review = entry.get("next_review") if entry else None
    stage = entry.get("review_stage", 0) if entry else -1
    if entry is None or (prev_next_review and date.fromisoformat(prev_next_review) <= today()):
        stage += 1
    stage = max(stage, 0)
    next_review = (today() + timedelta(days=REVIEW_INTERVALS[stage])).isoformat() if stage < len(REVIEW_INTERVALS) else None
    user_progress[slug] = {
        "completed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "score": score,
        "review_stage": stage,
        "next_review": next_review,
    }


def due_for_review(pages: dict, progress: dict) -> set:
    t = today().isoformat()
    return {
        slug for slug, entry in progress.items()
        if entry.get("next_review") and entry["next_review"] <= t
        and pages.get(slug, {}).get("course_order") is not None
    }


def onboarding_day(username: str, users: dict) -> int:
    created = users.get(username, {}).get("created_at")
    if not created:
        return 0
    started = datetime.fromisoformat(created).date()
    return (today() - started).days


def touch_streak(username: str) -> None:
    users = github_store.users_store.load()
    account = users.get(username)
    if not account:
        return
    streak = account.setdefault("streak", {"count": 0, "last_activity_date": None})
    t = today().isoformat()
    if streak["last_activity_date"] == t:
        return
    yesterday = (today() - timedelta(days=1)).isoformat()
    streak["count"] = streak["count"] + 1 if streak["last_activity_date"] == yesterday else 1
    streak["last_activity_date"] = t
    github_store.users_store.save(users, f"стрик: {username} день {streak['count']}")


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


@app.post("/admin/users/<username>/buddy")
def admin_set_buddy(username):
    guard = require_admin()
    if guard:
        return guard
    users = github_store.users_store.load()
    if username not in users:
        abort(404)
    weeks = [request.form.get(f"week{i}") == "on" for i in range(1, 5)]
    users[username]["buddy"] = {"mentor": request.form.get("mentor", "").strip(), "weeks": weeks}
    github_store.users_store.save(users, f"наставничество: обновлена карточка «{username}»")
    return redirect(url_for("admin_users"))


# ---------- главная ----------

@app.get("/")
def home():
    guard = require_login()
    if guard:
        return guard
    touch_streak(session["user"])
    pages = github_store.pages_store.load()
    lessons = [p for p in pages.values() if p.get("course_order") is not None]
    user_progress = github_store.progress_store.load().get(session["user"], {})
    done = sum(1 for p in pages if pages[p].get("course_order") is not None and p in user_progress)
    review_count = len(due_for_review(pages, user_progress))
    users = github_store.users_store.load()
    streak = users.get(session["user"], {}).get("streak", {}).get("count", 0)
    day_n = onboarding_day(session["user"], users)
    return render_template(
        "home.html", lessons_total=len(lessons), lessons_done=done,
        review_count=review_count, streak=streak, day_n=day_n,
    )


# ---------- профиль: имя в тренажёре, допуск к звонкам ----------

def is_course_complete(username: str, pages: dict, progress: dict) -> bool:
    lessons = [s for s, m in pages.items() if m.get("course_order") is not None]
    return bool(lessons) and all(s in progress.get(username, {}) for s in lessons)


@app.get("/profile")
def profile():
    guard = require_login()
    if guard:
        return guard
    users = github_store.users_store.load()
    account = users.get(session["user"], {})
    pages = github_store.pages_store.load()
    progress = github_store.progress_store.load()
    course_done = is_course_complete(session["user"], pages, progress)
    return render_template(
        "profile.html", account=account, course_done=course_done,
        threshold=int(CERT_SCORE_THRESHOLD * 100),
    )


@app.post("/profile/trainer_name")
def profile_set_trainer_name():
    guard = require_login()
    if guard:
        return guard
    users = github_store.users_store.load()
    users[session["user"]]["trainer_name"] = request.form.get("trainer_name", "").strip()
    github_store.users_store.save(users, f"профиль: {session['user']} указал имя в тренажёре")
    return redirect(url_for("profile"))


@app.post("/profile/check_certification")
def profile_check_certification():
    guard = require_login()
    if guard:
        return guard
    users = github_store.users_store.load()
    account = users[session["user"]]
    pages = github_store.pages_store.load()
    progress = github_store.progress_store.load()
    course_done = is_course_complete(session["user"], pages, progress)

    result = trainer_link.best_score(account.get("trainer_name", ""))
    if result is None:
        status = {"checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "passed": False, "score": None, "sessions": 0, "error": True}
    else:
        ratio, sessions = result
        status = {
            "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "passed": course_done and ratio >= CERT_SCORE_THRESHOLD,
            "score": round(ratio * 100), "sessions": sessions, "error": False,
        }
    account["cert_status"] = status
    github_store.users_store.save(users, f"допуск к звонкам: проверка для {session['user']}")
    return redirect(url_for("profile"))


# ---------- обучение ----------

@app.get("/course")
def course_list():
    guard = require_login()
    if guard:
        return guard
    pages = github_store.pages_store.load()
    progress = github_store.progress_store.load().get(session["user"], {})
    due = due_for_review(pages, progress)
    users = github_store.users_store.load()
    day_n = onboarding_day(session["user"], users)
    lessons = [
        {"slug": slug, "done": slug in progress, "due": slug in due,
         "overdue": meta.get("plan_day") is not None and meta.get("plan_day") <= day_n and slug not in progress,
         **meta}
        for slug, meta in pages.items()
        if meta.get("course_order") is not None
    ]
    lessons.sort(key=lambda it: it["course_order"])
    return render_template("course_list.html", lessons=lessons, day_n=day_n)


@app.get("/course/review")
def course_review():
    guard = require_login()
    if guard:
        return guard
    pages = github_store.pages_store.load()
    progress = github_store.progress_store.load().get(session["user"], {})
    due = due_for_review(pages, progress)
    lessons = sorted(
        [{"slug": s, **pages[s]} for s in due],
        key=lambda it: it["course_order"],
    )
    return render_template("course_review.html", lessons=lessons)


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
    is_due = slug in due_for_review(pages, progress)
    return render_template(
        "course_view.html", page=page, slug=slug,
        prev_lesson=prev_lesson, next_lesson=next_lesson,
        done=slug in progress, entry=progress.get(slug), quiz=quiz_for_view, due=is_due,
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
        record_pass(user_progress, slug, None)
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
        record_pass(user_progress, slug, f"{correct_count}/{total}")
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
        done=slug in progress_now, entry=progress_now.get(slug), due=False,
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
        user_progress = progress.get(username, {})
        done = sum(1 for lesson in lessons if lesson["slug"] in user_progress)
        day_n = onboarding_day(username, users)
        overdue = sum(
            1 for lesson in lessons
            if lesson.get("plan_day") is not None and lesson["plan_day"] <= day_n
            and lesson["slug"] not in user_progress
        )
        cert = account.get("cert_status", {})
        rows.append({
            "name": account.get("display_name", username), "done": done, "day_n": day_n,
            "overdue": overdue, "certified": cert.get("passed", False),
            "buddy": account.get("buddy", {}),
        })
    return render_template("course_progress.html", rows=rows, total=len(lessons))


# ---------- вики (база знаний, не входит в курс) ----------

@app.get("/wiki")
def wiki_list():
    guard = require_login()
    if guard:
        return guard
    pages = github_store.pages_store.load()
    q = request.args.get("q", "").strip().lower()
    tag = request.args.get("tag", "").strip()
    items = [
        {"slug": slug, **meta}
        for slug, meta in pages.items()
        if meta.get("course_order") is None
    ]
    all_tags = sorted({t for it in items for t in (it.get("tags") or [])})
    if tag:
        items = [it for it in items if tag in (it.get("tags") or [])]
    if q:
        items = [
            it for it in items
            if q in it["title"].lower() or q in plain_text(it["html"]).lower()
        ]
    items.sort(key=lambda it: it["title"].lower())
    return render_template("wiki_list.html", items=items, q=request.args.get("q", ""), all_tags=all_tags, active_tag=tag)


@app.get("/wiki/new")
def wiki_new_form():
    guard = require_login()
    if guard:
        return guard
    return render_template("wiki_edit.html", page=None, slug=None, quiz_text="", tags_text="")


@app.post("/wiki/new")
def wiki_new():
    course_order = request.form.get("course_order", "").strip()
    guard = require_admin() if course_order else require_login()
    if guard:
        return guard
    title = request.form.get("title", "").strip() or "Без названия"
    html = sanitize(request.form.get("html", ""))
    quiz = parse_quiz(request.form.get("quiz_text", ""))
    plan_day = request.form.get("plan_day", "").strip()
    tags = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
    pages = github_store.pages_store.load()
    slug = new_slug()
    while slug in pages:
        slug = new_slug()
    pages[slug] = {
        "title": title,
        "html": html,
        "course_order": int(course_order) if course_order else None,
        "plan_day": int(plan_day) if plan_day else None,
        "quiz": quiz,
        "tags": tags,
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
    return render_template(
        "wiki_edit.html", page=page, slug=slug,
        quiz_text=quiz_to_text(page.get("quiz")), tags_text=", ".join(page.get("tags") or []),
    )


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
    plan_day = request.form.get("plan_day", "").strip()
    tags = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
    pages[slug] = {
        "title": title,
        "html": html,
        "course_order": int(course_order) if course_order else None,
        "plan_day": int(plan_day) if plan_day else None,
        "quiz": quiz,
        "tags": tags,
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
