# GlobeTrotter — Database Design & Domain Model

## 1. Relational Schema Diagram (PostgreSQL 17)

```
       +-----------------------+              +--------------------------+
       |       res_users       |              |    globetrotter_city     |
       +-----------------------+              +--------------------------+
       | id (PK)               |<---\         | id (PK)                  |<----\
       | name                  |     \        | name                     |      \
       | email (UNIQUE)        |      \       | country                  |       \
       | password_hash         |       \      | region                   |        \
       | preferred_currency    |        \     | cost_index               |         \
       | preferred_travel_style|         \    | popularity               |          \
       | role                  |          \   | recommended_duration_days|           \
       +-----------------------+           \  | cover_image              |            \
                   |                        \ | travel_styles            |             \
                   | 1:N                     \+--------------------------+              \
                   ▼                          \     | 1:N                                \
       +-----------------------+               \    ▼                                     \
       |   globetrotter_trip   |                \ +----------------------+                 \
       +-----------------------+                 \|globetrotter_activity |                  \
       | id (PK)               |                  +----------------------+                   \
       | user_id (FK)          |                  | id (PK)              |                    \
       | name                  |                  | city_id (FK)         |                     \
       | start_date            |                  | name                 |                      \
       | end_date              |                  | category             |                       \
       | total_budget          |                  | duration_hours       |                        \
       | travelers_count       |                  | estimated_cost       |                         \
       | currency              |                  | popularity           |                          \
       | travel_style          |                  +----------------------+                           \
       | share_token (UNIQUE)  |                             | 1:N (optional)                         \
       | is_public             |                             ▼                                         \
       +-----------------------+                  +---------------------------+                         \
          | 1:N           | 1:N                   |globetrotter_trip_activity |                          \
          |               |                       +---------------------------+                           \
          ▼               ▼                       | id (PK)                   |                            \
  +---------------+  +--------------------+       | trip_id (FK)              |                             \
  |globetrotter_  |  |globetrotter_expense|       | stop_id (FK)              |                              \
  |trip_stop      |  +--------------------+       | activity_id (FK nullable) |                               \
  +---------------+  | id (PK)            |       | name                      |                                \
  | id (PK)       |  | trip_id (FK)       |       | category                  |                                 \
  | trip_id (FK)  |  | stop_id (FK)       |       | day_number                |                                  \
  | city_id (FK)  |--| category           |       | scheduled_time            |                                   \
  | sequence      |  | name               |       | duration_hours            |                                    \
  | arrival_date  |  | amount             |       | estimated_cost            |                                     \
  | departure_date|  | date               |       +---------------------------+                                      \
  | notes         |  | notes              |                                                                           \
  +---------------+  +--------------------+                                                                            \
          |                                                                                                             \
          \-------------------------------------------------------------------------------------------------------------/
```

---

## 2. Table Specifications

### 2.1 `res_users` (Traveler & Administrator Accounts)
| Field | Type | Modifiers | Description |
|---|---|---|---|
| `id` | `SERIAL` | `PRIMARY KEY` | Unique User ID |
| `name` | `VARCHAR(255)` | `NOT NULL` | Full Name |
| `email` | `VARCHAR(255)` | `UNIQUE, NOT NULL` | Login Identifier |
| `password_hash` | `VARCHAR(255)` | `NOT NULL` | PBKDF2-SHA256 Hash |
| `preferred_currency` | `VARCHAR(10)` | `DEFAULT 'INR'` | User currency preference |
| `preferred_travel_style`| `VARCHAR(50)` | `DEFAULT 'balanced'` | Default trip style |
| `role` | `VARCHAR(50)` | `DEFAULT 'traveler'` | Role (`traveler` or `admin`) |

### 2.2 `globetrotter_city` (Global Destinations)
| Field | Type | Modifiers | Description |
|---|---|---|---|
| `id` | `SERIAL` | `PRIMARY KEY` | Unique City ID |
| `name` | `VARCHAR(255)` | `NOT NULL` | City Name |
| `country` | `VARCHAR(255)` | `NOT NULL` | Country Name |
| `region` | `VARCHAR(50)` | `NOT NULL` | Geographic Region |
| `cost_index` | `INT` | `DEFAULT 2` | Cost Level (1-5) |
| `popularity` | `INT` | `DEFAULT 80` | Popularity Score (1-100) |
| `recommended_duration_days`| `INT` | `DEFAULT 3` | Suggested stay duration |
| `cover_image` | `TEXT` | | Curated destination imagery |

