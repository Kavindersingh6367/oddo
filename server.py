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


def calculate_user_travel_dna(cur, user_id):
    """
    Computes a transparent, data-driven Travel DNA profile for a user based on:
    - Activity categories across all trips
    - Travel styles & trip durations
    - Hotel category preferences
    - Saved bookmarks
    """
    # 1. Activity Category Counts
    cur.execute("""
        SELECT a.category, COUNT(*) as count 
        FROM globetrotter_trip_activity a
        JOIN globetrotter_trip t ON a.trip_id = t.id
        WHERE t.user_id = %s
        GROUP BY a.category
    """, (user_id,))
    act_counts = {row['category']: int(row['count']) for row in cur.fetchall()}
    total_acts = sum(act_counts.values())

    # 2. Trip Styles & Durations
    cur.execute("""
        SELECT travel_style, total_budget, start_date, end_date 
        FROM globetrotter_trip 
        WHERE user_id = %s
    """, (user_id,))
    trips = cur.fetchall()
    total_trips = len(trips)

    # 3. Hotel Selections
    cur.execute("""
        SELECT h.hotel_category, COUNT(*) as count
        FROM globetrotter_trip_hotel th
        JOIN globetrotter_trip t ON th.trip_id = t.id
        JOIN globetrotter_hotel h ON th.hotel_id = h.id
        WHERE t.user_id = %s
        GROUP BY h.hotel_category
    """, (user_id,))
    hotel_counts = {row['hotel_category']: int(row['count']) for row in cur.fetchall()}

    adv_count = act_counts.get('adventure', 0) * 1.0 + act_counts.get('nature', 0) * 0.4
    cult_count = act_counts.get('culture', 0) * 1.0 + act_counts.get('sightseeing', 0) * 0.6
    food_count = act_counts.get('food', 0) * 1.0 + act_counts.get('entertainment', 0) * 0.3
    relax_count = act_counts.get('relaxation', 0) * 1.0 + act_counts.get('nature', 0) * 0.4
    sight_count = act_counts.get('sightseeing', 0) * 1.0 + act_counts.get('culture', 0) * 0.4

    # Baseline seed points for new/demo users so the radar is always meaningful
    adv_base, cult_base, food_base, relax_base, sight_base = 65, 82, 74, 55, 80

    if total_acts > 0:
        max_c = max(1.0, float(max(adv_count, cult_count, food_count, relax_count, sight_count, 1)))
        adv_score = min(98, max(25, int(round((adv_count / max_c) * 45 + 45))))
        cult_score = min(98, max(25, int(round((cult_count / max_c) * 45 + 45))))
        food_score = min(98, max(25, int(round((food_count / max_c) * 45 + 45))))
        relax_score = min(98, max(25, int(round((relax_count / max_c) * 45 + 45))))
        sight_score = min(98, max(25, int(round((sight_count / max_c) * 45 + 45))))
    else:
        cur.execute("SELECT preferred_travel_style FROM res_users WHERE id = %s", (user_id,))
        u_row = cur.fetchone()
        u_style = (u_row.get('preferred_travel_style') if u_row else 'balanced') or 'balanced'
        if u_style == 'adventure':
            adv_score, cult_score, food_score, relax_score, sight_score = 88, 65, 60, 40, 75
        elif u_style == 'luxury':
            adv_score, cult_score, food_score, relax_score, sight_score = 50, 80, 85, 90, 85
        elif u_style == 'relaxed':
            adv_score, cult_score, food_score, relax_score, sight_score = 45, 60, 75, 92, 70
        else:
            adv_score, cult_score, food_score, relax_score, sight_score = adv_base, cult_base, food_base, relax_base, sight_base

    # Compute Typical Duration
    avg_duration = 5
    durations = []
    for t in trips:
        if t.get('start_date') and t.get('end_date'):
            s = t['start_date']
            e = t['end_date']
            if isinstance(s, str): s = datetime.strptime(s, '%Y-%m-%d').date()
            if isinstance(e, str): e = datetime.strptime(e, '%Y-%m-%d').date()
            durations.append((e - s).days + 1)
    if durations:
        avg_duration = int(round(sum(durations) / len(durations)))
        if avg_duration <= 3:
            typical_duration_text = "Weekend Getaways (2–4 Days)"
        elif avg_duration <= 7:
            typical_duration_text = "Standard Journeys (5–7 Days)"
        elif avg_duration <= 14:
            typical_duration_text = "Extended Expeditions (8–14 Days)"
        else:
            typical_duration_text = "Grand Grand Tours (15+ Days)"
    else:
        typical_duration_text = "Standard Journeys (5–7 Days)"

    # Compute Budget & Stay Style
    lux_stays = hotel_counts.get('luxury', 0) + hotel_counts.get('premium', 0)
    bud_stays = hotel_counts.get('budget', 0) + hotel_counts.get('economy', 0)
    mid_stays = hotel_counts.get('mid_range', 0)

    if lux_stays > mid_stays and lux_stays > bud_stays:
        preferred_stay = "Luxury & Boutique Palaces"
        budget_pref = "Luxury"
    elif bud_stays > mid_stays and bud_stays > lux_stays:
        preferred_stay = "Hostels & Economy Stays"
        budget_pref = "Budget"
    else:
        preferred_stay = "Mid-Range Heritage Stays"
        budget_pref = "Balanced"

    top_scores = sorted([
        ('Culture', cult_score),
        ('Adventure', adv_score),
        ('Food & Dining', food_score),
        ('Relaxation', relax_score),
        ('Sightseeing', sight_score)
    ], key=lambda x: x[1], reverse=True)

    primary = top_scores[0][0]
    secondary = top_scores[1][0]
    persona_title = f"{primary} & {secondary} Explorer"

    return {
        'adventure': adv_score,
        'culture': cult_score,
        'food': food_score,
        'relaxation': relax_score,
        'sightseeing': sight_score,
        'nature': int((adv_score + relax_score) / 2),
        'shopping': int((cult_score + food_score) / 2),
        'budget_preference': budget_pref,
        'typical_trip_duration': typical_duration_text,
        'preferred_stay': preferred_stay,
        'persona_title': persona_title,
        'total_trips_analyzed': total_trips,
        'total_activities_logged': total_acts,
        'insights': [
            f"Strongest affinity for {primary} ({top_scores[0][1]}%) and {secondary} ({top_scores[1][1]}%).",
            f"Prefers {budget_pref.lower()} accommodations with a typical cadence of {typical_duration_text.lower()}.",
            f"Recommendation engine automatically prioritizes {primary.lower()}-aligned destinations and experiences."
        ]
    }


