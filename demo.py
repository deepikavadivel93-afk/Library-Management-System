"""Non-interactive demo that exercises every feature and prints the output."""
import os
from datetime import date, timedelta
from library_system import Library

if os.path.exists("demo.db"): os.remove("demo.db")
lib = Library("demo.db")
today = date(2026, 10, 1)

print(">>> Adding books")
for t, a, c, n in [("Python Crash Course", "Eric Matthes", "Programming", 3),
                   ("Database System Concepts", "Silberschatz", "Databases", 2),
                   ("Wings of Fire", "A.P.J. Abdul Kalam", "Biography", 1),
                   ("Clean Code", "Robert C. Martin", "Programming", 2)]:
    print(f"Book ID {lib.add_book(t, a, c, n)} -> {t}")

print("\n>>> Registering members")
print("Member ID", lib.add_member("Arun Kumar", "arun@example.com"))
print("Member ID", lib.add_member("Priya Raman", "priya@example.com"))

print("\n>>> Searching for 'Programming'")
for b in lib.search_books("Programming"):
    print(b["book_id"], b["title"], "-", b["author"], f"({b['available']}/{b['copies']} available)")

print("\n>>> Issuing books")
print(lib.issue_book(1, 1, on=today - timedelta(days=20)))
print(lib.issue_book(3, 2, on=today - timedelta(days=5)))
print(lib.issue_book(3, 1, on=today))
print(lib.issue_book(99, 1, on=today))

print("\n>>> Issued books report")
for r in lib.issued_report():
    print(tuple(r))

print("\n>>> Returning books")
print(lib.return_book(1, on=today))
print(lib.return_book(1, on=today))

print("\n>>> Inventory")
for r in lib.inventory_report():
    print(tuple(r))
