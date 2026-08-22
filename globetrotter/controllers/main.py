# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request, Response
import json
import logging

_logger = logging.getLogger(__name__)

def json_response(data, status=200):
    return Response(
        json.dumps(data, default=str),
        status=status,
        mimetype='application/json'
    )

class GlobetrotterAPI(http.Controller):

    # ================= AUTHENTICATION =================
    @http.route('/api/v1/auth/signup', type='json', auth='public', methods=['POST'], csrf=False)
    def signup(self, **kw):
        data = request.jsonrequest or {}
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''
        name = (data.get('name') or '').strip()

        if not email or not password or not name:
            return {'error': 'Name, email, and password are required.'}

        existing = request.env['res.users'].sudo().search([('login', '=', email)], limit=1)
        if existing:
            return {'error': 'An account with this email already exists.'}

        try:
            user = request.env['res.users'].sudo().create({
                'name': name,
                'login': email,
                'email': email,
                'password': password,
                'groups_id': [(4, request.env.ref('globetrotter.group_globetrotter_user').id)]
            })
            return {
                'success': True,
                'user': {
                    'id': user.id,
                    'name': user.name,
                    'email': user.login,
                }
            }
        except Exception as e:
            _logger.exception("Signup error: %s", e)
            return {'error': str(e)}

    @http.route('/api/v1/auth/login', type='json', auth='public', methods=['POST'], csrf=False)
    def login(self, **kw):
        data = request.jsonrequest or {}
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''

        if not email or not password:
            return {'error': 'Email and password are required.'}

        try:
            uid = request.session.authenticate(request.db, email, password)
            if uid:
                user = request.env['res.users'].sudo().browse(uid)
                return {
                    'success': True,
                    'user': {
                        'id': user.id,
                        'name': user.name,
                        'email': user.login,
                        'preferred_currency': user.preferred_currency or 'INR',
                        'preferred_travel_style': user.preferred_travel_style or 'balanced',
                    }
                }
            return {'error': 'Invalid email or password.'}
        except Exception as e:
            return {'error': 'Invalid credentials or login failed.'}

    # ================= TRIPS CRUD =================
    @http.route('/api/v1/trips', type='json', auth='user', methods=['GET', 'POST'], csrf=False)
    def handle_trips(self, **kw):
        user = request.env.user
        if request.httprequest.method == 'GET':
            trips = request.env['globetrotter.trip'].search([('user_id', '=', user.id)])
            results = []
            for t in trips:
                results.append({
                    'id': t.id,
                    'name': t.name,
                    'start_date': str(t.start_date),
                    'end_date': str(t.end_date),
                    'duration_days': t.duration_days,
                    'cover_image': t.cover_image,
                    'currency': t.currency,
                    'travelers_count': t.travelers_count,
                    'total_budget': t.total_budget,
                    'travel_style': t.travel_style,
                    'status': t.status,
                    'stops_count': t.stops_count,
                    'activities_count': t.activities_count,
                    'total_estimated_cost': t.total_estimated_cost,
                    'remaining_budget': t.remaining_budget,
                    'budget_utilization': t.budget_utilization,
                    'trip_balance_score': t.trip_balance_score,
                })
            return {'success': True, 'trips': results}

        elif request.httprequest.method == 'POST':
            data = request.jsonrequest or {}
            try:
                trip = request.env['globetrotter.trip'].create({
                    'name': data.get('name'),
                    'start_date': data.get('start_date'),
                    'end_date': data.get('end_date'),
                    'description': data.get('description'),
                    'cover_image': data.get('cover_image'),
                    'currency': data.get('currency', 'INR'),
                    'travelers_count': int(data.get('travelers_count', 1)),
                    'total_budget': float(data.get('total_budget', 0.0)),
                    'travel_style': data.get('travel_style', 'balanced'),
                    'user_id': user.id,
                })
                return {'success': True, 'trip_id': trip.id}
            except Exception as e:
                return {'error': str(e)}

    # ================= DESTINATIONS =================
    @http.route('/api/v1/destinations', type='json', auth='public', methods=['GET'], csrf=False)
    def get_destinations(self, **kw):
        cities = request.env['globetrotter.city'].sudo().search([])
        res = []
        for c in cities:
            res.append({
                'id': c.id,
                'name': c.name,
                'country': c.country,
                'region': c.region,
                'description': c.description,
                'cost_index': c.cost_index,
                'popularity': c.popularity,
                'recommended_duration_days': c.recommended_duration_days,
                'cover_image': c.cover_image,
                'travel_styles': c.travel_styles.split(',') if c.travel_styles else [],
                'activity_count': c.activity_count,
            })
        return {'success': True, 'destinations': res}
