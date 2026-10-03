import sqlite3
import unittest
from datetime import date, timedelta

from library_system import FINE_PER_DAY, LOAN_DAYS, Library


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.lib = Library(":memory:")
        self.book = self.lib.add_book("Clean Code", "Robert C. Martin", "Programming", 2)
        self.member = self.lib.add_member("Arun Kumar", "arun@example.com")

    def tearDown(self):
        self.lib.close()

    def test_search_by_title_author_and_category(self):
        for keyword in ("Clean", "Martin", "Programming"):
            self.assertEqual(len(self.lib.search_books(keyword)), 1)
        self.assertEqual(self.lib.search_books("Biology"), [])

    def test_issue_reduces_stock_and_sets_due_date(self):
        on = date(2026, 1, 1)
        msg = self.lib.issue_book(self.book, self.member, on=on)
        self.assertIn((on + timedelta(days=LOAN_DAYS)).isoformat(), msg)
        self.assertEqual(self.lib.list_books()[0]["available"], 1)

    def test_cannot_issue_without_copies(self):
        self.lib.issue_book(self.book, self.member)
        self.lib.issue_book(self.book, self.member)
        self.assertIn("no copies", self.lib.issue_book(self.book, self.member))

    def test_unknown_book_is_rejected(self):
        self.assertIn("not found", self.lib.issue_book(999, self.member))

    def test_on_time_return_has_no_fine(self):
        on = date(2026, 1, 1)
        self.lib.issue_book(self.book, self.member, on=on)
        msg = self.lib.return_book(1, on=on + timedelta(days=LOAN_DAYS))
        self.assertIn("Fine: Rs.0", msg)
        self.assertEqual(self.lib.list_books()[0]["available"], 2)

    def test_late_return_fine(self):
        on = date(2026, 1, 1)
        self.lib.issue_book(self.book, self.member, on=on)
        msg = self.lib.return_book(1, on=on + timedelta(days=LOAN_DAYS + 6))
        self.assertIn(f"Fine: Rs.{6 * FINE_PER_DAY}", msg)
        self.assertEqual(self.lib.stats()["fines"], 6 * FINE_PER_DAY)

    def test_cannot_return_twice(self):
        self.lib.issue_book(self.book, self.member)
        self.lib.return_book(1)
        self.assertIn("not found", self.lib.return_book(1))

    def test_duplicate_email_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.lib.add_member("Someone Else", "arun@example.com")

    def test_stats_counts_overdue(self):
        self.lib.issue_book(self.book, self.member, on=date.today() - timedelta(days=30))
        s = self.lib.stats()
        self.assertEqual((s["issued"], s["overdue"]), (1, 1))


if __name__ == "__main__":
    unittest.main()
