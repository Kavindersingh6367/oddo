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
