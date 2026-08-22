# GlobeTrotter — 3-Minute Live Hackathon Demo Script

This script walks through the complete end-to-end user story optimized for a live hackathon evaluation.

---

## ⏱️ Step 1: Introduction & Dashboard (0:00 – 0:30)

1. Open `http://127.0.0.1:8069`.
2. Highlight the **Modern Travel SaaS UI** (Deep Purple/Indigo `#4F46E5` palette, Glassmorphism, Warm Coral accents).
3. Click **"1-Click Demo Traveler"** on the hero banner to instantly log in as Rohan Sharma.
4. Show the **Dashboard**: KPI summary cards (Total Itineraries, Active Trips, Total Trip Budgets, Next Destination), and Trending Destinations.

---

## ⏱️ Step 2: Create "Rajasthan Explorer" Trip (0:30 – 1:00)

1. Click **"+ Plan New Trip"**.
2. Form fields populated:
   - **Trip Title**: `Rajasthan Explorer`
   - **Dates**: Oct 1 – Oct 7 (7 Days)
   - **Budget**: `₹35,000`
   - **Travelers**: `2`
   - **Currency**: `INR (₹)`
   - **Travel Style**: `Balanced Explorer`
3. Click **"Create & Build Itinerary"** — seamlessly transitions directly to the Itinerary Builder!

---

## ⏱️ Step 3: Multi-City Route & Sequence (1:00 – 1:30)

1. View the **Multi-City Route Sequence Rail**.
2. Click **"+ Add City Stop"** and add:
   - **Delhi** (Oct 1 – Oct 3)
   - **Jaipur** (Oct 3 – Oct 5)
   - **Udaipur** (Oct 5 – Oct 7)
3. Demonstrate **Route Reordering**: Click arrow button to swap Jaipur and Udaipur, then move it back to show real-time sequence updates.

---

## ⏱️ Step 4: Schedule Activities & Curated Discovery (1:30 – 2:00)

1. Scroll to **Day 1**: Click **"+ Add Activity"**, pick *"Red Fort & Old Delhi Heritage Walk"* from curated experiences.
2. Scroll to **Day 3**: Click **"+ Add Activity"**, pick *"Amber Fort & Sheesh Mahal Exploration"*.
3. Scroll to **Day 5**: Click **"+ Add Activity"**, pick *"Lake Pichola Sunset Boat Cruise"*.
4. Click **"+ Add Expense"** and log:
   - AC Cab Transfer: `₹12,000`
   - Heritage Haveli Stays: `₹15,000`

---

## ⏱️ Step 5: Dynamic Budget Intelligence & Balance Score (2:00 – 2:30)

1. Switch toolbar to **"Budget & Intelligence"** tab:
   - Show dynamic calculation: `₹31,700` estimated cost out of `₹35,000` target (`91%` utilization, `₹3,300` remaining).
   - Show **Cost Per Traveler** (`₹15,850`) and **Cost Per Day** (`₹4,529/day`).
   - Show **Category Distribution Bars** (Transport, Accommodation, Activities).
   - Show **Rule-Based Intelligence Alert**: *"Your itinerary is nearing full budget utilization (91%), with ₹3,300 remaining."*
   - Show **Travel Balance Score Gauge**: `88/100` with transparent breakdown for Budget Discipline, Activity Pacing, City Dwell, and Completeness.

---

## ⏱️ Step 6: Interactive Calendar, Timeline & Presentation Mode (2:30 – 2:45)

1. Click **"Calendar View"** — shows clean grid with scheduled events and daily cost totals.
2. Click **"Timeline View"** — shows connected journey nodes from Day 1 to Day 7.
3. Click **"Presentation Mode"** — full-screen executive summary with high-res cover banner and route cards suitable for stakeholder presentations.

---

## ⏱️ Step 7: Public Sharing & 1-Click Itinerary Cloning (2:45 – 3:00)

1. Click **"Share Publicly"** — generates unguessable secure token `/shared/<token>`.
2. Open public share URL in new tab / incognito — shows read-only snapshot.
3. Click **"📋 Copy Trip to My Account"** as a different user — clones the entire itinerary, stops, scheduled activities, and expenses with new IDs!
4. Conclude by highlighting the **Odoo 17 Model Architecture** (`globetrotter.trip`, `globetrotter.trip.stop`, `globetrotter.trip.activity`, `globetrotter.expense`, Security Record Rules, PostgreSQL 17 persistence).
