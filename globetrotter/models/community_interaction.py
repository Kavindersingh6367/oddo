# -*- coding: utf-8 -*-
from odoo import models, fields

class GlobetrotterCommunityInteraction(models.Model):
    _name = 'globetrotter.community.interaction'
    _description = 'GlobeTrotter Community Post Like, Save, or Import'

    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    post_id = fields.Many2one('globetrotter.community.post', string='Community Post', required=True, ondelete='cascade')
    interaction_type = fields.Selection([
        ('like', 'Like'),
        ('save', 'Save Bookmark'),
        ('import', 'Imported to Trip'),
    ], string='Type', required=True)
    created_at = fields.Datetime(string='Timestamp', default=fields.Datetime.now)

    _sql_constraints = [
        ('user_post_interaction_unique', 'unique(user_id, post_id, interaction_type)', 'Interaction already recorded for this user and post.'),
    ]
