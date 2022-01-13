# type:ignore
import os


class Config:
    # flask
    SECRET_KEY = ('\x00\x8c\xfd\xed\x963\xac.\xcfl\xea\x80e'
                  '\xc7\xbbB\xde\xef-\xd3\xeb6\xf3\xa4')
    PROPAGATE_EXCEPTIONS = True

    # sqlalchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    SQLALCHEMY_DATABASE_URI = None

    # cache
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 60

    # debug-toolbar
    DEBUG_TB_PROFILER_ENABLED = False

    CRON = {
        'TYPE': 'XXL-JOB',
        'XXL-JOB': {
            'ADDRESS': 'http://127.0.0.1:10098/lesoon-schedule-api',
            'ACCESS_TOKEN': 'token123',
            'EXECUTOR': {
                'APP_NAME': 'lesoon-cron-examples',
            }
        }
    }
