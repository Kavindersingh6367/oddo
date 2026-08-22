# -*- coding: utf-8 -*-
"""
GlobeTrotter Comprehensive Automated Test Suite
Validates authentication, trip CRUD, stop reordering, activity scheduling,
dynamic budgeting, rule-based intelligence, travel balance score, security record rules,
and public itinerary cloning.
"""

import unittest
import requests
import time
import subprocess
import os
import sys

BASE_URL = "http://127.0.0.1:8069"

class TestGlobeTrotter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
    
        max_retries = 10
        for i in range(max_retries):
            try:
                res = requests.get(f"{BASE_URL}/api/v1/destinations", timeout=2)
                if res.status_code == 200:
                    break
            except Exception:
                time.sleep(1)

    def test_01_destinations_catalog(self):
        """Test destination retrieval, search filtering, and seed verification."""
        res = requests.get(f"{BASE_URL}/api/v1/destinations")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get('success'))
        destinations = data.get('destinations', [])
        self.assertGreaterEqual(len(destinations), 5)
        
        # Check specific seed cities
        names = [d['name'] for d in destinations]
        self.assertIn("Delhi", names)
        self.assertIn("Jaipur", names)
        self.assertIn("Udaipur", names)

    def test_02_authentication_workflow(self):
        """Test user signup, login, session validation, and duplicate email prevention."""
        ts = int(time.time() * 1000)
        test_email = f"traveler_{ts}@globetrotter.travel"
        test_pass = "secret123"

        # 1. Signup
        signup_res = requests.post(f"{BASE_URL}/api/v1/auth/signup", json={
            "name": "Aarav Patel",
            "email": test_email,
            "password": test_pass,
            "preferred_currency": "INR",
            "preferred_travel_style": "balanced"
        })
        self.assertEqual(signup_res.status_code, 200)
        signup_data = signup_res.json()
        self.assertTrue(signup_data.get('success'))
        token = signup_data.get('token')
        self.assertTrue(token)

        # 2. Duplicate signup should fail
        dup_res = requests.post(f"{BASE_URL}/api/v1/auth/signup", json={
            "name": "Duplicate User",
            "email": test_email,
            "password": test_pass
        })
        self.assertEqual(dup_res.status_code, 400)
        self.assertIn("already exists", dup_res.json().get('error', ''))

        # 3. Invalid login should fail
        bad_login = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": test_email,
            "password": "wrongpassword"
        })
        self.assertEqual(bad_login.status_code, 400)

        # 4. Valid login
        login_res = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": test_email,
            "password": test_pass
        })
        self.assertEqual(login_res.status_code, 200)
        self.assertTrue(login_res.json().get('success'))

        # 5. Auth Me
        me_res = requests.get(f"{BASE_URL}/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.json().get('user', {}).get('email'), test_email)

    def test_03_acceptance_test_rajasthan_explorer_workflow(self):
        """
        Acceptance Test Scenario:
        1. Login as user
        2. Create 'Rajasthan Explorer' trip (Budget: 35,000, 2 travelers)
        3. Add Delhi, Jaipur, Udaipur stops
        4. Reorder stops
        5. Add activities to Day 1, Day 2, Day 3
        6. Add logistics expenses
        7. Verify dynamic budget rollup, per-traveler cost, and intelligence alerts
        8. Verify Travel Balance Score
        9. Generate public share token & verify read-only access
        10. Copy/clone trip into another user's account and verify independence
        """
        # Step 1: Login
        login_res = requests.post(f"{BASE_URL}/api/v1/auth/demo-login", json={"role": "traveler"})
        self.assertEqual(login_res.status_code, 200)
        token = login_res.json()['token']
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Create Trip 'Rajasthan Explorer'
        create_res = requests.post(f"{BASE_URL}/api/v1/trips", headers=headers, json={
            "name": "Rajasthan Explorer",
            "start_date": "2026-10-01",
            "end_date": "2026-10-07",
            "total_budget": 35000.0,
            "travelers_count": 2,
            "currency": "INR",
            "travel_style": "balanced",
            "description": "Cultural journey through Mughal monuments, Rajput hilltop palaces, and serene desert lakes."
        })
        self.assertEqual(create_res.status_code, 200)
        trip_id = create_res.json()['trip_id']
        self.assertTrue(trip_id)

        # Get destination IDs for Delhi, Jaipur, Udaipur
        d_res = requests.get(f"{BASE_URL}/api/v1/destinations").json()
        cities = {c['name']: c['id'] for c in d_res['destinations']}
        
        # Step 3: Add stops (Delhi, Jaipur, Udaipur)
        stop1_res = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/stops", headers=headers, json={
            "city_id": cities["Delhi"],
            "arrival_date": "2026-10-01",
            "departure_date": "2026-10-03",
            "notes": "Heritage hotel in Connaught Place"
        })
        self.assertTrue(stop1_res.json().get('success'))
        stop1_id = stop1_res.json()['stop_id']

        stop2_res = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/stops", headers=headers, json={
            "city_id": cities["Jaipur"],
            "arrival_date": "2026-10-03",
            "departure_date": "2026-10-05",
            "notes": "Haveli stay near Amber Fort"
        })
        self.assertTrue(stop2_res.json().get('success'))
        stop2_id = stop2_res.json()['stop_id']

        stop3_res = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/stops", headers=headers, json={
            "city_id": cities["Udaipur"],
            "arrival_date": "2026-10-05",
            "departure_date": "2026-10-07",
            "notes": "Lakefront boutique resort"
        })
        self.assertTrue(stop3_res.json().get('success'))
        stop3_id = stop3_res.json()['stop_id']

        # Step 4: Reorder stops (Delhi -> Udaipur -> Jaipur)
        reorder_res = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/stops/reorder", headers=headers, json={
            "stop_ids": [stop1_id, stop3_id, stop2_id]
        })
        self.assertTrue(reorder_res.json().get('success'))

        # Put order back to normal: Delhi -> Jaipur -> Udaipur
        requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/stops/reorder", headers=headers, json={
            "stop_ids": [stop1_id, stop2_id, stop3_id]
        })

        # Step 5: Add Activities to Days
        act1 = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/activities", headers=headers, json={
            "stop_id": stop1_id,
            "name": "Red Fort & Old Delhi Heritage Walk",
            "category": "culture",
            "day_number": 1,
            "scheduled_time": "09:30",
            "duration_hours": 3.0,
            "estimated_cost": 1300.0  # for 2 travelers
        })
        self.assertTrue(act1.json().get('success'))

        act2 = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/activities", headers=headers, json={
            "stop_id": stop2_id,
            "name": "Amber Fort & Sheesh Mahal Exploration",
            "category": "sightseeing",
            "day_number": 3,
            "scheduled_time": "10:00",
            "duration_hours": 3.5,
            "estimated_cost": 1500.0
        })
        self.assertTrue(act2.json().get('success'))

        act3 = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/activities", headers=headers, json={
            "stop_id": stop3_id,
            "name": "Lake Pichola Sunset Boat Cruise to Jag Mandir",
            "category": "relaxation",
            "day_number": 5,
            "scheduled_time": "17:00",
            "duration_hours": 2.0,
            "estimated_cost": 1900.0
        })
        self.assertTrue(act3.json().get('success'))

        # Step 6: Add Expenses & Logistics
        exp1 = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/expenses", headers=headers, json={
            "category": "transportation",
            "name": "Private AC Cab Delhi -> Jaipur -> Udaipur",
            "amount": 12000.0,
            "notes": "Chauffeur included for 7 days"
        })
        self.assertTrue(exp1.json().get('success'))

        exp2 = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/expenses", headers=headers, json={
            "category": "accommodation",
            "name": "6 Nights Heritage Haveli Stays (Double Occupancy)",
            "amount": 15000.0,
            "notes": "Breakfast included"
        })
        self.assertTrue(exp2.json().get('success'))

        # Step 7: Verify Dynamic Budget Rollup
        trip_view = requests.get(f"{BASE_URL}/api/v1/trips/{trip_id}", headers=headers).json()['trip']
        expected_act_cost = 1300.0 + 1500.0 + 1900.0  # 4,700
        expected_total = 4700.0 + 12000.0 + 15000.0   # 31,700

        self.assertEqual(trip_view['cost_activities'], expected_act_cost)
        self.assertEqual(trip_view['cost_transportation'], 12000.0)
        self.assertEqual(trip_view['cost_accommodation'], 15000.0)
        self.assertEqual(trip_view['total_estimated_cost'], expected_total)
        self.assertEqual(trip_view['cost_per_traveler'], expected_total / 2.0)
        self.assertEqual(trip_view['remaining_budget'], 35000.0 - expected_total)
        self.assertAlmostEqual(trip_view['budget_utilization'], (31700.0 / 35000.0) * 100.0, places=1)

        # Step 8: Verify Travel Balance Score
        self.assertGreaterEqual(trip_view['trip_balance_score'], 70)
        factors = trip_view['balance_score_summary']
        factor_names = [f['name'] for f in factors]
        self.assertIn("Budget Discipline", factor_names)
        self.assertIn("Activity Density", factor_names)
        self.assertIn("City Pacing & Dwell", factor_names)

        # Step 9: Sharing & Public URL
        share_res = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/share", headers=headers, json={
            "is_public": True,
            "share_budget": True
        })
        self.assertTrue(share_res.json().get('success'))
        token_str = share_res.json()['share_token']

        # Access public unauthenticated URL
        pub_res = requests.get(f"{BASE_URL}/api/v1/shared/{token_str}")
        self.assertEqual(pub_res.status_code, 200)
        pub_trip = pub_res.json()['trip']
        self.assertEqual(pub_trip['name'], "Rajasthan Explorer")
        self.assertEqual(len(pub_trip['stops']), 3)
        self.assertEqual(len(pub_trip['activities']), 3)

        # Step 10: Copy Trip into another user's account
        # Create a second user
        ts2 = int(time.time() * 1000)
        u2_res = requests.post(f"{BASE_URL}/api/v1/auth/signup", json={
            "name": "Priya Sen",
            "email": f"priya_{ts2}@globetrotter.travel",
            "password": "password123"
        }).json()
        u2_token = u2_res['token']
        u2_headers = {"Authorization": f"Bearer {u2_token}"}

        copy_res = requests.post(f"{BASE_URL}/api/v1/shared/{token_str}/copy", headers=u2_headers)
        self.assertEqual(copy_res.status_code, 200)
        cloned_trip_id = copy_res.json()['trip_id']
        self.assertNotEqual(trip_id, cloned_trip_id)

        # Verify cloned trip exists in Priya's trips
        u2_trips = requests.get(f"{BASE_URL}/api/v1/trips", headers=u2_headers).json()['trips']
        cloned_match = [t for t in u2_trips if t['id'] == cloned_trip_id]
        self.assertEqual(len(cloned_match), 1)
        self.assertEqual(cloned_match[0]['total_estimated_cost'], expected_total)

    def test_04_security_record_rules_multi_tenancy(self):
        """Verify that User A cannot modify or access User B's private itineraries without authorization."""
        ts = int(time.time() * 1000)
        user_a = requests.post(f"{BASE_URL}/api/v1/auth/signup", json={
            "name": "User Alpha",
            "email": f"alpha_{ts}@globetrotter.travel",
            "password": "password123"
        }).json()['token']

        user_b = requests.post(f"{BASE_URL}/api/v1/auth/signup", json={
            "name": "User Beta",
            "email": f"beta_{ts}@globetrotter.travel",
            "password": "password123"
        }).json()['token']

        
        trip_a = requests.post(f"{BASE_URL}/api/v1/trips", headers={"Authorization": f"Bearer {user_a}"}, json={
            "name": "Private Secret Alpha Vacation",
            "start_date": "2026-11-01",
            "end_date": "2026-11-05",
            "total_budget": 50000.0
        }).json()['trip_id']

        
        hack_attempt = requests.get(f"{BASE_URL}/api/v1/trips/{trip_a}", headers={"Authorization": f"Bearer {user_b}"})
        self.assertEqual(hack_attempt.status_code, 403)
        self.assertIn("Access Denied", hack_attempt.json().get('error', ''))

        del_attempt = requests.delete(f"{BASE_URL}/api/v1/trips/{trip_a}", headers={"Authorization": f"Bearer {user_b}"})
        self.assertEqual(del_attempt.status_code, 403)


    def test_05_hotel_catalog_and_recommendations(self):
        """Test hotel recommendations engine, scoring, filtering, profiles, and comparison."""
        # 1. Query Jaipur Recommendations
        res = requests.get(f"{BASE_URL}/api/v1/hotels/recommendations?city=Jaipur&nights=2&rooms=1")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get('success'))
        hotels = data.get('hotels', [])
        self.assertGreaterEqual(len(hotels), 3)

        # Check scoring and structured explanations
        first_hotel = hotels[0]
        self.assertIn('recommendation_score', first_hotel)
        self.assertGreaterEqual(first_hotel['recommendation_score'], 50)
        self.assertLessEqual(first_hotel['recommendation_score'], 100)
        self.assertIn('primary_badge', first_hotel)
        self.assertIn('why_points', first_hotel)
        self.assertGreaterEqual(len(first_hotel['why_points']), 1)
        self.assertIn('total_stay_cost', first_hotel)

        # 2. Filter by Category = luxury
        lux_res = requests.get(f"{BASE_URL}/api/v1/hotels/recommendations?city=Jaipur&category=luxury").json()
        lux_hotels = lux_res.get('hotels', [])
        self.assertTrue(all(h['hotel_category'] == 'luxury' for h in lux_hotels))

        # 3. Sort by Price Ascending
        sort_res = requests.get(f"{BASE_URL}/api/v1/hotels/recommendations?city=Jaipur&sort_by=price_asc").json()
        prices = [float(h['price_per_night']) for h in sort_res['hotels']]
        self.assertEqual(prices, sorted(prices))

        # 4. Single Hotel Profile
        h_id = first_hotel['id']
        detail_res = requests.get(f"{BASE_URL}/api/v1/hotels/{h_id}")
        self.assertEqual(detail_res.status_code, 200)
        h_detail = detail_res.json().get('hotel', {})
        self.assertEqual(h_detail.get('id'), h_id)
        self.assertTrue(h_detail.get('name'))
        self.assertIn('location_score', h_detail)

        # 5. Side-by-Side Comparison Matrix
        if len(hotels) >= 2:
            comp_ids = f"{hotels[0]['id']},{hotels[1]['id']}"
            comp_res = requests.get(f"{BASE_URL}/api/v1/hotels/compare?ids={comp_ids}&nights=2&rooms=1")
            self.assertEqual(comp_res.status_code, 200)
            comp_data = comp_res.json()
            self.assertEqual(len(comp_data.get('comparison', [])), 2)

    def test_06_budget_aware_hotel_selection_and_expense_sync(self):
        """Test budget-aware scoring, booking creation, automatic expense sync, update, and removal."""
        # 1. Login
        login_res = requests.post(f"{BASE_URL}/api/v1/auth/demo-login", json={"role": "traveler"}).json()
        token = login_res['token']
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create Trip with ₹40,000 budget
        trip_res = requests.post(f"{BASE_URL}/api/v1/trips", headers=headers, json={
            "name": "Delhi Heritage Weekend",
            "start_date": "2026-10-10",
            "end_date": "2026-10-13",
            "total_budget": 40000.0,
            "travelers_count": 2,
            "currency": "INR",
            "travel_style": "balanced"
        }).json()
        trip_id = trip_res['trip_id']

        # 3. Add Delhi Stop
        d_res = requests.get(f"{BASE_URL}/api/v1/destinations").json()
        delhi_id = next(c['id'] for c in d_res['destinations'] if c['name'] == 'Delhi')
        stop_res = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/stops", headers=headers, json={
            "city_id": delhi_id,
            "arrival_date": "2026-10-10",
            "departure_date": "2026-10-13",
            "notes": "Central Delhi stay"
        }).json()
        stop_id = stop_res['stop_id']

        # 4. Get Delhi Hotels
        h_res = requests.get(f"{BASE_URL}/api/v1/hotels/recommendations?city_id={delhi_id}&trip_id={trip_id}&check_in=2026-10-10&check_out=2026-10-13&rooms=1").json()
        hotels = h_res['hotels']
        self.assertGreaterEqual(len(hotels), 1)
        selected_hotel = hotels[0]
        hotel_id = selected_hotel['id']
        rate = float(selected_hotel['price_per_night'])
        nights = 3
        expected_cost = rate * nights * 1

        # 5. Book Hotel via API
        book_res = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/hotels", headers=headers, json={
            "hotel_id": hotel_id,
            "stop_id": stop_id,
            "check_in": "2026-10-10",
            "check_out": "2026-10-13",
            "number_of_guests": 2,
            "number_of_rooms": 1,
            "room_type_selected": "Deluxe King Room",
            "notes": "Late check-in requested"
        })
        self.assertEqual(book_res.status_code, 200)
        book_data = book_res.json()
        self.assertTrue(book_data['success'])
        booking_id = book_data['booking_id']
        expense_id = book_data['expense_id']
        self.assertEqual(book_data['total_cost'], expected_cost)

        # 6. Verify Trip Financial Rollup
        trip_data = requests.get(f"{BASE_URL}/api/v1/trips/{trip_id}", headers=headers).json()['trip']
        self.assertEqual(trip_data['cost_accommodation'], expected_cost)
        self.assertEqual(trip_data['total_estimated_cost'], expected_cost)
        self.assertEqual(trip_data['remaining_budget'], 40000.0 - expected_cost)
        self.assertEqual(len(trip_data['hotels']), 1)
        self.assertEqual(trip_data['stops'][0]['hotel_booking']['id'], booking_id)

        # 7. Update Hotel Booking (change to 2 rooms)
        update_res = requests.put(f"{BASE_URL}/api/v1/trips/{trip_id}/hotels/{booking_id}", headers=headers, json={
            "check_in": "2026-10-10",
            "check_out": "2026-10-13",
            "number_of_rooms": 2
        })
        self.assertEqual(update_res.status_code, 200)
        new_expected_cost = rate * nights * 2
        self.assertEqual(update_res.json()['total_cost'], new_expected_cost)

        # Verify updated expense and trip budget
        trip_data_after_update = requests.get(f"{BASE_URL}/api/v1/trips/{trip_id}", headers=headers).json()['trip']
        self.assertEqual(trip_data_after_update['cost_accommodation'], new_expected_cost)
        self.assertEqual(trip_data_after_update['remaining_budget'], 40000.0 - new_expected_cost)

        # 8. Delete Hotel Booking and verify clean removal
        del_res = requests.delete(f"{BASE_URL}/api/v1/trips/{trip_id}/hotels/{booking_id}", headers=headers)
        self.assertEqual(del_res.status_code, 200)

        trip_data_after_del = requests.get(f"{BASE_URL}/api/v1/trips/{trip_id}", headers=headers).json()['trip']
        self.assertEqual(trip_data_after_del['cost_accommodation'], 0.0)
        self.assertEqual(trip_data_after_del['total_estimated_cost'], 0.0)
        self.assertEqual(trip_data_after_del['remaining_budget'], 40000.0)
        self.assertEqual(len(trip_data_after_del['hotels']), 0)
        self.assertIsNone(trip_data_after_del['stops'][0]['hotel_booking'])

    def test_07_multi_city_hotel_booking_and_multi_tenancy(self):
        """Test multi-city trip with distinct hotels for Delhi, Jaipur, and Udaipur, cloning, and security."""
        # 1. Login User Alpha
        ts = int(time.time() * 1000)
        u1_res = requests.post(f"{BASE_URL}/api/v1/auth/signup", json={
            "name": "Dev Traveler",
            "email": f"dev_{ts}@globetrotter.travel",
            "password": "password123"
        }).json()
        u1_token = u1_res['token']
        headers1 = {"Authorization": f"Bearer {u1_token}"}

        # 2. Create Multi-City Trip
        trip_id = requests.post(f"{BASE_URL}/api/v1/trips", headers=headers1, json={
            "name": "Golden Triangle Hotel Expedition",
            "start_date": "2026-11-01",
            "end_date": "2026-11-07",
            "total_budget": 60000.0,
            "travelers_count": 2
        }).json()['trip_id']

        d_res = requests.get(f"{BASE_URL}/api/v1/destinations").json()
        cities = {c['name']: c['id'] for c in d_res['destinations']}

        # Add 3 Stops: Delhi, Jaipur, Udaipur
        stop_delhi = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/stops", headers=headers1, json={
            "city_id": cities["Delhi"], "arrival_date": "2026-11-01", "departure_date": "2026-11-03"
        }).json()['stop_id']

        stop_jaipur = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/stops", headers=headers1, json={
            "city_id": cities["Jaipur"], "arrival_date": "2026-11-03", "departure_date": "2026-11-05"
        }).json()['stop_id']

        stop_udaipur = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/stops", headers=headers1, json={
            "city_id": cities["Udaipur"], "arrival_date": "2026-11-05", "departure_date": "2026-11-07"
        }).json()['stop_id']

        # Fetch hotels for each city and book
        h_delhi = requests.get(f"{BASE_URL}/api/v1/hotels/recommendations?city_id={cities['Delhi']}").json()['hotels'][0]
        h_jaipur = requests.get(f"{BASE_URL}/api/v1/hotels/recommendations?city_id={cities['Jaipur']}").json()['hotels'][0]
        h_udaipur = requests.get(f"{BASE_URL}/api/v1/hotels/recommendations?city_id={cities['Udaipur']}").json()['hotels'][0]

        # Book Delhi hotel
        b1 = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/hotels", headers=headers1, json={
            "hotel_id": h_delhi['id'], "stop_id": stop_delhi, "check_in": "2026-11-01", "check_out": "2026-11-03", "number_of_rooms": 1
        }).json()['booking_id']

        # Book Jaipur hotel
        b2 = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/hotels", headers=headers1, json={
            "hotel_id": h_jaipur['id'], "stop_id": stop_jaipur, "check_in": "2026-11-03", "check_out": "2026-11-05", "number_of_rooms": 1
        }).json()['booking_id']

        # Book Udaipur hotel
        b3 = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/hotels", headers=headers1, json={
            "hotel_id": h_udaipur['id'], "stop_id": stop_udaipur, "check_in": "2026-11-05", "check_out": "2026-11-07", "number_of_rooms": 1
        }).json()['booking_id']

        # Verify all 3 stops have distinct hotel bookings attached
        trip_view = requests.get(f"{BASE_URL}/api/v1/trips/{trip_id}", headers=headers1).json()['trip']
        self.assertEqual(len(trip_view['hotels']), 3)
        self.assertEqual(trip_view['stops'][0]['hotel_booking']['hotel_id'], h_delhi['id'])
        self.assertEqual(trip_view['stops'][1]['hotel_booking']['hotel_id'], h_jaipur['id'])
        self.assertEqual(trip_view['stops'][2]['hotel_booking']['hotel_id'], h_udaipur['id'])

        total_accommodation_cost = (
            float(h_delhi['price_per_night']) * 2 +
            float(h_jaipur['price_per_night']) * 2 +
            float(h_udaipur['price_per_night']) * 2
        )
        self.assertEqual(trip_view['cost_accommodation'], total_accommodation_cost)

        # 3. Multi-Tenant Security Check: User Beta cannot tamper with User Alpha's hotel bookings
        u2_res = requests.post(f"{BASE_URL}/api/v1/auth/signup", json={
            "name": "Attacker Beta",
            "email": f"beta_{ts}@globetrotter.travel",
            "password": "password123"
        }).json()
        headers2 = {"Authorization": f"Bearer {u2_res['token']}"}

        tamper_put = requests.put(f"{BASE_URL}/api/v1/trips/{trip_id}/hotels/{b1}", headers=headers2, json={"number_of_rooms": 5})
        self.assertEqual(tamper_put.status_code, 403)

        tamper_del = requests.delete(f"{BASE_URL}/api/v1/trips/{trip_id}/hotels/{b1}", headers=headers2)
        self.assertEqual(tamper_del.status_code, 403)

        # 4. Clone / Copy Trip and verify hotel bookings clone properly
        dup_res = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/duplicate", headers=headers1)
        self.assertEqual(dup_res.status_code, 200)
        cloned_id = dup_res.json()['trip_id']
        cloned_view = requests.get(f"{BASE_URL}/api/v1/trips/{cloned_id}", headers=headers1).json()['trip']
        self.assertEqual(len(cloned_view['hotels']), 3)
        self.assertEqual(cloned_view['cost_accommodation'], total_accommodation_cost)


    def test_06_weather_service_and_itinerary_adjustment(self):
        """Verify Weather API, hazard risk analysis, and single/batch weather-aware adjustments."""
        # 1. Test Weather Forecast Query Endpoint
        w_res = requests.get(f"{BASE_URL}/api/v1/weather?city_id=1&start_date=2026-10-01&end_date=2026-10-04")
        self.assertEqual(w_res.status_code, 200)
        w_data = w_res.json()
        self.assertTrue(w_data.get('success'))
        fc = w_data.get('forecast', {})
        self.assertEqual(fc.get('city_name'), 'Delhi')
        self.assertGreaterEqual(len(fc.get('days', [])), 3)

        # 2. Setup user and trip for weather intelligence testing
        ts = int(time.time() * 1000)
        u_res = requests.post(f"{BASE_URL}/api/v1/auth/signup", json={
            "name": "Weather Explorer",
            "email": f"weather_{ts}@globetrotter.travel",
            "password": "password123"
        }).json()
        token = u_res['token']
        headers = {"Authorization": f"Bearer {token}"}

        # Create 3-day trip
        trip_res = requests.post(f"{BASE_URL}/api/v1/trips", headers=headers, json={
            "name": "Monsoon & Weather Test Tour",
            "start_date": "2026-10-01",
            "end_date": "2026-10-03",
            "total_budget": 25000.0,
            "currency": "INR"
        }).json()
        trip_id = trip_res['trip_id']

        # Add Stop
        stop_res = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/stops", headers=headers, json={
            "city_id": 1,
            "arrival_date": "2026-10-01",
            "departure_date": "2026-10-03",
            "duration_days": 3
        }).json()
        stop_id = stop_res['stop_id']

        # Add Outdoor Activity on Day 1
        act1 = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/activities", headers=headers, json={
            "stop_id": stop_id,
            "name": "Red Fort & Old Delhi Heritage Walk",
            "category": "sightseeing",
            "day_number": 1,
            "scheduled_time": "10:00",
            "duration_hours": 3.0,
            "estimated_cost": 650.0
        }).json()['activity_id']

        # Add Indoor Activity on Day 2
        act2 = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/activities", headers=headers, json={
            "stop_id": stop_id,
            "name": "National Craft Museum & Indoor Gallery",
            "category": "culture",
            "day_number": 2,
            "scheduled_time": "14:00",
            "duration_hours": 2.5,
            "estimated_cost": 400.0
        }).json()['activity_id']

        # 3. Fetch Weather Analysis
        analysis_res = requests.get(f"{BASE_URL}/api/v1/trips/{trip_id}/weather-analysis", headers=headers)
        self.assertEqual(analysis_res.status_code, 200)
        analysis_data = analysis_res.json()
        self.assertTrue(analysis_data.get('success'))
        analysis = analysis_data['analysis']
        self.assertIn('weather_health_score', analysis)
        self.assertEqual(len(analysis['evaluated_activities']), 2)

        # 4. Test Single Weather Adjustment: Reschedule Day
        adj_res = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/weather-adjust", headers=headers, json={
            "activity_id": act1,
            "action_type": "move_day",
            "target_day_number": 3
        })
        self.assertEqual(adj_res.status_code, 200)
        self.assertTrue(adj_res.json().get('success'))

        # Verify activity was moved to Day 3
        trip_detail = requests.get(f"{BASE_URL}/api/v1/trips/{trip_id}", headers=headers).json()['trip']
        moved_act = [a for a in trip_detail['activities'] if a['id'] == act1][0]
        self.assertEqual(moved_act['day_number'], 3)

        # 5. Test Single Weather Adjustment: Swap with Indoor Activity
        swap_res = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/weather-adjust", headers=headers, json={
            "activity_id": act1,
            "action_type": "swap_indoor",
            "substitute_activity": {
                "name": "National Museum & Art Center (Indoor)",
                "category": "culture",
                "estimated_cost": 500.0,
                "duration_hours": 2.0,
                "description": "Exquisite ancient art and artifacts."
            }
        })
        self.assertEqual(swap_res.status_code, 200)
        self.assertTrue(swap_res.json().get('success'))

        # Verify activity was replaced
        trip_detail2 = requests.get(f"{BASE_URL}/api/v1/trips/{trip_id}", headers=headers).json()['trip']
        swapped_act = [a for a in trip_detail2['activities'] if a['id'] == act1][0]
        self.assertEqual(swapped_act['name'], "National Museum & Art Center (Indoor)")
        self.assertEqual(swapped_act['category'], "culture")

        # 6. Test Batch Weather Adjustment (Apply All)
        batch_res = requests.post(f"{BASE_URL}/api/v1/trips/{trip_id}/weather-adjust-all", headers=headers)
        self.assertEqual(batch_res.status_code, 200)
        self.assertTrue(batch_res.json().get('success'))


if __name__ == '__main__':

    unittest.main()

