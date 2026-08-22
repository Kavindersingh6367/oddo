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
| `category` | `VARCHAR(50)` | `NOT NULL` | Category (`transportation`, `accommodation`, `food`, `miscellaneous`) |
| `name` | `VARCHAR(255)` | `NOT NULL` | Expense Description |
| `amount` | `NUMERIC(12,2)`| `DEFAULT 0.0` | Cost Amount |
