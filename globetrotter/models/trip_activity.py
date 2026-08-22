# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class GlobetrotterTripActivity(models.Model):
    _name = 'globetrotter.trip.activity'
    _description = 'GlobeTrotter Scheduled Itinerary Activity'
    _order = 'day_number asc, sequence asc, scheduled_time asc, id asc'

    trip_id = fields.Many2one('globetrotter.trip', string='Trip', required=True, ondelete='cascade', index=True)
    stop_id = fields.Many2one('globetrotter.trip.stop', string='Trip Stop / City', ondelete='cascade', index=True)
    activity_id = fields.Many2one('globetrotter.activity', string='Catalog Activity Source', ondelete='set null')
    
    name = fields.Char(string='Activity Title', required=True)
    category = fields.Selection([
        ('sightseeing', 'Sightseeing'),
        ('food', 'Food & Dining'),
        ('adventure', 'Adventure'),
        ('culture', 'Culture & History'),
        ('nature', 'Nature & Outdoors'),
        ('shopping', 'Shopping'),
        ('entertainment', 'Entertainment'),
        ('relaxation', 'Relaxation & Wellness'),
        ('transport', 'Transit / Transfer'),
    ], string='Category', default='sightseeing', required=True)
    
    day_number = fields.Integer(string='Day Number (1, 2, ...)', default=1, required=True, index=True)
    scheduled_date = fields.Date(string='Scheduled Date')
    scheduled_time = fields.Char(string='Time Slot', default='10:00')
    duration_hours = fields.Float(string='Duration (Hours)', default=2.0)
    estimated_cost = fields.Float(string='Estimated Cost', default=0.0)
    sequence = fields.Integer(string='Display Order', default=10)
    notes = fields.Text(string='Activity Notes')
    image = fields.Char(string='Photo URL')

    @api.onchange('activity_id')
    def _onchange_activity_id(self):
        if self.activity_id:
            self.name = self.activity_id.name
            self.category = self.activity_id.category
            self.duration_hours = self.activity_id.duration_hours
            self.estimated_cost = self.activity_id.estimated_cost
            self.image = self.activity_id.image

    @api.constrains('estimated_cost')
    def _check_cost(self):
        for record in self:
            if record.estimated_cost < 0:
                raise ValidationError(_("Activity cost cannot be negative."))

    @api.constrains('day_number')
    def _check_day_number(self):
        for record in self:
            if record.day_number < 1:
                raise ValidationError(_("Day number must be at least 1."))
