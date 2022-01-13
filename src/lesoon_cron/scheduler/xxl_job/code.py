import enum


class XxlJobStrategyCode(enum.Enum):
    # 串行执行
    SerialExecution = 'SERIAL_EXECUTION'
    # 丢弃后续调度
    DiscardLater = 'DISCARD_LATER'
    # 覆盖前续调度
    CoverEarly = 'COVER_EARLY'


class ResponseCode(enum.Enum):
    # 成功
    Success = 200
    # 失败
    Failure = 500
    # 超时
    Timeout = 502
    # 异常
    Error = 504
