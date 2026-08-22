# -*- coding: utf-8 -*-
"""
Database connection pool, schema initialization, migrations, and seeding for GlobeTrotter (PostgreSQL 17).
"""

import psycopg2
import psycopg2.extras
from passlib.hash import pbkdf2_sha256
import json
import logging
from datetime import date, timedelta
from globetrotter.data.seed_data import DESTINATIONS_DATA

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger("globetrotter.db")

DB_CONFIG = {
    "dbname": "globetrotter_db",
    "user": "postgres",
    "host": "127.0.0.1",
    "port": 5432
}

def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn

def init_db():
    """Initializes normalized PostgreSQL schema, indexes, constraints and seed data."""
    _logger.info("Initializing PostgreSQL schema for GlobeTrotter...")
    conn = get_db_connection()
    with conn.cursor() as cur:
        # 1. Users Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS res_users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                preferred_currency VARCHAR(10) DEFAULT 'INR',
                preferred_travel_style VARCHAR(50) DEFAULT 'balanced',
                preferred_language VARCHAR(10) DEFAULT 'en',
                avatar_url TEXT,
                bio TEXT,
                role VARCHAR(50) DEFAULT 'traveler',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. Cities Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS globetrotter_city (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                country VARCHAR(255) NOT NULL,
                region VARCHAR(50) NOT NULL DEFAULT 'asia',
                description TEXT,
                cost_index INT DEFAULT 2,
                popularity INT DEFAULT 80,
                recommended_duration_days INT DEFAULT 3,
                cover_image TEXT,
                latitude NUMERIC(10, 6),
                longitude NUMERIC(10, 6),
                travel_styles TEXT,
                CONSTRAINT uq_city_country UNIQUE(name, country)
            );
            CREATE INDEX IF NOT EXISTS idx_city_name ON globetrotter_city(name);
            CREATE INDEX IF NOT EXISTS idx_city_country ON globetrotter_city(country);
            CREATE INDEX IF NOT EXISTS idx_city_region ON globetrotter_city(region);
        """)

        # 3. Activities Catalog Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS globetrotter_activity (
                id SERIAL PRIMARY KEY,
                city_id INT NOT NULL REFERENCES globetrotter_city(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                category VARCHAR(50) NOT NULL DEFAULT 'sightseeing',
                duration_hours NUMERIC(4, 2) DEFAULT 2.0,
                estimated_cost NUMERIC(12, 2) DEFAULT 0.0,
                currency VARCHAR(10) DEFAULT 'INR',
                popularity INT DEFAULT 85,
                image TEXT,
                location_name VARCHAR(255)
            );
            CREATE INDEX IF NOT EXISTS idx_activity_city ON globetrotter_activity(city_id);
            CREATE INDEX IF NOT EXISTS idx_activity_category ON globetrotter_activity(category);
        """)

        # 4. Trips Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS globetrotter_trip (
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL REFERENCES res_users(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                description TEXT,
                cover_image TEXT,
                currency VARCHAR(10) DEFAULT 'INR',
                travelers_count INT DEFAULT 1,
                total_budget NUMERIC(14, 2) DEFAULT 0.0,
                travel_style VARCHAR(50) DEFAULT 'balanced',
                status VARCHAR(50) DEFAULT 'upcoming',
                share_token VARCHAR(100) UNIQUE,
                is_public BOOLEAN DEFAULT FALSE,
                share_budget BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_trip_user ON globetrotter_trip(user_id);
            CREATE INDEX IF NOT EXISTS idx_trip_token ON globetrotter_trip(share_token);
        """)

        # 5. Trip Stops Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS globetrotter_trip_stop (
                id SERIAL PRIMARY KEY,
                trip_id INT NOT NULL REFERENCES globetrotter_trip(id) ON DELETE CASCADE,
                city_id INT NOT NULL REFERENCES globetrotter_city(id) ON DELETE RESTRICT,
                sequence INT DEFAULT 10,
                arrival_date DATE NOT NULL,
                departure_date DATE NOT NULL,
                duration_days INT DEFAULT 1,
                notes TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_stop_trip ON globetrotter_trip_stop(trip_id);
            CREATE INDEX IF NOT EXISTS idx_stop_seq ON globetrotter_trip_stop(trip_id, sequence);
        """)

        # 6. Scheduled Trip Activities Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS globetrotter_trip_activity (
                id SERIAL PRIMARY KEY,
                trip_id INT NOT NULL REFERENCES globetrotter_trip(id) ON DELETE CASCADE,
                stop_id INT REFERENCES globetrotter_trip_stop(id) ON DELETE CASCADE,
                activity_id INT REFERENCES globetrotter_activity(id) ON DELETE SET NULL,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(50) DEFAULT 'sightseeing',
                day_number INT DEFAULT 1,
                scheduled_date DATE,
                scheduled_time VARCHAR(20) DEFAULT '10:00',
                duration_hours NUMERIC(4, 2) DEFAULT 2.0,
                estimated_cost NUMERIC(12, 2) DEFAULT 0.0,
                sequence INT DEFAULT 10,
                notes TEXT,
                image TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_trip_act_trip ON globetrotter_trip_activity(trip_id);
            CREATE INDEX IF NOT EXISTS idx_trip_act_day ON globetrotter_trip_activity(trip_id, day_number);
        """)

        # 7. Expenses Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS globetrotter_expense (
                id SERIAL PRIMARY KEY,
                trip_id INT NOT NULL REFERENCES globetrotter_trip(id) ON DELETE CASCADE,
                stop_id INT REFERENCES globetrotter_trip_stop(id) ON DELETE SET NULL,
                category VARCHAR(50) NOT NULL DEFAULT 'accommodation',
                name VARCHAR(255) NOT NULL,
                amount NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
                date DATE,
                notes TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_expense_trip ON globetrotter_expense(trip_id);
        """)

        # 8. Saved Destinations Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS globetrotter_saved_destination (
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL REFERENCES res_users(id) ON DELETE CASCADE,
                city_id INT NOT NULL REFERENCES globetrotter_city(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_user_city UNIQUE(user_id, city_id)
            );
        """)

        # 9. Public Shared Trip Log
        cur.execute("""
            CREATE TABLE IF NOT EXISTS globetrotter_shared_trip (
                id SERIAL PRIMARY KEY,
                trip_id INT NOT NULL REFERENCES globetrotter_trip(id) ON DELETE CASCADE,
                share_token VARCHAR(100) UNIQUE NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                view_count INT DEFAULT 0,
                copy_count INT DEFAULT 0,
                allow_budget_view BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 10. Hotels Catalog Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS globetrotter_hotel (
                id SERIAL PRIMARY KEY,
                city_id INT NOT NULL REFERENCES globetrotter_city(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                address VARCHAR(255),
                latitude NUMERIC(10, 6),
                longitude NUMERIC(10, 6),
                image TEXT,
                rating NUMERIC(3, 2) DEFAULT 4.5,
                review_count INT DEFAULT 150,
                price_per_night NUMERIC(12, 2) NOT NULL DEFAULT 3000.0,
                currency VARCHAR(10) DEFAULT 'INR',
                hotel_category VARCHAR(50) NOT NULL DEFAULT 'mid_range',
                amenities TEXT DEFAULT 'wifi,breakfast,ac,parking',
                room_types TEXT DEFAULT 'Standard Double Room, Deluxe Suite',
                max_guests INT DEFAULT 3,
                available_rooms INT DEFAULT 10,
                check_in_time VARCHAR(20) DEFAULT '14:00',
                check_out_time VARCHAR(20) DEFAULT '11:00',
                location_score NUMERIC(3, 1) DEFAULT 9.0,
                cleanliness_score NUMERIC(3, 1) DEFAULT 9.2,
                service_score NUMERIC(3, 1) DEFAULT 8.8,
                value_score NUMERIC(3, 1) DEFAULT 9.0,
                popularity_score INT DEFAULT 88,
                active BOOLEAN DEFAULT TRUE
            );
            CREATE INDEX IF NOT EXISTS idx_hotel_city ON globetrotter_hotel(city_id);
            CREATE INDEX IF NOT EXISTS idx_hotel_category ON globetrotter_hotel(hotel_category);
            CREATE INDEX IF NOT EXISTS idx_hotel_price ON globetrotter_hotel(price_per_night);
            CREATE INDEX IF NOT EXISTS idx_hotel_rating ON globetrotter_hotel(rating);
        """)

        # 11. Trip Hotel Bookings Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS globetrotter_trip_hotel (
                id SERIAL PRIMARY KEY,
                trip_id INT NOT NULL REFERENCES globetrotter_trip(id) ON DELETE CASCADE,
                hotel_id INT NOT NULL REFERENCES globetrotter_hotel(id) ON DELETE RESTRICT,
                stop_id INT REFERENCES globetrotter_trip_stop(id) ON DELETE CASCADE,
                expense_id INT REFERENCES globetrotter_expense(id) ON DELETE SET NULL,
                check_in DATE NOT NULL,
                check_out DATE NOT NULL,
                number_of_nights INT DEFAULT 1,
                number_of_guests INT DEFAULT 2,
                number_of_rooms INT DEFAULT 1,
                price_per_night NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
                total_cost NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
                room_type_selected VARCHAR(255) DEFAULT 'Standard Double Room',
                notes TEXT,
                status VARCHAR(50) DEFAULT 'selected',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_trip_hotel_trip ON globetrotter_trip_hotel(trip_id);
            CREATE INDEX IF NOT EXISTS idx_trip_hotel_stop ON globetrotter_trip_hotel(stop_id);
            CREATE INDEX IF NOT EXISTS idx_trip_hotel_hotel ON globetrotter_trip_hotel(hotel_id);
        """)

        # 12. Community Posts Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS globetrotter_community_post (
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL REFERENCES res_users(id) ON DELETE CASCADE,
                city_id INT REFERENCES globetrotter_city(id) ON DELETE SET NULL,
                trip_id INT REFERENCES globetrotter_trip(id) ON DELETE SET NULL,
                title VARCHAR(255) NOT NULL,
                experience_text TEXT NOT NULL,
                cover_image TEXT,
                rating NUMERIC(3, 1) DEFAULT 4.8,
                estimated_cost NUMERIC(12, 2) DEFAULT 0.0,
                travel_style VARCHAR(50) DEFAULT 'balanced',
                activity_highlights JSONB DEFAULT '[]'::jsonb,
                likes_count INT DEFAULT 0,
                saves_count INT DEFAULT 0,
                imports_count INT DEFAULT 0,
                tags TEXT,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_comm_city ON globetrotter_community_post(city_id);
            CREATE INDEX IF NOT EXISTS idx_comm_user ON globetrotter_community_post(user_id);
            CREATE INDEX IF NOT EXISTS idx_comm_likes ON globetrotter_community_post(likes_count DESC);
        """)

        # 13. Community Interactions Table (Likes, Saves, Imports)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS globetrotter_community_interaction (
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL REFERENCES res_users(id) ON DELETE CASCADE,
                post_id INT NOT NULL REFERENCES globetrotter_community_post(id) ON DELETE CASCADE,
                interaction_type VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_user_post_interaction UNIQUE(user_id, post_id, interaction_type)
            );
            CREATE INDEX IF NOT EXISTS idx_comm_int_user ON globetrotter_community_interaction(user_id);
            CREATE INDEX IF NOT EXISTS idx_comm_int_post ON globetrotter_community_interaction(post_id);
        """)

        # 14. Apply Migrations / Column Additions
        cur.execute("""
            ALTER TABLE res_users ADD COLUMN IF NOT EXISTS first_name VARCHAR(100);
            ALTER TABLE res_users ADD COLUMN IF NOT EXISTS last_name VARCHAR(100);
            ALTER TABLE res_users ADD COLUMN IF NOT EXISTS phone VARCHAR(50);
            ALTER TABLE res_users ADD COLUMN IF NOT EXISTS city VARCHAR(100);
            ALTER TABLE res_users ADD COLUMN IF NOT EXISTS country VARCHAR(100);
            ALTER TABLE res_users ADD COLUMN IF NOT EXISTS additional_info TEXT;

            ALTER TABLE globetrotter_trip_activity ADD COLUMN IF NOT EXISTS section_type VARCHAR(50) DEFAULT 'activity';
            ALTER TABLE globetrotter_trip_activity ADD COLUMN IF NOT EXISTS location_address TEXT;
        """)

    seed_database(conn)
    conn.close()
    _logger.info("Database schema initialized and seed verification complete.")

