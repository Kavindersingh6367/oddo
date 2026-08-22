
# 🌍 GlobeTrotter

### Personalized Intelligent Travel Planning Platform

> **Odoo Hackathon Project**

GlobeTrotter is a modern, personalized travel-planning platform designed to simplify the process of planning and managing multi-city trips.

Instead of managing destinations, activities, schedules, and expenses across multiple applications, GlobeTrotter brings the complete travel-planning workflow into one intelligent platform.

---

## 🚀 Project Overview

GlobeTrotter enables travelers to:

* 🗺️ Create personalized multi-city trip
* 📍 Discover and manage destinations
* 🎯 Explore activities
* 📅 Build day-wise itineraries
* 💰 Track and calculate trip budgets
* 📊 Analyze expenses
* 🧠 Receive budget insights
* 📆 Visualize trips using calendar/timeline views
* 🔗 Share itineraries publicly
* 📋 Copy shared itineraries
* 👤 Manage personal travel preferences

The project is built with **Odoo as the core business and data platform**, using its ORM, PostgreSQL database, security system, models, controllers, and business logic.

---

# 🎯 Problem Statement

Planning a multi-city trip often requires managing information across multiple disconnected platforms.

Travelers typically need to separately manage:

* Destinations
* Travel dates
* Hotels
* Activities
* Transportation
* Food expenses
* Daily schedules
* Overall budgets
* Shared itineraries

This makes trip planning complicated, time-consuming, and difficult to maintain.

### GlobeTrotter solves this by providing a single platform where users can:

**Discover → Plan → Organize → Budget → Visualize → Share**

their entire journey.

---

# 💡 Our Solution

GlobeTrotter converts travel planning into a structured, interactive workflow.

### User Flow

```text
Create Account
      ↓
Dashboard
      ↓
Create Trip
      ↓
Discover Destinations
      ↓
Add Cities
      ↓
Build Itinerary
      ↓
Add Activities
      ↓
Manage Expenses
      ↓
Calculate Budget
      ↓
Calendar / Timeline
      ↓
Share Trip
```

---

# ✨ Key Features

## 🔐 Authentication

* User login
* User registration
* Session management
* Protected user data
* User-specific trips

---

## 🏠 Personalized Dashboard

The dashboard provides a central overview of the traveler's planning activity.

Includes:

* Upcoming trips
* Recent trips
* Trip statistics
* Budget summaries
* Recommended destinations
* Quick trip creation

---

## 🧳 Trip Management

Users can create and manage multiple trips.

Each trip can contain:

* Trip name
* Start date
* End date
* Description
* Cover image
* Number of travelers
* Travel style
* Currency
* Budget

Trips can be:

* Created
* Edited
* Viewed
* Duplicated
* Shared
* Deleted

---

## 🌎 Destination Discovery

Users can search and discover cities and destinations.

Destination information can include:

* City
* Country
* Region
* Description
* Cost index
* Popularity
* Recommended duration

Users can directly add destinations to their trips.

---

## 🗓️ Interactive Itinerary Builder

The itinerary builder is the core of GlobeTrotter.

Users can:

* Add cities
* Remove cities
* Reorder cities
* Assign dates
* Add activities
* Assign activities to days
* Add transportation
* Add accommodation
* Add meals
* Add miscellaneous expenses
* Add notes

Example:

```text
Day 1 — Delhi
 ├── Arrival
 ├── Hotel Check-in
 ├── India Gate
 └── Dinner

Day 2 — Delhi
 ├── Red Fort
 ├── Museum
 └── Local Market

Day 3 — Jaipur
 ├── Travel Delhi → Jaipur
 ├── Hotel Check-in
 └── City Palace
```

---

# 🎯 Activity Discovery

Activities can be explored by destination and category.

Supported categories include:

* 🏛️ Sightseeing
* 🍴 Food
* 🏔️ Adventure
* 🎭 Culture
* 🌳 Nature
* 🛍️ Shopping
* 🎵 Entertainment
* 🧘 Relaxation

Activity information includes:

* Name
* Description
* Category
* Duration
* Estimated cost
* Popularity

Activities added to an itinerary automatically contribute to the trip budget.

---

# 💰 Smart Budget Management

GlobeTrotter automatically calculates trip expenses.

### Expense Categories

* Transportation
* Accommodation
* Activities
* Food
* Miscellaneous

