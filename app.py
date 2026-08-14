from flask import Flask, jsonify, request, render_template
from flask_cors import CORS, cross_origin
import sqlite3
import json

app = Flask(__name__)
CORS(app)

def get_db_connection():
    conn = sqlite3.connect('cinematic_pulse.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_all_dbs():
    conn = get_db_connection()
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

@app.route('/api/bookings', methods=['POST'])
@cross_origin()
def create_booking():
    data = request.get_json() or {}
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO bookings (movie_id, showtime_id, seats_booked, total_amount, status)
        VALUES (?, ?, ?, ?, ?)
    """, (
        data.get('movie_id', 1),
        data.get('showtime_id', 1),
        str(data.get('seats', 'A1, A2')),
        data.get('total_amount', 630),
        'Confirmed'
    ))
    conn.commit()
    booking_id = cursor.lastrowid
    conn.close()
    return jsonify({'success': True, 'booking_id': booking_id})

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
