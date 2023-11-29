from time import time


def measure_func(func):
    # this wrapper shows the execution time of the function object passed
    def wrap_func(*args, **kwargs):
        t1 = time()
        result = func(*args, **kwargs)
        t2 = time()
        print(f'{func.__name__!r} executed in {(t2-t1):.4f}s, with result: {result}')
        return result
    return wrap_func