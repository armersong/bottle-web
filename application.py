# coding: utf-8
"""
    插件:
            参考bottle的插件

    拦截器:
            特别的bottle插件. 串接在请求处理练中。
            不同与一般的bottle插件。任何时候都会执行

    服务:
            class Service(object):
                def __init__(self, appenv, *args, **kwargs):
                    pass

                def on_active(self):
                    pass

                def on_inactive(self):
                    pass

            规则:
                1. on_active: 只会调用一次，尽量在此调用初始化过程。
                               否则容易发生依赖问题
                2. on_inactive: 服务停止时调用
                3. 所有依赖的服务通过self.service_id访问

    控制器:
            有两种模式:
            class Test(Action):
                def index(self， plugin_name):
                    pass

                def on_active(self):
                    pass

                def on_inactive(self):
                    pass
            或者:

            def fuc( appenv, plugin_name, ...):
                pass

            规则: 使用类的方式。依赖的服务可以通过self.service_id获得

    env: 内建插件，保存了全局信息
            1. app : Bottle实例
            2. cfg : 特别的配置信息
            3. log : 日志实例
            4. services: 所有服务列表。通过services.service_id获取具体服务实例

"""
import logging
import logging.config
import os
import sys
import types

from bottle import Bottle, TEMPLATE_PATH, install, PluginError, run
from importlib import import_module
from xml.etree.ElementTree import parse, tostring

__all__ = ["Application", "ImmutableObject", "load_logger_from_config",
           "Service", "Action", "Interceptor",
           "get_service", "get_app", "get_log",
           ]

DEFAULE_CFG_FILENAME = "app-config.xml"

def load_logger_from_config(config="logging.conf"):
    """Read logging config and return default logger"""
    logging.config.fileConfig(config)
    return logging.getLogger()

class ApplicationError(RuntimeError):
    """Application basic exception class"""
    pass

class ServiceNotFoundError(ApplicationError):
    """ """
    pass

class PluginNotFoundError(ApplicationError):
    """ """
    pass