### Budget Analytics

The system calculates:

* Total estimated cost
* Cost per traveler
* Cost per day
* Cost per city
* Cost by category
* Remaining budget
* Budget utilization

Example:

```text
Trip Budget       ₹50,000
Estimated Cost    ₹42,500
Remaining         ₹7,500
Utilization       85%
```

---

# 🧠 Budget Intelligence

GlobeTrotter provides transparent rule-based travel insights.

For example:

```text
⚠️ Your trip is approximately ₹8,500 over budget.
```

or:

```text
💡 Day 4 is significantly above your daily average.
```

or:

```text
✓ Your current itinerary is within budget.
```

These insights are generated from actual itinerary and expense data rather than fabricated recommendations.

---

# 📊 Trip Balance Score

GlobeTrotter can calculate a transparent **Trip Balance Score** based on factors such as:

* Budget utilization
* Activity density
* Number of cities
* Travel duration
* Travel time

Example:

```text
Trip Balance Score
82 / 100
```

The score is explainable and based on measurable trip characteristics.

---

# 📅 Calendar & Timeline

Users can visualize their itinerary in multiple formats.

### Calendar View

Displays:

* Dates
* Cities
* Activities
* Times
* Costs

### Timeline View

Provides a chronological view of the entire journey.

```text
DAY 1
  ↓
Activity
  ↓
Activity
  ↓
Transport
  ↓
DAY 2
  ↓
Activity
```

---

# 🔗 Public Trip Sharing

Users can share their itinerary through a secure public link.

Example:

```text
/shared/<secure-token>
```

The public itinerary provides a read-only version of the trip.

Users can:

* Copy the link
* Share the trip
* View the itinerary
* Copy the itinerary into their own account

Private user information is not exposed.

---

# 👤 User Profile

Users can manage:

* Name
* Email
* Profile image
* Currency
* Language
* Travel preferences
* Saved destinations
* Account settings

---

# 📊 Admin Analytics

The platform can provide administrative insights such as:

* Total users
* Total trips
* Popular cities
* Popular activities
* Average trip budget
* Average trip duration
* Platform engagement

Administrative information is protected through Odoo access control.

---

# 🏗️ Technology Stack

## Backend

* **Odoo**
* **Python**
* **Odoo ORM**
* **PostgreSQL**

## Frontend

* Odoo Web Framework
* OWL where appropriate
* HTML
* CSS
* JavaScript

## Development

* Git
* GitHub
* Python
* Odoo Development Environment

---

# 🏛️ Architecture

GlobeTrotter follows a modular Odoo architecture.

```text
                    ┌─────────────────────┐
                    │      User / UI      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Odoo Web Layer    │
                    │ Controllers / OWL   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Business Logic   │
                    │    Odoo Models      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      Odoo ORM       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     PostgreSQL      │
                    └─────────────────────┘
```

---

# 🗄️ Data Model

The core relational structure includes:

```text
User
 │
 ├── Trips
 │     │
 │     ├── Trip Stops
 │     │      │
 │     │      └── City
 │     │
 │     ├── Trip Activities
 │     │      │
 │     │      └── Activity
 │     │
 │     ├── Expenses
 │     │
 │     └── Budget
 │
 ├── Saved Destinations
 │
 └── Shared Trips
```

### Core Odoo Models

```text
globetrotter.trip
globetrotter.trip.stop
globetrotter.city
globetrotter.activity
globetrotter.trip.activity
globetrotter.expense
globetrotter.budget
globetrotter.shared.trip
globetrotter.saved.destination
```

---

# 🔐 Security

GlobeTrotter uses Odoo's security architecture.

Security includes:

* Access Control Lists
* Record Rules
* User ownership validation
* Admin authorization
* Protected private trips
* Secure public share tokens
* Input validation

Users cannot access or modify another user's private trips.

---

# 📁 Project Structure

```text
oddo/
│
├── globetrotter/
│   ├── __init__.py
│   ├── __manifest__.py
│   │
│   ├── controllers/
│   │   ├── __init__.py
│   │   └── main.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── activity.py
│   │   ├── city.py
│   │   ├── expense.py
│   │   ├── res_users.py
│   │   ├── saved_destination.py
│   │   ├── shared_trip.py
│   │   ├── trip.py
│   │   ├── trip_activity.py
│   │   └── trip_stop.py
│   │
│   ├── security/
│   │   ├── globetrotter_security.xml
│   │   └── ir.model.access.csv
│   │
│   ├── views/
│   │   ├── activity_views.xml
│   │   ├── city_views.xml
│   │   ├── expense_views.xml
│   │   ├── menu_views.xml
│   │   └── trip_views.xml
│   │
│   └── data/
│       └── seed_data.py
│
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── app.js
│   └── index.html
│
├── tests/
│   ├── __init__.py
│   └── test_globetrotter.py
│
├── database.py
├── server.py
└── README.md
```

