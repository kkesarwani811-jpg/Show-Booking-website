# 🎬 CineHub — Premium Movie Booking Experience

> A full-stack movie ticketing web application built with **Flask** + **SQLite**, featuring a cinematic dark UI, interactive seat selection, cinema explorer with live map, food ordering, rewards system, and an admin dashboard.

---

## 📸 Pages at a Glance

| Page | Route | Description |
|---|---|---|
| Home | `/` | Movie catalog with dynamic card grid |
| Cinema Explorer | `/cinema-explorer` | Interactive Leaflet map of nearby cinemas |
| Pick Showtime | `/pick-showtime` | Select date & screen format |
| Seat Selection | `/select-seats` | Interactive seat picker |
| Food & Snacks | `/food-snacks` | Pre-order food items |
| Booking History | `/booking-history` | View past bookings |
| Digital Ticket | `/digital-ticket` | QR-style e-ticket view |
| Rewards | `/rewards` | Loyalty points & tier dashboard |
| Admin Dashboard | `/admin` | Manage movies, stats, rewards |
| Search | `/search?q=` | Search movies by title or genre |

---

## 🗂️ Project Structure

```
movie app/
├── app.py                  # Flask app — routes, API endpoints, scheduler, DB init
├── migrate_db.py           # Database migration script (schema updates & backfill)
├── init_db.py              # Standalone DB initializer (extended schema)
├── cinematic_pulse.db      # SQLite database (auto-generated)
├── package.json            # Node dependencies (anime.js)
├── .gitignore
│
├── services/
│   ├── __init__.py
│   └── movie_sync.py       # TMDb API sync & automated lifecycle cleanup
│
├── static/
│   ├── style.css           # Base stylesheet (dark theme)
│   └── select_seats.js     # Seat selection logic (anime.js powered)
│
├── templates/
│   ├── index.html          # Home / movie catalog
│   ├── cinema_explorer.html# Map-based cinema finder (Leaflet.js)
│   ├── pick_showtime.html  # Showtime picker
│   ├── select_seats.html   # Seat grid UI
│   ├── food_snacks.html    # Concession ordering
│   ├── booking_history.html# User booking records
│   ├── digital_ticket.html # E-ticket display
│   ├── rewards.html        # Loyalty rewards page
│   ├── admin_dashboard.html# Admin panel
│   ├── login.html          # Login page
│   ├── search_results.html # Search results
│   ├── movie_detail.html   # Movie details (v1)
│   └── movie_details.html  # Movie details (v2)
│
├── venv/                   # Python virtual environment
└── node_modules/           # Node packages (anime.js)
```

---

## ⚙️ Tech Stack

### Backend
| Technology | Version | Purpose |
|---|---|---|
| **Python** | 3.x | Runtime |
| **Flask** | 3.1.3 | Web framework |
| **Flask-APScheduler** | 1.13.1 | Background cron & interval automation |
| **Requests** | 2.34.2 | TMDb API integration |
| **Flask-CORS** | 6.0.5 | Cross-origin API support |
| **SQLite3** | built-in | Relational database |
| **Werkzeug** | 3.1.8 | WSGI utilities |
| **Jinja2** | 3.1.6 | HTML templating |

### Frontend
| Technology | Purpose |
|---|---|
| **Tailwind CSS** (CDN) | Utility-first styling |
| **Font Awesome 6** (CDN) | Icons |
| **Leaflet.js 1.9.4** (CDN) | Interactive cinema map |
| **Anime.js 4.5.0** (npm) | Seat selection animations |
| **Vanilla JavaScript** | Fetch API, DOM logic |

---

## 🗄️ Database Schema

The app uses a single SQLite file `cinematic_pulse.db` with the following tables:

```
┌─────────────┐    ┌──────────────┐    ┌────────────────┐
│   movies    │    │  showtimes   │    │   bookings     │
│─────────────│    │──────────────│    │────────────────│
│ movie_id PK │◄───│ movie_id FK  │◄───│ movie_id FK    │
│ title       │    │ cinema_id FK │    │ showtime_id FK │
│ poster_url  │    │ theater_name │    │ seats_booked   │
│ genre       │    │ show_time    │    │ total_amount   │
│ duration    │    │ screen_type  │    │ status         │
│ rating      │    │ price        │    │ created_at     │
│ trailer_url │    └──────────────┘    └────────────────┘
└─────────────┘

┌───────────────────┐    ┌────────────┐
│      cinemas      │    │ food_items │
│───────────────────│    │────────────│
│ cinema_id PK      │    │ item_id PK │
│ cinema_name       │    │ name       │
│ city / area       │    │ category   │
│ latitude/longitude│    │ price      │
│ formats (JSON)    │    │ image_url  │
│ facilities (JSON) │    └────────────┘
│ rating            │
│ starting_price    │
│ screens_count     │
└───────────────────┘
```

