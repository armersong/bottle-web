# coding:utf-8
'''
事件分发服务。
@todo 增加外部的发布订阅功能(redis)
      增加事件分发配置，控制内部和外部事件路由
'''
from blinker import Signal, ANY
from service import Service

__all__ = [ "EventService" ]

class EventService(Service):
    def __init__(self, env):
        """event service"""
        super(EventService, self).__init__(env)
        self._channel = Signal('event_channel')

    def subscribe(self, func, event_type=None ):
        '''
        :param func: def func(event_type, **kwarg):
                        pass
        :param event_filter: option
        :return:
        '''
        # sender = event_type or ANY
        # weak = True
        # if isinstance(event_type, basestring):
        #     weak = False
        # self._channel.connect(func, sender, weak)
        sender = event_type or ANY
        self._channel.connect(func, sender)

    def unsubscribe(self, func):
        self._channel.disconnect(func)

    def publish(self, event_type, **kwarg):
        self._channel.send(event_type, **kwarg)
