# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class GlobetrotterExpense(models.Model):
    _name = 'globetrotter.expense'
    _description = 'GlobeTrotter Trip Expense & Logistics'
    _order = 'date asc, id asc'

    trip_id = fields.Many2one('globetrotter.trip', string='Trip', required=True, ondelete='cascade', index=True)
    stop_id = fields.Many2one('globetrotter.trip.stop', string='Associated Stop', ondelete='set null')
    
    name = fields.Char(string='Expense Description', required=True)
    category = fields.Selection([
        ('transportation', 'Transportation / Flights / Trains'),
        ('accommodation', 'Accommodation / Hotel / Villa'),
        ('activities', 'Activities & Tours'),
        ('food', 'Food & Dining'),
        ('miscellaneous', 'Miscellaneous / Shopping / Visa'),
    ], string='Expense Category', required=True, default='accommodation', index=True)
    
    amount = fields.Float(string='Cost Amount', required=True, default=0.0)
    date = fields.Date(string='Date Incurred')
    notes = fields.Text(string='Notes / Booking Reference')

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount < 0:
                raise ValidationError(_("Expense amount cannot be negative."))
