from lesoon_common.dataclass.base import BaseDataClass
from lesoon_common.dataclass.base import dataclass
from lesoon_common.dataclass.base import field
from marshmallow import post_load

from lesoon_cron.scheduler.xxl_job.code import ResponseCode
from lesoon_cron.scheduler.xxl_job.code import XxlJobStrategyCode


@dataclass
class TriggerParam(BaseDataClass):
    # 任务id
    job_id: int
    # 任务处理器
    executor_handler: str
    # 任务参数
    executor_params: str
    # 任务阻塞策略
    executor_block_strategy: XxlJobStrategyCode = field(metadata=dict(
        by_value=True))
    # 任务超时时间
    executor_timeout: int
    # 日志id
    log_id: int
    # 日志开始时间
    log_date_time: int
    # glue脚本类型
    glue_type: str
    # glue脚本
    glue_source: str
    # 分片索引号
    broadcast_index: int
    # 分片总数
    broadcast_total: int

    @post_load
    def load_strategy(self, data, **kwargs):
        data['executor_block_strategy'] = XxlJobStrategyCode(
            data['executor_block_strategy'])
        return data


@dataclass
class CallbackParam(BaseDataClass):
    log_id: int
    log_date_time: int
    code: ResponseCode = field(default=ResponseCode.Success,
                               metadata=dict(by_value=True))
    msg: str = ''


@dataclass
class LogResult(BaseDataClass):
    from_line_num: int
    to_line_num: int
    log_content: str
    is_end: bool


@dataclass
class Response(BaseDataClass):
    code: ResponseCode = field(default=ResponseCode.Success,
                               metadata=dict(by_value=True))
    msg: str = ''
