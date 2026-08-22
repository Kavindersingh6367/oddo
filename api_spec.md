# GlobeTrotter — REST & JSON-RPC API Specification

Base URL: `http://127.0.0.1:8069/api/v1`

---

## 1. Authentication & Profile Endpoints

### `POST /auth/signup`
Creates a new user account with full profile details.
* **Request Body**:
  ```json
  {
    "name": "Rohan Sharma",
    "first_name": "Rohan",
    "last_name": "Sharma",
    "email": "rohan@example.com",
    "password": "secretPassword123",
    "phone": "+91 98765 43210",
    "city": "Mumbai",
    "country": "India",
    "preferred_currency": "INR",
    "preferred_travel_style": "balanced",
    "avatar_url": "https://images.unsplash.com/...",
    "additional_info": "Passionate about heritage architecture and local street food."
  }
  ```
* **Response (200 OK)**:
  ```json
  {
    "success": true,
    "token": "a49f82e1c9...",
    "user": { "id": 1, "name": "Rohan Sharma", "email": "rohan@example.com", "role": "traveler" }
  }
  ```

### `POST /auth/login`
Authenticates user and issues session token.
* **Request Body**:
  ```json
  {
    "email": "rohan@example.com",
    "password": "secretPassword123"
  }
  ```
* **Response (200 OK)**:
  ```json
  {
    "success": true,
    "token": "a49f82e1c9...",
    "user": { "id": 1, "name": "Rohan Sharma", "email": "rohan@example.com", "role": "traveler" }
  }
  ```

### `POST /auth/demo-login`
Fast 1-click login for Hackathon presentation.
* **Request Body**: `{"role": "traveler"}` or `{"role": "admin"}`

### `GET /auth/me`
Fetches authenticated user profile, travel style, preferences, and dynamically calculated Travel DNA radar profile.

### `PUT /auth/profile`
Updates traveler preferences, personal info, avatar, and travel style.

### `GET /user/travel-dna`
Retrieves deep 7-factor Travel DNA breakdown (`adventure`, `culture`, `food`, `relaxation`, `sightseeing`, `nature`, `shopping`), explorer persona title, accommodation preference, average trip duration preference, and actionable traveler insights.

---

## 2. Trips Endpoints

### `GET /trips?status={all|upcoming|ongoing|completed|draft}`
Lists all trips owned by the authenticated user with real-time computed budget rollup, Trip Health score (/100), and balance alerts.

### `POST /trips`
Creates a new trip and validates date sequences and budget positivity.
* **Request Body**:
  ```json
  {
    "name": "Rajasthan Explorer",
    "start_date": "2026-10-01",
    "end_date": "2026-10-07",
    "total_budget": 35000.0,
    "travelers_count": 2,
    "currency": "INR",
    "travel_style": "balanced",
    "cover_image": "https://images.unsplash.com/...",
    "description": "Delhi -> Jaipur -> Udaipur journey."
  }
  ```

### `GET /trips/<id>`
Retrieves full itinerary details: stops, day-by-day scheduled activities (with section types & location addresses), hotel reservations, logged expenses, budget rollup, intelligence alerts, 0–100 Trip Health Diagnostics breakdown, and Smart Balancing suggestions.

### `PUT /trips/<id>`
Updates trip metadata, dates, or target budget.

### `DELETE /trips/<id>`
Deletes trip and cascades deletion to all associated stops, activities, hotel bookings, and expenses.

### `POST /trips/<id>/duplicate`
Deep-clones the entire trip including all child stops, activities, hotel bookings, and expenses with new relational IDs.

### `POST /trips/<id>/share`
Generates/toggles secure public sharing link.
* **Request Body**: `{"is_public": true, "share_budget": true}`
* **Response**: `{"share_token": "V4xy3PQT...", "share_url": "/shared/V4xy3PQT..."}`

### `POST /trips/<id>/balance`
Executes the Smart Itinerary Balancing Engine to automatically shift scheduled activities from overloaded days (>8.0 hrs) into underloaded or free days.

---

## 3. Stops & Activity Endpoints

### `POST /trips/<id>/stops`
Adds a destination stop to the trip.

### `POST /trips/<id>/stops/reorder`
Reorders sequence of stops in the route.
* **Request Body**: `{"stop_ids": [12, 14, 13]}`

### `DELETE /trips/<id>/stops/<stop_id>`
Removes stop and associated activities from the trip.

### `POST /trips/<id>/activities`
Schedules an activity or section item to a specific day number and stop.
* **Request Body**:
  ```json
  {
    "name": "Amber Palace Sunrise Trek",
    "section_type": "activity",
    "day_number": 2,
    "scheduled_time": "08:00",
    "category": "culture",
    "estimated_cost": 500.0,
    "duration_hours": 2.5,
    "stop_id": 4,
    "location_address": "Devisinghpura, Amer, Jaipur 302001",
    "notes": "Bring camera for panoramic view."
  }
  ```

