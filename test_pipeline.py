import sqlite3
import unittest
from pathlib import Path

from pipeline import load


class FeedTest(unittest.TestCase):
    def test_backfill_conflict_and_replay(self):
        feed = Path(__file__).with_name("sample.jsonl")
        with sqlite3.connect(":memory:") as db:
            self.assertEqual(load(db, feed), {"inserted": 3, "duplicate": 1, "rejected": 2})
            self.assertEqual(load(db, feed), {"duplicate": 4, "rejected": 2})
            self.assertEqual(db.execute("SELECT COUNT(*) FROM rejects").fetchone()[0], 2)
            changes = db.execute("SELECT change_paise FROM price_changes ORDER BY day").fetchall()
            self.assertEqual(changes, [(-500,), (-2100,)])
