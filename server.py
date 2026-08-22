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

                computed = compute_trip_business_logic(t_dict, stops, activities, expenses)
                t_dict.update(computed)
                t_dict['stops'] = stops
                t_dict['activities'] = activities
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

                t_dict['stops'] = stops
                t_dict['activities'] = activities
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
