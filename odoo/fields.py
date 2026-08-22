# -*- coding: utf-8 -*-
from datetime import date, datetime

class Field:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.string = kwargs.get('string', args[0] if args and isinstance(args[0], str) else '')
        self.required = kwargs.get('required', False)
        self.default = kwargs.get('default', None)
        self.compute = kwargs.get('compute', None)
        self.store = kwargs.get('store', False)
        self.copy = kwargs.get('copy', True)
        self.index = kwargs.get('index', False)
        self.help = kwargs.get('help', '')
        self.readonly = kwargs.get('readonly', False)
        self.related = kwargs.get('related', None)
        self.digits = kwargs.get('digits', None)
        self.ondelete = kwargs.get('ondelete', None)

Char = Field
Text = Field
Integer = Field
Float = Field
Boolean = Field
Selection = Field
Many2one = Field
One2many = Field
Many2many = Field
Binary = Field

class Date(Field):
    @staticmethod
    def context_today(model=None):
        return date.today()

class Datetime(Field):
    @staticmethod
    def now():
        return datetime.utcnow()
