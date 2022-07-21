import ast
import logging
import queue
import threading
import time
import traceback
import typing as t

from lesoon_common import LesoonFlask

from lesoon_cron.scheduler.xxl_job.code import ResponseCode
from lesoon_cron.scheduler.xxl_job.context import XxlJobContext
from lesoon_cron.scheduler.xxl_job.dataclass import CallbackParam
from lesoon_cron.scheduler.xxl_job.dataclass import Response
from lesoon_cron.scheduler.xxl_job.dataclass import TriggerParam
from lesoon_cron.scheduler.xxl_job.globals import XxlJobGlobals
from lesoon_cron.scheduler.xxl_job.helper import XxlJobHelper
from lesoon_cron.scheduler.xxl_job.log import XxlJobLogger
from lesoon_cron.scheduler.xxl_job.thread.base import InheritableThread
from lesoon_cron.scheduler.xxl_job.thread.base import StoppableThread


class RegistryThread(threading.Thread):
    beat_period: int = 30
    logger: logging.Logger = logging.getLogger('xxl-job-register')
    stop_flag: bool = False

    def __init__(self, app_name: str, registry_address: str):
        self.app_name = app_name
        self.registry_address = registry_address
        super().__init__(name='xxl-job-register')

    @classmethod
    def stop(cls):
        cls.stop_flag = True

    def run(self) -> None:
        while not self.stop_flag:
            try:
                self.logger.info('正在进行XXL-JOB执行器注册...')
                XxlJobHelper.client.registry(
                    register_key=self.app_name,
                    register_value=self.registry_address)
                self.logger.info('进行XXL-JOB执行器注册成功...')
            except Exception as e:
                self.logger.error(f'注册XXL-JOB执行器发生异常:{e}')
            finally:
                time.sleep(self.beat_period)

        self.logger.info('正在移除XXL-JOB已注册执行器...')
        XxlJobHelper.client.remove_registry(
            register_key=self.app_name, register_value=self.registry_address)
        self.logger.info('XXL-JOB已注册执行器移除成功...')


class CallbackThread(threading.Thread):
    callback_queue: queue.Queue = queue.Queue()
    callback_retry_period: int = 30
    stop_flag: bool = False
    logger: logging.Logger = logging.getLogger('xxl-job-callback')

    def __init__(self):
        super().__init__(name='xxl-job-callback')

    @classmethod
    def stop(cls):
        cls.stop_flag = True

    @classmethod
    def push_callback(cls, param: CallbackParam):
        cls.callback_queue.put(param)
        cls.logger.info(f'回调参数{param}已入队，等待回调.')

    def _trigger_callback(self):
        try:
            callback_param = self.callback_queue.get()
            if callback_param:
                params = [callback_param]
                while self.callback_queue.qsize():
                    params.append(self.callback_queue.get_nowait())
                XxlJobHelper.client.callback(params=params)
                self.logger.info(f'{params}调度任务结果回调完成')
        except Exception as e:
            self.logger.error(e)

    def run(self) -> None:
        while not self.stop_flag:
            self._trigger_callback()
        self._trigger_callback()


