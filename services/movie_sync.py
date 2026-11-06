"""
Movie Catalog Ingestion & Lifecycle Automation Service (CineHub)
Integrates with The Movie Database (TMDb) API and handles automated
lifecycle expiration and archiving, similar to BookMyShow.
"""

import os
import logging
import sqlite3
import requests
from datetime import datetime, date, timedelta

logger = logging.getLogger('movie_sync')
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

# TMDb Genre ID to Name Mapping
TMDB_GENRES = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
    80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
    14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
    9648: "Mystery", 10749: "Romance", 878: "Sci-Fi", 10770: "TV Movie",
    53: "Thriller", 10752: "War", 37: "Western"
}

# Curated fallback theatrical releases with verified, official TMDb CDN posters
CURATED_INDIAN_RELEASES = [
    {
        "id": 533535,
        "title": "Deadpool & Wolverine",
        "overview": "A listless Wade Wilson toils away in civilian life with his days as the morally flexible mercenary, Deadpool, behind him. But when his homeworld faces an existential threat, Wade must reluctantly suit-up again with an even more reluctant Wolverine.",
        "poster_path": "https://image.tmdb.org/t/p/w500/8cdWjvZQUExUUTzyp4t6EDMubfO.jpg",
        "genre": "Action / Comedy / Sci-Fi",
        "duration": "2h 08m",
        "rating": 8.1,
        "trailer_url": "https://www.youtube.com/embed/73_1biulkYk",
        "release_date": "2024-07-26",
        "votes": "48.2K"
    },
    {
        "id": 558449,
        "title": "Gladiator II",
        "overview": "Years after witnessing the death of the revered hero Maximus at the hands of his uncle, Lucius must enter the Colosseum after his home is conquered by the tyrannical Emperors who now lead Rome with an iron fist.",
        "poster_path": "https://image.tmdb.org/t/p/w500/2cxhvwyEwRlysAmRH4iodkvo0z5.jpg",
        "genre": "Action / Adventure / Drama",
        "duration": "2h 28m",
        "rating": 7.8,
        "trailer_url": "https://www.youtube.com/embed/4rgYUipGJNo",
        "release_date": "2024-11-15",
        "votes": "32.4K"
    },
    {
        "id": 693134,
        "title": "Dune: Part Two",
        "overview": "Follow the mythic journey of Paul Atreides as he unites with Chani and the Fremen while on a path of revenge against the conspirators who destroyed his family.",
        "poster_path": "https://image.tmdb.org/t/p/w500/1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg",
        "genre": "Sci-Fi / Adventure",
        "duration": "2h 46m",
        "rating": 8.9,
        "trailer_url": "https://www.youtube.com/embed/Way9Dexny3w",
        "release_date": "2024-03-01",
        "votes": "76.1K"
    },
    {
        "id": 872585,
        "title": "Oppenheimer",
        "overview": "The story of J. Robert Oppenheimer's role in the development of the atomic bomb during World War II.",
        "poster_path": "https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg",
        "genre": "Biography / Drama / History",
        "duration": "3h 00m",
        "rating": 8.9,
        "trailer_url": "https://www.youtube.com/embed/uYPbbksJxIg",
        "release_date": "2023-07-21",
        "votes": "84.3K"
    },
    {
        "id": 569094,
        "title": "Spider-Man: Across the Spider-Verse",
        "overview": "Miles Morales catapults across the Multiverse, where he encounters a team of Spider-People charged with protecting its very existence.",
        "poster_path": "https://image.tmdb.org/t/p/w500/8Vt6mWEReuy4Of61Lnj5Xj704m8.jpg",
        "genre": "Animation / Action / Adventure",
        "duration": "2h 20m",
        "rating": 8.7,
        "trailer_url": "https://www.youtube.com/embed/cqGjhVJWtEg",
        "release_date": "2023-06-02",
        "votes": "65.8K"
    },
    {
        "id": 157336,
        "title": "Interstellar",
        "overview": "The adventures of a group of explorers who make use of a newly discovered wormhole to surpass the limitations on human space travel.",
        "poster_path": "https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
        "genre": "Sci-Fi / Drama",
        "duration": "2h 49m",
        "rating": 8.7,
        "trailer_url": "https://www.youtube.com/embed/zSWdZVtXT7E",
        "release_date": "2014-11-05",
        "votes": "92.5K"
    },
    {
        "id": 155,
        "title": "The Dark Knight",
        "overview": "Batman raises the stakes in his war on crime. With the help of Lt. Jim Gordon and District Attorney Harvey Dent, Batman sets out to dismantle the remaining criminal organizations that plague the streets.",
        "poster_path": "https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg",
        "genre": "Action / Crime / Drama",
        "duration": "2h 32m",
        "rating": 9.0,
        "trailer_url": "https://www.youtube.com/embed/EXeTwQWrcwY",
        "release_date": "2008-07-18",
        "votes": "98.2K"
    },
    {
        "id": 76600,
        "title": "Avatar: The Way of Water",
        "overview": "Set more than a decade after the events of the first film, learn the story of the Sully family, the trouble that follows them, the lengths they go to keep each other safe, the battles they fight to stay alive, and the tragedies they endure.",
        "poster_path": "https://image.tmdb.org/t/p/w500/t6HIqrRAclMCA60NsSmeqe9RmNV.jpg",
        "genre": "Sci-Fi / Adventure / Action",
        "duration": "3h 12m",
        "rating": 8.0,
        "trailer_url": "https://www.youtube.com/embed/d9MyW72ELq0",
        "release_date": "2022-12-16",
        "votes": "51.0K"
    }
]


