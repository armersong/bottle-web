# coding:utf-8
import json
import os

from bottle import TEMPLATE_PATH, Jinja2Template, request, abort
from service import Service

__all__ = [ "JinjiaTemplateService" ]

class JinjiaTemplateService(Service):
    def __init__(self, env, pathes, global_vars):
        super(JinjiaTemplateService, self).__init__(env)
        self._templateCls = Jinja2Template
        self._init_path(pathes)
        self._globals = json.loads(global_vars or '{}')
        self._templates = {}    # template cache: key: (id(lookup), tpl), value(template plugin instance)

    def _init_path(self, pathes):
        self._template_path = list(TEMPLATE_PATH)
        for path in (pathes or '').split(';'):
            path = path.strip()
            if path not in self._template_path:
                self._template_path.append(path)

    def render(self, template_file_name, *args, **kwargs):
        kw = dict(self._globals)
        ss = self._env.services["session_service"]
        kw.update({"env": self._env, "req": request, "session": self._env.services["session_service"].get_session(),
                   "base_url": os.path.dirname(request.fullpath),
                   "abs_base_url": os.path.dirname(request.url)})
        kw.update(kwargs)
        return self.get_template(template_file_name).render(*args, **kw)

    def __setitem__(self, key, value):
        self._globals[key] = value

    def get_template(self, tpl, lookup=None, settings =None):
        '''
        获取模板
        :param tpl: 需要渲染的源。可以带扩展名或不带
        :param lookup: 寻找路径
        :param settings: 
        :return: 
        '''
        lookup = lookup or self._template_path
        settings = settings or {}
        tplid = (id(lookup), tpl)
        if tplid not in self._templates:
            if isinstance(tpl, self._templateCls):
                self._templates[tplid] = tpl
                if settings: self._templates[tplid].prepare(**settings)
            elif "\n" in tpl or "{" in tpl or "%" in tpl or '$' in tpl:
                self._templates[tplid] = self._templateCls(source=tpl, lookup=lookup, **settings)
            else:
                self._templates[tplid] = self._templateCls(name=tpl, lookup=lookup, **settings)
        if not self._templates[tplid]:
            abort(500, 'Template (%s) not found' % tpl)
        return self._templates[tplid]