def calculate_trip_health(trip_dict, stops, activities, expenses, hotels):
    """
    Computes a comprehensive 0-100 Trip Health & Diagnostics score,
    detecting budget pressure, activity overload, schedule congestion,
    rushed city pacing, and empty days with actionable suggestions.
    """
    duration_days = max(1, trip_dict.get('duration_days') or 1)
    total_cost = float(trip_dict.get('total_estimated_cost') or 0.0)
    budget = float(trip_dict.get('total_budget') or 0.0)
    utilization = float(trip_dict.get('budget_utilization') or 0.0)
    curr = trip_dict.get('currency', 'INR')

    # 1. Budget Health (0-30)
    score_budget = 30
    budget_diagnostics = []
    if budget > 0:
        if total_cost > budget:
            diff = total_cost - budget
            score_budget = max(5, 30 - int((diff / budget) * 35))
            budget_diagnostics.append(f"Over budget by {format_currency_text(diff, curr)}.")
        elif utilization >= 90:
            score_budget = 25
            budget_diagnostics.append("Near full budget utilization (90%+).")
        elif utilization >= 60:
            score_budget = 30
            budget_diagnostics.append("Budget healthy and well-allocated (60–90%).")
        else:
            score_budget = 24
            budget_diagnostics.append("Low budget utilization (under 60%).")
    else:
        score_budget = 20
        budget_diagnostics.append("No target budget set.")

    # 2. Activity Load & Density (0-25)
    score_load = 25
    load_diagnostics = []
    day_act_counts = {}
    day_act_hours = {}
    for a in activities:
        d = int(a.get('day_number') or 1)
        day_act_counts[d] = day_act_counts.get(d, 0) + 1
        day_act_hours[d] = day_act_hours.get(d, 0.0) + float(a.get('duration_hours') or 2.0)

    overloaded_days = [d for d, cnt in day_act_counts.items() if cnt >= 4 or day_act_hours.get(d, 0) >= 8.0]
    empty_days = [d for d in range(1, duration_days + 1) if d not in day_act_counts]

    if overloaded_days:
        score_load -= min(15, len(overloaded_days) * 7)
        load_diagnostics.append(f"Day(s) {', '.join(map(str, overloaded_days))} are heavily packed (4+ activities / 8+ hours). Schedule fatigue risk.")
    if empty_days:
        score_load -= min(8, len(empty_days) * 3)
        load_diagnostics.append(f"Day(s) {', '.join(map(str, empty_days))} have no planned activities.")
    if not overloaded_days and not empty_days and activities:
        load_diagnostics.append("Balanced daily activity distribution (2–3 activities per day).")
    elif not activities:
        score_load = 10
        load_diagnostics.append("No activities scheduled yet.")

    score_load = max(5, score_load)

    # 3. City Dwell Time & Transit Pacing (0-20)
    score_dwell = 20
    dwell_diagnostics = []
    stops_count = len(stops)
    if stops_count > 0:
        days_per_city = duration_days / stops_count
        if days_per_city < 1.5:
            score_dwell = 10
            dwell_diagnostics.append(f"Rushed city hopping ({days_per_city:.1f} days/city). High transit overhead.")
        elif 1.5 <= days_per_city <= 4.0:
            score_dwell = 20
            dwell_diagnostics.append(f"Ideal dwell time ({days_per_city:.1f} days per city stop).")
        else:
            score_dwell = 18
            dwell_diagnostics.append(f"Immersive slow-travel pacing ({days_per_city:.1f} days per city).")
    else:
        score_dwell = 5
        dwell_diagnostics.append("No city stops added.")

    # 4. Accommodation Coverage (0-15)
    score_hotel = 15
    hotel_diagnostics = []
    stop_ids_with_hotel = set(h.get('stop_id') for h in hotels if h.get('stop_id'))
    missing_hotel_stops = [s.get('city_name', f"Stop {s['id']}") for s in stops if s['id'] not in stop_ids_with_hotel]
    
    if missing_hotel_stops:
        score_hotel -= min(10, len(missing_hotel_stops) * 4)
        hotel_diagnostics.append(f"Missing hotel reservation for stop(s): {', '.join(missing_hotel_stops)}.")
    else:
        hotel_diagnostics.append("All destination stops have booked accommodations.")

    stay_cost = float(trip_dict.get('cost_accommodation') or 0.0)
    if total_cost > 0 and (stay_cost / total_cost) >= 0.55:
        score_hotel -= 3
        hotel_diagnostics.append(f"Accommodation represents {int(stay_cost/total_cost*100)}% of total spend.")

    score_hotel = max(4, score_hotel)

    # 5. Itinerary Completeness (0-10)
    score_comp = 10
    comp_diagnostics = []
    if not stops: score_comp -= 4
    if len(activities) < 3: score_comp -= 3
    if not expenses and not hotels: score_comp -= 3
    score_comp = max(2, score_comp)
    if score_comp >= 8:
        comp_diagnostics.append("Comprehensive itinerary with stops, stays, and activities.")
    else:
        comp_diagnostics.append("Itinerary is in draft state; add activities and stays.")

    total_health = min(100, max(10, score_budget + score_load + score_dwell + score_hotel + score_comp))

    if total_health >= 85:
        health_status = "Healthy"
        health_color = "emerald"
    elif total_health >= 70:
        health_status = "Good / Minor Attention"
        health_color = "amber"
    else:
        health_status = "Needs Optimization"
        health_color = "rose"

    actionable_recommendations = []
    if overloaded_days:
        for od in overloaded_days:
            light_day = next((d for d in range(1, duration_days + 1) if day_act_counts.get(d, 0) <= 2 and d != od), None)
            if light_day:
                actionable_recommendations.append({
                    'type': 'balance',
                    'title': f'Balance Day {od} Schedule',
                    'message': f"Day {od} has {day_act_counts.get(od)} activities. Move 1-2 activities to Day {light_day} for a more relaxing pace.",
                    'action_label': f"Move to Day {light_day}",
                    'from_day': od,
                    'to_day': light_day
                })
    if missing_hotel_stops:
        actionable_recommendations.append({
            'type': 'hotel',
            'title': 'Add Accommodation',
            'message': f"Select recommended hotels for {', '.join(missing_hotel_stops)} to complete your stay plan.",
            'action_label': 'Find Hotels'
        })
    if budget > 0 and total_cost > budget:
        actionable_recommendations.append({
            'type': 'budget',
            'title': 'Trim Budget Overrun',
            'message': f"Trip is {format_currency_text(total_cost - budget, curr)} over budget. Consider switching to budget or mid-range hotel alternatives.",
            'action_label': 'Review Budget'
        })

    return {
        'health_score': total_health,
        'health_status': health_status,
        'health_color': health_color,
        'breakdown': {
            'budget_health': {'score': score_budget, 'max': 30, 'diagnostics': budget_diagnostics},
            'activity_load': {'score': score_load, 'max': 25, 'diagnostics': load_diagnostics},
            'dwell_pacing': {'score': score_dwell, 'max': 20, 'diagnostics': dwell_diagnostics},
            'accommodation_coverage': {'score': score_hotel, 'max': 15, 'diagnostics': hotel_diagnostics},
            'completeness': {'score': score_comp, 'max': 10, 'diagnostics': comp_diagnostics}
        },
        'actionable_recommendations': actionable_recommendations
    }


