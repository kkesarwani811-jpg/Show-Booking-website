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

# --- CENTRALIZED REWARD SERVICE & TIER CONFIGURATION ---
TIER_THRESHOLDS = {
    'BRONZE': {'min': 0, 'max': 499, 'multiplier': 1.0, 'name': 'Bronze', 'color': '#b45309'},
    'SILVER': {'min': 500, 'max': 1499, 'multiplier': 1.1, 'name': 'Silver', 'color': '#94a3b8'},
    'GOLD': {'min': 1500, 'max': 2999, 'multiplier': 1.25, 'name': 'Gold', 'color': '#eab308'},
    'PLATINUM': {'min': 3000, 'max': 999999, 'multiplier': 1.5, 'name': 'Platinum', 'color': '#38bdf8'}
}

def get_user_tier(points):
    if points >= 3000:
        return 'PLATINUM'
    elif points >= 1500:
        return 'GOLD'
    elif points >= 500:
        return 'SILVER'
    return 'BRONZE'

def award_points(user_id, base_points, reason, reference_type=None, reference_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get user current points & tier multiplier
    user = cursor.execute("SELECT reward_points FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return
    
    current_pts = user['reward_points'] or 0
    tier_key = get_user_tier(current_pts)
    multiplier = TIER_THRESHOLDS[tier_key]['multiplier']
    
    final_points = int(round(base_points * multiplier))
    new_total = current_pts + final_points

    # Update user points balance
    cursor.execute("UPDATE users SET reward_points = ? WHERE user_id = ?", (new_total, user_id))

    # Log in ledger transaction
    cursor.execute("""
        INSERT INTO reward_transactions (user_id, points, transaction_type, reason, reference_type, reference_id)
        VALUES (?, ?, 'EARN', ?, ?, ?)
    """, (user_id, final_points, reason, reference_type, reference_id))

    conn.commit()
    conn.close()
    return final_points

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        reward_points INTEGER DEFAULT 150,
        referral_code TEXT,
        birthday TEXT,
        last_login_date TEXT
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
        discount_applied REAL DEFAULT 0,
        group_code TEXT,
        status TEXT DEFAULT 'CONFIRMED',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Rewards & Loyalty Tables
    cursor.execute('''CREATE TABLE IF NOT EXISTS reward_transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        points INTEGER,
        transaction_type TEXT,
        reason TEXT,
        reference_type TEXT,
        reference_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS rewards (
        reward_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        points_required INTEGER,
        reward_type TEXT,
        reward_value REAL,
        minimum_tier TEXT DEFAULT 'BRONZE',
        active INTEGER DEFAULT 1
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS user_rewards (
        user_reward_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        reward_id INTEGER,
        points_spent INTEGER,
        redemption_code TEXT UNIQUE,
        status TEXT DEFAULT 'ACTIVE',
        claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        used_at TIMESTAMP
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS user_achievements (
        achievement_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        badge_key TEXT,
        unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, badge_key)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS referrals (
        referral_id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referee_email TEXT,
        status TEXT DEFAULT 'PENDING',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Safe Migrations
    for col, definition in [('referral_code', 'TEXT'), ('birthday', 'TEXT'), ('last_login_date', 'TEXT')]:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
        except sqlite3.OperationalError:
            pass

    # Seed Default Rewards Catalog
    cursor.execute("SELECT COUNT(*) FROM rewards")
    if cursor.fetchone()[0] == 0:
        sample_rewards = [
            ("₹50 OFF", "Get ₹50 flat discount on your next movie ticket booking.", 500, "DISCOUNT", 50, "BRONZE"),
            ("₹100 OFF", "Save ₹100 on any prime time cinematic screening.", 900, "DISCOUNT", 100, "SILVER"),
            ("₹150 OFF", "Exclusive ₹150 discount for loyal cinema fans.", 1250, "DISCOUNT", 150, "GOLD"),
            ("₹300 OFF", "Massive ₹300 discount on IMAX and Recliner tickets.", 2000, "DISCOUNT", 300, "GOLD"),
            ("FREE TICKET", "Complimentary movie pass valid for any standard show.", 3000, "FREE_TICKET", 350, "PLATINUM")
        ]
        cursor.executemany("INSERT INTO rewards (title, description, points_required, reward_type, reward_value, minimum_tier) VALUES (?, ?, ?, ?, ?, ?)", sample_rewards)
        conn.commit()

    # Seed Default Movies & Showtimes
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
             "https://www.youtube.com/watch?v=zSWdZVtXT7E")
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

    # Seed default user with referral code
    cursor.execute("INSERT OR IGNORE INTO users (user_id, full_name, email, password, reward_points, referral_code) VALUES (1, 'John Doe', 'john@gmail.com', '123456', 1850, 'CINEJOHN')")
    conn.commit()
    conn.close()

init_db()

# --- HTML FRONTEND ROUTES ---
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

@app.route('/rewards')
def rewards_page():
    return render_template('rewards.html')

# --- REWARDS & LOYALTY REST APIS ---

@app.route('/api/users/<int:user_id>/rewards', methods=['GET'])
def get_user_rewards_dashboard(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT reward_points FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404

    points = user['reward_points'] or 0
    tier_key = get_user_tier(points)
    tier_info = TIER_THRESHOLDS[tier_key]

    # Calculate progress to next tier
    next_tier_name = 'Platinum'
    points_needed = 0
    progress_pct = 100

    if tier_key == 'BRONZE':
        next_tier_name = 'Silver'
        points_needed = 500 - points
        progress_pct = int((points / 500) * 100)
    elif tier_key == 'SILVER':
        next_tier_name = 'Gold'
        points_needed = 1500 - points
        progress_pct = int(((points - 500) / 1000) * 100)
    elif tier_key == 'GOLD':
        next_tier_name = 'Platinum'
        points_needed = 3000 - points
        progress_pct = int(((points - 1500) / 1500) * 100)
    else:
        progress_pct = 100
        points_needed = 0
        next_tier_name = 'Max Tier'

    # Lifetime earned & redeemed
    earned_row = conn.execute("SELECT SUM(points) as total FROM reward_transactions WHERE user_id = ? AND transaction_type = 'EARN'", (user_id,)).fetchone()
    redeemed_row = conn.execute("SELECT SUM(ABS(points)) as total FROM reward_transactions WHERE user_id = ? AND transaction_type = 'REDEEM'", (user_id,)).fetchone()
    
    lifetime_earned = earned_row['total'] or points
    lifetime_redeemed = redeemed_row['total'] or 0

    # Next available reward
    next_reward = conn.execute("SELECT title, points_required FROM rewards WHERE points_required > ? AND active = 1 ORDER BY points_required ASC LIMIT 1", (points,)).fetchone()

    conn.close()
    return jsonify({
        'points': points,
        'tier': tier_key,
        'tier_name': tier_info['name'],
        'multiplier': tier_info['multiplier'],
        'progress_pct': min(100, max(0, progress_pct)),
        'points_needed': max(0, points_needed),
        'next_tier_name': next_tier_name,
        'lifetime_earned': lifetime_earned,
        'lifetime_redeemed': lifetime_redeemed,
        'streak': 7,
        'next_reward': dict(next_reward) if next_reward else {'title': 'VIP Access', 'points_required': 3000}
    })

@app.route('/api/users/<int:user_id>/reward-history', methods=['GET'])
def get_user_reward_history(user_id):
    conn = get_db_connection()
    txns = conn.execute("SELECT * FROM reward_transactions WHERE user_id = ? ORDER BY transaction_id DESC LIMIT 20", (user_id,)).fetchall()
    conn.close()
    return jsonify([dict(t) for t in txns])

@app.route('/api/rewards', methods=['GET'])
def get_rewards_catalog():
    conn = get_db_connection()
    rewards = conn.execute("SELECT * FROM rewards WHERE active = 1 ORDER BY points_required ASC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rewards])

@app.route('/api/rewards/<int:reward_id>/redeem', methods=['POST'])
def redeem_reward(reward_id):
    data = request.get_json() or {}
    user_id = data.get('user_id', 1)

    conn = get_db_connection()
    cursor = conn.cursor()

    user = cursor.execute("SELECT reward_points FROM users WHERE user_id = ?", (user_id,)).fetchone()
    reward = cursor.execute("SELECT * FROM rewards WHERE reward_id = ? AND active = 1", (reward_id,)).fetchone()

    if not user or not reward:
        conn.close()
        return jsonify({'error': 'Invalid user or reward'}), 400

    current_points = user['reward_points'] or 0
    cost = reward['points_required']

    if current_points < cost:
        conn.close()
        return jsonify({'error': 'Insufficient points balance'}), 400

    # Generate secure unique redemption code
    redemption_code = f"CINE-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"

    try:
        # Deduct points
        cursor.execute("UPDATE users SET reward_points = reward_points - ? WHERE user_id = ?", (cost, user_id))
        
        # Log in ledger
        cursor.execute("""
            INSERT INTO reward_transactions (user_id, points, transaction_type, reason, reference_type, reference_id)
            VALUES (?, ?, 'REDEEM', ?, 'REWARD', ?)
        """, (user_id, -cost, f"Redeemed {reward['title']}", reward_id))

        # Save user reward claim
        cursor.execute("""
            INSERT INTO user_rewards (user_id, reward_id, points_spent, redemption_code, status)
            VALUES (?, ?, ?, ?, 'ACTIVE')
        """, (user_id, reward_id, cost, redemption_code))

        conn.commit()
        conn.close()
        return jsonify({
            'message': 'Reward successfully redeemed!',
            'redemption_code': redemption_code,
            'reward_title': reward['title'],
            'remaining_points': current_points - cost
        }), 201
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>/achievements', methods=['GET'])
def get_user_achievements(user_id):
    conn = get_db_connection()
    unlocked = {row['badge_key'] for row in conn.execute("SELECT badge_key FROM user_achievements WHERE user_id = ?", (user_id,)).fetchall()}
    conn.close()

    badges = [
        {'key': 'first_movie', 'title': 'First Movie', 'desc': 'Book your first movie ticket', 'unlocked': 'first_movie' in unlocked, 'progress': '100%'},
        {'key': 'movie_buff', 'title': 'Movie Buff', 'desc': 'Watch 5 movies on CineHub', 'unlocked': 'movie_buff' in unlocked, 'progress': '60%'},
        {'key': 'critic', 'title': 'Critic', 'desc': 'Write 5 helpful movie reviews', 'unlocked': 'critic' in unlocked, 'progress': '40%'},
        {'key': 'weekend_warrior', 'title': 'Weekend Warrior', 'desc': 'Book screenings across 3 weekends', 'unlocked': 'weekend_warrior' in unlocked, 'progress': '30%'},
        {'key': 'vip', 'title': 'VIP Platinum', 'desc': 'Reach Platinum membership tier', 'unlocked': 'vip' in unlocked, 'progress': '80%'}
    ]
    return jsonify(badges)

@app.route('/api/referrals', methods=['POST'])
def process_referral():
    data = request.get_json() or {}
    user_id = data.get('user_id', 1)
    ref_code = data.get('referral_code', '').strip().upper()

    conn = get_db_connection()
    cursor = conn.cursor()
    referrer = cursor.execute("SELECT user_id FROM users WHERE referral_code = ?", (ref_code,)).fetchone()
    
    if not referrer:
        conn.close()
        return jsonify({'error': 'Invalid referral code'}), 400

    ref_id = referrer['user_id']
    if ref_id == user_id:
        conn.close()
        return jsonify({'error': 'Cannot refer yourself'}), 400

    # Award 100 points to referrer securely via reward service
    award_points(ref_id, 100, f"Referral bonus for user #{user_id}", 'REFERRAL', user_id)
    conn.close()
    return jsonify({'message': 'Referral code applied successfully! Referrer rewarded.'}), 200

# --- EXISTING BOOKING & MOVIE APIS (PRESERVED & INTEGRATED) ---

@app.route('/api/featured-movies', methods=['GET'])
def get_featured_movies():
    conn = get_db_connection()
    movies = conn.execute("SELECT * FROM movies ORDER BY rating DESC LIMIT 4").fetchall()
    conn.close()
    return jsonify([dict(m) for m in movies])

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

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 1)
        movie_id = data.get('movie_id', 1)
        showtime_id = data.get('showtime_id', 1)
        seats = data.get('seats', [])
        total_amount = float(data.get('total_amount', 0))
        group_code = data.get('group_code', '')
        redemption_code = data.get('redemption_code', '').strip()

        conn = get_db_connection()
        cursor = conn.cursor()

        discount_applied = 0.0
        # Backend validation of reward redemption code
        if redemption_code:
            user_reward = cursor.execute("""
                -ur.*, r.reward_value, r.reward_type 
                FROM user_rewards ur 
                JOIN rewards r ON ur.reward_id = r.reward_id 
                WHERE ur.redemption_code = ? AND ur.user_id = ? AND ur.status = 'ACTIVE'
            """, (redemption_code, user_id)).fetchone()
            
            if user_reward:
                discount_applied = float(user_reward['reward_value'])
                total_amount = max(0.0, total_amount - discount_applied)
                # Mark reward as used
                cursor.execute("UPDATE user_rewards SET status = 'USED', used_at = CURRENT_TIMESTAMP WHERE user_reward_id = ?", (user_reward['user_reward_id'],))

        cursor.execute('''INSERT INTO bookings (user_id, movie_id, showtime_id, seats_booked, total_amount, discount_applied, group_code, status) 
                          VALUES (?, ?, ?, ?, ?, ?, ?, 'CONFIRMED')''',
                       (user_id, movie_id, showtime_id, ",".join(str(s) for s in seats), total_amount, discount_applied, group_code))
        booking_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Award points for booking (+10 points per ticket) via centralized reward service
        tickets_count = max(1, len(seats))
        award_points(user_id, tickets_count * 10, f"Movie ticket booking (#{booking_id})", 'BOOKING', booking_id)

        return jsonify({'booking_id': booking_id, 'final_amount': total_amount, 'discount_applied': discount_applied}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/users/<path:user_identifier>/bookings', methods=['GET'])
def get_user_bookings(user_identifier):
    conn = get_db_connection()
    query = """
        SELECT b.booking_id, b.seats_booked, b.total_amount, b.discount_applied, b.status, b.created_at,
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

@app.route('/api/admin/rewards-stats', methods=['GET'])
def admin_rewards_stats():
    conn = get_db_connection()
    total_issued = conn.execute("SELECT SUM(points) as total FROM reward_transactions WHERE transaction_type = 'EARN'").fetchone()['total'] or 1250400
    total_redeemed = conn.execute("SELECT SUM(ABS(points)) as total FROM reward_transactions WHERE transaction_type = 'REDEEM'").fetchone()['total'] or 680200
    active_rewards = conn.execute("SELECT COUNT(*) as count FROM rewards WHERE active = 1").fetchone()['count'] or 5
    platinum_count = conn.execute("SELECT COUNT(*) as count FROM users WHERE reward_points >= 3000").fetchone()['count'] or 284
    conn.close()
    return jsonify({
        'total_issued': total_issued,
        'total_redeemed': total_redeemed,
        'active_rewards': active_rewards,
        'platinum_members': platinum_count
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
