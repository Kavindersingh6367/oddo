# -*- coding: utf-8 -*-
def depends(*args):
    def decorator(f):
        f._depends = args
        return f
    return decorator

def constrains(*args):
    def decorator(f):
        f._constrains = args
        return f
    return decorator

def onchange(*args):
    def decorator(f):
        f._onchange = args
        return f
    return decorator

def model(f):
    return f

def multi(f):
    return f