> **Extended schema** (via `init_db.py`) also includes: `users`, `payments`, `wishlist`, `reviews` tables.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Node.js & npm (for anime.js)
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/cinehub.git
cd "cinehub"
```

### 2. Set Up Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install flask flask-cors
```

### 4. Install Node Dependencies (anime.js)

```bash
npm install
```

### 5. Initialize the Database *(optional)*

The database auto-initializes when `app.py` runs. To run the extended schema separately:

```bash
python init_db.py
```

### 6. Run the App

```bash
python app.py
```

Open your browser at **[http://localhost:5000](http://localhost:5000)**

---

## 🔌 API Reference

All API endpoints return **JSON** and support CORS.

### Movies

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/movies` | List all movies |
| `GET` | `/api/movies/<id>` | Get movie by ID |
| `GET` | `/api/movies/<id>/showtimes` | Get showtimes for a movie |

### Cinemas

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/cinemas` | List all cinemas (formats & facilities parsed from JSON) |
| `GET` | `/api/cinemas/<id>/showtimes` | Cinema details + grouped movie showtimes |

### Food & Bookings

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/food-items` | List all food/snack items |
| `POST` | `/api/bookings` | Create a booking |
| `GET` | `/api/users/<id>/bookings` | Get all bookings for a user |
| `GET` | `/api/users/<id>/rewards` | Get user reward points & tier |

### Catalog Automation & Admin

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/admin/sync-movies` | Manually trigger TMDb now-playing sync & showtime generation |
| `POST` | `/api/admin/archive-shows` | Manually trigger expired showtime & zero-show movie archival |
| `GET` | `/api/admin/catalog-status` | Overview of active vs archived movies, showtimes, and scheduler state |

#### `POST /api/bookings` — Request Body

```json
{
  "movie_id": 1,
  "showtime_id": 2,
  "seats": ["A1", "A2"],
  "total_amount": 700
}
```

---

## 🎭 Sample Data

The app ships with pre-seeded data for immediate use:

**Movies:** Dune: Part Two · Interstellar · Oppenheimer · The Dark Knight

**Cinemas (Mumbai):**
- CineMax IMAX Luxe — Lower Parel ⭐ 4.9
- PVR ICON Gold — Andheri West ⭐ 4.8
- INOX Megaplex Laser — Malad West ⭐ 4.6
- Cinepolis VIP Grand — Thane West ⭐ 4.7
- Carnival Cinemas Metro — Marine Lines ⭐ 4.3

**Screen Formats:** IMAX 3D · 4DX · Dolby Atmos · Laser 4K · Standard 2D

---

## 🏆 Rewards System

The app includes a tiered loyalty program:

| Tier | Multiplier | Description |
|---|---|---|
| Silver | 1.0x | Starter tier |
| Gold | 1.25x | Mid-level loyalty |
| Platinum | 1.5x | Top tier |

Users earn points per booking; the admin dashboard tracks totals issued and redeemed.

---

## 🛠️ Development Notes

- **Debug mode** is enabled by default (`app.run(debug=True)`). Disable for production.
- The `cinematic_pulse.db` file is auto-created on first run — no manual DB setup needed.
- `formats` and `facilities` cinema fields are stored as **JSON strings** and parsed on every API response.
- The admin dashboard at `/admin` has **no authentication** — add login protection before deploying.
- `static/style.css` provides base dark-theme styles; most UI uses **inline Tailwind** classes.

---

## 📋 Roadmap / Future Improvements

- [ ] Add user authentication (login/register with session management)
- [ ] Protect `/admin` route with admin-only middleware
- [ ] Add payment gateway integration
- [ ] Implement real-time seat availability locking
- [ ] Add movie search with fuzzy matching
- [ ] Add mobile-responsive seat selection view
- [ ] Generate real QR codes for digital tickets
- [ ] Deploy to cloud (Render, Railway, or Fly.io)

---

## 📄 License

This project is for educational and portfolio purposes.

---

> Built with ❤️ using Flask, Tailwind CSS, Leaflet.js, and Anime.js
