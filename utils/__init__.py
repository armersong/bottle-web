# coding: utf-8
from importlib import import_module
from uuid import uuid4

__all__ = ["gen_uuid", "get_object"]

def gen_uuid():
    return uuid4().hex

def get_object(obj_name):
    """according to object name, import object type"""
    names = obj_name.split(".")
    mod = import_module('.'.join(names[:-1]))
    obj = getattr(mod, names[-1])
    return obj
