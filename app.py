"""Flask web interface for the Library Management System.

Run:  python app.py      then open  http://127.0.0.1:5000
"""
import os
import sqlite3
from datetime import date, timedelta

from flask import Flask, flash, g, redirect, render_template, request, url_for

from library_system import FINE_PER_DAY, LOAN_DAYS, Library

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
DB = os.environ.get("LIBRARY_DB", "library.db")


def get_lib():
    if "lib" not in g:
        g.lib = Library(DB)
    return g.lib


@app.teardown_appcontext
def close_lib(_exc):
    lib = g.pop("lib", None)
    if lib is not None:
        lib.close()


def notify(message):
    """Flash a library message, colouring it red if it starts with 'Error'."""
    flash(message, "error" if message.startswith("Error") else "success")


@app.context_processor
def inject_globals():
    return {"LOAN_DAYS": LOAN_DAYS, "FINE_PER_DAY": FINE_PER_DAY, "today": date.today().isoformat()}


@app.route("/")
def dashboard():
    return render_template("dashboard.html", stats=get_lib().stats())


@app.route("/books", methods=["GET", "POST"])
def books():
    lib = get_lib()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        category = request.form.get("category", "").strip()
        try:
            copies = int(request.form.get("copies", "1"))
        except ValueError:
            copies = 0
        if not title or not author or copies < 1:
            flash("Error: title, author and at least 1 copy are required", "error")
        else:
            book_id = lib.add_book(title, author, category, copies)
            flash(f"Added '{title}' (Book ID {book_id})", "success")
        return redirect(url_for("books"))
    q = request.args.get("q", "").strip()
    rows = lib.search_books(q) if q else lib.list_books()
    return render_template("books.html", books=rows, q=q)


@app.route("/members", methods=["GET", "POST"])
def members():
    lib = get_lib()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        if not name or not email:
            flash("Error: name and email are required", "error")
        else:
            try:
                member_id = lib.add_member(name, email)
                flash(f"Registered {name} (Member ID {member_id})", "success")
            except sqlite3.IntegrityError:
                flash("Error: a member with that email already exists", "error")
        return redirect(url_for("members"))
    return render_template("members.html", members=lib.list_members())


@app.route("/circulation")
def circulation():
    lib = get_lib()
    today = date.today()
    active = []
    for r in lib.issued_report():
        late = max(0, (today - date.fromisoformat(r["due_date"])).days)
        active.append({**dict(r), "late_days": late, "fine_now": late * FINE_PER_DAY})
    available_books = [b for b in lib.list_books() if b["available"] > 0]
    return render_template("circulation.html", active=active, books=available_books,
                           members=lib.list_members(), history=lib.history())


@app.route("/issue", methods=["POST"])
def issue():
    try:
        book_id = int(request.form["book_id"])
        member_id = int(request.form["member_id"])
    except (KeyError, ValueError):
        flash("Error: choose a book and a member", "error")
        return redirect(url_for("circulation"))
    on = None
    raw = request.form.get("issue_date", "").strip()
    if raw:
        try:
            on = date.fromisoformat(raw)
        except ValueError:
            flash("Error: invalid date", "error")
            return redirect(url_for("circulation"))
        if on > date.today():
            flash("Error: issue date cannot be in the future", "error")
            return redirect(url_for("circulation"))
    notify(get_lib().issue_book(book_id, member_id, on=on))
    return redirect(url_for("circulation"))


@app.route("/return/<int:txn_id>", methods=["POST"])
def return_(txn_id):
    notify(get_lib().return_book(txn_id))
    return redirect(url_for("circulation"))


@app.route("/seed", methods=["POST"])
def seed():
    """Load sample data so the system can be demonstrated straight away."""
    lib = get_lib()
    if lib.stats()["titles"] == 0:
        for t, a, c, n in [("Python Crash Course", "Eric Matthes", "Programming", 3),
                           ("Database System Concepts", "Silberschatz", "Databases", 2),
                           ("Wings of Fire", "A.P.J. Abdul Kalam", "Biography", 1),
                           ("Clean Code", "Robert C. Martin", "Programming", 2),
                           ("Artificial Intelligence: A Modern Approach", "Russell & Norvig", "AI", 2)]:
            lib.add_book(t, a, c, n)
        try:
            lib.add_member("Arun Kumar", "arun@example.com")
            lib.add_member("Priya Raman", "priya@example.com")
        except sqlite3.IntegrityError:
            pass
        lib.issue_book(1, 1, on=date.today() - timedelta(days=20))   # overdue by 6 days
        lib.issue_book(3, 2, on=date.today() - timedelta(days=5))
        flash("Sample data loaded - one book is already overdue so you can test the fine.", "success")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
