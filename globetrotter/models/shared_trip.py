# -*- coding: utf-8 -*-
from odoo import models, fields, api
import secrets

class GlobetrotterSharedTrip(models.Model):
    _name = 'globetrotter.shared.trip'
    _description = 'GlobeTrotter Public Share Link Token'
    _order = 'create_date desc'

    trip_id = fields.Many2one('globetrotter.trip', string='Trip', required=True, ondelete='cascade', index=True)
    share_token = fields.Char(string='Secure Token', required=True, default=lambda self: secrets.token_urlsafe(16), index=True)
    is_active = fields.Boolean(string='Link Active', default=True)
    view_count = fields.Integer(string='View Count', default=0)
    copy_count = fields.Integer(string='Copy Count', default=0)
    allow_budget_view = fields.Boolean(string='Show Budget in Public View', default=True)
    created_at = fields.Datetime(string='Generated At', default=fields.Datetime.now)

    _sql_constraints = [
        ('uniq_share_token', 'unique(share_token)', 'The share token must be unique!')
    ]
