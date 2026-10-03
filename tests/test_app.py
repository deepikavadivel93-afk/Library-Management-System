import os
import tempfile
import unittest

import app as web


class WebAppTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        web.DB = self.path
        web.app.config["TESTING"] = True
        self.client = web.app.test_client()

    def tearDown(self):
        os.remove(self.path)

    def test_pages_load(self):
        for url in ("/", "/books", "/members", "/circulation"):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_full_workflow(self):
        self.client.post("/books", data={"title": "Wings of Fire", "author": "Kalam", "category": "Bio", "copies": "1"})
        self.client.post("/members", data={"name": "Priya", "email": "p@example.com"})
        r = self.client.post("/issue", data={"book_id": "1", "member_id": "1", "issue_date": "2020-01-01"},
                             follow_redirects=True)
        self.assertIn(b"Issued", r.data)
        self.assertIn(b"late", r.data)
        r = self.client.post("/return/1", follow_redirects=True)
        self.assertIn(b"Returned. Late by", r.data)
        r = self.client.get("/circulation")
        self.assertNotIn(b"Nothing returned yet", r.data)   # the return now shows in history
        self.assertIn(b"No books are currently issued", r.data)
        self.assertIn(b"Wings of Fire", self.client.get("/books?q=Kalam").data)

    def test_validation_errors(self):
        r = self.client.post("/books", data={"title": "", "author": "", "copies": "0"}, follow_redirects=True)
        self.assertIn(b"required", r.data)
        self.client.post("/members", data={"name": "A", "email": "a@x.com"})
        r = self.client.post("/members", data={"name": "B", "email": "a@x.com"}, follow_redirects=True)
        self.assertIn(b"already exists", r.data)
        r = self.client.post("/issue", data={"book_id": "", "member_id": ""}, follow_redirects=True)
        self.assertIn(b"choose a book", r.data)
        r = self.client.post("/issue", data={"book_id": "1", "member_id": "1", "issue_date": "2999-01-01"},
                             follow_redirects=True)
        self.assertIn(b"future", r.data)

    def test_seed_loads_sample_data_once(self):
        self.client.post("/seed")
        self.client.post("/seed")          # second call must not duplicate anything
        page = self.client.get("/books").data
        self.assertEqual(page.count(b"Python Crash Course"), 1)
        self.assertIn(b"Overdue", self.client.get("/").data)
        self.assertIn(b"6 day(s) late", self.client.get("/circulation").data)


if __name__ == "__main__":
    unittest.main()
