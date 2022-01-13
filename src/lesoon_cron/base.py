import typing as t

from lesoon_common import LesoonFlask


class LesoonCron:

    def __init__(self, app: t.Optional[LesoonFlask] = None):
        if app:
            self.init_app(app)

    @staticmethod
    def _default_config() -> dict:
        return {'TYPE': 'XXL-JOB', 'ENABLE': True, 'XXL-JOB': {}}

    def init_app(self, app: LesoonFlask):
        config = app.config.get('CRON', {})
        for k, v in self._default_config().items():
            config.setdefault(k, v)
        if not config['ENABLE']:
            return
        if (cron_type := config['TYPE']) == 'XXL-JOB':
            from lesoon_cron.scheduler import XxlJob
            app.xxl_job = XxlJob()
            app.xxl_job.initialize(app=app)
        else:
            raise ValueError(f'暂不支持此调度平台:{cron_type}')
