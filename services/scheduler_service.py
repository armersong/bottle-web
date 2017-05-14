# coding: utf-8
'''
任务调度服务
'''
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.base import JobLookupError

from service import Service

__all__ = ["SchedulerService"]

_cur_sched = None

class SchedulerServiceError(RuntimeError):
    pass

class SchedulerService(Service):
    def __init__(self, env, db, collection, worker_num):
        super(SchedulerService, self).__init__(env)
        self._db_name = db
        self._collection_name = collection
        self._worker_num = worker_num
        self._sched = None
        global _cur_sched
        _cur_sched = self

    def on_active(self):
        super(SchedulerService, self).on_active()
        self._init_scheduler()

    def on_inactive(self):
        if self._sched is not None:
            self._sched.shutdown()

    def _init_scheduler(self):
        jobstores = {
            'default': MongoDBJobStore(self._db_name, self._collection_name,
                                       host=self.mongodb_service.get_connection_info()),
        }
        executors = {
            'default': ThreadPoolExecutor(self._worker_num),
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 3
        }
        self._sched = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults)
        self._sched.start()

    def add_job(self, handler, dt, args=None, kwargs=None, job_id=None, replace_existing=True):
        '''
        增加单一任务。执行即消亡
        :param handler: 回调函数。需要考虑多线程问题
                        def handler(env, *args, **kwargs):pass
        :param dt: datetime
        :param job_id: string, 自定义id
        :param kwargs: handler的参数
        :return: job id
        '''
        args = args or []
        args.insert(0, handler)
        job = self._sched.add_job(dispatch_expire_job, 'date', run_date=dt, id=job_id, args=args, kwargs=kwargs,
                                  replace_existing=replace_existing)
        return job.id

    def add_interval_job(self, handler,
                         weeks=0, days=0, hours=0, minutes=0, seconds=0, args=None, kwargs=None, job_id=None,
                         replace_existing=True):
        '''
        增加定期任务
        :param handler: 回调函数。需要考虑多线程问题.
                        def handler(env, *args, **kwargs):pass
        :param weeks:
        :param days:
        :param hours:
        :param minutes:
        :param seconds:
        :param job_id: string, 自定义id
        :param kwargs: handler的参数
        :return: job id
        '''
        args = args or []
        args.insert(0, handler)
        job = self._sched.add_job(dispatch_expire_job, 'interval', weeks=weeks, days=days, hours=hours,
                                  minutes=minutes, seconds=seconds, id=job_id, args=args, kwargs=kwargs,
                                  replace_existing=replace_existing)
        return job.id

    def remove_job(self, job_id):
        try:
            self._sched.remove_job(job_id)
        except JobLookupError:
            pass

    def pause_job(self, job_id):
        self._sched.pause_job(job_id)

    def resume_job(self, job_id):
        self._sched.resume_job(job_id)

def dispatch_expire_job(func, *args, **kwargs):
    global _cur_sched
    env = _cur_sched.get_env()
    env.log.info('expired job, run %s' % func.__name__)
    func(env, *args, **kwargs)
