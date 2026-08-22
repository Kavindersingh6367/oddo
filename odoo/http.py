# -*- coding: utf-8 -*-
class HttpRequest:
    def __init__(self):
        self.method = 'GET'
        self.session = {}

class OdooRequest:
    def __init__(self):
        self.httprequest = HttpRequest()
        self.jsonrequest = {}
        self.session = None
        self.env = None
        self.db = 'globetrotter_db'

request = OdooRequest()

class Response:
    def __init__(self, response='', status=200, mimetype='text/plain'):
        self.response = response
        self.status = status
        self.mimetype = mimetype

class Controller:
    pass

def route(route=None, **kwargs):
    def decorator(f):
        f._odoo_route = route
        f._odoo_route_kwargs = kwargs
        return f
    return decorator
