import logging
import typing as t

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
        split_address, url_prefix = config['ADDRESS'].rsplit('/', 1), ''

        if len(split_address) > 1:
            xxl_job_address = split_address[1]
            if xxl_job_address and ':' not in xxl_job_address:
                url_prefix = xxl_job_address

        XxlJobHelper.client = XxlJobClient(base_url=config['ADDRESS'],
                                           url_prefix=url_prefix,
                                           access_token=config['ACCESS_TOKEN'])

        # 启动工作线程
        self.logger.info(f'XXL-JOB 当前以{self.beat_period}s进行心跳注册,'
                         f' 以{self.check_task_period}s进行任务状态检测.')

        self.registry(app=app, config=config)
        self.logger.info('XXL-JOB心跳注册线程启动完成.')

        self.callback(app=app, config=config)
        self.logger.info('XXL-JOB任务状态检测线程启动完成.')

        XxlJobLogger.log_dir_path = config['LOG_DIR_PATH']
        self.init_resource(app=app)

    def init_resource(self, app: LesoonFlask):
        # 注册xxl-job路由
        api = Api(app=app)
        XxlJobResource.meta.name = self.resource_name
        api.add_resource(XxlJobResource)