def get_balancing_suggestions(trip_dict, stops, activities):
    """
    Finds concrete activity moves from overloaded days to lighter days.
    """
    duration_days = max(1, trip_dict.get('duration_days') or 1)
    day_activities = {}
    for a in activities:
        d = int(a.get('day_number') or 1)
        day_activities.setdefault(d, []).append(a)

    suggestions = []
    sug_id = 1
    for d, acts in day_activities.items():
        if len(acts) >= 4:
            for target_d in range(1, duration_days + 1):
                target_acts = day_activities.get(target_d, [])
                if len(target_acts) <= 2 and target_d != d:
                    movable_act = acts[-1]
                    suggestions.append({
                        'id': sug_id,
                        'activity_id': movable_act['id'],
                        'activity_name': movable_act['name'],
                        'from_day': d,
                        'to_day': target_d,
                        'reason': f"Day {d} has {len(acts)} activities ({sum(float(x.get('duration_hours') or 2) for x in acts):.1f}h scheduled). Moving '{movable_act['name']}' to Day {target_d} balances your daily schedule.",
                        'impact': "Improves Trip Health score by +8 pts and avoids afternoon exhaustion."
                    })
                    sug_id += 1
                    break
    return suggestions




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
        cur.execute("""
            SELECT id, name, email, first_name, last_name, phone, city, country,
                   preferred_currency, preferred_travel_style, preferred_language,
                   avatar_url, bio, additional_info, role, created_at
            FROM res_users WHERE id = %s
        """, (user_id,))
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

            # 1. Auth Me & Travel DNA
            if path == '/api/v1/auth/me':
                if not user:
                    conn.close()
                    return self._send_error('Not authenticated', status=401)
                u_dict = dict(user)
                u_dict['travel_dna'] = calculate_user_travel_dna(cur, user['id'])
                conn.close()
                return self._send_json({'success': True, 'user': u_dict})

            # 1b. Direct Travel DNA profile
            elif path == '/api/v1/user/travel-dna':
                if not user:
                    conn.close()
                    return self._send_error('Not authenticated', status=401)
                dna = calculate_user_travel_dna(cur, user['id'])
                conn.close()
                return self._send_json({'success': True, 'travel_dna': dna})

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

            # 6. Single Trip Details (with Health & Smart Balancing)
            elif path.startswith('/api/v1/trips/') and not any(sub in path for sub in ['/duplicate', '/share', '/stops', '/activities', '/expenses', '/balance']):
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

                if trip['user_id'] != user['id'] and user.get('role') != 'admin' and not trip['is_public']:
                    conn.close()
                    return self._send_error('Access Denied: You do not have permission to view this trip', status=403)

                t_dict = dict(trip)
                cur.execute("""
                    SELECT s.*, c.name as city_name, c.country as country_name, c.cover_image as city_image, c.region as city_region
                    FROM globetrotter_trip_stop s
                    JOIN globetrotter_city c ON s.city_id = c.id
                    WHERE s.trip_id = %s
                    ORDER BY s.sequence ASC, s.arrival_date ASC;
                """, (trip_id,))
                stops = [dict(s) for s in cur.fetchall()]

                cur.execute("""
                    SELECT a.*, c.name as city_name
                    FROM globetrotter_trip_activity a
                    LEFT JOIN globetrotter_trip_stop s ON a.stop_id = s.id
                    LEFT JOIN globetrotter_city c ON s.city_id = c.id
                    WHERE a.trip_id = %s
                    ORDER BY a.day_number ASC, a.sequence ASC, a.scheduled_time ASC;
                """, (trip_id,))
                activities = [dict(a) for a in cur.fetchall()]

                cur.execute("""
                    SELECT e.*, c.name as city_name
                    FROM globetrotter_expense e
                    LEFT JOIN globetrotter_trip_stop s ON e.stop_id = s.id
                    LEFT JOIN globetrotter_city c ON s.city_id = c.id
                    WHERE e.trip_id = %s
                    ORDER BY e.date ASC, e.id ASC;
                """, (trip_id,))
                expenses = [dict(e) for e in cur.fetchall()]

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

                # Add Trip Health and Smart Balancing
                t_dict['trip_health'] = calculate_trip_health(t_dict, stops, activities, expenses, hotels)
                t_dict['balancing_suggestions'] = get_balancing_suggestions(t_dict, stops, activities)

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

                cur.execute("UPDATE globetrotter_shared_trip SET view_count = view_count + 1 WHERE share_token = %s", (token,))

                cur.execute("""
                    SELECT s.*, c.name as city_name, c.country as country_name, c.cover_image as city_image, c.region as city_region
                    FROM globetrotter_trip_stop s
                    JOIN globetrotter_city c ON s.city_id = c.id
                    WHERE s.trip_id = %s
                    ORDER BY s.sequence ASC, s.arrival_date ASC;
                """, (trip_id,))
                stops = [dict(s) for s in cur.fetchall()]

                cur.execute("""
                    SELECT a.*, c.name as city_name
                    FROM globetrotter_trip_activity a
                    LEFT JOIN globetrotter_trip_stop s ON a.stop_id = s.id
                    LEFT JOIN globetrotter_city c ON s.city_id = c.id
                    WHERE a.trip_id = %s
                    ORDER BY a.day_number ASC, a.sequence ASC;
                """, (trip_id,))
                activities = [dict(a) for a in cur.fetchall()]

                cur.execute("SELECT * FROM globetrotter_expense WHERE trip_id = %s ORDER BY date ASC", (trip_id,))
                expenses = [dict(e) for e in cur.fetchall()]

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

            # 9. Community Posts Discovery
            elif path == '/api/v1/community/posts':
                search_q = query.get('q', [''])[0].strip()
                city_id = query.get('city_id', [''])[0]
                travel_style = query.get('travel_style', [''])[0]
                sort_by = query.get('sort_by', ['popular'])[0]

                sql = """
                    SELECT p.*, u.name as author_name, u.avatar_url as author_avatar,
                           c.name as city_name, c.country as country_name
                    FROM globetrotter_community_post p
                    JOIN res_users u ON p.user_id = u.id
                    LEFT JOIN globetrotter_city c ON p.city_id = c.id
                    WHERE p.active = TRUE
                """
                params = []

                if search_q:
                    sql += " AND (p.title ILIKE %s OR p.experience_text ILIKE %s OR p.tags ILIKE %s OR c.name ILIKE %s)"
                    params.extend([f"%{search_q}%", f"%{search_q}%", f"%{search_q}%", f"%{search_q}%"])
                if city_id:
                    sql += " AND p.city_id = %s"
                    params.append(int(city_id))
                if travel_style and travel_style != 'all':
                    sql += " AND p.travel_style = %s"
                    params.append(travel_style)

                if sort_by == 'newest':
                    sql += " ORDER BY p.created_at DESC"
                elif sort_by == 'rating':
                    sql += " ORDER BY p.rating DESC, p.likes_count DESC"
                elif sort_by == 'imports':
                    sql += " ORDER BY p.imports_count DESC, p.likes_count DESC"
                else: # 'popular'
                    sql += " ORDER BY p.likes_count DESC, p.saves_count DESC"

                cur.execute(sql, params)
                posts = [dict(p) for p in cur.fetchall()]

                # Parse JSON highlights
                for p in posts:
                    if isinstance(p.get('activity_highlights'), str):
                        try:
                            p['activity_highlights'] = json.loads(p['activity_highlights'])
                        except Exception:
                            p['activity_highlights'] = []
                    elif not p.get('activity_highlights'):
                        p['activity_highlights'] = []

                    # If user is logged in, attach interaction state
                    if user:
                        cur.execute("SELECT interaction_type FROM globetrotter_community_interaction WHERE user_id = %s AND post_id = %s", (user['id'], p['id']))
                        interactions = set(r['interaction_type'] for r in cur.fetchall())
                        p['liked_by_me'] = 'like' in interactions
                        p['saved_by_me'] = 'save' in interactions
                    else:
                        p['liked_by_me'] = False
                        p['saved_by_me'] = False

                conn.close()
                return self._send_json({'success': True, 'posts': posts})

            # 9b. Single Community Post Detail
            elif path.startswith('/api/v1/community/posts/'):
                try:
                    post_id = int(path.split('/')[-1])
                except ValueError:
                    conn.close()
                    return self._send_error('Invalid post ID')

                cur.execute("""
                    SELECT p.*, u.name as author_name, u.avatar_url as author_avatar, u.bio as author_bio,
                           c.name as city_name, c.country as country_name
                    FROM globetrotter_community_post p
                    JOIN res_users u ON p.user_id = u.id
                    LEFT JOIN globetrotter_city c ON p.city_id = c.id
                    WHERE p.id = %s AND p.active = TRUE;
                """, (post_id,))
                post = cur.fetchone()
                if not post:
                    conn.close()
                    return self._send_error('Community post not found', status=404)

                p_dict = dict(post)
                if isinstance(p_dict.get('activity_highlights'), str):
                    try:
                        p_dict['activity_highlights'] = json.loads(p_dict['activity_highlights'])
                    except Exception:
                        p_dict['activity_highlights'] = []
                elif not p_dict.get('activity_highlights'):
                    p_dict['activity_highlights'] = []

                if user:
                    cur.execute("SELECT interaction_type FROM globetrotter_community_interaction WHERE user_id = %s AND post_id = %s", (user['id'], post_id))
                    interactions = set(r['interaction_type'] for r in cur.fetchall())
                    p_dict['liked_by_me'] = 'like' in interactions
                    p_dict['saved_by_me'] = 'save' in interactions
                else:
                    p_dict['liked_by_me'] = False
                    p_dict['saved_by_me'] = False

                conn.close()
                return self._send_json({'success': True, 'post': p_dict})

            # 10. Universal Global Search (Ctrl+K)
            elif path == '/api/v1/search':
                q = query.get('q', [''])[0].strip()
                if not q:
                    conn.close()
                    return self._send_json({
                        'success': True,
                        'results': {'destinations': [], 'activities': [], 'hotels': [], 'trips': [], 'community': []}
                    })

                like_term = f"%{q}%"

                # Destinations
                cur.execute("""
                    SELECT id, name, country, region, cover_image, cost_index, popularity 
                    FROM globetrotter_city 
                    WHERE name ILIKE %s OR country ILIKE %s OR region ILIKE %s 
                    ORDER BY popularity DESC LIMIT 5;
                """, (like_term, like_term, like_term))
                dests = [dict(r) for r in cur.fetchall()]

                # Activities
                cur.execute("""
                    SELECT a.id, a.name, a.category, a.duration_hours, a.estimated_cost, a.image, c.name as city_name 
                    FROM globetrotter_activity a 
                    JOIN globetrotter_city c ON a.city_id = c.id 
                    WHERE a.name ILIKE %s OR a.description ILIKE %s OR a.category ILIKE %s
                    ORDER BY a.popularity DESC LIMIT 5;
                """, (like_term, like_term, like_term))
                acts = [dict(r) for r in cur.fetchall()]

                # Hotels
                cur.execute("""
                    SELECT h.id, h.name, h.hotel_category, h.rating, h.price_per_night, h.image, c.name as city_name 
                    FROM globetrotter_hotel h 
                    JOIN globetrotter_city c ON h.city_id = c.id 
                    WHERE h.active = TRUE AND (h.name ILIKE %s OR h.address ILIKE %s OR h.hotel_category ILIKE %s)
                    ORDER BY h.rating DESC LIMIT 5;
                """, (like_term, like_term, like_term))
                hotels = [dict(r) for r in cur.fetchall()]

                # Trips (user's or public)
                if user:
                    cur.execute("""
                        SELECT id, name, start_date, end_date, total_budget, currency, cover_image, travel_style 
                        FROM globetrotter_trip 
                        WHERE (user_id = %s OR is_public = TRUE) AND (name ILIKE %s OR description ILIKE %s)
                        ORDER BY start_date DESC LIMIT 4;
                    """, (user['id'], like_term, like_term))
                else:
                    cur.execute("""
                        SELECT id, name, start_date, end_date, total_budget, currency, cover_image, travel_style, share_token 
                        FROM globetrotter_trip 
                        WHERE is_public = TRUE AND (name ILIKE %s OR description ILIKE %s)
                        ORDER BY start_date DESC LIMIT 4;
                    """, (like_term, like_term))
                trips = [dict(r) for r in cur.fetchall()]

                # Community Posts
                cur.execute("""
                    SELECT p.id, p.title, p.rating, p.cover_image, p.travel_style, p.likes_count, c.name as city_name 
                    FROM globetrotter_community_post p 
                    LEFT JOIN globetrotter_city c ON p.city_id = c.id 
                    WHERE p.active = TRUE AND (p.title ILIKE %s OR p.tags ILIKE %s OR p.experience_text ILIKE %s)
                    ORDER BY p.likes_count DESC LIMIT 4;
                """, (like_term, like_term, like_term))
                posts = [dict(r) for r in cur.fetchall()]

                conn.close()
                return self._send_json({
                    'success': True,
                    'query': q,
                    'results': {
                        'destinations': dests,
                        'activities': acts,
                        'hotels': hotels,
                        'trips': trips,
                        'community': posts
                    }
                })

            # 11. Admin Analytics Dashboard
            elif path == '/api/v1/admin/analytics':
                if not user or user.get('role') != 'admin':
                    conn.close()
                    return self._send_error('Admin privileges required.', status=403)

                cur.execute("SELECT COUNT(*) FROM res_users;")
                total_users = cur.fetchone()['count']

                cur.execute("SELECT COUNT(*) FROM globetrotter_trip;")
                total_trips = cur.fetchone()['count']

                cur.execute("SELECT SUM(total_budget) as total_budget_sum, AVG(total_budget) as avg_budget FROM globetrotter_trip;")
                budget_row = cur.fetchone()
                total_budget_sum = float(budget_row['total_budget_sum'] or 0.0)
                avg_budget = float(budget_row['avg_budget'] or 0.0)

                # Popular Cities
                cur.execute("""
                    SELECT c.name, c.country, COUNT(s.id) as visit_count
                    FROM globetrotter_city c
                    LEFT JOIN globetrotter_trip_stop s ON c.id = s.city_id
                    GROUP BY c.id, c.name, c.country
                    ORDER BY visit_count DESC, c.popularity DESC
                    LIMIT 6;
                """)
                top_cities = [dict(c) for c in cur.fetchall()]

                # Popular Activities
                cur.execute("""
                    SELECT a.name, a.category, COUNT(ta.id) as schedule_count
                    FROM globetrotter_activity a
                    LEFT JOIN globetrotter_trip_activity ta ON a.id = ta.activity_id
                    GROUP BY a.id, a.name, a.category
                    ORDER BY schedule_count DESC, a.popularity DESC
                    LIMIT 6;
                """)
                top_activities = [dict(a) for a in cur.fetchall()]

                # Travel Style Distribution
                cur.execute("""
                    SELECT travel_style, COUNT(*) as count
                    FROM globetrotter_trip
                    GROUP BY travel_style
                    ORDER BY count DESC;
                """)
                styles = [dict(s) for s in cur.fetchall()]

                # Hotel Tier Preferences
                cur.execute("""
                    SELECT h.hotel_category, COUNT(th.id) as bookings_count
                    FROM globetrotter_hotel h
                    LEFT JOIN globetrotter_trip_hotel th ON h.id = th.hotel_id
                    GROUP BY h.hotel_category
                    ORDER BY bookings_count DESC;
                """)
                hotel_tiers = [dict(h) for h in cur.fetchall()]

                # Community Stats
                cur.execute("SELECT COUNT(*) as total_posts, SUM(likes_count) as total_likes, SUM(imports_count) as total_imports FROM globetrotter_community_post WHERE active = TRUE;")
                comm_row = cur.fetchone()

                conn.close()
                return self._send_json({
                    'success': True,
                    'analytics': {
                        'total_users': total_users,
                        'total_trips': total_trips,
                        'total_budget_sum': total_budget_sum,
                        'avg_budget': avg_budget,
                        'top_cities': top_cities,
                        'top_activities': top_activities,
                        'styles': styles,
                        'hotel_tiers': hotel_tiers,
                        'community': {
                            'total_posts': int(comm_row['total_posts'] or 0),
                            'total_likes': int(comm_row['total_likes'] or 0),
                            'total_imports': int(comm_row['total_imports'] or 0)
                        }
                    }
                })

            # 12. Admin User Management List
            elif path == '/api/v1/admin/users':
                if not user or user.get('role') != 'admin':
                    conn.close()
                    return self._send_error('Admin privileges required.', status=403)

                cur.execute("""
                    SELECT u.id, u.name, u.email, u.first_name, u.last_name, u.city, u.country,
                           u.preferred_currency, u.preferred_travel_style, u.role, u.created_at,
                           COUNT(t.id) as trips_count
                    FROM res_users u
                    LEFT JOIN globetrotter_trip t ON u.id = t.user_id
                    GROUP BY u.id
                    ORDER BY u.created_at DESC;
                """)
                users_list = [dict(u) for u in cur.fetchall()]
                conn.close()
                return self._send_json({'success': True, 'users': users_list})

        conn.close()
        return self._send_error('Endpoint not found', status=404)


    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._read_json_body()

        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            user = self._get_current_user(cur)

            # 1. Signup (Extended with registration fields)
            if path == '/api/v1/auth/signup':
                name = (body.get('name') or '').strip()
                first_name = (body.get('first_name') or '').strip()
                last_name = (body.get('last_name') or '').strip()
                if not name and (first_name or last_name):
                    name = f"{first_name} {last_name}".strip()
                
                email = (body.get('email') or '').strip().lower()
                password = body.get('password') or ''
                phone = (body.get('phone') or '').strip()
                city = (body.get('city') or '').strip()
                country = (body.get('country') or '').strip()
                currency = body.get('preferred_currency', 'INR')
                travel_style = body.get('preferred_travel_style', 'balanced')
                avatar = body.get('avatar_url', '') or 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80'
                additional_info = body.get('additional_info', '')

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
                    INSERT INTO res_users (
                        name, email, password_hash, first_name, last_name, phone,
                        city, country, preferred_currency, preferred_travel_style,
                        avatar_url, additional_info, role
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'traveler')
                    RETURNING id, name, email, first_name, last_name, phone, city, country,
                              preferred_currency, preferred_travel_style, avatar_url, role;
                """, (
                    name, email, pbkdf2_sha256.hash(password), first_name, last_name, phone,
                    city, country, currency, travel_style, avatar, additional_info
                ))
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

                cur.execute("""
                    SELECT id, name, email, password_hash, first_name, last_name, phone,
                           city, country, preferred_currency, preferred_travel_style, avatar_url, role
                    FROM res_users WHERE email = %s
                """, (email,))
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
                cur.execute("""
                    SELECT id, name, email, first_name, last_name, phone, city, country,
                           preferred_currency, preferred_travel_style, avatar_url, role
                    FROM res_users WHERE email = %s
                """, (target_email,))
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

            # 8. Add Trip Activity / Flexible Day Section
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
                sec_type = body.get('section_type', 'activity')
                loc_addr = body.get('location_address', '')

                cur.execute("""
                    INSERT INTO globetrotter_trip_activity (
                        trip_id, stop_id, activity_id, name, category,
                        day_number, scheduled_time, duration_hours, estimated_cost,
                        notes, image, section_type, location_address
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    trip_id, body.get('stop_id'), body.get('activity_id'), name,
                    body.get('category', 'sightseeing'), day_num, time_slot, dur, cost,
                    body.get('notes', ''), body.get('image', ''), sec_type, loc_addr
                ))
                act_row = cur.fetchone()
                conn.close()
                return self._send_json({'success': True, 'activity_id': act_row['id'], 'message': 'Section added to itinerary!'})

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

                if stop_id:
                    cur.execute("SELECT * FROM globetrotter_trip_hotel WHERE trip_id = %s AND stop_id = %s", (trip_id, stop_id))
                    prev_booking = cur.fetchone()
                    if prev_booking and prev_booking.get('expense_id'):
                        cur.execute("DELETE FROM globetrotter_expense WHERE id = %s", (prev_booking['expense_id'],))
                        cur.execute("DELETE FROM globetrotter_trip_hotel WHERE id = %s", (prev_booking['id'],))

                exp_name = f"Accommodation: {hotel['name']} ({nights} nights)"
                cur.execute("""
                    INSERT INTO globetrotter_expense (trip_id, stop_id, category, name, amount, date, notes)
                    VALUES (%s, %s, 'accommodation', %s, %s, %s, %s)
                    RETURNING id;
                """, (trip_id, stop_id, exp_name, total_cost, check_in, f"Auto-generated for {hotel['name']}"))
                exp_row = cur.fetchone()
                exp_id = exp_row['id']

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

            # 8c. Smart Itinerary Balancing (Accept Suggestion / Rebalance)
            elif path.startswith('/api/v1/trips/') and path.endswith('/balance'):
                if not user:
                    conn.close()
                    return self._send_error('Authentication required', status=401)

                trip_id = int(path.split('/')[4])
                cur.execute("SELECT * FROM globetrotter_trip WHERE id = %s", (trip_id,))
                trip = cur.fetchone()
                if not trip or (trip['user_id'] != user['id'] and user.get('role') != 'admin'):
                    conn.close()
                    return self._send_error('Unauthorized', status=403)

                activity_id = body.get('activity_id')
                target_day = int(body.get('target_day') or 1)

                if activity_id:
                    cur.execute("""
                        UPDATE globetrotter_trip_activity
                        SET day_number = %s
                        WHERE id = %s AND trip_id = %s;
                    """, (target_day, int(activity_id), trip_id))
                else:
                    # Auto-balance all overloaded days
                    cur.execute("SELECT * FROM globetrotter_trip_activity WHERE trip_id = %s ORDER BY day_number ASC", (trip_id,))
                    acts = [dict(a) for a in cur.fetchall()]
                    cur.execute("SELECT * FROM globetrotter_trip_stop WHERE trip_id = %s", (trip_id,))
                    stops = cur.fetchall()
                    suggestions = get_balancing_suggestions(dict(trip), stops, acts)
                    for sug in suggestions:
                        cur.execute("""
                            UPDATE globetrotter_trip_activity
                            SET day_number = %s
                            WHERE id = %s AND trip_id = %s;
                        """, (sug['to_day'], sug['activity_id'], trip_id))

                conn.close()
                return self._send_json({'success': True, 'message': 'Itinerary successfully balanced!'})

            # 8d. Move Activity Day
            elif '/activities/' in path and path.endswith('/move-day'):
                if not user:
                    conn.close()
                    return self._send_error('Authentication required', status=401)

                parts = path.split('/')
                trip_id = int(parts[4])
                act_id = int(parts[6])
                new_day = int(body.get('day_number') or 1)

                cur.execute("SELECT * FROM globetrotter_trip WHERE id = %s", (trip_id,))
                trip = cur.fetchone()
                if not trip or (trip['user_id'] != user['id'] and user.get('role') != 'admin'):
                    conn.close()
                    return self._send_error('Unauthorized', status=403)

                cur.execute("UPDATE globetrotter_trip_activity SET day_number = %s WHERE id = %s AND trip_id = %s", (new_day, act_id, trip_id))
                conn.close()
                return self._send_json({'success': True, 'message': f'Activity moved to Day {new_day}.'})

            # 8e. Duplicate Activity
            elif '/activities/' in path and path.endswith('/duplicate'):
                if not user:
                    conn.close()
                    return self._send_error('Authentication required', status=401)

                parts = path.split('/')
                trip_id = int(parts[4])
                act_id = int(parts[6])

                cur.execute("SELECT * FROM globetrotter_trip WHERE id = %s", (trip_id,))
                trip = cur.fetchone()
                if not trip or (trip['user_id'] != user['id'] and user.get('role') != 'admin'):
                    conn.close()
                    return self._send_error('Unauthorized', status=403)

                cur.execute("SELECT * FROM globetrotter_trip_activity WHERE id = %s AND trip_id = %s", (act_id, trip_id))
                act = cur.fetchone()
                if not act:
                    conn.close()
                    return self._send_error('Activity not found', status=404)

                target_day = int(body.get('target_day') or act['day_number'] or 1)

                cur.execute("""
                    INSERT INTO globetrotter_trip_activity (
                        trip_id, stop_id, activity_id, name, category,
                        day_number, scheduled_time, duration_hours, estimated_cost,
                        sequence, notes, image, section_type, location_address
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    trip_id, act['stop_id'], act['activity_id'], f"{act['name']} (Copy)", act['category'],
                    target_day, act['scheduled_time'], act['duration_hours'], act['estimated_cost'],
                    act['sequence'] + 5, act['notes'], act['image'], act['section_type'], act['location_address']
                ))
                new_act_id = cur.fetchone()['id']
                conn.close()
                return self._send_json({'success': True, 'activity_id': new_act_id, 'message': 'Activity section duplicated!'})

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
                        INSERT INTO globetrotter_trip_activity (trip_id, stop_id, activity_id, name, category, day_number, scheduled_time, duration_hours, estimated_cost, sequence, notes, image, section_type, location_address)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (
                        new_trip_id, new_stop_id, a['activity_id'], a['name'], a['category'],
                        a['day_number'], a['scheduled_time'], a['duration_hours'], a['estimated_cost'],
                        a['sequence'], a['notes'], a['image'], a['section_type'], a['location_address']
                    ))

                cur.execute("SELECT * FROM globetrotter_expense WHERE trip_id = %s", (src_trip_id,))
                for e in cur.fetchall():
                    new_stop_id = stop_map.get(e['stop_id'])
                    cur.execute("""
                        INSERT INTO globetrotter_expense (trip_id, stop_id, category, name, amount, date, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """, (new_trip_id, new_stop_id, e['category'], e['name'], e['amount'], e['date'], e['notes']))

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

            # 12. Copy Shared Trip
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
                cur.execute("UPDATE globetrotter_shared_trip SET copy_count = copy_count + 1 WHERE share_token = %s", (token,))

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
                        INSERT INTO globetrotter_trip_activity (trip_id, stop_id, activity_id, name, category, day_number, scheduled_time, duration_hours, estimated_cost, sequence, notes, image, section_type, location_address)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (
                        new_trip_id, new_stop_id, a['activity_id'], a['name'], a['category'],
                        a['day_number'], a['scheduled_time'], a['duration_hours'], a['estimated_cost'],
                        a['sequence'], a['notes'], a['image'], a['section_type'], a['location_address']
                    ))

                cur.execute("SELECT * FROM globetrotter_expense WHERE trip_id = %s", (src_trip_id,))
                for e in cur.fetchall():
                    new_stop_id = stop_map.get(e['stop_id'])
                    cur.execute("""
                        INSERT INTO globetrotter_expense (trip_id, stop_id, category, name, amount, date, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """, (new_trip_id, new_stop_id, e['category'], e['name'], e['amount'], e['date'], e['notes']))

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

            # 14. Create Community Experience Post
            elif path == '/api/v1/community/posts':
                if not user:
                    conn.close()
                    return self._send_error('Authentication required', status=401)

                title = (body.get('title') or '').strip()
                experience_text = (body.get('experience_text') or '').strip()
                city_id = body.get('city_id')
                cover_image = body.get('cover_image') or 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=800&q=80'
                rating = float(body.get('rating') or 5.0)
                cost = float(body.get('approximate_cost') or 0.0)
                travel_style = body.get('travel_style', 'balanced')
                tags = body.get('tags', '')
                highlights = body.get('activity_highlights', [])

                if not title or not experience_text:
                    conn.close()
                    return self._send_error('Title and experience details are required.')

                cur.execute("""
                    INSERT INTO globetrotter_community_post (
                        user_id, city_id, title, experience_text, cover_image,
                        rating, approximate_cost, travel_style, tags, activity_highlights
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    user['id'], city_id, title, experience_text, cover_image,
                    rating, cost, travel_style, tags, json.dumps(highlights)
                ))
                new_post_id = cur.fetchone()['id']
                conn.close()
                return self._send_json({'success': True, 'post_id': new_post_id, 'message': 'Community experience published!'})

            # 15. Like / Save Community Post
            elif '/community/posts/' in path and path.endswith('/interact'):
                if not user:
                    conn.close()
                    return self._send_error('Authentication required', status=401)

                post_id = int(path.split('/')[-2])
                itype = body.get('type', 'like') # 'like' or 'save'

                cur.execute("SELECT id FROM globetrotter_community_interaction WHERE user_id = %s AND post_id = %s AND interaction_type = %s", (user['id'], post_id, itype))
                existing = cur.fetchone()

                if existing:
                    # Toggle off
                    cur.execute("DELETE FROM globetrotter_community_interaction WHERE id = %s", (existing['id'],))
                    if itype == 'like':
                        cur.execute("UPDATE globetrotter_community_post SET likes_count = GREATEST(0, likes_count - 1) WHERE id = %s", (post_id,))
                    else:
                        cur.execute("UPDATE globetrotter_community_post SET saves_count = GREATEST(0, saves_count - 1) WHERE id = %s", (post_id,))
                    active_now = False
                else:
                    # Toggle on
                    cur.execute("INSERT INTO globetrotter_community_interaction (user_id, post_id, interaction_type) VALUES (%s, %s, %s)", (user['id'], post_id, itype))
                    if itype == 'like':
                        cur.execute("UPDATE globetrotter_community_post SET likes_count = likes_count + 1 WHERE id = %s", (post_id,))
                    else:
                        cur.execute("UPDATE globetrotter_community_post SET saves_count = saves_count + 1 WHERE id = %s", (post_id,))
                    active_now = True

                cur.execute("SELECT likes_count, saves_count FROM globetrotter_community_post WHERE id = %s", (post_id,))
                counts = cur.fetchone()
                conn.close()
                return self._send_json({
                    'success': True,
                    'interaction_type': itype,
                    'active': active_now,
                    'likes_count': counts['likes_count'],
                    'saves_count': counts['saves_count']
                })

            # 16. Community 1-Click Import to Itinerary
            elif '/community/posts/' in path and path.endswith('/import'):
                if not user:
                    conn.close()
                    return self._send_error('Authentication required', status=401)

                post_id = int(path.split('/')[-2])
                trip_id = body.get('trip_id')
                stop_id = body.get('stop_id')
                target_day = int(body.get('day_number') or 1)
                selected_activities = body.get('activities', [])

                if not trip_id:
                    conn.close()
                    return self._send_error('Destination Trip is required for import.')

                cur.execute("SELECT * FROM globetrotter_trip WHERE id = %s", (int(trip_id),))
                trip = cur.fetchone()
                if not trip or (trip['user_id'] != user['id'] and user.get('role') != 'admin'):
                    conn.close()
                    return self._send_error('Unauthorized or trip not found', status=403)

                cur.execute("SELECT * FROM globetrotter_community_post WHERE id = %s", (post_id,))
                post = cur.fetchone()
                if not post:
                    conn.close()
                    return self._send_error('Community post not found', status=404)

                imported_count = 0
                imported_cost = 0.0

                for item in selected_activities:
                    act_name = item.get('name', 'Community Highlight')
                    act_cat = item.get('category', 'sightseeing')
                    act_cost = float(item.get('estimated_cost') or 0.0)
                    act_dur = float(item.get('duration_hours') or 2.0)
                    act_time = item.get('time', '10:00')
                    sec_type = item.get('section_type', 'activity')
                    loc_addr = item.get('location_address', '')
                    notes = item.get('notes', f"Imported from '{post['title']}'")

                    cur.execute("""
                        INSERT INTO globetrotter_trip_activity (
                            trip_id, stop_id, name, category, day_number, scheduled_time,
                            duration_hours, estimated_cost, notes, section_type, location_address
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (
                        trip_id, stop_id, act_name, act_cat, target_day, act_time,
                        act_dur, act_cost, notes, sec_type, loc_addr
                    ))

                    if act_cost > 0:
                        imported_cost += act_cost

                    imported_count += 1

                # Increment import counters
                cur.execute("UPDATE globetrotter_community_post SET imports_count = imports_count + 1 WHERE id = %s", (post_id,))
                cur.execute("""
                    INSERT INTO globetrotter_community_interaction (user_id, post_id, interaction_type)
                    VALUES (%s, %s, 'import')
                    ON CONFLICT (user_id, post_id, interaction_type) DO NOTHING;
                """, (user['id'], post_id))

                conn.close()
                return self._send_json({
                    'success': True,
                    'imported_count': imported_count,
                    'imported_cost': imported_cost,
                    'message': f"Successfully imported {imported_count} activities into Day {target_day} of your itinerary!"
                })

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

            # 1. Update Profile (Extended)
            if path == '/api/v1/auth/profile':
                name = body.get('name', user['name'])
                first_name = body.get('first_name', user.get('first_name', ''))
                last_name = body.get('last_name', user.get('last_name', ''))
                phone = body.get('phone', user.get('phone', ''))
                city = body.get('city', user.get('city', ''))
                country = body.get('country', user.get('country', ''))
                additional_info = body.get('additional_info', user.get('additional_info', ''))
                pref_curr = body.get('preferred_currency', user['preferred_currency'])
                pref_style = body.get('preferred_travel_style', user['preferred_travel_style'])
                bio = body.get('bio', user.get('bio', ''))
                avatar = body.get('avatar_url', user.get('avatar_url', ''))

                cur.execute("""
                    UPDATE res_users 
                    SET name = %s, first_name = %s, last_name = %s, phone = %s,
                        city = %s, country = %s, additional_info = %s,
                        preferred_currency = %s, preferred_travel_style = %s,
                        bio = %s, avatar_url = %s
                    WHERE id = %s
                    RETURNING id, name, email, first_name, last_name, phone, city, country,
                              preferred_currency, preferred_travel_style, preferred_language,
                              avatar_url, bio, additional_info, role;
                """, (
                    name, first_name, last_name, phone, city, country,
                    additional_info, pref_curr, pref_style, bio, avatar, user['id']
                ))
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

                if booking.get('expense_id'):
                    exp_name = f"Accommodation: {booking['hotel_name']} ({nights} nights)"
                    cur.execute("""
                        UPDATE globetrotter_expense 
                        SET amount = %s, date = %s, name = %s
                        WHERE id = %s;
                    """, (total_cost, check_in, exp_name, booking['expense_id']))

                conn.close()
                return self._send_json({'success': True, 'total_cost': total_cost, 'nights': nights, 'message': 'Hotel accommodation updated!'})

            # 3. Update Activity / Flexible Day Section
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
                        category = COALESCE(%s, category),
                        section_type = COALESCE(%s, section_type),
                        location_address = COALESCE(%s, location_address)
                    WHERE id = %s;
                """, (
                    body.get('name'), body.get('day_number'), body.get('scheduled_time'),
                    body.get('duration_hours'), body.get('estimated_cost'), body.get('notes'),
                    body.get('category'), body.get('section_type'), body.get('location_address'), act_id
                ))
                conn.close()
                return self._send_json({'success': True, 'message': 'Activity section updated!'})


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

from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer

def run_server(port=8069):
    init_db()
    server_address = ('0.0.0.0', port)
    httpd = ThreadingHTTPServer(server_address, GlobeTrotterRequestHandler)
    _logger.info(f"GlobeTrotter Server running at http://127.0.0.1:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        _logger.info("Server shutting down.")
        httpd.server_close()

if __name__ == '__main__':
    run_server(8069)

