"""Load a daily INR price feed and report data quality outcomes."""
import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    sku TEXT NOT NULL, day TEXT NOT NULL, paise INTEGER NOT NULL,
    PRIMARY KEY (sku, day)
);
CREATE TABLE IF NOT EXISTS rejects (
    batch TEXT NOT NULL, line INTEGER NOT NULL, reason TEXT NOT NULL,
    raw TEXT NOT NULL, PRIMARY KEY (batch, line)
);
CREATE VIEW IF NOT EXISTS price_changes AS
WITH prior AS (
    SELECT *, lag(paise) OVER (PARTITION BY sku ORDER BY day) AS previous_paise
    FROM observations
)
SELECT sku, day, paise, previous_paise, paise - previous_paise AS change_paise
FROM prior WHERE previous_paise IS NOT NULL AND paise <> previous_paise;
"""


def normalize(raw):
    row = json.loads(raw)
    if not isinstance(row, dict):
        raise ValueError("expected an object")
    sku = row.get("sku")
    if not isinstance(sku, str) or not sku.strip():
        raise ValueError("missing SKU")
    day = row.get("date")
    if not isinstance(day, str):
        raise ValueError("missing date")
    day = date.fromisoformat(day).isoformat()
    price = row.get("price_paise")
    if type(price) is not int or not 0 <= price <= 2**63 - 1:
        raise ValueError("price must fit a nonnegative 64-bit integer")
    return sku.strip().upper(), day, price


def load(db, path):
    data = path.read_bytes()
    batch = hashlib.sha256(data).hexdigest()
    counts = Counter()
    db.executescript(SCHEMA)
    with db:
        db.execute("BEGIN IMMEDIATE")
        for line, raw in enumerate(data.decode("utf-8-sig").splitlines(), 1):
            try:
                sku, day, price = normalize(raw)
                previous = db.execute(
                    "SELECT paise FROM observations WHERE sku=? AND day=?", (sku, day)
                ).fetchone()
                if previous is None:
                    db.execute("INSERT INTO observations VALUES (?, ?, ?)", (sku, day, price))
                    counts["inserted"] += 1
                elif previous[0] == price:
                    counts["duplicate"] += 1
                else:
                    raise ValueError("conflicting price for existing SKU and day")
            except ValueError as error:
                db.execute("INSERT OR IGNORE INTO rejects VALUES (?, ?, ?, ?)",
                           (batch, line, str(error), raw))
                counts["rejected"] += 1
    return dict(counts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("feed", nargs="?", type=Path, default=Path(__file__).with_name("sample.jsonl"))
    parser.add_argument("--database", default="catalog.sqlite")
    args = parser.parse_args()
    with sqlite3.connect(args.database) as connection:
        print(json.dumps(load(connection, args.feed), sort_keys=True))
        for record in connection.execute("SELECT * FROM price_changes ORDER BY sku, day"):
            print(*record, sep=" | ")
