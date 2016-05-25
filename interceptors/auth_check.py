# coding: utf-8

import re
from application import Interceptor
from bottle import request, HTTPError

class AuthCheck(Interceptor):
    name = 'auth_check'
    def __init__(self, id, env, *args, **kwargs):
        filters = self._parse_filters(kwargs.get('filters'))
        kwargs['filters'] = filters
        super(AuthCheck, self).__init__(id, env, *args, **kwargs)

    def _parse_filters(self, xml_node):
        filters = []
        if xml_node is None:
            return filters
        for node in xml_node.find('excludes').getchildren():
            if node.tag != 'exclude':
                continue
            methodes = node.attrib.get('method', 'all').strip().lower()\
                                                               .split(',')
            path = node.text.strip()
            filters.append((re.compile(path), methodes))
        return filters

    def _handle(self, callback, conf, func_args, *args, **kwargs):
        meth = request.method.lower()
        path = request.path
        filters = self._kwargs['filters']
        check_token = True
        for pattern, methes in filters:
            if pattern.match(path) and ((meth in methes) or ('all' in methes)):
                check_token = False
                break
        if check_token:
            try:
                token = request.query[self._kwargs['field_name']]
                # @todo do token check
            except Exception as exc:
                self._env.log.exception("token check failed %s" % str(exc))
                return HTTPError(401, 'invalid token')

        return callback(*args, **kwargs)
