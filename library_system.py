"""Library Management System - Python + SQLite
Features: add/search books, register members, issue/return with fine calculation, reports.
"""
import sqlite3
from datetime import date, timedelta

DB_FILE = "library.db"
LOAN_DAYS = 14
FINE_PER_DAY = 2  # Rs. per day late


class Library:
    def __init__(self, db_file=DB_FILE):
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def close(self):
        self.conn.close()

    def _create_tables(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS books(
            book_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, author TEXT NOT NULL,
            category TEXT, copies INTEGER NOT NULL DEFAULT 1,
            available INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS members(
            member_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT UNIQUE);
        CREATE TABLE IF NOT EXISTS transactions(
            txn_id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER REFERENCES books(book_id),
            member_id INTEGER REFERENCES members(member_id),
            issue_date TEXT NOT NULL, due_date TEXT NOT NULL,
            return_date TEXT, fine INTEGER DEFAULT 0);
        """)
        self.conn.commit()

    # ---- Books ----
    def add_book(self, title, author, category, copies=1):
        cur = self.conn.execute(
            "INSERT INTO books(title,author,category,copies,available) VALUES(?,?,?,?,?)",
            (title, author, category, copies, copies))
        self.conn.commit()
        return cur.lastrowid

    def search_books(self, keyword):
        like = f"%{keyword}%"
        return self.conn.execute(
            "SELECT * FROM books WHERE title LIKE ? OR author LIKE ? OR category LIKE ?",
            (like, like, like)).fetchall()

    # ---- Members ----
    def add_member(self, name, email):
        cur = self.conn.execute("INSERT INTO members(name,email) VALUES(?,?)", (name, email))
        self.conn.commit()
        return cur.lastrowid

    # ---- Issue / Return ----
    def issue_book(self, book_id, member_id, on=None):
        on = on or date.today()
        book = self.conn.execute("SELECT * FROM books WHERE book_id=?", (book_id,)).fetchone()
        if book is None:
            return "Error: book not found"
        if book["available"] < 1:
            return "Error: no copies available"
        due = on + timedelta(days=LOAN_DAYS)
        self.conn.execute(
            "INSERT INTO transactions(book_id,member_id,issue_date,due_date) VALUES(?,?,?,?)",
            (book_id, member_id, on.isoformat(), due.isoformat()))
        self.conn.execute("UPDATE books SET available=available-1 WHERE book_id=?", (book_id,))
        self.conn.commit()
        return f"Issued '{book['title']}' - due on {due.isoformat()}"

    def return_book(self, txn_id, on=None):
        on = on or date.today()
        t = self.conn.execute("SELECT * FROM transactions WHERE txn_id=? AND return_date IS NULL",
                              (txn_id,)).fetchone()
        if t is None:
            return "Error: active transaction not found"
        late = (on - date.fromisoformat(t["due_date"])).days
        fine = max(0, late) * FINE_PER_DAY
        self.conn.execute("UPDATE transactions SET return_date=?, fine=? WHERE txn_id=?",
                          (on.isoformat(), fine, txn_id))
        self.conn.execute("UPDATE books SET available=available+1 WHERE book_id=?", (t["book_id"],))
        self.conn.commit()
        return f"Returned. Late by {max(0, late)} day(s). Fine: Rs.{fine}"

    # ---- Listing helpers (used by the web interface) ----
    def list_books(self):
        return self.conn.execute("SELECT * FROM books ORDER BY title").fetchall()

    def list_members(self):
        return self.conn.execute("SELECT * FROM members ORDER BY name").fetchall()

    def history(self, limit=15):
        return self.conn.execute("""
            SELECT t.txn_id, b.title, m.name, t.issue_date, t.return_date, t.fine
            FROM transactions t JOIN books b USING(book_id) JOIN members m USING(member_id)
            WHERE t.return_date IS NOT NULL ORDER BY t.return_date DESC, t.txn_id DESC LIMIT ?""",
            (limit,)).fetchall()

    def stats(self, today=None):
        today = (today or date.today()).isoformat()
        q = lambda sql, *a: self.conn.execute(sql, a).fetchone()[0]
        return {
            "titles": q("SELECT COUNT(*) FROM books"),
            "copies": q("SELECT COALESCE(SUM(copies),0) FROM books"),
            "available": q("SELECT COALESCE(SUM(available),0) FROM books"),
            "issued": q("SELECT COUNT(*) FROM transactions WHERE return_date IS NULL"),
            "overdue": q("SELECT COUNT(*) FROM transactions WHERE return_date IS NULL AND due_date < ?", today),
            "members": q("SELECT COUNT(*) FROM members"),
            "fines": q("SELECT COALESCE(SUM(fine),0) FROM transactions"),
        }

    # ---- Reports ----
    def issued_report(self):
        return self.conn.execute("""
            SELECT t.txn_id, b.title, m.name, t.issue_date, t.due_date
            FROM transactions t JOIN books b USING(book_id) JOIN members m USING(member_id)
            WHERE t.return_date IS NULL ORDER BY t.due_date""").fetchall()

    def inventory_report(self):
        return self.conn.execute("SELECT book_id,title,copies,available FROM books").fetchall()


def menu():
    lib = Library()
    options = """
===== LIBRARY MANAGEMENT SYSTEM =====
1. Add Book        2. Search Books    3. Add Member
4. Issue Book      5. Return Book     6. Issued Books Report
7. Inventory       0. Exit"""
    while True:
        print(options)
        ch = input("Enter choice: ").strip()
        if ch == "1":
            print("Book ID:", lib.add_book(input("Title: "), input("Author: "),
                                           input("Category: "), int(input("Copies: "))))
        elif ch == "2":
            for b in lib.search_books(input("Keyword: ")):
                print(b["book_id"], b["title"], "-", b["author"], f"({b['available']}/{b['copies']})")
        elif ch == "3":
            print("Member ID:", lib.add_member(input("Name: "), input("Email: ")))
        elif ch == "4":
            print(lib.issue_book(int(input("Book ID: ")), int(input("Member ID: "))))
        elif ch == "5":
            print(lib.return_book(int(input("Transaction ID: "))))
        elif ch == "6":
            for r in lib.issued_report():
                print(tuple(r))
        elif ch == "7":
            for r in lib.inventory_report():
                print(tuple(r))
        elif ch == "0":
            break
        else:
            print("Invalid choice")


if __name__ == "__main__":
    menu()