### 2.3 `globetrotter_trip` (Master Itinerary)
| Field | Type | Modifiers | Description |
|---|---|---|---|
| `id` | `SERIAL` | `PRIMARY KEY` | Unique Trip ID |
| `user_id` | `INT` | `REFERENCES res_users(id) ON DELETE CASCADE` | Trip Owner |
| `name` | `VARCHAR(255)` | `NOT NULL` | Itinerary Title |
| `start_date` | `DATE` | `NOT NULL` | Journey Start Date |
| `end_date` | `DATE` | `NOT NULL` | Journey End Date |
| `total_budget` | `NUMERIC(14,2)`| `DEFAULT 0.0` | Target Budget |
| `travelers_count` | `INT` | `DEFAULT 1` | Party Size |
| `currency` | `VARCHAR(10)` | `DEFAULT 'INR'` | Currency Symbol |
| `share_token` | `VARCHAR(100)` | `UNIQUE` | Public Sharing Token |
| `is_public` | `BOOLEAN` | `DEFAULT FALSE` | Public Sharing Enabled |

### 2.4 `globetrotter_trip_stop` (Route Sequence)
| Field | Type | Modifiers | Description |
|---|---|---|---|
| `id` | `SERIAL` | `PRIMARY KEY` | Unique Stop ID |
| `trip_id` | `INT` | `REFERENCES globetrotter_trip(id) ON DELETE CASCADE` | Parent Trip |
| `city_id` | `INT` | `REFERENCES globetrotter_city(id) ON DELETE RESTRICT` | Destination |
| `sequence` | `INT` | `DEFAULT 10` | Route Order Sequence |
| `arrival_date` | `DATE` | `NOT NULL` | Arrival Date |
| `departure_date` | `DATE` | `NOT NULL` | Departure Date |
| `duration_days` | `INT` | `DEFAULT 1` | Computed Stay Days |

### 2.5 `globetrotter_trip_activity` (Scheduled Experiences)
| Field | Type | Modifiers | Description |
|---|---|---|---|
| `id` | `SERIAL` | `PRIMARY KEY` | Scheduled Activity ID |
| `trip_id` | `INT` | `REFERENCES globetrotter_trip(id) ON DELETE CASCADE` | Parent Trip |
| `stop_id` | `INT` | `REFERENCES globetrotter_trip_stop(id) ON DELETE CASCADE`| Destination Stop |
| `day_number` | `INT` | `DEFAULT 1` | Day in Schedule |
| `scheduled_time`| `VARCHAR(20)` | `DEFAULT '10:00'` | Scheduled Time Slot |
| `name` | `VARCHAR(255)` | `NOT NULL` | Activity Name |
| `category` | `VARCHAR(50)` | `DEFAULT 'sightseeing'` | Category Type |
| `estimated_cost`| `NUMERIC(12,2)`| `DEFAULT 0.0` | Cost in Trip Currency |

### 2.6 `globetrotter_expense` (Logistics & Costs)
| Field | Type | Modifiers | Description |
|---|---|---|---|
| `id` | `SERIAL` | `PRIMARY KEY` | Expense ID |
| `trip_id` | `INT` | `REFERENCES globetrotter_trip(id) ON DELETE CASCADE` | Parent Trip |
| `stop_id` | `INT` | `REFERENCES globetrotter_trip_stop(id) ON DELETE SET NULL`| Optional Link to Stop |
| `category` | `VARCHAR(50)` | `NOT NULL` | Category (`transportation`, `accommodation`, `food`, `miscellaneous`) |
| `name` | `VARCHAR(255)` | `NOT NULL` | Expense Description |
| `amount` | `NUMERIC(12,2)`| `DEFAULT 0.0` | Cost Amount |
| `date` | `DATE` | | Incurred Date |
| `notes` | `TEXT` | | Optional notes |

