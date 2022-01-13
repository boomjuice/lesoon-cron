import typing as t

from lesoon_cron.scheduler.xxl_job.code import ResponseCode
from lesoon_cron.scheduler.xxl_job.thread.base import InheritableLocal

local = InheritableLocal()


class XxlJobContext:
    """
    xxl-job 线程上下文管理.

    Attributes:
        job_id: 任务id
        job_args: 任务位置参数
        job_kwargs: 任务命名参数
        job_file_path: 任务日志文件名
        broadcast_index: 分片索引号
        broadcast_total: 分片索引总计

    """

    @staticmethod
    def set(context: 'XxlJobContext'):
        local.xxl_job_context = context

    @staticmethod
    def get() -> t.Optional['XxlJobContext']:
        if hasattr(local, 'xxl_job_context'):
            return local.xxl_job_context
        else:
            return None

    def __init__(self, job_id: int, job_args: t.Sequence, job_kwargs: dict,
                 job_file_path: str, broadcast_index: int,
                 broadcast_total: int):
        self.job_id = job_id
        self.job_args = job_args
        self.job_kwargs = job_kwargs
        self.job_file_path = job_file_path
        self.broadcast_index = broadcast_index
        self.broadcast_total = broadcast_total
        self.response_code = ResponseCode.Success
        self.response_msg = ''