### `PUT /trips/<id>/activities/<act_id>`
Modifies activity section type, time slot, day assignment, duration, location address, notes, or cost.

### `DELETE /trips/<id>/activities/<act_id>`
Removes scheduled activity and recalculates trip budget and health diagnostics.

### `POST /trips/<id>/activities/<act_id>/move-day`
Moves activity directly to a new target day number.
* **Request Body**: `{"day_number": 3}`

### `POST /trips/<id>/activities/<act_id>/duplicate`
Clones a single activity into the same day or a target day.
* **Request Body**: `{"target_day": 4}`

### `POST /trips/<id>/expenses`
Logs transportation, accommodation, meal, or miscellaneous expense.

### `DELETE /trips/<id>/expenses/<exp_id>`
Removes logged expense and updates financial summary.

---

## 4. Hotel Recommendation & Accommodations Endpoints

### `GET /hotels/recommendations?city_id={id}&trip_id={id}&check_in={date}&check_out={date}&guests={n}&rooms={n}&category={cat}&min_rating={r}&min_price={p}&max_price={p}&amenities={wifi,pool}&sort_by={sort}`
Searches and scores hotel recommendations with transparent 0–100 matching engine, dynamic badges (`🏆 Best Overall`, `💰 Best Budget`, etc.), budget fit flags, and "Why this hotel?" data-driven explanations.

### `GET /hotels/<id>`
Retrieves single hotel details, sub-ratings (location, cleanliness, service, value), room types, and amenities.

### `GET /hotels/compare?ids={id1,id2,id3}&trip_id={id}&nights={n}&rooms={n}`
Returns side-by-side comparison matrix for 2–3 hotels with price rollups and quality sub-scores.

### `POST /trips/<trip_id>/hotels`
Adds/books a hotel stay for a specific trip stop. Automatically creates a linked `accommodation` expense in `globetrotter_expense` and updates total cost and remaining budget.

### `PUT /trips/<trip_id>/hotels/<booking_id>`
Modifies hotel reservation (dates, rooms, guests, room type) and automatically recalculates total cost and linked accommodation expense.

### `DELETE /trips/<trip_id>/hotels/<booking_id>`
Removes hotel reservation and deletes linked accommodation expense, restoring trip budget.

---

## 5. Community Hub Endpoints

### `GET /community/posts?q={search}&city={city_id}&style={style}&sort_by={popular|rating|newest|imports}`
Lists community travel stories and shared itineraries with author details, tags, ratings, likes/saves counts, and highlight previews.

### `GET /community/posts/<id>`
Retrieves full community story details including full narrative, photos, activity highlights list with costs, and author bio.

### `POST /community/posts`
Publishes a new traveler experience / itinerary story to the community hub.

### `POST /community/posts/<id>/interact`
Toggles user like or bookmark/save on a community post.
* **Request Body**: `{"type": "like"}` or `{"type": "save"}`

### `POST /community/posts/<id>/import`
**1-Click Itinerary Import Engine**: Selects activities from the community post and imports them into a target user trip and day, automatically logging estimated costs into the trip budget rollup.
* **Request Body**:
  ```json
  {
    "trip_id": 5,
    "stop_id": 12,
    "day_number": 2,
    "activities": [
      { "name": "Nahargarh Fort Sunset Point", "category": "sightseeing", "estimated_cost": 300, "duration_hours": 2.0, "time": "17:00" }
    ]
  }
  ```

---

## 6. Universal Global Search & Discovery Endpoints

### `GET /search?q={query}`
Universal omni-search returning categorized matches across Destinations, Curated Activities, Recommended Hotels, and Community Stories with rich metadata and direct modal deep links.

### `GET /destinations?q={query}&region={region}&style={style}`
Searches destination catalog with live filters.

### `GET /destinations/<id>`
Fetches destination metadata and list of curated experiences.

### `GET /activities?category={category}&city_id={city_id}`
Searches curated activities catalog.

### `GET /shared/<token>`
Unauthenticated public read-only itinerary snapshot.

### `POST /shared/<token>/copy`
Deep-clones the public shared itinerary into the logged-in caller's account.

---

## 7. Admin Intelligence & Management Endpoints (Role: `admin`)

### `GET /admin/analytics`
Returns real-time platform metrics: total users, total trips, average trip budget, top visited destination rankings, travel style distribution breakdown, and community engagement metrics.

### `GET /admin/users`
Returns complete user management table with traveler names, emails, roles, cities, countries, preferred currencies, travel styles, and trip creation counts.
