"""
Database Migration Script for CineHub
Adds movie status, TMDb metadata, and showtime schedule/lifecycle columns.
"""

import sqlite3
import os
from datetime import date, datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'cinematic_pulse.db')


def parse_time_to_24h(time_str: str) -> str:
    """Converts '10:00 AM' or '07:00 PM (Prime)' to '10:00' or '19:00'."""
    if not time_str:
        return "18:00"
    parts = time_str.strip().split()
    if len(parts) >= 2:
        clean = f"{parts[0]} {parts[1].upper()}"
        for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
            try:
                dt = datetime.strptime(clean, fmt)
                return dt.strftime("%H:%M")
            except ValueError:
                pass
    try:
        dt = datetime.strptime(parts[0], "%H:%M")
        return dt.strftime("%H:%M")
    except ValueError:
        return "18:00"


def run_migration():
    print(f"Connecting to database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # --- 1. MIGRATION FOR MOVIES TABLE ---
    movies_cols = [r[1] for r in cur.execute("PRAGMA table_info(movies)").fetchall()]
    print("Existing movies columns:", movies_cols)

    if 'status' not in movies_cols:
        cur.execute("ALTER TABLE movies ADD COLUMN status TEXT DEFAULT 'NOW_SHOWING'")
        print("  + Added 'status' to movies (DEFAULT 'NOW_SHOWING')")

    if 'tmdb_id' not in movies_cols:
        cur.execute("ALTER TABLE movies ADD COLUMN tmdb_id INTEGER")
        print("  + Added 'tmdb_id' to movies")

    if 'description' not in movies_cols:
        cur.execute("ALTER TABLE movies ADD COLUMN description TEXT")
        print("  + Added 'description' to movies")

    if 'release_date' not in movies_cols:
        cur.execute("ALTER TABLE movies ADD COLUMN release_date TEXT")
        print("  + Added 'release_date' to movies")

    cur.execute("UPDATE movies SET status = 'NOW_SHOWING' WHERE status IS NULL")

    # --- 2. MIGRATION FOR SHOWTIMES TABLE ---
    showtimes_cols = [r[1] for r in cur.execute("PRAGMA table_info(showtimes)").fetchall()]
    print("Existing showtimes columns:", showtimes_cols)

    if 'show_date' not in showtimes_cols:
        cur.execute("ALTER TABLE showtimes ADD COLUMN show_date TEXT")
        print("  + Added 'show_date' (YYYY-MM-DD) to showtimes")

    if 'show_time_24' not in showtimes_cols:
        cur.execute("ALTER TABLE showtimes ADD COLUMN show_time_24 TEXT")
        print("  + Added 'show_time_24' (HH:MM) to showtimes")

    if 'status' not in showtimes_cols:
        cur.execute("ALTER TABLE showtimes ADD COLUMN status TEXT DEFAULT 'ACTIVE'")
        print("  + Added 'status' to showtimes (DEFAULT 'ACTIVE')")

    # Backfill missing dates & 24h times for existing showtimes
    today = date.today().isoformat()
    rows = cur.execute("SELECT showtime_id, show_time, show_date, show_time_24 FROM showtimes").fetchall()
    updated_shows = 0
    for r in rows:
        needs_update = False
        s_date = r['show_date'] or today
        s_time_24 = r['show_time_24'] or parse_time_to_24h(r['show_time'])
        if r['show_date'] != s_date or r['show_time_24'] != s_time_24:
            cur.execute("""
                UPDATE showtimes
                SET show_date = ?, show_time_24 = ?, status = COALESCE(status, 'ACTIVE')
                WHERE showtime_id = ?
            """, (s_date, s_time_24, r['showtime_id']))
            updated_shows += 1

    print(f"  + Backfilled show_date and show_time_24 for {updated_shows} showtimes")

    # Create index for fast date/status queries
    cur.execute("CREATE INDEX IF NOT EXISTS idx_showtimes_schedule ON showtimes(show_date, show_time_24, status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_movies_status ON movies(status)")

    conn.commit()
    conn.close()
    print("Migration finished successfully!")


if __name__ == '__main__':
    run_migration()
