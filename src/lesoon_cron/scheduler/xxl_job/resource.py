import typing as t

from lesoon_common import current_app
from lesoon_common.model import CamelSchema
from lesoon_common.model import fields
from lesoon_restful import use_args
from lesoon_restful.resource import Resource
from lesoon_restful.routes import Route

from lesoon_cron.scheduler.xxl_job.code import ResponseCode
from lesoon_cron.scheduler.xxl_job.code import XxlJobStrategyCode
from lesoon_cron.scheduler.xxl_job.dataclass import Response
from lesoon_cron.scheduler.xxl_job.dataclass import TriggerParam
from lesoon_cron.scheduler.xxl_job.globals import XxlJobGlobals
from lesoon_cron.scheduler.xxl_job.log import XxlJobLogger
from lesoon_cron.utils import context_inject


class JobSchema(CamelSchema):
    job_id = fields.Int()


class XxlJobLogSchema(CamelSchema):
    log_id = fields.Int()
    log_date_time = fields.Int(data_key='logDateTim')
    from_line_num = fields.Int()


class XxlJobResource(Resource):
    job_args = {'job_id': fields.Int(data_key='jobId')}

    @Route.POST('/beat', rel='心跳检测')
    def beat_check(self):
        return Response().json()

    @Route.POST('/idleBeat', rel='忙碌检测')
    @use_args(job_args, as_kwargs=True)
    def idle_beat_check(self, job_id: int):
        code, msg = ResponseCode.Success, ''
        if jt := XxlJobGlobals.get_job_thread(job_id):
            if not jt.is_running_or_has_queue:
                code, msg = ResponseCode.Failure, 'job调度线程运行中...'
        return Response(code=code, msg=msg).json()

    @Route.POST('/run', rel='运行任务')
    @use_args(TriggerParam.Schema)
    def run(self, trigger_param: TriggerParam):
        tp = trigger_param
        jt = XxlJobGlobals.get_job_thread(job_id=tp.job_id)
        remove_reason = ''

        if jt:
            if tp.executor_block_strategy == XxlJobStrategyCode.DiscardLater:
                if jt.is_running_or_has_queue:
                    return Response(
                        code=ResponseCode.Failure,
                        msg=f'任务已存在调度进行中,当前策略:{tp.executor_block_strategy}'
                    ).json()
            elif tp.executor_block_strategy == XxlJobStrategyCode.CoverEarly:
                remove_reason = f'根据策略:{tp.executor_block_strategy}停止旧线程'
                jt = None

        if not jt:
            # 获取处理器类以及处理方法
            cls_name, handle_func_name = tp.executor_handler.rsplit('.', 1)
            handler_cls = XxlJobGlobals.get_handler(cls_name)
            if not handler_cls:
                return Response(code=ResponseCode.Error,
                                msg=f'无法找到对应的处理器类:{cls_name}').json()
            handler = handler_cls()
            if not hasattr(handler, handle_func_name):
                return Response(
                    code=ResponseCode.Error,
                    msg=f'{cls_name}处理器类没有该处理函数{handle_func_name}').json()
            handle_func = getattr(handler, handle_func_name)
            handle_func = context_inject(current_app.app_context())(handle_func)
            jt = XxlJobGlobals.register_job_thread(job_id=tp.job_id,
                                                   handle_func=handle_func,
                                                   reason=remove_reason)
        return jt.push_trigger(trigger_param=tp).json()

    @Route.POST('/kill', rel='终止任务')
    @use_args(job_args, as_kwargs=True)
    def kill(self, job_id: int):
        XxlJobGlobals.remove_job_thread(job_id=job_id, reason='调度中心触发终止任务')
        return Response().json()

    @Route.POST('/log', rel='查看执行日志')
    @use_args(XxlJobLogSchema, as_kwargs=True)
    def log(self, log_id: int, log_date_time: int, from_line_num: int):
        log_file_path = XxlJobLogger.get_log_file_path(log_time=log_date_time,
                                                       log_id=log_id)
        log_result = XxlJobLogger.read(log_file_path=log_file_path,
                                       from_line_num=from_line_num).json()
        response = Response().json()
        response['content'] = log_result
        return response
