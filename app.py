from flask import Flask, jsonify, request, render_template
from flask_cors import CORS, cross_origin
import sqlite3
import json
from datetime import datetime, timedelta, timezone

LOCK_TTL_MINUTES = 7  # How long a seat lock is held before it auto-expires

app = Flask(__name__)
CORS(app)

def get_db_connection():
    conn = sqlite3.connect('cinematic_pulse.db', detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    # Enforce foreign-key constraints and enable WAL for better concurrency
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')
    return conn


def utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def _parse_booked_seats(seats_booked_str: str) -> list[str]:
    """
    Normalise a seats_booked string (e.g. "A1, A2" or '["A1","A2"]')
    into a clean list of uppercase seat labels.
    """
    if not seats_booked_str:
        return []
    seats_booked_str = seats_booked_str.strip()
    if seats_booked_str.startswith('['):
        try:
            return [s.strip().upper() for s in json.loads(seats_booked_str)]
        except (json.JSONDecodeError, ValueError):
            pass
    return [s.strip().upper() for s in seats_booked_str.split(',') if s.strip()]

def init_all_dbs():
    conn = get_db_connection()

    # Self-healing migration for existing DBs created by older scripts
    movies_cols = [r[1] for r in conn.execute('PRAGMA table_info(movies)').fetchall()]
    if movies_cols and 'duration' not in movies_cols:
        conn.execute('ALTER TABLE movies ADD COLUMN duration TEXT DEFAULT "2h 30m"')
    
    showtimes_cols = [r[1] for r in conn.execute('PRAGMA table_info(showtimes)').fetchall()]
    if showtimes_cols and 'cinema_id' not in showtimes_cols:
        conn.execute('ALTER TABLE showtimes ADD COLUMN cinema_id INTEGER')
    if showtimes_cols and 'screen_type' not in showtimes_cols:
        conn.execute('ALTER TABLE showtimes ADD COLUMN screen_type TEXT DEFAULT "Standard 2D"')

    # 1. Movies Table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            movie_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            poster_url TEXT,
            genre TEXT,
            duration TEXT,
            rating REAL,
            trailer_url TEXT
        )
    ''')
    if conn.execute('SELECT COUNT(*) FROM movies').fetchone()[0] == 0:
        conn.executemany('''
            INSERT INTO movies (title, poster_url, genre, duration, rating, trailer_url) VALUES (?, ?, ?, ?, ?, ?)
        ''', [
            ('Dune: Part Two', 'https://images.unsplash.com/photo-1534447677768-be436bb09401?w=500', 'Sci-Fi / Adventure', '2h 46m', 8.9, 'https://www.youtube.com/embed/Way9Dexny3w'),
            ('Interstellar', 'https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?w=500', 'Sci-Fi / Drama', '2h 49m', 8.7, 'https://www.youtube.com/embed/zSWdZVtXT7E'),
            ('Oppenheimer', 'https://images.unsplash.com/photo-1578849278619-e73505e9610f?w=500', 'Biography / Drama', '3h 00m', 8.9, 'https://www.youtube.com/embed/uYPbbksJxIg'),
            ('The Dark Knight', 'https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=500', 'Action / Crime', '2h 32m', 9.0, 'https://www.youtube.com/embed/EXeTwQWrcwY')
        ])

    # 2. Food Items Table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS food_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            image_url TEXT
        )
    ''')
    if conn.execute('SELECT COUNT(*) FROM food_items').fetchone()[0] == 0:
        conn.executemany('''
            INSERT INTO food_items (name, category, price, image_url) VALUES (?, ?, ?, ?)
        ''', [
            ('Large Butter Popcorn', 'Popcorn', 250, 'https://images.unsplash.com/photo-1578849278619-e73505e9610f?w=400'),
            ('Chilled Coca-Cola (Large)', 'Drinks', 150, 'https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=400'),
            ('Cheese Nachos Supreme', 'Snacks', 220, 'https://images.unsplash.com/photo-1582169226686-4f4c2e5b88c3?w=400'),
            ('Chocolate Brownie Sundae', 'Desserts', 280, 'https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=400')
        ])

    # 3. Cinemas Table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS cinemas (
            cinema_id INTEGER PRIMARY KEY AUTOINCREMENT,
            cinema_name TEXT NOT NULL,
            city TEXT NOT NULL,
            area TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            address TEXT NOT NULL,
            rating REAL NOT NULL,
            distance_km REAL NOT NULL,
            formats TEXT NOT NULL,
            facilities TEXT NOT NULL,
            premium_seating INTEGER DEFAULT 1,
            parking INTEGER DEFAULT 1,
            starting_price REAL NOT NULL,
            badge TEXT,
            screens_count INTEGER NOT NULL,
            image_url TEXT NOT NULL
        )
    ''')
    if conn.execute('SELECT COUNT(*) FROM cinemas').fetchone()[0] == 0:
        conn.executemany('''
            INSERT INTO cinemas (cinema_name, city, area, latitude, longitude, address, rating, distance_km, formats, facilities, premium_seating, parking, starting_price, badge, screens_count, image_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            ('CineMax IMAX Luxe', 'Mumbai', 'Lower Parel', 18.9950, 72.8258, 'High Street Phoenix, Senapati Bapat Marg, Lower Parel, Mumbai', 4.9, 1.8, '["IMAX", "4DX", "Dolby Atmos", "3D"]', '["Premium Seating", "Recliner Seats", "Dolby Atmos", "Parking", "Food Court", "Wheelchair Accessible"]', 1, 1, 280, '✦ PREMIUM EXPERIENCE', 6, 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=700'),
            ('PVR ICON Gold', 'Mumbai', 'Andheri West', 19.1363, 72.8311, 'Infinity Mall, New Link Rd, Andheri West, Mumbai', 4.8, 3.4, '["Dolby Atmos", "4DX", "3D", "2D"]', '["Recliner Seats", "Dolby Atmos", "Parking", "Food Court", "Wheelchair Accessible"]', 1, 1, 320, '🏆 TOP RATED', 8, 'https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=700'),
            ('INOX Megaplex Laser', 'Mumbai', 'Malad West', 19.1765, 72.8362, 'Inorbit Mall, Link Rd, Malad West, Mumbai', 4.6, 5.2, '["IMAX", "Dolby Atmos", "3D", "2D"]', '["Premium Seating", "Parking", "Food Court", "Wheelchair Accessible"]', 1, 1, 220, '🔥 MOST POPULAR', 11, 'https://images.unsplash.com/photo-1595769816263-9b910be24d5f?w=700'),
            ('Cinepolis VIP Grand', 'Mumbai', 'Thane West', 19.2183, 72.9781, 'Viviana Mall, Eastern Express Hwy, Thane West, Mumbai', 4.7, 7.8, '["Dolby Atmos", "4DX", "3D"]', '["Premium Seating", "Recliner Seats", "Parking", "Food Court"]', 1, 1, 260, '✦ LUXE COMFORT', 7, 'https://images.unsplash.com/photo-1524712245354-2c4e5e7121c0?w=700'),
            ('Carnival Cinemas Metro', 'Mumbai', 'Marine Lines', 18.9416, 72.8277, 'Dhobi Talao, Marine Lines, Mumbai', 4.3, 8.5, '["2D", "3D", "Dolby Atmos"]', '["Food Court", "Wheelchair Accessible"]', 0, 0, 150, None, 4, 'https://images.unsplash.com/photo-1507676184212-d03ab07a01bf?w=700')
        ])

    # 4. Showtimes Table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS showtimes (
            showtime_id INTEGER PRIMARY KEY AUTOINCREMENT,
            cinema_id INTEGER,
            movie_id INTEGER,
            theater_name TEXT,
            show_time TEXT,
            screen_type TEXT,
            price REAL
        )
    ''')
    if conn.execute('SELECT COUNT(*) FROM showtimes').fetchone()[0] == 0:
        conn.executemany('''
            INSERT INTO showtimes (cinema_id, movie_id, theater_name, show_time, screen_type, price) VALUES (?, ?, ?, ?, ?, ?)
        ''', [
            (1, 1, 'CineMax IMAX Luxe', '10:00 AM', 'IMAX 3D', 350),
            (1, 1, 'CineMax IMAX Luxe', '01:30 PM', 'IMAX 3D', 400),
            (1, 1, 'CineMax IMAX Luxe', '07:00 PM', 'IMAX 3D (Prime)', 450),
            (1, 2, 'CineMax IMAX Luxe', '09:45 PM', 'IMAX 70mm', 420),
            (2, 1, 'PVR ICON Gold', '11:15 AM', 'Dolby Atmos', 320),
            (2, 1, 'PVR ICON Gold', '04:30 PM', '4DX 3D', 420),
            (2, 3, 'PVR ICON Gold', '08:15 PM', 'Dolby Atmos', 380),
            (3, 1, 'INOX Megaplex Laser', '12:00 PM', 'IMAX 3D', 280),
            (3, 4, 'INOX Megaplex Laser', '06:30 PM', 'Laser 4K', 250),
            (4, 1, 'Cinepolis VIP Grand', '02:00 PM', '4DX', 350),
            (5, 1, 'Carnival Cinemas Metro', '03:00 PM', 'Standard 2D', 180)
        ])

    # 5. Bookings Table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER,
            showtime_id INTEGER,
            seats_booked TEXT,
            total_amount REAL,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 6. Seat Locks Table — temporary holds during checkout (TTL: LOCK_TTL_MINUTES)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS seat_locks (
            lock_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            showtime_id  INTEGER NOT NULL,
            seat_number  TEXT    NOT NULL,
            user_id      INTEGER NOT NULL,
            expires_at   TIMESTAMP NOT NULL,
            UNIQUE (showtime_id, seat_number)
        )
    ''')
    # Index to make expiry sweeps fast
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_seat_locks_showtime
        ON seat_locks (showtime_id, expires_at)
    ''')
    conn.commit()
    conn.close()

init_all_dbs()

# ----------------- PAGE ROUTES -----------------
@app.route('/')
def home(): return render_template('index.html')

@app.route('/cinema-explorer')
@app.route('/cinemas')
def cinema_explorer_page(): return render_template('cinema_explorer.html')

@app.route('/pick-showtime')
def pick_showtime(): return render_template('pick_showtime.html')

@app.route('/select-seats')
def select_seats(): return render_template('select_seats.html')

@app.route('/food-snacks')
def food_snacks_page(): return render_template('food_snacks.html')

@app.route('/booking-history')
def booking_history(): return render_template('booking_history.html')

@app.route('/digital-ticket')
def digital_ticket(): return render_template('digital_ticket.html')

@app.route('/rewards')
def rewards_page(): return render_template('rewards.html')

@app.route('/admin')
def admin_page(): return render_template('admin_dashboard.html')

@app.route('/search')
def search():
    query = request.args.get('q', '').lower()
    conn = get_db_connection()
    movies = conn.execute("SELECT * FROM movies WHERE LOWER(title) LIKE ? OR LOWER(genre) LIKE ?", 
                           ('%'+query+'%', '%'+query+'%')).fetchall()
    conn.close()
    return render_template('search_results.html', movies=[dict(m) for m in movies], query=query)

# ----------------- API ROUTES -----------------
@app.route('/api/cinemas', methods=['GET'])
@cross_origin()
def get_cinemas():
    conn = get_db_connection()
    cinemas = conn.execute('SELECT * FROM cinemas').fetchall()
    result = []
    for c in cinemas:
        item = dict(c)
        try:
            item['formats'] = json.loads(item['formats'])
            item['facilities'] = json.loads(item['facilities'])
        except Exception:
            item['formats'] = ['2D', '3D']
            item['facilities'] = ['Standard']
        result.append(item)
    conn.close()
    return jsonify(result)

@app.route('/api/cinemas/<int:cinema_id>/showtimes', methods=['GET'])
@cross_origin()
def get_cinema_showtimes(cinema_id):
    conn = get_db_connection()
    cinema = conn.execute('SELECT * FROM cinemas WHERE cinema_id = ?', (cinema_id,)).fetchone()
    if not cinema:
        conn.close()
        return jsonify({'error': 'Cinema not found'}), 404

    shows = conn.execute('''
        SELECT s.showtime_id, s.show_time, s.screen_type, s.price,
               m.movie_id, m.title as movie_title, m.poster_url, m.genre, m.duration, m.rating
        FROM showtimes s
        JOIN movies m ON s.movie_id = m.movie_id
        WHERE s.cinema_id = ?
        ORDER BY m.title, s.show_time
    ''', (cinema_id,)).fetchall()

    grouped_movies = {}
    for s in shows:
        mid = s['movie_id']
        if mid not in grouped_movies:
            grouped_movies[mid] = {
                'movie_id': mid,
                'title': s['movie_title'],
                'poster_url': s['poster_url'],
                'genre': s['genre'],
                'duration': s['duration'],
                'rating': s['rating'],
                'showtimes': []
            }
        grouped_movies[mid]['showtimes'].append({
            'showtime_id': s['showtime_id'],
            'time': s['show_time'],
            'type': s['screen_type'],
            'price': s['price']
        })

    cinema_data = dict(cinema)
    cinema_data['formats'] = json.loads(cinema_data['formats'])
    cinema_data['facilities'] = json.loads(cinema_data['facilities'])
    cinema_data['movies'] = list(grouped_movies.values())
    conn.close()
    return jsonify(cinema_data)

@app.route('/api/movies', methods=['GET'])
@cross_origin()
def get_movies():
    conn = get_db_connection()
    movies = conn.execute('SELECT * FROM movies').fetchall()
    conn.close()
    return jsonify([dict(m) for m in movies])

@app.route('/api/movies/<int:movie_id>', methods=['GET'])
@cross_origin()
def get_movie_detail(movie_id):
    conn = get_db_connection()
    movie = conn.execute('SELECT * FROM movies WHERE movie_id = ?', (movie_id,)).fetchone()
    conn.close()
    if not movie: return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(movie))

@app.route('/api/movies/<int:movie_id>/showtimes', methods=['GET'])
@cross_origin()
def get_movie_showtimes(movie_id):
    conn = get_db_connection()
    showtimes = conn.execute('SELECT * FROM showtimes WHERE movie_id = ?', (movie_id,)).fetchall()
    conn.close()
    if not showtimes:
        return jsonify([
            {'showtime_id': 1, 'theater_name': 'CineMax IMAX Luxe', 'show_time': '10:00 AM', 'price': 350},
            {'showtime_id': 2, 'theater_name': 'PVR ICON Gold', 'show_time': '01:30 PM', 'price': 320},
            {'showtime_id': 3, 'theater_name': 'INOX Megaplex Laser', 'show_time': '07:00 PM', 'price': 450}
        ])
    return jsonify([dict(s) for s in showtimes])

@app.route('/api/food-items', methods=['GET'])
@cross_origin()
def get_food_items():
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM food_items').fetchall()
    conn.close()
    return jsonify([dict(i) for i in items])

@app.route('/api/showtimes/<int:showtime_id>/seats', methods=['GET'])
@cross_origin()
def get_seat_availability(showtime_id):
    """
    Returns two lists for a given showtime:
      - booked_seats  : permanently confirmed seats (from bookings table)
      - locked_seats  : seats temporarily held by other users (not yet expired)

    The frontend uses this to grey-out unavailable seats before the user picks.
    """
    conn = get_db_connection()
    now = utc_now()

    # --- 1. Confirmed seats (all bookings for this showtime, status = Confirmed) ---
    rows = conn.execute(
        "SELECT seats_booked FROM bookings WHERE showtime_id = ? AND status = 'Confirmed'",
        (showtime_id,)
    ).fetchall()

    booked_seats: set[str] = set()
    for row in rows:
        booked_seats.update(_parse_booked_seats(row['seats_booked']))

    # --- 2. Active locks held by OTHER users (expired locks are silently ignored) ---
    user_id = request.args.get('user_id', type=int)
    lock_query = '''
        SELECT seat_number FROM seat_locks
        WHERE showtime_id = ?
          AND expires_at > ?
    '''
    lock_params: tuple = (showtime_id, now.isoformat())

    if user_id is not None:
        # Exclude the requesting user's own locks so they can still see their selection
        lock_query += ' AND user_id != ?'
        lock_params = (showtime_id, now.isoformat(), user_id)

    lock_rows = conn.execute(lock_query, lock_params).fetchall()
    locked_seats = [r['seat_number'] for r in lock_rows]

    conn.close()

    return jsonify({
        'showtime_id': showtime_id,
        'booked_seats': sorted(booked_seats),
        'locked_seats': sorted(locked_seats),
    })


@app.route('/api/seats/lock', methods=['POST'])
@cross_origin()
def lock_seats():
    """
    Temporarily lock seats for a user during checkout.

    Request JSON:
        {
          "showtime_id": 3,
          "seats":       ["A1", "B4"],
          "user_id":     42
        }

    Rules:
      - Rejects with 409 if any seat is already CONFIRMED in bookings.
      - Rejects with 409 if any seat has an active lock held by a DIFFERENT user.
      - If the requesting user already holds a lock on a seat, the lock is refreshed.
      - Lock TTL is LOCK_TTL_MINUTES (default 7 minutes) from now.

    Response (200):
        { "locked": ["A1", "B4"], "expires_at": "2026-11-06T18:08:31+00:00" }
    """
    data = request.get_json(silent=True) or {}

    # --- Input validation ---
    showtime_id = data.get('showtime_id')
    seats_raw   = data.get('seats', [])
    user_id     = data.get('user_id')

    if not showtime_id or not seats_raw or user_id is None:
        return jsonify({'error': 'showtime_id, seats (array), and user_id are required'}), 400

    if not isinstance(seats_raw, list) or len(seats_raw) == 0:
        return jsonify({'error': 'seats must be a non-empty array'}), 400

    requested_seats = [s.strip().upper() for s in seats_raw]
    now        = utc_now()
    expires_at = now + timedelta(minutes=LOCK_TTL_MINUTES)

    conn = get_db_connection()
    try:
        # Collect booked seats for this showtime
        rows = conn.execute(
            "SELECT seats_booked FROM bookings WHERE showtime_id = ? AND status = 'Confirmed'",
            (showtime_id,)
        ).fetchall()
        booked_seats: set[str] = set()
        for row in rows:
            booked_seats.update(_parse_booked_seats(row['seats_booked']))

        # Collect active locks held by OTHER users
        lock_rows = conn.execute('''
            SELECT seat_number FROM seat_locks
            WHERE showtime_id = ?
              AND user_id    != ?
              AND expires_at  > ?
        ''', (showtime_id, user_id, now.isoformat())).fetchall()
        foreign_locks: set[str] = {r['seat_number'] for r in lock_rows}

        # Find seats that are unavailable
        booked_conflicts = [s for s in requested_seats if s in booked_seats]
        locked_conflicts  = [s for s in requested_seats if s in foreign_locks]

        if booked_conflicts or locked_conflicts:
            conn.close()
            return jsonify({
                'error':           'One or more seats are unavailable',
                'booked_conflicts': booked_conflicts,
                'locked_conflicts': locked_conflicts,
            }), 409

        # Upsert locks — refresh if the same user already holds them
        for seat in requested_seats:
            conn.execute('''
                INSERT INTO seat_locks (showtime_id, seat_number, user_id, expires_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(showtime_id, seat_number)
                DO UPDATE SET user_id    = excluded.user_id,
                              expires_at = excluded.expires_at
            ''', (showtime_id, seat, user_id, expires_at.isoformat()))

        conn.commit()
    except Exception as exc:
        conn.rollback()
        conn.close()
        return jsonify({'error': 'Failed to acquire seat locks', 'detail': str(exc)}), 500

    conn.close()
    return jsonify({
        'locked':     requested_seats,
        'expires_at': expires_at.isoformat(),
        'lock_ttl_minutes': LOCK_TTL_MINUTES,
    })


@app.route('/api/bookings', methods=['POST'])
@cross_origin()
def create_booking():
    """
    Confirm a seat booking.

    Request JSON:
        {
          "movie_id":     1,
          "showtime_id":  3,
          "seats":        ["A1", "B4"],
          "user_id":      42,
          "total_amount": 700
        }

    Validation (inside a single SQLite transaction):
      1. Checks every requested seat is NOT already confirmed in bookings.
      2. Checks every seat is either:
           a) locked by this user (active lock), OR
           b) completely free (no lock at all / lock already expired).
      3. Inserts the booking record.
      4. Purges the user's seat locks for this showtime.

    Returns 409 Conflict if any seat is taken by another booking or another user's lock.
    """
    data = request.get_json(silent=True) or {}

    showtime_id  = data.get('showtime_id', 1)
    movie_id     = data.get('movie_id', 1)
    user_id      = data.get('user_id', 1)
    total_amount = data.get('total_amount', 630)

    # Normalise seats — accept both list and legacy comma-string
    raw_seats = data.get('seats', 'A1, A2')
    if isinstance(raw_seats, list):
        requested_seats = [s.strip().upper() for s in raw_seats]
    else:
        requested_seats = _parse_booked_seats(str(raw_seats))

    if not requested_seats:
        return jsonify({'error': 'No seats provided'}), 400

    seats_str = ', '.join(requested_seats)
    now = utc_now()

    conn = get_db_connection()
    try:
        # --- BEGIN explicit transaction ---
        conn.execute('BEGIN EXCLUSIVE')

        # 1. Collect confirmed seats for this showtime
        rows = conn.execute(
            "SELECT seats_booked FROM bookings WHERE showtime_id = ? AND status = 'Confirmed'",
            (showtime_id,)
        ).fetchall()
        booked_seats: set[str] = set()
        for row in rows:
            booked_seats.update(_parse_booked_seats(row['seats_booked']))

        booked_conflicts = [s for s in requested_seats if s in booked_seats]
        if booked_conflicts:
            conn.rollback()
            conn.close()
            return jsonify({
                'error':   'Seats already booked by another user',
                'conflicts': booked_conflicts,
            }), 409

        # 2. Validate locks — each seat must be either unlocked OR locked by this user
        lock_rows = conn.execute('''
            SELECT seat_number, user_id FROM seat_locks
            WHERE showtime_id = ?
              AND expires_at  > ?
        ''', (showtime_id, now.isoformat())).fetchall()

        # Map: seat -> owner user_id  (only active locks)
        active_locks: dict[str, int] = {r['seat_number']: r['user_id'] for r in lock_rows}

        foreign_lock_conflicts = [
            s for s in requested_seats
            if s in active_locks and active_locks[s] != user_id
        ]
        if foreign_lock_conflicts:
            conn.rollback()
            conn.close()
            return jsonify({
                'error':     'Seats are temporarily held by another user',
                'conflicts': foreign_lock_conflicts,
            }), 409

        # 3. Insert confirmed booking
        cursor = conn.execute('''
            INSERT INTO bookings (movie_id, showtime_id, seats_booked, total_amount, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (movie_id, showtime_id, seats_str, total_amount, 'Confirmed'))
        booking_id = cursor.lastrowid

        # 4. Release this user's seat locks for the showtime (cleanup)
        conn.execute('''
            DELETE FROM seat_locks
            WHERE showtime_id = ? AND user_id = ?
        ''', (showtime_id, user_id))

        conn.commit()
    except Exception as exc:
        conn.rollback()
        conn.close()
        return jsonify({'error': 'Booking failed due to a server error', 'detail': str(exc)}), 500

    conn.close()
    return jsonify({
        'success':    True,
        'booking_id': booking_id,
        'seats':      requested_seats,
        'status':     'Confirmed',
    }), 201

@app.route('/api/users/<int:user_id>/bookings', methods=['GET'])
@cross_origin()
def get_user_bookings(user_id):
    conn = get_db_connection()
    bookings = conn.execute("""
        SELECT b.booking_id, b.seats_booked, b.total_amount, b.status, b.created_at,
               m.title as movie_title, m.poster_url, m.genre,
               COALESCE(s.theater_name, 'CineHub IMAX') as theater_name, 
               COALESCE(s.show_time, '07:00 PM') as show_time
        FROM bookings b
        LEFT JOIN movies m ON b.movie_id = m.movie_id
        LEFT JOIN showtimes s ON b.showtime_id = s.showtime_id
        ORDER BY b.booking_id DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(b) for b in bookings])

@app.route('/api/users/<int:user_id>/rewards', methods=['GET'])
@cross_origin()
def get_user_rewards(user_id):
    return jsonify({'points': 1850, 'tier_name': 'Gold', 'multiplier': 1.25})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
