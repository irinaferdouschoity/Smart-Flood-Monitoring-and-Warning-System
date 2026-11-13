"""Create the MySQL database + tables and add the 6 starter locations.

Run from the project root (virtual environment active):
    python scripts/setup_database.py

Safe to run more than once: tables use CREATE IF NOT EXISTS and locations are
only added when the locations table is empty.
"""
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pymysql
from sqlalchemy.engine import make_url

from backend.config import settings

SCHEMA = Path(__file__).resolve().parents[1] / "sql" / "schema.sql"

# IDs match data/city_specific_risk.csv and the flood-label CSVs.
LOCATIONS = [
    (1, "Dhaka", "Bangladesh", 23.8103, 90.4125),
    (5, "Mumbai", "India", 19.0760, 72.8777),
    (6, "Jakarta", "Indonesia", -6.2088, 106.8456),
    (7, "London", "United Kingdom", 51.5074, -0.1278),
    (8, "New Orleans", "United States", 29.9511, -90.0715),
    (9, "Tokyo", "Japan", 35.6762, 139.6503),
]


def main():
    url = make_url(settings.database_url)
    try:
        conn = pymysql.connect(
            host=url.host or "localhost",
            port=url.port or 3306,
            user=url.username or "root",
            password=url.password or "",
            charset="utf8mb4",
            autocommit=True,
        )
    except pymysql.err.OperationalError as exc:
        raise SystemExit(
            "\nCould not connect to MySQL.\n"
            "  1. Is MySQL started in the XAMPP Control Panel?\n"
            "  2. Is DATABASE_URL in .env correct (user / password / port)?\n"
            f"Details: {exc}\n"
        )

    with conn:
        cur = conn.cursor()
        sql = SCHEMA.read_text(encoding="utf-8")
        for statement in sql.split(";"):
            if statement.strip():
                cur.execute(statement)
        print("Database and tables are ready.")

        cur.execute(f"USE `{url.database}`")
        cur.execute("SELECT COUNT(*) FROM locations")
        if cur.fetchone()[0] == 0:
            for loc_id, name, country, lat, lon in LOCATIONS:
                cur.execute(
                    "INSERT INTO locations "
                    "(location_id, location_name, country, latitude, longitude, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (loc_id, name, country, lat, lon, datetime.utcnow()),
                )
            print(f"Added {len(LOCATIONS)} starter locations.")
        else:
            print("Locations already exist - left unchanged.")


if __name__ == "__main__":
    main()
