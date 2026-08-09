from flask import Flask, jsonify, request, render_template, session
from flask_cors import CORS
import sqlite3
import datetime
import re
import uuid

app = Flask(__name__)
app.secret_key = 'cinehub_super_secret_key'
CORS(app)

def get_db_connection():
    conn = sqlite3.connect('cinematic_pulse.db')
    conn.row_factory = sqlite3.Row
    return conn

def parse_youtube_url(url):
    if not url:
        return ""
    if "embed/" in url:
        return url
    video_id = ""
    if "youtu.be/" in url:
        video_id = url.split("youtu.be/")[1].split("?")[0]
    elif "watch?v=" in url:
        match = re.search(r"v=([a-zA-Z0-9_-]+)", url)
        if match:
            video_id = match.group(1)
    if video_id:
        return f"https://www.youtube.com/embed/{video_id}?autoplay=1&mute=1&loop=1&controls=0&showinfo=0&autohide=1&modestbranding=1&playlist={video_id}"
    return url

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        reward_points INTEGER DEFAULT 100
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS movies (
        movie_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        genre TEXT,
        duration_mins INTEGER,
        rating REAL,
        description TEXT,
        poster_url TEXT,
        trailer_url TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS showtimes (
        showtime_id INTEGER PRIMARY KEY AUTOINCREMENT,
        movie_id INTEGER,
        theater_name TEXT,
        show_time TEXT,
        price REAL
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS bookings (
        booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        movie_id INTEGER,
        showtime_id INTEGER,
        seats_booked TEXT,
        total_amount REAL,
        group_code TEXT,
        status TEXT DEFAULT 'CONFIRMED',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS wishlist (
        wishlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        movie_id INTEGER,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, movie_id)
    )''')

    cursor.execute("SELECT COUNT(*) FROM movies")
    if cursor.fetchone()[0] == 0:
        sample_movies = [
            ("Dune: Part Two", "Sci-Fi / Action", 166, 8.8, 
             "Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family.", 
             "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1200&auto=format&fit=crop&q=80", 
             "https://www.youtube.com/watch?v=Way9Dexny3w"),
            
            ("Interstellar", "Sci-Fi / Adventure", 169, 8.7, 
             "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival.", 
             "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&auto=format&fit=crop&q=80", 
             "https://www.youtube.com/watch?v=zSWdZVtXT7E"),

            ("Spider-Man: Across the Spider-Verse", "Action / Animation", 140, 8.7, 
             "Miles Morales catapults across the Multiverse, where he encounters a team of Spider-People.", 
             "https://images.unsplash.com/photo-1635805737707-575885ab0820?w=1200&auto=format&fit=crop&q=80", 
             "https://www.youtube.com/watch?v=cqGjhVJWtEg")
        ]
        cursor.executemany("INSERT INTO movies (title, genre, duration_mins, rating, description, poster_url, trailer_url) VALUES (?, ?, ?, ?, ?, ?, ?)", sample_movies)
        conn.commit()

    cursor.execute("SELECT movie_id FROM movies")
    movies = cursor.fetchall()
    for m in movies:
        mid = m['movie_id']
        st = cursor.execute("SELECT COUNT(*) FROM showtimes WHERE movie_id = ?", (mid,)).fetchone()[0]
        if st == 0:
            cursor.execute("INSERT INTO showtimes (movie_id, theater_name, show_time, price) VALUES (?, 'CineHub IMAX, Mumbai', '07:00 PM', 350)", (mid,))

    cursor.execute("INSERT OR IGNORE INTO users (user_id, full_name, email, password) VALUES (1, 'John Doe', 'john@gmail.com', '123456')")
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/search')
def search_page():
    return render_template('search_results.html')

@app.route('/pick-showtime')
def pick_showtime():
    return render_template('pick_showtime.html')

@app.route('/select-seats')
def select_seats():
    return render_template('select_seats.html')

@app.route('/booking-history')
def booking_history():
    return render_template('booking_history.html')

@app.route('/digital-ticket')
def digital_ticket():
    return render_template('digital_ticket.html')

@app.route('/api/featured-movies', methods=['GET'])
def get_featured_movies():
    conn = get_db_connection()
    movies = conn.execute("SELECT * FROM movies ORDER BY rating DESC LIMIT 4").fetchall()
    conn.close()
    return jsonify([dict(m) for m in movies])

@app.route('/api/recommendations/<path:user_id>', methods=['GET'])
def get_recommendations(user_id):
    conn = get_db_connection()
    all_movies = [dict(m) for m in conn.execute("SELECT * FROM movies").fetchall()]
    conn.close()
    
    recs = []
    for m in all_movies:
        m['trailer_url'] = parse_youtube_url(m['trailer_url'])
        recs.append({
            **m,
            'match_percentage': 96,
            'why_recommended': f"Matches your interest in {m['genre'].split('/')[0]}"
        })

    return jsonify({
        'last_watched_title': all_movies[0]['title'] if all_movies else "Dune: Part Two",
        'recommendations': recs
    })

@app.route('/api/movies', methods=['GET'])
def get_movies():
    conn = get_db_connection()
    movies = conn.execute('SELECT * FROM movies').fetchall()
    conn.close()
    return jsonify([dict(m) for m in movies])

@app.route('/api/movies/<int:movie_id>', methods=['GET'])
def get_movie_detail(movie_id):
    conn = get_db_connection()
    movie = conn.execute('SELECT * FROM movies WHERE movie_id = ?', (movie_id,)).fetchone()
    conn.close()
    if not movie:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(movie))

@app.route('/api/movies/<int:movie_id>/showtimes', methods=['GET'])
def get_showtimes(movie_id):
    conn = get_db_connection()
    showtimes = conn.execute('SELECT * FROM showtimes WHERE movie_id = ?', (movie_id,)).fetchall()
    conn.close()
    return jsonify([dict(st) for st in showtimes])

@app.route('/api/wishlist/toggle', methods=['POST'])
def toggle_wishlist():
    return jsonify({'status': 'success'}), 200

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    try:
        data = request.get_json() or {}
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO bookings (user_id, movie_id, showtime_id, seats_booked, total_amount, group_code, status) 
                          VALUES (?, ?, ?, ?, ?, ?, 'CONFIRMED')''',
                       (data.get('user_id', 1), data.get('movie_id', 1), data.get('showtime_id', 1), 
                        ",".join(str(s) for s in data.get('seats', [])), data.get('total_amount', 0), data.get('group_code', '')))
        booking_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return jsonify({'booking_id': booking_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/users/<path:user_identifier>/bookings', methods=['GET'])
def get_user_bookings(user_identifier):
    conn = get_db_connection()
    query = """
        SELECT b.booking_id, b.seats_booked, b.total_amount, b.status, b.created_at,
               m.title as movie_title, m.poster_url, m.genre,
               COALESCE(s.theater_name, 'CineHub IMAX, Mumbai') as theater_name, 
               COALESCE(s.show_time, '07:00 PM') as show_time, 
               'CP-' || b.booking_id as transaction_ref
        FROM bookings b
        LEFT JOIN movies m ON b.movie_id = m.movie_id
        LEFT JOIN showtimes s ON b.showtime_id = s.showtime_id
        ORDER BY b.booking_id DESC
    """
    bookings = conn.execute(query).fetchall()
    conn.close()
    return jsonify([dict(b) for b in bookings]), 200

@app.route('/api/bookings/<int:booking_id>/cancel', methods=['POST'])
def cancel_booking(booking_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE bookings SET status = 'CANCELLED' WHERE booking_id = ?", (booking_id,))
    conn.commit()
    conn.close()
    return jsonify({'booking_id': booking_id}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
