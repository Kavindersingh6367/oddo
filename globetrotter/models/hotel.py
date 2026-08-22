# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class GlobetrotterHotel(models.Model):
    _name = 'globetrotter.hotel'
    _description = 'GlobeTrotter Destination Hotel & Accommodation'
    _order = 'popularity_score desc, rating desc, name asc'

    name = fields.Char(string='Hotel Name', required=True, index=True)
    city_id = fields.Many2one('globetrotter.city', string='City', required=True, ondelete='cascade', index=True)
    city_name = fields.Char(related='city_id.name', string='City Name', store=True)
    country = fields.Char(related='city_id.country', string='Country', store=True)
    
    description = fields.Text(string='Description')
    address = fields.Char(string='Address / Location Landmark')
    latitude = fields.Float(string='Latitude', digits=(10, 6))
    longitude = fields.Float(string='Longitude', digits=(10, 6))
    image = fields.Char(string='Cover Image URL')
    
    rating = fields.Float(string='Guest Rating (1.0-5.0)', default=4.5)
    review_count = fields.Integer(string='Review Count', default=150)
    price_per_night = fields.Float(string='Price Per Night', required=True, default=3000.0)
    currency = fields.Char(string='Currency', default='INR')
    
    hotel_category = fields.Selection([
        ('budget', 'Budget'),
        ('economy', 'Economy'),
        ('mid_range', 'Mid-Range'),
        ('premium', 'Premium'),
        ('luxury', 'Luxury'),
    ], string='Category Tier', required=True, default='mid_range', index=True)
    
    amenities = fields.Char(string='Amenities (comma-separated)', default='wifi,breakfast,ac,parking')
    room_types = fields.Char(string='Available Room Types', default='Standard Double Room, Deluxe Suite')
    max_guests = fields.Integer(string='Max Guests Per Room', default=3)
    available_rooms = fields.Integer(string='Available Rooms', default=10)
    check_in_time = fields.Char(string='Check-In Time', default='14:00')
    check_out_time = fields.Char(string='Check-Out Time', default='11:00')
    
    # Sub-scores (1.0 to 10.0 scale)
    location_score = fields.Float(string='Location Score (1-10)', default=9.0)
    cleanliness_score = fields.Float(string='Cleanliness Score (1-10)', default=9.2)
    service_score = fields.Float(string='Service Score (1-10)', default=8.8)
    value_score = fields.Float(string='Value For Money Score (1-10)', default=9.0)
    popularity_score = fields.Integer(string='Popularity Score (1-100)', default=88)
    active = fields.Boolean(string='Active', default=True)

    booking_ids = fields.One2many('globetrotter.trip.hotel', 'hotel_id', string='Trip Bookings')

    @api.constrains('price_per_night')
    def _check_price(self):
        for record in self:
            if record.price_per_night < 0:
                raise ValidationError(_("Hotel price per night cannot be negative."))

    @api.constrains('rating')
    def _check_rating(self):
        for record in self:
            if not (1.0 <= record.rating <= 5.0):
                raise ValidationError(_("Rating must be between 1.0 and 5.0."))
