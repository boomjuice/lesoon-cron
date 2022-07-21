import copy
import ctypes
import inspect
import threading
from _threading_local import local


class StoppableThread(threading.Thread):
    """
    可中断线程.

    源码地址：https://blog.finxter.com/how-to-kill-a-thread-in-python/
    """

    @staticmethod
    def _async_raise(tid, exc_type):
        """raises the exception, performs cleanup if needed"""
        if not inspect.isclass(exc_type):
            raise TypeError('Only types can be raised (not instances)')
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_long(tid), ctypes.py_object(exc_type))
        if res == 0:
            raise ValueError('invalid thread id')
        elif res != 1:
            # """if it returns a number greater than one, you're in trouble,
            # and you should call it again with exc=NULL to revert the effect"""
            ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, 0)
            raise SystemError('PyThreadState_SetAsyncExc failed')

    def _get_my_tid(self):
        """determines this (self's) thread id"""

        # do we have it cached?
        if hasattr(self, '_thread_id'):
            return self._thread_id

        # no, look for it in the _active dict
        for tid, t in threading._active.items():  # noqa
            if t is self:
                self._thread_id = tid
                return tid

        raise AssertionError("could not determine the thread's id")

    def raise_exc(self, exc_type):
        """raises the given exception type in the context of this thread"""
        self._async_raise(self._get_my_tid(), exc_type)

    def terminate(self):
        """raises SystemExit in the context of the given thread, which should
        cause the thread to exit silently (unless caught)"""
        if self.is_alive():
            self.raise_exc(SystemExit)


class InheritableThread(StoppableThread):
    """
    用于创建可继承父线程变量的线程.
    """

    def __init__(self,
                 group=None,
                 target=None,
                 name=None,
                 args=(),
                 kwargs=None,
                 *,
                 daemon=None):
        super().__init__(group=group,
                         target=target,
                         name=name,
                         args=args,
                         kwargs=kwargs,
                         daemon=daemon)
        self.parent = threading.current_thread()
        self.exc = None
        self.ret = None

    def run(self):
        """
        为捕获线程运行中异常重写.
        """
        try:
            super().run()
        except Exception as e:
            self.exc = e

    def join(self, timeout=None):
        super().join(timeout)
        if self.exc:
            raise self.exc
        return self.ret


class InheritableLocal(local):
    """
    如果需要父线程的变量，请使用InheritableThread创建线程.
    """

    def copy_parent_attribute(self):
        parent = threading.current_thread().parent  # noqa
        parent_local = self._local__impl.dicts.get(id(parent))
        if parent_local is not None:
            parent_dicts = parent_local[1]
            for key, value in parent_dicts.items():
                self.__setattr__(key, copy.deepcopy(value))

    def __new__(cls, *args, **kwargs):
        self = local.__new__(cls, *args, **kwargs)  # noqa
        try:
            self.copy_parent_attribute()
        except AttributeError:
            # 不是由InheritableThread创建的线程不需要拷贝属性
            pass
        return self

    def __getattribute__(self, item):
        try:
            return local.__getattribute__(self, item)
        except AttributeError as e:
            try:
                self.copy_parent_attribute()
                return local.__getattribute__(self, item)
            except AttributeError:
                raise e

    def __delattr__(self, item):
        try:
            return local.__delattr__(self, item)
        except AttributeError as e:
            try:
                self.copy_parent_attribute()
                return local.__delattr__(self, item)
            except AttributeError:
                raise e
