# GlobeTrotter — Test Plan & Quality Assurance Strategy

## 1. Test Strategy & Scope

The testing strategy validates all core tiers of GlobeTrotter:
1. **Relational Database Integrity**: Constraints, foreign key cascades, unique indexes, and defaults in PostgreSQL 17.
2. **Odoo Model & Business Logic**: Dynamic budget rollups, rule-based intelligence alerts, and travel balance scoring algorithms.
3. **Multi-Tenant Security & Isolation**: Record rules preventing cross-user data tampering.
4. **End-to-End User Flow**: Full acceptance test matching the hackathon prompt.

---

## 2. Test Cases Overview

| Test ID | Test Category | Target Component | Expected Result | Status |
|---|---|---|---|---|
| `TC-01` | Catalog Discovery | `/api/v1/destinations` | Seeded global cities (Delhi, Jaipur, Udaipur, Paris, Tokyo...) returned with accurate cost index & activity counts. | ✅ PASSED |
| `TC-02` | Authentication | `/api/v1/auth/*` | Signup, login, password validation, duplicate email rejection, session authorization. | ✅ PASSED |
| `TC-03` | Itinerary Builder | `/api/v1/trips` & stops | Create "Rajasthan Explorer", add Delhi, Jaipur, Udaipur stops, reorder stops sequence. | ✅ PASSED |
| `TC-04` | Activity Scheduling | `/api/v1/trips/*/activities` | Assign experiences to Day 1, Day 2, Day 3 with duration and costs. | ✅ PASSED |
| `TC-05` | Dynamic Budget Engine | Trip Computed Fields | Rollup total cost, cost per traveler, cost per day, remaining budget, budget utilization %. | ✅ PASSED |
| `TC-06` | Financial Intelligence | Rule-Based Alerts | Over-budget alerts, near-budget warnings, accommodation/transit dominance detection. | ✅ PASSED |
| `TC-07` | Travel Balance Score | Pacing Engine | 0-100 score factoring budget alignment, activity density, dwell time, and completeness. | ✅ PASSED |
| `TC-08` | Public Sharing | `/api/v1/shared/*` | Secure unguessable token generation and read-only snapshot retrieval. | ✅ PASSED |
| `TC-09` | 1-Click Trip Clone | `/api/v1/shared/*/copy` | Clones entire itinerary + child stops + activities + expenses into another user account. | ✅ PASSED |
| `TC-10` | Security & Isolation | Record Rules | User A cannot access, edit, or delete User B's private itinerary (HTTP 403 Forbidden). | ✅ PASSED |

---

## 3. Running Automated Tests

Execute the test suite against the live PostgreSQL-backed server:

```powershell
python tests/test_globetrotter.py
```

Result: `Ran 4 tests in 1.834s — OK (100% Passed)`.
