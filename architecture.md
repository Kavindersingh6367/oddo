# GlobeTrotter — Complete Architecture & Technical Blueprint

## 1. System Overview

GlobeTrotter is an enterprise-grade, personalized travel-planning platform architected specifically for the **Odoo Hackathon**. It combines Odoo relational domain modeling, PostgreSQL 17 persistence, dynamic budget calculation rollups, deep algorithmic engines, and a responsive modern web interface.

```
+---------------------------------------------------------------------------------------------------+
|                                       GLOBETROTTER PLATFORM                                       |
+---------------------------------------------------------------------------------------------------+
|  Frontend Client Layer (HTML5, Vanilla CSS Design System, Responsive SPA Architecture)            |
|  - Modern Visual Hierarchy (Deep Indigo #4F46E5, Warm Coral #F97316 & Emerald #10B981)            |
|  - Travel DNA Engine: 7-Factor Radar Profile & Explorer Personas                                  |
|  - Trip Health & Diagnostics (0-100 Score with Multi-Factor Ring & Actionable Cards)               |
|  - Smart Itinerary Balancing: Overload Detection & 1-Click Day Optimization                       |
|  - 7 Section Types: Activities, Transit, Hotels, Food, Events, Free Time, and Custom Items        |
|  - Destination Stays & Accommodations: 7-Factor Hotel Recommendation Scoring & Comparison Matrix  |
|  - Community Hub: Traveler Stories, Social Reactions (Likes/Saves) & 1-Click Itinerary Import     |
|  - Universal Global Search: Ctrl+K / Cmd+K Omni-Search across all Entities                        |
|  - Dual View Modes: Interactive Monthly/Weekly Calendar Grid & Vertical Journey Timeline          |
|  - Secure Public Share Viewer (/shared/<token>) & 1-Click Itinerary Duplication                   |
|  - Platform Intelligence & User Management (Role: Admin)                                          |
+---------------------------------------------------------------------------------------------------+
                                            │ HTTP / JSON-RPC / REST API
                                            ▼
+---------------------------------------------------------------------------------------------------+
|  Odoo Module & Controller Layer (globetrotter/)                                                   |
|  - __manifest__.py (Odoo 17 app declaration, security, data, views)                               |
|  - Controllers: /api/v1/auth, /api/v1/trips, /api/v1/hotels, /api/v1/community, /api/v1/admin     |
|  - Access Control Lists (security/ir.model.access.csv)                                            |
|  - Record Rules (security/globetrotter_security.xml) for Multi-Tenant Isolation                   |
|  - XML Views: Forms, Trees, Kanban, Calendar, Graph/Pivot, Menus                                  |
+---------------------------------------------------------------------------------------------------+
                                            │ ORM Model Layer
                                            ▼
+---------------------------------------------------------------------------------------------------+
|  Relational Domain Models & Business Logic (PostgreSQL 17)                                        |
|  - res.users (Travel DNA preferences, currency, role, extended contact fields)                    |
|  - globetrotter.city (Destinations, cost index, popularity, coordinates, travel styles)           |
|  - globetrotter.activity (Curated catalog experiences, category, duration, cost)                  |
|  - globetrotter.hotel (Accommodations, ratings, price tiers, amenities, sub-scores)               |
|  - globetrotter.trip (Itinerary root, computed budget, health diagnostics, balance score)         |
|  - globetrotter.trip.stop (Relational stops, sequence, arrival/departure dates)                   |
|  - globetrotter.trip.activity (Scheduled stop activities, section types, day slots, location)     |
|  - globetrotter.trip.hotel (Hotel reservations, linked expenses, check-in/out dates)              |
|  - globetrotter.expense (Categorized logistics: stay, transit, food, misc)                        |
|  - globetrotter.community.post (Travel stories, ratings, tags, highlights, author)                |
|  - globetrotter.community.interaction (User likes and bookmark saves)                             |
|  - globetrotter.shared.trip (Public unguessable secure tokens, analytics tracking)                |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Computational Engines & Algorithms

### 2.1 Travel DNA Profiling Engine
Evaluates a user's past trips, scheduled activity categories, and configured preferences across 7 dimensions:
* **Dimensions**: Adventure, Culture, Food, Relaxation, Sightseeing, Nature, Shopping (0–100 each).
* **Persona Determination**: Evaluates the dominant dimension to classify the traveler into distinct personas (`Cultural Connoisseur`, `Culinary Explorer`, `Adrenaline Seeker`, `Serenity Seeker`, `Panoramic Sightseer`, `Nature Enthusiast`, `Balanced Explorer`).
* **Preferences Rollup**: Computes preferred accommodation tier (Economy, Midscale, Boutique, Luxury) and average trip duration profile.

### 2.2 Trip Health & Diagnostics Engine (0–100 Score)
A multi-factor diagnostic algorithm evaluating itinerary quality:
1. **Budget Discipline (30 pts)**:
   - Evaluates budget utilization against 100%. Max points when between 60% and 95%. Severe penalties for budget overruns (>100%).
2. **Activity Load & Pacing (25 pts)**:
   - Evaluates daily hours and activity count. Ideal is 3–6 hours/day. Heavy penalty for days exceeding 8 hours (traveler burnout).
3. **Destination Dwell Pacing (20 pts)**:
   - Evaluates whether stops allow sufficient time (minimum 2 days per city).
4. **Accommodation Coverage (15 pts)**:
   - Checks whether every destination stop has confirmed hotel/lodging coverage.
5. **Itinerary Completeness (10 pts)**:
   - Rewards balanced integration of activities, stops, and logistics.

### 2.3 Smart Itinerary Balancing Engine
* **Overload Detection**: Flags days where total scheduled duration exceeds 8.0 hours.
* **Underload Detection**: Identifies days with $< 3.0$ hours of activities.
* **Rebalancing Proposal**: Suggests shifting specific activities from overloaded days to the nearest underloaded day with the fewest hours.
* **1-Click Execution**: Traveler can click "⚡ Accept Suggestion" to automatically execute database transactions that rebalance the itinerary schedule.

### 2.4 Hotel Recommendation & Matching Engine (0–100 Score)
Evaluates accommodations for a specific city and trip dates using a 7-factor weighted scoring model:
* **Style Match (25%)**: Alignment with user travel style.
* **Budget Fit (20%)**: Price per night compared to daily remaining budget.
* **Rating (20%)**: Hotel guest review score (0–5).
* **Location (15%)**: Proximity score (0–10) to attractions.
* **Amenities (10%)**: Match with desired perks (WiFi, Pool, Spa, Breakfast).
* **Popularity (5%)**: Booking count and trend score.
* **Value for Money (5%)**: Rating-to-price ratio.

### 2.5 1-Click Community Itinerary Import Engine
Allows travelers to selectively choose highlights from public community stories and import them directly into their own active trip and day number. Automatically creates `globetrotter_trip_activity` records and recalculates budget rollups.

---

## 3. Security Architecture & Isolation

1. **Password Security**: Standard PBKDF2 with SHA-256 and cryptographic salt.
2. **Session Security**: High-entropy hexadecimal authentication tokens validated on all `/api/v1/*` routes.
3. **Multi-Tenant Isolation**: Record rules enforce strict boundary checks:
   - `SELECT`, `UPDATE`, `DELETE` operations on trips, stops, activities, and hotels require `user_id = current_user.id`.
4. **Admin Protection**: Admin endpoints (`/api/v1/admin/*`) require `user.role === 'admin'`. Unauthorized requests receive `403 Forbidden`.
5. **Secure Sharing**: Public sharing uses unguessable URL-safe tokens (`secrets.token_urlsafe(16)`).
