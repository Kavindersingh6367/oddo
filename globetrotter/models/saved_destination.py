# -*- coding: utf-8 -*-
from odoo import models, fields, api

class GlobetrotterSavedDestination(models.Model):
    _name = 'globetrotter.saved.destination'
    _description = 'GlobeTrotter User Bookmarked Destination'
    _order = 'create_date desc'

    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self.env.user, index=True)
    city_id = fields.Many2one('globetrotter.city', string='Saved City', required=True, ondelete='cascade', index=True)
    created_at = fields.Datetime(string='Saved Date', default=fields.Datetime.now)

    _sql_constraints = [
        ('uniq_user_city', 'unique(user_id, city_id)', 'This city is already saved in your bookmarks!')
    ]
