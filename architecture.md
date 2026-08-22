# GlobeTrotter — Architecture Documentation

## 1. System Overview

GlobeTrotter is an enterprise-ready, personalized travel-planning platform architected specifically for the **Odoo Hackathon**. It combines Odoo relational domain modeling, PostgreSQL 17 persistence, dynamic budget calculation rollups, rule-based travel intelligence, and a high-performance modern web interface.

```
+---------------------------------------------------------------------------------------------------+
|                                       GLOBETROTTER PLATFORM                                       |
+---------------------------------------------------------------------------------------------------+
|  Frontend Client Layer (HTML5, Vanilla CSS Design System, Responsive SPA Architecture)            |
|  - Modern Visual Hierarchy (Deep Purple/Indigo #4F46E5 & Warm Coral #F97316)                      |
|  - Multi-City Route Sequence Rail with Dynamic Reordering                                         |
|  - Day-by-Day Activity Scheduling and Curated Experience Discovery                                |
|  - Real-Time Budget Engine, Category Distribution, and Rule-Based Financial Intelligence          |
|  - Interactive Travel Balance Score Gauge (0-100) with Factor Decomposition                        |
|  - Dual View Modes: Interactive Monthly/Weekly Calendar Grid & Vertical Journey Timeline          |
|  - Presentation Showcase Mode (for live Hackathon Demos)                                          |
|  - Secure Public Share Viewer (/shared/<token>) & 1-Click Itinerary Duplication                   |
+---------------------------------------------------------------------------------------------------+
                                            │ HTTP / JSON-RPC / REST API
                                            ▼
+---------------------------------------------------------------------------------------------------+
|  Odoo Module & Controller Layer (globetrotter/)                                                   |
|  - __manifest__.py (Odoo 17 app declaration, security, data, views)                               |
|  - Controllers: /api/v1/auth, /api/v1/trips, /api/v1/destinations, /api/v1/shared, /api/v1/admin  |
|  - Access Control Lists (security/ir.model.access.csv)                                            |
|  - Record Rules (security/globetrotter_security.xml) for Multi-Tenant Isolation                   |
|  - XML Views: Forms, Trees, Kanban, Calendar, Graph/Pivot, Menus                                  |
+---------------------------------------------------------------------------------------------------+
                                            │ ORM Model Layer
                                            ▼
+---------------------------------------------------------------------------------------------------+
|  Relational Domain Models & Business Logic (PostgreSQL 17)                                        |
|  - res.users (Travel preferences, currency, role, password hashing)                               |
|  - globetrotter.city (Destinations, cost index, popularity, coordinates, travel styles)           |
|  - globetrotter.activity (Curated catalog experiences, category, duration, cost)                  |
|  - globetrotter.trip (Itinerary root, computed budget, balance score, intelligence alerts)        |
|  - globetrotter.trip.stop (Relational stops, sequence, arrival/departure dates)                   |
|  - globetrotter.trip.activity (Scheduled stop activities, day assignment, time slots)             |
|  - globetrotter.expense (Categorized logistics: stay, transit, food, misc)                        |
|  - globetrotter.shared.trip (Public unguessable secure tokens, analytics tracking)                |
|  - globetrotter.saved.destination (User destination bookmarks)                                    |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Component Design

### 2.1 Backend Runtime & Odoo Compatibility
* **Server**: Asynchronous WSGI/HTTP server running against PostgreSQL 17 (`globetrotter_db`).
* **Session Management**: Cryptographically secure token sessions with `pbkdf2_sha256` password hashing.
* **Multi-Tenant Security**: Record rules ensure users can only access their own private itineraries (`user_id = current_user.id`). Public access is strictly isolated to itineraries with `is_public = True` referenced by secure unguessable tokens.

### 2.2 Business Logic & Computed Fields
1. **Dynamic Budget Rollup**:
   $$\text{Total Cost} = \sum \text{Activity Costs} + \sum \text{Expenses}$$
   $$\text{Cost Per Traveler} = \frac{\text{Total Cost}}{\text{Travelers Count}}$$
   $$\text{Cost Per Day} = \frac{\text{Total Cost}}{\text{Duration Days}}$$
   $$\text{Utilization \%} = \frac{\text{Total Cost}}{\text{Total Budget}} \times 100$$

2. **Transparent Rule-Based Budget Intelligence**:
   - **Over-Budget Warning**: Triggered when $\text{Total Cost} > \text{Total Budget}$, calculating exact overrun.
   - **Near-Budget Warning**: Triggered when remaining budget is $\le 10\%$ of total budget.
   - **Category Dominance**: Alerts traveler when accommodation ($\ge 40\%$) or transportation ($\ge 35\%$) commands a disproportionate share of spending.
   - **Daily Spending Outliers**: Identifies single days whose activity density exceeds $2\times$ the daily average.

3. **Travel Balance Score (0 - 100)**:
   - **Budget Discipline (30 pts)**: Evaluates utilization alignment against target.
   - **Activity Density (25 pts)**: Rewards balanced pacing (1.5 - 4.0 activities/day) while penalizing traveler fatigue.
   - **City Dwell Time (25 pts)**: Evaluates time spent per destination vs inter-city travel overhead.
   - **Itinerary Completeness (20 pts)**: Rewards scheduling completeness across stops, activities, and logistics.

---

## 3. Security Architecture

1. **Access Control Lists (ACL)**:
   - `globetrotter.city`: Read-only for standard users, Full CRUD for managers.
   - `globetrotter.trip`: Full CRUD for trip owners.
   - `globetrotter.trip.stop`, `globetrotter.trip.activity`, `globetrotter.expense`: Cascading ownership from parent trip.
2. **Record Rules**:
   - `rule_globetrotter_trip_user`: `['|', ('user_id', '=', user.id), ('is_public', '=', True)]`
   - `rule_globetrotter_trip_manager`: `[(1, '=', 1)]`
3. **Public Sharing Security**:
   - Public URLs use high-entropy random tokens (`secrets.token_urlsafe(16)`).
   - Sensitive user information and private trips are completely inaccessible via enumeration.
