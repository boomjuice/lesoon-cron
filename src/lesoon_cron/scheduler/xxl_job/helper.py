import io
import logging
import typing as t
from datetime import datetime

from lesoon_cron.scheduler.xxl_job.client import XxlJobClient
from lesoon_cron.scheduler.xxl_job.code import ResponseCode
from lesoon_cron.scheduler.xxl_job.context import XxlJobContext
from lesoon_cron.scheduler.xxl_job.log import XxlJobLogger

logger: logging.Logger = logging.getLogger('xxl-job-helper')


class XxlJobHelper:
    client: t.Optional[XxlJobClient] = None

    @staticmethod
    def log(msg: str):
        logging.info(msg)
        xxl_job_contex = XxlJobContext.get()
        if not xxl_job_contex:
            return False
        if file_path := xxl_job_contex.job_file_path:
            with io.StringIO() as s:
                s.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' ')
                s.write(msg)
                XxlJobLogger.write(log_file_path=file_path, msg=s.getvalue())
            return True
        else:
            return False

    @staticmethod
    def handle_result(code: ResponseCode, msg: str = '') -> bool:
        if context := XxlJobContext.get():
            context.response_code = code
            context.response_msg = msg
            return True
        else:
            return False

    @staticmethod
    def handle_success(msg: str = ''):
        return XxlJobHelper.handle_result(code=ResponseCode.Success, msg=msg)

    @staticmethod
    def handle_failure(msg: str = ''):
        return XxlJobHelper.handle_result(code=ResponseCode.Failure, msg=msg)

    @staticmethod
    def handle_timeout(msg: str = ''):
        return XxlJobHelper.handle_result(code=ResponseCode.Timeout, msg=msg)