def get_db_path():
    """Resolve database path relative to project root."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cinematic_pulse.db')


def get_db_connection():
    conn = sqlite3.connect(get_db_path(), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')
    return conn


def parse_time_to_24h(time_str: str) -> str:
    """Converts 12-hour AM/PM string to HH:MM format."""
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


def fetch_now_playing_movies(api_key: str = None, region: str = "IN", page: int = 1):
    """
    Calls TMDb API /movie/now_playing endpoint for region India.
    Falls back gracefully to curated Indian releases if no API key is provided
    or if network/API limits are reached.
    """
    api_key = api_key or os.environ.get("TMDB_API_KEY")
    if not api_key:
        logger.warning("TMDB_API_KEY is not set. Using curated Indian theatrical release feed.")
        return CURATED_INDIAN_RELEASES

    url = f"{TMDB_API_BASE}/movie/now_playing"
    params = {
        "api_key": api_key,
        "region": region,
        "page": page,
        "language": "en-US"
    }

    try:
        response = requests.get(url, params=params, timeout=8)
        if response.status_code == 401:
            logger.error("Invalid TMDB_API_KEY provided. Using curated fallback feed.")
            return CURATED_INDIAN_RELEASES

        response.raise_for_status()
        data = response.json()
        raw_movies = data.get("results", [])
        logger.info(f"Retrieved {len(raw_movies)} now playing movies from TMDb for region {region}.")

        parsed_movies = []
        for m in raw_movies[:10]:  # Ingest top 10 now playing titles
            tmdb_id = m.get("id")
            title = m.get("title")
            overview = m.get("overview", "")
            poster_path = m.get("poster_path")
            poster_url = f"{TMDB_IMAGE_BASE}{poster_path}" if poster_path else "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500"
            rating = round(m.get("vote_average", 7.5), 1)
            release_date = m.get("release_date", date.today().isoformat())

            # Resolve genres
            genre_ids = m.get("genre_ids", [])
            genres_list = [TMDB_GENRES.get(gid, "Drama") for gid in genre_ids if gid in TMDB_GENRES]
            genre_str = " / ".join(genres_list[:3]) if genres_list else "Action / Drama"

            # Optional runtime & trailer detail queries
            duration = "2h 20m"
            trailer_url = "https://www.youtube.com/embed/Way9Dexny3w"
            try:
                # Runtime detail
                detail_res = requests.get(f"{TMDB_API_BASE}/movie/{tmdb_id}", params={"api_key": api_key}, timeout=5)
                if detail_res.ok:
                    runtime = detail_res.json().get("runtime")
                    if runtime and runtime > 0:
                        duration = f"{runtime // 60}h {runtime % 60:02d}m"

                # Video / Trailer detail
                videos_res = requests.get(f"{TMDB_API_BASE}/movie/{tmdb_id}/videos", params={"api_key": api_key}, timeout=5)
                if videos_res.ok:
                    videos = videos_res.json().get("results", [])
                    for v in videos:
                        if v.get("site") == "YouTube" and v.get("type") in ("Trailer", "Teaser"):
                            trailer_url = f"https://www.youtube.com/embed/{v.get('key')}"
                            break
            except Exception as e:
                logger.debug(f"Could not fetch full details for {title}: {e}")

            parsed_movies.append({
                "id": tmdb_id,
                "title": title,
                "overview": overview,
                "poster_path": poster_url,
                "genre": genre_str,
                "duration": duration,
                "rating": rating,
                "trailer_url": trailer_url,
                "release_date": release_date
            })

        return parsed_movies

    except requests.RequestException as e:
        logger.error(f"Error calling TMDb API: {e}. Falling back to curated catalog.")
        return CURATED_INDIAN_RELEASES


def generate_initial_showtimes_for_movie(conn, movie_id: int):
    """
    Generates realistic upcoming showtimes across active cinemas for a newly ingested movie.
    Covers today, tomorrow, and the day after tomorrow at prime screening times.
    """
    cinemas = conn.execute("SELECT cinema_id, cinema_name FROM cinemas LIMIT 4").fetchall()
    if not cinemas:
        return 0

    slots = [
        ("11:00 AM", "11:00", "Dolby Atmos", 320.0),
        ("02:30 PM", "14:30", "IMAX 3D", 420.0),
        ("06:15 PM", "18:15", "Laser 4K (Prime)", 380.0),
        ("09:30 PM", "21:30", "IMAX 3D", 450.0)
    ]

    today = date.today()
    showtimes_inserted = 0

    for day_offset in range(3):
        show_date_str = (today + timedelta(days=day_offset)).isoformat()
        for idx, cinema in enumerate(cinemas):
            # Select 2 distinct slots per cinema
            c_id = cinema['cinema_id'] if isinstance(cinema, sqlite3.Row) or isinstance(cinema, dict) else cinema[0]
            c_name = cinema['cinema_name'] if isinstance(cinema, sqlite3.Row) or isinstance(cinema, dict) else cinema[1]
            assigned_slots = [slots[(idx + day_offset) % len(slots)], slots[(idx + day_offset + 2) % len(slots)]]
            for s_time, s_time_24, screen, price in assigned_slots:
                conn.execute("""
                    INSERT INTO showtimes (
                        cinema_id, movie_id, theater_name, show_date, show_time, show_time_24, screen_type, price, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
                """, (c_id, movie_id, c_name, show_date_str, s_time, s_time_24, screen, price))
                showtimes_inserted += 1

    return showtimes_inserted


def sync_tmdb_catalog(api_key: str = None):
    """
    Syncs live TMDb releases into CineHub database:
    1. Fetches current in-theater titles (TMDb /movie/now_playing).
    2. Inserts new movies into `movies` table.
    3. Auto-creates initial active showtimes for newly added movies.
    4. Runs archive_expired_shows() to ensure database hygiene.
    """
    logger.info("Starting TMDb Movie Catalog Sync...")
    movies_data = fetch_now_playing_movies(api_key=api_key)
    conn = get_db_connection()

    new_movies_count = 0
    showtimes_created = 0

    try:
        for m in movies_data:
            tmdb_id = m.get("id")
            title = m.get("title")
            poster_url = m.get("poster_path")
            genre = m.get("genre", "Action / Drama")
            duration = m.get("duration", "2h 30m")
            rating = m.get("rating", 7.5)
            trailer_url = m.get("trailer_url")
            overview = m.get("overview", "")
            release_date = m.get("release_date")

            # Check if movie already exists by tmdb_id or title
            existing = conn.execute("""
                SELECT movie_id, status FROM movies
                WHERE (tmdb_id IS NOT NULL AND tmdb_id = ?) OR LOWER(title) = LOWER(?)
            """, (tmdb_id, title)).fetchone()

            if existing:
                # If existing movie was archived, reactivate it since it's now playing
                if existing['status'] != 'NOW_SHOWING':
                    conn.execute("UPDATE movies SET status = 'NOW_SHOWING' WHERE movie_id = ?", (existing['movie_id'],))
                    logger.info(f"Re-activated movie: {title} (ID {existing['movie_id']}) to NOW_SHOWING")
                continue

            # Insert new movie record
            cursor = conn.execute("""
                INSERT INTO movies (
                    title, poster_url, genre, duration, rating, trailer_url, description, status, tmdb_id, release_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'NOW_SHOWING', ?, ?)
            """, (title, poster_url, genre, duration, rating, trailer_url, overview, tmdb_id, release_date))
            
            new_movie_id = cursor.lastrowid
            new_movies_count += 1
            logger.info(f"Ingested new movie: '{title}' (Movie ID: {new_movie_id}, TMDb ID: {tmdb_id})")

            # Generate initial showtimes
            created_shows = generate_initial_showtimes_for_movie(conn, new_movie_id)
            showtimes_created += created_shows

        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error during movie catalog sync: {e}", exc_info=True)
        conn.close()
        return {"status": "error", "error": str(e)}

    # Run automated cleanup after ingestion
    cleanup_result = archive_expired_shows(conn=conn)
    conn.close()

    result = {
        "status": "success",
        "new_movies_added": new_movies_count,
        "showtimes_created": showtimes_created,
        "expired_showtimes": cleanup_result.get("expired_showtimes", 0),
        "archived_movies": cleanup_result.get("archived_movies", 0),
        "timestamp": datetime.now().isoformat()
    }
    logger.info(f"TMDb Sync Complete: {result}")
    return result


def archive_expired_shows(conn=None):
    """
    Automated Lifecycle & Cleanup:
    1. Sets any showtime where datetime(show_date || ' ' || show_time_24) < datetime('now', 'localtime') to 'EXPIRED'.
    2. If a movie has 0 upcoming active showtimes, set its status to 'ARCHIVED'
       so it disappears from the live catalog.
    """
    close_after = False
    if conn is None:
        conn = get_db_connection()
        close_after = True

    try:
        # Step 1: Expire past showtimes
        # SQLite's datetime('now', 'localtime') evaluates to current local date & time
        cur1 = conn.execute("""
            UPDATE showtimes
            SET status = 'EXPIRED'
            WHERE status = 'ACTIVE'
              AND datetime(show_date || ' ' || COALESCE(show_time_24, '23:59')) < datetime('now', 'localtime')
        """)
        expired_count = cur1.rowcount
        if expired_count > 0:
            logger.info(f"Archived {expired_count} expired showtimes.")

        # Step 2: Archive movies that have 0 upcoming active showtimes
        cur2 = conn.execute("""
            UPDATE movies
            SET status = 'ARCHIVED'
            WHERE status = 'NOW_SHOWING'
              AND movie_id NOT IN (
                  SELECT DISTINCT movie_id
                  FROM showtimes
                  WHERE status = 'ACTIVE'
                    AND datetime(show_date || ' ' || COALESCE(show_time_24, '23:59')) >= datetime('now', 'localtime')
              )
        """)
        archived_movies_count = cur2.rowcount
        if archived_movies_count > 0:
            logger.info(f"Archived {archived_movies_count} movies with no remaining active shows.")

        conn.commit()
        return {
            "expired_showtimes": expired_count,
            "archived_movies": archived_movies_count
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"Error during archive_expired_shows: {e}", exc_info=True)
        return {"error": str(e), "expired_showtimes": 0, "archived_movies": 0}
    finally:
        if close_after:
            conn.close()


if __name__ == '__main__':
    print("Testing TMDb Movie Sync & Cleanup Service...")
    res = sync_tmdb_catalog()
    print("Sync Result:", res)
