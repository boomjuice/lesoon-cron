import typing as t

from lesoon_client import BaseClient

from lesoon_cron.scheduler.xxl_job.dataclass import CallbackParam


class XxlJobClient(BaseClient):

    def __init__(self, *args, access_token: str = '', **kwargs):
        super().__init__(*args, **kwargs)
        self.headers = {'XXL-JOB-ACCESS-TOKEN': access_token}

    def _decode_result(self, res):
        """解析请求结果."""
        log_msg = {'url': res.url, 'data': res.content, 'msg': ''}
        try:
            res = res.json()
            log_msg['data'] = res
            if 'code' in res:
                if res['code'] == 200:
                    self.log.info(f'XXL-JOB执行器调用成功:{log_msg}')
                else:
                    log_msg['msg'] = res['msg']
                    self.log.error(f'XXL-JOB执行器调用失败:{log_msg}')
            else:
                raise
        except Exception as e:
            log_msg['msg'] = e
            self.log.error(f'XXL-JOB调用发生未知异常:{log_msg}')

        return res

    def registry(self,
                 register_key: str,
                 register_value: str,
                 register_group: str = 'EXECUTOR'):
        """
        注册执行器
        Args:
            register_key: 执行器地址
            register_value: 执行器名称
            register_group: 执行器分组

        """
        data = {
            'registryGroup': register_group,
            'registryKey': register_key,
            'registryValue': register_value
        }
        return self.POST('/api/registry', json=data, headers=self.headers)

    def remove_registry(self,
                        register_key: str,
                        register_value: str,
                        register_group: str = 'EXECUTOR'):
        """
        移除执行器
        Args:
            register_key: 执行器地址
            register_value: 执行器名称
            register_group: 执行器分组

        """
        data = {
            'registryGroup': register_group,
            'registryKey': register_key,
            'registryValue': register_value
        }
        return self.POST('/api/registryRemove', json=data, headers=self.headers)

    def callback(self, params: t.List[CallbackParam]):
        """
        任务执行完成回调
        Args:
            params: 参数列表

        """

        data = [{
            'logId': param.log_id,
            'logDateTim': param.log_date_time,
            'handleCode': param.code.value,
            'handleMsg': param.msg
        } for param in params]
        return self.POST('/api/callback', json=data, headers=self.headers)
