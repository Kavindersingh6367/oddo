# GlobeTrotter — Test Plan & Quality Assurance Strategy

## 1. Test Strategy & Scope

The automated test suite in [`tests/test_globetrotter.py`](file:///d:/oddo/tests/test_globetrotter.py) comprehensively validates all functional tiers of GlobeTrotter:
1. **Relational Database Integrity**: Constraints, foreign key cascades, unique indexes, and schema migrations in PostgreSQL 17.
2. **Odoo Model & Business Logic**: Dynamic budget rollups, rule-based intelligence alerts, and travel balance scoring algorithms.
3. **Multi-Tenant Security & Isolation**: Record rules preventing cross-user data tampering.
4. **Hotel Recommendation Engine**: 7-factor scoring, comparison matrix, and automatic expense syncing.
5. **Differentiating Innovation Engines**: Travel DNA profiling, Trip Health 0–100 scoring, Smart Balancing, Community 1-Click Import, Global Search, and Protected Admin Analytics.

---

## 2. Test Cases Overview (13 / 13 PASSED)

| Test ID | Test Category | Target Component | Description & Expected Result | Status |
|---|---|---|---|---|
| `TC-01` | Catalog Discovery | `/api/v1/destinations` | Seeded global cities (Delhi, Jaipur, Udaipur, Paris, Tokyo...) returned with accurate cost index & activity counts. | ✅ PASSED |
| `TC-02` | Authentication & CRUD | `/api/v1/auth/*` | Full signup, login, session validation, duplicate email rejection, and demo login. | ✅ PASSED |
| `TC-03` | Multi-City Itinerary | `/api/v1/trips` & stops | Create "Rajasthan Explorer", add Delhi, Jaipur, Udaipur stops, reorder stops sequence. | ✅ PASSED |
| `TC-04` | Activity Scheduling | `/api/v1/trips/*/activities` | Assign experiences to Day 1, Day 2, Day 3 with duration, category, and cost. | ✅ PASSED |
| `TC-05` | Dynamic Budget Engine | Trip Computed Fields | Dynamic rollups: total cost, cost per traveler, cost per day, remaining budget, and utilization %. | ✅ PASSED |
| `TC-06` | Public Sharing & Clone | `/api/v1/shared/*` | Generates secure unguessable token, read-only snapshot retrieval, and deep-clone into another account. | ✅ PASSED |
| `TC-07` | Security & Isolation | Record Rules | User A cannot access, edit, or delete User B's private itinerary (HTTP 403 Forbidden). | ✅ PASSED |
| `TC-08` | Hotel Engine & Booking | `/api/v1/hotels/*` | 7-factor scoring (0–100), comparison matrix, reservation booking, auto-expense creation, and cascade delete. | ✅ PASSED |
| `TC-09` | Multi-City Hotel Workflow | 3-City Stays | Validates hotel stays booked across all stops, stay modifications, and trip duplication with bookings. | ✅ PASSED |
| `TC-10` | Travel DNA Engine | `/api/v1/user/travel-dna` | Validates 7-factor dimensional radar calculation, persona title, and insights list generation. | ✅ PASSED |
| `TC-11` | Trip Health & Diagnostics | `/api/v1/trips/<id>` | 0–100 multi-factor health score assessing Budget Discipline, Activity Load, Pacing, and Stay Coverage. | ✅ PASSED |
| `TC-12` | Smart Balancing Engine | `/api/v1/trips/<id>/balance` | Detects overloaded day (>8 hrs) and successfully shifts activities to an underloaded day via 1-click balancing. | ✅ PASSED |
| `TC-13` | Community Hub & Import | `/api/v1/community/*` | Tests community post querying, likes/saves interaction, and 1-Click Import into user itinerary. | ✅ PASSED |
| `TC-14` | Universal Global Search | `/api/v1/search?q={query}` | Validates omni-search matching across destinations, activities, hotels, and community stories. | ✅ PASSED |
| `TC-15` | Admin Intelligence & Users | `/api/v1/admin/*` | Validates 403 Forbidden for travelers and 200 OK for admins returning platform analytics and user table. | ✅ PASSED |

---

## 3. Running Automated Tests

Execute the automated test suite against the live backend:

```powershell
python -m unittest tests/test_globetrotter.py
```

### Test Execution Result:
```
Ran 13 tests in 5.741s

OK (13/13 Passed)
```
