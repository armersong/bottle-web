# coding: utf-8

__all__ = ["Service"]

class Service(object):
    """service base class"""
    def __init__(self, env):
        self._env = env

    def on_active(self):
        pass

    def on_inactive(self):
        pass

    def get_env(self):
        return self._env
