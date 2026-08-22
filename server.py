# -*- coding: utf-8 -*-
"""
GlobeTrotter Production Backend Server
Full-featured Odoo-compliant REST & JSON-RPC runtime powered by PostgreSQL 17.
"""

import os
import json
import secrets
import logging
from datetime import date, datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse
from passlib.hash import pbkdf2_sha256
import psycopg2
import psycopg2.extras

from database import get_db_connection, init_db
from weather_service import WeatherService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
_logger = logging.getLogger("globetrotter.server")

SESSIONS = {}  # token -> user_id

def date_converter(o):
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    return str(o)

def compute_trip_business_logic(trip_dict, stops, activities, expenses):
    """Calculates all Odoo computed fields: budget rollup, intelligence alerts, and travel balance score."""
    start_date = trip_dict.get('start_date')
    end_date = trip_dict.get('end_date')
    
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    duration_days = 1
    if start_date and end_date:
        duration_days = max(1, (end_date - start_date).days + 1)
    
    today = date.today()
    if not start_date or not end_date:
        status = 'draft'
    elif end_date < today:
        status = 'completed'
    elif start_date <= today <= end_date:
        status = 'ongoing'
    else:
        status = 'upcoming'

    # Compute Costs
    cost_activities = sum(float(a.get('estimated_cost') or 0.0) for a in activities)
    
    transport = sum(float(e.get('amount') or 0.0) for e in expenses if e.get('category') == 'transportation')
    stay = sum(float(e.get('amount') or 0.0) for e in expenses if e.get('category') == 'accommodation')
    food = sum(float(e.get('amount') or 0.0) for e in expenses if e.get('category') == 'food')
    misc = sum(float(e.get('amount') or 0.0) for e in expenses if e.get('category') == 'miscellaneous')
    extra_act = sum(float(e.get('amount') or 0.0) for e in expenses if e.get('category') == 'activities')
    
    total_act_cost = cost_activities + extra_act
    total_cost = total_act_cost + transport + stay + food + misc
    
    travelers = max(1, int(trip_dict.get('travelers_count') or 1))
    budget = float(trip_dict.get('total_budget') or 0.0)
    
    cost_per_traveler = total_cost / travelers
    cost_per_day = total_cost / duration_days
    remaining_budget = budget - total_cost
    budget_utilization = (total_cost / budget * 100.0) if budget > 0 else (100.0 if total_cost > 0 else 0.0)
    
    currency_sym = trip_dict.get('currency') or 'INR'

    # Budget Intelligence Rules
    alerts = []
    if budget > 0:
        if total_cost > budget:
            diff = total_cost - budget
            alerts.append({
                'type': 'warning',
                'code': 'OVER_BUDGET',
                'title': 'Over Budget Warning',
                'message': f"Your trip is approximately {currency_sym} {diff:,.0f} over your target budget.",
                'severity': 'high'
            })
        elif total_cost > 0 and (budget - total_cost) <= (budget * 0.1):
            diff = budget - total_cost
            alerts.append({
                'type': 'info',
                'code': 'NEAR_BUDGET',
                'title': 'Near Budget Limit',
                'message': f"Your itinerary is nearing full budget utilization ({budget_utilization:.0f}%), with {currency_sym} {diff:,.0f} remaining.",
                'severity': 'medium'
            })
        else:
            diff = budget - total_cost
            alerts.append({
                'type': 'success',
                'code': 'WITHIN_BUDGET',
                'title': 'Within Budget',
                'message': f"Your itinerary is currently within budget with {currency_sym} {diff:,.0f} remaining.",
                'severity': 'low'
            })

    if total_cost > 0:
        if (stay / total_cost) >= 0.40:
            pct = int((stay / total_cost) * 100)
            alerts.append({
                'type': 'info',
                'code': 'DOMINANT_ACCOMMODATION',
                'title': 'Accommodation Focus',
                'message': f"Accommodation represents {pct}% of your estimated trip cost.",
                'severity': 'medium'
            })
        if (transport / total_cost) >= 0.35:
            pct = int((transport / total_cost) * 100)
            alerts.append({
                'type': 'info',
                'code': 'DOMINANT_TRANSPORT',
                'title': 'Transportation Focus',
                'message': f"Transportation represents {pct}% of your estimated trip cost.",
                'severity': 'medium'
            })

    if duration_days > 1 and total_cost > 0:
        daily_avg = total_cost / duration_days
        day_costs = {}
        for a in activities:
            d_num = a.get('day_number') or 1
            day_costs[d_num] = day_costs.get(d_num, 0.0) + float(a.get('estimated_cost') or 0.0)
        for d_num, dcost in day_costs.items():
            if dcost >= daily_avg * 2.0 and dcost > 2000:
                alerts.append({
                    'type': 'warning',
                    'code': 'EXPENSIVE_DAY',
                    'title': f'High Spending Day',
                    'message': f"Day {d_num} is significantly above your daily average ({currency_sym} {daily_avg:,.0f}/day vs {currency_sym} {dcost:,.0f} scheduled).",
                    'severity': 'medium'
                })

    # Travel Balance Score
    factors = []
    # 1. Budget Discipline (0-30)
    score_budget = 30
    if budget <= 0:
        score_budget = 20
        f_desc = "Budget not specified; baseline allocation."
    else:
        if 60 <= budget_utilization <= 100:
            score_budget = 30
            f_desc = f"Optimal budget alignment ({budget_utilization:.0f}% utilized)."
        elif 30 <= budget_utilization < 60:
            score_budget = 24
            f_desc = f"Conservative spending ({budget_utilization:.0f}% utilized)."
        elif 100 < budget_utilization <= 120:
            score_budget = 18
            f_desc = f"Slight budget overrun ({budget_utilization:.0f}% utilized)."
        elif budget_utilization > 120:
            score_budget = 8
            f_desc = f"Significant budget overrun ({budget_utilization:.0f}% utilized)."
        else:
            score_budget = 15
            f_desc = "Minimal budget allocation."
    factors.append({'name': 'Budget Discipline', 'score': score_budget, 'max': 30, 'description': f_desc})

    # 2. Activity Density (0-25)
    score_density = 25
    acts_count = len(activities)
    avg_acts = acts_count / duration_days if duration_days else 0
    if 1.5 <= avg_acts <= 4.0:
        score_density = 25
        f_desc = f"Balanced pacing ({avg_acts:.1f} activities/day)."
    elif 0.5 <= avg_acts < 1.5:
        score_density = 20
        f_desc = f"Relaxed schedule ({avg_acts:.1f} activities/day)."
    elif avg_acts > 4.0:
        score_density = 14
        f_desc = f"High density schedule ({avg_acts:.1f} activities/day; potential fatigue)."
    else:
        score_density = 10
        f_desc = "Few scheduled activities. Add more destination experiences."
    factors.append({'name': 'Activity Density', 'score': score_density, 'max': 25, 'description': f_desc})

    # 3. City Pacing & Dwell (0-25)
    stops_count = len(stops)
    score_dwell = 25
    if stops_count == 0:
        score_dwell = 5
        f_desc = "No destination stops added yet."
    else:
        days_per_stop = duration_days / stops_count
        if 1.5 <= days_per_stop <= 5.0:
            score_dwell = 25
            f_desc = f"Healthy exploration pace ({days_per_stop:.1f} days per stop)."
        elif days_per_stop > 5.0:
            score_dwell = 22
            f_desc = f"Deep dive travel style ({days_per_stop:.1f} days per stop)."
        else:
            score_dwell = 12
            f_desc = f"Fast-paced city hopping ({days_per_stop:.1f} days/stop; transit overhead)."
    factors.append({'name': 'City Pacing & Dwell', 'score': score_dwell, 'max': 25, 'description': f_desc})

    # 4. Itinerary Completeness (0-20)
    score_comp = 0
    comp_details = []
    if stops_count > 0:
        score_comp += 5
        comp_details.append("Stops defined")
    if acts_count >= 2:
        score_comp += 5
        comp_details.append("Activities scheduled")
    if expenses:
        score_comp += 5
        comp_details.append("Logistics accounted")
    if trip_dict.get('description') or trip_dict.get('cover_image'):
        score_comp += 5
        comp_details.append("Profile details")
    factors.append({'name': 'Itinerary Completeness', 'score': score_comp, 'max': 20, 'description': ", ".join(comp_details) if comp_details else "Draft stage"})

    total_score = min(100, max(0, score_budget + score_density + score_dwell + score_comp))

    category_breakdown = {
        'transportation': transport,
        'accommodation': stay,
        'activities': total_act_cost,
        'food': food,
        'miscellaneous': misc
    }

    return {
        'duration_days': duration_days,
        'status': status,
        'stops_count': stops_count,
        'activities_count': acts_count,
        'cost_transportation': transport,
        'cost_accommodation': stay,
        'cost_activities': total_act_cost,
        'cost_food': food,
        'cost_miscellaneous': misc,
        'total_estimated_cost': total_cost,
        'cost_per_traveler': cost_per_traveler,
        'cost_per_day': cost_per_day,
        'remaining_budget': remaining_budget,
        'budget_utilization': round(budget_utilization, 1),
        'category_breakdown': category_breakdown,
        'trip_balance_score': total_score,
        'balance_score_summary': factors,
        'budget_intelligence_alerts': alerts
    }

def format_currency_text(amount, currency='INR'):
    sym = '₹' if currency == 'INR' else ('$' if currency == 'USD' else ('€' if currency == 'EUR' else f"{currency} "))
    return f"{sym}{amount:,.0f}"