class Application(object):
    """Bottle application load and run framework"""
    def __init__(self, logger=None, cfg=None, app_config=None):
        self._env = ImmutableObject()
        self._env.app = Bottle()
        self._env.log = logger or load_logger_from_config()
        self._env.cfg = cfg
        self._env.services = ImmutableObject()
        self._server_listen = ("localhost", 8000)
        self._actions = []     # ((action_func_name, actionFunc),)
        self._action_classes = {}     # ((class_name, inst),)
        self._plugins = []     # ((plugin_id, pluginInstance),)
        self._services = []    # ((service_id, serviceInstance))
        # self._interceptors = [AppEnvPlugin(self._env)]
        self._interceptors = []
        self._init_internal_interceptors()

        config = app_config or os.path.join(os.getcwd(), DEFAULE_CFG_FILENAME)
        self._load_cfg(config)
        self._is_setup = False

    def get_wsgi(self):
        if not self._is_setup:
            self._setup()
        return self._env.app

    def _init_internal_interceptors(self):
        self._interceptors.append( AppEnv(AppEnv.name, self._env))
        for plugin in self._interceptors:
            install(plugin)

    def _load_cfg(self, config):
        """load config file and init"""
        root = parse(config).getroot()
        self._add_lib_path(root.find('libpathes'))
        handlers = ( \
            ('services', self._parse_services, ('service',)), \
            ('interceptors', self._parse_interceptors, ('interceptor',)), \
            ('plugins', self._parse_plugins, ('plugin',)), \
            ('actions', self._parse_actions, ('action',)))
        for key, handler, args in handlers:
            try:
                node = root.find(key)
                if node is not None:
                    handler(node, *args)
            except Exception as exc:
                self._env.log.exception(unicode(exc))

        self._parse_server(root.find("server"))

    def _add_lib_path(self, xml_node):
        for node in xml_node.getchildren():
            path = os.path.abspath(node.text)
            if path not in sys.path:
                self._env.log.info("append path %s" % path)
                sys.path.append(path)

    def _parse_plugins(self, xml_node, node_name):
        """parse plugins node and init plugins"""
        for node in xml_node.getchildren():
            try:
                if node.tag != node_name:
                    continue
                plugin_id = node.attrib["id"].strip()
                # class
                plugin_cls_name = node.attrib["class"].strip()
                plugin = self._get_list_item_by_key(self._plugins, plugin_id)
                if plugin is  not None:
                    continue
                plugin_cls = self._get_object(plugin_cls_name)
                # params
                params = dict(keyword=plugin_id)
                _,_params = self._parse_params(node)
                params.update(_params)
                # new instance
                plugin = plugin_cls(**params)
                self._plugins.append((plugin_id, plugin))
                self._env.log.info("plugin %s -> %s" % (plugin_id, plugin_cls))
            except Exception as exc:
                self._env.log.exception("load plugin item %s failed:%s" % \
                                            (tostring(node), unicode(exc)))

    def _parse_interceptors(self, xml_node, node_name):
        """parse plugins node and init plugins"""
        for node in xml_node.getchildren():
            try:
                if node.tag != node_name:
                    continue
                plugin_id = node.attrib["id"].strip()
                # class
                plugin_cls_name = node.attrib["class"].strip()
                plugin = self._get_list_item_by_key(self._plugins, plugin_id)
                if plugin is  not None:
                    continue
                plugin_cls = self._get_object(plugin_cls_name)
                # params
                _,params = self._parse_params(node)
                # depend services
                dep_services = []
                dep_services_node = node.find("dep-services")
                if dep_services_node is not None:
                    dep_services = self._check_dep_services(dep_services_node)
                # new instance
                plugin = plugin_cls(plugin_id, self._env, **params)
                # put service
                for svr_id, svr_inst in dep_services:
                    setattr(plugin, svr_id, svr_inst)
                self._plugins.append((plugin_id, plugin))
                self._interceptors.append(plugin)
                self._env.log.info("interceptor %s -> %s" % (plugin_id, \
                                                             plugin_cls))
            except Exception as exc:
                self._env.log.exception("load interceptor item %s failed:%s" % \
                                            (tostring(node), unicode(exc)))

    def _parse_actions(self, xml_node, node_name):
        """parse actions config"""
        app = self._env.app

        for node in xml_node.getchildren():
            try:
                if node.tag != node_name:
                    continue
                path = node.attrib["path"]
                func_name = node.attrib["func"].strip()
                cls_name = node.attrib.get("class", "").strip()

                full_func_name = func_name
                if cls_name != "":
                    full_func_name = cls_name + "." + func_name
                handler = self._get_list_item_by_key(self._actions, \
                                                     full_func_name)
                cls_inst = None
                if handler is None:
                    if cls_name != "":
                        cls_inst = self._get_class_instance(cls_name)
                        handler = getattr(cls_inst, func_name)
                    else:
                        handler = self._get_object(full_func_name)
                    self._actions.append((full_func_name, handler))
                # plugins
                plugins = list(self._interceptors)
                plugins_node = node.find("dep-plugins")
                if plugins_node is not None:
                    plugins.extend(self._parse_action_plugins(plugins_node))
                # depend services
                dep_services_node = node.find("dep-services")
                if dep_services_node is not None:
                    services = self._check_dep_services(dep_services_node)
                    # put service
                    if type(handler) == types.MethodType:
                        for svr_id, svr_inst in services:
                            setattr(cls_inst, svr_id, svr_inst)

                # route map
                app.route(path, \
                    node.attrib["method"].strip().upper().split(";"), \
                    handler, apply=plugins)
                self._env.log.info("route %s -> %s" % (path, full_func_name))
            except Exception as exc:
                self._env.log.exception("load action item %s failed:%s" % \
                                            (tostring(node), unicode(exc)))

    def _parse_action_plugins(self, xml_node):
        """parse aciont plugins config"""
        plugins = []
        dep_plugins = xml_node.text or ""
        for plugin_id in dep_plugins.strip().split(","):
            if plugin_id == "":
                continue
            plugin = self._get_list_item_by_key(self._plugins, plugin_id)
            if plugin is None:
                raise PluginNotFoundError("plugin %s not found" % plugin_id)
            plugins.append(plugin)
        return plugins

    def _check_dep_services(self, xml_node):
        """check if dependent service exists

        throw ServiceNotFoundError if service is not found

        """
        services = []
        dep_services = xml_node.text or ""
        for service_id in dep_services.strip().split(","):
            if service_id == "":
                continue
            service_id = service_id.strip()
            inst = self._get_list_item_by_key(self._services, service_id)
            if inst is None:
                raise ServiceNotFoundError("service %s not found" % service_id)
            services.append((service_id, inst))
        return services

    def _parse_services(self, xml_node, node_name):
        """parse services config"""
        for node in xml_node.getchildren():
            try:
                if node.tag != node_name:
                    continue
                service_id = node.attrib["id"].strip()
                # class
                service_cls_name = node.attrib["class"].strip()
                service = self._get_list_item_by_key(self._services, \
                                                     service_id)
                if service is  not None:
                    continue
                service_cls = self._get_object(service_cls_name)
                # depend services
                dep_services_node = node.find("dep-services")
                dep_services = []
                if dep_services_node is not None:
                    dep_services = self._check_dep_services(dep_services_node)
                # params
                params = dict(env=self._env)
                _,_params = self._parse_params(node)
                params.update(_params)
                # new instance
                service = service_cls(**params)
                for svr_id, svr_inst in dep_services:
                    setattr(service, svr_id, svr_inst)
                self._services.append((service_id, service))
                self._env.services[service_id] = service
                self._env.log.info("service %s -> %s" \
                                    % (service_id, service_cls))
            except Exception as exc:
                self._env.log.exception("load service item %s failed:%s" % \
                                            (tostring(node), unicode(exc)))

    def _parse_server(self, xml_node):
        self._server_listen = xml_node.find("listen").text.strip().split(":")

    def _parse_params(self, node, params_name='params', param_name='param'):
        args = []
        kwargs = {}
        params_node = node.find(params_name)
        if params_node is None:
            return args,kwargs
        for param_node in params_node.getchildren():
            if param_node.tag != param_name \
               or param_node.attrib["name"] == "":
                continue
            key_type = param_node.attrib["type"].strip().lower()
            key = param_node.attrib["name"].strip()
            value = param_node.text.strip()
            if key_type == "int":
                value = int(value)
            elif key_type == "float":
                value = float(value)
            elif key_type == "subnode":
                value = param_node
            kwargs[key] = value
            args.append(value)
        return args,kwargs

    def _get_class_instance(self, cls_name, *args, **kwargs):
        inst = self._action_classes.get(cls_name)
        if inst is None:
            cls = self._get_object(cls_name)
            inst = cls(self._env, *args, **kwargs)
            self._action_classes[cls_name] = inst
        return inst

    def run(self, run_server_func=None):
        """start application service"""
        if not self._is_setup:
            self._setup()
            self._is_setup = True
        run_server = run_server_func or self._run_server
        run_server()
        self._teardown()

    def _run_server(self):
        """default run_server function, use default http server"""
        self._env.log.info("run server...")
        run(self._env.app, reloader=True,\
            host=self._server_listen[0], port=self._server_listen[1])
        self._env.log.info("server quiting...")

    def _setup(self):
        """install plugins and active services"""
        # active services
        for service_id, service in self._services:
            try:
                self._env.log.info("active service %s" % service_id)
                on_active = getattr(service, "on_active")
                on_active()
            except AttributeError:
                pass
            except Exception as exc:
                self._env.log.exception("active service %s failed:%s" % \
                                            (service_id, unicode(exc)))

        # install plugins
        for plugin_id, plugin in self._plugins:
            try:
                self._env.log.info("install plugin %s" % plugin_id)
                install(plugin)
            except Exception as exc:
                self._env.log.exception("load plugin %s failed:%s" % \
                                            (plugin_id, unicode(exc)))


        # actions
        for cls_name, cls_inst in self._action_classes.items():
            try:
                self._env.log.info("active action class %s" % cls_name)
                on_active = getattr(cls_inst, "on_active")
                on_active()
            except AttributeError:
                pass
            except Exception as exc:
                self._env.log.exception("active action %s failed:%s" % \
                                            (cls_name, unicode(exc)))

    def _teardown(self):
        """disactive services"""
        # actions
        for cls_name, cls_inst in self._action_classes.items():
            try:
                self._env.log.info("disactive action class %s" % cls_name)
                on_inactive = getattr(cls_inst, "on_active")
                on_inactive()
            except AttributeError:
                pass
            except Exception as exc:
                self._env.log.exception("disactive action %s failed:%s" % \
                                            (cls_name, unicode(exc)))

        # active services
        for service_id, service in self._services:
            try:
                self._env.log.info("disactive service %s" % service_id)
                on_inactive = getattr(service, "on_inactive")
                on_inactive()
            except AttributeError:
                pass
            except Exception as exc:
                self._env.log.exception("disactive service %s failed:%s" % \
                                            (service_id, unicode(exc)))

    @classmethod
    def _get_object(cls, obj_name):
        """according to object name, import object type"""
        names = obj_name.split(".")
        mod = import_module('.'.join(names[:-1]))
        obj = getattr(mod, names[-1])
        return obj

    @classmethod
    def _get_list_item_by_key(cls, array, key):
        """get list item by key since item is a tuple(key,value)"""
        for key_, value in array:
            if key == key_:
                return value
        return None

