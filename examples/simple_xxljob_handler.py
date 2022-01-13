import logging
import random
import time

from lesoon_common import LesoonFlask

from lesoon_cron import LesoonCron
from lesoon_cron.scheduler.xxl_job import XxlJobHandler
from lesoon_cron.scheduler.xxl_job import XxlJobHelper

app = LesoonFlask(__name__, extra_extensions={'cron': LesoonCron()})
app.logger.setLevel(logging.DEBUG)


class SimpleHandler(XxlJobHandler):

    def test(self, a: str, b: str = '11'):
        print(f'进行调度,调度参数:{a=}{b=}')
        XxlJobHelper.log(f'进行调度,调度参数:{a=} {b=}')
        time.sleep(random.randint(5, 20))
        XxlJobHelper.log('调度中...')
        time.sleep(1)
        XxlJobHelper.log('调度完成')


if __name__ == '__main__':
    import pprint

    pprint.pprint(sorted(app.url_map.iter_rules(), key=lambda x: x.rule))
    app.run(host='0.0.0.0')