def calculate_hotel_recommendation(hotel, nights=1, rooms=1, guests=2, trip_budget=0.0, remaining_budget=None, travel_style='balanced'):
    """
    Calculates 0-100 normalized recommendation score, dynamic category label,
    budget compatibility flag, and structured 'Why this hotel?' explanation.
    """
    price_per_night = float(hotel.get('price_per_night') or 0.0)
    rating = float(hotel.get('rating') or 4.0)
    review_count = int(hotel.get('review_count') or 100)
    category = (hotel.get('hotel_category') or 'mid_range').lower()
    location_score = float(hotel.get('location_score') or 9.0)
    cleanliness_score = float(hotel.get('cleanliness_score') or 9.0)
    service_score = float(hotel.get('service_score') or 9.0)
    value_score = float(hotel.get('value_score') or 9.0)
    popularity_score = float(hotel.get('popularity_score') or 80.0)
    amenities = (hotel.get('amenities') or '').lower()
    
    nights = max(1, int(nights or 1))
    rooms = max(1, int(rooms or 1))
    stay_cost = price_per_night * nights * rooms
    
    # 1. Price Fit (25 pts)
    price_score = 25.0
    fits_budget = True
    budget_impact = "fits"
    if remaining_budget is not None and remaining_budget > 0:
        if stay_cost <= remaining_budget:
            price_score = 25.0
            fits_budget = True
            budget_impact = "fits"
        elif stay_cost <= remaining_budget * 1.25:
            overrun_ratio = (stay_cost - remaining_budget) / (remaining_budget * 0.25)
            price_score = max(15.0, 25.0 - (overrun_ratio * 10.0))
            fits_budget = False
            budget_impact = "near_limit"
        else:
            overrun_ratio = (stay_cost - remaining_budget) / remaining_budget
            price_score = max(5.0, 15.0 - min(10.0, overrun_ratio * 5.0))
            fits_budget = False
            budget_impact = "exceeds"
    elif trip_budget > 0 and remaining_budget is not None and remaining_budget <= 0:
        price_score = max(5.0, 18.0 - (stay_cost / 5000.0))
        fits_budget = False
        budget_impact = "exceeds"
    else:
        price_score = (value_score / 10.0) * 25.0

    # 2. Rating Score (20 pts)
    rating_score = (min(5.0, max(1.0, rating)) / 5.0) * 20.0

    # 3. Location Score (15 pts)
    loc_score = (min(10.0, max(1.0, location_score)) / 10.0) * 15.0

    # 4. Travel Style Match (15 pts)
    style = (travel_style or 'balanced').lower()
    style_score = 15.0
    if style == 'budget':
        if category in ('budget', 'economy'):
            style_score = 15.0
        elif category == 'mid_range':
            style_score = 10.0
        else:
            style_score = 5.0
    elif style == 'luxury':
        if category in ('luxury', 'premium'):
            style_score = 15.0
        elif category == 'mid_range':
            style_score = 9.0
        else:
            style_score = 4.0
    elif style == 'family':
        if 'family_rooms' in amenities or 'pool' in amenities:
            style_score = 15.0
        elif int(hotel.get('max_guests') or 2) >= 3:
            style_score = 13.0
        else:
            style_score = 9.0
    elif style == 'relaxed':
        if 'pool' in amenities or 'spa' in amenities or 'beach' in amenities:
            style_score = 15.0
        else:
            style_score = 10.0
    elif style == 'adventure':
        if location_score >= 9.0 and ('parking' in amenities or category in ('budget', 'economy', 'mid_range')):
            style_score = 15.0
        else:
            style_score = 11.0
    else:
        style_score = 15.0

    # 5. Amenities Score (10 pts)
    present_amenities = [a.strip() for a in amenities.split(',') if a.strip()]
    amenities_score = min(10.0, (len(present_amenities) / 5.0) * 10.0)

    # 6. Popularity Score (5 pts)
    pop_score = (min(100.0, max(0.0, popularity_score)) / 100.0) * 5.0

    # 7. Value Score (10 pts)
    val_score = (min(10.0, max(0.0, value_score)) / 10.0) * 10.0

    total_match = min(100, max(10, int(round(price_score + rating_score + loc_score + style_score + amenities_score + pop_score + val_score))))

    if total_match >= 90:
        match_tier = "Excellent Match"
    elif total_match >= 78:
        match_tier = "Great Match"
    elif total_match >= 65:
        match_tier = "Good Match"
    else:
        match_tier = "Fair Match"

    # Category Labels
    badges = []
    if total_match >= 90:
        badges.append({"label": "🏆 Best Overall", "class": "badge-best-overall"})
    if category in ('budget', 'economy') and price_score >= 20.0:
        badges.append({"label": "💰 Best Budget", "class": "badge-best-budget"})
    if rating >= 4.7:
        badges.append({"label": "⭐ Best Rated", "class": "badge-best-rated"})
    if location_score >= 9.4:
        badges.append({"label": "📍 Best Location", "class": "badge-best-location"})
    if value_score >= 9.4:
        badges.append({"label": "✨ Best Value", "class": "badge-best-value"})
    if category == 'luxury':
        badges.append({"label": "🏨 Luxury Pick", "class": "badge-luxury"})
    if 'family_rooms' in amenities or (style == 'family' and 'pool' in amenities):
        badges.append({"label": "👨‍👩‍👧 Best for Families", "class": "badge-family"})
    if 'pool' in amenities and 'spa' in amenities:
        badges.append({"label": "🌿 Best for Relaxed Travel", "class": "badge-relaxed"})
    if style == 'adventure' and location_score >= 9.0:
        badges.append({"label": "🎒 Best for Adventure", "class": "badge-adventure"})

    primary_badge = badges[0] if badges else {"label": "✨ Recommended", "class": "badge-top-rec"}

    # "Why this hotel?" data-driven points
    why_points = []
    curr = hotel.get('currency', 'INR')
    if remaining_budget is not None and remaining_budget > 0:
        if fits_budget:
            why_points.append(f"Fits within your remaining trip budget ({format_currency_text(remaining_budget, curr)} available).")
        else:
            diff = stay_cost - remaining_budget
            why_points.append(f"Estimated stay ({format_currency_text(stay_cost, curr)}) exceeds remaining budget by {format_currency_text(diff, curr)}.")
    else:
        why_points.append(f"Nightly rate of {format_currency_text(price_per_night, curr)} with strong value score ({value_score}/10).")

    why_points.append(f"{rating}/5.0 guest rating with {review_count:,} verified traveler reviews.")
    
    if location_score >= 9.0:
        why_points.append(f"Outstanding location score of {location_score}/10 with easy access to city attractions.")
    
    why_points.append(f"Well-suited for your {style.capitalize()} travel style with {category.replace('_', '-').title()} amenities.")

    key_amenities_formatted = []
    for a in present_amenities[:4]:
        key_amenities_formatted.append(a.replace('_', ' ').title())
    if key_amenities_formatted:
        why_points.append(f"Includes: {', '.join(key_amenities_formatted)}.")

    return {
        'total_stay_cost': stay_cost,
        'recommendation_score': total_match,
        'match_tier': match_tier,
        'primary_badge': primary_badge,
        'all_badges': badges,
        'fits_budget': fits_budget,
        'budget_impact': budget_impact,
        'why_points': why_points,
        'sub_scores': {
            'price_fit': round(price_score, 1),
            'rating': round(rating_score, 1),
            'location': round(loc_score, 1),
            'style_match': round(style_score, 1),
            'amenities': round(amenities_score, 1),
            'popularity': round(pop_score, 1),
            'value': round(val_score, 1)
        }
    }



class GlobeTrotterRequestHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.join(os.path.dirname(__file__), "static"), **kwargs)

    def _send_json(self, data, status=200):
        body = json.dumps(data, default=date_converter).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Session-Token')
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, message, status=400):
        self._send_json({'error': message, 'success': False}, status=status)

    def _read_json_body(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length == 0:
                return {}
            raw = self.rfile.read(length).decode('utf-8')
            return json.loads(raw)
        except Exception as e:
            return {}

    def _get_current_user(self, cur):
        auth_header = self.headers.get('Authorization') or ''
        session_token = self.headers.get('X-Session-Token') or ''
        
        if auth_header.startswith('Bearer '):
            session_token = auth_header.split('Bearer ', 1)[1].strip()

        if not session_token or session_token not in SESSIONS:
            return None

        user_id = SESSIONS[session_token]
        cur.execute("SELECT id, name, email, preferred_currency, preferred_travel_style, preferred_language, avatar_url, bio, role FROM res_users WHERE id = %s", (user_id,))
        return cur.fetchone()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Session-Token')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Static assets routing
        if not path.startswith('/api/'):
            # Allow public shared route SPA direct access
            if path.startswith('/shared/'):
                self.path = '/index.html'
            return super().do_GET()

        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            user = self._get_current_user(cur)

            # 1. Auth Me
            if path == '/api/v1/auth/me':
                if not user:
                    conn.close()
                    return self._send_error('Not authenticated', status=401)
                conn.close()
                return self._send_json({'success': True, 'user': dict(user)})

            # 2. Destinations Catalog
            elif path == '/api/v1/destinations':
                search_q = query.get('q', [''])[0].strip()
                region = query.get('region', [''])[0].strip()
                style = query.get('style', [''])[0].strip()

                sql = "SELECT c.*, COUNT(a.id) as activity_count FROM globetrotter_city c LEFT JOIN globetrotter_activity a ON c.id = a.city_id WHERE 1=1"
                params = []

                if search_q:
                    sql += " AND (c.name ILIKE %s OR c.country ILIKE %s)"
                    params.extend([f"%{search_q}%", f"%{search_q}%"])
                if region and region != 'all':
                    sql += " AND c.region = %s"
                    params.append(region)
                if style and style != 'all':
                    sql += " AND c.travel_styles ILIKE %s"
                    params.append(f"%{style}%")

                sql += " GROUP BY c.id ORDER BY c.popularity DESC, c.name ASC"
                cur.execute(sql, params)
                cities = cur.fetchall()
                conn.close()
                return self._send_json({'success': True, 'destinations': [dict(c) for c in cities]})

            # 3. Destination Detail
            elif path.startswith('/api/v1/destinations/'):
                city_id = path.split('/')[-1]
                cur.execute("SELECT * FROM globetrotter_city WHERE id = %s", (city_id,))
                city = cur.fetchone()
                if not city:
                    conn.close()
                    return self._send_error('Destination not found', status=404)
                
                cur.execute("SELECT * FROM globetrotter_activity WHERE city_id = %s ORDER BY popularity DESC", (city_id,))
                activities = cur.fetchall()
                res = dict(city)
                res['activities'] = [dict(a) for a in activities]
                conn.close()
                return self._send_json({'success': True, 'destination': res})

            # 4. Activities Search & Filter
            elif path == '/api/v1/activities':
                city_id = query.get('city_id', [''])[0]
                category = query.get('category', [''])[0]
                search_q = query.get('q', [''])[0].strip()

                sql = "SELECT a.*, c.name as city_name, c.country as country_name FROM globetrotter_activity a JOIN globetrotter_city c ON a.city_id = c.id WHERE 1=1"
                params = []

                if city_id:
                    sql += " AND a.city_id = %s"
                    params.append(city_id)
                if category and category != 'all':
                    sql += " AND a.category = %s"
                    params.append(category)
                if search_q:
                    sql += " AND (a.name ILIKE %s OR a.description ILIKE %s)"
                    params.extend([f"%{search_q}%", f"%{search_q}%"])

                sql += " ORDER BY a.popularity DESC, a.name ASC"
                cur.execute(sql, params)
                acts = cur.fetchall()
                conn.close()
                return self._send_json({'success': True, 'activities': [dict(a) for a in acts]})

            # 4b. Hotel Recommendations & Discovery
            elif path == '/api/v1/hotels/recommendations':
                city_id = query.get('city_id', [''])[0]
                city_name = query.get('city', [''])[0].strip()
                trip_id = query.get('trip_id', [''])[0]
                check_in = query.get('check_in', [''])[0]
                check_out = query.get('check_out', [''])[0]
                guests = int(query.get('guests', ['2'])[0] or 2)
                rooms = int(query.get('rooms', ['1'])[0] or 1)
                category = query.get('category', [''])[0]
                min_rating = float(query.get('min_rating', ['0'])[0] or 0)
                min_price = float(query.get('min_price', ['0'])[0] or 0)
                max_price = float(query.get('max_price', ['0'])[0] or 0)
                req_amenities = query.get('amenities', [''])[0]
                sort_by = query.get('sort_by', ['recommended'])[0]

                # Calculate nights
                nights = 1
                if check_in and check_out:
                    try:
                        d_in = datetime.strptime(check_in, '%Y-%m-%d').date()
                        d_out = datetime.strptime(check_out, '%Y-%m-%d').date()
                        if d_out > d_in:
                            nights = (d_out - d_in).days
                    except Exception:
                        nights = 1

                # Trip context for budget-aware scoring
                trip_budget = 0.0
                remaining_budget = None
                travel_style = 'balanced'
                if trip_id:
                    try:
                        cur.execute("SELECT * FROM globetrotter_trip WHERE id = %s", (int(trip_id),))
                        t = cur.fetchone()
                        if t:
                            travel_style = t['travel_style'] or 'balanced'
                            trip_budget = float(t['total_budget'] or 0.0)
                            cur.execute("SELECT * FROM globetrotter_trip_activity WHERE trip_id = %s", (t['id'],))
                            acts = cur.fetchall()
                            cur.execute("SELECT * FROM globetrotter_expense WHERE trip_id = %s", (t['id'],))
                            exps = cur.fetchall()
                            cur.execute("SELECT * FROM globetrotter_trip_stop WHERE trip_id = %s", (t['id'],))
                            stps = cur.fetchall()
                            comp = compute_trip_business_logic(dict(t), stps, acts, exps)
                            remaining_budget = comp.get('remaining_budget')
                    except Exception:
                        pass

                sql = """
                    SELECT h.*, c.name as city_name, c.country as country_name 
                    FROM globetrotter_hotel h 
                    JOIN globetrotter_city c ON h.city_id = c.id 
                    WHERE h.active = TRUE
                """
                params = []
                if city_id:
                    sql += " AND h.city_id = %s"
                    params.append(int(city_id))
                elif city_name:
                    sql += " AND (c.name ILIKE %s OR h.address ILIKE %s)"
                    params.extend([f"%{city_name}%", f"%{city_name}%"])

                if category and category != 'all':
                    sql += " AND h.hotel_category = %s"
                    params.append(category)
                if min_rating > 0:
                    sql += " AND h.rating >= %s"
                    params.append(min_rating)
                if min_price > 0:
                    sql += " AND h.price_per_night >= %s"
                    params.append(min_price)
                if max_price > 0:
                    sql += " AND h.price_per_night <= %s"
                    params.append(max_price)

                cur.execute(sql, params)
                hotels = [dict(h) for h in cur.fetchall()]

                # Apply amenities filter if present
                if req_amenities and req_amenities != 'all':
                    filtered = []
                    needed = [a.strip().lower() for a in req_amenities.split(',') if a.strip()]
                    for h in hotels:
                        h_amen = (h.get('amenities') or '').lower()
                        if all(a in h_amen for a in needed):
                            filtered.append(h)
                    hotels = filtered

                # Compute recommendation score and insights for each hotel
                scored_hotels = []
                for h in hotels:
                    rec_data = calculate_hotel_recommendation(
                        h, nights=nights, rooms=rooms, guests=guests,
                        trip_budget=trip_budget, remaining_budget=remaining_budget,
                        travel_style=travel_style
                    )
                    h.update(rec_data)
                    scored_hotels.append(h)

                # Sort
                if sort_by == 'price_asc':
                    scored_hotels.sort(key=lambda x: (x.get('price_per_night', 0), -x.get('recommendation_score', 0)))
                elif sort_by == 'price_desc':
                    scored_hotels.sort(key=lambda x: (-x.get('price_per_night', 0), -x.get('recommendation_score', 0)))
                elif sort_by == 'rating':
                    scored_hotels.sort(key=lambda x: (-x.get('rating', 0), -x.get('recommendation_score', 0)))
                elif sort_by == 'value':
                    scored_hotels.sort(key=lambda x: (-x.get('value_score', 0), -x.get('recommendation_score', 0)))
                elif sort_by == 'location':
                    scored_hotels.sort(key=lambda x: (-x.get('location_score', 0), -x.get('recommendation_score', 0)))
                else: # 'recommended'
                    scored_hotels.sort(key=lambda x: (-x.get('recommendation_score', 0), -x.get('popularity_score', 0)))

                conn.close()
                return self._send_json({
                    'success': True,
                    'hotels': scored_hotels,
                    'search_criteria': {
                        'city_id': city_id,
                        'city_name': city_name,
                        'check_in': check_in,
                        'check_out': check_out,
                        'nights': nights,
                        'rooms': rooms,
                        'guests': guests,
                        'remaining_budget': remaining_budget,
                        'travel_style': travel_style
                    }
                })

            # 4c. Single Hotel Profile
            elif path.startswith('/api/v1/hotels/') and not any(sub in path for sub in ['/recommendations', '/compare']):
                try:
                    hotel_id = int(path.split('/')[-1])
                except ValueError:
                    conn.close()
                    return self._send_error('Invalid hotel ID')

                cur.execute("""
                    SELECT h.*, c.name as city_name, c.country as country_name, c.region as city_region
                    FROM globetrotter_hotel h
                    JOIN globetrotter_city c ON h.city_id = c.id
                    WHERE h.id = %s;
                """, (hotel_id,))
                hotel = cur.fetchone()
                if not hotel:
                    conn.close()
                    return self._send_error('Hotel not found', status=404)

                h_dict = dict(hotel)
                rec = calculate_hotel_recommendation(h_dict)
                h_dict.update(rec)
                conn.close()
                return self._send_json({'success': True, 'hotel': h_dict})

            # 4d. Hotel Comparison Matrix
            elif path == '/api/v1/hotels/compare':
                ids_str = query.get('ids', [''])[0]
                if not ids_str:
                    conn.close()
                    return self._send_error('No hotel IDs specified for comparison')
                
                try:
                    ids = [int(i.strip()) for i in ids_str.split(',') if i.strip()]
                except ValueError:
                    conn.close()
                    return self._send_error('Invalid hotel IDs')

                if not ids:
                    conn.close()
                    return self._send_error('No valid hotel IDs provided')

                nights = int(query.get('nights', ['1'])[0] or 1)
                rooms = int(query.get('rooms', ['1'])[0] or 1)
                trip_id = query.get('trip_id', [''])[0]

                trip_budget = 0.0
                remaining_budget = None
                travel_style = 'balanced'
                if trip_id:
                    try:
                        cur.execute("SELECT * FROM globetrotter_trip WHERE id = %s", (int(trip_id),))
                        t = cur.fetchone()
                        if t:
                            travel_style = t['travel_style'] or 'balanced'
                            trip_budget = float(t['total_budget'] or 0.0)
                            cur.execute("SELECT * FROM globetrotter_trip_activity WHERE trip_id = %s", (t['id'],))
                            acts = cur.fetchall()
                            cur.execute("SELECT * FROM globetrotter_expense WHERE trip_id = %s", (t['id'],))
                            exps = cur.fetchall()
                            cur.execute("SELECT * FROM globetrotter_trip_stop WHERE trip_id = %s", (t['id'],))
                            stps = cur.fetchall()
                            comp = compute_trip_business_logic(dict(t), stps, acts, exps)
                            remaining_budget = comp.get('remaining_budget')
                    except Exception:
                        pass

                cur.execute("""
                    SELECT h.*, c.name as city_name, c.country as country_name
                    FROM globetrotter_hotel h
                    JOIN globetrotter_city c ON h.city_id = c.id
                    WHERE h.id = ANY(%s);
                """, (ids,))
                hotels = [dict(h) for h in cur.fetchall()]
                for h in hotels:
                    rec = calculate_hotel_recommendation(
                        h, nights=nights, rooms=rooms,
                        trip_budget=trip_budget, remaining_budget=remaining_budget,
                        travel_style=travel_style
                    )
                    h.update(rec)

                conn.close()
                return self._send_json({'success': True, 'comparison': hotels, 'nights': nights, 'rooms': rooms})

            # Weather Forecast API
            elif path == '/api/v1/weather':
                city_id = query.get('city_id', [''])[0]
                lat = query.get('lat', [''])[0]
                lon = query.get('lon', [''])[0]
                start_date = query.get('start_date', [''])[0]
                end_date = query.get('end_date', [''])[0]
                city_name = query.get('city_name', [''])[0]

                if city_id:
                    cur.execute("SELECT name, latitude, longitude FROM globetrotter_city WHERE id = %s", (city_id,))
                    crow = cur.fetchone()
                    if crow:
                        city_name = crow['name']
                        lat = crow['latitude'] or lat
                        lon = crow['longitude'] or lon

                f_data = WeatherService.fetch_weather_forecast(
                    latitude=lat or 28.6139,
                    longitude=lon or 77.2090,
                    start_date_str=start_date,
                    end_date_str=end_date,
                    city_name=city_name
                )
                conn.close()
                return self._send_json({'success': True, 'forecast': f_data})

            # Trip Weather Analysis API
            elif path.startswith('/api/v1/trips/') and path.endswith('/weather-analysis'):
                if not user:
                    conn.close()
                    return self._send_error('Authentication required', status=401)

                try:
                    trip_id = int(path.split('/')[4])
                except ValueError:
                    conn.close()
                    return self._send_error('Invalid trip ID')

                cur.execute("SELECT * FROM globetrotter_trip WHERE id = %s", (trip_id,))
                trip = cur.fetchone()
                if not trip:
                    conn.close()
                    return self._send_error('Trip not found', status=404)

                if trip['user_id'] != user['id'] and user.get('role') != 'admin' and not trip['is_public']:
                    conn.close()
                    return self._send_error('Access Denied', status=403)

                t_dict = dict(trip)
                cur.execute("""
                    SELECT s.*, c.name as city_name, c.country as country_name, c.latitude, c.longitude
                    FROM globetrotter_trip_stop s
                    JOIN globetrotter_city c ON s.city_id = c.id
                    WHERE s.trip_id = %s
                    ORDER BY s.sequence ASC, s.arrival_date ASC;
                """, (trip_id,))
                stops = [dict(s) for s in cur.fetchall()]

                cur.execute("""
                    SELECT a.*, c.name as city_name, s.city_id
                    FROM globetrotter_trip_activity a
                    LEFT JOIN globetrotter_trip_stop s ON a.stop_id = s.id
                    LEFT JOIN globetrotter_city c ON s.city_id = c.id
                    WHERE a.trip_id = %s
                    ORDER BY a.day_number ASC, a.sequence ASC;
                """, (trip_id,))
                activities = [dict(a) for a in cur.fetchall()]

                city_ids = list(set([s['city_id'] for s in stops if s.get('city_id')]))
                catalog_by_city = {}
                if city_ids:
                    cur.execute("SELECT * FROM globetrotter_activity WHERE city_id = ANY(%s) ORDER BY popularity DESC", (city_ids,))
                    for ca in cur.fetchall():
                        catalog_by_city.setdefault(ca['city_id'], []).append(dict(ca))

                analysis = WeatherService.generate_trip_weather_intelligence(t_dict, stops, activities, catalog_by_city)
                conn.close()
                return self._send_json({'success': True, 'analysis': analysis})

            # 5. Trips List
            elif path == '/api/v1/trips':
                if not user:
                    conn.close()
                    return self._send_error('Authentication required', status=401)

                status_filter = query.get('status', ['all'])[0]
                cur.execute("""
                    SELECT t.*, u.name as owner_name 
                    FROM globetrotter_trip t 
                    JOIN res_users u ON t.user_id = u.id 
                    WHERE t.user_id = %s 
                    ORDER BY t.start_date ASC, t.id DESC;
                """, (user['id'],))
                trips = cur.fetchall()

                full_trips = []
                for t in trips:
                    t_dict = dict(t)
                    # fetch child items to compute fields
                    cur.execute("SELECT * FROM globetrotter_trip_stop WHERE trip_id = %s ORDER BY sequence ASC, arrival_date ASC", (t_dict['id'],))
                    stops = cur.fetchall()
                    cur.execute("SELECT * FROM globetrotter_trip_activity WHERE trip_id = %s ORDER BY day_number ASC, sequence ASC", (t_dict['id'],))
                    acts = cur.fetchall()
                    cur.execute("SELECT * FROM globetrotter_expense WHERE trip_id = %s ORDER BY date ASC", (t_dict['id'],))
                    exps = cur.fetchall()

                    computed = compute_trip_business_logic(t_dict, stops, acts, exps)
                    t_dict.update(computed)
                    
                    if status_filter == 'all' or t_dict['status'] == status_filter:
                        full_trips.append(t_dict)

                conn.close()
                return self._send_json({'success': True, 'trips': full_trips})

            # 6. Single Trip Details
            elif path.startswith('/api/v1/trips/') and not any(sub in path for sub in ['/duplicate', '/share', '/stops', '/activities', '/expenses']):
                if not user:
                    conn.close()
                    return self._send_error('Authentication required', status=401)
                
                try:
                    trip_id = int(path.split('/')[-1])
                except ValueError:
                    conn.close()
                    return self._send_error('Invalid trip ID')

                cur.execute("SELECT * FROM globetrotter_trip WHERE id = %s", (trip_id,))
                trip = cur.fetchone()
                if not trip:
                    conn.close()
                    return self._send_error('Trip not found', status=404)

                # Security check (Record Rules: user can only view their own trip or public trip)
                if trip['user_id'] != user['id'] and user.get('role') != 'admin' and not trip['is_public']:
                    conn.close()
                    return self._send_error('Access Denied: You do not have permission to view this trip', status=403)

                t_dict = dict(trip)
                # fetch stops with city meta
                cur.execute("""
                    SELECT s.*, c.name as city_name, c.country as country_name, c.cover_image as city_image, c.region as city_region
                    FROM globetrotter_trip_stop s
                    JOIN globetrotter_city c ON s.city_id = c.id
                    WHERE s.trip_id = %s
                    ORDER BY s.sequence ASC, s.arrival_date ASC;
                """, (trip_id,))
                stops = [dict(s) for s in cur.fetchall()]

                # fetch scheduled activities
                cur.execute("""
                    SELECT a.*, c.name as city_name
                    FROM globetrotter_trip_activity a
                    LEFT JOIN globetrotter_trip_stop s ON a.stop_id = s.id
                    LEFT JOIN globetrotter_city c ON s.city_id = c.id
                    WHERE a.trip_id = %s
                    ORDER BY a.day_number ASC, a.sequence ASC, a.scheduled_time ASC;
                """, (trip_id,))
                activities = [dict(a) for a in cur.fetchall()]

                # fetch expenses
                cur.execute("""
                    SELECT e.*, c.name as city_name
                    FROM globetrotter_expense e
                    LEFT JOIN globetrotter_trip_stop s ON e.stop_id = s.id
                    LEFT JOIN globetrotter_city c ON s.city_id = c.id
                    WHERE e.trip_id = %s
                    ORDER BY e.date ASC, e.id ASC;
                """, (trip_id,))
                expenses = [dict(e) for e in cur.fetchall()]

                # fetch hotel bookings
                cur.execute("""
                    SELECT th.*, h.name as hotel_name, h.image as hotel_image, h.rating as hotel_rating,
                           h.address as hotel_address, h.hotel_category, h.amenities as hotel_amenities,
                           c.name as city_name, c.country as country_name
                    FROM globetrotter_trip_hotel th
                    JOIN globetrotter_hotel h ON th.hotel_id = h.id
                    LEFT JOIN globetrotter_trip_stop s ON th.stop_id = s.id
                    LEFT JOIN globetrotter_city c ON s.city_id = c.id
                    WHERE th.trip_id = %s
                    ORDER BY th.check_in ASC, th.id ASC;
                """, (trip_id,))
                hotels = [dict(h) for h in cur.fetchall()]

                # attach hotel to stop
                for s in stops:
                    s['hotel_booking'] = next((h for h in hotels if h.get('stop_id') == s['id']), None)

                computed = compute_trip_business_logic(t_dict, stops, activities, expenses)
                t_dict.update(computed)
                t_dict['stops'] = stops
                t_dict['activities'] = activities
                t_dict['hotels'] = hotels
                t_dict['expenses'] = expenses

                conn.close()
                return self._send_json({'success': True, 'trip': t_dict})

            # 7. Public Shared Trip Viewer
            elif path.startswith('/api/v1/shared/'):
                token = path.split('/')[-1]
                cur.execute("""
                    SELECT t.*, u.name as owner_name 
                    FROM globetrotter_trip t 
                    JOIN res_users u ON t.user_id = u.id 
                    WHERE t.share_token = %s AND t.is_public = TRUE;
                """, (token,))
                trip = cur.fetchone()
                if not trip:
                    conn.close()
                    return self._send_error('Shared itinerary not found or has expired.', status=404)

                trip_id = trip['id']
                t_dict = dict(trip)

                # Increment view count
                cur.execute("UPDATE globetrotter_shared_trip SET view_count = view_count + 1 WHERE share_token = %s", (token,))

                # fetch stops
                cur.execute("""
                    SELECT s.*, c.name as city_name, c.country as country_name, c.cover_image as city_image, c.region as city_region
                    FROM globetrotter_trip_stop s
                    JOIN globetrotter_city c ON s.city_id = c.id
                    WHERE s.trip_id = %s
                    ORDER BY s.sequence ASC, s.arrival_date ASC;
                """, (trip_id,))
                stops = [dict(s) for s in cur.fetchall()]

                # fetch activities
                cur.execute("""
                    SELECT a.*, c.name as city_name
                    FROM globetrotter_trip_activity a
                    LEFT JOIN globetrotter_trip_stop s ON a.stop_id = s.id
                    LEFT JOIN globetrotter_city c ON s.city_id = c.id
                    WHERE a.trip_id = %s
                    ORDER BY a.day_number ASC, a.sequence ASC;
                """, (trip_id,))
                activities = [dict(a) for a in cur.fetchall()]

                # fetch expenses
                cur.execute("SELECT * FROM globetrotter_expense WHERE trip_id = %s ORDER BY date ASC", (trip_id,))
                expenses = [dict(e) for e in cur.fetchall()]

                # fetch hotel bookings
                cur.execute("""
                    SELECT th.*, h.name as hotel_name, h.image as hotel_image, h.rating as hotel_rating,
                           h.address as hotel_address, h.hotel_category, h.amenities as hotel_amenities,
                           c.name as city_name, c.country as country_name
                    FROM globetrotter_trip_hotel th
                    JOIN globetrotter_hotel h ON th.hotel_id = h.id
                    LEFT JOIN globetrotter_trip_stop s ON th.stop_id = s.id
                    LEFT JOIN globetrotter_city c ON s.city_id = c.id
                    WHERE th.trip_id = %s
                    ORDER BY th.check_in ASC, th.id ASC;
                """, (trip_id,))
                hotels = [dict(h) for h in cur.fetchall()]

                for s in stops:
                    s['hotel_booking'] = next((h for h in hotels if h.get('stop_id') == s['id']), None)

                computed = compute_trip_business_logic(t_dict, stops, activities, expenses)
                t_dict.update(computed)

                # Privacy: If share_budget is False, hide financial details
                if not t_dict.get('share_budget'):
                    t_dict['total_budget'] = 0.0
                    t_dict['total_estimated_cost'] = 0.0
                    t_dict['cost_per_traveler'] = 0.0
                    t_dict['cost_per_day'] = 0.0
                    t_dict['remaining_budget'] = 0.0
                    t_dict['budget_utilization'] = 0.0
                    t_dict['category_breakdown'] = {}
                    t_dict['budget_intelligence_alerts'] = []
                    expenses = []
                    for a in activities:
                        a['estimated_cost'] = 0.0
                    for h in hotels:
                        h['price_per_night'] = 0.0
                        h['total_cost'] = 0.0

                t_dict['stops'] = stops
                t_dict['activities'] = activities
                t_dict['hotels'] = hotels
                t_dict['expenses'] = expenses
                conn.close()
                return self._send_json({'success': True, 'trip': t_dict})

            # 8. Saved Bookmarks
            elif path == '/api/v1/saved-destinations':
                if not user:
                    conn.close()
                    return self._send_error('Authentication required', status=401)
                cur.execute("""
                    SELECT c.*, sd.created_at as saved_at 
                    FROM globetrotter_saved_destination sd
                    JOIN globetrotter_city c ON sd.city_id = c.id
                    WHERE sd.user_id = %s
                    ORDER BY sd.created_at DESC;
                """, (user['id'],))
                saved = cur.fetchall()
                conn.close()
                return self._send_json({'success': True, 'saved_destinations': [dict(s) for s in saved]})

            # 9. Admin Analytics
            elif path == '/api/v1/admin/analytics':
                if not user or user.get('role') != 'admin':
                    conn.close()
                    return self._send_error('Admin privileges required.', status=403)

                cur.execute("SELECT COUNT(*) FROM res_users;")
                total_users = cur.fetchone()['count']

                cur.execute("SELECT COUNT(*) FROM globetrotter_trip;")
                total_trips = cur.fetchone()['count']

                cur.execute("SELECT AVG(total_budget) as avg_budget FROM globetrotter_trip WHERE total_budget > 0;")
                avg_budget_row = cur.fetchone()
                avg_budget = float(avg_budget_row['avg_budget'] or 0.0)

                # Popular Cities
                cur.execute("""
                    SELECT c.name, c.country, COUNT(s.id) as visit_count
                    FROM globetrotter_city c
                    LEFT JOIN globetrotter_trip_stop s ON c.id = s.city_id
                    GROUP BY c.id, c.name, c.country
                    ORDER BY visit_count DESC, c.popularity DESC
                    LIMIT 5;
                """)
                top_cities = [dict(c) for c in cur.fetchall()]

                # Style distribution
                cur.execute("""
                    SELECT travel_style, COUNT(*) as count
                    FROM globetrotter_trip
                    GROUP BY travel_style
                    ORDER BY count DESC;
                """)
                styles = [dict(s) for s in cur.fetchall()]

                conn.close()
                return self._send_json({
                    'success': True,
                    'analytics': {
                        'total_users': total_users,
                        'total_trips': total_trips,
                        'avg_budget': avg_budget,
                        'top_cities': top_cities,
                        'styles': styles
                    }
                })

        conn.close()
        return self._send_error('Endpoint not found', status=404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._read_json_body()

        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            user = self._get_current_user(cur)

            # 1. Signup
            if path == '/api/v1/auth/signup':
                name = (body.get('name') or '').strip()
                email = (body.get('email') or '').strip().lower()
                password = body.get('password') or ''

                if not name or not email or not password:
                    conn.close()
                    return self._send_error('Name, email, and password are required.')
                if len(password) < 6:
                    conn.close()
                    return self._send_error('Password must be at least 6 characters.')

                cur.execute("SELECT id FROM res_users WHERE email = %s", (email,))
                if cur.fetchone():
                    conn.close()
                    return self._send_error('An account with this email already exists.')

                cur.execute("""
                    INSERT INTO res_users (name, email, password_hash, preferred_currency, preferred_travel_style, role)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, name, email, preferred_currency, preferred_travel_style, role;
                """, (name, email, pbkdf2_sha256.hash(password), body.get('preferred_currency', 'INR'), body.get('preferred_travel_style', 'balanced'), 'traveler'))
                new_user = cur.fetchone()
                
                token = secrets.token_hex(24)
                SESSIONS[token] = new_user['id']
                conn.close()
                return self._send_json({'success': True, 'token': token, 'user': dict(new_user)})

            # 2. Login
            elif path == '/api/v1/auth/login':
                email = (body.get('email') or '').strip().lower()
                password = body.get('password') or ''

                if not email or not password:
                    conn.close()
                    return self._send_error('Email and password are required.')

                cur.execute("SELECT id, name, email, password_hash, preferred_currency, preferred_travel_style, role FROM res_users WHERE email = %s", (email,))
                existing = cur.fetchone()
                if not existing or not pbkdf2_sha256.verify(password, existing['password_hash']):
                    conn.close()
                    return self._send_error('Invalid email or password.')

                token = secrets.token_hex(24)
                SESSIONS[token] = existing['id']
                u_res = dict(existing)
                u_res.pop('password_hash', None)
                conn.close()
                return self._send_json({'success': True, 'token': token, 'user': u_res})

            # 3. 1-Click Demo Login
            elif path == '/api/v1/auth/demo-login':
                role = body.get('role', 'traveler')
                target_email = 'admin@globetrotter.travel' if role == 'admin' else 'demo@globetrotter.travel'
                cur.execute("SELECT id, name, email, preferred_currency, preferred_travel_style, role FROM res_users WHERE email = %s", (target_email,))
                u = cur.fetchone()
                if not u:
                    conn.close()
                    return self._send_error('Demo account not configured.')
                token = secrets.token_hex(24)
                SESSIONS[token] = u['id']
                conn.close()
                return self._send_json({'success': True, 'token': token, 'user': dict(u)})

            # 4. Logout
            elif path == '/api/v1/auth/logout':
                auth_header = self.headers.get('Authorization') or ''
                if auth_header.startswith('Bearer '):
                    tok = auth_header.split('Bearer ', 1)[1].strip()
                    SESSIONS.pop(tok, None)
                conn.close()
                return self._send_json({'success': True, 'message': 'Logged out successfully.'})

            # 5. Create Trip
            elif path == '/api/v1/trips':
                if not user:
                    conn.close()
                    return self._send_error('Authentication required', status=401)

                name = (body.get('name') or '').strip()
                start_date = body.get('start_date')
                end_date = body.get('end_date')
                travelers = int(body.get('travelers_count') or 1)
                budget = float(body.get('total_budget') or 0.0)

                if not name:
                    conn.close()
                    return self._send_error('Trip name is required.')
                if not start_date or not end_date:
                    conn.close()
                    return self._send_error('Start date and end date are required.')
                if end_date < start_date:
                    conn.close()
                    return self._send_error('End date cannot be earlier than start date.')
                if budget < 0:
                    conn.close()
                    return self._send_error('Budget cannot be negative.')
                if travelers < 1:
                    conn.close()
                    return self._send_error('Travelers must be at least 1.')

                cover = body.get('cover_image')
                if not cover:
                    cover = "https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=1200&q=80"

                cur.execute("""
                    INSERT INTO globetrotter_trip (user_id, name, start_date, end_date, description, cover_image, currency, travelers_count, total_budget, travel_style, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    user['id'], name, start_date, end_date, body.get('description', ''),
                    cover, body.get('currency', 'INR'), travelers, budget,
                    body.get('travel_style', 'balanced'), 'upcoming'
                ))
                new_trip = cur.fetchone()
                conn.close()
                return self._send_json({'success': True, 'trip_id': new_trip['id'], 'message': 'Trip created successfully!'})

            # 6. Add Trip Stop
            elif path.startswith('/api/v1/trips/') and path.endswith('/stops'):
                if not user:
                    conn.close()
                    return self._send_error('Authentication required', status=401)

                trip_id = int(path.split('/')[4])
                cur.execute("SELECT * FROM globetrotter_trip WHERE id = %s", (trip_id,))
                trip = cur.fetchone()
                if not trip or (trip['user_id'] != user['id'] and user.get('role') != 'admin'):
                    conn.close()
                    return self._send_error('Trip not found or unauthorized', status=403)

                city_id = body.get('city_id')
                arrival_date = body.get('arrival_date') or str(trip['start_date'])
                departure_date = body.get('departure_date') or str(trip['end_date'])

                if not city_id:
                    conn.close()
                    return self._send_error('Destination City is required.')
                if departure_date < arrival_date:
                    conn.close()
                    return self._send_error('Stop departure date cannot be before arrival date.')

                # Calculate next sequence
                cur.execute("SELECT COALESCE(MAX(sequence), 0) + 10 as next_seq FROM globetrotter_trip_stop WHERE trip_id = %s", (trip_id,))
                seq = cur.fetchone()['next_seq']

                delta = (datetime.strptime(departure_date, '%Y-%m-%d').date() - datetime.strptime(arrival_date, '%Y-%m-%d').date()).days + 1
                duration = max(1, delta)

                cur.execute("""
                    INSERT INTO globetrotter_trip_stop (trip_id, city_id, sequence, arrival_date, departure_date, duration_days, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (trip_id, city_id, seq, arrival_date, departure_date, duration, body.get('notes', '')))
                stop_row = cur.fetchone()
                conn.close()
                return self._send_json({'success': True, 'stop_id': stop_row['id'], 'message': 'Destination stop added!'})

            # 7. Reorder Stops
            elif path.startswith('/api/v1/trips/') and path.endswith('/stops/reorder'):
                if not user:
                    conn.close()
                    return self._send_error('Authentication required', status=401)

                trip_id = int(path.split('/')[4])
                stop_ids = body.get('stop_ids', [])

                for idx, sid in enumerate(stop_ids):
                    cur.execute("UPDATE globetrotter_trip_stop SET sequence = %s WHERE id = %s AND trip_id = %s", (idx * 10 + 10, sid, trip_id))

                conn.close()
                return self._send_json({'success': True, 'message': 'Stops reordered successfully.'})

            # 8. Add Trip Activity
            elif path.startswith('/api/v1/trips/') and path.endswith('/activities'):
                if not user:
                    conn.close()
                    return self._send_error('Authentication required', status=401)

                trip_id = int(path.split('/')[4])
                cur.execute("SELECT * FROM globetrotter_trip WHERE id = %s", (trip_id,))
                trip = cur.fetchone()
                if not trip or (trip['user_id'] != user['id'] and user.get('role') != 'admin'):
                    conn.close()
                    return self._send_error('Unauthorized', status=403)

                name = (body.get('name') or '').strip()
                if not name:
                    conn.close()
                    return self._send_error('Activity name is required.')

                day_num = int(body.get('day_number') or 1)
                cost = float(body.get('estimated_cost') or 0.0)
                dur = float(body.get('duration_hours') or 2.0)
                time_slot = body.get('scheduled_time', '10:00')

                cur.execute("""
                    INSERT INTO globetrotter_trip_activity (trip_id, stop_id, activity_id, name, category, day_number, scheduled_time, duration_hours, estimated_cost, notes, image)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    trip_id, body.get('stop_id'), body.get('activity_id'), name,
                    body.get('category', 'sightseeing'), day_num, time_slot, dur, cost,
                    body.get('notes', ''), body.get('image', '')
                ))
                act_row = cur.fetchone()
                conn.close()
                return self._send_json({'success': True, 'activity_id': act_row['id'], 'message': 'Activity added to itinerary!'})

            # 8b. Add Trip Hotel Booking
            elif path.startswith('/api/v1/trips/') and path.endswith('/hotels'):
                if not user:
                    conn.close()
                    return self._send_error('Authentication required', status=401)

                trip_id = int(path.split('/')[4])
                cur.execute("SELECT * FROM globetrotter_trip WHERE id = %s", (trip_id,))
                trip = cur.fetchone()
                if not trip or (trip['user_id'] != user['id'] and user.get('role') != 'admin'):
                    conn.close()
                    return self._send_error('Unauthorized', status=403)

                hotel_id = body.get('hotel_id')
                stop_id = body.get('stop_id')
                check_in = body.get('check_in')
                check_out = body.get('check_out')
                guests = int(body.get('number_of_guests') or 2)
                rooms = int(body.get('number_of_rooms') or 1)
                room_type = body.get('room_type_selected') or 'Standard Double Room'
                notes = body.get('notes', '')

                if not hotel_id or not check_in or not check_out:
                    conn.close()
                    return self._send_error('Hotel, check-in date, and check-out date are required.')

                cur.execute("SELECT * FROM globetrotter_hotel WHERE id = %s", (int(hotel_id),))
                hotel = cur.fetchone()
                if not hotel:
                    conn.close()
                    return self._send_error('Hotel not found', status=404)

                try:
                    d_in = datetime.strptime(check_in, '%Y-%m-%d').date()
                    d_out = datetime.strptime(check_out, '%Y-%m-%d').date()
                    if d_out <= d_in:
                        conn.close()
                        return self._send_error('Check-out date must be after check-in date.')
                    nights = (d_out - d_in).days
                except Exception as e:
                    conn.close()
                    return self._send_error('Invalid dates format (YYYY-MM-DD).')

                price_per_night = float(hotel['price_per_night'] or 0.0)
                total_cost = price_per_night * nights * rooms

                # Check if this stop already has a hotel booking; if so, replace previous linked expense
                if stop_id:
                    cur.execute("SELECT * FROM globetrotter_trip_hotel WHERE trip_id = %s AND stop_id = %s", (trip_id, stop_id))
                    prev_booking = cur.fetchone()
                    if prev_booking and prev_booking.get('expense_id'):
                        cur.execute("DELETE FROM globetrotter_expense WHERE id = %s", (prev_booking['expense_id'],))
                        cur.execute("DELETE FROM globetrotter_trip_hotel WHERE id = %s", (prev_booking['id'],))

                # Create linked accommodation expense
                exp_name = f"Accommodation: {hotel['name']} ({nights} nights)"
                cur.execute("""
                    INSERT INTO globetrotter_expense (trip_id, stop_id, category, name, amount, date, notes)
                    VALUES (%s, %s, 'accommodation', %s, %s, %s, %s)
                    RETURNING id;
                """, (trip_id, stop_id, exp_name, total_cost, check_in, f"Auto-generated for {hotel['name']}"))
                exp_row = cur.fetchone()
                exp_id = exp_row['id']

                # Create trip hotel booking
                cur.execute("""
                    INSERT INTO globetrotter_trip_hotel (
                        trip_id, hotel_id, stop_id, expense_id, check_in, check_out,
                        number_of_nights, number_of_guests, number_of_rooms,
                        price_per_night, total_cost, room_type_selected, notes, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'selected')
                    RETURNING id;
                """, (
                    trip_id, hotel_id, stop_id, exp_id, check_in, check_out,
                    nights, guests, rooms, price_per_night, total_cost, room_type, notes
                ))
                booking_id = cur.fetchone()['id']

                conn.close()
                return self._send_json({
                    'success': True,
                    'booking_id': booking_id,
                    'expense_id': exp_id,
                    'total_cost': total_cost,
                    'nights': nights,
                    'message': f"Hotel '{hotel['name']}' successfully added to your itinerary!"
                })

            # 9. Add Trip Expense
            elif path.startswith('/api/v1/trips/') and path.endswith('/expenses'):
                if not user:
                    conn.close()
                    return self._send_error('Authentication required', status=401)

                trip_id = int(path.split('/')[4])
                cur.execute("SELECT * FROM globetrotter_trip WHERE id = %s", (trip_id,))
                trip = cur.fetchone()
                if not trip or (trip['user_id'] != user['id'] and user.get('role') != 'admin'):
                    conn.close()
                    return self._send_error('Unauthorized', status=403)

                name = (body.get('name') or '').strip()
                amount = float(body.get('amount') or 0.0)
                category = body.get('category', 'accommodation')

                if not name:
                    conn.close()
                    return self._send_error('Expense name is required.')

                cur.execute("""
                    INSERT INTO globetrotter_expense (trip_id, stop_id, category, name, amount, date, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (trip_id, body.get('stop_id'), category, name, amount, body.get('date'), body.get('notes', '')))
                exp_row = cur.fetchone()
                conn.close()
                return self._send_json({'success': True, 'expense_id': exp_row['id'], 'message': 'Expense recorded!'})

            # 10. Generate / Toggle Share Token
            elif path.startswith('/api/v1/trips/') and path.endswith('/share'):
                if not user:
                    conn.close()
                    return self._send_error('Authentication required', status=401)

                trip_id = int(path.split('/')[4])
                cur.execute("SELECT * FROM globetrotter_trip WHERE id = %s", (trip_id,))
                trip = cur.fetchone()
                if not trip or (trip['user_id'] != user['id'] and user.get('role') != 'admin'):
                    conn.close()
                    return self._send_error('Unauthorized', status=403)

                token = trip['share_token']
                if not token:
                    token = secrets.token_urlsafe(16)

                is_public = body.get('is_public', True)
                share_budget = body.get('share_budget', True)

                cur.execute("""
                    UPDATE globetrotter_trip 
                    SET share_token = %s, is_public = %s, share_budget = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                """, (token, is_public, share_budget, trip_id))

                cur.execute("""
                    INSERT INTO globetrotter_shared_trip (trip_id, share_token, is_active, allow_budget_view)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (share_token) DO UPDATE SET
                        is_active = EXCLUDED.is_active,
                        allow_budget_view = EXCLUDED.allow_budget_view;
                """, (trip_id, token, is_public, share_budget))

                conn.close()
                return self._send_json({
                    'success': True,
                    'share_token': token,
                    'share_url': f"/shared/{token}",
                    'is_public': is_public,
                    'share_budget': share_budget,
                    'message': 'Share link generated!'
                })

            # Weather Adjustment Single Action
            elif path.startswith('/api/v1/trips/') and path.endswith('/weather-adjust'):
                if not user:
                    conn.close()
                    return self._send_error('Authentication required', status=401)

                trip_id = int(path.split('/')[4])
                activity_id = int(body.get('activity_id'))
                action_type = body.get('action_type')

                cur.execute("SELECT * FROM globetrotter_trip WHERE id = %s", (trip_id,))
                trip = cur.fetchone()
                if not trip or (trip['user_id'] != user['id'] and user.get('role') != 'admin'):
                    conn.close()
                    return self._send_error('Trip not found or unauthorized', status=403)

                if action_type == 'move_day':
                    target_day = int(body.get('target_day_number'))
                    cur.execute("""
                        UPDATE globetrotter_trip_activity 
                        SET day_number = %s 
                        WHERE id = %s AND trip_id = %s;
                    """, (target_day, activity_id, trip_id))
                    msg = f"Activity rescheduled to Day {target_day}."
                elif action_type == 'swap_indoor':
                    sub = body.get('substitute_activity') or {}
                    name = sub.get('name')
                    category = sub.get('category', 'culture')
                    cost = float(sub.get('estimated_cost') or 0.0)
                    duration = float(sub.get('duration_hours') or 2.0)
                    desc = sub.get('description', '')
                    image = sub.get('image', '')
                    cur.execute("""
                        UPDATE globetrotter_trip_activity
                        SET name = %s, category = %s, estimated_cost = %s, duration_hours = %s, notes = %s, image = %s
                        WHERE id = %s AND trip_id = %s;
                    """, (name, category, cost, duration, desc, image, activity_id, trip_id))
                    msg = f"Replaced with indoor activity '{name}'."
                else:
                    conn.close()
                    return self._send_error('Invalid action_type')

                conn.close()
                return self._send_json({'success': True, 'message': msg})

            # Weather Adjustment Batch Action (Apply All Suggestions)
            elif path.startswith('/api/v1/trips/') and path.endswith('/weather-adjust-all'):
                if not user:
                    conn.close()
                    return self._send_error('Authentication required', status=401)

                trip_id = int(path.split('/')[4])
                cur.execute("SELECT * FROM globetrotter_trip WHERE id = %s", (trip_id,))
                trip = cur.fetchone()
                if not trip or (trip['user_id'] != user['id'] and user.get('role') != 'admin'):
                    conn.close()
                    return self._send_error('Trip not found or unauthorized', status=403)

                t_dict = dict(trip)
                cur.execute("""
                    SELECT s.*, c.name as city_name, c.country as country_name, c.latitude, c.longitude
                    FROM globetrotter_trip_stop s
                    JOIN globetrotter_city c ON s.city_id = c.id
                    WHERE s.trip_id = %s
                    ORDER BY s.sequence ASC, s.arrival_date ASC;
                """, (trip_id,))
                stops = [dict(s) for s in cur.fetchall()]

                cur.execute("""
                    SELECT a.*, c.name as city_name, s.city_id
                    FROM globetrotter_trip_activity a
                    LEFT JOIN globetrotter_trip_stop s ON a.stop_id = s.id
                    LEFT JOIN globetrotter_city c ON s.city_id = c.id
                    WHERE a.trip_id = %s
                    ORDER BY a.day_number ASC, a.sequence ASC;
                """, (trip_id,))
                activities = [dict(a) for a in cur.fetchall()]

                city_ids = list(set([s['city_id'] for s in stops if s.get('city_id')]))
                catalog_by_city = {}
                if city_ids:
                    cur.execute("SELECT * FROM globetrotter_activity WHERE city_id = ANY(%s) ORDER BY popularity DESC", (city_ids,))
                    for ca in cur.fetchall():
                        catalog_by_city.setdefault(ca['city_id'], []).append(dict(ca))

                analysis = WeatherService.generate_trip_weather_intelligence(t_dict, stops, activities, catalog_by_city)
                
                adjusted_count = 0
                for act in analysis.get('evaluated_activities', []):
                    if act.get('risk_analysis', {}).get('risk_level') in ['high', 'moderate'] and act.get('suggestions'):
                        sug = act['suggestions'][0]
                        act_id = act['id']
                        if sug['type'] == 'move_day':
                            cur.execute("UPDATE globetrotter_trip_activity SET day_number = %s WHERE id = %s AND trip_id = %s",
                                        (sug['target_day_number'], act_id, trip_id))
                            adjusted_count += 1
                        elif sug['type'] == 'swap_indoor':
                            sub = sug.get('substitute_activity', {})
                            cur.execute("""
                                UPDATE globetrotter_trip_activity
                                SET name = %s, category = %s, estimated_cost = %s, duration_hours = %s, notes = %s, image = %s
                                WHERE id = %s AND trip_id = %s;
                            """, (sub.get('name'), sub.get('category', 'culture'), float(sub.get('estimated_cost') or 0),
                                  float(sub.get('duration_hours') or 2), sub.get('description', ''), sub.get('image', ''),
                                  act_id, trip_id))
                            adjusted_count += 1

                conn.close()
                return self._send_json({
                    'success': True, 
                    'adjusted_count': adjusted_count,
                    'message': f"Applied {adjusted_count} smart weather adjustments across your itinerary!"
                })

            # 11. Duplicate / Clone Trip
            elif path.startswith('/api/v1/trips/') and path.endswith('/duplicate'):
                if not user:
                    conn.close()
                    return self._send_error('Authentication required', status=401)

                src_trip_id = int(path.split('/')[4])
                cur.execute("SELECT * FROM globetrotter_trip WHERE id = %s", (src_trip_id,))
                src = cur.fetchone()
                if not src:
                    conn.close()
                    return self._send_error('Source trip not found', status=404)

                # Clone trip record
                clone_name = f"{src['name']} (Copy)" if src['user_id'] == user['id'] else f"{src['name']} (My Plan)"
                cur.execute("""
                    INSERT INTO globetrotter_trip (user_id, name, start_date, end_date, description, cover_image, currency, travelers_count, total_budget, travel_style, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    user['id'], clone_name, src['start_date'], src['end_date'], src['description'],
                    src['cover_image'], src['currency'], src['travelers_count'], src['total_budget'],
                    src['travel_style'], 'upcoming'
                ))
                new_trip_id = cur.fetchone()['id']

                # Map old stop IDs to new stop IDs
                stop_map = {}
                cur.execute("SELECT * FROM globetrotter_trip_stop WHERE trip_id = %s ORDER BY sequence ASC", (src_trip_id,))
                for s in cur.fetchall():
                    cur.execute("""
                        INSERT INTO globetrotter_trip_stop (trip_id, city_id, sequence, arrival_date, departure_date, duration_days, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id;
                    """, (new_trip_id, s['city_id'], s['sequence'], s['arrival_date'], s['departure_date'], s['duration_days'], s['notes']))
                    stop_map[s['id']] = cur.fetchone()['id']

                # Clone activities
                cur.execute("SELECT * FROM globetrotter_trip_activity WHERE trip_id = %s", (src_trip_id,))
                for a in cur.fetchall():
                    new_stop_id = stop_map.get(a['stop_id'])
                    cur.execute("""
                        INSERT INTO globetrotter_trip_activity (trip_id, stop_id, activity_id, name, category, day_number, scheduled_time, duration_hours, estimated_cost, sequence, notes, image)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (
                        new_trip_id, new_stop_id, a['activity_id'], a['name'], a['category'],
                        a['day_number'], a['scheduled_time'], a['duration_hours'], a['estimated_cost'],
                        a['sequence'], a['notes'], a['image']
                    ))

                # Clone expenses
                cur.execute("SELECT * FROM globetrotter_expense WHERE trip_id = %s", (src_trip_id,))
                for e in cur.fetchall():
                    new_stop_id = stop_map.get(e['stop_id'])
                    cur.execute("""
                        INSERT INTO globetrotter_expense (trip_id, stop_id, category, name, amount, date, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """, (new_trip_id, new_stop_id, e['category'], e['name'], e['amount'], e['date'], e['notes']))

                # Clone hotels
                cur.execute("SELECT * FROM globetrotter_trip_hotel WHERE trip_id = %s", (src_trip_id,))
                for h in cur.fetchall():
                    new_stop_id = stop_map.get(h['stop_id'])
                    cur.execute("""
                        INSERT INTO globetrotter_trip_hotel (
                            trip_id, hotel_id, stop_id, check_in, check_out,
                            number_of_nights, number_of_guests, number_of_rooms,
                            price_per_night, total_cost, room_type_selected, notes, status
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (
                        new_trip_id, h['hotel_id'], new_stop_id, h['check_in'], h['check_out'],
                        h['number_of_nights'], h['number_of_guests'], h['number_of_rooms'],
                        h['price_per_night'], h['total_cost'], h['room_type_selected'], h['notes'], h['status']
                    ))

                conn.close()
                return self._send_json({'success': True, 'trip_id': new_trip_id, 'message': 'Itinerary copied into your account!'})

            # 12. Copy Shared Trip (Public action to copy into caller account)
            elif path.startswith('/api/v1/shared/') and path.endswith('/copy'):
                if not user:
                    conn.close()
                    return self._send_error('Please log in to copy this itinerary to your account.', status=401)

                token = path.split('/')[4]
                cur.execute("SELECT * FROM globetrotter_trip WHERE share_token = %s AND is_public = TRUE", (token,))
                src = cur.fetchone()
                if not src:
                    conn.close()
                    return self._send_error('Shared itinerary not found or inactive.', status=404)

                src_trip_id = src['id']
                # Increment copy count
                cur.execute("UPDATE globetrotter_shared_trip SET copy_count = copy_count + 1 WHERE share_token = %s", (token,))

                # Create clone
                clone_name = f"{src['name']} (Shared Copy)"
                cur.execute("""
                    INSERT INTO globetrotter_trip (user_id, name, start_date, end_date, description, cover_image, currency, travelers_count, total_budget, travel_style, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    user['id'], clone_name, src['start_date'], src['end_date'], src['description'],
                    src['cover_image'], src['currency'], src['travelers_count'], src['total_budget'],
                    src['travel_style'], 'upcoming'
                ))
                new_trip_id = cur.fetchone()['id']

                stop_map = {}
                cur.execute("SELECT * FROM globetrotter_trip_stop WHERE trip_id = %s ORDER BY sequence ASC", (src_trip_id,))
                for s in cur.fetchall():
                    cur.execute("""
                        INSERT INTO globetrotter_trip_stop (trip_id, city_id, sequence, arrival_date, departure_date, duration_days, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id;
                    """, (new_trip_id, s['city_id'], s['sequence'], s['arrival_date'], s['departure_date'], s['duration_days'], s['notes']))
                    stop_map[s['id']] = cur.fetchone()['id']

                cur.execute("SELECT * FROM globetrotter_trip_activity WHERE trip_id = %s", (src_trip_id,))
                for a in cur.fetchall():
                    new_stop_id = stop_map.get(a['stop_id'])
                    cur.execute("""
                        INSERT INTO globetrotter_trip_activity (trip_id, stop_id, activity_id, name, category, day_number, scheduled_time, duration_hours, estimated_cost, sequence, notes, image)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (
                        new_trip_id, new_stop_id, a['activity_id'], a['name'], a['category'],
                        a['day_number'], a['scheduled_time'], a['duration_hours'], a['estimated_cost'],
                        a['sequence'], a['notes'], a['image']
                    ))

                # Clone expenses for shared copy
                cur.execute("SELECT * FROM globetrotter_expense WHERE trip_id = %s", (src_trip_id,))
                for e in cur.fetchall():
                    new_stop_id = stop_map.get(e['stop_id'])
                    cur.execute("""
                        INSERT INTO globetrotter_expense (trip_id, stop_id, category, name, amount, date, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """, (new_trip_id, new_stop_id, e['category'], e['name'], e['amount'], e['date'], e['notes']))

                # Clone hotels
                cur.execute("SELECT * FROM globetrotter_trip_hotel WHERE trip_id = %s", (src_trip_id,))
                for h in cur.fetchall():
                    new_stop_id = stop_map.get(h['stop_id'])
                    cur.execute("""
                        INSERT INTO globetrotter_trip_hotel (
                            trip_id, hotel_id, stop_id, check_in, check_out,
                            number_of_nights, number_of_guests, number_of_rooms,
                            price_per_night, total_cost, room_type_selected, notes, status
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (
                        new_trip_id, h['hotel_id'], new_stop_id, h['check_in'], h['check_out'],
                        h['number_of_nights'], h['number_of_guests'], h['number_of_rooms'],
                        h['price_per_night'], h['total_cost'], h['room_type_selected'], h['notes'], h['status']
                    ))

                conn.close()
                return self._send_json({'success': True, 'trip_id': new_trip_id, 'message': 'Trip successfully copied to My Trips!'})

            # 13. Bookmark Destination
            elif path == '/api/v1/saved-destinations':
                if not user:
                    conn.close()
                    return self._send_error('Authentication required', status=401)
                city_id = body.get('city_id')
                if not city_id:
                    conn.close()
                    return self._send_error('City ID required')
                cur.execute("""
                    INSERT INTO globetrotter_saved_destination (user_id, city_id)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id, city_id) DO NOTHING;
                """, (user['id'], city_id))
                conn.close()
                return self._send_json({'success': True, 'message': 'Destination saved!'})

        conn.close()
        return self._send_error('Endpoint not found', status=404)

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._read_json_body()

        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            user = self._get_current_user(cur)
            if not user:
                conn.close()
                return self._send_error('Authentication required', status=401)

            # 1. Update Profile
            if path == '/api/v1/auth/profile':
                name = body.get('name', user['name'])
                pref_curr = body.get('preferred_currency', user['preferred_currency'])
                pref_style = body.get('preferred_travel_style', user['preferred_travel_style'])
                bio = body.get('bio', user.get('bio', ''))
                avatar = body.get('avatar_url', user.get('avatar_url', ''))

                cur.execute("""
                    UPDATE res_users 
                    SET name = %s, preferred_currency = %s, preferred_travel_style = %s, bio = %s, avatar_url = %s
                    WHERE id = %s
                    RETURNING id, name, email, preferred_currency, preferred_travel_style, preferred_language, avatar_url, bio, role;
                """, (name, pref_curr, pref_style, bio, avatar, user['id']))
                updated_u = cur.fetchone()
                conn.close()
                return self._send_json({'success': True, 'user': dict(updated_u), 'message': 'Profile updated!'})

            # 2. Update Trip
            elif path.startswith('/api/v1/trips/') and len(path.split('/')) == 5:
                trip_id = int(path.split('/')[4])
                cur.execute("SELECT * FROM globetrotter_trip WHERE id = %s", (trip_id,))
                trip = cur.fetchone()
                if not trip or (trip['user_id'] != user['id'] and user.get('role') != 'admin'):
                    conn.close()
                    return self._send_error('Trip not found or unauthorized', status=403)

                name = body.get('name', trip['name'])
                start_date = body.get('start_date', trip['start_date'])
                end_date = body.get('end_date', trip['end_date'])
                budget = float(body.get('total_budget', trip['total_budget']))
                travelers = int(body.get('travelers_count', trip['travelers_count']))
                style = body.get('travel_style', trip['travel_style'])
                currency = body.get('currency', trip['currency'])
                desc = body.get('description', trip['description'])
                cover = body.get('cover_image', trip['cover_image'])

                cur.execute("""
                    UPDATE globetrotter_trip
                    SET name = %s, start_date = %s, end_date = %s, total_budget = %s, travelers_count = %s,
                        travel_style = %s, currency = %s, description = %s, cover_image = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                """, (name, start_date, end_date, budget, travelers, style, currency, desc, cover, trip_id))

                conn.close()
                return self._send_json({'success': True, 'message': 'Trip updated successfully!'})

            # 2b. Update Hotel Booking
            elif '/hotels/' in path:
                parts = path.split('/')
                booking_id = int(parts[-1])
                cur.execute("""
                    SELECT th.*, h.name as hotel_name, h.price_per_night as base_price, t.user_id 
                    FROM globetrotter_trip_hotel th 
                    JOIN globetrotter_trip t ON th.trip_id = t.id 
                    JOIN globetrotter_hotel h ON th.hotel_id = h.id 
                    WHERE th.id = %s;
                """, (booking_id,))
                booking = cur.fetchone()
                if not booking or (booking['user_id'] != user['id'] and user.get('role') != 'admin'):
                    conn.close()
                    return self._send_error('Unauthorized or booking not found', status=403)

                check_in = body.get('check_in', str(booking['check_in']))
                check_out = body.get('check_out', str(booking['check_out']))
                rooms = int(body.get('number_of_rooms') or booking['number_of_rooms'] or 1)
                guests = int(body.get('number_of_guests') or booking['number_of_guests'] or 2)
                room_type = body.get('room_type_selected', booking['room_type_selected'])
                notes = body.get('notes', booking['notes'])
                status = body.get('status', booking['status'])

                d_in = datetime.strptime(str(check_in), '%Y-%m-%d').date()
                d_out = datetime.strptime(str(check_out), '%Y-%m-%d').date()
                if d_out <= d_in:
                    conn.close()
                    return self._send_error('Check-out must be after check-in.')
                nights = (d_out - d_in).days

                price_per_night = float(booking['price_per_night'])
                total_cost = price_per_night * nights * rooms

                cur.execute("""
                    UPDATE globetrotter_trip_hotel
                    SET check_in = %s, check_out = %s, number_of_nights = %s,
                        number_of_rooms = %s, number_of_guests = %s,
                        room_type_selected = %s, notes = %s, status = %s,
                        total_cost = %s
                    WHERE id = %s;
                """, (check_in, check_out, nights, rooms, guests, room_type, notes, status, total_cost, booking_id))

                # Update linked expense
                if booking.get('expense_id'):
                    exp_name = f"Accommodation: {booking['hotel_name']} ({nights} nights)"
                    cur.execute("""
                        UPDATE globetrotter_expense 
                        SET amount = %s, date = %s, name = %s
                        WHERE id = %s;
                    """, (total_cost, check_in, exp_name, booking['expense_id']))

                conn.close()
                return self._send_json({'success': True, 'total_cost': total_cost, 'nights': nights, 'message': 'Hotel accommodation updated!'})

            # 3. Update Activity
            elif '/activities/' in path:
                parts = path.split('/')
                act_id = int(parts[-1])
                cur.execute("""
                    UPDATE globetrotter_trip_activity
                    SET name = COALESCE(%s, name),
                        day_number = COALESCE(%s, day_number),
                        scheduled_time = COALESCE(%s, scheduled_time),
                        duration_hours = COALESCE(%s, duration_hours),
                        estimated_cost = COALESCE(%s, estimated_cost),
                        notes = COALESCE(%s, notes),
                        category = COALESCE(%s, category)
                    WHERE id = %s;
                """, (
                    body.get('name'), body.get('day_number'), body.get('scheduled_time'),
                    body.get('duration_hours'), body.get('estimated_cost'), body.get('notes'),
                    body.get('category'), act_id
                ))
                conn.close()
                return self._send_json({'success': True, 'message': 'Activity updated!'})

        conn.close()
        return self._send_error('Endpoint not found', status=404)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            user = self._get_current_user(cur)
            if not user:
                conn.close()
                return self._send_error('Authentication required', status=401)

            # 1. Delete Trip
            if path.startswith('/api/v1/trips/') and len(path.split('/')) == 5:
                trip_id = int(path.split('/')[4])
                cur.execute("SELECT * FROM globetrotter_trip WHERE id = %s", (trip_id,))
                trip = cur.fetchone()
                if not trip or (trip['user_id'] != user['id'] and user.get('role') != 'admin'):
                    conn.close()
                    return self._send_error('Unauthorized or trip not found', status=403)

                cur.execute("DELETE FROM globetrotter_trip WHERE id = %s", (trip_id,))
                conn.close()
                return self._send_json({'success': True, 'message': 'Trip deleted.'})

            # 2. Delete Stop
            elif '/stops/' in path:
                parts = path.split('/')
                stop_id = int(parts[-1])
                cur.execute("DELETE FROM globetrotter_trip_stop WHERE id = %s", (stop_id,))
                conn.close()
                return self._send_json({'success': True, 'message': 'Stop deleted.'})

            # 2b. Delete Hotel Booking
            elif '/hotels/' in path:
                parts = path.split('/')
                booking_id = int(parts[-1])
                cur.execute("""
                    SELECT th.*, t.user_id 
                    FROM globetrotter_trip_hotel th 
                    JOIN globetrotter_trip t ON th.trip_id = t.id 
                    WHERE th.id = %s;
                """, (booking_id,))
                booking = cur.fetchone()
                if not booking or (booking['user_id'] != user['id'] and user.get('role') != 'admin'):
                    conn.close()
                    return self._send_error('Unauthorized or booking not found', status=403)

                if booking.get('expense_id'):
                    cur.execute("DELETE FROM globetrotter_expense WHERE id = %s", (booking['expense_id'],))
                cur.execute("DELETE FROM globetrotter_trip_hotel WHERE id = %s", (booking_id,))
                conn.close()
                return self._send_json({'success': True, 'message': 'Hotel accommodation removed.'})

            # 3. Delete Activity
            elif '/activities/' in path:
                parts = path.split('/')
                act_id = int(parts[-1])
                cur.execute("DELETE FROM globetrotter_trip_activity WHERE id = %s", (act_id,))
                conn.close()
                return self._send_json({'success': True, 'message': 'Activity deleted.'})

            # 4. Delete Expense
            elif '/expenses/' in path:
                parts = path.split('/')
                exp_id = int(parts[-1])
                cur.execute("DELETE FROM globetrotter_expense WHERE id = %s", (exp_id,))
                conn.close()
                return self._send_json({'success': True, 'message': 'Expense deleted.'})

            # 5. Remove Bookmark
            elif path.startswith('/api/v1/saved-destinations/'):
                city_id = int(path.split('/')[-1])
                cur.execute("DELETE FROM globetrotter_saved_destination WHERE user_id = %s AND city_id = %s", (user['id'], city_id))
                conn.close()
                return self._send_json({'success': True, 'message': 'Bookmark removed.'})

        conn.close()
        return self._send_error('Endpoint not found', status=404)

def run_server(port=8069):
    init_db()
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, GlobeTrotterRequestHandler)
    _logger.info(f"GlobeTrotter Server running at http://127.0.0.1:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        _logger.info("Server shutting down.")
        httpd.server_close()

if __name__ == '__main__':
    run_server(8069)
