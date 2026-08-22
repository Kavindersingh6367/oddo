# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class GlobetrotterTripStop(models.Model):
    _name = 'globetrotter.trip.stop'
    _description = 'GlobeTrotter Itinerary Stop / City'
    _order = 'sequence asc, arrival_date asc, id asc'

    trip_id = fields.Many2one('globetrotter.trip', string='Trip', required=True, ondelete='cascade', index=True)
    city_id = fields.Many2one('globetrotter.city', string='City / Destination', required=True, ondelete='restrict', index=True)
    
    city_name = fields.Char(related='city_id.name', string='City Name', store=True)
    country_name = fields.Char(related='city_id.country', string='Country', store=True)
    cover_image = fields.Char(related='city_id.cover_image', string='City Photo')
    
    sequence = fields.Integer(string='Sequence Order', default=10, index=True)
    arrival_date = fields.Date(string='Arrival Date', required=True)
    departure_date = fields.Date(string='Departure Date', required=True)
    duration_days = fields.Integer(string='Duration (Days)', compute='_compute_duration', store=True)
    notes = fields.Text(string='Stop Notes & Recommendations')
    
    trip_activity_ids = fields.One2many('globetrotter.trip.activity', 'stop_id', string='Stop Activities', copy=True)
    expense_ids = fields.One2many('globetrotter.expense', 'stop_id', string='Stop Expenses')

    @api.depends('arrival_date', 'departure_date')
    def _compute_duration(self):
        for stop in self:
            if stop.arrival_date and stop.departure_date:
                delta = (stop.departure_date - stop.arrival_date).days + 1
                stop.duration_days = max(1, delta)
            else:
                stop.duration_days = 1

    @api.constrains('arrival_date', 'departure_date')
    def _check_stop_dates(self):
        for stop in self:
            if stop.arrival_date and stop.departure_date and stop.departure_date < stop.arrival_date:
                raise ValidationError(_("Stop departure date cannot be before arrival date."))
            if stop.trip_id.start_date and stop.arrival_date and stop.arrival_date < stop.trip_id.start_date:
                raise ValidationError(_("Stop arrival date cannot be before trip start date."))
            if stop.trip_id.end_date and stop.departure_date and stop.departure_date > stop.trip_id.end_date:
                raise ValidationError(_("Stop departure date cannot exceed trip end date."))