---

# ⚙️ Installation

## 1. Clone the repository

```bash
git clone https://github.com/Kavindersingh6367/oddo.git
```

```bash
cd oddo
```

## 2. Create a virtual environment

Windows:

```powershell
python -m venv .venv
```

Activate:

```powershell
.venv\Scripts\activate
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

# 3. Install Dependencies

Install the dependencies required by the project/environment.

```bash
pip install -r requirements.txt
```

If `requirements.txt` is not yet present, install the dependencies specified by the project's Odoo environment and configuration.

---

# 4. Configure PostgreSQL

Create/configure the PostgreSQL database required by your Odoo environment.

Make sure the database credentials and configuration match the project configuration.

Do not commit database passwords or secrets to GitHub.

---

# 5. Run the Application

Start the Odoo/application server using the command configured for the project.

For example:

```bash
python server.py
```

Use the project's actual Odoo startup configuration if it differs.

---

# 🧪 Testing

Run the project's test suite using the configured Odoo/Python test environment.

Example:

```bash
python -m pytest
```

The test suite covers important application behavior such as:

* Trip operations
* Budget calculations
* Activities
* Data relationships
* Security behavior

---

# 🎬 Hackathon Demo Flow

The recommended demonstration scenario is:

### 1. Dashboard

Show the personalized travel dashboard.

### 2. Create Trip

Create:

```text
Rajasthan Explorer
```

Budget:

```text
₹35,000
```

Travelers:

```text
2
```

### 3. Add Destinations

```text
Delhi → Jaipur → Udaipur
```

### 4. Add Activities

Add sightseeing, food and cultural activities.

### 5. Budget

Show the automatically calculated:

* Total cost
* Category breakdown
* Daily cost
* Remaining budget
* Budget utilization

### 6. Intelligence

Show the budget insight/warning.

### 7. Timeline

Open the day-wise itinerary.

### 8. Share

Generate the public itinerary.

### 9. Copy

Copy the shared itinerary into another account.

---

# 🏆 Why GlobeTrotter?

GlobeTrotter combines travel planning and business-data management into a single platform.

Instead of treating travel planning as a collection of disconnected screens, GlobeTrotter models the complete travel journey as connected business data:

```text
Traveler
   ↓
Trip
   ↓
Cities
   ↓
Activities
   ↓
Expenses
   ↓
Budget
   ↓
Insights
   ↓
