import socket
from functools import wraps

from flask.ctx import AppContext
from lesoon_common.dataclass.user import TokenUser
from lesoon_common.utils.jwt import set_current_user


def context_inject(context: AppContext):
    _context = context

    def wrapper(fn):

        @wraps(fn)
        def decorator(*args, **kwargs):
            with _context:
                # 注入线程用户防止model写入报错
                set_current_user(TokenUser.new())
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
