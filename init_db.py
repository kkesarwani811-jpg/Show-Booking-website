import sqlite3

def init_db():
    conn = sqlite3.connect("cinematic_pulse.db")
    cursor = conn.cursor()

    # Create / Upgrade Users Table with Reward Points
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            reward_points INTEGER DEFAULT 120,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create Movies Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            movie_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            genre TEXT,
            duration_mins INTEGER,
            rating TEXT,
            poster_url TEXT,
            trailer_url TEXT,
            description TEXT
        )
    """)

    # Create Showtimes Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS showtimes (
            showtime_id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER,
            theater_name TEXT,
            show_time TEXT,
            price REAL,
            FOREIGN KEY (movie_id) REFERENCES movies (movie_id)
        )
    """)

    # Create Bookings Table (with group code support)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            movie_id INTEGER,
            showtime_id INTEGER,
            seats_booked TEXT,
            total_amount REAL,
            status TEXT DEFAULT 'CONFIRMED',
            group_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (movie_id) REFERENCES movies (movie_id),
            FOREIGN KEY (showtime_id) REFERENCES showtimes (showtime_id)
        )
    """)

    # Create Payments Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            payment_gateway TEXT NOT NULL,
            transaction_ref TEXT UNIQUE NOT NULL,
            amount REAL NOT NULL,
            payment_status TEXT DEFAULT 'SUCCESS',
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (booking_id) REFERENCES bookings (booking_id)
        )
    """)

    # Create Wishlist Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wishlist (
            wishlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            movie_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (movie_id) REFERENCES movies (movie_id),
            UNIQUE(user_id, movie_id)
        )
    """)

    # Create Reviews Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            review_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            movie_id INTEGER NOT NULL,
            rating INTEGER CHECK(rating >= 1 AND rating <= 5),
            review_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (movie_id) REFERENCES movies (movie_id)
        )
    """)

    # Ensure Default User exists
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (full_name, email, password, reward_points) VALUES (?, ?, ?, ?)", 
                       ("John Doe", "john@example.com", "password123", 150))

    conn.commit()
    conn.close()
    print("Database upgraded with AI, Wishlist, Reviews, Rewards, and Group Booking schema!")

if __name__ == "__main__":
    init_db()