### 2.7 `globetrotter_hotel` (Curated Hotel Catalog)
| Field | Type | Modifiers | Description |
|---|---|---|---|
| `id` | `SERIAL` | `PRIMARY KEY` | Unique Hotel ID |
| `name` | `VARCHAR(255)` | `NOT NULL` | Hotel Name |
| `city_id` | `INT` | `REFERENCES globetrotter_city(id) ON DELETE CASCADE` | Destination City |
| `description` | `TEXT` | | Property description |
| `address` | `VARCHAR(255)` | | Street Address / Landmark |
| `latitude` | `NUMERIC(9,6)` | | Geo Coordinates |
| `longitude` | `NUMERIC(9,6)` | | Geo Coordinates |
| `image` | `TEXT` | | Primary photo URL |
| `rating` | `NUMERIC(3,2)` | `DEFAULT 4.5` | Verified guest rating (1.0 - 5.0) |
| `review_count` | `INT` | `DEFAULT 100` | Number of verified reviews |
| `price_per_night` | `NUMERIC(12,2)`| `NOT NULL` | Nightly standard room rate |
| `currency` | `VARCHAR(10)` | `DEFAULT 'INR'` | Hotel base currency |
| `hotel_category`| `VARCHAR(50)` | `DEFAULT 'mid_range'` | Tier (`budget`, `economy`, `mid_range`, `premium`, `luxury`) |
| `amenities` | `TEXT` | | Comma-separated amenity tags |
| `room_types` | `TEXT` | | Available room configurations |
| `max_guests` | `INT` | `DEFAULT 2` | Max capacity per room |
| `location_score` | `NUMERIC(3,1)`| `DEFAULT 9.0` | Proximity index (0.0 - 10.0) |
| `cleanliness_score`| `NUMERIC(3,1)`| `DEFAULT 9.0` | Hygiene rating (0.0 - 10.0) |
| `service_score` | `NUMERIC(3,1)`| `DEFAULT 9.0` | Staff service rating (0.0 - 10.0) |
| `value_score` | `NUMERIC(3,1)`| `DEFAULT 9.0` | Price/value index (0.0 - 10.0) |
| `popularity_score`| `INT` | `DEFAULT 80` | Booking demand index (0 - 100) |
| `active` | `BOOLEAN` | `DEFAULT TRUE` | Catalog active flag |

### 2.8 `globetrotter_trip_hotel` (Trip Accommodation Reservations)
| Field | Type | Modifiers | Description |
|---|---|---|---|
| `id` | `SERIAL` | `PRIMARY KEY` | Unique Booking ID |
| `trip_id` | `INT` | `REFERENCES globetrotter_trip(id) ON DELETE CASCADE` | Parent Trip |
| `hotel_id` | `INT` | `REFERENCES globetrotter_hotel(id) ON DELETE RESTRICT`| Selected Hotel |
| `stop_id` | `INT` | `REFERENCES globetrotter_trip_stop(id) ON DELETE CASCADE`| Destination Stop |
| `expense_id` | `INT` | `REFERENCES globetrotter_expense(id) ON DELETE SET NULL`| Linked Expense Record |
| `check_in` | `DATE` | `NOT NULL` | Check-in Date |
| `check_out` | `DATE` | `NOT NULL` | Check-out Date |
| `number_of_nights`| `INT` | `DEFAULT 1` | Duration of Stay |
| `number_of_guests`| `INT` | `DEFAULT 2` | Number of Guests |
| `number_of_rooms` | `INT` | `DEFAULT 1` | Rooms Reserved |
| `price_per_night` | `NUMERIC(12,2)`| `NOT NULL` | Locked Nightly Rate |
| `total_cost` | `NUMERIC(12,2)`| `NOT NULL` | Computed Total (`price * nights * rooms`) |
| `room_type_selected`| `VARCHAR(100)`| `DEFAULT 'Standard Double Room'` | Room Configuration |
| `notes` | `TEXT` | | Special Requests |
| `status` | `VARCHAR(50)` | `DEFAULT 'selected'` | Status (`selected`, `confirmed`, `cancelled`) |

