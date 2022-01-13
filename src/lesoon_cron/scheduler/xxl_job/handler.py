import typing as t

from lesoon_cron.scheduler.xxl_job.globals import XxlJobGlobals


class XxlJobHandlerMeta(type):

    def __new__(mcs, name: str, bases: t.Tuple[t.Type, ...], members: dict):
        new_class = super().__new__(mcs, name, bases, members)
        XxlJobGlobals.register_handler(name, new_class)
        return new_class


class XxlJobHandler(metaclass=XxlJobHandlerMeta):
    pass
