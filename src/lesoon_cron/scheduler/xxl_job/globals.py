import typing as t

from lesoon_common import LesoonFlask
if t.TYPE_CHECKING:
    from lesoon_cron.scheduler.xxl_job.handler import XxlJobHandlerMeta
    from lesoon_cron.scheduler.xxl_job.thread.work import JobThread


class XxlJobGlobals:
    """
    xxl-job 全局变量

    """

    # 执行器字典
    _register_handlers: t.Dict[str, 'XxlJobHandlerMeta'] = {}

    # 任务线程字典
    _register_job_threads: t.Dict[int, 'JobThread'] = {}

    @classmethod
    def remove_job_thread(cls, job_id: int,
                          reason: str) -> t.Optional['JobThread']:
        if jt := cls._register_job_threads.get(job_id):
            jt.stop(reason=reason)
            for child in jt.children:
                child.terminate()
            jt.terminate()
            del cls._register_job_threads[job_id]
            return jt
        return None

    @classmethod
    def get_job_thread(cls, job_id: int) -> t.Optional['JobThread']:
        return cls._register_job_threads.get(job_id)

    @classmethod
    def get_handler(cls, name: str):
        return cls._register_handlers.get(name)

    @classmethod
    def register_handler(cls, name: str, handler: 'XxlJobHandlerMeta'):
        cls._register_handlers[name] = handler

    @classmethod
    def register_job_thread(cls,
                            job_id: int,
                            handle_func: t.Callable,
                            reason: str = '清除旧任务线程') -> 'JobThread':
        from lesoon_cron.scheduler.xxl_job.thread.work import JobThread
        new_jt = JobThread(job_id=job_id, handle_func=handle_func)
        cls.remove_job_thread(job_id=job_id, reason=reason)
        cls._register_job_threads[job_id] = new_jt
        new_jt.start()
        return new_jt
