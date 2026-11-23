# Catalog Feed Quality

Load daily supplier prices into SQLite, investigate rejected rows, and see which products changed price. This local portfolio demo uses synthetic INR data and models the validation and change-detection work in an [Upwork data engineering brief](https://www.upwork.com/freelance-jobs/apply/Data-Engineer-Python-SQL-ETL-Data-Quality_~022095648576606845827/).

## Run the example

From the repository root with Python 3.11+ and SQLite 3.25+:

    python pipeline.py
    python -m unittest -v

The six-line feed produces three observations, one duplicate, and two rejects on the first run. Tea drops from ₹125 to ₹120 and then to ₹99. The ₹120 record arrives last among the three dates. The SQL view orders by observation date so the price history still reads correctly.

## Bring a feed

    python pipeline.py supplier.jsonl --database catalog.sqlite

Provide one JSON object per UTF-8 line with a string sku, an ISO date, and a nonnegative integer price_paise. Each database represents one supplier and one currency. SKU matching ignores case and surrounding whitespace. The first accepted observation wins for a given SKU and day. A conflicting price goes to rejects with the original row, reason, and line number.

Each file loads within a transaction. Replaying a file preserves stored observations and reject counts. The console reports how each input line was handled on that invocation. Query price_changes for historical movements and rejects for rows requiring review. The demo reads each file into memory.
