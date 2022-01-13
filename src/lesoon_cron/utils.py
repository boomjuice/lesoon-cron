import socket
from datetime import datetime
from functools import wraps

from flask.ctx import AppContext
from lesoon_common.dataclass.user import TokenUser
from lesoon_common.globals import _app_ctx_stack
from lesoon_common.model.alchemy.base import BaseModel
from lesoon_common.wrappers import LesoonQuery
from sqlalchemy import event
from sqlalchemy.orm.query import BulkUpdate


def context_inject(context: AppContext):
    _context = context

    def wrapper(fn):

        @wraps(fn)
        def decorator(*args, **kwargs):
            with _context:
                # 注入线程用户防止model写入报错
                _app_ctx_stack.top.jwt_user = TokenUser.system_default()
                ret = fn(*args, **kwargs)

            return ret

        return decorator

    return wrapper


def get_local_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Use Google Public DNS server to determine own IP
        sock.connect(('8.8.8.8', 80))

        return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except socket.gaierror:
            return '127.0.0.1'
    finally:
        sock.close()
