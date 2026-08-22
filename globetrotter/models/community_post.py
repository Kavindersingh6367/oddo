# -*- coding: utf-8 -*-
from odoo import models, fields, api

class GlobetrotterCommunityPost(models.Model):
    _name = 'globetrotter.community.post'
    _description = 'GlobeTrotter Community Travel Experience Post'
    _order = 'likes_count desc, created_at desc'

    user_id = fields.Many2one('res.users', string='Author', required=True, ondelete='cascade', default=lambda self: self.env.user)
    city_id = fields.Many2one('globetrotter.city', string='Destination', ondelete='set null')
    trip_id = fields.Many2one('globetrotter.trip', string='Source Trip', ondelete='set null')
    
    title = fields.Char(string='Experience Title', required=True)
    experience_text = fields.Text(string='Story & Travel Tips', required=True)
    cover_image = fields.Char(string='Cover Photo URL')
    rating = fields.Float(string='Experience Rating (1-5)', default=4.8)
    estimated_cost = fields.Float(string='Approximate Cost', default=0.0)
    travel_style = fields.Selection([
        ('budget', 'Budget'),
        ('balanced', 'Balanced'),
        ('luxury', 'Luxury'),
        ('adventure', 'Adventure'),
        ('relaxed', 'Relaxed'),
        ('family', 'Family'),
        ('solo', 'Solo'),
        ('business', 'Business'),
    ], string='Travel Style', default='balanced')

    activity_highlights = fields.Text(string='Structured Activities (JSON)')
    tags = fields.Char(string='Tags (e.g. #heritage, #foodie, #budget)')
    
    likes_count = fields.Integer(string='Likes', default=0)
    saves_count = fields.Integer(string='Saves', default=0)
    imports_count = fields.Integer(string='Itinerary Imports', default=0)
    
    active = fields.Boolean(string='Active', default=True)
    created_at = fields.Datetime(string='Created At', default=fields.Datetime.now)
