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

    seed_database(conn)
    conn.close()
    _logger.info("Database schema initialized and seed verification complete.")

def seed_database(conn):
    """Populates default admin/demo accounts, destinations, activities, and initial showcase trips."""
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

if __name__ == "__main__":
    init_db()
