# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class GlobetrotterActivity(models.Model):
    _name = 'globetrotter.activity'
    _description = 'GlobeTrotter Destination Activity'
    _order = 'popularity desc, name asc'

    city_id = fields.Many2one('globetrotter.city', string='City', required=True, ondelete='cascade', index=True)
    city_name = fields.Char(related='city_id.name', string='City Name', store=True)
    country_name = fields.Char(related='city_id.country', string='Country', store=True)
    
    name = fields.Char(string='Activity Name', required=True, index=True)
    description = fields.Text(string='Description')
    category = fields.Selection([
        ('sightseeing', 'Sightseeing'),
        ('food', 'Food & Dining'),
        ('adventure', 'Adventure'),
        ('culture', 'Culture & History'),
        ('nature', 'Nature & Outdoors'),
        ('shopping', 'Shopping'),
        ('entertainment', 'Entertainment'),
        ('relaxation', 'Relaxation & Wellness'),
    ], string='Category', required=True, default='sightseeing', index=True)
    
    duration_hours = fields.Float(string='Duration (Hours)', default=2.0, required=True)
    estimated_cost = fields.Float(string='Estimated Cost', default=0.0, required=True)
    currency = fields.Char(string='Currency', default='INR')
    popularity = fields.Integer(string='Popularity (1-100)', default=85)
    image = fields.Char(string='Image URL')
    location_name = fields.Char(string='Specific Location / Landmark')

    @api.constrains('duration_hours')
    def _check_duration(self):
        for record in self:
            if record.duration_hours < 0.25 or record.duration_hours > 24.0:
                raise ValidationError(_("Duration must be between 0.25 and 24 hours."))

    @api.constrains('estimated_cost')
    def _check_cost(self):
        for record in self:
            if record.estimated_cost < 0:
                raise ValidationError(_("Estimated cost cannot be negative."))
