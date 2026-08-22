# -*- coding: utf-8 -*-
class Model:
    _name = ''
    _description = ''
    _order = 'id desc'
    _inherit = None

    def __init__(self, env=None, ids=None):
        self.env = env
        self._ids = ids or []

    def ensure_one(self):
        return self

    def copy(self, default=None):
        return self

class TransientModel(Model):
    pass

class AbstractModel(Model):
    pass