Shareable Itinerary
```

This makes the system:

* Structured
* Extensible
* Data-driven
* Secure
* Maintainable
* Suitable for future integrations

---

# 🚀 Future Improvements

Potential future enhancements include:

* AI-powered itinerary generation
* Weather-aware itinerary adjustments
* Hotel recommendations
* Flight/transport integration
* Real-time travel pricing
* Map integration
* Collaborative trip planning
* Expense splitting
* Currency conversion
* Personalized recommendation engine
* Mobile application
* Advanced travel analytics

---

# 👥 Team

**GlobeTrotter — Odoo Hackathon Project**

Built with ❤️ for the Odoo Hackathon.

---

# 📜 License

This project is developed as a hackathon project.

Add the appropriate license before public production/commercial use.
=======
# GlobeTrotter — Empowering Personalized Travel Planning

> **Built for Odoo Hackathon**  
> An end-to-end, production-grade travel planning platform featuring multi-city itineraries, curated activity discovery, dynamic budgeting engine, rule-based travel intelligence, interactive calendar/timeline views, secure public sharing, and 1-click trip duplication.

---

## 🌟 Key Features

1. **Multi-City Itinerary Builder (Central Feature)**
   - Add, remove, and reorder destination cities with sequence optimization.
   - Day-by-day scheduling with time slots, categories, durations, and costs.
   - Associated destination stops and stay notes.

2. **Curated Destination & Activity Discovery**
   - Rich seed catalog: Delhi, Jaipur, Udaipur, Mumbai, Goa, Bengaluru, Paris, London, Tokyo, Dubai, Singapore.
   - Filter by Region, Travel Style, Popularity, and Cost Index ($ – $$$$$).
   - Instant "+ Add to Itinerary" integration.

3. **Dynamic Budget Engine & Rule-Based Intelligence**
   - Real-time rollup of total estimated cost, cost per traveler, and cost per day.
   - Categorized cost breakdowns: Transportation, Accommodation, Activities, Food, Miscellaneous.
   - Transparent Rule-Based Alerts:
     - Over-budget warnings with exact overrun amount.
     - Dominant category warnings (e.g. accommodation $\ge 40\%$).
     - High spending day outlier detection.
     - Healthy budget affirmations.

4. **Travel Balance Score (0 – 100)**
   - Multi-factor evaluation engine:
     - **Budget Discipline (30 pts)**
     - **Activity Density & Pacing (25 pts)**
     - **City Dwell Time & Travel Overhead (25 pts)**
     - **Itinerary Completeness (20 pts)**
   - Transparent breakdown modal explaining each factor.

5. **Multi-View Experience**
   - **Itinerary Builder**: Day-by-day activity cards with edit/delete actions.
   - **Calendar View**: Interactive monthly/weekly grid with daily cost badges.
   - **Vertical Timeline View**: Continuous journey nodes connecting days and transit.
   - **Presentation Mode**: Clean executive showcase layout designed for live demos.

6. **Secure Public Sharing & 1-Click Itinerary Duplication**
   - Secure unguessable token generation (`/shared/<token>`).
   - Read-only public preview with optional budget visibility toggle.
   - **"Copy Trip to My Account"**: Clones master trip + child stops + activities + expenses into the caller's account with new relational IDs.

7. **Odoo 17 Domain Architecture & Security**
   - Normalized relational schema in PostgreSQL 17.
   - Models: `globetrotter.trip`, `globetrotter.trip.stop`, `globetrotter.city`, `globetrotter.activity`, `globetrotter.trip.activity`, `globetrotter.expense`, `globetrotter.shared.trip`, `globetrotter.saved.destination`, `res.users`.
   - Record Rules & ACLs enforcing strict multi-tenant isolation.
   - Odoo XML Views: Trees, Forms, Kanban, Calendar, Graph, Pivot, and Menus.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Backend & ORM** | Python 3.10+, Odoo 17 Model & Security Architecture |
| **Database** | PostgreSQL 17 (`globetrotter_db`), Relational Schema with Foreign Keys & Cascades |
| **Authentication** | Cryptographic token sessions with PBKDF2-SHA256 password hashing |
| **Frontend** | Vanilla HTML5 & CSS3 Design System (Deep Purple/Indigo `#4F46E5` & Warm Coral `#F97316`), Responsive SPA |
| **Testing** | Automated Python test suite with unit, integration, and security tests |

---

## 🚀 Installation & Running Locally

### 1. Prerequisites
- Python 3.10+
- PostgreSQL 17 running on `localhost:5432` with user `postgres`

### 2. Install Dependencies
```powershell
pip install psycopg2-binary passlib reportlab polib xlsxwriter pydot pyopenssl cryptography requests
```

### 3. Initialize Database & Run Server
```powershell
python server.py
```
The application will automatically:
1. Create `globetrotter_db` schema, tables, constraints, and indexes in PostgreSQL.
2. Populate rich seed destinations and activities.
3. Start the server at `http://127.0.0.1:8069`.

---

## 🧪 Running Automated Tests

Run the complete test suite:
```powershell
python tests/test_globetrotter.py
```
**Test Coverage**:
- Destination catalog & seed verification
- User registration, login, and duplicate rejection
- Acceptance Test Workflow: "Rajasthan Explorer" creation, stops, activity scheduling, expenses, dynamic budget rollup, intelligence alerts, balance score, public sharing, and trip cloning
- Security multi-tenancy & record rule isolation

---

## 📋 Hackathon Demo Credentials

| Role | Email | Password | Quick Action |
|---|---|---|---|
| **Demo Traveler** | `demo@globetrotter.travel` | `demo123` | Click **"1-Click Demo Traveler"** on homepage |
| **Administrator** | `admin@globetrotter.travel` | `admin123` | Click **"1-Click Admin Demo"** on homepage |

