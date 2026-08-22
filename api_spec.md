# GlobeTrotter — REST & JSON-RPC API Specification

Base URL: `http://127.0.0.1:8069/api/v1`

---

## 1. Authentication Endpoints

### `POST /auth/signup`
Creates a new user account.
* **Request Body**:
  ```json
  {
    "name": "Rohan Sharma",
    "email": "rohan@example.com",
    "password": "secretPassword123",
    "preferred_currency": "INR",
    "preferred_travel_style": "balanced"
  }
  ```
* **Response (200 OK)**:
  ```json
  {
    "success": true,
    "token": "a49f82e1c9...",
    "user": { "id": 1, "name": "Rohan Sharma", "email": "rohan@example.com" }
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
    "user": { "id": 1, "name": "Rohan Sharma", "email": "rohan@example.com" }
  }
  ```

### `POST /auth/demo-login`
Fast 1-click login for Hackathon presentation.
* **Request Body**: `{"role": "traveler"}` or `{"role": "admin"}`

### `GET /auth/me`
Fetches authenticated user profile and preferences.

---

## 2. Trips Endpoints

### `GET /trips?status={all|upcoming|ongoing|completed|draft}`
Lists all trips owned by the authenticated user with real-time computed budget rollup and balance scores.

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
Retrieves full itinerary details: stops, day-by-day scheduled activities, expenses, budget rollup, intelligence alerts, and balance score.

### `PUT /trips/<id>`
Updates trip metadata, dates, or target budget.

### `DELETE /trips/<id>`
Deletes trip and cascades deletion to all associated stops, activities, and expenses.

### `POST /trips/<id>/duplicate`
Deep-clones the entire trip including all child stops, activities, and expenses with new relational IDs.

### `POST /trips/<id>/share`
Generates/toggles secure public sharing link.
* **Request Body**: `{"is_public": true, "share_budget": true}`
* **Response**: `{"share_token": "V4xy3PQT...", "share_url": "/shared/V4xy3PQT..."}`

---

## 3. Stops & Activity Endpoints

### `POST /trips/<id>/stops`
Adds a destination stop to the trip.

### `POST /trips/<id>/stops/reorder`
Reorders sequence of stops in the route.
* **Request Body**: `{"stop_ids": [12, 14, 13]}`

### `POST /trips/<id>/activities`
Schedules an activity to a specific day number and stop.

### `PUT /trips/<id>/activities/<act_id>`
Modifies activity time slot, day assignment, duration, or cost.

### `DELETE /trips/<id>/activities/<act_id>`
Removes scheduled activity.

### `POST /trips/<id>/expenses`
Logs transportation, accommodation, meal, or miscellaneous expense.

---

## 4. Discovery & Sharing Endpoints

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

## 5. Hotel Recommendation & Accommodations Endpoints

### `GET /hotels/recommendations?city_id={id}&trip_id={id}&check_in={date}&check_out={date}&guests={n}&rooms={n}&category={cat}&min_rating={r}&min_price={p}&max_price={p}&amenities={wifi,pool}&sort_by={sort}`
Searches and scores hotel recommendations with transparent 0–100 matching engine, dynamic badges (`🏆 Best Overall`, `💰 Best Budget`, etc.), budget fit flags, and "Why this hotel?" data-driven explanations.
* **Response (200 OK)**:
  ```json
  {
    "success": true,
    "hotels": [
      {
        "id": 1,
        "name": "Pearl Palace Heritage Boutique",
        "hotel_category": "mid_range",
        "rating": 4.8,
        "review_count": 850,
        "price_per_night": 2900.0,
        "recommendation_score": 96,
        "match_tier": "Excellent Match",
        "primary_badge": { "label": "🏆 Best Overall", "class": "badge-best-overall" },
        "fits_budget": true,
        "total_stay_cost": 5800.0,
        "why_points": [
          "Fits within your remaining trip budget (₹28,000 available).",
          "4.8/5.0 guest rating with 850 verified traveler reviews.",
          "Outstanding location score of 9.5/10 with easy access to city attractions."
        ]
      }
    ]
  }
  ```

### `GET /hotels/<id>`
Retrieves single hotel details, sub-ratings (location, cleanliness, service, value), room types, and amenities.

### `GET /hotels/compare?ids={id1,id2,id3}&trip_id={id}&nights={n}&rooms={n}`
Returns side-by-side comparison matrix for 2–3 hotels with price rollups and quality sub-scores.

### `POST /trips/<trip_id>/hotels`
Adds/books a hotel stay for a specific trip stop. Automatically creates a linked `accommodation` expense in `globetrotter_expense` and updates total cost and remaining budget.
* **Request Body**:
  ```json
  {
    "hotel_id": 1,
    "stop_id": 4,
    "check_in": "2026-10-03",
    "check_out": "2026-10-05",
    "number_of_guests": 2,
    "number_of_rooms": 1,
    "room_type_selected": "Deluxe Heritage Room",
    "notes": "Late check-in requested"
  }
  ```

### `PUT /trips/<trip_id>/hotels/<booking_id>`
Modifies hotel reservation (dates, rooms, guests, room type) and automatically recalculates total cost and linked accommodation expense.

### `DELETE /trips/<trip_id>/hotels/<booking_id>`
Removes hotel reservation and deletes linked accommodation expense, restoring trip budget.