class JobThread(StoppableThread):
    logger: logging.Logger = logging.getLogger('xxl-job-trigger')

    def __init__(self, job_id: int, handle_func: t.Callable):
        self.job_id = job_id
        self.handle_func = handle_func
        self.running = False
        self.idle_times = 0
        self.log_id_set: t.Set[int] = set()
        self.stop_flag = False
        self.stop_reason = ''
        self.trigger_queue: 'queue.Queue[TriggerParam]' = queue.Queue()
        self.children: t.Set[InheritableThread] = set()
        super().__init__(name='xxl-job-trigger')

    def stop(self, reason: str = ''):
        self.stop_flag = True
        self.stop_reason = reason

    @property
    def is_running_or_has_queue(self):
        return self.running or self.trigger_queue.qsize()

    def push_trigger(self, trigger_param: TriggerParam) -> Response:
        if trigger_param.log_id in self.log_id_set:
            return Response(
                code=ResponseCode.Failure,
                msg=
                f'jobId[{trigger_param.job_id}]:logId[{trigger_param.log_id}]重复调度'
            )
        else:
            self.trigger_queue.put(trigger_param)
            self.log_id_set.add(trigger_param.log_id)
            self.logger.debug(f'调度任务：[{trigger_param}] 已进入队列.')
            return Response()

    @staticmethod
    def _extract_func_param(params) -> t.Tuple[tuple, dict]:
        func_args, func_kwargs = (), {}
        if params:
            params = ast.literal_eval(params)
            if isinstance(params, dict):
                func_kwargs = params
            elif isinstance(params, t.Sequence):
                func_args = tuple(params)  # type: ignore
            else:
                func_args = (params,)  # type: ignore
        return func_args, func_kwargs

    def run(self) -> None:
        """
            job线程入口.
            用于执行调度任务，包含以下操作:
            1. 不间断的从队列中获取调度参数.
            2. 处理调度参数.
                超时任务：另起子线程，超时终止线程.
                普通任务：直接运行对应处理函数.
            3. 调度完成后推送回调参数给回调线程.
            4. 如果当前线程被终止，则清理队列中剩余任务.

            """
        while not self.stop_flag:
            self.running = False
            self.idle_times += 1
            tp = None
            error_msg = ''
            try:
                try:
                    tp = self.trigger_queue.get(timeout=3)
                except queue.Empty:
                    continue
                if tp:
                    self.running = True
                    self.idle_times = 0
                    self.log_id_set.remove(tp.log_id)
                    args, kwargs = self._extract_func_param(tp.executor_params)
                    log_file = XxlJobLogger.get_log_file_path(
                        log_time=tp.log_date_time, log_id=tp.log_id)
                    # 新建线程xxl-job上下文在回调以及日志中使用
                    xxl_job_context = XxlJobContext(
                        job_id=tp.job_id,
                        job_args=args,
                        job_kwargs=kwargs,
                        job_file_path=log_file,
                        broadcast_index=tp.broadcast_index,
                        broadcast_total=tp.broadcast_total)
                    XxlJobContext.set(xxl_job_context)
                    XxlJobHelper.log(
                        f'<br>----------- xxl-job job execute start -----------<br>----------- Args:{args} Kwargs:{kwargs}'
                    )
                    if tp.executor_timeout:
                        # 超时任务另起子线程做处理
                        f: t.Optional[InheritableThread] = None
                        try:
                            f = InheritableThread(target=self.handle_func,
                                                  args=args,
                                                  kwargs=kwargs)
                            self.children.add(f)
                            f.start()
                            f.join(timeout=tp.executor_timeout)
                            if f.is_alive():
                                raise TimeoutError
                        except TimeoutError as e:
                            XxlJobHelper.log(
                                '<br>----------- xxl-job job execute timeout')
                            self.logger.info(e)
                            XxlJobHelper.handle_timeout(
                                f'job[{tp.job_id}]:log[{tp.log_id}]调度执行超时')
                        finally:
                            f.terminate()
                            self.children.remove(f)
                    else:
                        # 直接调用
                        self.handle_func(*args, **kwargs)

                    XxlJobHelper.log(
                        f'<br>----------- xxl-job job execute end(finish) -----------'
                        f'<br>----------- Result: code={XxlJobContext.get().response_code}, msg={XxlJobContext.get().response_msg}'
                    )
                elif self.idle_times > 30 and self.trigger_queue.empty():
                    # 超过30次轮询没有调度，则删除job线程
                    XxlJobGlobals.remove_job_thread(job_id=self.job_id,
                                                    reason='闲置线程自动清理')
            except InterruptedError:
                if tp:
                    XxlJobHelper.handle_failure(
                        f'job[{tp.job_id}]:log[{tp.log_id}]调度被终止')
            except Exception as e:
                self.logger.exception(e)
                if tp:
                    XxlJobHelper.handle_failure('任务执行异常')
                if self.stop_flag:
                    XxlJobHelper.log(
                        f'<br>----------- JobThread toStop, stop reason:{self.stop_reason}'
                    )
                    self.logger.info(
                        f'因为{self.stop_reason},job[{self.job_id}]线程停止工作...')
                XxlJobHelper.log(
                    f'<br>----------- JobThread Exception: + {traceback.format_exc()} + '
                    f'<br>----------- xxl-job job execute end(error) -----------'
                )
            finally:
                if tp:
                    CallbackThread.push_callback(
                        CallbackParam(log_id=tp.log_id,
                                      log_date_time=tp.log_date_time,
                                      code=XxlJobContext.get().response_code,
                                      msg=XxlJobContext.get().response_msg))

        # 工作线程停止时，清理余下调度队列
        while self.trigger_queue.qsize():
            if tp := self.trigger_queue.get_nowait():
                CallbackThread.push_callback(
                    CallbackParam(log_id=tp.log_id,
                                  log_date_time=tp.log_date_time,
                                  code=ResponseCode.Failure,
                                  msg=f'job[{self.job_id}]线程已停止工作, 清理任务队列'))

        self.logger.info(f'xxl-job job线程[{threading.current_thread()}]停止工作')
