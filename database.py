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

import os

DB_CONFIG = {
    "dbname": os.environ.get("DB_NAME", os.environ.get("PGDATABASE", "globetrotter_db")),
    "user": os.environ.get("DB_USER", os.environ.get("PGUSER", "postgres")),
    "password": os.environ.get("DB_PASSWORD", os.environ.get("PGPASSWORD", None)),
    "host": os.environ.get("DB_HOST", os.environ.get("PGHOST", "127.0.0.1")),
    "port": int(os.environ.get("DB_PORT", os.environ.get("PGPORT", "5432"))),
}
DB_CONFIG = {k: v for k, v in DB_CONFIG.items() if v is not None}

import subprocess
import sys
import time

def _ensure_pg_service_running():
    try:
        subprocess.run(["wsl", "-d", "Ubuntu", "-u", "root", "--", "service", "postgresql", "start"], 
                       capture_output=True, timeout=10)
        time.sleep(1)
    except Exception:
        pass

def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        return conn
    except psycopg2.OperationalError as e:
        if "127.0.0.1" in str(DB_CONFIG.get("host")) or "localhost" in str(DB_CONFIG.get("host")):
            _logger.info("Attempting to auto-start local PostgreSQL service...")
            _ensure_pg_service_running()
            conn = psycopg2.connect(**DB_CONFIG)
            conn.autocommit = True
            return conn
        raise e

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

if __name__ == "__main__":
    init_db()
