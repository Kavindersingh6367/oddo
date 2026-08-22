# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime

class GlobetrotterTripHotel(models.Model):
    _name = 'globetrotter.trip.hotel'
    _description = 'GlobeTrotter Itinerary Hotel Accommodation Booking'
    _order = 'check_in asc, id asc'

    trip_id = fields.Many2one('globetrotter.trip', string='Trip', required=True, ondelete='cascade', index=True)
    hotel_id = fields.Many2one('globetrotter.hotel', string='Hotel', required=True, ondelete='restrict', index=True)
    stop_id = fields.Many2one('globetrotter.trip.stop', string='Associated Trip Stop / City', ondelete='cascade', index=True)
    expense_id = fields.Many2one('globetrotter.expense', string='Linked Accommodation Expense', ondelete='set null')

    hotel_name = fields.Char(related='hotel_id.name', string='Hotel Name', store=True)
    city_name = fields.Char(related='hotel_id.city_name', string='City Name', store=True)
    hotel_image = fields.Char(related='hotel_id.image', string='Hotel Photo')
    hotel_rating = fields.Float(related='hotel_id.rating', string='Rating')

    check_in = fields.Date(string='Check-In Date', required=True)
    check_out = fields.Date(string='Check-Out Date', required=True)
    number_of_nights = fields.Integer(string='Nights', compute='_compute_nights', store=True)
    number_of_guests = fields.Integer(string='Guests', default=2, required=True)
    number_of_rooms = fields.Integer(string='Rooms', default=1, required=True)
    
    price_per_night = fields.Float(string='Price Per Night', required=True)
    total_cost = fields.Float(string='Total Accommodation Cost', compute='_compute_total_cost', store=True)
    
    room_type_selected = fields.Char(string='Selected Room Type', default='Standard Double Room')
    notes = fields.Text(string='Booking Notes / Confirmation')
    status = fields.Selection([
        ('planned', 'Planned'),
        ('selected', 'Selected'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='selected', required=True)

    @api.depends('check_in', 'check_out')
    def _compute_nights(self):
        for record in self:
            if record.check_in and record.check_out:
                delta = (record.check_out - record.check_in).days
                record.number_of_nights = max(1, delta)
            else:
                record.number_of_nights = 1

    @api.depends('price_per_night', 'number_of_nights', 'number_of_rooms')
    def _compute_total_cost(self):
        for record in self:
            record.total_cost = (record.price_per_night or 0.0) * (record.number_of_nights or 1) * (record.number_of_rooms or 1)

    @api.constrains('check_in', 'check_out')
    def _check_dates(self):
        for record in self:
            if record.check_in and record.check_out and record.check_out <= record.check_in:
                raise ValidationError(_("Check-out date must be strictly after check-in date."))

    @api.constrains('number_of_rooms', 'number_of_guests')
    def _check_counts(self):
        for record in self:
            if record.number_of_rooms < 1:
                raise ValidationError(_("Number of rooms must be at least 1."))
            if record.number_of_guests < 1:
                raise ValidationError(_("Number of guests must be at least 1."))
