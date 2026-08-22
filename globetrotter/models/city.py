# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class GlobetrotterCity(models.Model):
    _name = 'globetrotter.city'
    _description = 'GlobeTrotter Travel Destination City'
    _order = 'popularity desc, name asc'

    name = fields.Char(string='City Name', required=True, index=True)
    country = fields.Char(string='Country', required=True, index=True)
    region = fields.Selection([
        ('asia', 'Asia'),
        ('europe', 'Europe'),
        ('north_america', 'North America'),
        ('south_america', 'South America'),
        ('middle_east', 'Middle East'),
        ('africa', 'Africa'),
        ('oceania', 'Oceania'),
    ], string='Region', required=True, default='asia', index=True)
    description = fields.Text(string='Description')
    cost_index = fields.Integer(string='Cost Index (1-5)', default=2, help='1=Budget, 5=Ultra Luxury')
    popularity = fields.Integer(string='Popularity Score (1-100)', default=80)
    recommended_duration_days = fields.Integer(string='Recommended Duration (Days)', default=3)
    cover_image = fields.Char(string='Cover Image URL')
    latitude = fields.Float(string='Latitude', digits=(10, 6))
    longitude = fields.Float(string='Longitude', digits=(10, 6))
    travel_styles = fields.Char(string='Matching Travel Styles', help='Comma separated tags e.g. culture,adventure,family')
    
    activity_ids = fields.One2many('globetrotter.activity', 'city_id', string='Activities')
    activity_count = fields.Integer(string='Total Activities', compute='_compute_activity_count', store=True)
    stop_ids = fields.One2many('globetrotter.trip.stop', 'city_id', string='Trip Stops')
    total_trips_count = fields.Integer(string='Total Trips Visited', compute='_compute_total_trips_count')

    @api.depends('activity_ids')
    def _compute_activity_count(self):
        for record in self:
            record.activity_count = len(record.activity_ids)

    def _compute_total_trips_count(self):
        for record in self:
            record.total_trips_count = len(record.stop_ids)

    @api.constrains('cost_index')
    def _check_cost_index(self):
        for record in self:
            if not (1 <= record.cost_index <= 5):
                raise ValidationError(_("Cost index must be between 1 and 5."))

    @api.constrains('popularity')
    def _check_popularity(self):
        for record in self:
            if not (1 <= record.popularity <= 100):
                raise ValidationError(_("Popularity must be between 1 and 100."))
