import io
import logging
import os
from datetime import datetime

from lesoon_cron.scheduler.xxl_job.dataclass import LogResult


class XxlJobLogger:
    logger = logging.getLogger('xxl-job-file-log')
    log_dir_path = '/data/logs/xxl-job/handler'

    @classmethod
    def get_log_file_path(cls, log_time: int, log_id):
        if len(str(log_time)) > 10:
            # 时间戳包含毫秒
            log_time //= 1000
        log_date = datetime.fromtimestamp(log_time).strftime('%Y-%m-%d')
        log_file_dir = f'{cls.log_dir_path}@{log_date}'
        if not os.path.exists(log_file_dir):
            os.makedirs(log_file_dir, exist_ok=True)
        return os.path.join(log_file_dir, f'{log_id}.log')

    @classmethod
    def write(cls, log_file_path: str, msg: str):
        try:
            with open(log_file_path, mode='a+', encoding='utf-8') as f:
                f.write(msg + '\n')
        except Exception as e:
            cls.logger.exception(e)

    @classmethod
    def read(cls, log_file_path: str, from_line_num: int) -> LogResult:
        to_line_num = 0
        if not os.path.exists(log_file_path):
            return LogResult(from_line_num=from_line_num,
                             to_line_num=to_line_num,
                             log_content='日志文件不存在，读取日志失败！',
                             is_end=True)
        else:
            with open(log_file_path,
                      encoding='utf-8') as f, io.StringIO() as content:
                for line_no, line in enumerate(f, start=1):
                    to_line_num = line_no
                    if to_line_num >= from_line_num:
                        content.write(line)
                return LogResult(from_line_num=from_line_num,
                                 to_line_num=to_line_num,
                                 log_content=content.getvalue(),
                                 is_end=False)
