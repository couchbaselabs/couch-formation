##
##

from typing import Callable
from functools import wraps


def prereq(requirements=()) -> Callable:
    def prereq_handler(func):
        @wraps(func)
        def f_wrapper(self, *args, **kwargs):
            for p_func in requirements:
                getattr(self, p_func)(*args, **kwargs)
            try:
                return func(self, *args, **kwargs)
            except Exception:
                raise
        return f_wrapper
    return prereq_handler
