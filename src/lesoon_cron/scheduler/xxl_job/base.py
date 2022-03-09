import logging
import os
import random
import time
import typing as t

import filelock
from lesoon_common import LesoonFlask
from lesoon_restful.api import Api

from lesoon_cron.scheduler.xxl_job.client import XxlJobClient
from lesoon_cron.scheduler.xxl_job.helper import XxlJobHelper
from lesoon_cron.scheduler.xxl_job.log import XxlJobLogger
from lesoon_cron.scheduler.xxl_job.resource import XxlJobResource
from lesoon_cron.scheduler.xxl_job.thread.work import CallbackThread
from lesoon_cron.scheduler.xxl_job.thread.work import RegistryThread
from lesoon_cron.utils import get_local_ip


class XxlJob:
    resource_name: str = 'xxlJob'

    def __init__(self):
        self.beat_period = 5
        self.check_task_period = 1
        self.stop_registry = False
        self.registry_thread = None
        self.callback_thread = None
        self.logger = logging.getLogger('XXL-JOB')

    @staticmethod
    def _default_config() -> dict:
        return {
            'ADDRESS': '',
            'ACCESS_TOKEN': '',
            'BEAT_PERIOD': 30,
            'CALLBACK_RETRY_PERIOD': 30,
            'LOG_DIR_PATH': '/data/logs/xxl-job/handler',
            'EXECUTOR': {
                'APP_NAME': 'LESOON-CRON',
                'IP': f'http://{get_local_ip()}',
                'PORT': 5000,
            }
        }

    def registry(self, app: LesoonFlask, config: dict):
        """
        注册xxl-job执行器
        Args:
            app: lesoonFlask.app
            config: xxl-job配置

        """
        RegistryThread.beat_period = config['BEAT_PERIOD']

        EXECUTOR_CONFIG = config['EXECUTOR']
        for k, v in self._default_config()['EXECUTOR'].items():
            EXECUTOR_CONFIG.setdefault(k, v)
        registry_thread = RegistryThread(
            app_name=EXECUTOR_CONFIG['APP_NAME'],
            registry_address=
            f"{EXECUTOR_CONFIG['IP']}:{EXECUTOR_CONFIG['PORT']}/{self.resource_name}"
        )
        self.registry_thread = registry_thread
        registry_thread.start()

    def callback(self, app: LesoonFlask, config: dict):
        """
        注册xxl-job任务回调线程
        Args:
            app: lesoonFlask.app
            config: xxl-job配置

        """
        CallbackThread.callback_retry_period = config['CALLBACK_RETRY_PERIOD']
        callback_thread = CallbackThread()
        self.callback_thread = callback_thread
        callback_thread.start()

    def initialize(self, app: LesoonFlask):
        """
        初始化xxl-job调度所需的一切工作
        包括：1. 启动xxl-job执行器注册线程
             2. 启动xxl-job任务状态监听线程
             3. 注册xxl-job路由以供xxl-job调用
             4. app属性绑定以处理调用问题

        """
        config = app.config['CRON'].get('XXL-JOB', {})
        for k, v in self._default_config().items():
            config.setdefault(k, v)
        # 注册xxl-job执行器
        XxlJobHelper.client = XxlJobClient(base_url=config['ADDRESS'],
                                           access_token=config['ACCESS_TOKEN'])
        XxlJobLogger.log_dir_path = config['LOG_DIR_PATH']
        self.init_resource(app=app)

        try:
            with filelock.FileLock('xxl-job-register.lock', timeout=0):
                # 启动工作线程
                self.logger.info(f'XXL-JOB 当前以{self.beat_period}s进行心跳注册,'
                                 f' 以{self.check_task_period}s进行任务状态检测.')

                self.registry(app=app, config=config)
                self.logger.info('XXL-JOB心跳注册线程启动完成.')

                self.callback(app=app, config=config)
                self.logger.info('XXL-JOB任务状态检测线程启动完成.')
                if os.environ.get('gunicorn_flag', None):
                    time.sleep(random.randint(20, 30))
        except filelock.Timeout:
            app.logger.info('XXL-JOB注册进程已存在....')

    def init_resource(self, app: LesoonFlask):
        # 注册xxl-job路由
        api = Api(app=app)
        XxlJobResource.meta.name = self.resource_name
        api.add_resource(XxlJobResource)
