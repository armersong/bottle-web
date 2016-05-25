# coding: utf-8
'''
作为第一个拦截器。否则容易出问题
'''
import re
from application import Interceptor
from bottle import request, HTTPResponse, HTTPError

class CrossDomainFilter(Interceptor):
    name = 'cross_domain_filter'
    def __init__(self, id, env, *args, **kwargs):
        filters = self._parse_filters(kwargs.get('filters'))
        kwargs['filters'] = filters
        super(CrossDomainFilter, self).__init__(id, env, *args, **kwargs)

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
        is_pass = True
        for pattern, methes in filters:
            if pattern.match(path) and ((meth in methes) or ('all' in methes)):
                is_pass = False
                break
        rv = callback(*args, **kwargs)
        if is_pass:
            if not isinstance(rv, HTTPResponse):
                rv = HTTPResponse(rv)
            rv.headers['Access-Control-Allow-Origin'] = '*'
            rv.headers['Access-Control-Allow-Methods'] = \
                                                        'GET,POST,PUT,OPTIONS'
            rv.headers['Access-Control-Allow-Headers'] = \
                                        'Referer, Accept, Origin, User-Agent'
        return rv