class ImmutableObject(object):
    """all attributes are readonly or append once"""
    def __init__(self):
        self._meta = dict()

    def __setattr__(self, key, value):
        if key != "_meta":
            meta = object.__getattribute__(self, "_meta")
            if meta.has_key(key):
                raise RuntimeError("Env attribute readonly")
            meta[key] = value
            return
        object.__setattr__(self, key, value)

    def __getattr__(self, item):
        meta = object.__getattribute__(self, "_meta")
        return meta[item]

    def __delattr__(self, item):
        raise RuntimeError("Env attribute readonly")

    def get_attribute_names(self):
        """get all attributes"""
        return self._meta.keys()

    def __getitem__(self, item):
        return self._meta[item]

    def __setitem__(self, key, value):
        self.__setattr__(key, value)

###############################################################################
# 服务基类
###############################################################################
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

###############################################################################
# 拦截器基类
###############################################################################
class Interceptor(object):
    name = 'interceptor'
    api = 2

    def __init__(self, id, env, *args, **kwargs):
        self.keyword = id
        self._env = env
        self._args = args
        self._kwargs = kwargs

    def setup(self, app):
        for other in app.plugins:
            try:
                if other.keyword == self.keyword:
                    raise PluginError("Found another redis plugin with "\
                            "conflicting settings (non-unique keyword).")
            except AttributeError:
                pass

    def apply(self, callback, route):
        def wrapper(*args, **kwargs):
            config = route.config
            # conf = config.get(self.keyword) or {}
            func_args = route.get_callback_args()
            return self._handle(callback, config, func_args, \
                                *args, **kwargs)
        return wrapper

    def _handle(self, callback, conf, func_args, *args, **kwargs):
        '''
        :param callback:
        :param conf: callback config info
        :param func_args: callback origin args
        :param args:
        :param kwargs:
        :return:
        '''
        raise NotImplementedError

# 内嵌环境插件,提供整体环境信息
class AppEnv(Interceptor):
    name = 'appenv'

    def __init__(self, id, env):
        super(AppEnv, self).__init__(id, env)

    def _handle(self, callback, conf, func_args, *args, **kwargs):
        keyword = conf.get('keyword', self.keyword)
        if keyword in func_args:
            kwargs[self.keyword] = self._env
        return callback(*args, **kwargs)

###############################################################################
# 控制器基类
###############################################################################
class Action(object):
    def __init__(self, env):
        self._env = env

###############################################################################
# 工具
###############################################################################
def get_service(env, name):
    return env.services[name]

def get_app(env):
    return env.app

def get_log(env):
    return env.log