def seed_database(conn):
    """Populates default admin/demo accounts, destinations, activities, hotels, and initial showcase trips."""
    from globetrotter.data.seed_data import HOTELS_DATA
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        # 1. Seed Demo & Admin Users
        cur.execute("SELECT id FROM res_users WHERE email = 'demo@globetrotter.travel'")
        demo_user = cur.fetchone()
        if not demo_user:
            cur.execute("""
                INSERT INTO res_users (name, email, password_hash, preferred_currency, preferred_travel_style, role, bio)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, (
                "Rohan Sharma",
                "demo@globetrotter.travel",
                pbkdf2_sha256.hash("demo123"),
                "INR",
                "balanced",
                "traveler",
                "Avid traveler, photographer, and culture enthusiast."
            ))
            demo_user = cur.fetchone()

        cur.execute("SELECT id FROM res_users WHERE email = 'admin@globetrotter.travel'")
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO res_users (name, email, password_hash, preferred_currency, preferred_travel_style, role, bio)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (
                "System Administrator",
                "admin@globetrotter.travel",
                pbkdf2_sha256.hash("admin123"),
                "INR",
                "luxury",
                "admin",
                "GlobeTrotter Platform Lead & Odoo System Administrator."
            ))

        # 2. Seed Cities and Activities
        for d in DESTINATIONS_DATA:
            cur.execute("""
                INSERT INTO globetrotter_city (name, country, region, description, cost_index, popularity, recommended_duration_days, cover_image, latitude, longitude, travel_styles)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (name, country) DO UPDATE SET
                    description = EXCLUDED.description,
                    cost_index = EXCLUDED.cost_index,
                    popularity = EXCLUDED.popularity,
                    cover_image = EXCLUDED.cover_image,
                    travel_styles = EXCLUDED.travel_styles
                RETURNING id;
            """, (
                d["name"], d["country"], d["region"], d["description"],
                d["cost_index"], d["popularity"], d["recommended_duration_days"],
                d["cover_image"], d["latitude"], d["longitude"], d["travel_styles"]
            ))
            city_row = cur.fetchone()
            city_id = city_row["id"]

            for act in d.get("activities", []):
                cur.execute("""
                    SELECT id FROM globetrotter_activity WHERE city_id = %s AND name = %s;
                """, (city_id, act["name"]))
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO globetrotter_activity (city_id, name, description, category, duration_hours, estimated_cost, currency, popularity, image, location_name)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (
                        city_id, act["name"], act["description"], act["category"],
                        act["duration_hours"], act["estimated_cost"], "INR",
                        act["popularity"], act["image"], act.get("location_name", "")
                    ))

        # 3. Seed Hotels
        for city_name, hotel_list in HOTELS_DATA.items():
            cur.execute("SELECT id FROM globetrotter_city WHERE name = %s;", (city_name,))
            city_row = cur.fetchone()
            if not city_row:
                continue
            city_id = city_row["id"]

            for h in hotel_list:
                cur.execute("SELECT id FROM globetrotter_hotel WHERE city_id = %s AND name = %s;", (city_id, h["name"]))
                existing_h = cur.fetchone()
                if not existing_h:
                    cur.execute("""
                        INSERT INTO globetrotter_hotel (
                            city_id, name, description, address, image, rating, review_count,
                            price_per_night, currency, hotel_category, amenities, room_types,
                            max_guests, available_rooms, location_score, cleanliness_score,
                            service_score, value_score, popularity_score, active
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE);
                    """, (
                        city_id, h["name"], h.get("description", ""), h.get("address", ""),
                        h.get("image", ""), h.get("rating", 4.5), h.get("review_count", 150),
                        h["price_per_night"], h.get("currency", "INR"), h["hotel_category"],
                        h.get("amenities", "wifi,breakfast,ac"), h.get("room_types", "Standard Double Room"),
                        h.get("max_guests", 3), h.get("available_rooms", 10),
                        h.get("location_score", 9.0), h.get("cleanliness_score", 9.2),
                        h.get("service_score", 8.8), h.get("value_score", 9.0),
                        h.get("popularity_score", 88)
                    ))
                else:
                    cur.execute("""
                        UPDATE globetrotter_hotel SET
                            price_per_night = %s,
                            rating = %s,
                            hotel_category = %s,
                            amenities = %s,
                            image = %s,
                            description = %s,
                            address = %s,
                            location_score = %s,
                            cleanliness_score = %s,
                            service_score = %s,
                            value_score = %s,
                            popularity_score = %s
                        WHERE id = %s;
                    """, (
                        h["price_per_night"], h.get("rating", 4.5), h["hotel_category"],
                        h.get("amenities", "wifi,breakfast,ac"), h.get("image", ""),
                        h.get("description", ""), h.get("address", ""),
                        h.get("location_score", 9.0), h.get("cleanliness_score", 9.2),
                        h.get("service_score", 8.8), h.get("value_score", 9.0),
                        h.get("popularity_score", 88), existing_h["id"]
                    ))

        # 4. Seed Community Experience Posts
        cur.execute("SELECT COUNT(*) as cnt FROM globetrotter_community_post;")
        if cur.fetchone()["cnt"] == 0:
            # Fetch user and city IDs
            cur.execute("SELECT id FROM res_users WHERE email = 'demo@globetrotter.travel';")
            author_id = cur.fetchone()["id"]

            COMMUNITY_SEEDS = [
                {
                    "title": "48 Hours of Royal Heritage & Street Food in Jaipur",
                    "city_name": "Jaipur",
                    "cover_image": "https://images.unsplash.com/photo-1599661046289-e31897846e41?w=800&auto=format&fit=crop&q=80",
                    "rating": 4.9,
                    "estimated_cost": 4500.0,
                    "travel_style": "balanced",
                    "tags": "#heritage, #streetfood, #rajasthan, #photography",
                    "likes_count": 48,
                    "saves_count": 29,
                    "imports_count": 14,
                    "experience_text": "Jaipur is magical when planned with early morning starts. Avoid midday crowds at Amber Fort by reaching at 8:00 AM. In the evening, the rooftop cafes facing Hawa Mahal provide an unbeatable view with hot masala chai.",
                    "activity_highlights": [
                        {"name": "Amber Fort Sunrise Exploration", "category": "culture", "duration_hours": 3.0, "estimated_cost": 500.0, "scheduled_time": "08:00", "notes": "Early morning entrance avoids tourist buses"},
                        {"name": "Hawa Mahal & Wind View Rooftop Cafe", "category": "sightseeing", "duration_hours": 1.5, "estimated_cost": 250.0, "scheduled_time": "11:30", "notes": "Best angle for photos and authentic chai"},
                        {"name": "Old City Bazaars & Johari Market Walk", "category": "shopping", "duration_hours": 2.0, "estimated_cost": 300.0, "scheduled_time": "16:00", "notes": "Handicrafts, textiles, and blue pottery"},
                        {"name": "Chokhi Dhani Cultural Village & Rajasthani Thali", "category": "food", "duration_hours": 3.0, "estimated_cost": 900.0, "scheduled_time": "19:30", "notes": "Folk dance, puppet shows and traditional feast"}
                    ]
                },
                {
                    "title": "Secret Bazaars & Monument Trail of Old Delhi",
                    "city_name": "Delhi",
                    "cover_image": "https://images.unsplash.com/photo-1587474260584-136574528ed5?w=800&auto=format&fit=crop&q=80",
                    "rating": 4.8,
                    "estimated_cost": 2200.0,
                    "travel_style": "budget",
                    "tags": "#olddelhi, #budgettravel, #foodtrail, #history",
                    "likes_count": 62,
                    "saves_count": 41,
                    "imports_count": 19,
                    "experience_text": "Delhi's true soul lives in Shahjahanabad. Take the heritage metro to Chandni Chowk, explore the spice market atop Khari Baoli, and enjoy the tranquil gardens of Humayun's Tomb right before sundown.",
                    "activity_highlights": [
                        {"name": "Red Fort Morning Architecture Walk", "category": "culture", "duration_hours": 2.5, "estimated_cost": 35.0, "scheduled_time": "09:00", "notes": "Mughal architecture and Diwan-i-Khas"},
                        {"name": "Chandni Chowk & Paranthe Wali Gali Food Trail", "category": "food", "duration_hours": 1.5, "estimated_cost": 250.0, "scheduled_time": "12:00", "notes": "Fried flatbreads and rabri jalebi"},
                        {"name": "Khari Baoli Spice Market Rooftop View", "category": "sightseeing", "duration_hours": 1.0, "estimated_cost": 50.0, "scheduled_time": "14:30", "notes": "Asia's largest wholesale spice market"},
                        {"name": "Humayun's Tomb Garden Sunset Walk", "category": "nature", "duration_hours": 2.0, "estimated_cost": 40.0, "scheduled_time": "17:00", "notes": "UNESCO World Heritage Site with serene water canals"}
                    ]
                },
                {
                    "title": "Lakeside Serenity & Palace Cruises in Udaipur",
                    "city_name": "Udaipur",
                    "cover_image": "https://images.unsplash.com/photo-1615836245337-f5b9b2303f10?w=800&auto=format&fit=crop&q=80",
                    "rating": 5.0,
                    "estimated_cost": 7500.0,
                    "travel_style": "luxury",
                    "tags": "#udaipur, #lakepichola, #luxury, #romance",
                    "likes_count": 89,
                    "saves_count": 55,
                    "imports_count": 27,
                    "experience_text": "The City of Lakes is the epitome of romantic serenity. Stay in a lake-facing heritage haveli, take the private boat cruise around Jag Mandir, and attend the Dharohar folk dance show at Bagore Ki Haveli.",
                    "activity_highlights": [
                        {"name": "City Palace Complex & Crystal Gallery", "category": "culture", "duration_hours": 3.0, "estimated_cost": 400.0, "scheduled_time": "10:00", "notes": "Panoramic views over Lake Pichola"},
                        {"name": "Lake Pichola Sunset Boat Cruise to Jag Mandir", "category": "adventure", "duration_hours": 1.5, "estimated_cost": 500.0, "scheduled_time": "16:30", "notes": "Golden hour reflection on palace walls"},
                        {"name": "Bagore Ki Haveli Dharohar Dance Performance", "category": "entertainment", "duration_hours": 1.5, "estimated_cost": 150.0, "scheduled_time": "19:00", "notes": "Rajasthani folk music, puppets, and fire dance"}
                    ]
                },
                {
                    "title": "Parisian Art, Cafes & Seine Sunset Promenade",
                    "city_name": "Paris",
                    "cover_image": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=800&auto=format&fit=crop&q=80",
                    "rating": 4.9,
                    "estimated_cost": 9500.0,
                    "travel_style": "balanced",
                    "tags": "#paris, #art, #culture, #cafeculture",
                    "likes_count": 76,
                    "saves_count": 48,
                    "imports_count": 22,
                    "experience_text": "Paris is best enjoyed on foot. Walk along the Seine from Notre-Dame to the Louvre, stop for espresso and croissants in Saint-Germain, and end the day watching the Eiffel Tower sparkle at 10 PM.",
                    "activity_highlights": [
                        {"name": "Louvre Museum Highlights Tour", "category": "culture", "duration_hours": 3.0, "estimated_cost": 1800.0, "scheduled_time": "09:30", "notes": "Mona Lisa and Venus de Milo"},
                        {"name": "Montmartre Hilltop & Sacré-Cœur Walk", "category": "sightseeing", "duration_hours": 2.0, "estimated_cost": 0.0, "scheduled_time": "14:00", "notes": "Cobblestone streets and panoramic city views"},
                        {"name": "Seine River Sunset Cruise", "category": "relaxation", "duration_hours": 1.5, "estimated_cost": 1500.0, "scheduled_time": "18:30", "notes": "Historic bridges and illuminated monuments"}
                    ]
                }
            ]

            for seed in COMMUNITY_SEEDS:
                cur.execute("SELECT id FROM globetrotter_city WHERE name = %s;", (seed["city_name"],))
                c_row = cur.fetchone()
                c_id = c_row["id"] if c_row else None
                cur.execute("""
                    INSERT INTO globetrotter_community_post (
                        user_id, city_id, title, experience_text, cover_image, rating,
                        estimated_cost, travel_style, activity_highlights, likes_count,
                        saves_count, imports_count, tags, active
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE);
                """, (
                    author_id, c_id, seed["title"], seed["experience_text"], seed["cover_image"],
                    seed["rating"], seed["estimated_cost"], seed["travel_style"],
                    json.dumps(seed["activity_highlights"]), seed["likes_count"],
                    seed["saves_count"], seed["imports_count"], seed["tags"]
                ))

if __name__ == "__main__":
    init_db()

