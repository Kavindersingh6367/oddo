# -*- coding: utf-8 -*-
from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    preferred_currency = fields.Selection([
        ('INR', '₹ INR (Indian Rupee)'),
        ('USD', '$ USD (US Dollar)'),
        ('EUR', '€ EUR (Euro)'),
        ('GBP', '£ GBP (British Pound)'),
        ('JPY', '¥ JPY (Japanese Yen)'),
        ('AED', 'د.إ AED (UAE Dirham)'),
        ('SGD', 'S$ SGD (Singapore Dollar)'),
    ], string='Preferred Currency', default='INR')

    preferred_travel_style = fields.Selection([
        ('budget', 'Budget'),
        ('balanced', 'Balanced'),
        ('luxury', 'Luxury'),
        ('adventure', 'Adventure'),
        ('relaxed', 'Relaxed'),
        ('family', 'Family'),
        ('solo', 'Solo'),
        ('business', 'Business'),
    ], string='Preferred Travel Style', default='balanced')

    preferred_language = fields.Selection([
        ('en', 'English'),
        ('fr', 'French'),
        ('es', 'Spanish'),
        ('de', 'German'),
        ('ja', 'Japanese'),
        ('hi', 'Hindi'),
    ], string='Preferred Language', default='en')

    avatar_url = fields.Char(string='Profile Photo URL')
    bio = fields.Text(string='Traveler Bio')

    trip_ids = fields.One2many('globetrotter.trip', 'user_id', string='Trips')
    saved_destination_ids = fields.One2many('globetrotter.saved.destination', 'user_id', string='Saved Destinations')
