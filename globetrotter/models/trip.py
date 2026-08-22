# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import secrets
import json
from datetime import datetime, timedelta

class GlobetrotterTrip(models.Model):
    _name = 'globetrotter.trip'
    _description = 'GlobeTrotter User Travel Itinerary'
    _order = 'start_date asc, id desc'

    user_id = fields.Many2one('res.users', string='Trip Owner', required=True, default=lambda self: self.env.user, index=True)
    name = fields.Char(string='Trip Name', required=True, index=True)
    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)
    end_date = fields.Date(string='End Date', required=True)
    description = fields.Text(string='Description')
    cover_image = fields.Char(string='Cover Image URL')
    
    currency = fields.Selection([
        ('INR', '₹ INR (Indian Rupee)'),
        ('USD', '$ USD (US Dollar)'),
        ('EUR', '€ EUR (Euro)'),
        ('GBP', '£ GBP (British Pound)'),
        ('JPY', '¥ JPY (Japanese Yen)'),
        ('AED', 'د.إ AED (UAE Dirham)'),
        ('SGD', 'S$ SGD (Singapore Dollar)'),
    ], string='Currency', required=True, default='INR')
    
    travelers_count = fields.Integer(string='Number of Travelers', required=True, default=1)
    total_budget = fields.Float(string='Total Budget', required=True, default=0.0)
    
    travel_style = fields.Selection([
        ('budget', 'Budget'),
        ('balanced', 'Balanced'),
        ('luxury', 'Luxury'),
        ('adventure', 'Adventure'),
        ('relaxed', 'Relaxed'),
        ('family', 'Family'),
        ('solo', 'Solo'),
        ('business', 'Business'),
    ], string='Travel Style', required=True, default='balanced')
    
    status = fields.Selection([
        ('draft', 'Draft'),
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('archived', 'Archived')
    ], string='Status', compute='_compute_status', store=True)

    # Relational Children
    stop_ids = fields.One2many('globetrotter.trip.stop', 'trip_id', string='Stops / Cities', copy=True)
    trip_activity_ids = fields.One2many('globetrotter.trip.activity', 'trip_id', string='Scheduled Activities', copy=True)
    expense_ids = fields.One2many('globetrotter.expense', 'trip_id', string='Expenses & Logistics', copy=True)
    
    # Sharing
    share_token = fields.Char(string='Public Share Token', copy=False, index=True)
    is_public = fields.Boolean(string='Publicly Shared', default=False)
    share_budget = fields.Boolean(string='Include Budget in Public View', default=True)

    # Computed fields
    duration_days = fields.Integer(string='Duration (Days)', compute='_compute_duration', store=True)
    stops_count = fields.Integer(string='Total Stops', compute='_compute_counts')
    activities_count = fields.Integer(string='Total Activities', compute='_compute_counts')
    
    # Budget Engine
    cost_activities = fields.Float(string='Activities Cost', compute='_compute_budget_engine')
    cost_transportation = fields.Float(string='Transportation Cost', compute='_compute_budget_engine')
    cost_accommodation = fields.Float(string='Accommodation Cost', compute='_compute_budget_engine')
    cost_food = fields.Float(string='Food & Dining Cost', compute='_compute_budget_engine')
    cost_miscellaneous = fields.Float(string='Miscellaneous Cost', compute='_compute_budget_engine')
    
    total_estimated_cost = fields.Float(string='Total Estimated Cost', compute='_compute_budget_engine', store=True)
    cost_per_traveler = fields.Float(string='Cost Per Traveler', compute='_compute_budget_engine')
    cost_per_day = fields.Float(string='Cost Per Day', compute='_compute_budget_engine')
    remaining_budget = fields.Float(string='Remaining Budget', compute='_compute_budget_engine')
    budget_utilization = fields.Float(string='Budget Utilization (%)', compute='_compute_budget_engine')
    
    # Rule-Based Intelligence & Balance Scoring
    trip_balance_score = fields.Integer(string='Trip Balance Score (0-100)', compute='_compute_balance_and_intelligence')
    balance_score_summary = fields.Text(string='Balance Score Factors Breakdown (JSON)', compute='_compute_balance_and_intelligence')
    budget_intelligence_alerts = fields.Text(string='Budget Intelligence Alerts (JSON)', compute='_compute_balance_and_intelligence')

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for trip in self:
            if trip.start_date and trip.end_date:
                delta = (trip.end_date - trip.start_date).days + 1
                trip.duration_days = max(1, delta)
            else:
                trip.duration_days = 1

    @api.depends('start_date', 'end_date')
    def _compute_status(self):
        today = fields.Date.context_today(self)
        for trip in self:
            if not trip.start_date or not trip.end_date:
                trip.status = 'draft'
            elif trip.end_date < today:
                trip.status = 'completed'
            elif trip.start_date <= today <= trip.end_date:
                trip.status = 'ongoing'
            else:
                trip.status = 'upcoming'

    def _compute_counts(self):
        for trip in self:
            trip.stops_count = len(trip.stop_ids)
            trip.activities_count = len(trip.trip_activity_ids)

    @api.depends('total_budget', 'travelers_count', 'duration_days', 'trip_activity_ids.estimated_cost', 'expense_ids.amount', 'expense_ids.category')
    def _compute_budget_engine(self):
        for trip in self:
            # Aggregate scheduled activities
            act_cost = sum(act.estimated_cost for act in trip.trip_activity_ids)
            
            # Aggregate categorized expenses
            transport = sum(exp.amount for exp in trip.expense_ids if exp.category == 'transportation')
            stay = sum(exp.amount for exp in trip.expense_ids if exp.category == 'accommodation')
            food = sum(exp.amount for exp in trip.expense_ids if exp.category == 'food')
            misc = sum(exp.amount for exp in trip.expense_ids if exp.category == 'miscellaneous')
            
            # If any expense was marked as activity category, add it
            act_expenses = sum(exp.amount for exp in trip.expense_ids if exp.category == 'activities')
            act_cost += act_expenses

            total = act_cost + transport + stay + food + misc
            travelers = max(1, trip.travelers_count or 1)
            days = max(1, trip.duration_days or 1)
            budget = trip.total_budget or 0.0

            trip.cost_activities = act_cost
            trip.cost_transportation = transport
            trip.cost_accommodation = stay
            trip.cost_food = food
            trip.cost_miscellaneous = misc
            trip.total_estimated_cost = total
            trip.cost_per_traveler = total / travelers
            trip.cost_per_day = total / days
            trip.remaining_budget = budget - total
            trip.budget_utilization = (total / budget * 100.0) if budget > 0 else (100.0 if total > 0 else 0.0)

    @api.depends('total_budget', 'total_estimated_cost', 'duration_days', 'stop_ids', 'trip_activity_ids', 'expense_ids')
    def _compute_balance_and_intelligence(self):
        for trip in self:
            alerts = []
            factors = []
            
            budget = trip.total_budget or 0.0
            total_cost = trip.total_estimated_cost or 0.0
            days = max(1, trip.duration_days or 1)
            stops_count = len(trip.stop_ids)
            acts_count = len(trip.trip_activity_ids)
            currency_sym = trip.currency or 'INR'

            # 1. Budget Intelligence Rules
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
                        'title': 'Budget Utilization High',
                        'message': f"Your itinerary is nearing full budget utilization ({trip.budget_utilization:.0f}%), with {currency_sym} {diff:,.0f} remaining.",
                        'severity': 'medium'
                    })
                else:
                    diff = budget - total_cost
                    alerts.append({
                        'type': 'success',
                        'code': 'WITHIN_BUDGET',
                        'title': 'Healthy Budget',
                        'message': f"Your itinerary is currently within budget with {currency_sym} {diff:,.0f} remaining.",
                        'severity': 'low'
                    })

            # Check category dominance (e.g. accommodation or transport > 40%)
            if total_cost > 0:
                if (trip.cost_accommodation / total_cost) >= 0.40:
                    pct = int((trip.cost_accommodation / total_cost) * 100)
                    alerts.append({
                        'type': 'info',
                        'code': 'DOMINANT_ACCOMMODATION',
                        'title': 'Accommodation Dominance',
                        'message': f"Accommodation represents {pct}% of your estimated trip cost.",
                        'severity': 'medium'
                    })
                if (trip.cost_transportation / total_cost) >= 0.35:
                    pct = int((trip.cost_transportation / total_cost) * 100)
                    alerts.append({
                        'type': 'info',
                        'code': 'DOMINANT_TRANSPORT',
                        'title': 'Transportation Dominance',
                        'message': f"Transportation represents {pct}% of your estimated trip cost.",
                        'severity': 'medium'
                    })

            # Daily spending outlier detection
            if days > 1 and total_cost > 0:
                daily_avg = total_cost / days
                # check if any specific day has high concentration
                day_costs = {}
                for act in trip.trip_activity_ids:
                    day_num = act.day_number or 1
                    day_costs[day_num] = day_costs.get(day_num, 0.0) + act.estimated_cost
                for day_num, dcost in day_costs.items():
                    if dcost >= daily_avg * 2.0 and dcost > 2000:
                        alerts.append({
                            'type': 'warning',
                            'code': 'EXPENSIVE_DAY',
                            'title': f'High Spending Day',
                            'message': f"Day {day_num} is significantly above your daily average ({currency_sym} {daily_avg:,.0f}/day vs {currency_sym} {dcost:,.0f} scheduled).",
                            'severity': 'medium'
                        })

            # 2. Travel Balance Score Calculation (0 - 100 pts)
            # Factor A: Budget Alignment (0-30 pts)
            score_budget = 30
            if budget <= 0:
                score_budget = 20
                factor_budget_desc = "Budget target not set; baseline score awarded."
            else:
                util = trip.budget_utilization
                if 60 <= util <= 100:
                    score_budget = 30
                    factor_budget_desc = f"Optimal budget alignment ({util:.0f}% utilized)."
                elif 30 <= util < 60:
                    score_budget = 24
                    factor_budget_desc = f"Conservative spending ({util:.0f}% utilized)."
                elif 100 < util <= 120:
                    score_budget = 18
                    factor_budget_desc = f"Slight budget overrun ({util:.0f}% utilized)."
                elif util > 120:
                    score_budget = 8
                    factor_budget_desc = f"Significant budget overrun ({util:.0f}% utilized)."
                else:
                    score_budget = 15
                    factor_budget_desc = "Very low budget allocation."
            factors.append({'name': 'Budget Discipline', 'score': score_budget, 'max': 30, 'description': factor_budget_desc})

            # Factor B: Activity Density & Pacing (0-25 pts)
            score_density = 25
            avg_acts_per_day = acts_count / days if days else 0
            if 1.5 <= avg_acts_per_day <= 4.0:
                score_density = 25
                factor_density_desc = f"Balanced pace ({avg_acts_per_day:.1f} activities/day)."
            elif 0.5 <= avg_acts_per_day < 1.5:
                score_density = 20
                factor_density_desc = f"Relaxed schedule ({avg_acts_per_day:.1f} activities/day)."
            elif avg_acts_per_day > 4.0:
                score_density = 14
                factor_density_desc = f"Packed schedule ({avg_acts_per_day:.1f} activities/day; risk of traveler fatigue)."
            else:
                score_density = 10
                factor_density_desc = "Few scheduled activities. Consider exploring destination experiences."
            factors.append({'name': 'Activity Density', 'score': score_density, 'max': 25, 'description': factor_density_desc})

            # Factor C: City Dwell Time & Travel Overhead (0-25 pts)
            score_dwell = 25
            if stops_count == 0:
                score_dwell = 5
                factor_dwell_desc = "No destination stops added yet."
            else:
                days_per_city = days / stops_count
                if 1.5 <= days_per_city <= 5.0:
                    score_dwell = 25
                    factor_dwell_desc = f"Healthy exploration pace ({days_per_city:.1f} days per city stop)."
                elif days_per_city > 5.0:
                    score_dwell = 22
                    factor_dwell_desc = f"Deep dive travel style ({days_per_city:.1f} days per city)."
                else:
                    score_dwell = 12
                    factor_dwell_desc = f"Fast-paced multi-city hopping ({days_per_city:.1f} days/city; higher transit time)."
            factors.append({'name': 'City Pacing & Dwell', 'score': score_dwell, 'max': 25, 'description': factor_dwell_desc})

            # Factor D: Itinerary Completeness (0-20 pts)
            score_complete = 0
            complete_reasons = []
            if stops_count > 0:
                score_complete += 5
                complete_reasons.append("Stops defined")
            if acts_count >= 2:
                score_complete += 5
                complete_reasons.append("Activities scheduled")
            if trip.expense_ids:
                score_complete += 5
                complete_reasons.append("Logistics accounted")
            if trip.description or trip.cover_image:
                score_complete += 5
                complete_reasons.append("Trip profile complete")
            factors.append({
                'name': 'Itinerary Completeness',
                'score': score_complete,
                'max': 20,
                'description': ", ".join(complete_reasons) if complete_reasons else "Initial draft stage"
            })

            total_score = min(100, max(0, score_budget + score_density + score_dwell + score_complete))
            trip.trip_balance_score = total_score
            trip.balance_score_summary = json.dumps(factors)
            trip.budget_intelligence_alerts = json.dumps(alerts)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for trip in self:
            if trip.start_date and trip.end_date and trip.end_date < trip.start_date:
                raise ValidationError(_("Trip end date cannot be earlier than start date."))

    @api.constrains('total_budget')
    def _check_budget(self):
        for trip in self:
            if trip.total_budget < 0:
                raise ValidationError(_("Trip budget cannot be negative."))

    @api.constrains('travelers_count')
    def _check_travelers(self):
        for trip in self:
            if trip.travelers_count < 1:
                raise ValidationError(_("Number of travelers must be at least 1."))

    def action_generate_share_token(self):
        self.ensure_one()
        if not self.share_token:
            self.share_token = secrets.token_urlsafe(16)
        self.is_public = True
        return self.share_token

    def action_duplicate_trip(self, target_user=None):
        self.ensure_one()
        owner = target_user or self.env.user
        copied_trip = self.copy({
            'name': f"{self.name} (Copy)" if owner == self.user_id else f"{self.name}",
            'user_id': owner.id,
            'is_public': False,
            'share_token': False,
        })
        return copied_trip
